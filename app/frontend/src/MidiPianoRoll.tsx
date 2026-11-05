import {useEffect,useRef,useState} from "react";
import {createPortal} from "react-dom";
import type {PointerEvent as ReactPointerEvent, MouseEvent as ReactMouseEvent} from "react";
import type {SongSection} from "./SectionEditor";

export type RollNote={id:string;start_sample:number;end_sample:number;pitch:number;velocity:number;channel:number};
export type Arrangement={asset_id:string;revision:number;sample_rate:number;duration_samples:number;source:{track_id:string;start_sample:number;candidate_id?:string;method?:string};notes:RollNote[];percussion?:{mode:"drums";keymap:NonNullable<DrumOptions["drum_keymap"]>};instrument_sections?:SavedInstrumentRecipe};
type Summary={asset_id:string;revision:number;source:Arrangement["source"];note_count:number;duration_samples:number};
type Operation={op:"add";note:RollNote}|{op:"remove";id:string}|{op:"update";id:string;changes:Partial<Omit<RollNote,"id">>};
type InstrumentOption={id:string;pack_id:string;name:string;engine:string};
type ProposalPart="Bass"|"Drums"|"Guitar"|"Piano"|"Other";
type MidiProposal={
 schema_version:number;base_revision:number;source_track_id:string;target_stem:ProposalPart;
 sections:{section_id:string;intent:string}[];
 operations:Operation[];instrument_sections:SavedInstrumentRecipe|null;
};
type ProposalReview={
 status:string;base_revision:number;note_diff:{added:RollNote[];removed:RollNote[];
 changed:{before:RollNote;after:RollNote}[]};
 instrument_before:SavedInstrumentRecipe|null;instrument_after:SavedInstrumentRecipe|null;
 selected_sections:string[];mutated:boolean;
};
type MockProposalResponse={provider:string;proposal:MidiProposal;review:ProposalReview};

type InstrumentRef={pack_id:string;instrument_id:string};
type SavedInstrumentRecipe={schema_version:1;default:InstrumentRef;section_ids:string[];
 overrides:({section_id:string}&InstrumentRef)[]};
type MatchAssignment={pack_id:string;instrument_id:string;instrument_name?:string;variant:string;section:string;evidence:string};
type DirectionMatch={status:"matched"|"ambiguous"|"no_family_match";family?:{pack_id:string;name:string;evidence:string};
 families?:{pack_id:string;name:string;evidence:string}[];assignments:MatchAssignment[];
 conflicts?:{section:string;candidates:MatchAssignment[]}[];unresolved_text:string;rule?:string};

export type DrumOptions={
 percussion:boolean;
 drum_keymap:{schema_version:number;mapping_kind:"gm"|"custom";lanes:{pitch:number;name:string}[]}|null;
 section_instruments?:{section_id:string;pack_id:string;instrument_id:string}[];
};
const GM_KIT:Record<number,string>={"35":"Acoustic Bass Drum","36":"Bass Drum 1","37":"Side Stick","38":"Acoustic Snare","39":"Hand Clap","40":"Electric Snare","41":"Low Floor Tom","42":"Closed Hi-Hat","43":"High Floor Tom","44":"Pedal Hi-Hat","45":"Low Tom","46":"Open Hi-Hat","47":"Low-Mid Tom","48":"Hi-Mid Tom","49":"Crash Cymbal 1","50":"High Tom","51":"Ride Cymbal 1","52":"Chinese Cymbal","53":"Ride Bell","54":"Tambourine","55":"Splash Cymbal","56":"Cowbell","57":"Crash Cymbal 2","58":"Vibraslap","59":"Ride Cymbal 2","60":"Hi Bongo","61":"Low Bongo","62":"Mute Hi Conga","63":"Open Hi Conga","64":"Low Conga","65":"High Timbale","66":"Low Timbale","67":"High Agogo","68":"Low Agogo","69":"Cabasa","70":"Maracas","71":"Short Whistle","72":"Long Whistle","73":"Short Guiro","74":"Long Guiro","75":"Claves","76":"Hi Wood Block","77":"Low Wood Block","78":"Mute Cuica","79":"Open Cuica","80":"Mute Triangle","81":"Open Triangle"};
type Props={jobId:string;sourceTrackId:string;targetStem?:string;requestedAssetId?:string;sections?:SongSection[];instruments?:InstrumentOption[];selectedInstrument?:string;onInstrumentChange?:(key:string)=>void;onDirtyChange?:(dirty:boolean)=>void;onUse:(asset:Arrangement,sectionIds:string[],options:DrumOptions)=>Promise<void>;onError:(error:string)=>void};
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
export function MidiPianoRoll({jobId,sourceTrackId,targetStem="Other",requestedAssetId,sections=[],instruments=[],selectedInstrument="",onInstrumentChange,onDirtyChange,onUse,onError}:Props){
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
 const [sectionPresetKeys,setSectionPresetKeys]=useState<Record<string,string>>({});
 const [directionText,setDirectionText]=useState("");
 const [directionBusy,setDirectionBusy]=useState(false);
 const [directionMatch,setDirectionMatch]=useState<DirectionMatch|null>(null);
 const [directionError,setDirectionError]=useState("");
 const [inspector,setInspector]=useState<"mapping"|"diff"|"presets"|"test"|null>(null);
 useEffect(()=>{
  const direction=directionText.trim();
  if(!direction){setDirectionMatch(null);return;}
  let live=true;
  const controller=new AbortController();
  const timer=window.setTimeout(()=>{
   void request<DirectionMatch>("/api/instruments/match-direction",{
    method:"POST",headers:{"Content-Type":"application/json"},
    signal:controller.signal,body:JSON.stringify({instruction:direction})
   }).then(result=>{if(live)setDirectionMatch(result);})
     .catch(error=>{if(live&&!(error instanceof DOMException&&error.name==="AbortError"))
       setDirectionError(String(error));});
  },400);
  return()=>{live=false;window.clearTimeout(timer);controller.abort();};
 },[directionText]);
 const [proposalPart,setProposalPart]=useState<ProposalPart>("Bass");
 const [mockVelocity,setMockVelocity]=useState(5);
 const [proposalBusy,setProposalBusy]=useState(false);
 const [proposalDraft,setProposalDraft]=useState<MockProposalResponse|null>(null);
 const [proposalError,setProposalError]=useState("");


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
 const noteDirty=asset!==null&&diffNotes(asset.notes,notes).length>0;
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
 const sectionInstruments=selectedSections.flatMap(sectionId=>{
  const key=sectionPresetKeys[sectionId];
  if(!key||key===selectedInstrument)return [];
  const instrument=instruments.find(item=>item.pack_id+"::"+item.id===key);
  return instrument?[{section_id:sectionId,pack_id:instrument.pack_id,instrument_id:instrument.id}]:[];
 });
 const drumOptions:DrumOptions={percussion:drumMode,
  drum_keymap:drumMode?{schema_version:1,mapping_kind:kitKind,lanes:kitLanes}:null,
  ...(selectedSections.length?{section_instruments:sectionInstruments}:{})};
 const currentDefault=selectedInstrument;
 const defaultItem=instruments.find(item=>item.pack_id+"::"+item.id===currentDefault);
 const desiredInstrumentSections:SavedInstrumentRecipe|null=selectedSections.length&&defaultItem?{
  schema_version:1,default:{pack_id:defaultItem.pack_id,instrument_id:defaultItem.id},
  section_ids:[...selectedSections].sort(),
  overrides:sectionInstruments.slice().sort((a,b)=>a.section_id.localeCompare(b.section_id))
 }:null;
 const presetDirty=asset!==null&&JSON.stringify(asset.instrument_sections||null)!==JSON.stringify(desiredInstrumentSections);
 const desiredPercussion=drumMode?{mode:"drums",keymap:drumOptions.drum_keymap}:null;
 const metadataDirty=asset!==null&&JSON.stringify(asset.percussion||null)!==JSON.stringify(desiredPercussion);
 const dirty=noteDirty||metadataDirty||presetDirty;
 useEffect(()=>{onDirtyChange?.(dirty);},[dirty,onDirtyChange]);
 useEffect(()=>{
  if(!dirty)return;
  const guard=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue="";};
  window.addEventListener("beforeunload",guard);
  return()=>window.removeEventListener("beforeunload",guard);
 },[dirty]);

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
  setNotes(updated);notesRef.current=updated;setProposalDraft(null);
 }
 function undo(){if(!history.length)return;setFuture(v=>[clone(notesRef.current),...v]);const last=history[history.length-1];setHistory(v=>v.slice(0,-1));edit(clone(last),false);}
 function redo(){if(!future.length)return;setHistory(v=>[...v,clone(notesRef.current)]);const first=future[0];setFuture(v=>v.slice(1));edit(clone(first),false);}
 function open(value:Arrangement){setProposalDraft(null);setProposalError("");
  setSelectedSections(value.instrument_sections?.section_ids||[]);
  setSectionPresetKeys(Object.fromEntries((value.instrument_sections?.overrides||[]).map(row=>[
   row.section_id,row.pack_id+"::"+row.instrument_id])));
  if(value.instrument_sections)onInstrumentChange?.(value.instrument_sections.default.pack_id+"::"+value.instrument_sections.default.instrument_id);
  setDirectionMatch(null);setDirectionError("");setDirectionText("");setInspector(null);
  const saved=value.percussion?.keymap;
  setDrumMode(Boolean(value.percussion)||(value.notes.length>0&&value.notes.every(n=>n.channel===9)));
  setKitKind(saved?.mapping_kind||"gm");
  setKitText(saved?.mapping_kind==="custom"?saved.lanes.map(l=>l.pitch+" = "+l.name).join("\n"):"");
  setKitExpanded(false);setAsset(value);edit(clone(value.notes),false);setHistory([]);setFuture([]);setSelected("");setSelectedIds([]);setMessage("");}
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
  if(!operations.length&&!metadataDirty&&!presetDirty){setMessage("No unsaved changes.");return;}
  if(drumMode&&kitError){onError(kitError);return;}
  if(selectedSections.length&&(!defaultItem||!["sf2","sfz"].includes(defaultItem.engine))){onError("Select an installed SF2 or SFZ default preset.");return;}
  if(selectedSections.some(id=>!sections.some(s=>s.id===id))){onError("Saved section no longer exists.");return;}
  setBusy(true);try{const saved=await request<Arrangement>(root+"/"+asset.asset_id,{
   method:"PATCH",headers:{"Content-Type":"application/json"},
   body:JSON.stringify({base_revision:asset.revision,operations,update_percussion:metadataDirty,
    percussion:desiredPercussion,update_instrument_sections:presetDirty,
    instrument_sections:desiredInstrumentSections})});
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
  const start=fromX(x),end=Math.min(asset.duration_samples,start+RATE*(drumMode ? 0.15 : 0.5));
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
   setProposalDraft(null);setProposalError("");
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
 const matchSections=selectedSections.length?visibleSections.filter(s=>selectedSections.includes(s.id)):visibleSections;
 const wholeSongScope=selectedSections.length===0;
 const scopeLabel=wholeSongScope?"Whole saved arrangement ("+visibleSections.length+" sections)":
  selectedSections.length+" selected song sections";
 const scopeIds=matchSections.map(s=>s.id);
 const scopeError=matchSections.some(s=>asset&&(
  s.start_seconds<asset.source.start_sample/RATE-.005||
  s.end_seconds>(asset.source.start_sample+asset.duration_samples)/RATE+.005))
  ?"A song section extends beyond this MIDI arrangement. Select fully contained sections or extend the score.":"";

 const mappingReady=directionMatch?.status==="matched"&&
  directionMatch.assignments.some(row=>row.section==="default");
 const mappingState=directionBusy?"working":mappingReady?"ready":
  directionError||proposalError||(directionMatch&&directionMatch.status!=="matched")
   ?"error":directionText.trim()?"unchecked":"empty";
 async function generateDirectionProposal(){
  if(!asset||!directionText.trim()||dirty||busy||proposalBusy||!scopeIds.length||scopeError)return;
  setDirectionBusy(true);setProposalBusy(true);setDirectionError("");setProposalError("");
  setProposalDraft(null);setDirectionMatch(null);
  try{
   const result=await request<MockProposalResponse&{mapping:DirectionMatch}>(
    root+"/"+asset.asset_id+"/proposal-direction",{
    method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({base_revision:asset.revision,source_track_id:asset.source.track_id,
      target_stem:["bass","drums","guitar","piano","other"].includes(targetStem.toLowerCase())?targetStem:"Other",
      instruction:directionText.trim(),section_ids:scopeIds})});
   setDirectionMatch(result.mapping);setProposalDraft(result);
   setMessage("Preset proposal ready to accept. MIDI notes unchanged.");
  }catch(error){setDirectionError(String(error));setProposalError(String(error));}
  finally{setDirectionBusy(false);setProposalBusy(false);}
 }
 async function makeMockProposal(){
  if(!asset||dirty||proposalBusy||busy||!scopeIds.length||scopeError)return;
  setProposalBusy(true);setProposalError("");setProposalDraft(null);
  try{
   const result=await request<MockProposalResponse>(
    root+"/"+asset.asset_id+"/proposal-mock",{
     method:"POST",headers:{"Content-Type":"application/json"},
     body:JSON.stringify({base_revision:asset.revision,source_track_id:asset.source.track_id,
      target_stem:proposalPart,section_ids:scopeIds,velocity_delta:mockVelocity})});
   setProposalDraft(result);
  }catch(error){setProposalError(String(error));}
  finally{setProposalBusy(false);}
 }
 async function acceptProposal(){
  if(!asset||!proposalDraft||proposalBusy||busy||dirty)return;
  if(proposalDraft.proposal.base_revision!==asset.revision){
   setProposalError("Saved score changed. Generate a fresh proposal.");setProposalDraft(null);return;
  }
  // The explicit checkmark is acceptance. Do not add a second modal for
  // a reversible, revisioned score update.
  setProposalBusy(true);setProposalError("");
  try{
   const response=await request<{asset:Arrangement;accepted:boolean}>(
    root+"/"+asset.asset_id+"/proposal-accept",{
     method:"POST",headers:{"Content-Type":"application/json"},
     body:JSON.stringify(proposalDraft.proposal)});
   open(response.asset);
   setMessage("Proposal saved as MIDI revision "+response.asset.revision+". Render to audition.");
   void refresh();
  }catch(error){setProposalError(String(error));setProposalDraft(null);}
  finally{setProposalBusy(false);}
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
     <section className="song-piano-roll song-roll-popout song-roll-modeless" role="dialog" aria-label="MIDI piano roll editor"
       onPointerDown={event=>{if(inspector&&!(event.target as HTMLElement).closest(".song-roll-inspector,.song-roll-status-icon"))setInspector(null);}}
       onKeyDown={event=>{if(event.key==="Escape"&&inspector){event.stopPropagation();setInspector(null);}}}
       style={{transform:`translate(${position.x}px,${position.y}px)`}}>
       <header className="song-roll-popout-header" onPointerDown={startWindowDrag} onPointerMove={dragWindow} onPointerUp={()=>{moveWindow.current=null;}} onLostPointerCapture={()=>{moveWindow.current=null;}} title="Drag to move piano roll window"><strong>Piano roll · {notes.length} notes</strong><span>{dirty?"Unsaved edits":"Saved revision "+(asset?.revision??"")}</span>
        <button type="button" title="Close piano roll (edits stay in memory until saved or reverted)" aria-label="Close piano roll" onClick={()=>setPopOut(false)}>×</button>
       </header>
   {asset&&<div className="song-roll-direction-row">
     <textarea aria-label="Instrument direction" rows={2}
      placeholder="Describe the instrument and how it should change..."
      value={directionText}
      onChange={e=>{setDirectionText(e.target.value);setDirectionMatch(null);setProposalDraft(null);setDirectionError("");setProposalError("");}}/>
     <button className="song-roll-primary-action" type="button"
      title="Generate a reviewable proposal for installed instrument presets"
      disabled={!directionText.trim()||busy||proposalBusy||dirty||!scopeIds.length||!!scopeError}
      onClick={()=>void generateDirectionProposal()}>{proposalBusy?"Generating...":"Generate proposal"}</button>
     <button className={"song-roll-status-icon is-"+mappingState} type="button"
      title={mappingReady?"Instrument presets identified. Click to inspect":"Inspect instrument mapping status"}
      aria-label="Inspect instrument mapping" aria-expanded={inspector==="mapping"}
      onClick={()=>setInspector(inspector==="mapping"?null:"mapping")}>◈</button>
     <button className={"song-roll-status-icon"+(proposalDraft?" is-ready":"")} type="button"
      title="Inspect proposal changes" aria-label="Inspect proposal changes"
      aria-expanded={inspector==="diff"}
      onClick={()=>setInspector(inspector==="diff"?null:"diff")}>≡</button>
     <button className="song-roll-status-icon" type="button"
      title="Inspect section presets" aria-label="Inspect section presets"
      aria-expanded={inspector==="presets"}
      onClick={()=>setInspector(inspector==="presets"?null:"presets")}>⚙</button>
     {proposalDraft&&<>
      <button type="button" className="song-roll-accept-action"
       title="Accept proposal into the saved MIDI score. Audio remains unchanged."
       aria-label="Accept proposal" disabled={busy||proposalBusy||dirty}
       onClick={()=>void acceptProposal()}>✓</button>
      <button type="button" className="song-roll-status-icon"
       title="Discard proposal" aria-label="Discard proposal"
       onClick={()=>{setProposalDraft(null);setDirectionMatch(null);setInspector(null);}}>×</button>
     </>}
   </div>}
   {asset&&<div className="song-roll-compact-status" aria-live="polite">
      <span title="Scope: select timeline sections below to narrow">{scopeLabel}</span>
      {selectedSections.length>0&&<button type="button" title="Use whole arrangement" aria-label="Use whole arrangement"
       onClick={()=>{setSelectedSections([]);setProposalDraft(null);setInspector(null);}}>↺</button>}
      {(scopeError||proposalError||directionError)&&<button type="button" className="song-roll-error-trigger"
       title={scopeError||proposalError||directionError} onClick={()=>setInspector("mapping")}>! Inspect</button>}
      {dirty&&<span>Unsaved changes</span>}
      {proposalDraft&&<span>Proposal ready</span>}
   </div>}
   {asset&&inspector&&<aside className="song-roll-inspector"
     aria-label={inspector==="mapping"?"Instrument mapping details":inspector==="diff"?"MIDI proposal details":inspector==="presets"?"Instrument presets":"Test proposal"}
     onKeyDown={e=>{if(e.key==="Escape"){e.stopPropagation();setInspector(null);}}}>
      <header><strong>{inspector==="mapping"?"Instrument mapping":inspector==="diff"?"Proposal details":
       inspector==="presets"?"Instrument presets":"Test tools"}</strong>
       <button type="button" title="Close inspector" aria-label="Close inspector" onClick={()=>setInspector(null)}>×</button>
      </header>
      {inspector==="mapping"&&<>
       {directionMatch?.family&&<strong>{directionMatch.family.name}</strong>}
       {directionMatch?.assignments.map((row,index)=><div key={index}>
        {row.section==="default"?"Default":row.section}: {row.instrument_name||row.variant}</div>)}
       {directionMatch?.conflicts?.map((row,index)=><div key={index} role="alert">Conflict: {row.section}</div>)}
       {!directionMatch&&<p>{directionError||"Generate a proposal to identify available presets."}</p>}
       <small>Identifies installed presets only. Musical direction beyond preset selection requires a composition model.</small>
      </>}
      {inspector==="diff"&&<>
       {!proposalDraft?<p>No proposal yet.</p>:<>
        <strong>{proposalDraft.provider==="library_mapping"?"Preset mapping proposal":"Offline test proposal"}</strong>
        <div>{proposalDraft.review.selected_sections.length} sections,
         {proposalDraft.review.note_diff.added.length} added,
         {proposalDraft.review.note_diff.removed.length} removed,
         {proposalDraft.review.note_diff.changed.length} changed notes</div>
        {proposalDraft.proposal.instrument_sections&&<>
         <div>Default: {instruments.find(x=>x.pack_id===proposalDraft.proposal.instrument_sections?.default.pack_id&&x.id===proposalDraft.proposal.instrument_sections?.default.instrument_id)?.name||"Installed instrument"}</div>
         {proposalDraft.proposal.instrument_sections.overrides.map(row=><div key={row.section_id}>
          {sections.find(s=>s.id===row.section_id)?.kind||row.section_id}: {instruments.find(x=>x.id===row.instrument_id&&x.pack_id===row.pack_id)?.name||row.instrument_id}
         </div>)}
        </>}
        {proposalDraft.review.note_diff.changed.slice(0,40).map(row=><div key={row.before.id}>
         MIDI {row.before.pitch} @ {(row.before.start_sample/RATE).toFixed(2)}s:
         {row.before.velocity} to {row.after.velocity}</div>)}
       </>}
      </>}
      {inspector==="presets"&&<>
        <label>Default <select aria-label="Default instrument" value={selectedInstrument}
         onChange={e=>onInstrumentChange?.(e.target.value)}>
          {instruments.filter(x=>["sf2","sfz"].includes(x.engine)).map(x=><option key={x.pack_id+"::"+x.id} value={x.pack_id+"::"+x.id}>{x.name}</option>)}
        </select></label>
        <div>{scopeLabel}</div>
        {matchSections.map(section=><label key={section.id}>
         {section.kind}{section.number?" "+section.number:""}
         <select aria-label={"Instrument for "+section.kind+" "+(section.number||"")}
          value={sectionPresetKeys[section.id]||""}
          onChange={e=>setSectionPresetKeys(previous=>({...previous,[section.id]:e.target.value}))}>
          <option value="">Default</option>
          {instruments.filter(x=>["sf2","sfz"].includes(x.engine)).map(x=><option key={x.pack_id+"::"+x.id} value={x.pack_id+"::"+x.id}>{x.name}</option>)}
         </select>
        </label>)}
        <button type="button" disabled={!dirty||busy} onClick={()=>void save()}>Save presets</button>
        <button type="button" title="Open offline mock test tools" aria-label="Open test tools"
         onClick={()=>setInspector("test")}>⚙ Test</button>
      </>}
      {inspector==="test"&&<>
       <small>Offline test only. Adjusts velocity, not musical arrangement.</small>
       <label>Part <select value={proposalPart} aria-label="Mock proposal part"
        onChange={e=>setProposalPart(e.target.value as ProposalPart)}>
        {(["Bass","Drums","Guitar","Piano","Other"] as const).map(x=><option key={x}>{x}</option>)}
       </select></label>
       <label>Velocity <input type="number" min={-20} max={20} value={mockVelocity}
        onChange={e=>setMockVelocity(Number(e.target.value))}/></label>
       <button type="button" disabled={!scopeIds.length||dirty||busy||proposalBusy||mockVelocity===0||Math.abs(mockVelocity)>20}
        onClick={()=>void makeMockProposal()}>Generate mock</button>
      </>}
   </aside>}
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
    <button type="button" onClick={()=>{void onUse(asset,selectedSections,drumOptions).catch(e=>onError(String(e)));}} disabled={dirty||busy||selectedSections.length>64||(drumMode&&!!kitError)} title={selectedSections.length?"Render selected sections as individually reviewable candidates":"Render whole saved arrangement"} aria-label="Render MIDI arrangement">▶ Render</button></>}
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
     <span>{selectedIds.length} notes selected · {scopeLabel}</span>
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
