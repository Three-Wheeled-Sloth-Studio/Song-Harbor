import { useEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

export type SongSection = {
  id: string; kind: string; number: number | null;
  start_seconds: number; end_seconds: number;
};
const kinds = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Instrumental", "Guitar Solo", "Outro", "End"];
const MIN_LENGTH = 0.1;
function clamp(x:number,min:number,max:number) {return Math.min(max,Math.max(min,x));}
function stamp(seconds:number) {
  const minutes=Math.floor(seconds/60);
  return `${minutes}:${(seconds%60).toFixed(2).padStart(5,"0")}`;
}
type Drag = {id:string; mode:"move"|"start"|"end"; x:number; original:SongSection; originals:SongSection[]; limits:[number,number]; width:number; changed:boolean};

export function SectionEditor({jobId,duration,position,initialSections,onSeek,viewStart=0,viewEnd=duration,onSectionsChange,onPersisted,onSectionDoubleClick,externalSections}:{
  jobId:string; duration:number; position:number; initialSections?:SongSection[]; onSeek:(seconds:number)=>void; viewStart?:number; viewEnd?:number; onSectionsChange?:(sections:SongSection[])=>void; onPersisted?:()=>void; onSectionDoubleClick?:(s:SongSection)=>void; externalSections?:SongSection[];
}) {
  const [sections,setSections]=useState<SongSection[]>(initialSections||[]);
  const [kind,setKind]=useState("Chorus");
  const [number,setNumber]=useState("");
  const [start,setStart]=useState<number|null>(null);
  const [end,setEnd]=useState<number|null>(null);
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  const [selected,setSelected]=useState<string|null>(null);
  const drag=useRef<Drag|null>(null);
  const sectionsRef=useRef(sections);
  const localRevision=useRef(false);
  const currentJob=useRef(jobId);
  sectionsRef.current=sections;
  useEffect(()=>{
    if(currentJob.current!==jobId){
      currentJob.current=jobId;
      localRevision.current=false;
      setStart(null);setEnd(null);setSelected(null);
    }
    // A delayed parent project refresh must never overwrite sections just imported.
    if(!localRevision.current)setSections(initialSections||[]);
  },[jobId,initialSections]);
  useEffect(()=>{onSectionsChange?.(sections);},[sections,onSectionsChange]);
  useEffect(()=>{
    if(externalSections){
      localRevision.current=true;
      setSections(externalSections);
      setSelected(null);
    }
  },[externalSections]);

  async function persist(next:SongSection[],rollback:SongSection[]=sectionsRef.current) {
    setBusy(true);setError("");setMessage("");
    try {
      const response=await fetch(`/api/projects/${jobId}/sections`,{
        method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({sections:next})
      });
      const result=await response.json() as {sections?:SongSection[],detail?:string};
      if(!response.ok||!result.sections) throw new Error(result.detail||"Could not save sections");
      localRevision.current=true;
      setSections(result.sections);setStart(null);setEnd(null);
      setMessage("Sections saved");
      onPersisted?.();
    } catch(e) {setSections(rollback);setError(e instanceof Error?e.message:"Could not save sections");}
    finally {setBusy(false);}
  }

  function bounds(id:string):[number,number] {
    const ordered=[...sectionsRef.current].sort((a,b)=>a.start_seconds-b.start_seconds);
    const index=ordered.findIndex(s=>s.id===id);
    return [index>0?ordered[index-1].end_seconds:0,
            index<ordered.length-1?ordered[index+1].start_seconds:duration];
  }
  function reposition(base:SongSection,mode:Drag["mode"],delta:number,limits:[number,number]):SongSection {
    const size=base.end_seconds-base.start_seconds;
    let first=base.start_seconds, last=base.end_seconds;
    if(mode==="move") {first=clamp(base.start_seconds+delta,limits[0],limits[1]-size);last=first+size;}
    if(mode==="start") first=clamp(base.start_seconds+delta,limits[0],last-MIN_LENGTH);
    if(mode==="end") last=clamp(base.end_seconds+delta,first+MIN_LENGTH,limits[1]);
    return {...base,start_seconds:Math.round(first*1000)/1000,end_seconds:Math.round(last*1000)/1000};
  }
  function moveBoundary(items:SongSection[],section:SongSection,mode:Drag["mode"],delta:number):SongSection[] {
    const ordered=[...items].sort((a,b)=>a.start_seconds-b.start_seconds);
    const index=ordered.findIndex(s=>s.id===section.id);
    if(index<0)return items;
    const prev=index>0?ordered[index-1]:null;
    const next=index<ordered.length-1?ordered[index+1]:null;
    const sharedStart=mode==="start"&&prev&&Math.abs(prev.end_seconds-section.start_seconds)<0.005;
    const sharedEnd=mode==="end"&&next&&Math.abs(next.start_seconds-section.end_seconds)<0.005;
    if(sharedStart){
      const at=Math.round(clamp(section.start_seconds+delta,prev.start_seconds+MIN_LENGTH,
                              section.end_seconds-MIN_LENGTH)*1000)/1000;
      return items.map(s=>s.id===section.id?{...s,start_seconds:at}:
        s.id===prev.id?{...s,end_seconds:at}:s);
    }
    if(sharedEnd){
      const at=Math.round(clamp(section.end_seconds+delta,section.start_seconds+MIN_LENGTH,
                              next.end_seconds-MIN_LENGTH)*1000)/1000;
      return items.map(s=>s.id===section.id?{...s,end_seconds:at}:
        s.id===next.id?{...s,start_seconds:at}:s);
    }
    const idx=ordered.findIndex(s=>s.id===section.id);
    const limits:[number,number]=[
      idx>0?ordered[idx-1].end_seconds:0,
      idx<ordered.length-1?ordered[idx+1].start_seconds:duration
    ];
    const changed=reposition(section,mode,delta,limits);
    return items.map(s=>s.id===section.id?changed:s);
  }
  function beginDrag(e:ReactPointerEvent<HTMLDivElement>,section:SongSection,mode:Drag["mode"]) {
    if(busy||duration<=0) return;
    e.preventDefault();e.stopPropagation();
    const width=e.currentTarget.closest("[data-section-lane]")?.getBoundingClientRect().width||1;
    drag.current={id:section.id,mode,x:e.clientX,original:section,originals:[...sectionsRef.current],limits:bounds(section.id),width,changed:false};
    setSelected(section.id);
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function moveDrag(e:ReactPointerEvent<HTMLDivElement>) {
    const d=drag.current;
    if(!d) return;
    const delta=(e.clientX-d.x)/d.width*(viewEnd-viewStart);
    const next=moveBoundary(d.originals,d.original,d.mode,delta);
    d.changed=d.changed||next.some(s=>{
      const before=d.originals.find(x=>x.id===s.id);
      return before?.start_seconds!==s.start_seconds||before?.end_seconds!==s.end_seconds;
    });
    setSections(next);
  }
  function finishDrag(e:ReactPointerEvent<HTMLDivElement>) {
    const d=drag.current;
    if(!d) return;
    moveDrag(e);
    const delta=(e.clientX-d.x)/d.width*(viewEnd-viewStart);
    const candidate=moveBoundary(d.originals,d.original,d.mode,delta);
    drag.current=null;
    if(candidate.some(s=>{
      const before=d.originals.find(x=>x.id===s.id);
      return before?.start_seconds!==s.start_seconds||before?.end_seconds!==s.end_seconds;
    }))void persist(candidate,d.originals);
  }
  function nudge(section:SongSection,mode:Drag["mode"],direction:number) {
    if(busy) return;
    const candidate=moveBoundary(sections,section,mode,direction*0.1);
    if(candidate.some(s=>{
      const before=sections.find(x=>x.id===s.id);
      return before?.start_seconds!==s.start_seconds||before?.end_seconds!==s.end_seconds;
    }))void persist(candidate);
  }
  const a=Math.min(start??position,end??position);
  const b=Math.max(start??position,end??position);
  const selectedSection=sections.find(s=>s.id===selected);

  return <section className="section-editor section-editor-rail" aria-label="Song sections">
    <div className="section-inline-row">
      <div className="section-inline-tools">
        <details className="section-manual-controls" title="Create section at playhead">
          <summary aria-label="Manual section tools" title="Section tools">≡</summary>
          <div className="section-manual-popover">
            <button type="button" onClick={()=>setStart(position)} title="Mark start">In</button>
            <button type="button" onClick={()=>setEnd(position)} title="Mark end">Out</button>
            <span>{start===null?"—":stamp(start)} – {end===null?"—":stamp(end)}</span>
            <select value={kind} aria-label="Section type" onChange={e=>setKind(e.target.value)}>
              {kinds.map(x=><option key={x}>{x}</option>)}
            </select>
            <input type="number" min="1" max="99" placeholder="#" aria-label="Section number" value={number}
              onChange={e=>setNumber(e.target.value)}/>
            <button type="button" title="Add section" disabled={busy||start===null||end===null||b-a<MIN_LENGTH||b>duration+0.005}
              onClick={()=>void persist([...sections,{id:crypto.randomUUID().replaceAll("-",""),kind,
                number:number?Number(number):null,start_seconds:a,end_seconds:b}])}>＋</button>
          </div>
        </details>
      </div>
    {duration>0&&<div data-section-lane="" aria-label="Draggable section timeline aligned to playback" style={{height:45,position:"relative",margin:"12px 0",background:"var(--color-surface-secondary, #7773)",borderRadius:4,overflow:"hidden"}}>
      {sections.filter(s=>s.end_seconds>viewStart&&s.start_seconds<viewEnd).map(s=><div key={s.id} style={{position:"absolute",left:`${100*(s.start_seconds-viewStart)/(viewEnd-viewStart)}%`,width:`${100*(s.end_seconds-s.start_seconds)/(viewEnd-viewStart)}%`,top:5,height:34,background:selected===s.id?"#3a778f":"#587b8e",border:"1px solid #fff8",borderRadius:4,minWidth:3,display:"flex",alignItems:"center",touchAction:"none"}}>
        <div role="slider" tabIndex={0} aria-label={`Resize start of ${s.kind}`} aria-valuemin={bounds(s.id)[0]} aria-valuemax={s.end_seconds-MIN_LENGTH} aria-valuenow={s.start_seconds}
          title="Drag to resize start. Arrow keys adjust by 0.1s."
          onKeyDown={e=>{if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();nudge(s,"start",e.key==="ArrowLeft"?-1:1);}}}
          onPointerDown={e=>beginDrag(e,s,"start")} onPointerMove={moveDrag} onPointerUp={finishDrag} onPointerCancel={()=>{if(drag.current)setSections(drag.current.originals);drag.current=null;}}
          style={{width:9,height:"100%",cursor:"ew-resize",background:"#ffffff55",flexShrink:0}}/>
        <div role="slider" tabIndex={0} aria-label={`Move ${s.kind}`} aria-valuemin={bounds(s.id)[0]} aria-valuemax={bounds(s.id)[1]-(s.end_seconds-s.start_seconds)} aria-valuenow={s.start_seconds}
          title={`${s.kind} ${stamp(s.start_seconds)}-${stamp(s.end_seconds)}. Drag to move, arrow keys 0.1s.`}
          onKeyDown={e=>{if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();nudge(s,"move",e.key==="ArrowLeft"?-1:1);}}}
          onDoubleClick={()=>onSectionDoubleClick?.(s)}
          onPointerDown={e=>beginDrag(e,s,"move")} onPointerMove={moveDrag} onPointerUp={finishDrag} onPointerCancel={()=>{if(drag.current)setSections(drag.current.originals);drag.current=null;}}
          style={{flex:1,minWidth:0,height:"100%",cursor:"grab",display:"flex",alignItems:"center",justifyContent:"center",overflow:"hidden",whiteSpace:"nowrap",fontSize:11}}>
          {s.kind}{s.number===null?"":` ${s.number}`}
        </div>
        <div role="slider" tabIndex={0} aria-label={`Resize end of ${s.kind}`} aria-valuemin={s.start_seconds+MIN_LENGTH} aria-valuemax={bounds(s.id)[1]} aria-valuenow={s.end_seconds}
          title="Drag to resize end. Arrow keys adjust by 0.1s."
          onKeyDown={e=>{if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();nudge(s,"end",e.key==="ArrowLeft"?-1:1);}}}
          onPointerDown={e=>beginDrag(e,s,"end")} onPointerMove={moveDrag} onPointerUp={finishDrag} onPointerCancel={()=>{drag.current=null;}}
          style={{width:9,height:"100%",cursor:"ew-resize",background:"#ffffff55",flexShrink:0}}/>
      </div>)}
      <div aria-hidden="true" style={{position:"absolute",left:`${100*(position-viewStart)/(viewEnd-viewStart)}%`,top:0,bottom:0,borderLeft:"2px solid #f2c46c",pointerEvents:"none"}}/>
    </div>}
    </div>
    {error&&<small role="alert">{error}</small>}
    {message&&<small role="status">{message}</small>}
  </section>;
}
