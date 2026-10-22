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
import { SectionWidthTool, type SavedWidthTarget } from "./SectionWidthTool";
import { SectionSpaceTool } from "./SectionSpaceTool";
import { SectionEqTool,type SavedEqTarget } from "./SectionEqTool";
import {SectionDeEssTool} from "./SectionDeEssTool";
import { EndingTool } from "./EndingTool";
import { compileSectionAutomation } from "./SectionAutomation";
import { SharedClockAudition, MixHeadroomError, type AuditionSource } from "./SharedClockAudition";
import type {AudioFinding} from "./AudioCleanupAnalyzer";
import {CleanupReview} from "./CleanupReview";
import {CorrectionWorkbench,type CorrectionDraft} from "./CorrectionWorkbench";
import {ToolWindow,TOOL_ITEMS,type WorkbenchTool} from "./WorkbenchTools";
import type { SongSection } from "./SectionEditor";

type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
type ChildSet = {active:boolean;export:string;tracks:{left:{url:string;file:string};right:{url:string;file:string}}};
type ChannelSets = Record<string,ChildSet>;
type EffectKey="pan"|"width"|"space"|"reverb"|"ending"|"eq"|"compression"|"ducking";
const EFFECT_KEYS:EffectKey[]=["pan","width","space","reverb","eq","compression","ducking","ending"];
const DEFAULT_BYPASS:Record<EffectKey,boolean>={pan:false,width:false,space:false,reverb:false,eq:false,compression:false,ducking:false,ending:false};
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

export function StemMixer({ jobId, files, expectedDuration, onMissingFfmpeg, savedStems, trackLabels, trackAliases, initialSections, initialTitle, onSaved }: {
  jobId: string; files: string[]; expectedDuration?: number;
  onMissingFfmpeg?: (retry: () => void) => void;
  savedStems?: SavedStem[];
  trackLabels?: Record<string,string>;
  trackAliases?: Record<string,string>;
  initialSections?: SongSection[];
  initialTitle?: string;
  onSaved?: () => void;
}) {
  const [stems, setStems] = useState<Stem[]>(() => files.map(filename => {
    const saved = savedStems?.find(stem => stem.filename === filename);
    return {
      filename, name: trackLabels?.[filename] || labelOf(filename),
      gain: saved ? Math.round(saved.gain * 100) : 100,
      mute: saved?.mute ?? false, solo: saved?.solo ?? false,
    };
  }).sort((a, b) => {const x=names.indexOf(a.name),y=names.indexOf(b.name);return x<0||y<0?0:x-y;}));
  const [title, setTitle] = useState(initialTitle || "Untitled song");
  const [saving, setSaving] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [dawOpen, setDawOpen] = useState(false);
  const [handoffFolder, setHandoffFolder] = useState("");
  const [notice, setNotice] = useState("");
  const [playing, setPlaying] = useState(false);
  const [monitorVolume, setMonitorVolume] = useState(75);
  const [bypassed,setBypassed]=useState<Record<EffectKey,boolean>>(DEFAULT_BYPASS);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(expectedDuration || 0);
  const [exporting, setExporting] = useState(false);
  const [cleanupFindings,setCleanupFindings]=useState<readonly AudioFinding[]>([]);
  const [cleanupScanned,setCleanupScanned]=useState(false);
  const [analyzing,setAnalyzing]=useState(false);
  const [cleanupError,setCleanupError]=useState("");
  const analysisRevision=useRef(0);
  const [masterTrimDb,setMasterTrimDb]=useState(0);
  const [headroomIssue,setHeadroomIssue]=useState<{peakDbfs:number;additionalTrimDb:number}|null>(null);
  const headroomFixRef=useRef<HTMLElement|null>(null);
  const [mixBytes,setMixBytes]=useState<number|null>(null);
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
  const [widthTargets,setWidthTargets]=useState<SavedWidthTarget[]>([]);
  const [eqTargets,setEqTargets]=useState<SavedEqTarget[]>([]);
  const [dynamicsTargets,setDynamicsTargets]=useState<{section_id:string;source_key:string;kind:"comp"|"duck"|"deess";threshold_db:number;ratio:number;depth_db:number;frequency?:number;q?:number;max_reduction_db?:number;transition_seconds:number;curve:"smooth"|"linear"}[]>([]);
  const [spaceTargets,setSpaceTargets]=useState<{section_id:string;source_key:string;amount:number;transition_seconds:number;curve:"linear"|"smooth"}[]>([]);
  const [panLoaded,setPanLoaded]=useState(false);
  const [ending,setEnding]=useState<{fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"}>({
    fade_seconds:0,tail_seconds:0,curve:"smooth"
  });
  const [openTools,setOpenTools]=useState<WorkbenchTool[]>([]);
  const [sectionEffect,setSectionEffect]=useState<"script"|"pan"|"reverb"|"width"|"space"|"eq"|"deess">("script");
  const [sectionEditId,setSectionEditId]=useState("");
  const [correction,setCorrection]=useState<CorrectionDraft|null>(null);
  const [correctionSaving,setCorrectionSaving]=useState(false);
  const [meters,setMeters]=useState<{filename:string;compressionDb:number;duckDb:number;deessDb:number}[]>([]);
  const [correctionError,setCorrectionError]=useState("");
  const [scriptFocus,setScriptFocus]=useState<SongSection|null>(null);
  const [scriptRevision,setScriptRevision]=useState(0);
  const [externalSections,setExternalSections]=useState<SongSection[]|undefined>(undefined);
  const [loopEnabled,setLoopEnabled]=useState(false);
  const [loopIn,setLoopIn]=useState<number|null>(null);
  const [loopOut,setLoopOut]=useState<number|null>(null);
  const audio=useRef<SharedClockAudition|null>(null);
  const [audioLoad,setAudioLoad]=useState<{ready:number;total:number}|null>(null);
  const [audioReady,setAudioReady]=useState(false);
  useEffect(()=>{
    if(!audioReady)return;
    const timer=window.setInterval(()=>{
      if(document.visibilityState!=="visible")return;
      setMeters(audio.current?.dynamicsMeters||[]);
    },130);
    return ()=>window.clearInterval(timer);
  },[audioReady]);
  const monitorRef=useRef(monitorVolume);
  monitorRef.current=monitorVolume;
  const playRef = useRef(false);
  const transportGeneration=useRef(0);
  const seekRef = useRef(0);
  const stemsRef = useRef(stems);
  stemsRef.current = stems;
  const anySolo = stems.some(s => s.solo);
  useEffect(()=>{audio.current?.setEffectBypass(correction?{...bypassed,compression:false,ducking:false}:bypassed);},[bypassed,audioReady,correction]);
  useEffect(()=>{if(headroomIssue)headroomFixRef.current?.scrollIntoView({behavior:"smooth",block:"nearest"});},[headroomIssue]);
  useEffect(()=>{audio.current?.setOutputTrimDb(masterTrimDb+(correction?.kind==="trim"&&correction.proposed?correction.trimDelta:0));},[masterTrimDb,correction,audioReady]);
  const visibleSeconds=duration>0?duration/zoom:0;
  const viewStart=duration>0?(duration-visibleSeconds)*viewportOffset:0;
  const viewEnd=duration>0?viewStart+visibleSeconds:0;
  // Native wheel scroll remains page scrolling everywhere, including the waveform.
  // Zoom uses the visible Tools control and its slider; no wheel interception.

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
    setWidthTargets([]);
    setSpaceTargets([]);
    setEqTargets([]);
    setDynamicsTargets([]);
    setEnding({fade_seconds:0,tail_seconds:0,curve:"smooth"});
    void fetch("/api/projects/"+jobId+"/sections/export")
      .then(async response=>{
        if(!response.ok)throw Error("Could not load pan automation");
        return response.json() as Promise<{reverb_targets:typeof reverbTargets;width_targets:SavedWidthTarget[];space_targets:typeof spaceTargets;eq_targets:SavedEqTarget[];dynamics_targets:typeof dynamicsTargets;ending:typeof ending}>;
      })
      .then(async data=>{
        const panResponse=await fetch("/api/projects/"+jobId+"/section-pan");
        if(!panResponse.ok)throw Error("Could not load pan automation");
        const panData=await panResponse.json() as {targets:SavedPanTarget[]};
        if(!cancelled){setPanTargets(panData.targets||[]);setReverbTargets(data.reverb_targets||[]);setWidthTargets(data.width_targets||[]);setSpaceTargets(data.space_targets||[]);setEqTargets(data.eq_targets||[]);setDynamicsTargets(data.dynamics_targets||[]);setEnding(data.ending||{fade_seconds:0,tail_seconds:0,curve:"smooth"});setPanLoaded(true);}
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
      engine.setOutputTrimDb(masterTrimDb);
      engine.setEffectBypass(bypassed);
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
    const byFile:Record<string,{pan?:ReturnType<typeof compileSectionAutomation>;reverb?:ReturnType<typeof compileSectionAutomation>;width?:ReturnType<typeof compileSectionAutomation>;space?:ReturnType<typeof compileSectionAutomation>;eq?:Partial<Record<1|2|3,{frequency:ReturnType<typeof compileSectionAutomation>;q:ReturnType<typeof compileSectionAutomation>;gain:ReturnType<typeof compileSectionAutomation>}>>;dynamics?:{compressor?:{threshold:ReturnType<typeof compileSectionAutomation>;ratio:ReturnType<typeof compileSectionAutomation>};duck?:{depthDb:ReturnType<typeof compileSectionAutomation>;keyFilename:string};deess?:{frequency:ReturnType<typeof compileSectionAutomation>;q:ReturnType<typeof compileSectionAutomation>;threshold:ReturnType<typeof compileSectionAutomation>;maxReduction:ReturnType<typeof compileSectionAutomation>}}}>={};
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
    for(const filename of files){
      const desired=widthTargets.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.width/100,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),width:compileSectionAutomation(desired,1,{min:0,max:1.5})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid width automation");return;}
    }
    for(const filename of files){
      const desired=spaceTargets.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.amount/100,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),space:compileSectionAutomation(desired,0,{min:0,max:.4})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid spatial reflections");return;}
    }
    for(const filename of files){
      for(const band of [1,2,3] as const){
        const desired=eqTargets.filter(item=>item.source_key===filename&&item.band===band)
          .flatMap(item=>{
            const section=sectionById.get(item.section_id);
            return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
              frequency:item.frequency,q:item.q,gain:item.gain_db,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
          });
        if(!desired.length)continue;
        try{
          const compile=(key:"frequency"|"q"|"gain",start:number,min:number,max:number)=>
            compileSectionAutomation(desired.map(item=>({sectionId:item.sectionId,start:item.start,end:item.end,
              value:item[key],transitionSeconds:item.transitionSeconds,curve:item.curve})),start,{min,max});
          const eq={...(byFile[filename]?.eq||{}),[band]:{
            frequency:compile("frequency",1000,30,16000),
            q:compile("q",1,.3,12),
            gain:compile("gain",0,-12,12)
          }};
          byFile[filename]={...(byFile[filename]||{}),eq};
        }catch(e){setError(e instanceof Error?e.message:"Invalid EQ automation");return;}
      }
    }
    const vocal=files.find(name=>name.includes("(Vocals)"));
    const staged=correction&&correction.proposed&&correction.kind!=="trim"?
      [...dynamicsTargets.filter(item=>!(item.section_id===correction.sectionId&&
        item.source_key===correction.file&&item.kind===correction.kind)),{
        section_id:correction.sectionId,source_key:correction.file,kind:correction.kind,
        threshold_db:correction.threshold,
        ratio:Math.min(4,1+(correction.ratio-1)*correction.auditionBoost),
        depth_db:Math.min(12,correction.depth*correction.auditionBoost),
        frequency:correction.frequency,q:correction.q,
        max_reduction_db:Math.min(12,correction.maxReduction*correction.auditionBoost),
        transition_seconds:correction.transition,curve:"smooth" as const
      }]:dynamicsTargets;
    for(const filename of files){
      const settings=staged.filter(item=>item.source_key===filename);
      if(!settings.length)continue;
      const compile=(kind:"comp"|"duck"|"deess",field:"threshold_db"|"ratio"|"depth_db"|"frequency"|"q"|"max_reduction_db",initial:number,min:number,max:number)=>{
        const desired=settings.filter(item=>item.kind===kind).flatMap(item=>{
          const section=sectionById.get(item.section_id);
          return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
            value:item[field]??initial,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
        });
        return compileSectionAutomation(desired,initial,{min,max});
      };
      try{
        const hasComp=settings.some(item=>item.kind==="comp");
        const hasDuck=settings.some(item=>item.kind==="duck");
        const hasDeess=settings.some(item=>item.kind==="deess");
        const dynamics={
          ...(hasComp?{compressor:{
            threshold:compile("comp","threshold_db",-18,-60,0),
            ratio:compile("comp","ratio",1,1,4)
          }}:{}),
          ...(hasDuck&&vocal?{duck:{
            keyFilename:vocal,depthDb:compile("duck","depth_db",0,0,12).map(point=>({...point,value:-point.value}))
          }}:{}),
          ...(hasDeess?{deess:{
            frequency:compile("deess","frequency",6500,3000,11000),
            q:compile("deess","q",2,.4,8),
            threshold:compile("deess","threshold_db",-32,-70,-10),
            maxReduction:compile("deess","max_reduction_db",0,0,12)
          }}:{})
        };
        byFile[filename]={...(byFile[filename]||{}),dynamics};
      }catch(e){setError(e instanceof Error?e.message:"Invalid dynamics automation");return;}
    }
    engine.setAutomation(byFile,Boolean(correction));
    engine.setEnding(ending);
    setDuration(engine.duration);
  },[audioReady,panLoaded,panTargets,reverbTargets,widthTargets,spaceTargets,eqTargets,dynamicsTargets,ending,timelineSections,files,correction]);

  // Findings describe a specific processed mix; edits invalidate those results.
  useEffect(()=>{
    analysisRevision.current++;
    setCleanupScanned(false);setCleanupFindings([]);
  },[stems,masterTrimDb,panTargets,reverbTargets,widthTargets,spaceTargets,eqTargets,dynamicsTargets,ending,channels]);

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

  function loopAround(start:number,end:number){
    const from=Math.max(0,Math.min(start,duration));
    const to=Math.max(from+.1,Math.min(end,duration));
    setLoopIn(from);setLoopOut(to);setLoopEnabled(true);
    seek(from);
    if(!playRef.current)void togglePlayback();
  }

  function tryCorrection(finding:AudioFinding){
    const section=timelineSections.find(item=>finding.timeSeconds>=item.start_seconds&&finding.timeSeconds<item.end_seconds);
    const currentIndex=timelineSections.findIndex(item=>item.id===section?.id);
    const relevant=dynamicsTargets.filter(item=>{
      const i=timelineSections.findIndex(value=>value.id===item.section_id);
      return i>=0&&i<=currentIndex&&
        (item.kind==="duck"&&item.depth_db>0||item.kind==="comp"&&item.ratio>1);
    }).sort((a,b)=>timelineSections.findIndex(item=>item.id===b.section_id)-
                    timelineSections.findIndex(item=>item.id===a.section_id));
    const preferred=relevant.find(item=>item.kind==="duck"&&
      finding.sources?.some(name=>item.source_key.includes("("+name+")")))||
      relevant.find(item=>item.kind==="comp"&&
        finding.sources?.some(name=>item.source_key.includes("("+name+")")))||
      relevant.find(item=>item.kind==="duck")||relevant[0];
    const suggestedStem=preferred?.source_key||
      files.find(f=>finding.sources?.some(name=>f.includes("("+name+")")))||
      files.find(f=>f.includes("(Drums)"))||files[0];
    const kind=finding.kind==="headroom"?"trim":finding.kind==="sibilance"?"deess":(preferred?.kind==="deess"?"duck":preferred?.kind||"duck");
    const deessStem=kind==="deess"?files.find(f=>f.includes("(Vocals)")):undefined;
    const file=(kind==="duck"&&suggestedStem?.includes("(Vocals)"))?
      files.find(f=>!f.includes("(Vocals)"))||suggestedStem:(deessStem||suggestedStem);
    const peakMatch=finding.detail.match(/(-?[0-9]+(?:\.[0-9]+)?) dBFS/);
    const peak=peakMatch?Number(peakMatch[1]):0;
    setCorrectionError("");
    setCorrection({
      finding,sectionId:section?.id||"",file,kind,
      threshold:kind==="deess"?-40:(preferred?.threshold_db??-18),ratio:1,depth:0,transition:1.5,
      frequency:6500,q:2,maxReduction:4,auditionBoost:1,
      trimDelta:-Math.max(0,Math.min(12,Math.round((peak+1)*10)/10)),proposed:false
    });
    loopAround(finding.timeSeconds-1,finding.timeSeconds+2);
  }

  async function acceptCorrection(){
    const trial=correction;
    if(!trial)return;
    setCorrectionError("");
    if(trial.kind==="trim"){
      setMasterTrimDb(Math.max(-60,masterTrimDb+trial.trimDelta));
      setCorrection(null);setMixUrl(null);
      return;
    }
    const index=timelineSections.findIndex(section=>section.id===trial.sectionId);
    if(index<0){setCorrectionError("Align a saved section before accepting a dynamics correction.");return;}
    const alias=trial.file.match(/\(([^)]+)\)/)?.[1];
    if(!alias){setCorrectionError("Track has no script-safe stem alias.");return;}
    const directive=trial.kind==="comp"?
      `${alias}.comp:${trial.threshold},${trial.ratio}@${trial.transition}s:smooth`:
      trial.kind==="deess"?
      `${alias}.deess:${trial.frequency},${trial.q},${trial.threshold},${trial.maxReduction}@${trial.transition}s:smooth`:
      `${alias}.duck:${trial.depth}@${trial.transition}s:smooth`;
    setCorrectionSaving(true);
    try{
      const response=await fetch("/api/projects/"+jobId+"/sections/export",{cache:"no-store"});
      const saved=await response.json() as {content?:string;detail?:string};
      if(!response.ok||!saved.content)throw Error(saved.detail||"Could not load saved section script");
      const lines=saved.content.split("\n");
      const sectionHeaders=lines.map((line,i)=>/^\[[^\n]+\]$/.test(line.trim())?i:-1).filter(i=>i>=0);
      const header=sectionHeaders[index];
      if(header===undefined)throw Error("Saved section sequence differs from the timeline. Reload the song and retry.");
      const nextHeader=sectionHeaders[index+1]??lines.length;
      let blockIndex=-1;
      for(let i=header+1;i<nextHeader;i++)if(/^\{.*\}$/.test(lines[i].trim())){blockIndex=i;break;}
      if(blockIndex<0){lines.splice(header+1,0,"{"+directive+"}");}
      else{
        const existing=lines[blockIndex].trim().slice(1,-1).trim().split(/\s+/).filter(Boolean);
        const without=existing.filter(token=>!token.startsWith(alias+"."+trial.kind+":"));
        lines[blockIndex]="{"+[...without,directive].join(" ")+"}";
      }
      const result=await fetch("/api/projects/"+jobId+"/sections/import",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content:lines.join("\n"),mode:"replace"})
      });
      const data=await result.json() as {detail?:string;sections?:SongSection[];pan_targets?:SavedPanTarget[];
        reverb_targets?:SavedReverbTarget[];width_targets?:SavedWidthTarget[];space_targets?:typeof spaceTargets;
        eq_targets?:SavedEqTarget[];dynamics_targets?:typeof dynamicsTargets;ending?:typeof ending};
      if(!result.ok||!data.sections)throw Error(data.detail||"Could not save dynamics correction");
      setCorrection(null);
      setExternalSections(data.sections);setTimelineSections(data.sections);
      setPanTargets(data.pan_targets||[]);setReverbTargets(data.reverb_targets||[]);
      setWidthTargets(data.width_targets||[]);setSpaceTargets(data.space_targets||[]);
      setEqTargets(data.eq_targets||[]);setDynamicsTargets(data.dynamics_targets||[]);
      if(data.ending)setEnding(data.ending);
      setScriptRevision(v=>v+1);setMixUrl(null);
      setNotice("Accepted "+trial.kind+" correction in section script; export uses the saved mix.");
    }catch(error){setCorrectionError(error instanceof Error?error.message:"Could not accept correction");}
    finally{setCorrectionSaving(false);}
  }

  async function analyzeMix(){
    const engine=audio.current;
    if(!engine?.ready){setCleanupError("Wait for synchronized audio to load before analyzing.");return;}
    const revision=analysisRevision.current;
    setAnalyzing(true);setCleanupError("");setCleanupScanned(false);setCleanupFindings([]);
    try{
      const results=await engine.analyzeMix();
      if(analysisRevision.current!==revision){
        setCleanupError("The mix changed during analysis. Re-analyze the new settings.");
        return;
      }
      setCleanupFindings(results);
      setCleanupScanned(true);
    }catch(e){
      setCleanupError(e instanceof Error?e.message:"Sound analysis failed");
    }finally{setAnalyzing(false);}
  }

  async function exportMix(overrideTrimDb?:number) {
    const engine=audio.current;
    if(correction){setError("Accept or discard the correction trial before exporting the saved mix.");return;}
    if(!engine?.ready){setError("Wait for synchronized audio to load before exporting.");return;}
    stop();
    setExporting(true);
    setMixUrl(null);
    setMixBytes(null);
    setError("");
    setNotice("");
    setHeadroomIssue(null);
    setCleanupScanned(false);
    setCleanupFindings([]);
    try{
      if(overrideTrimDb!==undefined){
        engine.setOutputTrimDb(overrideTrimDb);
        setMasterTrimDb(overrideTrimDb);
      }
      const blob=await engine.renderWav24();
      setCleanupFindings(engine.cleanupFindings);
      setCleanupScanned(true);
      if(renderedUrl.current)URL.revokeObjectURL(renderedUrl.current);
      renderedUrl.current=URL.createObjectURL(blob);
      setMixUrl(renderedUrl.current);
      setMixBytes(blob.size);
      setNotice("Mix rendered without clipping. Use Download WAV below to save it to your browser's configured download location.");
    }catch(e){
      if(e instanceof MixHeadroomError){
        setHeadroomIssue({peakDbfs:e.measuredPeakDbfs,additionalTrimDb:e.recommendedAdditionalTrimDb});
      }else{
        setError(e instanceof Error?e.message:"Processed WAV export failed");
      }
    }finally{
      setExporting(false);
    }
  }

  function applyHeadroomFix(){
    if(!headroomIssue||exporting)return;
    const corrected=Math.round((masterTrimDb+headroomIssue.additionalTrimDb)*10)/10;
    if(corrected< -60){
      setError("Required headroom exceeds the -60 dB master trim range. Inspect individual tracks and effects.");
      return;
    }
    void exportMix(corrected);
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
            onSectionDoubleClick={section=>{setScriptFocus(section);setSectionEditId(section.id);setSectionEffect("pan");setOpenTools(items=>[...items.filter(x=>x!=="sectionEdit"),"sectionEdit"]);}}/>
          {cleanupScanned&&cleanupFindings.length>0&&viewEnd>viewStart&&
            <div className="song-cleanup-marker-row" aria-label="Sound cleanup timeline markers">
              <span className="song-cleanup-marker-label">QC · {cleanupFindings.length}</span>
              <div className="song-cleanup-marker-track">
                {cleanupFindings.filter(item=>item.timeSeconds>=viewStart&&item.timeSeconds<=viewEnd)
                  .map((item,index)=><button type="button"
                    key={item.kind+":"+item.timeSeconds+":"+index}
                    className={"song-cleanup-marker"+(item.severity==="warning"?" is-warning":"")}
                    style={{left:`${100*(item.timeSeconds-viewStart)/(viewEnd-viewStart)}%`}}
                    aria-label={timecode(item.timeSeconds)+" "+item.label}
                    title={timecode(item.timeSeconds)+" · "+item.label}
                    onClick={()=>seek(item.timeSeconds)}/>)}
              </div>
            </div>}
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
      {stems.map(s => <div className={"mixer-track"+(trackLabels?.[s.filename]?" mixer-track--named":"")} key={s.filename}>
        <strong className={"stem-icon-name"+(trackLabels?.[s.filename]?" stem-icon-name--named":"")}
          title={s.name+" · script: "+(trackAliases?.[s.filename]||labelOf(s.filename))}
          aria-label={s.name}><AudioIcon kind={trackAliases?.[s.filename]||labelOf(s.filename)} size={32}/>
          {trackLabels?.[s.filename]?<span className="mixer-stem-names"><span className="mixer-stem-name">{s.name}</span>
            <small>{trackAliases?.[s.filename]||labelOf(s.filename)}</small></span>:<span className="sr-only">{s.name}</span>}
        </strong>
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
      <aside className="song-tool-rail" aria-label="Production tools">
        {TOOL_ITEMS.map(item=><button type="button" key={item.id}
          className="song-tool-icon" title={item.label} aria-label={"Open "+item.label+" tool"}
          aria-pressed={openTools.includes(item.id)}
          onClick={()=>{
            if(item.id==="sectionEdit")setSectionEditId(current=>current||timelineSections[0]?.id||"");
            if(item.id==="cleanup"&&openTools.includes("cleanup"))setCorrection(null);
            setOpenTools(existing=>existing.includes(item.id)?
              existing.filter(x=>x!==item.id):[...existing,item.id]);
          }}>
          <span aria-hidden="true">{item.icon}</span>
        </button>)}
      </aside>
      {openTools.map((tool,order)=><ToolWindow key={tool}
        name={TOOL_ITEMS.find(item=>item.id===tool)?.label||"Tool"} order={order}
        onFocus={()=>setOpenTools(current=>current[current.length-1]===tool?current:
          [...current.filter(item=>item!==tool),tool])}
        onClose={()=>{
          setOpenTools(items=>items.filter(item=>item!==tool));
          if(tool==="cleanup")setCorrection(null);
        }}>
        {tool==="sectionEdit"&&<>
          <div className="song-section-edit-context">
            <label>Section
              <select aria-label="Selected edit section" value={timelineSections.some(x=>x.id===sectionEditId)?sectionEditId:timelineSections[0]?.id||""}
                onChange={e=>{setSectionEditId(e.target.value);setScriptFocus(timelineSections.find(x=>x.id===e.target.value)||null);}}>
                {timelineSections.map(section=><option key={section.id} value={section.id}>
                  {section.kind}{section.number?" "+section.number:""} · {timecode(section.start_seconds)}
                </option>)}
              </select>
            </label>
            <div className="song-section-effect-tabs" role="tablist" aria-label="Section edit effect">
              {(["script","pan","reverb","width","space","eq","deess"] as const).map(effect=>
                <button key={effect} type="button" role="tab" aria-selected={sectionEffect===effect}
                  onClick={()=>setSectionEffect(effect)}>
                  {effect==="script"?"Script":effect==="width"?"Width":effect==="space"?"Reflections":effect==="eq"?"EQ":effect==="deess"?"De-ess":effect[0].toUpperCase()+effect.slice(1)}
                </button>)}
            </div>
          </div>
        </>}

        {tool==="sectionEdit"&&sectionEffect==="script"&&<>
        <SectionsTool jobId={jobId} open={tool==="sectionEdit"&&sectionEffect==="script"}
          onClose={()=>{setOpenTools(items=>items.filter(x=>x!=="sectionEdit"));}} focused={scriptFocus} revision={scriptRevision}
          onApplied={(items,targets,reverb,width,space,eq,dynamics,finish)=>{
            setPanTargets(targets);
            setReverbTargets(reverb);
            setWidthTargets(width);
            setSpaceTargets(space);
            setEqTargets(eq);
            setDynamicsTargets(dynamics);
            setMixUrl(null);
            setEnding(finish);
            setExternalSections(items);setTimelineSections(items);
            setZoom(1);setViewportOffset(0);setScriptRevision(v=>v+1);
          }}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="pan"&&<>
        <SectionPanTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          targets={panTargets} onChange={items=>{setPanTargets(items);setMixUrl(null);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="reverb"&&<>
        <SectionReverbTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          targets={reverbTargets} onChange={items=>{setReverbTargets(items);setMixUrl(null);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="width"&&<>
        <SectionWidthTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          targets={widthTargets} onChange={items=>{setWidthTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="space"&&<>
        <SectionSpaceTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          targets={spaceTargets} onChange={items=>{setSpaceTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="eq"&&<>
        <SectionEqTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          targets={eqTargets} onChange={items=>{setEqTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="deess"&&<>
          <SectionDeEssTool jobId={jobId} sections={timelineSections} files={files}
            initialSectionId={sectionEditId} targets={dynamicsTargets}
            onSaved={data=>{
              setExternalSections(data.sections);setTimelineSections(data.sections);
              setPanTargets(data.pan_targets);setReverbTargets(data.reverb_targets);
              setWidthTargets(data.width_targets);setSpaceTargets(data.space_targets);
              setEqTargets(data.eq_targets);setDynamicsTargets(data.dynamics_targets);
              setEnding(data.ending);setMixUrl(null);setScriptRevision(v=>v+1);
            }}/>
        </>}
        {tool==="cleanup"&&<>
        <CleanupReview findings={cleanupFindings} scanned={cleanupScanned}
          analyzing={analyzing} error={cleanupError} ready={audioReady} busy={exporting||Boolean(correction)}
          onAnalyze={()=>{void analyzeMix();}} onSeek={seek} onTryCorrection={tryCorrection}
          onLoop={(start,end)=>{
            setLoopIn(Math.min(start,duration));
            setLoopOut(Math.min(duration,end));
            setLoopEnabled(true);
            seek(Math.max(0,Math.min(start,duration)));
            if(!playRef.current)void togglePlayback();
          }}/>

        </>}
        {tool==="cleanup"&&correction&&<>
          <CorrectionWorkbench draft={correction} files={files} trimBase={masterTrimDb}
            reduction={meters.find(item=>item.filename===correction.file)}
            busy={correctionSaving} onChange={setCorrection} onAccept={()=>{void acceptCorrection();}}
            onCancel={()=>{setCorrection(null);setCorrectionError("");}}/>
          {correctionError&&<p role="alert" className="song-cleanup-error">{correctionError}</p>}
        </>}
        {tool==="ab"&&<>
        <details className="production-tool-detail" aria-label="A/B audition" open>
          <summary>◉ A/B comparison &amp; bypass</summary>
          <div className="timeline-loop-controls">
            <p>Audition the same stems and levels with production processing enabled or bypassed. WAV export always uses the processed mix.</p>
            <div className="production-tool-actions">
              <button type="button" aria-pressed={EFFECT_KEYS.every(k=>!bypassed[k])}
                onClick={()=>setBypassed({...DEFAULT_BYPASS})}>A · Processed</button>
              <button type="button" aria-pressed={EFFECT_KEYS.every(k=>bypassed[k])}
                onClick={()=>setBypassed({pan:true,width:true,space:true,reverb:true,eq:true,compression:true,ducking:true,ending:true})}>B · Original</button>
            </div>
            {EFFECT_KEYS.map(key=><label key={key}>
              <input type="checkbox" checked={bypassed[key]}
                onChange={e=>setBypassed(v=>({...v,[key]:e.target.checked}))}/>
              Bypass {key==="space"?"spatial reflections":key}
            </label>)}
            <div className="song-dynamics-meter" aria-label="Live per-stem gain reduction">
              <strong>Live gain reduction</strong>
              {meters.filter(item=>item.compressionDb>.05||item.duckDb>.05||item.deessDb>.05)
                .sort((a,b)=>(b.compressionDb+b.duckDb+b.deessDb)-(a.compressionDb+a.duckDb+a.deessDb))
                .slice(0,6).map(item=><div key={item.filename} className="song-dynamics-meter-row">
                  <span title={item.filename}>{item.filename.match(/\(([^)]+)\)/)?.[1]||item.filename}</span>
                  <meter min="0" max="12" value={Math.min(12,item.compressionDb+item.duckDb+item.deessDb)}/>
                  <output>{(item.compressionDb+item.duckDb+item.deessDb).toFixed(1)} dB</output>
                </div>)}
              {!meters.some(item=>item.compressionDb>.05||item.duckDb>.05||item.deessDb>.05)&&
                <small>No significant gain reduction at the current playback position.</small>}
              <small>Actual WebAudio compressor reduction plus scheduled duck/de-ess attenuation. Values are approximate and may update while playing.</small>
            </div>
            <small>Audition-only: individual stem balance, saved production instructions, and WAV render stay intact. Original mode retains active split-channel routing and master output trim.</small>
          </div>
        </details>

        </>}
        {tool==="ending"&&<>
        <EndingTool jobId={jobId} sections={timelineSections} ending={ending}
          onChange={value=>{setEnding(value);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}
        {tool==="zoom"&&<>
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

        </>}
        {tool==="loop"&&<>
        <details className="production-tool-detail" open><summary>⇥ Region loop</summary>
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

        </>}
        {tool==="channels"&&<>
          <ChannelSplitter jobId={jobId} files={files} onMissingFfmpeg={onMissingFfmpeg}
            onCompleted={()=>{void refreshChannels();}} />
        </>}
        {tool==="download"&&<div className="song-tool-handoff">
          <button type="button" onClick={()=>setDawOpen(true)}>Download tracks…</button>
        </div>}

      </ToolWindow>)}
      <div className="song-production-exports">
    <div className="mix-footer">
      <div className="mix-actions">
        <IconButton icon="⇩" label={exporting ? "Rendering mix WAV" : "Export mix WAV"}
          disabled={exporting||Boolean(correction)} onClick={()=>{void exportMix();}}/>
        {mixUrl && <a className="mix-download" href={mixUrl} download="Song Harbor Mix.wav" title="Download mix WAV">Download WAV</a>}
      </div>
      {exporting ? <Status tone="info">Export in progress</Status> : mixUrl ? <Status tone="success">Mix ready to download</Status> : null}
      <div className="mix-master-headroom">
        <label htmlFor="song-master-trim">Master output trim</label>
        <input id="song-master-trim" aria-label="Master output trim decibels"
          type="range" min="-60" max="0" step="0.1" value={masterTrimDb}
          onChange={e=>{setMasterTrimDb(Number(e.target.value));setMixUrl(null);setMixBytes(null);setHeadroomIssue(null);}}/>
        <output htmlFor="song-master-trim">{masterTrimDb.toFixed(1)} dB</output>
        <small>Output only. Stem balances, section automation, and source files are unchanged. The same trim is used in playback and WAV export.</small>
      </div>
      {headroomIssue&&<section ref={headroomFixRef} className="mix-headroom-fix" role="alert" aria-label="Resolve mix clipping">
        <strong>Mix needs output headroom</strong>
        <p>The full mix peaks at {headroomIssue.peakDbfs.toFixed(1)} dBFS before the output trim. Export has not created a WAV yet.</p>
        <p>Recommended: reduce the master output by {Math.abs(headroomIssue.additionalTrimDb).toFixed(1)} dB more for a -1 dBFS peak ceiling. This preserves the relative stem balance and dynamics without a limiter.</p>
        <button type="button" disabled={exporting||masterTrimDb+headroomIssue.additionalTrimDb< -60}
          onClick={applyHeadroomFix}>Apply safe output trim and re-render</button>
        <button type="button" disabled={exporting} onClick={()=>setHeadroomIssue(null)}>Review master trim manually</button>
      </section>}
      {mixUrl&&<small>24-bit stereo WAV · {mixBytes===null?"":(mixBytes/1048576).toFixed(1)+" MB"} · Destination: your browser's Downloads setting. Click Download WAV to save; browser downloads cannot reveal their actual destination to Song Harbor.</small>}
    </div>

      </div>
    </div>
    {dawOpen && <DawHandoff jobId={jobId} saveProject={saveProject} onClose={() => setDawOpen(false)} />}
    {notice && <p role="status" className="song-save-notice">{notice}</p>}
    {error && <p role="alert" className="error-message">{error}</p>}

  </section>;
}
