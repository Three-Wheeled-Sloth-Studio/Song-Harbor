import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SharedClockAudition} from "./SharedClockAudition";

type Note={pitch:number;start:number;end:number;velocity:number};
type Candidate={candidate_id:string;start_seconds:number;duration_seconds:number;notes:Note[];original_notes:Note[];rendered?:boolean;method:string};
type Track={track_id:string;stem_alias:string;display_name:string};
type Imported={project:unknown;job:unknown};
type Props={jobId:string;sections:SongSection[];songDuration:number;position:number;engine:SharedClockAudition|null;
 playing:boolean;onSeek:(seconds:number)=>void;onPlay:()=>Promise<void>;onPause:()=>void;
 onInserted:(data:Imported)=>void;saveProject:()=>Promise<boolean>;onError:(message:string)=>void};
function clock(seconds:number){const ms=Math.max(0,Math.round(seconds*1000));return Math.floor(ms/60000)+":"+String(Math.floor(ms%60000/1000)).padStart(2,"0")+"."+String(ms%1000).padStart(3,"0");}
const names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
function pitchName(value:number){return names[(value%12+12)%12]+(Math.floor(value/12)-1);}
async function req<T>(url:string,init?:RequestInit):Promise<T>{const r=await fetch(url,init);const data=await r.json() as T&{detail?:string};if(!r.ok)throw Error(data.detail||"Bass MIDI operation failed");return data;}
export function BassMidiTool({jobId,sections,songDuration,position,engine,playing,onSeek,onPlay,onPause,onInserted,saveProject,onError}:Props){
 const [trackId,setTrackId]=useState("");
 const [bassExists,setBassExists]=useState(true);
 const [sectionId,setSectionId]=useState("custom");
 const [customStart,setCustomStart]=useState(0);
 const [customDuration,setCustomDuration]=useState(20);
 const [candidate,setCandidate]=useState<Candidate|null>(null);
 const [notes,setNotes]=useState<Note[]>([]);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const [error,setError]=useState("");
 const [alias,setAlias]=useState("BassCello");
 const [previewReady,setPreviewReady]=useState(false);
 const chosen=sections.find(s=>s.id===sectionId);
 const start=chosen?chosen.start_seconds:customStart;
 const duration=chosen?chosen.end_seconds-chosen.start_seconds:customDuration;
 const inBounds=Number.isFinite(start)&&Number.isFinite(duration)&&start>=0&&duration>=.5&&duration<=45&&start+duration<=songDuration+.005;
 const base="/api/projects/"+jobId+"/bass-midi";
 useEffect(()=>{let live=true;void req<{tracks:Track[]}>("/api/projects/"+jobId+"/tracks").then(data=>{
   if(!live)return;const bass=data.tracks.find(t=>t.stem_alias.toLowerCase()==="bass");
   setTrackId(bass?.track_id||"");setBassExists(!!bass);
 }).catch(e=>{if(live)setError(String(e));});return()=>{live=false;};},[jobId]);

 useEffect(()=>()=>{engine?.clearCandidatePreview();},[engine,jobId]);
 function edited(index:number,patch:Partial<Note>){
   setNotes(current=>current.map((note,i)=>i===index?{...note,...patch}:note));setPreviewReady(false);engine?.clearCandidatePreview();
 }
 function revert(){setNotes(candidate?.original_notes.map(n=>({...n}))||[]);setPreviewReady(false);engine?.clearCandidatePreview();setMessage("Original extracted notes restored.");}
 async function analyze(){
   if(!trackId||!inBounds||busy)return;
   setBusy(true);setError("");setMessage("");engine?.clearCandidatePreview();setPreviewReady(false);
   try{
     const data=await req<Candidate>(base+"/analyze",{method:"POST",headers:{"Content-Type":"application/json"},
       body:JSON.stringify({track_id:trackId,start_seconds:start,duration_seconds:duration})});
     setCandidate(data);setNotes(data.notes.map(n=>({...n})));
     setMessage(data.notes.length+" estimated bass notes. Correct pitch/timing, then render preview.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function render(){
   if(!candidate||busy)return;
   setBusy(true);setError("");engine?.clearCandidatePreview();setPreviewReady(false);
   try{
     const data=await req<Candidate>(base+"/"+candidate.candidate_id+"/render",{
       method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({notes})});
     setCandidate(data);setNotes(data.notes);setPreviewReady(true);
     setMessage("Bowed-string approximation rendered. Solo it, compare, then optionally insert.");
   }catch(e){setError(String(e));}finally{setBusy(false);}
 }
 async function audition(solo:boolean){
   if(!candidate||!previewReady||!engine?.ready)return;
   setBusy(true);setError("");
   try{
     await engine.loadCandidatePreview(base+"/"+candidate.candidate_id+"/audio?revision="+Date.now(),candidate.start_seconds);
     engine.setCandidatePreviewSolo(solo);
     engine.setCandidatePreviewBlend(solo?100:60);
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
     form.append("file",new File([blob],"Bowed-"+candidate.candidate_id.slice(0,8)+".wav",{type:"audio/wav"}));
     form.append("stem_alias",alias);
     form.append("display_name","Bowed bass MIDI test ("+alias+")");
     form.append("start_seconds",String(candidate.start_seconds));
     const data=await req<Imported>("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
     engine?.clearCandidatePreview();
     setMessage("New track inserted. Original Bass is untouched; mute Bass to audition replacement, or remove this imported track to undo.");
     onInserted(data);
   }catch(e){const detail=String(e);setError(detail);onError(detail);}finally{setBusy(false);}
 }
 async function midi(){
   if(!candidate||!previewReady)return;
   const a=document.createElement("a");a.href=base+"/"+candidate.candidate_id+"/midi";
   a.download="Bass-to-Cello.mid";document.body.appendChild(a);a.click();a.remove();
 }
 function addNote(){
   const t=Math.max(0,Math.min(candidate?.duration_seconds||1,notes.length?notes[notes.length-1].end:0));
   const end=Math.min(candidate?.duration_seconds||1,t+.5);
   if(end-t<.06){setError("No space for another note near the end.");return;}
   setNotes(current=>[...current,{pitch:40,start:t,end,velocity:85}]);setPreviewReady(false);engine?.clearCandidatePreview();
 }
 function transpose(semitones:number){setNotes(current=>current.map(n=>({...n,pitch:Math.min(76,Math.max(28,n.pitch+semitones))})));setPreviewReady(false);engine?.clearCandidatePreview();}
 return <div className="song-midi-tool">
   <strong>Bass to MIDI / bowed bass test</strong>
   <small>CPU-only, monophonic prototype. Pitch and note boundaries are estimates. The rendered sound is an original bowed-string approximation, not a sampled acoustic cello.</small>
   {!bassExists&&<small role="alert">A separated track with alias Bass is required.</small>}
   <label>Source <input value="Bass (original stem only)" disabled/></label>
   <label>Region <select value={sectionId} onChange={e=>setSectionId(e.target.value)}><option value="custom">Custom range</option>{sections.map(s=><option key={s.id} value={s.id}>{s.kind}{s.number?" "+s.number:""} · {clock(s.start_seconds)}–{clock(s.end_seconds)} ({(s.end_seconds-s.start_seconds).toFixed(1)}s)</option>)}</select></label>
   {sectionId==="custom"&&<div className="song-midi-controls"><label>Start (s) <input type="number" min="0" max={songDuration} step=".1" value={customStart} onChange={e=>setCustomStart(Number(e.target.value))}/></label><label>Length (s) <input type="number" min=".5" max="45" step=".1" value={customDuration} onChange={e=>setCustomDuration(Number(e.target.value))}/></label><button type="button" onClick={()=>setCustomStart(Math.max(0,Math.min(position,songDuration-customDuration)))}>Start at playhead</button></div>}
   <small>{!inBounds?"Select a 0.5–45s range entirely within the song.":"Start with 10–30 seconds of relatively clean separated bass."}</small>
   <button type="button" disabled={!trackId||!inBounds||busy} onClick={()=>void analyze()}>{busy?"Working...":"Extract bass notes (CPU)"}</button>
   {candidate&&<><div className="song-midi-controls">
     <strong>{notes.length} notes · {clock(candidate.start_seconds)}–{clock(candidate.start_seconds+candidate.duration_seconds)}</strong>
     <button type="button" disabled={busy} onClick={revert}>Revert edits</button>
     <button type="button" disabled={busy} onClick={()=>transpose(-12)}>Octave down</button>
     <button type="button" disabled={busy} onClick={()=>transpose(12)}>Octave up</button>
     <button type="button" disabled={busy} onClick={addNote}>Add note</button>
   </div>
   <div className="song-midi-note-list" aria-label="Editable extracted MIDI notes">
    {notes.map((note,i)=><div key={i} className="song-midi-note">
      <span>{i+1}</span>
      <label>Pitch <select aria-label={"Note "+(i+1)+" pitch"} value={note.pitch} onChange={e=>edited(i,{pitch:Number(e.target.value)})}>{Array.from({length:49},(_,j)=>j+28).map(p=><option key={p} value={p}>{pitchName(p)} ({p})</option>)}</select></label>
      <label>Start <input aria-label={"Note "+(i+1)+" start"} type="number" min="0" max={candidate.duration_seconds} step=".01" value={note.start} onChange={e=>edited(i,{start:Number(e.target.value)})}/></label>
      <label>End <input aria-label={"Note "+(i+1)+" end"} type="number" min="0" max={candidate.duration_seconds} step=".01" value={note.end} onChange={e=>edited(i,{end:Number(e.target.value)})}/></label>
      <button type="button" aria-label={"Remove note "+(i+1)} onClick={()=>{setNotes(current=>current.filter((_,j)=>j!==i));setPreviewReady(false);engine?.clearCandidatePreview();}}>×</button>
    </div>)}
   </div>
   <div className="song-midi-controls"><button type="button" disabled={busy||!notes.length} onClick={()=>void render()}>{busy?"Working...":"Render bowed-string candidate"}</button>
    <button type="button" disabled={!previewReady||busy} onClick={()=>void audition(true)}>Solo candidate</button>
    <button type="button" disabled={!previewReady||busy} onClick={()=>void audition(false)}>A/B with song</button>
    <button type="button" disabled={!previewReady} onClick={()=>void midi()}>Export .mid</button>
   </div>
   <label>New track alias <input value={alias} maxLength={32} onChange={e=>setAlias(e.target.value)}/></label>
   <button type="button" disabled={!previewReady||busy} onClick={()=>void insert()}>Accept as NEW track (original preserved)</button>
   <small>Undo after acceptance: remove the imported bowed-bass track. The original Bass stem remains untouched and may be unmuted any time.</small>
   </>}
   {message&&<small role="status">{message}</small>}
   {error&&<small role="alert">{error}</small>}
 </div>;
}
