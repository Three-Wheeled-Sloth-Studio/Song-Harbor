import {useEffect,useRef,useState} from "react";
import type {PointerEvent as ReactPointerEvent} from "react";

export type RollNote={id:string;start_sample:number;end_sample:number;pitch:number;velocity:number;channel:number};
export type Arrangement={asset_id:string;revision:number;sample_rate:number;duration_samples:number;source:{track_id:string;start_sample:number;candidate_id?:string;method?:string};notes:RollNote[]};
type Summary={asset_id:string;revision:number;source:Arrangement["source"];note_count:number;duration_samples:number};
type Operation={op:"add";note:RollNote}|{op:"remove";id:string}|{op:"update";id:string;changes:Partial<Omit<RollNote,"id">>};
type Props={jobId:string;sourceTrackId:string;requestedAssetId?:string;onDirtyChange?:(dirty:boolean)=>void;onUse:(asset:Arrangement)=>Promise<void>;onError:(error:string)=>void};
const RATE=48000, ROW=17, KEY_WIDTH=43, PX_PER_SECOND=65, MIN_NOTE=.06*RATE;
const PITCH_LOW=28,PITCH_HIGH=76;
const pitchNames=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
const pitchLabel=(p:number)=>pitchNames[p%12]+(Math.floor(p/12)-1);
const clone=(n:RollNote[])=>n.map(x=>({...x}));
const same=(a:RollNote,b:RollNote)=>a.start_sample===b.start_sample&&a.end_sample===b.end_sample&&a.pitch===b.pitch&&a.velocity===b.velocity&&a.channel===b.channel;
export function diffNotes(previous:RollNote[],next:RollNote[]):Operation[]{
 const old=new Map(previous.map(n=>[n.id,n]));
 const current=new Map(next.map(n=>[n.id,n]));
 const operations:Operation[]=[];
 previous.forEach(n=>{if(!current.has(n.id))operations.push({op:"remove",id:n.id});});
 next.forEach(n=>{const prior=old.get(n.id);if(!prior)operations.push({op:"add",note:n});
 else if(!same(prior,n)){const changes:Partial<Omit<RollNote,"id">>={};
  (["start_sample","end_sample","pitch","velocity","channel"] as const).forEach(key=>{if(prior[key]!==n[key])changes[key]=n[key];});
  operations.push({op:"update",id:n.id,changes});}});
 return operations;
}
async function request<T>(url:string,init?:RequestInit):Promise<T>{
 const response=await fetch(url,init);const value=await response.json() as T&{detail?:string};
 if(!response.ok)throw Error(value.detail||"MIDI arrangement request failed");return value;
}
export function MidiPianoRoll({jobId,sourceTrackId,requestedAssetId,onDirtyChange,onUse,onError}:Props){
 const root="/api/projects/"+jobId+"/midi-arrangements";
 const [listing,setListing]=useState<Summary[]>([]);
 const [asset,setAsset]=useState<Arrangement|null>(null);
 const [notes,setNotes]=useState<RollNote[]>([]);
 const [history,setHistory]=useState<RollNote[][]>([]);
 const [future,setFuture]=useState<RollNote[][]>([]);
 const [selected,setSelected]=useState("");
 const [selectedIds,setSelectedIds]=useState<string[]>([]);
 const clipboard=useRef<RollNote[]>([]);
 const scrollerRef=useRef<HTMLDivElement|null>(null);
 const [snap,setSnap]=useState(false);
 const [gridMs,setGridMs]=useState(250);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const drag=useRef<{id:string;mode:"move"|"resize";originX:number;original:RollNote;group:RollNote[]}|null>(null);
 const notesRef=useRef(notes);notesRef.current=notes;
 const dirty=asset!==null&&diffNotes(asset.notes,notes).length>0;
 useEffect(()=>{onDirtyChange?.(dirty);},[dirty,onDirtyChange]);
 useEffect(()=>{
  if(!dirty)return;
  const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue="";};
  window.addEventListener("beforeunload",guard);
  return()=>window.removeEventListener("beforeunload",guard);
 },[dirty]);
 const listForTrack=listing.filter(x=>x.source.track_id===sourceTrackId);
 const width=asset?Math.max(540,KEY_WIDTH+asset.duration_samples/RATE*PX_PER_SECOND+18):540;
 const height=(PITCH_HIGH-PITCH_LOW+1)*ROW;
 const q=(sample:number)=>snap?Math.round(sample/(RATE*gridMs/1000))*(RATE*gridMs/1000):Math.round(sample);
 const toX=(sample:number)=>KEY_WIDTH+sample/RATE*PX_PER_SECOND;
 const fromX=(x:number)=>Math.max(0,Math.min(asset?.duration_samples||0,q((x-KEY_WIDTH)/PX_PER_SECOND*RATE)));
 const toY=(pitch:number)=>(PITCH_HIGH-pitch)*ROW;
 function edit(updated:RollNote[],record=true){
  if(record){setHistory(old=>[...old.slice(-99),clone(notesRef.current)]);setFuture([]);}
  setNotes(updated);notesRef.current=updated;
 }
 function undo(){if(!history.length)return;setFuture(v=>[clone(notesRef.current),...v]);const last=history[history.length-1];setHistory(v=>v.slice(0,-1));edit(clone(last),false);}
 function redo(){if(!future.length)return;setHistory(v=>[...v,clone(notesRef.current)]);const first=future[0];setFuture(v=>v.slice(1));edit(clone(first),false);}
 function open(value:Arrangement){setAsset(value);edit(clone(value.notes),false);setHistory([]);setFuture([]);setSelected("");setSelectedIds([]);setMessage("");}
 async function refresh(){try{const found=await request<{arrangements:Summary[]}>(root);setListing(found.arrangements);}catch(error){onError(String(error));}}
 useEffect(()=>{setAsset(null);setHistory([]);setFuture([]);setSelected("");setSelectedIds([]);void refresh();},[jobId,sourceTrackId]);
 useEffect(()=>{if(!requestedAssetId)return;
  let live=true;void request<Arrangement>(root+"/"+requestedAssetId).then(value=>{
   if(live&&value.source.track_id===sourceTrackId)open(value);
  }).catch(error=>{if(live)onError(String(error));});
  return()=>{live=false;};
 },[jobId,sourceTrackId,requestedAssetId]);
 async function load(id:string){if(dirty&&!window.confirm("Discard unsaved MIDI edits?"))return;
  setBusy(true);try{open(await request<Arrangement>(root+"/"+id));}catch(error){onError(String(error));}finally{setBusy(false);}}
 async function save(){if(!asset||busy)return;const operations=diffNotes(asset.notes,notes);
  if(!operations.length){setMessage("No unsaved changes.");return;}
  setBusy(true);try{const saved=await request<Arrangement>(root+"/"+asset.asset_id,{
   method:"PATCH",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({base_revision:asset.revision,operations})});
   open(saved);setMessage("Arrangement saved, revision "+saved.revision+".");void refresh();
  }catch(error){onError(String(error));}finally{setBusy(false);}}
 const picked=notes.filter(n=>selectedIds.includes(n.id));
 function selectOne(id:string){setSelected(id);setSelectedIds([id]);}
 function removeSelected(){
  if(!selectedIds.length||busy)return;
  const ids=new Set(selectedIds);edit(notesRef.current.filter(n=>!ids.has(n.id)));
  setSelected("");setSelectedIds([]);
 }
 function duplicateSelected(){
  if(!asset||!picked.length||busy)return;
  const first=Math.min(...picked.map(n=>n.start_sample));
  const last=Math.max(...picked.map(n=>n.end_sample));
  const offset=Math.max(0,Math.min(last-first+Math.round(RATE*.25),asset.duration_samples-last));
  if(!offset){setMessage("No room to duplicate selection.");return;}
  const copies=picked.map(n=>({...n,id:crypto.randomUUID().replace(/-/g,""),
    start_sample:n.start_sample+offset,end_sample:n.end_sample+offset}));
  edit([...notesRef.current,...copies]);setSelectedIds(copies.map(n=>n.id));setSelected(copies[0].id);
 }
 function copySelected(){if(!picked.length)return;clipboard.current=clone(picked);setMessage(picked.length+" note(s) copied.");}
 function pasteSelected(){
  if(!asset||!clipboard.current.length||busy)return;
  const source=clipboard.current;
  const first=Math.min(...source.map(n=>n.start_sample));
  const last=Math.max(...source.map(n=>n.end_sample));
  const offset=Math.round(RATE*.25);
  const target=Math.max(0,Math.min(asset.duration_samples-(last-first),last+offset));
  const copies=source.map(n=>({...n,id:crypto.randomUUID().replace(/-/g,""),
    start_sample:target+(n.start_sample-first),end_sample:target+(n.end_sample-first)}));
  if(copies.some(n=>n.end_sample>asset.duration_samples)){setMessage("Selection does not fit in this arrangement.");return;}
  edit([...notesRef.current,...copies]);setSelectedIds(copies.map(n=>n.id));setSelected(copies[0].id);
 }
 function nudgeSelected(pitchDelta:number,timeDelta:number){
  if(!asset||!picked.length||busy)return;
  const ids=new Set(selectedIds);
  const low=Math.min(...picked.map(n=>n.start_sample));
  const high=Math.max(...picked.map(n=>n.end_sample));
  const minPitch=Math.min(...picked.map(n=>n.pitch)),maxPitch=Math.max(...picked.map(n=>n.pitch));
  const delta=Math.max(-low,Math.min(asset.duration_samples-high,timeDelta));
  const pitch=Math.max(-minPitch,Math.min(127-maxPitch,pitchDelta));
  edit(notesRef.current.map(n=>ids.has(n.id)?{...n,pitch:n.pitch+pitch,
    start_sample:n.start_sample+delta,end_sample:n.end_sample+delta}:n));
 }
 function addAt(x:number,pitch:number){if(!asset)return;
  const start=fromX(x),end=Math.min(asset.duration_samples,start+RATE*.5);
  if(end-start<MIN_NOTE)return;
  const note:RollNote={id:crypto.randomUUID().replace(/-/g,""),start_sample:start,end_sample:Math.round(end),pitch,velocity:85,channel:0};
  edit([...notesRef.current,note]);selectOne(note.id);scrollerRef.current?.focus();}
 function startDrag(event:ReactPointerEvent<SVGRectElement>,note:RollNote,mode:"move"|"resize"){
  event.stopPropagation();
  if(event.shiftKey){
   const next=selectedIds.includes(note.id)?selectedIds.filter(id=>id!==note.id):[...selectedIds,note.id];
   setSelectedIds(next);setSelected(next.length?next[next.length-1]:"");
   scrollerRef.current?.focus();return;
  }
  event.currentTarget.setPointerCapture(event.pointerId);
  const group=mode==="move"&&selectedIds.includes(note.id)
   ?clone(notesRef.current.filter(n=>selectedIds.includes(n.id))):[{...note}];
  drag.current={id:note.id,mode,originX:event.clientX,original:{...note},group};
  if(!selectedIds.includes(note.id))selectOne(note.id);
  scrollerRef.current?.focus();
  setHistory(old=>[...old.slice(-99),clone(notesRef.current)]);setFuture([]);
 }
 function moveDrag(event:React.PointerEvent<SVGRectElement>){
  const d=drag.current;if(!d||!asset)return;
  const svg=event.currentTarget.ownerSVGElement;const bounds=svg?.getBoundingClientRect();
  const scale=bounds?width/bounds.width:1;
  const delta=Math.round((event.clientX-d.originX)*scale/PX_PER_SECOND*RATE);
  const quantize=(value:number)=>snap?q(value):Math.round(value);
  const n=d.original;
  if(d.mode==="move"){
   const low=Math.min(...d.group.map(v=>v.start_sample));
   const high=Math.max(...d.group.map(v=>v.end_sample));
   const movement=Math.max(-low,Math.min(asset.duration_samples-high,quantize(n.start_sample+delta)-n.start_sample));
   const originals=new Map(d.group.map(v=>[v.id,v]));
   edit(notesRef.current.map(note=>{
    const prior=originals.get(note.id);
    return prior?{...note,start_sample:prior.start_sample+movement,end_sample:prior.end_sample+movement}:note;
   }),false);
  }else{
   const end=Math.max(n.start_sample+MIN_NOTE,Math.min(asset.duration_samples,quantize(n.end_sample+delta)));
   edit(notesRef.current.map(note=>note.id===d.id?{...note,end_sample:Math.round(end)}:note),false);
  }
 }
 const active=notes.find(n=>n.id===selected);
 return <section className="song-piano-roll" aria-label="Editable MIDI arrangement">
   <div className="song-roll-toolbar">
    <strong>Arrangement</strong>
    <select aria-label="Saved MIDI arrangements" value={asset?.asset_id||""} onChange={e=>{if(e.target.value)void load(e.target.value);}} disabled={busy}>
     <option value="">Open saved arrangement...</option>
     {listForTrack.map(x=><option key={x.asset_id} value={x.asset_id}>{x.asset_id.slice(0,8)} · {x.note_count} notes · r{x.revision}</option>)}
    </select>
    <button type="button" onClick={()=>void refresh()} title="Refresh saved arrangements" disabled={busy}>Refresh</button>
    {asset&&<><button type="button" onClick={undo} disabled={!history.length||busy} title="Undo note edit">Undo</button>
    <button type="button" onClick={redo} disabled={!future.length||busy} title="Redo note edit">Redo</button>
    <button type="button" onClick={()=>{if(asset&&window.confirm("Revert all unsaved MIDI edits?"))open(asset);}} disabled={!dirty||busy} title="Discard unsaved edits and restore saved revision">Revert</button>
    <button type="button" onClick={duplicateSelected} disabled={!selectedIds.length||busy} title="Duplicate selected notes">Duplicate</button>
    <button type="button" onClick={removeSelected} disabled={!selectedIds.length||busy} title="Delete selected notes">Delete</button>
    <button type="button" onClick={copySelected} disabled={!selectedIds.length||busy} title="Copy selected notes">Copy</button>
    <button type="button" onClick={pasteSelected} disabled={!clipboard.current.length||busy} title="Paste copied notes into this arrangement">Paste</button>
    <button type="button" onClick={()=>void save()} disabled={!dirty||busy}>Save{dirty?" *":""}</button>
    <button type="button" onClick={()=>{void onUse(asset).catch(e=>onError(String(e)));}} disabled={dirty||busy} title="Render saved arrangement with selected instrument pack">Render arrangement</button></>}
   </div>
   {asset&&<>
    <div className="song-roll-toolbar song-roll-options">
     <label><input type="checkbox" checked={snap} onChange={e=>setSnap(e.target.checked)}/> Snap</label>
     <label>Grid <select value={gridMs} onChange={e=>setGridMs(Number(e.target.value))}><option value={125}>125 ms</option><option value={250}>250 ms</option><option value={500}>500 ms</option></select></label>
     <span>{dirty?"Unsaved changes":("Saved revision "+asset.revision)}</span>
     {active&&<label>Velocity <input type="number" min={1} max={127} value={active.velocity} onChange={e=>{const velocity=Number(e.target.value);if(Number.isInteger(velocity)&&velocity>=1&&velocity<=127)edit(notesRef.current.map(n=>n.id===active.id?{...n,velocity}:n));}}/></label>}
    </div>
    <div className="song-roll-scroller" ref={scrollerRef} tabIndex={0} aria-label="Piano roll; click empty grid to add notes, drag notes to move, drag right edge to resize"
     onKeyDown={e=>{if(e.target!==e.currentTarget)return;
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="z"){e.preventDefault();if(e.shiftKey)redo();else undo();}
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="y"){e.preventDefault();redo();}
      if((e.key==="Delete"||e.key==="Backspace")&&selectedIds.length){e.preventDefault();removeSelected();}
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="d"&&selectedIds.length){e.preventDefault();duplicateSelected();}
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="c"&&selectedIds.length){e.preventDefault();copySelected();}
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="v"&&clipboard.current.length){e.preventDefault();pasteSelected();}
      if(selectedIds.length&&["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(e.key)){
       e.preventDefault();const step=Math.round(RATE*gridMs/1000);
       nudgeSelected(e.key==="ArrowUp"?1:e.key==="ArrowDown"?-1:0,e.key==="ArrowRight"?step:e.key==="ArrowLeft"?-step:0);
      }}}>
     <svg width={width} height={height} role="img" aria-label="Editable piano roll">
      {Array.from({length:PITCH_HIGH-PITCH_LOW+1},(_,i)=>{const p=PITCH_HIGH-i;return <g key={p}>
       <rect x={0} y={i*ROW} width={width} height={ROW} fill={p%12===1||p%12===3||p%12===6||p%12===8||p%12===10?"#252e3b":"#303d4a"} stroke="#536171" strokeWidth=".3"/>
       <rect x={0} y={i*ROW} width={KEY_WIDTH} height={ROW} fill={p%12===1||p%12===3||p%12===6||p%12===8||p%12===10?"#8897a7":"#e2e7eb"} />
       <text x={4} y={i*ROW+12} fill="#111b22" fontSize="11">{pitchLabel(p)}</text>
       <rect x={KEY_WIDTH} y={i*ROW} width={width-KEY_WIDTH} height={ROW} fill="transparent" onClick={e=>{const box=e.currentTarget.ownerSVGElement?.getBoundingClientRect();const scale=box?width/box.width:1;const local=(e.clientX-(box?.left||0))*scale;addAt(local,p);}}/>
      </g>;})}
      {Array.from({length:Math.ceil((width-KEY_WIDTH)/(PX_PER_SECOND*.5))+1},(_,i)=><line key={i} x1={KEY_WIDTH+i*PX_PER_SECOND*.5} y1={0} x2={KEY_WIDTH+i*PX_PER_SECOND*.5} y2={height} stroke="#a7c0ce" strokeOpacity={i%2===0?.35:.12} pointerEvents="none"/>)}
      {notes.map(note=>{const x=toX(note.start_sample),w=Math.max(3,toX(note.end_sample)-x),y=toY(note.pitch);if(note.pitch<PITCH_LOW||note.pitch>PITCH_HIGH)return null;return <g key={note.id}>
       <rect x={x} y={y+2} width={w} height={ROW-4} rx={2} fill={selectedIds.includes(note.id)?"#e3b965":"#70bbaf"} stroke="#d6eee7" strokeWidth={1} onPointerDown={e=>startDrag(e,note,"move")} onPointerMove={moveDrag} onPointerUp={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}/>
       <rect x={x+Math.max(0,w-6)} y={y+2} width={Math.min(6,w)} height={ROW-4} fill="#467f82" onPointerDown={e=>startDrag(e,note,"resize")} onPointerMove={moveDrag} onPointerUp={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}/>
      </g>;})}
     </svg>
    </div>
    <small>Click grid to add; drag notes to move or resize. Shift-click to select multiple notes; drag selection to move together. Arrow keys nudge selected notes (left/right by grid interval, up/down by semitone); Delete removes and Ctrl+D duplicates, Ctrl+C/V copies and pastes. Undo/redo and Revert remain available. Snap is off by default. Overlapping notes render with SF2 instruments; other instrument types are not yet supported for saved arrangements. {notes.length} notes, {(asset.duration_samples/RATE).toFixed(2)}s.</small>
   </>}
   {!asset&&<small>Save an extracted MIDI arrangement, then open it here. Select an SF2 instrument and choose Render arrangement.</small>}
   {message&&<small role="status">{message}</small>}
  </section>;
}
