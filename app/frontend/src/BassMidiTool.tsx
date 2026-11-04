import {useEffect,useState} from "react";
import {MidiPianoRoll,type Arrangement} from "./MidiPianoRoll";
import type {SongSection} from "./SectionEditor";
import type {SharedClockAudition} from "./SharedClockAudition";

type Note={pitch:number;start:number;end:number;velocity:number};
export type Candidate={candidate_id:string;arrangement_id?:string;arrangement_revision?:number;section_id?:string;instrument?:string;pack_id?:string;source_track_id?:string;start_seconds:number;duration_seconds:number;notes:Note[];original_notes:Note[];rendered?:boolean;method:string};
export type MidiRenderSession={jobId:string;sourceTrackId:string;candidates:Candidate[];index:number;acceptedSectionIds:string[]};
type Track={track_id:string;stem_alias:string;display_name:string;imported?:boolean;start_seconds?:number;duration_seconds?:number};
type InstrumentPack={id:string;name:string;engine:string;source:string};
type InstrumentChoice={id:string;name:string;pack_id:string;engine:string;program:number;bank:number};
type InstrumentCatalogue={packs:InstrumentPack[];instruments:InstrumentChoice[];fluidsynth_ready:boolean;sfizz_ready?:boolean};
// General MIDI programs, zero-based. Favorites prioritize Infra Choir's
// gothic/industrial/orchestral palette without hiding any other presets.
const STARTER_PROGRAMS=[42,43,44,45,48,49,50,52,54,55,57,60,61,62,30,34,38,89];
const preferred=(x:InstrumentChoice)=>x.engine==="sf2"&&x.bank===0?STARTER_PROGRAMS.indexOf(x.program):-1;

type Starter={id:string;name:string;description:string;source_page:string;installed:boolean};
type CuratedSfz={id:string;name:string;family:string;fit:string;priority:number;description:string;source:string;license:string;version:string;approx_mb:number|null;status:string;source_page:string;download_url:string};
type Imported={project:unknown;job:unknown};
type Props={jobId:string;sections:SongSection[];songDuration:number;position:number;selectedTrackId?:string;engine:SharedClockAudition|null;
 stemControls:{filename:string;trackId?:string;gain:number;mute:boolean;solo:boolean;name:string}[];
 onStemMix:(filename:string,changes:{gain?:number;mute?:boolean;solo?:boolean})=>void;
 playing:boolean;onSeek:(seconds:number)=>void;onPlay:()=>Promise<void>;onPause:()=>void;
 onInserted:(data:Imported)=>void;saveProject:()=>Promise<boolean>;onError:(message:string)=>void;
 onConfigureFluidSynth?:()=>void;onConfigureSfizz?:()=>void;settingsOpen?:boolean;
 midiSession?:MidiRenderSession|null;onMidiSessionChange?:(value:MidiRenderSession|null)=>void;};
function clock(seconds:number){const ms=Math.max(0,Math.round(seconds*1000));return Math.floor(ms/60000)+":"+String(Math.floor(ms%60000/1000)).padStart(2,"0")+"."+String(ms%1000).padStart(3,"0");}
const names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
function pitchName(value:number){return names[(value%12+12)%12]+(Math.floor(value/12)-1);}
async function req<T>(url:string,init?:RequestInit):Promise<T>{const r=await fetch(url,init);const data=await r.json() as T&{detail?:string};if(!r.ok)throw Error(data.detail||"Stem MIDI operation failed");return data;}
export function BassMidiTool({jobId,sections,songDuration,position,selectedTrackId,engine,stemControls,onStemMix,playing,onSeek,onPlay,onPause,onInserted,saveProject,onError,onConfigureFluidSynth,onConfigureSfizz,settingsOpen,midiSession,onMidiSessionChange}:Props){
 const [trackId,setTrackId]=useState("");
 const [trackRows,setTrackRows]=useState<Track[]>([]);
 const [functionMode,setFunctionMode]=useState<"mix"|"midi">(midiSession?.jobId===jobId&&midiSession.candidates.length?"midi":"mix");
 const [regionMode,setRegionMode]=useState<"song"|"span"|"custom">("song");
 const [fromId,setFromId]=useState("");
 const [toId,setToId]=useState("");
 const [customStart,setCustomStart]=useState(0);
 const [customDuration,setCustomDuration]=useState(20);
 const persisted=midiSession?.jobId===jobId?midiSession:null;
 const [candidate,setCandidate]=useState<Candidate|null>(persisted?.candidates[persisted.index]||null);
 const [sectionQueue,setSectionQueue]=useState<Candidate[]>(persisted?.candidates||[]);
 const [sectionIndex,setSectionIndex]=useState(persisted?.index||0);
 const [acceptedSectionIds,setAcceptedSectionIds]=useState<string[]>(persisted?.acceptedSectionIds||[]);
 const [arrangementId,setArrangementId]=useState(persisted?.candidates[persisted.index]?.arrangement_id||"");
 const [rollDirty,setRollDirty]=useState(false);
 useEffect(()=>{if(rollDirty){setPreviewReady(false);engine?.clearCandidatePreview();}},[rollDirty,engine]);
 const [notes,setNotes]=useState<Note[]>([]);
 const [notePage,setNotePage]=useState(0);
 const [busy,setBusy]=useState(false);
 const [batchProgress,setBatchProgress]=useState("");
 const [message,setMessage]=useState("");
 const [error,setError]=useState("");
 const [alias,setAlias]=useState("Reinstrumented");
 const [batchPrefix,setBatchPrefix]=useState("Reinstrumented");
 const [auditionScope,setAuditionScope]=useState<"all"|"section">("all");
 const [auditionMode,setAuditionMode]=useState<"none"|"current"|"replacement"|"solo">("none");
 const [originalGain,setOriginalGain]=useState(10);
 const [packFilter,setPackFilter]=useState("all");
 const [instrument,setInstrument]=useState(persisted?.candidates[persisted.index]?.instrument||"bowed");
 const [instrumentPack,setInstrumentPack]=useState(persisted?.candidates[persisted.index]?.pack_id||"song-harbor-core");
 const [catalogue,setCatalogue]=useState<InstrumentCatalogue>({packs:[],instruments:[],fluidsynth_ready:false});
 const [installingPack,setInstallingPack]=useState(false);
 const [starters,setStarters]=useState<Starter[]>([]);
 const [curatedSfz,setCuratedSfz]=useState<CuratedSfz[]>([]);
 const [showCurated,setShowCurated]=useState(false);
 const [previewReady,setPreviewReady]=useState(false);
 const [candidateTrimDb,setCandidateTrimDb]=useState(0);
 const available=catalogue.instruments.filter(x=>packFilter==="all"||x.pack_id===packFilter).sort((a,b)=>{
   const pa=preferred(a),pb=preferred(b);
   if((pa>=0)!==(pb>=0))return pa>=0?-1:1;
   if(pa>=0&&pb>=0&&pa!==pb)return pa-pb;
   return a.name.localeCompare(b.name);
 });
 const chosenInstrument=catalogue.instruments.find(x=>x.id===instrument&&x.pack_id===instrumentPack);
 const selectedLabel=chosenInstrument?.name||"Instrument";
 const selectedPackName=catalogue.packs.find(x=>x.id===instrumentPack)?.name||"Song Harbor Core";
 const ordered=[...sections].sort((a,b)=>a.start_seconds-b.start_seconds);
 const from=ordered.find(s=>s.id===fromId)||ordered[0];
 const to=ordered.find(s=>s.id===toId)||ordered[ordered.length-1];
 const start=regionMode==="song"?0:regionMode==="span"?(from?.start_seconds||0):customStart;
 const end=regionMode==="song"?songDuration:regionMode==="span"?(to?.end_seconds||0):customStart+customDuration;
 const duration=end-start;
 const selectedTrack=trackRows.find(t=>t.track_id===trackId);
 const mix=stemControls.find(t=>t.trackId===trackId);
 const clipStart=selectedTrack?.start_seconds||0;
 const clipEnd=clipStart+(selectedTrack?.duration_seconds||songDuration);
 const inBounds=Number.isFinite(start)&&Number.isFinite(duration)&&start>=0&&duration>=.5&&duration<=600&&end<=songDuration+.005&&start>=clipStart-.005&&end<=clipEnd+.005;
 const base="/api/projects/"+jobId+"/bass-midi";
 useEffect(()=>{let live=true;
   const previous=midiSession?.jobId===jobId?midiSession:null;
   setCandidate(previous?.candidates[previous.index]||null);
   const restoredCandidate=previous?.candidates[previous.index];
   if(restoredCandidate?.section_id)setAlias(sectionAlias(restoredCandidate.section_id));
   if(restoredCandidate?.instrument)setInstrument(restoredCandidate.instrument);
   if(restoredCandidate?.pack_id)setInstrumentPack(restoredCandidate.pack_id);

   setArrangementId(previous?.candidates[previous.index]?.arrangement_id||"");
   setNotes(previous?.candidates[previous.index]?.notes||[]);
   setSectionQueue(previous?.candidates||[]);
   setSectionIndex(previous?.index||0);
   setAcceptedSectionIds(previous?.acceptedSectionIds||[]);
   setPreviewReady(Boolean(previous?.candidates[previous.index]));
   engine?.clearCandidatePreview();
   void req<{tracks:Track[]}>("/api/projects/"+jobId+"/tracks").then(data=>{
   if(!live)return;setTrackRows(data.tracks);
   setTrackId(current=>previous&&data.tracks.some(t=>t.track_id===previous.sourceTrackId)?previous.sourceTrackId:
      data.tracks.some(t=>t.track_id===selectedTrackId)?selectedTrackId!:
      data.tracks.some(t=>t.track_id===current)?current:
      (data.tracks.find(t=>t.stem_alias.toLowerCase()==="bass")||data.tracks[0])?.track_id||"");
 }).catch(e=>{if(live)setError(String(e));});return()=>{live=false;};},[jobId,selectedTrackId]);

 useEffect(()=>{let live=true;void req<{packs:CuratedSfz[]}>("/api/instruments/curated-sfz").then(data=>{if(live)setCuratedSfz(data.packs);}).catch(()=>{});return()=>{live=false;};},[]);
 useEffect(()=>{let live=true;void req<InstrumentCatalogue>("/api/instruments").then(data=>{if(live)setCatalogue(data);}).catch(e=>{if(live)setError(String(e));});void req<{starters:Starter[]}>("/api/instruments/starters").then(data=>{if(live)setStarters(data.starters);}).catch(()=>{});return()=>{live=false;};},[jobId]);
 useEffect(()=>{if(settingsOpen)return;let live=true;
   void req<InstrumentCatalogue>("/api/instruments").then(data=>{if(live)setCatalogue(data);}).catch(()=>{});
   return()=>{live=false;};
 },[settingsOpen,jobId]);
 async function installPack(file:File|undefined){
   if(!file||installingPack)return;
   setInstallingPack(true);setError("");setMessage("");
   try{
     const form=new FormData();
     form.append("file",file);form.append("pack_name",file.name.replace(/\\.sf2$/i,""));
     const response=await req<{pack_id:string;instruments:number}>("/api/instruments/sf2",{method:"POST",body:form});
     const data=await req<InstrumentCatalogue>("/api/instruments");
     setCatalogue(data);
     setPackFilter(response.pack_id);
     const first=data.instruments.find(x=>x.pack_id===response.pack_id&&x.program===42&&x.bank===0)||data.instruments.find(x=>x.pack_id===response.pack_id);
     if(first){setInstrument(first.id);setInstrumentPack(first.pack_id);}
     setPreviewReady(false);engine?.clearCandidatePreview();
     setMessage("Imported "+response.instruments+" instruments.");
   }catch(e){setError(String(e));}finally{setInstallingPack(false);}
 }
 async function installSfzPack(file:File|undefined, name?:string, curatedId?:string){
   if(!file||installingPack)return;
   setInstallingPack(true);setError("");setMessage("");
   try{
     const form=new FormData();
     form.append("file",file);
     form.append("pack_name",name||file.name.replace(/\\.zip$/i,""));
     if(curatedId)form.append("curated_id",curatedId);
     const installed=await req<{pack_id:string;instruments:number}>("/api/instruments/sfz",{method:"POST",body:form});
     const [data,remaining]=await Promise.all([
       req<InstrumentCatalogue>("/api/instruments"),
       req<{packs:CuratedSfz[]}>("/api/instruments/curated-sfz")]);
     setCatalogue(data);setCuratedSfz(remaining.packs);setPackFilter(installed.pack_id);
     const first=data.instruments.find(x=>x.pack_id===installed.pack_id);
     if(first)chooseInstrument(first.pack_id,first.id);
     setMessage("Imported "+installed.instruments+" SFZ instruments. Render saved arrangement to audition.");
   }catch(e){setError(String(e));}finally{setInstallingPack(false);}
 }
 async function installStarter(starter:Starter){
   if(installingPack)return;
   setInstallingPack(true);setMessage("");setError("");
   try{
     const outcome=await req<{pack_id:string;instruments:number}>("/api/instruments/starters/install",{
       method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({starter_id:starter.id})});
     const [library,listing]=await Promise.all([
       req<InstrumentCatalogue>("/api/instruments"),
       req<{starters:Starter[]}>("/api/instruments/starters")]);
     setCatalogue(library);setStarters(listing.starters);
     setPackFilter(outcome.pack_id);
     const selected=library.instruments.find(x=>x.pack_id===outcome.pack_id&&x.program===42&&x.bank===0)||library.instruments.find(x=>x.pack_id===outcome.pack_id);
     if(selected)chooseInstrument(selected.pack_id,selected.id);
     setMessage(starter.name+" installed · "+outcome.instruments+" presets");
   }catch(e){setError(String(e));}finally{setInstallingPack(false);}
 }
 function sectionAlias(sectionId:string){
   const section=sections.find(item=>item.id===sectionId);
   const kind=section?section.kind.replace(/[^A-Za-z0-9]/g,"").slice(0,12):"Part";
   const tag=sectionId.replace(/[^A-Za-z0-9]/g,"").slice(-8);
   return ("Reinst_"+kind+"_"+tag).slice(0,32);
 }
 function showSectionCandidate(index:number,candidates=sectionQueue,accepted=acceptedSectionIds){
   const item=candidates[index];
   if(!item)return;
   engine?.clearCandidatePreview();setAuditionMode("none");
   setCandidate(item);setNotes(item.notes);setSectionIndex(index);
   if(item.instrument)setInstrument(item.instrument);
   if(item.pack_id)setInstrumentPack(item.pack_id);
   setPreviewReady(true);setNotePage(0);
   if(item.section_id)setAlias(sectionAlias(item.section_id));
   onMidiSessionChange?.({jobId,sourceTrackId:trackId,candidates,index,acceptedSectionIds:accepted});
   setMessage("Review "+(index+1)+" of "+candidates.length+"; source gain changes only when this candidate is accepted.");
 }
 function chooseInstrument(packId:string,id:string){
   setInstrumentPack(packId);setInstrument(id);setPreviewReady(false);
   engine?.clearCandidatePreview();setMessage("");
 }
 useEffect(()=>()=>{engine?.clearCandidatePreview();},[engine,jobId]);
 function clearCandidate(){
   onMidiSessionChange?.(null);
   setArrangementId("");setCandidate(null);setSectionQueue([]);setAcceptedSectionIds([]);setNotes([]);setPreviewReady(false);setMessage("");setError("");
   engine?.clearCandidatePreview();
 }
 function edited(index:number,patch:Partial<Note>){
   setNotes(current=>current.map((note,i)=>i===index?{...note,...patch}:note));setPreviewReady(false);engine?.clearCandidatePreview();
 }
 function revert(){setNotes(candidate?.original_notes.map(n=>({...n}))||[]);setPreviewReady(false);engine?.clearCandidatePreview();setMessage("Notes restored.");}
 async function analyze(){
   if(!trackId||!inBounds||busy)return;
   setBusy(true);setError("");setMessage("");setArrangementId("");engine?.clearCandidatePreview();setPreviewReady(false);
   try{
     const data=await req<Candidate>(base+"/analyze",{method:"POST",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({track_id:trackId,start_seconds:start,duration_seconds:duration})});
     setCandidate(data);setNotes(data.notes.map(n=>({...n})));setNotePage(0);
     setMessage(data.notes.length+" notes extracted.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function render(){
   if(!candidate||busy)return;
   setBusy(true);setError("");engine?.clearCandidatePreview();setPreviewReady(false);
   try{
     const url=candidate.arrangement_id?
       "/api/projects/"+jobId+"/midi-arrangements/"+candidate.arrangement_id+"/render":
       base+"/"+candidate.candidate_id+"/render";
     if(candidate.arrangement_id&&!["sf2","sfz"].includes(chosenInstrument?.engine||""))throw Error("Select an SF2 or SFZ instrument for polyphonic rendering.");
     const body=candidate.arrangement_id?
       {revision:candidate.arrangement_revision,instrument_id:instrument,pack_id:instrumentPack}:
       {notes,instrument_id:instrument,pack_id:instrumentPack};
     const data=await req<Candidate>(url,{
       method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
     setCandidate(data);setNotes(data.notes);setPreviewReady(true);
     setMessage("Preview rendered.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function audition(mode:"current"|"replacement"|"solo"){
   if(!candidate||!previewReady||!engine?.ready||busy)return;
   setBusy(true);setError("");
   try{
     const clips=sectionQueue.length&&auditionScope==="all"?sectionQueue:[candidate];
     const first=clips[0];
     if(mode==="current"){
       engine.clearCandidatePreview();
     }else if(clips.length>1){
       await engine.loadCandidatePreviews(clips.map(item=>({
         url:base+"/"+item.candidate_id+"/audio?revision="+Date.now(),
         startSeconds:item.start_seconds
       })));
     }else{
       await engine.loadCandidatePreview(base+"/"+first.candidate_id+"/audio?revision="+Date.now(),first.start_seconds);
     }
     if(mode!=="current"){
       engine.setCandidatePreviewSolo(mode==="solo");
       engine.setCandidateOriginalMix(stemControls.find(t=>t.trackId===trackId)?.filename||"",originalGain);
       engine.setCandidatePreviewTrimDb(candidateTrimDb);
       engine.setCandidatePreviewBlend(100);
     }
     // Keep the transport position when comparing A/B. Only jump to the first
     // generated region when starting an audition from outside the selection.
     const inRange=clips.some(item=>position>=item.start_seconds&&position<item.start_seconds+item.duration_seconds);
     if(!playing&&!inRange)onSeek(first.start_seconds);
     setAuditionMode(mode);
     setMessage(mode==="current"?"A: Current mix, no unaccepted MIDI preview.":
       mode==="replacement"?"B: "+clips.length+" rendered section"+(clips.length===1?"":"s")+" mixed into the song. Original stem retained at "+originalGain+"% in those regions.":
       "Solo: "+clips.length+" rendered section"+(clips.length===1?"":"s")+", backing stems muted. Skips unselected gaps.");
     if(!playing)await onPlay();
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 useEffect(()=>{
   if(!playing||auditionMode!=="solo"||auditionScope!=="all"||sectionQueue.length<2)return;
   const ordered=[...sectionQueue].sort((a,b)=>a.start_seconds-b.start_seconds);
   for(let i=0;i<ordered.length-1;i++){
     const ending=ordered[i].start_seconds+ordered[i].duration_seconds;
     const next=ordered[i+1].start_seconds;
     if(position>=ending-.025&&position<next-.05){
       onSeek(next);
       break;
     }
   }
 },[position,playing,auditionMode,auditionScope,sectionQueue,onSeek]);
 async function addCandidateClip(item:Candidate,newAlias:string):Promise<Imported>{
   if(!/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(newAlias))throw Error("Invalid track alias");
   const response=await fetch(base+"/"+item.candidate_id+"/audio");
   if(!response.ok)throw Error("Could not retrieve rendered audio for "+(item.section_id||item.candidate_id));
   const blob=await response.blob();
   const form=new FormData();
   form.append("file",new File([blob],"Instrument-"+item.candidate_id.slice(0,8)+".wav",{type:"audio/wav"}));
   form.append("stem_alias",newAlias);
   const chosen=catalogue.instruments.find(x=>x.id===item.instrument&&x.pack_id===item.pack_id);
   form.append("display_name",(chosen?.name||selectedLabel)+" ("+newAlias+")");
   form.append("start_seconds",String(item.start_seconds));
   if(item.section_id)form.append("midi_candidate_id",item.candidate_id);
   form.append("preview_trim_db",String(candidateTrimDb));
   form.append("original_gain_percent",String(originalGain));
   if(originalGain<100)form.append("replace_source_track_id",trackId);
   return req<Imported>("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
 }
 async function insert(){
   if(!candidate||!previewReady||busy)return;
   setBusy(true);setError("");
   try{
     if(!await saveProject())throw Error("Save song before inserting a new track");
     onPause();
     const data=await addCandidateClip(candidate,alias);
     engine?.clearCandidatePreview();
     if(candidate.section_id){
       const accepted=[...new Set([...acceptedSectionIds,candidate.section_id])];
       const next=sectionQueue.findIndex((item,i)=>i!==sectionIndex&&item.section_id&&!accepted.includes(item.section_id));
       const index=next>=0?next:sectionIndex;
       setAcceptedSectionIds(accepted);
       setSectionIndex(index);
       onMidiSessionChange?.({jobId,sourceTrackId:trackId,candidates:sectionQueue,index,acceptedSectionIds:accepted});
       setMessage("Section accepted. "+(sectionQueue.length-accepted.length)+" sections remain.");
     }else{
       setMessage("New stem added. Remove it to restore the previous mix.");
     }
     onInserted(data);
   }catch(e){const detail=String(e);setError(detail);onError(detail);}finally{setBusy(false);}
 }
 async function insertAllSections(){
   if(busy||!sectionQueue.length)return;
   const pending=sectionQueue.filter(item=>item.section_id&&!acceptedSectionIds.includes(item.section_id));
   if(!pending.length)return;
   if(!window.confirm("Add "+pending.length+" rendered sections as separate reversible stems? Original bass is reduced only within each accepted section."))return;
   setBusy(true);setError("");setBatchProgress("Adding 0 of "+pending.length+" sections");
   let latest:Imported|null=null;
   const accepted=[...acceptedSectionIds];
   let completed=0;
   try{
     if(!await saveProject())throw Error("Save song before adding sections");
     onPause();
     for(const item of pending){
       setBatchProgress("Adding "+(completed+1)+" of "+pending.length+" sections");
       latest=await addCandidateClip(item,sectionAlias(item.section_id!));
       accepted.push(item.section_id!);
       completed++;
       onMidiSessionChange?.({jobId,sourceTrackId:trackId,candidates:sectionQueue,index:sectionIndex,acceptedSectionIds:[...accepted]});
     }
     setAcceptedSectionIds([...accepted]);
     setMessage("Added "+completed+" section stems. Other song regions remain unchanged.");
   }catch(e){
     const detail="Added "+completed+" of "+pending.length+" before stopping: "+String(e);
     setError(detail);onError(detail);
     setAcceptedSectionIds([...accepted]);
   }finally{
     setBatchProgress("");setBusy(false);
     if(latest)onInserted(latest);
   }
 }
 async function removeImportedStem(){
   if(!selectedTrack?.imported||busy)return;
   const name=selectedTrack.display_name;
   if(!window.confirm('Remove imported stem "'+name+'"? Song Harbor will archive its files and restore any original-stem regions it replaced.'))return;
   setBusy(true);setError("");
   try{
     onPause();
     const removed=await req<Imported>("/api/projects/"+jobId+"/tracks/"+encodeURIComponent(selectedTrack.track_id),{
       method:"DELETE",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({expected_alias:selectedTrack.stem_alias})});
     engine?.clearCandidatePreview();
     onMidiSessionChange?.(null);
     setSectionQueue([]);setAcceptedSectionIds([]);setCandidate(null);
     onInserted(removed);
   }catch(e){const detail=String(e);setError(detail);onError(detail);}
   finally{setBusy(false);}
 }
 async function useArrangement(asset:Arrangement,sectionIds:string[]){
   if(asset.source.track_id!==trackId)throw Error("Arrangement belongs to a different stem.");
   if(busy)return;
   setBusy(true);setError("");setPreviewReady(false);engine?.clearCandidatePreview();
   try{
     if(!["sf2","sfz"].includes(chosenInstrument?.engine||""))throw Error("Select an SF2 or SFZ instrument to render a polyphonic arrangement.");
     const root="/api/projects/"+jobId+"/midi-arrangements/"+asset.asset_id;
     const data=await req<Candidate|{candidates:Candidate[]}>(
       root+(sectionIds.length?"/render-sections":"/render"),{
       method:"POST",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({revision:asset.revision,instrument_id:instrument,pack_id:instrumentPack,
        ...(sectionIds.length?{section_ids:sectionIds}:{})})});
     setArrangementId(asset.asset_id);
     if("candidates" in data){
       setSectionQueue(data.candidates);setAcceptedSectionIds([]);setSectionIndex(0);
       showSectionCandidate(0,data.candidates,[]);
     }else{
       setSectionQueue([]);setAcceptedSectionIds([]);onMidiSessionChange?.(null);
       setCandidate(data);setNotes(data.notes);setNotePage(0);setPreviewReady(true);
       setMessage("Polyphonic candidate rendered from saved arrangement r"+asset.revision+". Original stem unchanged.");
     }
   }finally{setBusy(false);}
 }
 async function saveArrangement(){
   if(!candidate||busy)return;
   setBusy(true);setError("");
   try{
     // Persist current note edits first, never infer notes from an old render.
     const saved=await req<Candidate>(base+"/"+candidate.candidate_id+"/notes",{
       method:"PUT",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({notes,instrument_id:instrument,pack_id:instrumentPack})});
     const asset=await req<{asset_id:string;revision:number}>("/api/projects/"+jobId+"/midi-arrangements/from-candidate",{
       method:"POST",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({candidate_id:candidate.candidate_id})});
     setCandidate(saved);setNotes(saved.notes);setArrangementId(asset.asset_id);
     setPreviewReady(false);engine?.clearCandidatePreview();
     setMessage("Arrangement saved. Edit notes in the piano roll; render only the saved revision.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function midi(){
   if(!candidate||busy)return;
   setBusy(true);setError("");
   try{
     const saved=await req<Candidate>(base+"/"+candidate.candidate_id+"/notes",{
       method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({notes,instrument_id:instrument,pack_id:instrumentPack})});
     setCandidate(saved);setNotes(saved.notes);setPreviewReady(false);
     engine?.clearCandidatePreview();
     const a=document.createElement("a");a.href=base+"/"+candidate.candidate_id+"/midi";
     a.download="Stem-to-MIDI.mid";document.body.appendChild(a);a.click();a.remove();
     setMessage("MIDI saved and exported.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 function addNote(){
   const t=Math.max(0,Math.min(candidate?.duration_seconds||1,notes.length?notes[notes.length-1].end:0));
   const end=Math.min(candidate?.duration_seconds||1,t+.5);
   if(end-t<.06){setError("No space for another note near the end.");return;}
   setNotes(current=>[...current,{pitch:40,start:t,end,velocity:85}]);setPreviewReady(false);engine?.clearCandidatePreview();
 }
 function transpose(semitones:number){setNotes(current=>current.map(n=>({...n,pitch:Math.min(76,Math.max(28,n.pitch+semitones))})));setPreviewReady(false);engine?.clearCandidatePreview();}
 return <div className="song-midi-tool song-stem-hub">
   <div className="song-stem-hub-header">
     <label className="song-stem-hub-source" title="Active stem">
       <span className="sr-only">Stem</span>
       <select aria-label="Stem" value={trackId} onChange={e=>{if(rollDirty&&!window.confirm("Discard unsaved MIDI arrangement edits before switching stems?"))return;setRollDirty(false);onMidiSessionChange?.(null);setSectionQueue([]);setAcceptedSectionIds([]);setTrackId(e.target.value);setArrangementId("");setCandidate(null);setNotes([]);setPreviewReady(false);engine?.clearCandidatePreview();}}>
         {trackRows.map(t=><option key={t.track_id} value={t.track_id}>{t.display_name}</option>)}
       </select>
     </label>
     {selectedTrack?.imported&&<button type="button" title="Remove imported stem. Archives audio and restores source replacement regions" aria-label="Remove imported stem" disabled={busy} onClick={()=>void removeImportedStem()}>⌫</button>}
     <div className="song-stem-hub-tabs" role="group" aria-label="Stem function">
       <button type="button" aria-pressed={functionMode==="mix"} title="Stem mix controls" onClick={()=>setFunctionMode("mix")}>◉ <span>Mix</span></button>
       <button type="button" aria-pressed={functionMode==="midi"} title="Stem to MIDI" onClick={()=>setFunctionMode("midi")}>♮ <span>MIDI</span></button>
     </div>
   </div>
   {functionMode==="mix"&&<div className="song-stem-hub-mix">
     {mix?<div className="song-stem-hub-mix-row">
       <label title="Base stem gain">Gain <input type="range" min="0" max="100" step="1" value={mix.gain} onChange={e=>onStemMix(mix.filename,{gain:Number(e.target.value)})}/><output>{mix.gain}%</output></label>
       <button type="button" className={mix.mute?"is-muted":""} aria-pressed={mix.mute} title="Mute" onClick={()=>onStemMix(mix.filename,{mute:!mix.mute})}>M</button>
       <button type="button" className={mix.solo?"is-solo":""} aria-pressed={mix.solo} title="Solo" onClick={()=>onStemMix(mix.filename,{solo:!mix.solo})}>S</button>
       <button type="button" title="Reset gain, mute and solo" onClick={()=>onStemMix(mix.filename,{gain:100,mute:false,solo:false})}>↺</button>
     </div>:<small role="status">Choose a stem to edit its base mix.</small>}
     <button type="button" className="song-stem-hub-next" onClick={()=>setFunctionMode("midi")}>♮ Stem → MIDI</button>
   </div>}
   {functionMode==="midi"&&<>
     <div className="song-midi-region">
       <label title="Selection scope">Region <select aria-label="MIDI extraction region" value={regionMode} onChange={e=>{clearCandidate();setRegionMode(e.target.value as "song"|"span"|"custom");}}>
         <option value="song">Whole song</option>
         <option value="span">Section → section</option>
         <option value="custom">Custom</option>
       </select></label>
       {regionMode==="span"&&<div className="song-midi-span">
         <label>From <select aria-label="From section" value={from?.id||""} onChange={e=>{clearCandidate();setFromId(e.target.value);}}>{ordered.map(x=><option key={x.id} value={x.id}>{x.kind}{x.number?" "+x.number:""} · {clock(x.start_seconds)}</option>)}</select></label>
         <label>To <select aria-label="To section" value={to?.id||""} onChange={e=>{clearCandidate();setToId(e.target.value);}}>{ordered.map(x=><option key={x.id} value={x.id}>{x.kind}{x.number?" "+x.number:""} · {clock(x.end_seconds)}</option>)}</select></label>
       </div>}
       {regionMode==="custom"&&<div className="song-midi-span">
         <label>Start <input aria-label="MIDI region start seconds" type="number" min="0" step=".1" value={customStart} onChange={e=>{clearCandidate();setCustomStart(Number(e.target.value));}}/></label>
         <label>Length <input aria-label="MIDI region length seconds" type="number" min=".5" max="600" step=".1" value={customDuration} onChange={e=>{clearCandidate();setCustomDuration(Number(e.target.value));}}/></label>
         <button type="button" title="Start at current playhead" onClick={()=>{clearCandidate();setCustomStart(Math.max(0,Math.min(position,songDuration-customDuration)));}}>⌖</button>
       </div>}
       <div className="song-midi-region-footer">
         <span className="timecode">{clock(Math.max(0,start))} – {clock(Math.max(0,end))}</span>
         {!inBounds&&<small role="alert">{regionMode==="span"&&!ordered.length?"No sections":"Range must be within the stem and ≤10 min"}</small>}
         <button type="button" disabled={!trackId||!inBounds||busy} title="Transcribe selected range on CPU" onClick={()=>void analyze()}>{busy?"…":"♮ Extract"}</button>
       </div>
     </div>
         <div className="song-instrument-selectors">
           <label title="Choose instrument">Instrument <select aria-label="Instrument" value={instrumentPack+"::"+instrument} onChange={e=>{const [pack,id]=e.target.value.split("::");chooseInstrument(pack,id);}}>{available.map(x=><option key={x.pack_id+"::"+x.id} value={x.pack_id+"::"+x.id}>{preferred(x)>=0?"★ ":""}{x.name}{packFilter==="all"?" · "+(catalogue.packs.find(p=>p.id===x.pack_id)?.name||x.pack_id):""}</option>)}</select></label>
           <label title="Filter instruments by pack">Pack <select aria-label="Instrument pack" value={packFilter} onChange={e=>{const filter=e.target.value;setPackFilter(filter);const options=catalogue.instruments.filter(x=>filter==="all"||x.pack_id===filter);if(!options.some(x=>x.id===instrument&&x.pack_id===instrumentPack)){const first=options[0];if(first)chooseInstrument(first.pack_id,first.id);}}}><option value="all">All packs</option>{catalogue.packs.map(pack=><option key={pack.id} value={pack.id}>{pack.name}</option>)}</select></label>
         </div>
         <div className="song-instrument-import">
           {starters.map(starter=><button key={starter.id} type="button" title={starter.description+(starter.installed?" · Already installed":" · Download verified SoundFont from publisher")} disabled={installingPack||starter.installed} onClick={()=>void installStarter(starter)}>{starter.installed?"✓ "+starter.name:"↓ "+starter.name}</button>)}
           <label title="Import an existing local SF2 SoundFont (not a download)">＋ Import SF2<input type="file" accept=".sf2" disabled={installingPack} aria-label="Import SF2 instrument pack" onChange={e=>{void installPack(e.target.files?.[0]);e.target.value="";}}/></label>
           <label title="Import a downloaded SFZ instrument ZIP from your computer">＋ Import SFZ<input type="file" accept=".zip" disabled={installingPack} aria-label="Import SFZ ZIP instrument pack" onChange={e=>{void installSfzPack(e.target.files?.[0]);e.target.value="";}}/></label>
           <button type="button" aria-expanded={showCurated} onClick={()=>setShowCurated(v=>!v)} title="Browse recommended SFZ packs with publisher downloads and explicit local import">♫ Browse instrument library {showCurated?"▴":"▾"}</button>
           {chosenInstrument?.engine==="sfz"&&!catalogue.sfizz_ready&&<span role="status" className="song-midi-fluid-setup">sfizz renderer required <button type="button" disabled={!onConfigureSfizz} onClick={onConfigureSfizz}>Configure sfizz</button></span>}
           {chosenInstrument?.engine==="sf2"&&!catalogue.fluidsynth_ready&&<span className="song-midi-fluid-setup" role="status">FluidSynth required <button type="button" onClick={onConfigureFluidSynth} disabled={!onConfigureFluidSynth} title="Open FluidSynth settings to browse, detect and verify the executable">Configure FluidSynth</button></span>}
           <small title="Current source pack">{selectedPackName}</small>
         </div>
     {showCurated&&<div className="song-midi-curated" aria-label="Recommended SFZ instrument packs">
       <small>Recommended free instrument packs. Downloads open the publisher's site; ZIP import is local and explicit. Compatibility is not yet verified.</small>
       {curatedSfz.length===0&&<small>All curated SFZ packs have been imported. Installed instruments remain in the Pack selector.</small>}
       {curatedSfz.map(pack=><div className="song-midi-curated-row" key={pack.id}>
         <span title={pack.description}><strong>{pack.name}</strong> <small>{pack.family} · {pack.fit} · {pack.license}{pack.approx_mb?" · ~"+pack.approx_mb+" MB":""}</small></span>
         <small>{pack.description}</small>
         <a href={pack.download_url} target="_blank" rel="noopener noreferrer" title={"Publisher download: "+pack.source}>Get ZIP</a>
         <label title={"Import the downloaded ZIP for "+pack.name}>Import ZIP
           <input type="file" accept=".zip" disabled={installingPack} aria-label={"Import "+pack.name+" ZIP"}
            onChange={e=>{void installSfzPack(e.target.files?.[0],pack.name,pack.id);e.target.value="";}}/>
         </label>
         <a href={pack.source_page} target="_blank" rel="noopener noreferrer" title={"Publisher and licensing information for "+pack.name}>Source</a>
       </div>)}
     </div>}
     <MidiPianoRoll jobId={jobId} sourceTrackId={trackId} requestedAssetId={arrangementId}
       sections={sections} instruments={catalogue.instruments} selectedInstrument={instrumentPack+"::"+instrument}
       onInstrumentChange={key=>{const [pack,id]=key.split("::");setPackFilter("all");chooseInstrument(pack,id);}}
       onDirtyChange={setRollDirty} onUse={useArrangement} onError={onError}/>
     {candidate&&!candidate.arrangement_id&&!arrangementId&&<>
       <div className="song-midi-controls song-midi-edit-toolbar">
         <strong>{notes.length} notes</strong>
         <button type="button" title="Revert note edits" disabled={busy} onClick={revert}>↺</button>
         <button type="button" title="Transpose octave down" disabled={busy} onClick={()=>transpose(-12)}>−12</button>
         <button type="button" title="Transpose octave up" disabled={busy} onClick={()=>transpose(12)}>+12</button>
         <button type="button" title="Add note" disabled={busy} onClick={addNote}>＋</button>
         <button type="button" title="Save editable arrangement in project (independent of rendered audio)" disabled={busy} onClick={()=>void saveArrangement()}>Save arrangement</button>
         <button type="button" title="Save edited MIDI and export .mid" disabled={busy} onClick={()=>void midi()}>⇩ MIDI</button>
         {arrangementId&&<small title={"Persistent MIDI arrangement "+arrangementId}>Saved asset · {arrangementId.slice(0,8)}</small>}
       </div>
       <details className="song-midi-edit-details">
         <summary>Notes · {notes.length} <span className="timecode">{clock(candidate.start_seconds)}–{clock(candidate.start_seconds+candidate.duration_seconds)}</span></summary>
         <div className="song-midi-note-pagination"><button type="button" disabled={notePage===0} onClick={()=>setNotePage(p=>Math.max(0,p-1))} title="Previous notes">‹</button><span>{notes.length?notePage*40+1:0}–{Math.min(notes.length,(notePage+1)*40)} / {notes.length}</span><button type="button" disabled={(notePage+1)*40>=notes.length} onClick={()=>setNotePage(p=>p+1)} title="Next notes">›</button></div>
         <div className="song-midi-note-list" aria-label="Editable extracted MIDI notes">
           {notes.slice(notePage*40,(notePage+1)*40).map((note,pageIndex)=>{const i=notePage*40+pageIndex;return <div key={i} className="song-midi-note">
             <span>{i+1}</span>
             <label>Pitch <select aria-label={"Note "+(i+1)+" pitch"} value={note.pitch} onChange={e=>edited(i,{pitch:Number(e.target.value)})}>{Array.from({length:49},(_,j)=>j+28).map(p=><option key={p} value={p}>{pitchName(p)}</option>)}</select></label>
             <label>Start <input aria-label={"Note "+(i+1)+" start"} type="number" min="0" max={candidate.duration_seconds} step=".01" value={note.start} onChange={e=>edited(i,{start:Number(e.target.value)})}/></label>
             <label>End <input aria-label={"Note "+(i+1)+" end"} type="number" min="0" max={candidate.duration_seconds} step=".01" value={note.end} onChange={e=>edited(i,{end:Number(e.target.value)})}/></label>
             <button type="button" aria-label={"Remove note "+(i+1)} onClick={()=>{setNotes(current=>current.filter((_,j)=>j!==i));setPreviewReady(false);engine?.clearCandidatePreview();}}>×</button>
           </div>;})}
         </div>
       </details>
     </>}
     {candidate&&<>
       <div className="song-midi-render">
         {sectionQueue.length>0&&<div className="song-midi-section-batch" role="status">
           <strong>{sectionQueue.length} sections rendered</strong>
           <span>{acceptedSectionIds.length} accepted, {sectionQueue.length-acceptedSectionIds.length} pending</span>
           <button type="button" title="Add every remaining rendered section as an independent, reversible stem"
             disabled={busy||acceptedSectionIds.length>=sectionQueue.length}
             onClick={()=>void insertAllSections()}>✓ Add all {sectionQueue.length-acceptedSectionIds.length} sections</button>
           {batchProgress&&<small aria-live="polite">{batchProgress}</small>}
         </div>}
         {sectionQueue.length>0&&<div className="song-midi-section-review">
           <button type="button" title="Previous rendered section" aria-label="Previous rendered section" disabled={busy||sectionIndex===0}
            onClick={()=>showSectionCandidate(sectionIndex-1)}>←</button>
           <span>Section {sectionIndex+1}/{sectionQueue.length} · {candidate?.section_id?sections.find(x=>x.id===candidate.section_id)?.kind||"Section":""}
             {candidate?.section_id&&acceptedSectionIds.includes(candidate.section_id)?" · Accepted":""}</span>
           <button type="button" title="Next rendered section" aria-label="Next rendered section" disabled={busy||sectionIndex===sectionQueue.length-1}
            onClick={()=>showSectionCandidate(sectionIndex+1)}>→</button>
           <small>Each accepted section has its own source-replacement mask.</small>
         </div>}
         <div className="song-midi-controls">
           {arrangementId?<small title="Render the saved arrangement above to ensure the versioned MIDI notes are authoritative">Render via arrangement above</small>:<button type="button" title="Render selected instrument preview" disabled={busy||!notes.length} onClick={()=>void render()}>◈ Render</button>}
           {sectionQueue.length>1&&<label title="Audition the complete rendered batch or only the review selection">Scope <select aria-label="Preview scope" value={auditionScope} onChange={e=>{setAuditionScope(e.target.value as "all"|"section");engine?.clearCandidatePreview();setAuditionMode("none");}}><option value="all">All {sectionQueue.length}</option><option value="section">This section</option></select></label>}
           <button type="button" aria-pressed={auditionMode==="solo"} title="Preview only the rendered MIDI clips; skip gaps between selected sections" disabled={!previewReady||busy} onClick={()=>void audition("solo")}>▶ Solo</button>
           <button type="button" aria-pressed={auditionMode==="current"} title="A: Play current song without unaccepted MIDI preview" disabled={!previewReady||busy} onClick={()=>void audition("current")}>A: Current</button>
           <button type="button" aria-pressed={auditionMode==="replacement"} title="B: Play rendered MIDI clips with backing instruments and region-scoped original gain" disabled={!previewReady||busy} onClick={()=>void audition("replacement")}>B: MIDI</button>
           <label className="song-original-mix" title="Retained original stem gain inside this region; 0% replaces, 100% layers">Original <input type="range" min="0" max="100" step="1" aria-label="Original stem retained gain" value={originalGain} onChange={e=>{const value=Number(e.target.value);setOriginalGain(value);engine?.setCandidateOriginalMix(stemControls.find(t=>t.trackId===trackId)?.filename||"",value);}}/><output>{originalGain}%</output></label>
           <div className="song-candidate-volume" title="Candidate level, also applied when adding the track">◖ <input type="range" aria-label="Candidate volume trim" min="-12" max="9" step="1" value={candidateTrimDb} onChange={e=>{const db=Number(e.target.value);setCandidateTrimDb(db);engine?.setCandidatePreviewTrimDb(db);}}/><output>{candidateTrimDb>0?"+":""}{candidateTrimDb} dB</output><button type="button" title="Reset candidate volume" aria-label="Reset candidate volume" onClick={()=>{setCandidateTrimDb(0);engine?.setCandidatePreviewTrimDb(0);}}>↺</button></div>
         </div>
         {auditionMode!=="none"&&<div className="song-midi-audition-status" role="status">{
           auditionMode==="current"?"A: Current mix (without unaccepted MIDI preview)":
           auditionMode==="replacement"?"B: Rendered MIDI in selected sections, current backing mix":
           "Solo: Rendered MIDI only"+(sectionQueue.length>1&&auditionScope==="all"?" (all sections)":"")
         }</div>}
         {previewReady&&<div className="song-midi-accept">
           <input aria-label="New stem alias" title="New stem alias" maxLength={32} value={alias} onChange={e=>setAlias(e.target.value)}/>
           <button type="button" disabled={busy||Boolean(candidate.section_id&&acceptedSectionIds.includes(candidate.section_id))} title="Add only the currently reviewed section. To add all rendered sections, use Add all sections." onClick={()=>void insert()}>✓ {sectionQueue.length?"Add this section":"Add stem"}</button>
         </div>}
       </div>
     </>}
   </>}
   {message&&<small role="status" className="song-midi-status">{message}</small>}
   {error&&<div role="alert" className="song-midi-error">{error}{/fluidsynth/i.test(error)&&<button type="button" onClick={onConfigureFluidSynth} disabled={!onConfigureFluidSynth}>Configure FluidSynth</button>}{/sfizz|sfz renderer/i.test(error)&&<button type="button" onClick={onConfigureSfizz} disabled={!onConfigureSfizz}>Configure sfizz</button>}</div>}
 </div>;
}
