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
import { SectionSpaceTool,type SavedSpaceTarget } from "./SectionSpaceTool";
import { SectionEqTool,type SavedEqTarget } from "./SectionEqTool";
import {SectionDeEssTool} from "./SectionDeEssTool";
import { EndingTool } from "./EndingTool";
import { compileSectionAutomation, valueAt } from "./SectionAutomation";
import { SharedClockAudition, MixHeadroomError, type AuditionSource,type DeclickRecipe } from "./SharedClockAudition";
import {DeclickWorkbench,type DeclickDraft} from "./DeclickWorkbench";
import type {AudioFinding} from "./AudioCleanupAnalyzer";
import type {SectionInsight} from "./SectionInsights.ts";
import {CleanupReview} from "./CleanupReview";
import {AccompanimentGenerator} from "./AccompanimentGenerator";
import {CorrectionWorkbench,type CorrectionDraft} from "./CorrectionWorkbench";
import {ToolWindow,TOOL_ITEMS,type WorkbenchTool} from "./WorkbenchTools";
import type { SongSection } from "./SectionEditor";

type SectionPreview =
  |{kind:"pan";targets:SavedPanTarget[]}
  |{kind:"reverb";targets:SavedReverbTarget[]}
  |{kind:"width";targets:SavedWidthTarget[]}
  |{kind:"space";targets:SavedSpaceTarget[]}
  |{kind:"eq";targets:SavedEqTarget[]}
  |{kind:"deess";targets:typeof EMPTY_DYNAMICS_TARGETS};
type DynamicsTarget={section_id:string;source_key:string;kind:"comp"|"duck"|"deess";threshold_db:number;ratio:number;depth_db:number;frequency?:number;q?:number;max_reduction_db?:number;transition_seconds:number;curve:"smooth"|"linear"};
const EMPTY_DYNAMICS_TARGETS:DynamicsTarget[]=[];
type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
type ChildSet = {active:boolean;export:string;tracks:{left:{url:string;file:string};right:{url:string;file:string}}};
type ChannelSets = Record<string,ChildSet>;
type EffectKey="pan"|"width"|"space"|"reverb"|"ending"|"eq"|"compression"|"ducking"|"deess";
const EFFECT_KEYS:EffectKey[]=["pan","width","space","reverb","eq","compression","ducking","deess","ending"];
const DEFAULT_BYPASS:Record<EffectKey,boolean>={pan:false,width:false,space:false,reverb:false,eq:false,compression:false,ducking:false,deess:false,ending:false};
export type SavedStem = {filename: string; gain: number; mute: boolean; solo: boolean};
export type TrackIdentity = {track_id:string;working_filename:string;stem_alias:string;display_name:string;imported?:boolean;start_seconds?:number;duration_seconds?:number};
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

export function StemMixer({ jobId, files, expectedDuration, onMissingFfmpeg, savedStems, trackLabels, trackAliases, trackDetails, initialSections, initialTitle, onSaved, onTrackRenamed, onTrackAdded }: {
  jobId: string; files: string[]; expectedDuration?: number;
  onMissingFfmpeg?: (retry: () => void) => void;
  savedStems?: SavedStem[];
  trackLabels?: Record<string,string>;
  trackAliases?: Record<string,string>;
  trackDetails?: TrackIdentity[];
  initialSections?: SongSection[];
  initialTitle?: string;
  onSaved?: () => void;
  onTrackRenamed?: (project:unknown)=>void;
  onTrackAdded?: (project:unknown,job:unknown)=>void;
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
  const [trackIdentities,setTrackIdentities]=useState<TrackIdentity[]>(trackDetails||[]);
  const [renamingTrack,setRenamingTrack]=useState<string|null>(null);
  const [addingTrack,setAddingTrack]=useState(false);
  const [pendingFile,setPendingFile]=useState<File|null>(null);
  const [newDisplay,setNewDisplay]=useState("");
  const [newAlias,setNewAlias]=useState("");
  const [placement,setPlacement]=useState("start");
  const [customStart,setCustomStart]=useState("0");
  function chooseTrack(file:File|undefined){
    if(!file)return;
    const base=file.name.replace(/\.[^.]+$/,"");
    setPendingFile(file);setNewDisplay(base);
    setNewAlias(base.replace(/[^a-zA-Z0-9_-]/g,"_").replace(/^[^a-zA-Z]+/,"").slice(0,32)||"NewStem");
    setPlacement("start");setCustomStart("0");
  }
  async function addTrack(){
    const file=pendingFile;
    if(!file||addingTrack)return;
    if(openTools.includes("songText")){
      setError("Apply and close Whole Song Section Text before adding a stem.");
      return;
    }
    setAddingTrack(true);setError("");
    try{
      if(!await saveProject())return;
      stop();
      const form=new FormData();
      form.append("file",file);form.append("stem_alias",newAlias);form.append("display_name",newDisplay);
      if(placement.startsWith("section:"))form.append("section_id",placement.slice(8));
      else form.append("start_seconds",placement==="custom"?customStart:"0");
      const response=await fetch("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||"New stem import failed");
      setPendingFile(null);
      setNotice("New stem added at its selected timeline position.");
      onTrackAdded?.(data.project,data.job);
    }catch(e){setError(e instanceof Error?e.message:"Could not add stem");}
    finally{setAddingTrack(false);}
  }
  useEffect(()=>{
    let cancelled=false;
    void fetch("/api/projects/"+jobId+"/tracks",{cache:"no-store"})
      .then(async r=>{const data=await r.json();if(!r.ok)throw Error(data.detail||"Track identities unavailable");return data;})
      .then(data=>{if(!cancelled)setTrackIdentities(data.tracks||[]);})
      .catch(()=>{if(!cancelled)setTrackIdentities([]);});
    return ()=>{cancelled=true;};
  },[jobId]);
  async function renameTrack(filename:string){
    const track=trackIdentities.find(t=>t.working_filename===filename);
    if(!track){setError("This track has no saved identity yet. Reopen the song and retry.");return;}
    if(openTools.includes("songText")){
      setError("Close Whole Song Section Text before renaming. Apply any unsaved script changes first.");
      return;
    }
    const display=window.prompt("Display name for this track:",track.display_name);
    if(display===null)return;
    const alias=window.prompt("Script alias (letters/numbers/_/- only):",track.stem_alias);
    if(alias===null)return;
    setRenamingTrack(filename);setError("");
    try{
      // The mixer remounts after a rename: persist faders first rather than
      // accidentally reverting unsaved gain/mute/solo settings.
      if(!await saveProject())return;
      const response=await fetch("/api/projects/"+jobId+"/tracks/rename",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({track_id:track.track_id,expected_alias:track.stem_alias,display_name:display,stem_alias:alias})
      });
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||"Could not rename track");
      setNotice("Track renamed. Saved section scripts were migrated and verified.");
      onTrackRenamed?.(data.project);
    }catch(err){setError(err instanceof Error?err.message:String(err));}
    finally{setRenamingTrack(null);}
  }
  async function repositionTrack(track:TrackIdentity){
    const choices=timelineSections.map((s,i)=>`${i+1}. ${s.kind}${s.number===null?"":" "+s.number} — ${s.start_seconds.toFixed(3)}s`).join("\n");
    const answer=window.prompt("New start time in seconds, or enter a section number:\n"+choices,String(track.start_seconds||0));
    if(answer===null)return;
    const index=/^\d+$/.test(answer.trim())?Number(answer.trim())-1:-1;
    const start=index>=0&&timelineSections[index]?timelineSections[index].start_seconds:Number(answer);
    if(!Number.isFinite(start)||start<0){setError("Enter a non-negative timestamp or a listed section number.");return;}
    stop();setRenamingTrack(track.working_filename);setError("");
    try{
      if(!await saveProject())return;
      const response=await fetch("/api/projects/"+jobId+"/tracks/position",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({track_id:track.track_id,start_seconds:start})});
      const data=await response.json();if(!response.ok)throw Error(data.detail||"Could not reposition clip");
      setNotice("Clip moved to "+Number(start).toFixed(3)+" seconds.");onTrackAdded?.(data.project,data.job);
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setRenamingTrack(null);}
  }
  async function removeTrack(track:TrackIdentity){
    if(!window.confirm(`Remove ${track.display_name} from this song? The imported files will be archived for recovery.`))return;
    stop();setRenamingTrack(track.working_filename);setError("");
    try{
      if(!await saveProject())return;
      const response=await fetch("/api/projects/"+jobId+"/tracks/"+encodeURIComponent(track.track_id),{method:"DELETE",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_alias:track.stem_alias})});
      const data=await response.json();if(!response.ok)throw Error(data.detail||"Could not remove clip");
      setNotice(data.archive_warning||"Imported clip removed; its project files were archived for recovery.");onTrackAdded?.(data.project,data.job);
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setRenamingTrack(null);}
  }
  const [saving, setSaving] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [dawOpen, setDawOpen] = useState(false);
  const [handoffFolder, setHandoffFolder] = useState("");
  const [notice, setNotice] = useState("");
  const [playing, setPlaying] = useState(false);
  const [monitorVolume, setMonitorVolume] = useState(()=>{
    try{
      const value=Number(window.localStorage.getItem("song-harbor:monitor-volume"));
      return Number.isFinite(value)&&window.localStorage.getItem("song-harbor:monitor-volume")!==null
        ?Math.max(0,Math.min(100,value)):25;
    }catch{return 25;}
  });
  useEffect(()=>{
    try{window.localStorage.setItem("song-harbor:monitor-volume",String(monitorVolume));}
    catch{/* Private browser settings should not break playback. */}
  },[monitorVolume]);
  const [bypassed,setBypassed]=useState<Record<EffectKey,boolean>>(DEFAULT_BYPASS);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(expectedDuration || 0);
  const [exporting, setExporting] = useState(false);
  const [cleanupFindings,setCleanupFindings]=useState<readonly AudioFinding[]>([]);
  const [sectionInsights,setSectionInsights]=useState<readonly SectionInsight[]>([]);
  const [cleanupScanned,setCleanupScanned]=useState(false);
  const [cleanupStale,setCleanupStale]=useState(false);
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
  useEffect(()=>()=>{audio.current?.setReferenceOriginal(false);},[]);
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
  const [autoPanTargets,setAutoPanTargets]=useState<{section_id:string;target:"center";protected_sources:string[];protected_gain_sources?:string[];transition_seconds:number;curve:"smooth"|"linear"}[]>([]);
  const [autoPanReports,setAutoPanReports]=useState<string[]>([]);
  const [gainTargets,setGainTargets]=useState<{section_id:string;source_key:string;gain_db:number;transition_seconds:number;curve:"smooth"|"linear"}[]>([]);
  const [dynamicsTargets,setDynamicsTargets]=useState<DynamicsTarget[]>([]);
  const [spaceTargets,setSpaceTargets]=useState<{section_id:string;source_key:string;amount:number;transition_seconds:number;curve:"linear"|"smooth"}[]>([]);
  const [panLoaded,setPanLoaded]=useState(false);
  const [ending,setEnding]=useState<{fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"}>({
    fade_seconds:0,tail_seconds:0,curve:"smooth"
  });
  const [openTools,setOpenTools]=useState<WorkbenchTool[]>([]);
  const [sectionEffect,setSectionEffect]=useState<"pan"|"reverb"|"width"|"space"|"eq"|"deess">("pan");
  const [sectionEditId,setSectionEditId]=useState("");
  const [sectionPreviewActive,setSectionPreviewActive]=useState(false);
  const [sectionPreview,setSectionPreview]=useState<SectionPreview|null>(null);
  const [correction,setCorrection]=useState<CorrectionDraft|null>(null);
  const [declickDraft,setDeclickDraft]=useState<DeclickDraft|null>(null);
  const [declickRepairs,setDeclickRepairs]=useState<DeclickRecipe[]>([]);
  const [declickLoaded,setDeclickLoaded]=useState(false);
  const [declickBusy,setDeclickBusy]=useState(false);
  const [declickError,setDeclickError]=useState("");
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
  useEffect(()=>{audio.current?.setEffectBypass(correction?{...bypassed,compression:false,ducking:false,deess:false}:bypassed);},[bypassed,audioReady,correction]);
  useEffect(()=>{audio.current?.setReferenceOriginal(correction?.compare==="original"||declickDraft?.compare==="original");},
    [correction?.compare,declickDraft?.compare,audioReady]);
  useEffect(()=>{
    audio.current?.setPreviewDeclick(declickDraft?.recipe||null,declickDraft?.compare==="fix");
  },[declickDraft,audioReady]);
  useEffect(()=>{
    if(!audioReady)return;
    const engine=audio.current;
    if(!engine)return;
    let cancelled=false;
    setDeclickLoaded(false);
    void fetch("/api/projects/"+jobId+"/cleanup/declick",{cache:"no-store"})
      .then(async response=>{
        const body=await response.json() as {repairs?:DeclickRecipe[];detail?:string};
        if(!response.ok)throw Error(body.detail||"Cannot read saved repairs");
        if(!cancelled){const repairs=body.repairs||[];engine.setAcceptedDeclick(repairs);setDeclickRepairs(repairs);setDeclickLoaded(true);}
      }).catch(error=>{if(!cancelled)setDeclickError(error instanceof Error?error.message:String(error));});
    return()=>{cancelled=true;};
  },[audioReady,jobId]);
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
    setGainTargets([]);
    setAutoPanTargets([]);
    setDynamicsTargets([]);
    setEnding({fade_seconds:0,tail_seconds:0,curve:"smooth"});
    void fetch("/api/projects/"+jobId+"/sections/export")
      .then(async response=>{
        if(!response.ok)throw Error("Could not load pan automation");
        return response.json() as Promise<{reverb_targets:typeof reverbTargets;width_targets:SavedWidthTarget[];space_targets:typeof spaceTargets;eq_targets:SavedEqTarget[];gain_targets:typeof gainTargets;auto_pan_targets:typeof autoPanTargets;dynamics_targets:typeof dynamicsTargets;ending:typeof ending}>;
      })
      .then(async data=>{
        const panResponse=await fetch("/api/projects/"+jobId+"/section-pan");
        if(!panResponse.ok)throw Error("Could not load pan automation");
        const panData=await panResponse.json() as {targets:SavedPanTarget[]};
        if(!cancelled){setPanTargets(panData.targets||[]);setReverbTargets(data.reverb_targets||[]);setWidthTargets(data.width_targets||[]);setSpaceTargets(data.space_targets||[]);setEqTargets(data.eq_targets||[]);setGainTargets(data.gain_targets||[]);setAutoPanTargets(data.auto_pan_targets||[]);setDynamicsTargets(data.dynamics_targets||[]);setEnding(data.ending||{fade_seconds:0,tail_seconds:0,curve:"smooth"});setPanLoaded(true);}
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
      const identity=trackIdentities.find(track=>track.working_filename===filename);
      const sourceMeta={startSeconds:identity?.start_seconds||0,timelinePositioned:Boolean(identity?.imported)};
      const split=channels[filename];
      if(split?.active){
        sources.push({key:filename+":left",filename,url:split.tracks.left.url,pan:-1,...sourceMeta});
        sources.push({key:filename+":right",filename,url:split.tracks.right.url,pan:1,...sourceMeta});
      }else{
        sources.push({key:filename,filename,
          url:"/api/jobs/"+jobId+"/stream/"+encodeURIComponent(filename),pan:0,...sourceMeta});
      }
    }
    setAudioLoad({ready:0,total:sources.length});
    void engine.prepare(sources,(ready,total)=>{
      if(!cancelled)setAudioLoad({ready,total});
    },expectedDuration).then(()=>{
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
  },[files,jobId,expectedDuration,routingVersion,trackIdentities]);

  useEffect(()=>{
    const levels:Record<string,{gain:number}>={};
    for(const stem of stems)levels[stem.filename]={gain:effectiveGain(stem,anySolo)};
    audio.current?.setLevels(levels,monitorVolume/100);
  },[stems,anySolo,monitorVolume,audioReady]);

  useEffect(()=>{
    const engine=audio.current;
    if(!engine?.ready||!panLoaded)return;
    const proposed=sectionPreviewActive?sectionPreview:null;
    const trialPan=proposed?.kind==="pan"?proposed.targets:panTargets;
    const trialReverb=proposed?.kind==="reverb"?proposed.targets:reverbTargets;
    const trialWidth=proposed?.kind==="width"?proposed.targets:widthTargets;
    const trialSpace=proposed?.kind==="space"?proposed.targets:spaceTargets;
    const baseEq=proposed?.kind==="eq"?proposed.targets:eqTargets;
    const spectral=correction?.kind==="spectral"&&correction.proposed?correction:null;
    const trialEq=spectral&&spectral.eqBand?[
      ...baseEq.filter(item=>!(item.source_key===spectral.file&&item.section_id===spectral.sectionId&&item.band===spectral.eqBand)),
      {section_id:spectral.sectionId,source_key:spectral.file,band:spectral.eqBand,
       frequency:spectral.frequency,q:spectral.q,gain_db:-Math.min(9,spectral.depth*spectral.auditionBoost),
       transition_seconds:spectral.transition,curve:"smooth" as const}
    ]:baseEq;
    const trialDynamics=proposed?.kind==="deess"?proposed.targets:dynamicsTargets;
    const byFile:Record<string,{gain?:ReturnType<typeof compileSectionAutomation>;pan?:ReturnType<typeof compileSectionAutomation>;reverb?:ReturnType<typeof compileSectionAutomation>;width?:ReturnType<typeof compileSectionAutomation>;space?:ReturnType<typeof compileSectionAutomation>;eq?:Partial<Record<1|2|3,{frequency:ReturnType<typeof compileSectionAutomation>;q:ReturnType<typeof compileSectionAutomation>;gain:ReturnType<typeof compileSectionAutomation>}>>;dynamics?:{compressor?:{threshold:ReturnType<typeof compileSectionAutomation>;ratio:ReturnType<typeof compileSectionAutomation>};duck?:{depthDb:ReturnType<typeof compileSectionAutomation>;keyFilename:string};deess?:{frequency:ReturnType<typeof compileSectionAutomation>;q:ReturnType<typeof compileSectionAutomation>;threshold:ReturnType<typeof compileSectionAutomation>;maxReduction:ReturnType<typeof compileSectionAutomation>}}}>={};
    const sectionById=new Map(timelineSections.map(section=>[section.id,section]));
    // Virtual source keys address the left/right channels of an active split.
    // The parent key remains separate; all.gain and other parent directions
    // continue to affect the reconstructed stem bus.
    const effectKeys=[...files,...files.flatMap(filename=>channels[filename]?.active?
      [filename+":left",filename+":right"]:[])];
    for(const filename of effectKeys){
      const desired=gainTargets.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:Math.pow(10,item.gain_db/20),transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={gain:compileSectionAutomation(desired,1,{min:Math.pow(10,-24/20),max:Math.pow(10,12/20)})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid stem gain automation");return;}
    }
    for(const filename of effectKeys){
      const saved=trialPan.filter(item=>item.source_key===filename);
      if(!saved.length)continue;
      const desired=saved.flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{
          sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.pan,transitionSeconds:item.transition_seconds,curve:item.curve,
        }]:[];
      });
      try{
        byFile[filename]={...(byFile[filename]||{}),pan:compileSectionAutomation(desired,0,{min:-1,max:1})};
      }catch(e){
        setError(e instanceof Error?e.message:"Invalid section pan automation");
        return;
      }
    }
    for(const filename of effectKeys){
      const desired=trialReverb.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.wet,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),reverb:compileSectionAutomation(desired,0,{min:0,max:1})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid reverb automation");return;}
    }
    for(const filename of effectKeys){
      const desired=trialWidth.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.width/100,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),width:compileSectionAutomation(desired,1,{min:0,max:1.5})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid width automation");return;}
    }
    for(const filename of effectKeys){
      const desired=trialSpace.filter(item=>item.source_key===filename).flatMap(item=>{
        const section=sectionById.get(item.section_id);
        return section?[{sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:item.amount/100,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      if(!desired.length)continue;
      try{
        byFile[filename]={...(byFile[filename]||{}),space:compileSectionAutomation(desired,0,{min:0,max:.4})};
      }catch(e){setError(e instanceof Error?e.message:"Invalid spatial reflections");return;}
    }
    for(const filename of effectKeys){
      for(const band of [1,2,3] as const){
        const desired=trialEq.filter(item=>item.source_key===filename&&item.band===band)
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
    const staged=correction&&correction.proposed&&correction.kind!=="trim"&&correction.kind!=="spectral"?
      [...trialDynamics.filter(item=>!(item.section_id===correction.sectionId&&
        item.source_key===correction.file&&item.kind===correction.kind)),{
        section_id:correction.sectionId,source_key:correction.file,kind:correction.kind,
        threshold_db:correction.threshold,
        ratio:Math.min(4,1+(correction.ratio-1)*correction.auditionBoost),
        depth_db:Math.min(12,correction.depth*correction.auditionBoost),
        frequency:correction.frequency,q:correction.q,
        max_reduction_db:Math.min(12,correction.maxReduction*correction.auditionBoost),
        transition_seconds:correction.transition,curve:"smooth" as const
      }]:trialDynamics;
    for(const filename of effectKeys){
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
    // Auto-pan is a section-scoped analysis request, never a continuous live servo.
    // Explicit/inherited pan targets supplied by the importer remain locked.
    const reports:string[]=[];
    const autoPanDesired=new Map<string,{sectionId:string;start:number;end:number;value:number;transitionSeconds:number;curve:"smooth"|"linear"}[]>();
    const autoGainDesired=new Map<string,{sectionId:string;start:number;end:number;value:number;transitionSeconds:number;curve:"smooth"|"linear"}[]>();
    const autoOrdered=[...autoPanTargets].sort((a,b)=>
      (sectionById.get(a.section_id)?.start_seconds??0)-(sectionById.get(b.section_id)?.start_seconds??0));
    for(const request of autoOrdered){
      const section=sectionById.get(request.section_id);
      if(!section)continue;
      // As automatic edits are added, downstream sections inherit them naturally.
      const result=engine.solveSectionAutoPan(section.start_seconds,section.end_seconds,
        request.protected_sources,request.protected_gain_sources||[],byFile);
      reports.push(section.kind+" "+section.start_seconds.toFixed(1)+"s: "+
        result.beforeDb.toFixed(2)+" dB -> "+result.predictedDb.toFixed(2)+
        " dB predicted; "+result.reason);
      for(const correction of result.adjustments){
        if(!autoPanDesired.has(correction.filename))autoPanDesired.set(correction.filename,[]);
        autoPanDesired.get(correction.filename)!.push({
          sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
          value:correction.pan,transitionSeconds:request.transition_seconds,curve:request.curve});
        if(Math.abs(correction.gainDb)>.025){
          if(!autoGainDesired.has(correction.filename))autoGainDesired.set(correction.filename,[]);
          const base=byFile[correction.filename]?.gain
            ?valueAt(byFile[correction.filename].gain!,section.start_seconds):1;
          autoGainDesired.get(correction.filename)!.push({
            sectionId:section.id,start:section.start_seconds,end:section.end_seconds,
            value:base*Math.pow(10,correction.gainDb/20),
            transitionSeconds:request.transition_seconds,curve:request.curve});
        }
      }
      for(const [filename,additions] of autoPanDesired){
        const explicit=trialPan.filter(item=>item.source_key===filename).flatMap(item=>{
          const target=sectionById.get(item.section_id);
          return target?[{sectionId:target.id,start:target.start_seconds,end:target.end_seconds,
            value:item.pan,transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
        });
        const merged=[...explicit,...additions].sort((a,b)=>a.start-b.start);
        byFile[filename]={...(byFile[filename]||{}),
          pan:compileSectionAutomation(merged,0,{min:-1,max:1})};
      }
    }
    for(const [filename,additions] of autoGainDesired){
      const explicit=gainTargets.filter(item=>item.source_key===filename).flatMap(item=>{
        const target=sectionById.get(item.section_id);
        return target?[{sectionId:target.id,start:target.start_seconds,end:target.end_seconds,
          value:Math.pow(10,item.gain_db/20),transitionSeconds:item.transition_seconds,curve:item.curve}]:[];
      });
      byFile[filename]={...(byFile[filename]||{}),
        gain:compileSectionAutomation([...explicit,...additions].sort((a,b)=>a.start-b.start),
          1,{min:Math.pow(10,-24/20),max:Math.pow(10,12/20)})};
    }
    setAutoPanReports(previous=>previous.join("|")===reports.join("|")?previous:reports);
    engine.setAutomation(byFile,Boolean(correction||sectionPreviewActive));
    engine.setEnding(ending);
    setDuration(engine.duration);
  },[audioReady,panLoaded,panTargets,reverbTargets,widthTargets,spaceTargets,eqTargets,gainTargets,autoPanTargets,dynamicsTargets,ending,timelineSections,files,channels,stems,correction,sectionPreviewActive,sectionPreview]);

  // Retain the previous findings after a mix change as a labelled snapshot.
  // Old scan results must not be presented as analysis of the new settings.
  useEffect(()=>{
    analysisRevision.current++;
    setCleanupStale(true);
  },[stems,masterTrimDb,panTargets,reverbTargets,widthTargets,spaceTargets,eqTargets,gainTargets,autoPanTargets,dynamicsTargets,ending,channels,timelineSections,bypassed]);

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
        // Completion differs from Pause: reset both underlying shared-clock
        // state and visible playhead, so the next Play starts at zero.
        transportGeneration.current+=1;
        playRef.current=false;
        engine.stop();
        setPlaying(false);
        setPosition(0);
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

  function tryDeclick(finding:AudioFinding){
    const engine=audio.current;
    if(!engine?.ready)return;
    const sources=engine.declickSourceKeys;
    const preferred=sources.find(source=>finding.sources?.some(name=>
      source.filename.includes("("+name+")")) )||sources[0];
    if(!preferred){setDeclickError("No editable audio source");return;}
    setCorrection(null);
    setDeclickError("");
    setDeclickDraft({compare:"fix",recipe:{
      id:crypto.randomUUID(),filename:preferred.filename,source_key:preferred.key,
      time_seconds:finding.timeSeconds,half_window_ms:1
    }});
    loopAround(finding.timeSeconds-.8,finding.timeSeconds+1.2);
  }
  async function acceptDeclick(){
    const draft=declickDraft;
    if(!draft||draft.compare!=="fix"||declickBusy)return;
    setDeclickBusy(true);setDeclickError("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/cleanup/declick",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify(draft.recipe)
      });
      const body=await response.json() as {repairs?:DeclickRecipe[];detail?:string};
      if(!response.ok||!body.repairs)throw Error(body.detail||"Could not save de-click");
      setDeclickDraft(null);
      setDeclickRepairs(body.repairs);
      const engine=audio.current;
      engine?.setPreviewDeclick(null,false);
      engine?.setAcceptedDeclick(body.repairs);
      setCleanupStale(true);setMixUrl(null);
      setNotice("De-click accepted non-destructively; export uses saved repair.");
    }catch(error){setDeclickError(error instanceof Error?error.message:String(error));}
    finally{setDeclickBusy(false);}
  }
  async function undoDeclick(id:string){
    setDeclickBusy(true);setDeclickError("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/cleanup/declick/"+encodeURIComponent(id),{method:"DELETE"});
      const body=await response.json() as {repairs?:DeclickRecipe[];detail?:string};
      if(!response.ok||!body.repairs)throw Error(body.detail||"Could not undo de-click");
      setDeclickRepairs(body.repairs);
      audio.current?.setAcceptedDeclick(body.repairs);
      setCleanupStale(true);setMixUrl(null);
    }catch(error){setDeclickError(error instanceof Error?error.message:String(error));}
    finally{setDeclickBusy(false);}
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
    const suggestedStem=(["harshness","fizz","noise","signal_audit"].includes(finding.kind)?undefined:preferred?.source_key)||
      files.find(f=>finding.sources?.some(name=>f.includes("("+name+")")))||
      files.find(f=>f.includes("(Drums)"))||files[0];
    const kind=finding.kind==="headroom"?"trim":
      (["harshness","fizz","noise","signal_audit"].includes(finding.kind)?"spectral":
      finding.kind==="sibilance"?"deess":(preferred?.kind==="deess"?"duck":preferred?.kind||"duck"));
    const deessStem=kind==="deess"?files.find(f=>f.includes("(Vocals)")):undefined;
    const file=(kind==="duck"&&suggestedStem?.includes("(Vocals)"))?
      files.find(f=>!f.includes("(Vocals)"))||suggestedStem:(deessStem||suggestedStem);
    const eqUsed=eqTargets.filter(item=>item.section_id===section?.id&&item.source_key===file).map(item=>item.band);
    const eqBand=([3,2,1] as const).find(band=>!eqUsed.includes(band));
    if(kind==="spectral"&&(!section||!eqBand)){
      setCorrectionError("No free EQ band in this section for the selected source. Use Section EQ to adjust an existing band.");
      return;
    }
    const spectralFrequency=finding.kind==="harshness"?3500:finding.kind==="fizz"?10000:
      finding.kind==="noise"?8500:6000;
    const peakMatch=finding.detail.match(/(-?[0-9]+(?:\.[0-9]+)?) dBFS/);
    const peak=peakMatch?Number(peakMatch[1]):0;
    setCorrectionError("");
    setDeclickDraft(null);
    setCorrection({
      finding,sectionId:section?.id||"",file,kind,
      threshold:kind==="deess"?-40:(preferred?.threshold_db??-18),ratio:1.6,depth:kind==="spectral"?3:2,transition:1.5,
      frequency:kind==="spectral"?spectralFrequency:6500,q:2,maxReduction:4,auditionBoost:1,eqBand,
      trimDelta:-Math.max(0,Math.min(12,Math.round((peak+1)*10)/10)),proposed:false,compare:"current"
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
    if(trial.kind==="spectral"&&(!trial.eqBand||eqTargets.some(item=>item.section_id===trial.sectionId&&item.source_key===trial.file&&item.band===trial.eqBand))){
      setCorrectionError("Selected EQ band is occupied for this source and section. Choose a different track or edit the existing EQ.");return;
    }
    const directive=trial.kind==="spectral"?
      `${alias}.eq${trial.eqBand}:${trial.frequency},${trial.q.toFixed(1)},-${Math.min(9,trial.depth).toFixed(1)}@${trial.transition}s:smooth`:
      trial.kind==="comp"?
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
      let blockStart=-1,blockEnd=-1;
      for(let i=header+1;i<nextHeader;i++){
        if(!lines[i].trim().startsWith("{"))continue;
        blockStart=i;
        for(let j=i;j<nextHeader;j++){
          if(lines[j].trim().endsWith("}")){blockEnd=j;break;}
        }
        break;
      }
      if(blockStart<0){
        lines.splice(header+1,0,"{"+directive+"}");
      }else{
        if(blockEnd<blockStart)throw Error("Saved section contains an unfinished production block.");
        const text=lines.slice(blockStart,blockEnd+1).join("\n");
        const existing=text.trim().slice(1,-1).trim().split(/\s+/).filter(Boolean);
        const key=trial.kind==="spectral"?alias+".eq"+trial.eqBand+":":alias+"."+trial.kind+":";
        const without=existing.filter(token=>!token.startsWith(key));
        const edited=[...without,directive];
        const updated=edited.length===1?["{"+edited[0]+"}"]:
          ["{",...edited.map(token=>"  "+token),"}"];
        lines.splice(blockStart,blockEnd-blockStart+1,...updated);
      }
      const result=await fetch("/api/projects/"+jobId+"/sections/import",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content:lines.join("\n"),mode:"replace"})
      });
      const data=await result.json() as {detail?:string;sections?:SongSection[];pan_targets?:SavedPanTarget[];
        reverb_targets?:SavedReverbTarget[];width_targets?:SavedWidthTarget[];space_targets?:typeof spaceTargets;
        eq_targets?:SavedEqTarget[];dynamics_targets?:typeof dynamicsTargets;gain_targets?:typeof gainTargets;auto_pan_targets?:typeof autoPanTargets;ending?:typeof ending};
      if(!result.ok||!data.sections)throw Error(data.detail||"Could not save dynamics correction");
      setCorrection(null);
      setExternalSections(data.sections);setTimelineSections(data.sections);
      setPanTargets(data.pan_targets||[]);setReverbTargets(data.reverb_targets||[]);
      setWidthTargets(data.width_targets||[]);setSpaceTargets(data.space_targets||[]);
      setEqTargets(data.eq_targets||[]);setDynamicsTargets(data.dynamics_targets||[]);setGainTargets(data.gain_targets||[]);setAutoPanTargets(data.auto_pan_targets||[]);
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
    setAnalyzing(true);setCleanupError("");
    try{
      const results=await engine.analyzeMix(timelineSections);
      if(analysisRevision.current!==revision){
        setCleanupError("The mix changed during analysis. Re-analyze the new settings.");
        return;
      }
      setCleanupFindings(results);
      setSectionInsights(engine.sectionInsights);
      setCleanupScanned(true);
      setCleanupStale(false);
    }catch(e){
      setCleanupError(e instanceof Error?e.message:"Sound analysis failed");
    }finally{setAnalyzing(false);}
  }

  async function exportMix(overrideTrimDb?:number) {
    const engine=audio.current;
    if(correction||sectionPreviewActive){setError("Return Section Edit to A Saved and accept/discard corrections before exporting the saved mix.");return;}
    if(!engine?.ready){setError("Wait for synchronized audio to load before exporting.");return;}
    if(!declickLoaded){setError("Saved repair state has not loaded. Export is blocked to prevent missing accepted repairs.");return;}
    stop();
    setExporting(true);
    setMixUrl(null);
    setMixBytes(null);
    setError("");
    setNotice("");
    setHeadroomIssue(null);
    setCleanupStale(true);
    try{
      if(overrideTrimDb!==undefined){
        engine.setOutputTrimDb(overrideTrimDb);
        setMasterTrimDb(overrideTrimDb);
      }
      const blob=await engine.renderWav24();
      setCleanupFindings(engine.cleanupFindings);
      setCleanupScanned(true);
      setCleanupStale(false);
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
          <label className="master-monitor" title={"Monitoring volume "+monitorVolume+"% · remembered on this device · does not change exported mixes"}>
            <span aria-hidden="true">🔊</span>
            <input type="range" min="0" max="100" step="1" value={monitorVolume}
              aria-label="Playback monitoring volume" onChange={e=>setMonitorVolume(Number(e.target.value))}/>
          </label>
        </div>
        <section ref={timelineRef} className="integrated-timeline" aria-label="Integrated production timeline">
          <SectionEditor jobId={jobId} duration={duration} position={position}
            initialSections={initialSections} externalSections={externalSections} insights={sectionInsights}
            onAnalyzeSections={()=>{void analyzeMix();}} analyzingSections={analyzing} sectionAnalysisError={cleanupError}
            onSeek={seek} viewStart={viewStart} viewEnd={viewEnd}
            onSectionsChange={setTimelineSections}
            onPersisted={()=>setScriptRevision(v=>v+1)}
            onSectionDoubleClick={section=>{setScriptFocus(section);setSectionEditId(section.id);setSectionEffect("pan");setSectionPreviewActive(false);setSectionPreview(null);setOpenTools(items=>[...items.filter(x=>x!=="sectionEdit"),"sectionEdit"]);}}/>
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
        <details className="song-stem-controls" open>
        <summary className="song-stem-controls-summary">Stem controls · {stems.length} tracks</summary>
        <div className="mixer-heading">
          <div><h3>Mix levels</h3></div>
          <IconButton icon="↶" label="Reset mix" onClick={()=>{
            setStems(current=>current.map(s=>({...s,gain:100,mute:false,solo:false})));
          }}/>
        </div>
        <div className="mixer-tracks">
          <label className="track-add-button" title="Add an already-prepared audio stem to this song">
            {addingTrack?"Converting stem...":"+ Add stem"}
            <input type="file" accept=".wav,.flac,.mp3,.m4a,.aiff,.aif,.ogg,audio/*"
              aria-label="Choose audio file to add as a new stem" disabled={addingTrack||renamingTrack!==null}
              onChange={e=>{chooseTrack(e.target.files?.[0]);e.target.value="";}}
              style={{position:"absolute",width:1,height:1,opacity:0}}/>
          </label>
          {pendingFile&&<div className="track-import-editor">
            <strong>{pendingFile.name}</strong>
            <label>Display <input value={newDisplay} maxLength={100} onChange={e=>setNewDisplay(e.target.value)}/></label>
            <label>Script alias <input value={newAlias} maxLength={32} onChange={e=>setNewAlias(e.target.value)}/></label>
            <label>Place at <select value={placement} onChange={e=>setPlacement(e.target.value)}>
              <option value="start">Song start · 0.000s</option>
              <option value="custom">Timestamp…</option>
              {timelineSections.map(section=><option key={section.id} value={"section:"+section.id}>{section.kind}{section.number===null?"":" "+section.number} · {section.start_seconds.toFixed(3)}s</option>)}
            </select></label>
            {placement==="custom"&&<label>Seconds <input type="number" min="0" step="0.001" value={customStart} onChange={e=>setCustomStart(e.target.value)}/></label>}
            <Button onClick={()=>void addTrack()} disabled={addingTrack||!newDisplay.trim()||!newAlias.trim()}>{addingTrack?"Importing…":"Import clip"}</Button>
            <Button variant="subtle" onClick={()=>setPendingFile(null)} disabled={addingTrack}>Cancel</Button>
          </div>}
      {stems.map(s => <div className={"mixer-track"+(trackLabels?.[s.filename]?" mixer-track--named":"")} key={s.filename}>
        <strong className={"stem-icon-name"+(trackLabels?.[s.filename]?" stem-icon-name--named":"")}
          title={s.name+" · script: "+(trackAliases?.[s.filename]||labelOf(s.filename))}
          aria-label={s.name}><AudioIcon kind={trackAliases?.[s.filename]||labelOf(s.filename)} size={32}/>
          {trackLabels?.[s.filename]?<span className="mixer-stem-names"><span className="mixer-stem-name">{s.name}</span>
            <small>{trackAliases?.[s.filename]||labelOf(s.filename)}</small></span>:<span className="sr-only">{s.name}</span>}
          <span className="stem-label-toggles" aria-label={s.name+" quick controls"}>
            <button type="button" className={"track-toggle"+(s.mute?" is-muted":"")} aria-label={"Mute "+s.name}
              aria-pressed={s.mute} title={"Mute "+s.name} onClick={()=>update(s.filename,{mute:!s.mute})}>M</button>
            <button type="button" className={"track-toggle"+(s.solo?" is-solo":"")} aria-label={"Isolate "+s.name}
              aria-pressed={s.solo} title={"Isolate (solo) "+s.name} onClick={()=>update(s.filename,{solo:!s.solo})}>S</button>
          </span>
        </strong>
        <div className="track-actions">
          <button type="button" className="track-toggle" disabled={renamingTrack!==null}
            onClick={()=>void renameTrack(s.filename)}
            title={"Rename "+s.name+" and update its scripted production guidance"}
            aria-label={"Rename "+s.name}>✎</button>
          {trackIdentities.find(t=>t.working_filename===s.filename)?.imported&&<>
            <button type="button" className="track-toggle" disabled={renamingTrack!==null}
              onClick={()=>void repositionTrack(trackIdentities.find(t=>t.working_filename===s.filename)!)}
              title={"Reposition "+s.name} aria-label={"Reposition "+s.name}>↔</button>
            <button type="button" className="track-toggle track-remove" disabled={renamingTrack!==null}
              onClick={()=>void removeTrack(trackIdentities.find(t=>t.working_filename===s.filename)!)}
              title={"Remove "+s.name} aria-label={"Remove "+s.name}>×</button>
          </>}
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
        </details>
      </main>
      <aside className="song-tool-rail" aria-label="Production tools">
        {TOOL_ITEMS.map(item=><button type="button" key={item.id}
          className="song-tool-icon" title={item.label} aria-label={"Open "+item.label+" tool"}
          aria-pressed={openTools.includes(item.id)}
          onClick={()=>{
            if(item.id==="sectionEdit")setSectionEditId(current=>current||timelineSections[0]?.id||"");
            if(item.id==="cleanup"&&openTools.includes("cleanup")){setCorrection(null);setDeclickDraft(null);}
            if(item.id==="sectionEdit"&&openTools.includes("sectionEdit")){setSectionPreviewActive(false);setSectionPreview(null);}
            setOpenTools(existing=>existing.includes(item.id)?
              existing.filter(x=>x!==item.id):[...existing,item.id]);
          }}>
          <span aria-hidden="true">{item.icon}</span>
        </button>)}
      </aside>
      {openTools.map((tool,order)=><ToolWindow key={tool}
        name={tool==="songText"?"Whole-song section text":TOOL_ITEMS.find(item=>item.id===tool)?.label||"Tool"} order={order}
        onFocus={()=>setOpenTools(current=>current[current.length-1]===tool?current:
          [...current.filter(item=>item!==tool),tool])}
        onClose={()=>{
          setOpenTools(items=>items.filter(item=>item!==tool));
          if(tool==="sectionEdit"){setSectionPreviewActive(false);setSectionPreview(null);}
          if(tool==="cleanup"){setCorrection(null);setDeclickDraft(null);}
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
            <button type="button" className="song-open-full-script"
              onClick={()=>setOpenTools(items=>items.includes("songText")?items:[...items,"songText"])}>
              <span aria-hidden="true">{"{}"}</span> Edit whole-song section text…
            </button>
            <div className="song-section-audition" role="group" aria-label="Section edit A/B">
              <div className="song-section-audition-switch">
                <button type="button" aria-pressed={!sectionPreviewActive}
                  onClick={()=>setSectionPreviewActive(false)}>A · Saved</button>
                <button type="button" aria-pressed={sectionPreviewActive}
                  onClick={()=>{
                    setCorrection(null);
                    setSectionPreviewActive(true);
                    const section=timelineSections.find(x=>x.id===sectionEditId)||timelineSections[0];
                    if(section){
                      setLoopIn(section.start_seconds);
                      setLoopOut(section.end_seconds);
                      setLoopEnabled(true);
                      seek(section.start_seconds);
                      if(!playRef.current)void togglePlayback();
                    }
                  }}>B · Draft preview</button>
              </div>
              <small>Adjust the effect controls while B plays. A restores the saved mix.
                Nothing is written until the effect's Save/Apply button is used.
                Switch to A to discard the audition, or close this window.</small>
            </div>
            <div className="song-section-effect-tabs" role="tablist" aria-label="Section edit effect">
              {(["pan","reverb","width","space","eq","deess"] as const).map(effect=>
                <button key={effect} type="button" role="tab" aria-selected={sectionEffect===effect}
                  onClick={()=>{setSectionPreviewActive(false);setSectionPreview(null);setSectionEffect(effect);}}>
                  {effect==="width"?"Width":effect==="space"?"Reflections":effect==="eq"?"EQ":effect==="deess"?"De-ess":effect[0].toUpperCase()+effect.slice(1)}
                </button>)}
            </div>
          </div>
        </>}

        {autoPanReports.length>0&&<details className="auto-pan-diagnostics"><summary>Auto-pan diagnostics ({autoPanReports.length} sections, dry-stem estimates)</summary>
          {autoPanReports.map((line,i)=><p key={i}>{line}</p>)}
          <small>Final color scan measures actual effects-processed stereo mix, which can differ from this approximation.</small>
        </details>}
        {tool==="songText"&&<>
        <SectionsTool jobId={jobId} songTitle={title} open={tool==="songText"}
          position={position} duration={duration} playing={playing} onSeek={seek} onTogglePlay={()=>{void togglePlayback();}}
          onClose={()=>{setOpenTools(items=>items.filter(x=>x!=="songText"));}} focused={scriptFocus} revision={scriptRevision}
          onApplied={(items,targets,reverb,width,space,eq,dynamics,gain,auto,finish)=>{
            setPanTargets(targets);
            setReverbTargets(reverb);
            setWidthTargets(width);
            setSpaceTargets(space);
            setEqTargets(eq);
            setDynamicsTargets(dynamics);
            setGainTargets(gain);
            setAutoPanTargets(auto);
            setMixUrl(null);
            setEnding(finish);
            setExternalSections(items);setTimelineSections(items);
            setZoom(1);setViewportOffset(0);setScriptRevision(v=>v+1);
          }}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="pan"&&<>
        <SectionPanTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"pan",targets:items})}
          targets={panTargets} onChange={items=>{setSectionPreviewActive(false);setSectionPreview(null);setPanTargets(items);setMixUrl(null);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="reverb"&&<>
        <SectionReverbTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"reverb",targets:items})}
          targets={reverbTargets} onChange={items=>{setSectionPreviewActive(false);setSectionPreview(null);setReverbTargets(items);setMixUrl(null);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="width"&&<>
        <SectionWidthTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"width",targets:items})}
          targets={widthTargets} onChange={items=>{setSectionPreviewActive(false);setSectionPreview(null);setWidthTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}
        {tool==="sectionEdit"&&sectionEffect==="space"&&<>
        <SectionSpaceTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"space",targets:items})}
          targets={spaceTargets} onChange={items=>{setSectionPreviewActive(false);setSectionPreview(null);setSpaceTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="eq"&&<>
        <SectionEqTool jobId={jobId} sections={timelineSections} files={files} initialSectionId={sectionEditId}
          previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"eq",targets:items})}
          targets={eqTargets} onChange={items=>{setSectionPreviewActive(false);setSectionPreview(null);setEqTargets(items);setMixUrl(null);setScriptRevision(v=>v+1);}}/>

        </>}

        {tool==="sectionEdit"&&sectionEffect==="deess"&&<>
          <SectionDeEssTool jobId={jobId} sections={timelineSections} files={files}
            initialSectionId={sectionEditId} targets={dynamicsTargets}
            previewEnabled={sectionPreviewActive} onPreview={items=>setSectionPreview({kind:"deess",targets:items})}
            onSaved={data=>{setSectionPreviewActive(false);setSectionPreview(null);
              setExternalSections(data.sections);setTimelineSections(data.sections);
              setPanTargets(data.pan_targets);setReverbTargets(data.reverb_targets);
              setWidthTargets(data.width_targets);setSpaceTargets(data.space_targets);
              setEqTargets(data.eq_targets);setDynamicsTargets(data.dynamics_targets);
              setEnding(data.ending);setMixUrl(null);setScriptRevision(v=>v+1);
            }}/>
        </>}
        {tool==="cleanup"&&declickDraft&&<>
          <DeclickWorkbench draft={declickDraft} sources={audio.current?.declickSourceKeys||[]}
            locked={declickBusy} onChange={setDeclickDraft}
            onAccept={()=>{void acceptDeclick();}}
            onCancel={()=>{setDeclickDraft(null);setDeclickError("");}}/>
        </>}
        {tool==="cleanup"&&declickError&&<p role="alert" className="song-cleanup-error">{declickError}</p>}
        {tool==="cleanup"&&declickRepairs.length>0&&<details className="song-cleanup-repairs">
          <summary>Accepted de-clicks ({declickRepairs.length})</summary>
          {declickRepairs.map(item=><div key={item.id} className="song-cleanup-actions">
            <span>{item.time_seconds.toFixed(2)}s · {item.source_key.match(/\\(([^)]+)\\)/)?.[1]||item.filename}</span>
            <button type="button" disabled={declickBusy} onClick={()=>void undoDeclick(item.id)}>Undo</button>
          </div>)}
        </details>}
        {tool==="cleanup"&&correctionError&&!correction&&<p role="alert" className="song-cleanup-error">{correctionError}</p>}
        {tool==="cleanup"&&correction&&<>
          <CorrectionWorkbench draft={correction} files={files} trimBase={masterTrimDb}
            reduction={meters.find(item=>item.filename===correction.file)}
            busy={correctionSaving} onChange={next=>{
              if(next.kind==="spectral"&&next.file!==correction.file){
                const used=eqTargets.filter(item=>item.section_id===next.sectionId&&item.source_key===next.file).map(item=>item.band);
                next={...next,eqBand:([3,2,1] as const).find(band=>!used.includes(band))};
              }
              setCorrection(next);
            }} onAccept={()=>{void acceptCorrection();}}
            onCancel={()=>{setCorrection(null);setCorrectionError("");}}/>
          {correctionError&&<p role="alert" className="song-cleanup-error">{correctionError}</p>}
        </>}
        {tool==="cleanup"&&<>
        <CleanupReview findings={cleanupFindings} comparison={audio.current?.stageComparison} scanned={cleanupScanned} stale={cleanupStale}
          analyzing={analyzing} error={cleanupError} ready={audioReady} busy={exporting||Boolean(correction)}
          onAnalyze={()=>{void analyzeMix();}} onSeek={seek} onTryCorrection={tryCorrection} onTryDeclick={tryDeclick}
          onLoop={(start,end)=>{
            setLoopIn(Math.min(start,duration));
            setLoopOut(Math.min(duration,end));
            setLoopEnabled(true);
            seek(Math.max(0,Math.min(start,duration)));
            if(!playRef.current)void togglePlayback();
          }}/>

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
                onClick={()=>setBypassed({pan:true,width:true,space:true,reverb:true,eq:true,compression:true,ducking:true,deess:true,ending:true})}>B · Original</button>
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
        {tool==="accompaniment"&&<AccompanimentGenerator jobId={jobId} sections={timelineSections}
          engine={audio.current} playing={playing} position={position} onSeek={seek}
          onPlay={togglePlayback} onPause={stop} onInserted={({project,job})=>onTrackAdded?.(project,job)}
          saveProject={saveProject} onError={setError}/>}
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
          disabled={exporting||Boolean(correction)||sectionPreviewActive} onClick={()=>{void exportMix();}}/>
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
