import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SharedClockAudition} from "./SharedClockAudition";

type Note={pitch:number;start:number;end:number;velocity:number};
type Candidate={candidate_id:string;start_seconds:number;duration_seconds:number;notes:Note[];original_notes:Note[];rendered?:boolean;method:string};
type Track={track_id:string;stem_alias:string;display_name:string;start_seconds?:number;duration_seconds?:number};
type InstrumentPack={id:string;name:string;engine:string;source:string};
type InstrumentChoice={id:string;name:string;pack_id:string;engine:string;program:number;bank:number};
type InstrumentCatalogue={packs:InstrumentPack[];instruments:InstrumentChoice[];fluidsynth_ready:boolean};
// General MIDI programs, zero-based. Favorites prioritize Infra Choir's
// gothic/industrial/orchestral palette without hiding any other presets.
const STARTER_PROGRAMS=[42,43,44,45,48,49,50,52,54,55,57,60,61,62,30,34,38,89];
const preferred=(x:InstrumentChoice)=>x.engine==="sf2"&&x.bank===0?STARTER_PROGRAMS.indexOf(x.program):-1;

type Starter={id:string;name:string;description:string;source_page:string;installed:boolean};
type Imported={project:unknown;job:unknown};
type Props={jobId:string;sections:SongSection[];songDuration:number;position:number;selectedTrackId?:string;engine:SharedClockAudition|null;
 stemControls:{filename:string;trackId?:string;gain:number;mute:boolean;solo:boolean;name:string}[];
 onStemMix:(filename:string,changes:{gain?:number;mute?:boolean;solo?:boolean})=>void;
 playing:boolean;onSeek:(seconds:number)=>void;onPlay:()=>Promise<void>;onPause:()=>void;
 onInserted:(data:Imported)=>void;saveProject:()=>Promise<boolean>;onError:(message:string)=>void};
function clock(seconds:number){const ms=Math.max(0,Math.round(seconds*1000));return Math.floor(ms/60000)+":"+String(Math.floor(ms%60000/1000)).padStart(2,"0")+"."+String(ms%1000).padStart(3,"0");}
const names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
function pitchName(value:number){return names[(value%12+12)%12]+(Math.floor(value/12)-1);}
async function req<T>(url:string,init?:RequestInit):Promise<T>{const r=await fetch(url,init);const data=await r.json() as T&{detail?:string};if(!r.ok)throw Error(data.detail||"Stem MIDI operation failed");return data;}
export function BassMidiTool({jobId,sections,songDuration,position,selectedTrackId,engine,stemControls,onStemMix,playing,onSeek,onPlay,onPause,onInserted,saveProject,onError}:Props){
 const [trackId,setTrackId]=useState("");
 const [trackRows,setTrackRows]=useState<Track[]>([]);
 const [functionMode,setFunctionMode]=useState<"mix"|"midi">("mix");
 const [regionMode,setRegionMode]=useState<"song"|"span"|"custom">("song");
 const [fromId,setFromId]=useState("");
 const [toId,setToId]=useState("");
 const [customStart,setCustomStart]=useState(0);
 const [customDuration,setCustomDuration]=useState(20);
 const [candidate,setCandidate]=useState<Candidate|null>(null);
 const [notes,setNotes]=useState<Note[]>([]);
 const [notePage,setNotePage]=useState(0);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const [error,setError]=useState("");
 const [alias,setAlias]=useState("Reinstrumented");
 const [acceptMode,setAcceptMode]=useState<"replace"|"layer">("replace");
 const [packFilter,setPackFilter]=useState("all");
 const [instrument,setInstrument]=useState("bowed");
 const [instrumentPack,setInstrumentPack]=useState("song-harbor-core");
 const [catalogue,setCatalogue]=useState<InstrumentCatalogue>({packs:[],instruments:[],fluidsynth_ready:false});
 const [installingPack,setInstallingPack]=useState(false);
 const [starters,setStarters]=useState<Starter[]>([]);
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
 useEffect(()=>{let live=true;setCandidate(null);setNotes([]);setPreviewReady(false);engine?.clearCandidatePreview();
   void req<{tracks:Track[]}>("/api/projects/"+jobId+"/tracks").then(data=>{
   if(!live)return;setTrackRows(data.tracks);
   setTrackId(current=>data.tracks.some(t=>t.track_id===selectedTrackId)?selectedTrackId!:
      data.tracks.some(t=>t.track_id===current)?current:
      (data.tracks.find(t=>t.stem_alias.toLowerCase()==="bass")||data.tracks[0])?.track_id||"");
 }).catch(e=>{if(live)setError(String(e));});return()=>{live=false;};},[jobId,selectedTrackId]);

 useEffect(()=>{let live=true;void req<InstrumentCatalogue>("/api/instruments").then(data=>{if(live)setCatalogue(data);}).catch(e=>{if(live)setError(String(e));});void req<{starters:Starter[]}>("/api/instruments/starters").then(data=>{if(live)setStarters(data.starters);}).catch(()=>{});return()=>{live=false;};},[jobId]);
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
 function chooseInstrument(packId:string,id:string){
   setInstrumentPack(packId);setInstrument(id);setPreviewReady(false);
   engine?.clearCandidatePreview();setMessage("");
 }
 useEffect(()=>()=>{engine?.clearCandidatePreview();},[engine,jobId]);
 function clearCandidate(){
   setCandidate(null);setNotes([]);setPreviewReady(false);setMessage("");setError("");
   engine?.clearCandidatePreview();
 }
 function edited(index:number,patch:Partial<Note>){
   setNotes(current=>current.map((note,i)=>i===index?{...note,...patch}:note));setPreviewReady(false);engine?.clearCandidatePreview();
 }
 function revert(){setNotes(candidate?.original_notes.map(n=>({...n}))||[]);setPreviewReady(false);engine?.clearCandidatePreview();setMessage("Notes restored.");}
 async function analyze(){
   if(!trackId||!inBounds||busy)return;
   setBusy(true);setError("");setMessage("");engine?.clearCandidatePreview();setPreviewReady(false);
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
     const data=await req<Candidate>(base+"/"+candidate.candidate_id+"/render",{
       method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({notes,instrument_id:instrument,pack_id:instrumentPack})});
     setCandidate(data);setNotes(data.notes);setPreviewReady(true);
     setMessage("Preview rendered.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function audition(solo:boolean){
   if(!candidate||!previewReady||!engine?.ready)return;
   setBusy(true);setError("");
   try{
     await engine.loadCandidatePreview(base+"/"+candidate.candidate_id+"/audio?revision="+Date.now(),candidate.start_seconds);
     engine.setCandidatePreviewSolo(solo);
     engine.setCandidatePreviewBlend(solo?100:60);
     engine.setCandidatePreviewTrimDb(candidateTrimDb);
     onSeek(candidate.start_seconds);
     if(!playing)await onPlay();
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function insert(){
   if(!candidate||!previewReady||busy)return;
   if(!/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(alias)){setError("Invalid track alias");return;}
   setBusy(true);setError("");
   try{
     if(!await saveProject())throw Error("Save song before inserting a new track");
     onPause();
     const response=await fetch(base+"/"+candidate.candidate_id+"/audio");
     if(!response.ok)throw Error("Could not retrieve rendered bowed-string audio");
     const blob=await response.blob();
     const form=new FormData();
     form.append("file",new File([blob],"Instrument-"+candidate.candidate_id.slice(0,8)+".wav",{type:"audio/wav"}));
     form.append("stem_alias",alias);
     form.append("display_name",selectedLabel+" ("+alias+")");
     form.append("start_seconds",String(candidate.start_seconds));
     form.append("preview_trim_db",String(candidateTrimDb));
     form.append("accept_mode",acceptMode);
     if(acceptMode==="replace")form.append("replace_source_track_id",trackId);
     const data=await req<Imported>("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
     engine?.clearCandidatePreview();
     setMessage("New track added. Source preserved; remove the imported track to undo.");
     onInserted(data);
   }catch(e){const detail=String(e);setError(detail);onError(detail);}finally{setBusy(false);}
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
       <select aria-label="Stem" value={trackId} onChange={e=>{setTrackId(e.target.value);setCandidate(null);setNotes([]);setPreviewReady(false);engine?.clearCandidatePreview();}}>
         {trackRows.map(t=><option key={t.track_id} value={t.track_id}>{t.display_name}</option>)}
       </select>
     </label>
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
     {candidate&&<>
       <div className="song-midi-controls song-midi-edit-toolbar">
         <strong>{notes.length} notes</strong>
         <button type="button" title="Revert note edits" disabled={busy} onClick={revert}>↺</button>
         <button type="button" title="Transpose octave down" disabled={busy} onClick={()=>transpose(-12)}>−12</button>
         <button type="button" title="Transpose octave up" disabled={busy} onClick={()=>transpose(12)}>+12</button>
         <button type="button" title="Add note" disabled={busy} onClick={addNote}>＋</button>
         <button type="button" title="Save edited MIDI and export .mid" disabled={busy} onClick={()=>void midi()}>⇩ MIDI</button>
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
       <div className="song-midi-render">
         <div className="song-instrument-selectors">
           <label title="Choose instrument">Instrument <select aria-label="Instrument" value={instrumentPack+"::"+instrument} onChange={e=>{const [pack,id]=e.target.value.split("::");chooseInstrument(pack,id);}}>{available.map(x=><option key={x.pack_id+"::"+x.id} value={x.pack_id+"::"+x.id}>{preferred(x)>=0?"★ ":""}{x.name}{packFilter==="all"?" · "+(catalogue.packs.find(p=>p.id===x.pack_id)?.name||x.pack_id):""}</option>)}</select></label>
           <label title="Filter instruments by pack">Pack <select aria-label="Instrument pack" value={packFilter} onChange={e=>{const filter=e.target.value;setPackFilter(filter);const options=catalogue.instruments.filter(x=>filter==="all"||x.pack_id===filter);if(!options.some(x=>x.id===instrument&&x.pack_id===instrumentPack)){const first=options[0];if(first)chooseInstrument(first.pack_id,first.id);}}}><option value="all">All packs</option>{catalogue.packs.map(pack=><option key={pack.id} value={pack.id}>{pack.name}</option>)}</select></label>
         </div>
         <div className="song-instrument-import">
           {starters.filter(x=>!x.installed).map(starter=><button key={starter.id} type="button" title={starter.description+" · download from author"} disabled={installingPack} onClick={()=>void installStarter(starter)}>{installingPack?"…":"↓ Starter GM"}</button>)}
           <label title="Install a local SF2 SoundFont">＋ SF2<input type="file" accept=".sf2" disabled={installingPack} aria-label="Import SF2 instrument pack" onChange={e=>{void installPack(e.target.files?.[0]);e.target.value="";}}/></label>
           {chosenInstrument?.engine==="sf2"&&!catalogue.fluidsynth_ready&&<small role="status" title="Install FluidSynth and configure SONG_HARBOR_FLUIDSYNTH or put it on PATH">FluidSynth required for SF2 render</small>}
           <small title="Current source pack">{selectedPackName}</small>
         </div>
         <div className="song-midi-controls">
           <button type="button" title="Render selected instrument preview" disabled={busy||!notes.length} onClick={()=>void render()}>◈ Render</button>
           <button type="button" title="Solo candidate" disabled={!previewReady||busy} onClick={()=>void audition(true)}>▶ Solo</button>
           <button type="button" title="Audition in song" disabled={!previewReady||busy} onClick={()=>void audition(false)}>◉ A/B</button>
           <div className="song-candidate-volume" title="Candidate level, also applied when adding the track">◖ <input type="range" aria-label="Candidate volume trim" min="-12" max="9" step="1" value={candidateTrimDb} onChange={e=>{const db=Number(e.target.value);setCandidateTrimDb(db);engine?.setCandidatePreviewTrimDb(db);}}/><output>{candidateTrimDb>0?"+":""}{candidateTrimDb} dB</output><button type="button" title="Reset candidate volume" aria-label="Reset candidate volume" onClick={()=>{setCandidateTrimDb(0);engine?.setCandidatePreviewTrimDb(0);}}>↺</button></div>
         </div>
         {previewReady&&<div className="song-midi-accept">
           <input aria-label="New stem alias" title="New stem alias" maxLength={32} value={alias} onChange={e=>setAlias(e.target.value)}/>
           <select aria-label="Acceptance mode" title="Replace mutes the source only in this region" value={acceptMode} onChange={e=>setAcceptMode(e.target.value as "replace"|"layer")}><option value="replace">Replace</option><option value="layer">Layer</option></select>
           <button type="button" disabled={busy} title="Add candidate as a removable new stem" onClick={()=>void insert()}>✓ Add stem</button>
         </div>}
       </div>
     </>}
   </>}
   {message&&<small role="status" className="song-midi-status">{message}</small>}
   {error&&<small role="alert" className="song-midi-error">{error}</small>}
 </div>;
}
