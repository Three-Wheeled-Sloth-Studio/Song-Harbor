import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";

export type SavedEqTarget={section_id:string;source_key:string;band:number;frequency:number;
  q:number;gain_db:number;transition_seconds:number;curve:"smooth"|"linear"};
type Props={jobId:string;sections:SongSection[];files:string[]; initialSectionId?:string;
  targets:SavedEqTarget[];onChange:(items:SavedEqTarget[])=>void};
export function SectionEqTool({jobId,sections,files,targets,onChange,initialSectionId}:Props){
  const [sectionId,setSectionId]=useState(initialSectionId||"");
  useEffect(()=>{if(initialSectionId)setSectionId(initialSectionId);},[initialSectionId]);
  const [file,setFile]=useState("");
  const [band,setBand]=useState(1);
  const [frequency,setFrequency]=useState(1000);
  const [q,setQ]=useState(1);
  const [gain,setGain]=useState(0);
  const [transition,setTransition]=useState(2);
  const [curve,setCurve]=useState<"smooth"|"linear">("smooth");
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  const currentSection=sections.some(s=>s.id===sectionId)?sectionId:sections[0]?.id||"";
  const currentFile=files.includes(file)?file:files[0]||"";
  const existing=targets.find(t=>t.section_id===currentSection&&t.source_key===currentFile&&t.band===band);
  useEffect(()=>{
    setFrequency(existing?.frequency??1000);
    setQ(existing?.q??1);
    setGain(existing?.gain_db??0);
    setTransition(existing?.transition_seconds??2);
    setCurve(existing?.curve??"smooth");
  },[currentSection,currentFile,band,targets]);
  useEffect(()=>{setMessage("");setError("");},[jobId]);
  async function persist(next:SavedEqTarget[]){
    setSaving(true);setMessage("");setError("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/section-eq",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({targets:next})
      });
      const data=await response.json() as {targets?:SavedEqTarget[];detail?:string};
      if(!response.ok||!data.targets)throw Error(data.detail||"Could not save EQ settings");
      onChange(data.targets);
      setMessage("EQ saved. Section script, playback and WAV export updated.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  function save(){
    if(!currentSection||!currentFile)return;
    void persist([...targets.filter(t=>t.section_id!==currentSection||
      t.source_key!==currentFile||t.band!==band),
      {section_id:currentSection,source_key:currentFile,band,frequency,q,
       gain_db:gain,transition_seconds:transition,curve}]);
  }
  const valid=Number.isFinite(frequency)&&Number.isFinite(q)&&Number.isFinite(gain)&&
    Number.isFinite(transition)&&frequency>=30&&frequency<=16000&&q>=.3&&q<=12&&
    gain>=-12&&gain<=12&&transition>=.05&&transition<=30;
  return <details className="production-tool-detail" open>
    <summary>Parametric EQ</summary>
    <div className="timeline-loop-controls">
      <p>Three per-stem peaking bands, smoothly automatable by section. Start with modest corrections.</p>
      <label className="subtool-section-picker">Section<select aria-label="EQ section" value={currentSection} onChange={e=>setSectionId(e.target.value)}>
        {sections.map(s=><option key={s.id} value={s.id}>{s.kind}{s.number?" "+s.number:""} ({s.start_seconds.toFixed(1)}s)</option>)}
      </select></label>
      <label>Stem<select aria-label="EQ stem" value={currentFile} onChange={e=>setFile(e.target.value)}>
        {files.map(f=><option key={f} value={f}>{f}</option>)}
      </select></label>
      <label>Band<select aria-label="EQ band" value={band} onChange={e=>setBand(Number(e.target.value))}>
        <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option>
      </select></label>
      <label>Frequency (Hz)<input aria-label="EQ frequency" type="number" min="30" max="16000" step="10"
        value={frequency} onChange={e=>setFrequency(Number(e.target.value))}/></label>
      <label>Q (bandwidth)<input aria-label="EQ Q" type="number" min=".3" max="12" step=".1"
        value={q} onChange={e=>setQ(Number(e.target.value))}/></label>
      <label>Gain: {gain>0?"+":""}{gain.toFixed(1)} dB
        <input aria-label="EQ gain" type="range" min="-12" max="12" step=".5"
          value={gain} onChange={e=>setGain(Number(e.target.value))}/>
      </label>
      <label>Transition (seconds)<input aria-label="EQ transition" type="number" min=".05" max="30" step=".05"
        value={transition} onChange={e=>setTransition(Number(e.target.value))}/></label>
      <label>Curve<select aria-label="EQ curve" value={curve} onChange={e=>setCurve(e.target.value as "smooth"|"linear")}>
        <option value="smooth">Smooth</option><option value="linear">Linear</option>
      </select></label>
      <button type="button" disabled={saving||!valid||!currentSection||!currentFile} onClick={save}>Save EQ band</button>
      {existing&&<button type="button" disabled={saving} onClick={()=>void persist(
        targets.filter(t=>t.section_id!==currentSection||t.source_key!==currentFile||t.band!==band)
      )}>Remove band target</button>}
      <small>Unspecified sections inherit earlier band values. The initial mode is static peaking EQ, not dynamic EQ or a compressor.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
