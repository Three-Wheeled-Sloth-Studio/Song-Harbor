import { useCallback, useEffect, useRef, useState } from "react";
import { Button, IconButton, Status } from "@tws-ui/core/react";
import { DawHandoff } from "./DawHandoff";
import { AudioIcon } from "./AudioIcons";
import { SectionEditor } from "./SectionEditor";
import { ChannelSplitter } from "./ChannelSplitter";
import { StemWaveforms } from "./StemWaveforms";
import { SectionsTool } from "./SectionsTool";
import { SectionPanTool, type SavedPanTarget } from "./SectionPanTool";
import { SectionReverbTool, type SavedReverbTarget } from "./SectionReverbTool";
import { compileSectionAutomation } from "./SectionAutomation";
import { SharedClockAudition, type AuditionSource } from "./SharedClockAudition";
import type { SongSection } from "./SectionEditor";

type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
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
  const renderedUrl=useRef<string|null>(null);
  useEffect(()=>()=>{if(renderedUrl.current)URL.revokeObjectURL(renderedUrl.current);},[]);
  const [error, setError] = useState("");
  const [channels,setChannels]=useState<ChannelSets>({});
  const [routingVersion,setRoutingVersion]=useState(0);
  const [channelBusy,setChannelBusy]=useState(false);
  const [zoom,setZoom]=useState(1);
  const timelineRef=useRef<HTMLElement|null>(null);
  const [viewportOffset,setViewportOffset]=useState(0);
  const [timelineSections,setTimelineSections]=useState<SongSection[]>(initialSections||[]);
  const [panTargets,setPanTargets]=useState<SavedPanTarget[]>([]);
  const [reverbTargets,setReverbTargets]=useState<SavedReverbTarget[]>([]);
  const [panLoaded,setPanLoaded]=useState(false);
  const [scriptOpen,setScriptOpen]=useState(false);
  const [scriptFocus,setScriptFocus]=useState<SongSection|null>(null);
  const [scriptRevision,setScriptRevision]=useState(0);
  const [externalSections,setExternalSections]=useState<SongSection[]|undefined>(undefined);
  const [loopEnabled,setLoopEnabled]=useState(false);
  const [loopIn,setLoopIn]=useState<number|null>(null);
  const [loopOut,setLoopOut]=useState<number|null>(null);
  const audio=useRef<SharedClockAudition|null>(null);
  const [audioLoad,setAudioLoad]=useState<{ready:number;total:number}|null>(null);
  const [audioReady,setAudioReady]=useState(false);
  const monitorRef=useRef(monitorVolume);
  monitorRef.current=monitorVolume;
  const playRef = useRef(false);
  const transportGeneration=useRef(0);
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
  useEffect(()=>{
    let cancelled=false;
    setPanLoaded(false);
    setPanTargets([]);
    setReverbTargets([]);
    void fetch("/api/projects/"+jobId+"/sections/export")
      .then(async response=>{
        if(!response.ok)throw Error("Could not load pan automation");
        return response.json() as Promise<{reverb_targets:typeof reverbTargets}>;
      })
      .then(async data=>{
        const panResponse=await fetch("/api/projects/"+jobId+"/section-pan");
        if(!panResponse.ok)throw Error("Could not load pan automation");
        const panData=await panResponse.json() as {targets:SavedPanTarget[]};
        if(!cancelled){setPanTargets(panData.targets||[]);setReverbTargets(data.reverb_targets||[]);setPanLoaded(true);}
      })
      .catch(e=>{if(!cancelled)setError(e instanceof Error?e.message:String(e));});
    return ()=>{cancelled=true;};
  },[jobId]);

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
    playRef.current=false;
    audio.current?.pause();
    setPlaying(false);
    setPosition(audio.current?.position??0);
  },[]);

  useEffect(()=>{
    let cancelled=false;
    const generation=++transportGeneration.current;
    const engine=new SharedClockAudition();
    audio.current=engine;
    setAudioReady(false);
    setAudioLoad({ready:0,total:files.length});
    setError("");
    playRef.current=false;
    setPlaying(false);
    setPosition(0);
    setDuration(expectedDuration||0);
    const sources:AuditionSource[]=[];
    for(const filename of files){
      const split=channels[filename];
      if(split?.active){
        sources.push({key:filename+":left",filename,url:split.tracks.left.url,pan:-1});
        sources.push({key:filename+":right",filename,url:split.tracks.right.url,pan:1});
      }else{
        sources.push({key:filename,filename,
          url:"/api/jobs/"+jobId+"/stream/"+encodeURIComponent(filename),pan:0});
      }
    }
    setAudioLoad({ready:0,total:sources.length});
    void engine.prepare(sources,(ready,total)=>{
      if(!cancelled)setAudioLoad({ready,total});
    }).then(()=>{
      if(cancelled||generation!==transportGeneration.current)return;
      const levels:Record<string,{gain:number}>={};
      const settings=stemsRef.current;
      const solo=settings.some(stem=>stem.solo);
      for(const stem of settings)levels[stem.filename]={gain:effectiveGain(stem,solo)};
      engine.setLevels(levels,monitorRef.current/100);
      setDuration(engine.duration);
      setAudioReady(true);
      setAudioLoad(null);
    }).catch(err=>{
      if(cancelled)return;
      setAudioReady(false);
      setAudioLoad(null);
      setError(err instanceof Error?err.message:String(err));
    });
    return ()=>{
      cancelled=true;
      ++transportGeneration.current;
      playRef.current=false;
      if(audio.current===engine)audio.current=null;
      void engine.dispose();
    };
  },[files,jobId,expectedDuration,routingVersion]);

  useEffect(()=>{
    const levels:Record<string,{gain:number}>={};
    for(const stem of stems)levels[stem.filename]={gain:effectiveGain(stem,anySolo)};
    audio.current?.setLevels(levels,monitorVolume/100);
  },[stems,anySolo,monitorVolume,audioReady]);

  useEffect(()=>{
    const engine=audio.current;
    if(!engine?.ready||!panLoaded)return;
    const byFile:Record<string,{pan?:ReturnType<typeof compileSectionAutomation>;reverb?:ReturnType<typeof compileSectionAutomation>}>={};
    const sectionById=new Map(timelineSections.map(section=>[section.id,section]));
    for(const filename of files){
      const saved=panTargets.filter(item=>item.source_key===filename);
      if(!saved.length)continue;
      const desired=saved.flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{
          sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.pan,transitionSeconds:item.transition_seconds,curve:item.curve,
        }]:[];
      });
      try{
        byFile[filename]={pan:compileSectionAutomation(desired,0,{min:-1,max:1})};
      }catch(e){
        setError(e instanceof Error?e.message:"Invalid section pan automation");
        return;
      }
    }
    for(const filename of files){
      const desired=reverbTargets.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.wet,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),reverb:compileSectionAutomation(desired,0,{min:0,max:1})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid reverb automation");return;}
    }
    engine.setAutomation(byFile);
  },[audioReady,panLoaded,panTargets,reverbTargets,timelineSections,files]);

  // Monitoring volume never changes the rendered mix; only stem edits invalidate it.
  useEffect(() => { setMixUrl(null); }, [stems]);

  useEffect(()=>{
    if(!playing)return;
    const timer=window.setInterval(()=>{
      const engine=audio.current;
      if(!engine||!engine.playing)return;
      const now=engine.position;
      setPosition(now);
      if(loopEnabled&&loopIn!==null&&loopOut!==null&&loopOut>loopIn+0.1
          &&now>=loopOut-0.02){
        engine.seek(loopIn);
        setPosition(loopIn);
        return;
      }
      if(now>=engine.duration-0.025){
        stop();
        setPosition(engine.duration);
      }
    },33);
    return ()=>window.clearInterval(timer);
  },[playing,stop,loopEnabled,loopIn,loopOut]);

  async function togglePlayback(){
    if(playRef.current){stop();return;}
    const engine=audio.current;
    if(!engine?.ready){setError("Synchronized audio is still loading.");return;}
    setError("");
    const generation=++transportGeneration.current;
    playRef.current=true;
    try{
      await engine.play();
      if(generation!==transportGeneration.current){
        engine.pause();
        return;
      }
      setPosition(engine.position);
      setPlaying(true);
    }catch(err){
      if(generation===transportGeneration.current){
        playRef.current=false;
        setPlaying(false);
        setError(err instanceof Error?err.message:"Synchronized playback failed");
      }
    }
  }

  function seek(next:number){
    const target=Math.max(0,Math.min(duration,next));
    audio.current?.seek(target);
    setPosition(target);
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
    const engine=audio.current;
    if(!engine?.ready){setError("Wait for synchronized audio to load before exporting.");return;}
    stop();
    setExporting(true);
    setMixUrl(null);
    setError("");
    try{
      const blob=await engine.renderWav24();
      if(renderedUrl.current)URL.revokeObjectURL(renderedUrl.current);
      renderedUrl.current=URL.createObjectURL(blob);
      setMixUrl(renderedUrl.current);
      setNotice("Rendered 24-bit WAV using the audition routing and section automation. Monitoring volume excluded.");
    }catch(e){
      setError(e instanceof Error?e.message:"Processed WAV export failed");
    }finally{
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
        {audioLoad&&<div className="audition-buffer-status" role="status">
          Preparing synchronized audio · {audioLoad.ready}/{audioLoad.total} tracks
        </div>}
        <div className="transport production-playline" aria-label="Playback transport">
          <button type="button" title="Rewind 5 seconds; right click to start" aria-label="Rewind five seconds"
            onClick={()=>skip(-5)}
            onContextMenu={e=>{e.preventDefault();seek(0);}}>⏪</button>
          <IconButton icon={playing?"⏸":"▶"} label={playing?"Pause":"Play"} disabled={!audioReady} onClick={togglePlayback}/>
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
          onApplied={(items,targets,reverb)=>{
            setPanTargets(targets);
            setReverbTargets(reverb);
            setExternalSections(items);setTimelineSections(items);
            setZoom(1);setViewportOffset(0);setScriptRevision(v=>v+1);
          }}/>
        <SectionPanTool jobId={jobId} sections={timelineSections} files={files}
          targets={panTargets} onChange={items=>{setPanTargets(items);setMixUrl(null);}}/>
        <SectionReverbTool jobId={jobId} sections={timelineSections} files={files}
          targets={reverbTargets} onChange={items=>{setReverbTargets(items);setMixUrl(null);}}/>
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
