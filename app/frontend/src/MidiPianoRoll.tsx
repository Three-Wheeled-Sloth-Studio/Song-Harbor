import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {PointerEvent as ReactPointerEvent, MouseEvent as ReactMouseEvent} from "react";
import type {SongSection} from "./SectionEditor";

export type RollNote={id:string;start_sample:number;end_sample:number;pitch:number;velocity:number;channel:number};
export type Arrangement={asset_id:string;revision:number;sample_rate:number;duration_samples:number;source:{track_id:string;start_sample:number;candidate_id?:string;method?:string};notes:RollNote[]};
type Summary={asset_id:string;revision:number;source:Arrangement["source"];note_count:number;duration_samples:number};
type Operation={op:"add";note:RollNote}|{op:"remove";id:string}|{op:"update";id:string;changes:Partial<Omit<RollNote,"id">>};
type InstrumentOption={id:string;pack_id:string;name:string;engine:string};
export type DrumOptions={percussion:boolean;drum_keymap:{schema_version:number;mapping_kind:"gm"|"custom";lanes:{pitch:number;name:string}[]}|null};
const GM_KIT:Record<number,string>={35:"Acoustic Kick",36:"Kick",37:"Rim",38:"Snare",39:"Clap",40:"Electric Snare",41:"Floor Tom",42:"Closed Hat",43:"Floor Tom",44:"Pedal Hat",45:"Low Tom",46:"Open Hat",47:"Mid Tom",48:"Mid Tom",49:"Crash",50:"High Tom",51:"Ride",52:"China",53:"Ride Bell",54:"Tambourine",55:"Splash",56:"Cowbell",57:"Crash 2",58:"Vibraslap",59:"Ride 2",60:"Bongo",61:"Bongo",62:"Conga",63:"Conga",64:"Conga",65:"Timbale",66:"Timbale",67:"Agogo",68:"Agogo",69:"Cabasa",70:"Maracas",71:"Whistle",72:"Whistle",73:"Guiro",74:"Guiro",75:"Claves",76:"Wood Block",77:"Wood Block",78:"Cuica",79:"Cuica",80:"Triangle",81:"Triangle"};
type Props={jobId:string;sourceTrackId:string;requestedAssetId?:string;sections?:SongSection[];instruments?:InstrumentOption[];selectedInstrument?:string;onInstrumentChange?:(key:string)=>void;onDirtyChange?:(dirty:boolean)=>void;onUse:(asset:Arrangement,sectionIds:string[],options:DrumOptions)=>Promise<void>;onError:(error:string)=>void};
const RATE=48000, ROW=17, KEY_WIDTH=43, MIN_NOTE=.06*RATE;
const PITCH_LOW=28,PITCH_HIGH=76, VELOCITY_HEIGHT=92;
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
export function MidiPianoRoll({jobId,sourceTrackId,requestedAssetId,sections=[],instruments=[],selectedInstrument="",onInstrumentChange,onDirtyChange,onUse,onError}:Props){
 const root="/api/projects/"+jobId+"/midi-arrangements";
 const [listing,setListing]=useState<Summary[]>([]);
 const [asset,setAsset]=useState<Arrangement|null>(null);
 const [notes,setNotes]=useState<RollNote[]>([]);
 const [drumMode,setDrumMode]=useState(false);
 const [kitKind,setKitKind]=useState<"gm"|"custom">("gm");
 const [kitText,setKitText]=useState("");
 const [kitExpanded,setKitExpanded]=useState(false);
 const [history,setHistory]=useState<RollNote[][]>([]);
 const [future,setFuture]=useState<RollNote[][]>([]);
 const [selected,setSelected]=useState("");
 const [popOut,setPopOut]=useState(false);
 const [selectedSections,setSelectedSections]=useState<string[]>([]);
 const [position,setPosition]=useState({x:0,y:0});
 const moveWindow=useRef<{x:number;y:number;left:number;top:number}|null>(null);
 const [selectedIds,setSelectedIds]=useState<string[]>([]);
 const clipboard=useRef<RollNote[]>([]);
 const scrollerRef=useRef<HTMLDivElement|null>(null);
 const [snap,setSnap]=useState(false);
 const [gridMs,setGridMs]=useState(250);
 const [pixelsPerSecond,setPixelsPerSecond]=useState(65);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const drag=useRef<{id:string;mode:"move"|"resize";originX:number;original:RollNote;group:RollNote[]}|null>(null);
 const velocityDrag=useRef<{ids:string[]}|null>(null);
 const notesRef=useRef(notes);notesRef.current=notes;
 const dirty=asset!==null&&diffNotes(asset.notes,notes).length>0;
 useEffect(()=>{onDirtyChange?.(dirty);},[dirty,onDirtyChange]);
 useEffect(()=>{
  if(!dirty)return;
  const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue="";};
  window.addEventListener("beforeunload",guard);
  return()=>window.removeEventListener("beforeunload",guard);
 },[dirty]);
 const sfzSelected=instruments.some(x=>x.pack_id+"::"+x.id===selectedInstrument&&x.engine==="sfz");
 const keyWidth=drumMode?148:KEY_WIDTH, topPitch=drumMode?81:PITCH_HIGH;
 let kitLanes:{pitch:number;name:string}[]=[],kitError="";
 if(drumMode){
  if(kitKind==="gm")kitLanes=Object.entries(GM_KIT).map(([p,name])=>({pitch:Number(p),name}));
  else try{
   const used=new Set<number>();
   for(const line of kitText.split(/\r?\n/)){
    if(!line.trim())continue;
    const match=/^\s*(\d{1,3})\s*[=:]\s*(.{1,80})\s*$/.exec(line);
    if(!match||Number(match[1])>127||used.has(Number(match[1])))throw Error("Kit lanes must be unique MIDI pitch = name entries.");
    used.add(Number(match[1]));kitLanes.push({pitch:Number(match[1]),name:match[2].trim()});
   }
   if(!kitLanes.length)throw Error("Define at least one kit lane.");
  }catch(e){kitError=String(e);}
  if(sfzSelected&&kitKind==="gm")kitError="Select a verified custom map for SFZ drums.";
  const keys=new Set(kitLanes.map(l=>l.pitch));
  const missing=[...new Set(notes.filter(n=>!keys.has(n.pitch)).map(n=>n.pitch))];
  if(missing.length)kitError="Unmapped drum pitches: "+missing.join(", ");
 }
 const kitNames=new Map(kitLanes.map(l=>[l.pitch,l.name]));
 const drumOptions:DrumOptions={percussion:drumMode,drum_keymap:drumMode?{schema_version:1,mapping_kind:kitKind,lanes:kitLanes}:null};
 const listForTrack=listing.filter(x=>x.source.track_id===sourceTrackId);
 const width=asset?Math.max(540,keyWidth+asset.duration_samples/RATE*pixelsPerSecond+18):540;
 const rollHeight=(topPitch-PITCH_LOW+1)*ROW;
 const height=rollHeight+VELOCITY_HEIGHT;
 const q=(sample:number)=>snap?Math.round(sample/(RATE*gridMs/1000))*(RATE*gridMs/1000):Math.round(sample);
 const toX=(sample:number)=>keyWidth+sample/RATE*pixelsPerSecond;
 const fromX=(x:number)=>Math.max(0,Math.min(asset?.duration_samples||0,q((x-keyWidth)/pixelsPerSecond*RATE)));
 const toY=(pitch:number)=>(topPitch-pitch)*ROW;
 function edit(updated:RollNote[],record=true){
  if(record){setHistory(old=>[...old.slice(-99),clone(notesRef.current)]);setFuture([]);}
  setNotes(updated);notesRef.current=updated;
 }
 function undo(){if(!history.length)return;setFuture(v=>[clone(notesRef.current),...v]);const last=history[history.length-1];setHistory(v=>v.slice(0,-1));edit(clone(last),false);}
 function redo(){if(!future.length)return;setHistory(v=>[...v,clone(notesRef.current)]);const first=future[0];setFuture(v=>v.slice(1));edit(clone(first),false);}
 function open(value:Arrangement){setSelectedSections([]);setDrumMode(value.notes.length>0&&value.notes.every(n=>n.channel===9));setAsset(value);edit(clone(value.notes),false);setHistory([]);setFuture([]);setSelected("");setSelectedIds([]);setMessage("");}
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
  const pitch=Math.max(PITCH_LOW-minPitch,Math.min(topPitch-maxPitch,pitchDelta));
  edit(notesRef.current.map(n=>ids.has(n.id)?{...n,pitch:n.pitch+pitch,
    start_sample:n.start_sample+delta,end_sample:n.end_sample+delta}:n));
 }
 function addAt(x:number,pitch:number){if(!asset)return;
  const start=fromX(x),end=Math.min(asset.duration_samples,start+RATE*(drumMode?.15:.5));
  if(end-start<MIN_NOTE)return;
  const note:RollNote={id:crypto.randomUUID().replace(/-/g,""),start_sample:start,end_sample:Math.round(end),pitch,velocity:85,channel:drumMode?9:0};
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
  const delta=Math.round((event.clientX-d.originX)*scale/pixelsPerSecond*RATE);
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
 function velocityAt(event:ReactPointerEvent<SVGRectElement>){
  const bounds=event.currentTarget.ownerSVGElement?.getBoundingClientRect();
  const scale=bounds?height/bounds.height:1;
  const y=(event.clientY-(bounds?.top||0))*scale;
  return Math.max(1,Math.min(127,Math.round((rollHeight+VELOCITY_HEIGHT-8-y)/(VELOCITY_HEIGHT-18)*127)));
 }
 function startVelocity(event:ReactPointerEvent<SVGRectElement>,note:RollNote){
  event.stopPropagation();
  if(busy)return;
  const ids=selectedIds.includes(note.id)?selectedIds:[note.id];
  if(!selectedIds.includes(note.id))selectOne(note.id);
  event.currentTarget.setPointerCapture(event.pointerId);
  velocityDrag.current={ids};
  setHistory(old=>[...old.slice(-99),clone(notesRef.current)]);setFuture([]);
  setVelocity(event,ids);
 }
 function setVelocity(event:ReactPointerEvent<SVGRectElement>,ids:string[]){
  const value=velocityAt(event);
  const chosen=new Set(ids);
  edit(notesRef.current.map(note=>chosen.has(note.id)?{...note,velocity:value}:note),false);
 }
 function moveVelocity(event:ReactPointerEvent<SVGRectElement>){
  if(velocityDrag.current)setVelocity(event,velocityDrag.current.ids);
 }
 const visibleSections=asset?sections.filter(section=>{
   const start=asset.source.start_sample/RATE,end=start+asset.duration_samples/RATE;
   return section.end_seconds>start&&section.start_seconds<end;
 }):[];
 const selectedSectionRanges=visibleSections.filter(section=>selectedSections.includes(section.id));
 function chooseSection(section:SongSection,event:ReactMouseEvent<HTMLButtonElement>){
   const matching=event.altKey?visibleSections.filter(item=>item.kind.toLowerCase()===section.kind.toLowerCase()).map(item=>item.id):[section.id];
   setSelectedSections(previous=>{
     if(event.ctrlKey||event.metaKey||event.shiftKey){
       return matching.every(id=>previous.includes(id))
         ?previous.filter(id=>!matching.includes(id))
         :[...new Set([...previous,...matching])];
     }
     return matching;
   });
 }
 function startWindowDrag(event:ReactPointerEvent<HTMLElement>){
   if((event.target as HTMLElement).closest("button,input,select"))return;
   event.currentTarget.setPointerCapture(event.pointerId);
   moveWindow.current={x:event.clientX,y:event.clientY,left:position.x,top:position.y};
 }
 function dragWindow(event:ReactPointerEvent<HTMLElement>){
   const original=moveWindow.current;
   if(!original)return;
   setPosition({x:original.left+event.clientX-original.x,y:original.top+event.clientY-original.y});
 }
 const active=notes.find(n=>n.id===selected);
 return <div className="song-roll-launcher">
   <span title={asset?"Saved MIDI arrangement "+asset.asset_id:"No saved arrangement open"}><strong>MIDI score</strong> {asset?notes.length+" notes · revision "+asset.revision:"No score open"}{dirty?" · unsaved edits":""}</span>
   <button type="button" title="Open piano roll editor in a large workspace" aria-label="Open piano roll" onClick={()=>setPopOut(true)}>▦</button>
   {popOut&&createPortal(<div className="song-roll-overlay song-roll-overlay-modeless" role="presentation">
     <section className="song-piano-roll song-roll-popout song-roll-modeless" role="dialog" aria-label="MIDI piano roll editor" style={{transform:`translate(${position.x}px,${position.y}px)`}}>
       <header className="song-roll-popout-header" onPointerDown={startWindowDrag} onPointerMove={dragWindow} onPointerUp={()=>{moveWindow.current=null;}} onLostPointerCapture={()=>{moveWindow.current=null;}} title="Drag to move piano roll window"><strong>Piano roll · {notes.length} notes</strong><span>{dirty?"Unsaved edits":"Saved revision "+(asset?.revision??"")}</span>
        <button type="button" title="Close piano roll (edits stay in memory until saved or reverted)" aria-label="Close piano roll" onClick={()=>setPopOut(false)}>×</button>
       </header>
   {asset&&<div className="song-roll-instrument">
     <label>Render instrument <select aria-label="MIDI render instrument" value={selectedInstrument} onChange={e=>onInstrumentChange?.(e.target.value)}>
       {instruments.filter(x=>["sf2","sfz"].includes(x.engine)).map(item=><option key={item.pack_id+"::"+item.id} value={item.pack_id+"::"+item.id}>{item.name}</option>)}
     </select></label>
     <small>{selectedSections.length?selectedSections.length+" sections selected · one combined stereo output":"Whole saved arrangement"} · Audio L/R routing follows stem acceptance</small>
     {!!selectedSections.length&&<button type="button" title="Clear selected sections and render the complete saved arrangement" aria-label="Clear section selection" onClick={()=>setSelectedSections([])}>× Clear sections</button>}
   </div>}
   <div className="song-roll-toolbar">
    <strong>Arrangement</strong>
    <select aria-label="Saved MIDI arrangements" value={asset?.asset_id||""} onChange={e=>{if(e.target.value)void load(e.target.value);}} disabled={busy}>
     <option value="">Open saved arrangement...</option>
     {listForTrack.map(x=><option key={x.asset_id} value={x.asset_id}>{x.asset_id.slice(0,8)} · {x.note_count} notes · r{x.revision}</option>)}
    </select>
    <button type="button" onClick={()=>void refresh()} title="Refresh saved arrangements" aria-label="Refresh arrangements" disabled={busy}>↻</button>
    {asset&&<><button type="button" onClick={undo} disabled={!history.length||busy} title="Undo note edit" aria-label="Undo">↶</button>
    <button type="button" onClick={redo} disabled={!future.length||busy} title="Redo note edit" aria-label="Redo">↷</button>
    <button type="button" onClick={()=>{if(asset&&window.confirm("Revert all unsaved MIDI edits?"))open(asset);}} disabled={!dirty||busy} title="Discard unsaved edits and restore saved revision" aria-label="Revert">⟲</button>
    <button type="button" onClick={duplicateSelected} disabled={!selectedIds.length||busy} title="Duplicate selected notes" aria-label="Duplicate">⧉</button>
    <button type="button" onClick={removeSelected} disabled={!selectedIds.length||busy} title="Delete selected notes" aria-label="Delete">×</button>
    <button type="button" onClick={()=>{setSelectedIds(notes.map(n=>n.id));setSelected(notes[0]?.id||"");scrollerRef.current?.focus();}} disabled={!notes.length||busy} title="Select every note in arrangement" aria-label="All">▣</button>
    <button type="button" onClick={()=>{setSelectedIds([]);setSelected("");}} disabled={!selectedIds.length||busy} title="Clear note selection" aria-label="Clear">□</button>
    <button type="button" onClick={copySelected} disabled={!selectedIds.length||busy} title="Copy selected notes" aria-label="Copy">⎘</button>
    <button type="button" onClick={pasteSelected} disabled={!clipboard.current.length||busy} title="Paste copied notes into this arrangement" aria-label="Paste">⎗</button>
    <button type="button" onClick={()=>void save()} disabled={!dirty||busy} title="Save arrangement edits" aria-label="Save arrangement edits">▣{dirty?" *":""}</button>
    <button type="button" onClick={()=>{void onUse(asset,selectedSections,drumOptions).catch(e=>onError(String(e)));}} disabled={dirty||busy||selectedSections.length>8||(drumMode&&!!kitError)} title={selectedSections.length?"Render selected sections as individually reviewable candidates":"Render whole saved arrangement"} aria-label="Render MIDI arrangement">▶ Render</button></>}
   </div>
   {asset&&<>
    <div className="song-roll-toolbar song-roll-options">
     <label>Drums <input type="checkbox" checked={drumMode} onChange={e=>{
       const enabled=e.target.checked;
       if(notesRef.current.length&&!window.confirm("Convert notes to "+(enabled?"channel 10 percussion":"channel 1 melodic")+"? Save before rendering."))return;
       setDrumMode(enabled);
       if(notesRef.current.length)edit(notesRef.current.map(n=>({...n,channel:enabled?9:0})));
      }}/></label>
      {drumMode&&<label>Kit <select aria-label="Drum kit mapping" value={kitKind} onChange={e=>{setKitKind(e.target.value as "gm"|"custom");setKitExpanded(e.target.value==="custom");}}>
       <option value="gm" disabled={sfzSelected}>GM SoundFont</option><option value="custom">Custom / SFZ</option>
      </select></label>}
      {drumMode&&kitKind==="custom"&&<button type="button" onClick={()=>setKitExpanded(v=>!v)}>Map notes</button>}
      {kitError&&<small role="alert">{kitError}</small>}
      <label><input type="checkbox" checked={snap} onChange={e=>setSnap(e.target.checked)}/> Snap</label>
     <label>Grid <select value={gridMs} onChange={e=>setGridMs(Number(e.target.value))}><option value={125}>125 ms</option><option value={250}>250 ms</option><option value={500}>500 ms</option></select></label>
     <label>Zoom <select aria-label="Piano roll horizontal zoom" value={pixelsPerSecond} onChange={e=>{const next=Number(e.target.value);const scroller=scrollerRef.current;const center=scroller?(scroller.scrollLeft+scroller.clientWidth/2-keyWidth)/pixelsPerSecond:0;setPixelsPerSecond(next);if(scroller)requestAnimationFrame(()=>{scroller.scrollLeft=Math.max(0,keyWidth+center*next-scroller.clientWidth/2);});}}><option value={24}>Overview</option><option value={65}>Normal</option><option value={130}>Close</option><option value={260}>Detail</option></select></label>
     <span>{dirty?"Unsaved changes":("Saved revision "+asset.revision)}</span>
     {active&&<label>{selectedIds.length>1?"Selection velocity":"Velocity"} <input type="number" min={1} max={127} value={active.velocity} onChange={e=>{const velocity=Number(e.target.value);if(Number.isInteger(velocity)&&velocity>=1&&velocity<=127){const ids=new Set(selectedIds);edit(notesRef.current.map(n=>ids.has(n.id)?{...n,velocity}:n));}}}/></label>}
     <span>{selectedIds.length} notes selected · {selectedSections.length} sections selected</span>
    </div>
    {drumMode&&kitKind==="custom"&&kitExpanded&&<div className="song-roll-toolbar song-roll-options">
      <label>Kit note mappings <textarea aria-label="Custom drum keymap" rows={5} value={kitText}
       placeholder={"36 = Kick\n38 = Snare\n42 = Closed Hat"} onChange={e=>setKitText(e.target.value)}/></label>
      <small>Use playable SFZ note pitches. Labels do not remap samples.</small>
     </div>}
     <div className="song-roll-scroller" ref={scrollerRef} tabIndex={0} aria-label="Piano roll; click empty grid to add notes, drag notes to move, drag right edge to resize"
     onKeyDown={e=>{if(e.target!==e.currentTarget)return;
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="a"){e.preventDefault();setSelectedIds(notes.map(n=>n.id));setSelected(notes[0]?.id||"");}
      if(e.key==="Escape"){e.preventDefault();setSelectedIds([]);setSelected("");}
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
     {asset&&<div className="song-roll-time-sections" style={{width,height:32}} aria-label="Song sections, aligned with the MIDI timeline">
       <span className="song-roll-time-key" title="Ctrl or Shift click adds; Alt click selects all of this section type.">§</span>
       {visibleSections.map(section=>{
         const localStart=Math.max(0,section.start_seconds*RATE-asset.source.start_sample);
         const localEnd=Math.min(asset.duration_samples,section.end_seconds*RATE-asset.source.start_sample);
         const left=toX(localStart);
         const span=(localEnd-localStart)/RATE*pixelsPerSecond;
         return <button key={section.id} type="button"
           style={{left,width:Math.max(7,span)}}
           className={selectedSections.includes(section.id)?"is-selected":""}
           aria-pressed={selectedSections.includes(section.id)}
           title={section.kind+(section.number?" "+section.number:"")+" · "+section.start_seconds.toFixed(2)+"-"+section.end_seconds.toFixed(2)+"s · Alt-click selects all "+section.kind+" sections"}
           onClick={event=>chooseSection(section,event)}>
           {section.kind}{section.number?" "+section.number:""}
         </button>;
       })}
     </div>}
     <svg width={width} height={height} role="img" aria-label="Editable piano roll">
      {Array.from({length:topPitch-PITCH_LOW+1},(_,i)=>{const p=topPitch-i;return <g key={p}>
       <rect x={0} y={i*ROW} width={width} height={ROW} fill={p%12===1||p%12===3||p%12===6||p%12===8||p%12===10?"#252e3b":"#303d4a"} stroke="#536171" strokeWidth=".3"/>
       <rect x={0} y={i*ROW} width={keyWidth} height={ROW} fill={p%12===1||p%12===3||p%12===6||p%12===8||p%12===10?"#8897a7":"#e2e7eb"} />
       <text x={4} y={i*ROW+12} fill="#111b22" fontSize="11">{drumMode?(kitNames.get(p)||('Note '+p)):pitchLabel(p)}</text>
       <rect x={keyWidth} y={i*ROW} width={width-keyWidth} height={ROW} fill="transparent" onClick={e=>{const box=e.currentTarget.ownerSVGElement?.getBoundingClientRect();const scale=box?width/box.width:1;const local=(e.clientX-(box?.left||0))*scale;addAt(local,p);}}/>
      </g>;})}
      {Array.from({length:Math.ceil((width-KEY_WIDTH)/(pixelsPerSecond*.5))+1},(_,i)=><line key={i} x1={keyWidth+i*pixelsPerSecond*.5} y1={0} x2={keyWidth+i*pixelsPerSecond*.5} y2={rollHeight} stroke="#a7c0ce" strokeOpacity={i%2===0?.35:.12} pointerEvents="none"/>)}
      {notes.map(note=>{const x=toX(note.start_sample),w=Math.max(3,toX(note.end_sample)-x),y=toY(note.pitch);if(note.pitch<PITCH_LOW||note.pitch>topPitch)return null;return <g key={note.id}>
       <rect x={x} y={y+2} width={w} height={ROW-4} rx={2} fill={selectedIds.includes(note.id)?"#e3b965":"#70bbaf"} stroke="#d6eee7" strokeWidth={1} onPointerDown={e=>startDrag(e,note,"move")} onPointerMove={moveDrag} onPointerUp={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}/>
       <rect x={x+Math.max(0,w-6)} y={y+2} width={Math.min(6,w)} height={ROW-4} fill="#467f82" onPointerDown={e=>startDrag(e,note,"resize")} onPointerMove={moveDrag} onPointerUp={()=>{drag.current=null;}} onLostPointerCapture={()=>{drag.current=null;}}/>
      </g>;})}
      <rect x={0} y={rollHeight} width={width} height={VELOCITY_HEIGHT} fill="#192633" stroke="#536171" strokeWidth={1}/>
      <text x={4} y={rollHeight+14} fill="#e2e7eb" fontSize={11}>Velocity</text>
      {[32,64,96,127].map(v=><line key={v} x1={keyWidth} x2={width} y1={rollHeight+VELOCITY_HEIGHT-8-(v/127)*(VELOCITY_HEIGHT-18)} y2={rollHeight+VELOCITY_HEIGHT-8-(v/127)*(VELOCITY_HEIGHT-18)} stroke="#8196a5" strokeOpacity={.25} pointerEvents="none"/>)}
      {notes.map(note=>{
       const x=toX(note.start_sample), barWidth=Math.max(5,Math.min(12,toX(note.end_sample)-x));
       const heightValue=note.velocity/127*(VELOCITY_HEIGHT-18);
       return <rect key={"velocity-"+note.id} x={x} y={rollHeight+VELOCITY_HEIGHT-8-heightValue}
        width={barWidth} height={Math.max(2,heightValue)} fill={selectedIds.includes(note.id)?"#e3b965":"#70bbaf"}
        stroke="#d6eee7" strokeWidth={.5} aria-label={"Velocity "+note.velocity+" for "+pitchLabel(note.pitch)}
        onPointerDown={e=>startVelocity(e,note)} onPointerMove={moveVelocity}
        onPointerUp={()=>{velocityDrag.current=null;}} onLostPointerCapture={()=>{velocityDrag.current=null;}}/>;
      })}
     </svg>
    </div>
    <small>Click grid to add; drag notes to move or resize. Shift-click to select multiple notes; drag selection to move together. Ctrl+A selects all; Escape clears selection. Arrow keys nudge selected notes (left/right by grid interval, up/down by semitone); Delete removes and Ctrl+D duplicates, Ctrl+C/V copies and pastes. Drag the velocity bars beneath the notes to edit one note or the selected group. Undo/redo and Revert remain available. Snap is off by default. Saved arrangements render with configured SF2 or SFZ instruments; drum mode uses explicit kit note mappings; ensemble lanes are future work. {notes.length} notes, {(asset.duration_samples/RATE).toFixed(2)}s.</small>
   </>}
   {!asset&&<small>Save an extracted MIDI arrangement, then open it here. Select a configured SF2 or SFZ instrument and render from the editor.</small>}
   {message&&<small role="status">{message}</small>}
  </section></div>,document.body)}
 </div>;
}
