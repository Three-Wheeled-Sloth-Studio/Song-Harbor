import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {AutomationCurve} from "./SectionAutomation";

export type SavedPanTarget={
  section_id:string;source_key:string;pan:number;
  transition_seconds:number;curve:AutomationCurve;
};
type Props={
  jobId:string;sections:SongSection[];files:string[]; initialSectionId?:string;
  targets:SavedPanTarget[];
  onChange:(items:SavedPanTarget[])=>void;
  previewEnabled?:boolean;onPreview?:(items:SavedPanTarget[])=>void;
};
export function SectionPanTool({jobId,sections,files,targets,onChange,initialSectionId,previewEnabled=false,onPreview}:Props){
  const [sectionId,setSectionId]=useState(initialSectionId||"");
  useEffect(()=>{if(initialSectionId)setSectionId(initialSectionId);},[initialSectionId]);
  const [file,setFile]=useState("");
  const [pan,setPan]=useState(0);
  const [transition,setTransition]=useState(1);
  const [curve,setCurve]=useState<AutomationCurve>("smooth");
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  const currentSection=sections.some(s=>s.id===sectionId)?sectionId:(sections[0]?.id||"");
  const available=files;
  const currentFile=available.includes(file)?file:(available[0]||"");
  const existing=targets.find(t=>t.section_id===currentSection&&t.source_key===currentFile);
  useEffect(()=>{
    if(existing){
      setPan(existing.pan);setTransition(existing.transition_seconds);setCurve(existing.curve);
    }else{setPan(0);setTransition(1);setCurve("smooth");}
  },[currentSection,currentFile,targets]);
  useEffect(()=>{setError("");setMessage("");},[jobId]);

  async function persist(next:SavedPanTarget[]){
    setSaving(true);setError("");setMessage("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/section-pan",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({targets:next})
      });
      const data=await response.json() as {targets?:SavedPanTarget[];detail?:string};
      if(!response.ok||!data.targets)throw Error(data.detail||"Could not save pan targets");
      onChange(data.targets);
      setMessage("Pan targets saved. Preview only; processed export is not implemented.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  const valid=Boolean(currentSection&&currentFile);
  const proposed:SavedPanTarget={section_id:currentSection,source_key:currentFile,
    pan,transition_seconds:transition,curve};
  function updateTarget(){
    if(!valid)return;
    void persist([...targets.filter(t=>!(t.section_id===currentSection&&t.source_key===currentFile)),proposed]);
  }
  function removeTarget(){
    void persist(targets.filter(t=>!(t.section_id===currentSection&&t.source_key===currentFile)));
  }

  // Live preview remains a purely local draft. Save/Apply is the only API write.
  useEffect(()=>{
    if(!previewEnabled||!currentSection||!currentFile)return;
    onPreview?.([...targets.filter(t=>t.section_id!==currentSection||t.source_key!==currentFile),{
      section_id:currentSection,source_key:currentFile,pan,transition_seconds:transition,curve
    }]);
  // Deliberately react to editable values, not to parent re-renders.
  },[previewEnabled,currentSection,currentFile,pan,transition,curve]);
  return <details className="production-tool-detail" open>
    <summary>Section pan (preview)</summary>
    <div className="timeline-loop-controls">
      <p>Animate individual stems between sections. Changes are reversible and saved.</p>
      <label className="subtool-section-picker">Section
        <select aria-label="Automation section" value={currentSection} onChange={e=>setSectionId(e.target.value)}>
          {sections.map(s=><option key={s.id} value={s.id}>
            {s.kind}{s.number?" "+s.number:""} ({s.start_seconds.toFixed(1)}s)
          </option>)}
        </select>
      </label>
      <label>Stem
        <select aria-label="Automation stem" value={currentFile} onChange={e=>setFile(e.target.value)}>
          {available.map(f=><option key={f} value={f}>{f}</option>)}
        </select>
      </label>
      <p>Pan moves the combined stereo stem, preserving split L/R routing at the center position.</p>
      <label>Pan target: {pan<0?Math.abs(Math.round(pan*100))+"% left":pan>0?Math.round(pan*100)+"% right":"center"}
        <input aria-label="Section pan target" type="range" min="-1" max="1" step=".05" value={pan}
          onChange={e=>setPan(Number(e.target.value))}/>
      </label>
      <label>Transition (seconds)
        <input aria-label="Pan transition seconds" type="number" min=".05" max="30" step=".05"
          value={transition} onChange={e=>setTransition(Number(e.target.value))}/>
      </label>
      <label>Curve
        <select aria-label="Pan transition curve" value={curve}
          onChange={e=>setCurve(e.target.value as AutomationCurve)}>
          <option value="smooth">Smooth</option><option value="linear">Linear</option>
        </select>
      </label>
      <button type="button" disabled={!valid||saving||!Number.isFinite(transition)||transition<.05||transition>30}
        onClick={updateTarget}>Save pan target</button>
      {existing&&<button type="button" disabled={saving} onClick={removeTarget}>Remove target</button>}
      <small>Saved instructions affect synchronized audition, not WAV mix export.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
