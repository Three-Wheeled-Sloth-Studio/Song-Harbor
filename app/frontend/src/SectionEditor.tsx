import { useEffect, useState } from "react";

export type SongSection = {
  id: string; kind: string; number: number | null;
  start_seconds: number; end_seconds: number;
};
const kinds = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Instrumental", "Guitar Solo", "Outro", "End"];

function stamp(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds % 60).toFixed(2).padStart(5, "0")}`;
}

export function SectionEditor({jobId, duration, position, initialSections, onSeek}: {
  jobId: string; duration: number; position: number;
  initialSections?: SongSection[]; onSeek: (seconds: number) => void;
}) {
  const [sections, setSections] = useState<SongSection[]>(initialSections || []);
  const [kind, setKind] = useState("Chorus");
  const [number, setNumber] = useState("");
  const [start, setStart] = useState<number | null>(null);
  const [end, setEnd] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {setSections(initialSections || []); setStart(null); setEnd(null);}, [jobId, initialSections]);

  async function persist(next: SongSection[]) {
    setBusy(true); setError(""); setMessage("");
    try {
      const response = await fetch(`/api/projects/${jobId}/sections`, {
        method:"PUT", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({sections:next})
      });
      const result = await response.json() as {sections?:SongSection[], detail?:string};
      if (!response.ok || !result.sections) throw new Error(result.detail || "Could not save sections");
      setSections(result.sections);
      setStart(null); setEnd(null);
      setMessage("Section markers saved without modifying audio.");
    } catch (e) {setError(e instanceof Error ? e.message : "Could not save section");}
    finally {setBusy(false);}
  }

  const rangeStart = Math.min(start ?? position, end ?? position);
  const rangeEnd = Math.max(start ?? position, end ?? position);
  return <section className="section-editor" aria-label="Song sections" style={{padding:"12px 0",borderTop:"1px solid var(--color-border, #6665)"}}>
    <h3 style={{margin:"0 0 8px"}}>Sections</h3>
    <p style={{fontSize:12,margin:"0 0 8px"}}>Mark a range while auditioning, then label it. Markers guide later effects and analysis; audio stays unchanged.</p>
    <div style={{display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
      <button type="button" onClick={()=>setStart(position)} title="Mark section start at current playback position">Mark in</button>
      <button type="button" onClick={()=>setEnd(position)} title="Mark section end at current playback position">Mark out</button>
      <span style={{fontVariantNumeric:"tabular-nums"}}>{start===null?"--:--":stamp(start)} to {end===null?"--:--":stamp(end)}</span>
      <label>Type <select value={kind} onChange={e=>setKind(e.target.value)}>{kinds.map(x=><option key={x}>{x}</option>)}</select></label>
      <label>Number <input aria-label="Section number" type="number" min="1" max="99" value={number} placeholder="optional" onChange={e=>setNumber(e.target.value)} style={{width:65}}/></label>
      <button type="button" disabled={busy||start===null||end===null||rangeEnd<=rangeStart||rangeEnd>duration+0.005}
        onClick={()=>void persist([...sections,{id:crypto.randomUUID().replaceAll("-",""),kind,number:number?Number(number):null,start_seconds:rangeStart,end_seconds:rangeEnd}])}>Add section</button>
    </div>
    {duration>0 && <div aria-label="Section timeline" style={{height:18,position:"relative",margin:"12px 0",background:"var(--color-surface-secondary, #7773)",borderRadius:4}}>
      {sections.map(s=><button type="button" key={s.id} title={`${s.kind} ${stamp(s.start_seconds)}-${stamp(s.end_seconds)}. Seek to start.`}
        onClick={()=>onSeek(s.start_seconds)} style={{position:"absolute",left:`${100*s.start_seconds/duration}%`,width:`${100*(s.end_seconds-s.start_seconds)/duration}%`,top:0,bottom:0,background:"#6a98ae",border:"1px solid #fff8",borderRadius:3,minWidth:2,padding:0}}/>)}
    </div>}
    <div style={{display:"flex",flexDirection:"column",gap:4}}>
      {sections.map(s=><div key={s.id} style={{display:"flex",alignItems:"center",gap:8}}>
        <button type="button" onClick={()=>onSeek(s.start_seconds)} title="Play from section start">▶</button>
        <span style={{flex:1,fontVariantNumeric:"tabular-nums"}}>[{s.kind}{s.number===null?"":` ${s.number}`} {stamp(s.start_seconds)}-{stamp(s.end_seconds)}]</span>
        <button type="button" disabled={busy} onClick={()=>void persist(sections.filter(x=>x.id!==s.id))} aria-label={`Remove ${s.kind} section`} title="Remove marker only">×</button>
      </div>)}
    </div>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
