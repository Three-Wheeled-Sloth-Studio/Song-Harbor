import { useCallback, useEffect, useRef, useState } from "react";
import { Button, IconButton, Status } from "@tws-ui/core/react";
import { DawHandoff } from "./DawHandoff";
import { AudioIcon } from "./AudioIcons";
import { SectionEditor } from "./SectionEditor";
import { ChannelSplitter } from "./ChannelSplitter";
import { StemWaveforms } from "./StemWaveforms";
import { SectionsTool } from "./SectionsTool";
import type { SongSection } from "./SectionEditor";

type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
type MixResponse = { url: string; filename: string };
type ChildSet = {active:boolean;export:string;tracks:{left:{url:string;file:string};right:{url:string;file:string}}};
type ChannelSets = Record<string,ChildSet>;
export type SavedStem = {filename: string; gain: number; mute: boolean; solo: boolean};
const names = ["Vocals", "Drums", "Bass", "Guitar", "Piano", "Other"];



function labelOf(filename: string) {
  return names.find(label => filename.includes("(" + label + ")")) || filename;
}
function timecode(seconds: number) {
  const s = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}
function effectiveGain(stem: Stem, anySolo: boolean) {
  return stem.mute || (anySolo && !stem.solo) ? 0 : stem.gain / 100;
}

export function StemMixer({ jobId, files, expectedDuration, onMissingFfmpeg, savedStems, initialSections, initialTitle, onSaved }: {
  jobId: string; files: string[]; expectedDuration?: number;
  onMissingFfmpeg?: (retry: () => void) => void;
  savedStems?: SavedStem[];
  initialSections?: SongSection[];
  initialTitle?: string;
  onSaved?: () => void;
}) {
  const [stems, setStems] = useState<Stem[]>(() => files.map(filename => {
    const saved = savedStems?.find(stem => stem.filename === filename);
    return {
      filename, name: labelOf(filename),
      gain: saved ? Math.round(saved.gain * 100) : 100,
      mute: saved?.mute ?? false, solo: saved?.solo ?? false,
    };
  }).sort((a, b) => names.indexOf(a.name) - names.indexOf(b.name)));
  const [title, setTitle] = useState(initialTitle || "Untitled song");
  const [saving, setSaving] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [dawOpen, setDawOpen] = useState(false);
  const [handoffFolder, setHandoffFolder] = useState("");
  const [notice, setNotice] = useState("");
  const [playing, setPlaying] = useState(false);
  const [monitorVolume, setMonitorVolume] = useState(75);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(expectedDuration || 0);
  const [exporting, setExporting] = useState(false);
  const [mixUrl, setMixUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [channels,setChannels]=useState<ChannelSets>({});
  const [routingVersion,setRoutingVersion]=useState(0);
  const [channelBusy,setChannelBusy]=useState(false);
  const [zoom,setZoom]=useState(1);
  const timelineRef=useRef<HTMLElement|null>(null);
  const [viewportOffset,setViewportOffset]=useState(0);
  const [timelineSections,setTimelineSections]=useState<SongSection[]>(initialSections||[]);
  const [scriptOpen,setScriptOpen]=useState(false);
  const [scriptFocus,setScriptFocus]=useState<SongSection|null>(null);
  const [scriptRevision,setScriptRevision]=useState(0);
  const [externalSections,setExternalSections]=useState<SongSection[]|undefined>(undefined);
  const [loopEnabled,setLoopEnabled]=useState(false);
  const [loopIn,setLoopIn]=useState<number|null>(null);
  const [loopOut,setLoopOut]=useState<number|null>(null);
  const context=useRef<AudioContext|null>(null);
  const audio = useRef<Map<string, HTMLAudioElement>>(new Map());
  const playRef = useRef(false);
  const transportGeneration=useRef(0);
  const lastHardResync=useRef(0);
  const clockSamples=useRef(new Map<HTMLAudioElement,number>());
  const seekRef = useRef(0);
  const stemsRef = useRef(stems);
  stemsRef.current = stems;
  const anySolo = stems.some(s => s.solo);
  const visibleSeconds=duration>0?duration/zoom:0;
  const viewStart=duration>0?(duration-visibleSeconds)*viewportOffset:0;
  const viewEnd=duration>0?viewStart+visibleSeconds:0;
  // Timeline wheel zooms around the pointer; Shift+wheel pans the visible window.
  // Native non-passive handler ensures preventDefault works in Chromium.
  useEffect(()=>{
    const element=timelineRef.current;
    if(!element)return;
    const choices=[1,2,4,8,16];
    function wheel(event:WheelEvent){
      if(!duration)return;
      const source=event.target;
      if(source instanceof Element && source.closest("input,select,textarea,[contenteditable=true],button:not(.waveform-seek)"))return;
      const amount=event.deltaY||event.deltaX;
      if(!amount)return;
      event.preventDefault();
      if(event.shiftKey){
        setViewportOffset(current=>Math.max(0,Math.min(1,current+Math.sign(amount)*0.07)));
        return;
      }
      const bounds=(element!.querySelector(".waveform-seek")||element!).getBoundingClientRect();
      const fraction=Math.max(0,Math.min(1,(event.clientX-bounds.left)/Math.max(1,bounds.width)));
      const currentZoom=zoom;
      const currentIndex=choices.indexOf(currentZoom);
      const nextZoom=choices[Math.max(0,Math.min(choices.length-1,currentIndex+(amount>0?-1:1)))];
      if(nextZoom===currentZoom)return;
      const point=(duration-duration/currentZoom)*viewportOffset+fraction*duration/currentZoom;
      const nextWidth=duration/nextZoom;
      const nextOffset=nextZoom===1?0:(point-fraction*nextWidth)/(duration-nextWidth);
      setZoom(nextZoom);
      setViewportOffset(Math.max(0,Math.min(1,nextOffset)));
    }
    element.addEventListener("wheel",wheel,{passive:false});
    return ()=>element.removeEventListener("wheel",wheel);
  },[duration,zoom,viewportOffset]);

  const refreshChannels=useCallback(async()=>{
    const r=await fetch("/api/projects/"+jobId+"/channels");
    if(r.ok){const data=await r.json() as {channels:ChannelSets};setChannels(data.channels||{});setRoutingVersion(v=>v+1);}
  },[jobId]);
  useEffect(()=>{void refreshChannels();},[refreshChannels]);
  async function toggleChannel(filename:string){
    const entry=channels[filename];
    if(!entry||channelBusy)return;
    stop();setChannelBusy(true);setError("");
    try{
      const r=await fetch("/api/projects/"+jobId+"/channels",{method:"PUT",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({filename,active:!entry.active})});
      const data=await r.json() as {channels?:ChannelSets;detail?:string};
      if(!r.ok||!data.channels)throw Error(data.detail||"Routing update failed");
      setChannels(data.channels);setRoutingVersion(v=>v+1);setMixUrl(null);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setChannelBusy(false);}
  }
  const stop = useCallback(() => {
    transportGeneration.current+=1;
    playRef.current = false;
    setPlaying(false);
    audio.current.forEach(element => {element.pause();element.playbackRate=1;});
    clockSamples.current.clear();
  }, []);

  useEffect(() => {
    const players=new Map<string,HTMLAudioElement>();
    const ctx=new AudioContext();
    context.current=ctx;
    for(const filename of files){
      const split=channels[filename];
      const sources=split?.active
        ? [{key:filename+":left",url:split.tracks.left.url,pan:-1},
           {key:filename+":right",url:split.tracks.right.url,pan:1}]
        : [{key:filename,url:"/api/jobs/"+jobId+"/stream/"+encodeURIComponent(filename),pan:0}];
      for(const item of sources){
        const player=new Audio(item.url);
        player.preload="auto";
        player.addEventListener("loadedmetadata",()=>{
          if(Number.isFinite(player.duration))setDuration(current=>Math.max(current,player.duration));
        });
        player.addEventListener("error",()=>{
          setError("An audio stream failed. Verify the derived channel files.");
          stop();
        });
        const source=ctx.createMediaElementSource(player);
        if(item.pan===0)source.connect(ctx.destination);
        else {
          const panner=ctx.createStereoPanner();
          panner.pan.value=item.pan;
          source.connect(panner).connect(ctx.destination);
        }
        players.set(item.key,player);
      }
    }
    audio.current=players;
    setDuration(expectedDuration||0);
    setPosition(0);setPlaying(false);playRef.current=false;
    lastHardResync.current=0;
    clockSamples.current.clear();
    return ()=>{
      players.forEach(p=>{p.pause();p.removeAttribute("src");p.load();});
      players.clear();
      void ctx.close();
      if(context.current===ctx)context.current=null;
    };
  },[files,jobId,expectedDuration,stop,routingVersion]);

  useEffect(()=>{
    for(const stem of stems){
      const entry=channels[stem.filename];
      const keys=entry?.active?[stem.filename+":left",stem.filename+":right"]:[stem.filename];
      for(const key of keys){
        const player=audio.current.get(key);
        if(player)player.volume=Math.min(1,Math.max(0,effectiveGain(stem,anySolo)*monitorVolume/100));
      }
    }
  },[stems,anySolo,monitorVolume,channels,routingVersion]);

  // Monitoring volume never changes the rendered mix; only stem edits invalidate it.
  useEffect(() => { setMixUrl(null); }, [stems]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const entries=[...audio.current.entries()];
      if(entries.length===0)return;
      const available:{player:HTMLAudioElement;time:number;audible:boolean}[]=[];
      // A stalled or buffering media element must never become the timeline clock.
      // Select from streams that demonstrably advanced since the last sample.
      const samples=clockSamples.current;
      const activeStems=stemsRef.current;
      const soloed=activeStems.some(s=>s.solo);
      for(const [key,player] of entries){
        const current=player.currentTime;
        const previous=samples.get(player);
        samples.set(player,current);
        if(player.paused||player.ended||player.seeking||player.readyState<2)continue;
        if(previous===undefined||current-previous<0.012||current-previous>1.0)continue;
        const stem=activeStems.find(x=>key===x.filename||key.startsWith(x.filename+":"));
        const audible=stem?effectiveGain(stem,soloed)>0 && monitorVolume>0:false;
        available.push({player,time:current,audible});
      }
      if(available.length===0){
        // When all tracks end, stop even though none can be a moving clock.
        // If they are merely buffering, hold the last genuine audio position.
        if(entries.every(([,player])=>player.ended))stop();
        return;
      }
      const audible=available.filter(item=>item.audible);
      const candidates=audible.length>0?audible:available;
      const ordered=candidates.map(item=>item.time).sort((x,y)=>x-y);
      const midpoint=Math.floor(ordered.length/2);
      const current=ordered.length%2===1
        ?ordered[midpoint]:(ordered[midpoint-1]+ordered[midpoint])/2;
      setPosition(current);
      const players=entries.map(([,player])=>player);
      if(loopEnabled&&loopIn!==null&&loopOut!==null&&loopOut>loopIn+0.1&&current>=loopOut-0.02){
        players.forEach(player=>{
          player.playbackRate=1;
          try{player.currentTime=loopIn;}catch{/* decoder not ready */}
        });
        samples.clear();
        lastHardResync.current=performance.now();
        setPosition(loopIn);
        return;
      }
      if((duration>0&&current>=duration-0.03)||players.every(player=>player.ended)){
        stop();
        return;
      }
      // Softly bring other *moving* streams towards the actual audible position.
      // In particular, never drag the timeline back to a stuck first stem.
      const now=performance.now();
      const advancing=new Set(available.map(item=>item.player));
      for(const player of players){
        if(!advancing.has(player)){
          player.playbackRate=1;
          continue;
        }
        const difference=player.currentTime-current;
        if(Math.abs(difference)>1.5&&now-lastHardResync.current>4000&&player.readyState>=3){
          lastHardResync.current=now;
          try{player.currentTime=current;}catch{/* decoder not ready */}
          player.playbackRate=1;
        }else if(Math.abs(difference)>0.12){
          player.playbackRate=difference>0?0.975:1.025;
        }else{
          player.playbackRate=1;
        }
      }
    }, 160);
    return () => window.clearInterval(timer);
  }, [playing,duration,stop,loopEnabled,loopIn,loopOut,monitorVolume]);

  async function togglePlayback() {
    if(playRef.current){stop();return;}
    setError("");
    const players=[...audio.current.values()];
    if(players.length<6){setError("Audio tracks have not loaded.");return;}
    const generation=++transportGeneration.current;
    clockSamples.current.clear();
    playRef.current=true;
    const time=position>=duration-0.05&&duration>0?0:position;
    try{
      await context.current?.resume();
      if(generation!==transportGeneration.current)return;
      // Preserve current position on resume instead of re-seeking every source.
      // Only seek if reset/explicit navigation changed its time materially.
      for(const player of players){
        if(Math.abs(player.currentTime-time)>0.3)player.currentTime=time;
        player.playbackRate=1;
      }
      await Promise.all(players.map(player=>player.play()));
      if(generation!==transportGeneration.current){
        players.forEach(player=>player.pause());
        return;
      }
      setPlaying(true);
    }catch{
      if(generation===transportGeneration.current){
        stop();
        setError("Playback failed. Check that the stems have finished loading.");
      }
    }
  }

  function seek(next: number) {
    clockSamples.current.clear();
    lastHardResync.current=performance.now();
    setPosition(next);
    seekRef.current = next;
    audio.current.forEach(player => {
      try { player.currentTime = next; } catch { /* player metadata not yet ready */ }
    });
  }

  const positionRef=useRef(position);
  positionRef.current=position;
  const togglePlaybackRef=useRef(togglePlayback);
  togglePlaybackRef.current=togglePlayback;
  const durationRef=useRef(duration);
  durationRef.current=duration;
  const seekRefFunction=useRef(seek);
  seekRefFunction.current=seek;
  useEffect(()=>{
    // Capture before focused buttons receive the browser's Space-to-click.
    // Typing, native form controls and accessible section sliders keep their keys.
    function keydown(event:KeyboardEvent){
      if(event.altKey||event.ctrlKey||event.metaKey||event.repeat)return;
      const source=event.target;
      if(source instanceof Element &&
          source.closest('input,textarea,select,[contenteditable="true"],[role="slider"],[role="textbox"]'))return;
      if(event.code==="Space"){
        event.preventDefault();
        event.stopPropagation();
        void togglePlaybackRef.current();
      }else if(event.key==="ArrowLeft"){
        event.preventDefault();
        seekRefFunction.current(Math.max(0,positionRef.current-5));
      }else if(event.key==="ArrowRight"){
        event.preventDefault();
        seekRefFunction.current(Math.min(durationRef.current,positionRef.current+5));
      }
    }
    function keyup(event:KeyboardEvent){
      if(event.code!=="Space"||event.altKey||event.ctrlKey||event.metaKey)return;
      const source=event.target;
      if(source instanceof Element &&
        source.closest('input,textarea,select,[contenteditable="true"],[role="slider"],[role="textbox"]'))return;
      // Native button activation usually happens on Space keyup.
      event.preventDefault();
      event.stopPropagation();
    }
    window.addEventListener("keydown",keydown,true);
    window.addEventListener("keyup",keyup,true);
    return ()=>{
      window.removeEventListener("keydown",keydown,true);
      window.removeEventListener("keyup",keyup,true);
    };
  },[]);
  function stopAndReset(){stop();seek(0);}
  function skip(seconds:number){seek(Math.max(0,Math.min(duration,position+seconds)));}
  function update(filename: string, changes: Partial<Stem>) {
    setStems(current => current.map(s => s.filename === filename ? { ...s, ...changes } : s));
  }

  async function saveProject(): Promise<boolean> {
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await fetch("/api/projects/" + jobId, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), stems: stemsRef.current.map(s => ({
          filename: s.filename, gain: s.gain / 100, mute: s.mute, solo: s.solo,
        })) }),
      });
      if (!result.ok) {
        const detail = await result.json().catch(() => ({})) as {detail?: string};
        throw new Error(detail.detail || "Could not save song project");
      }
      setNotice("Song project saved.");
      onSaved?.();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save song project");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handoffWaveform() {
    setHandoffBusy(true); setError(""); setNotice("");
    try {
      if (!(await saveProject())) return;
      const response = await fetch("/api/projects/" + jobId + "/waveform", {method: "POST"});
      const result = await response.json() as {directory?: string;detail?: string};
      if (!response.ok || !result.directory) throw new Error(result.detail || "Waveform export failed");
      setHandoffFolder(result.directory);
      setNotice("Waveform folder ready. Import the six WAVs on separate tracks at 0:00.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Waveform export failed");
    } finally {
      setHandoffBusy(false);
    }
  }

  async function openWaveformFolder() {
    try {
      const response = await fetch("/api/projects/" + jobId + "/waveform/open", {method: "POST"});
      if (!response.ok) throw new Error("Could not open Waveform folder");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open folder");
    }
  }

  async function exportMix() {
    stop();
    setExporting(true);
    setMixUrl(null);
    setError("");
    try {
      const response = await fetch("/api/jobs/" + jobId + "/mix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stems: stemsRef.current.map(s => ({
          filename: s.filename, gain: s.gain / 100, mute: s.mute, solo: s.solo,
        })) }),
      });
      const data = await response.json() as MixResponse & { detail?: string };
      if (!response.ok) {
        if (response.status === 409 && /ffmpeg/i.test(data.detail || "") && onMissingFfmpeg) {
          onMissingFfmpeg(() => { void exportMix(); });
          return;
        }
        throw new Error(data.detail || "Mix export failed");
      }
      setMixUrl(data.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Mix export failed");
    } finally {
      setExporting(false);
    }
  }

  return <section className="mixer" aria-label="Stem mixer">
    <div className="song-project-controls">
      <label htmlFor="song-project-name">Song project</label>
      <input id="song-project-name" value={title} maxLength={120} onChange={e => setTitle(e.target.value)} />
      <IconButton icon="▣" label="Save song" disabled={saving || !title.trim()} onClick={() => { void saveProject(); }}/>
    </div>
    <div className="production-workspace">
      <main className="production-main">
        <div className="transport production-playline" aria-label="Playback transport">
          <button type="button" title="Rewind 5 seconds; right click to start" aria-label="Rewind five seconds"
            onClick={()=>skip(-5)}
            onContextMenu={e=>{e.preventDefault();seek(0);}}>⏪</button>
          <IconButton icon={playing?"⏸":"▶"} label={playing?"Pause":"Play"} onClick={togglePlayback}/>
          <button type="button" title="Stop and return to start" aria-label="Stop" onClick={stopAndReset}>■</button>
          <button type="button" title="Forward 5 seconds" aria-label="Forward five seconds" onClick={()=>skip(5)}>⏩</button>
          <span className="timecode">{timecode(position)}</span>
          <input type="range" aria-label="Playback position" min={0} max={Math.max(duration,1)}
            step={0.05} value={Math.min(position,duration||1)} onChange={e=>seek(Number(e.target.value))}/>
          <span className="timecode">{timecode(duration)}</span>
          <label className="master-monitor" title="Monitoring volume; does not change exported mixes">
            <span aria-hidden="true">🔊</span>
            <input type="range" min="0" max="100" step="1" value={monitorVolume}
              aria-label="Playback monitoring volume" onChange={e=>setMonitorVolume(Number(e.target.value))}/>
          </label>
        </div>
        <section ref={timelineRef} className="integrated-timeline" aria-label="Integrated production timeline">
          <SectionEditor jobId={jobId} duration={duration} position={position}
            initialSections={initialSections} externalSections={externalSections}
            onSeek={seek} viewStart={viewStart} viewEnd={viewEnd}
            onSectionsChange={setTimelineSections}
            onPersisted={()=>setScriptRevision(v=>v+1)}
            onSectionDoubleClick={section=>{setScriptFocus(section);setScriptOpen(true);}}/>
          <StemWaveforms jobId={jobId} files={stems.map(s=>({
            filename:s.filename,label:s.name,
            children:channels[s.filename]?.active?(["left","right"] as const).map(channel=>({
              filename:s.filename+":"+channel,label:"↳ "+channel.toUpperCase(),
              waveUrl:"/api/projects/"+jobId+"/channels/waveform/"+encodeURIComponent(s.filename)+"/"+channel
            })):[]
          }))} duration={duration} position={position} onSeek={seek}
            viewStart={viewStart} viewEnd={viewEnd} sections={timelineSections}/>
        </section>
        <div className="mixer-heading">
          <div><h3>Stems</h3></div>
          <IconButton icon="↶" label="Reset mix" onClick={()=>{
            setStems(current=>current.map(s=>({...s,gain:100,mute:false,solo:false})));
          }}/>
        </div>
        <div className="mixer-tracks">
      {stems.map(s => <div className="mixer-track" key={s.filename}>
        <strong className="stem-icon-name" title={s.name} aria-label={s.name}><AudioIcon kind={s.name} size={32}/><span className="sr-only">{s.name}</span></strong>
        <div className="track-actions">
          <button type="button" className={"track-toggle" + (s.mute ? " is-muted" : "")}
            aria-pressed={s.mute} title={"Mute " + s.name} onClick={() => update(s.filename, { mute: !s.mute })}>M</button>
          <button type="button" className={"track-toggle" + (s.solo ? " is-solo" : "")}
            aria-pressed={s.solo} title={"Solo " + s.name} onClick={() => update(s.filename, { solo: !s.solo })}>S</button>
        </div>
        <input type="range" min="0" max="100" step="1" value={s.gain}
          aria-label={s.name + " volume"} onChange={e => update(s.filename, {gain: Number(e.target.value)})} />
        <span className="track-percent">{s.gain}%</span>
        {channels[s.filename]&&<button type="button" className="derived-route-toggle"
          disabled={channelBusy} onClick={()=>{void toggleChannel(s.filename);}}
          title="Switch between stereo original and left/right derived children">
          {channels[s.filename].active?"L/R active":"Stereo active"}
        </button>}
      </div>)}<div className="derived-routing-note">{Object.values(channels).some(c=>c.active)
        ?"Split channels replace their parent originals in playback and mix export."
        :"Original stereo stems active. Expand split channels with their track buttons."}</div>
    </div>
      </main>
      <aside className="production-tools" aria-label="Production tools">
        <div className="production-tools-heading"><strong>Tools</strong><span aria-hidden="true">⚙</span></div>
        <button type="button" className="production-tool-open" aria-expanded={scriptOpen}
          onClick={()=>{setScriptFocus(null);setScriptOpen(v=>!v);}}
          title="Open canonical time-stamped arrangement text">≡ Sections</button>
        <SectionsTool jobId={jobId} open={scriptOpen}
          onClose={()=>setScriptOpen(false)} focused={scriptFocus} revision={scriptRevision}
          onApplied={items=>{
            setExternalSections(items);setTimelineSections(items);
            setZoom(1);setViewportOffset(0);setScriptRevision(v=>v+1);
          }}/>
        <div className="production-tools-zoom">
          <strong>Zoom</strong>
          <select aria-label="Timeline zoom" value={zoom} onChange={e=>setZoom(Number(e.target.value))}>
            {[1,2,4,8,16].map(v=><option value={v} key={v}>{v}×</option>)}
          </select>
          <input type="range" aria-label="Timeline zoom slider" min="0" max="4" step="1"
            value={Math.log2(zoom)} onChange={e=>setZoom(2**Number(e.target.value))}/>
          {zoom>1&&<input type="range" aria-label="Timeline horizontal position" min="0" max="1" step=".001"
            value={viewportOffset} onChange={e=>setViewportOffset(Number(e.target.value))}/>}
        </div>
        <details className="production-tool-detail"><summary>⇥ Region loop</summary>
          <div className="timeline-loop-controls">
            <button type="button" onClick={()=>setLoopIn(position)}>In</button>
            <button type="button" onClick={()=>setLoopOut(position)}>Out</button>
            <label><input type="checkbox" checked={loopEnabled}
              disabled={loopIn===null||loopOut===null||loopOut<=loopIn+0.1}
              onChange={e=>setLoopEnabled(e.target.checked)}/> Loop</label>
            <span>{loopIn===null?"—":timecode(loopIn)} – {loopOut===null?"—":timecode(loopOut)}</span>
            <button type="button" onClick={()=>{setLoopEnabled(false);setLoopIn(null);setLoopOut(null);}}>×</button>
          </div>
        </details>
    <div className="mix-footer">
      <div className="mix-actions">
        <IconButton icon="⇩" label={exporting ? "Rendering mix WAV" : "Export mix WAV"}
          disabled={exporting} onClick={exportMix}/>
        {mixUrl && <a className="mix-download" href={mixUrl} download="Song Harbor Mix.wav" title="Download mix WAV">⇩ WAV</a>}
      </div>
      {exporting ? <Status tone="info">Export in progress</Status> : mixUrl ? <Status tone="success">Mix ready</Status> : null}
    </div>
    <ChannelSplitter jobId={jobId} files={files} onMissingFfmpeg={onMissingFfmpeg} onCompleted={()=>{void refreshChannels();}} />
    <div className="daw-handoff">
      <IconButton icon="🎚" label="Export to DAW" onClick={() => setDawOpen(true)}/>
    </div>
      </aside>
    </div>
    {dawOpen && <DawHandoff jobId={jobId} saveProject={saveProject} onClose={() => setDawOpen(false)} />}
    {notice && <p role="status" className="song-save-notice">{notice}</p>}
    {error && <p role="alert" className="error-message">{error}</p>}

  </section>;
}
