import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";

export type SavedReverbTarget={
  section_id:string;source_key:string;wet:number;transition_seconds:number;
  curve:"linear"|"smooth";
};
type Props={
  jobId:string;sections:SongSection[];files:string[]; initialSectionId?:string;
  targets:SavedReverbTarget[];previewEnabled?:boolean;onPreview?:(items:SavedReverbTarget[])=>void;onChange:(items:SavedReverbTarget[])=>void;
};
export function SectionReverbTool({jobId,sections,files,targets,onChange,initialSectionId,previewEnabled=false,onPreview}:Props){
  const [sectionId,setSectionId]=useState(initialSectionId||"");
  useEffect(()=>{if(initialSectionId)setSectionId(initialSectionId);},[initialSectionId]);
  const [file,setFile]=useState("");
  const [wet,setWet]=useState(0);
  const [transition,setTransition]=useState(1);
  const [curve,setCurve]=useState<"linear"|"smooth">("smooth");
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const currentSection=sections.some(s=>s.id===sectionId)?sectionId:sections[0]?.id||"";
  const currentFile=files.includes(file)?file:files[0]||"";
  const current=targets.find(item=>item.section_id===currentSection&&item.source_key===currentFile);
  useEffect(()=>{
    setWet(current?.wet??0);
    setTransition(current?.transition_seconds??1);
    setCurve(current?.curve??"smooth");
  },[currentSection,currentFile,targets]);
  useEffect(()=>{setMessage("");setError("");},[jobId]);
  async function persist(next:SavedReverbTarget[]){
    setSaving(true);setError("");setMessage("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/section-reverb",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({targets:next})
      });
      const data=await response.json() as {targets?:SavedReverbTarget[];detail?:string};
      if(!response.ok||!data.targets)throw Error(data.detail||"Could not save reverb targets");
      onChange(data.targets);
      setMessage("Section reverb saved.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  function save(){
    if(!currentSection||!currentFile)return;
    const item:SavedReverbTarget={section_id:currentSection,source_key:currentFile,
      wet,transition_seconds:transition,curve};
    void persist([...targets.filter(t=>t.section_id!==currentSection||t.source_key!==currentFile),item]);
  }

  // Live preview remains a purely local draft. Save/Apply is the only API write.
  useEffect(()=>{
    if(!previewEnabled||!currentSection||!currentFile)return;
    onPreview?.([...targets.filter(t=>t.section_id!==currentSection||t.source_key!==currentFile),{
      section_id:currentSection,source_key:currentFile,wet,transition_seconds:transition,curve
    }]);
  // Deliberately react to editable values, not to parent re-renders.
  },[previewEnabled,currentSection,currentFile,wet,transition,curve]);
  return <details className="production-tool-detail" open>
    <summary>Section reverb</summary>
    <div className="timeline-loop-controls">
      <p>Diffuse room reverb send. Dry stem and original L/R routing stay intact.</p>
      <label className="subtool-section-picker">Section
        <select aria-label="Reverb section" value={currentSection} onChange={e=>setSectionId(e.target.value)}>
          {sections.map(s=><option key={s.id} value={s.id}>
            {s.kind}{s.number?" "+s.number:""} ({s.start_seconds.toFixed(1)}s)
          </option>)}
        </select>
      </label>
      <label>Stem
        <select aria-label="Reverb stem" value={currentFile} onChange={e=>setFile(e.target.value)}>
          {files.map(name=><option key={name} value={name}>{name}</option>)}
        </select>
      </label>
      <label>Wet send: {Math.round(wet*100)}%
        <input aria-label="Reverb send amount" type="range" min="0" max="1" step=".05"
          value={wet} onChange={e=>setWet(Number(e.target.value))}/>
      </label>
      <label>Transition (seconds)
        <input aria-label="Reverb transition seconds" type="number" min=".05" max="30" step=".05"
          value={transition} onChange={e=>setTransition(Number(e.target.value))}/>
      </label>
      <label>Curve
        <select aria-label="Reverb curve" value={curve} onChange={e=>setCurve(e.target.value as "linear"|"smooth")}>
          <option value="smooth">Smooth</option><option value="linear">Linear</option>
        </select>
      </label>
      <button type="button" disabled={!currentSection||!currentFile||saving||!Number.isFinite(transition)||transition<.05||transition>30}
        onClick={save}>Save reverb target</button>
      {current&&<button type="button" disabled={saving} onClick={()=>void persist(targets.filter(t=>t.section_id!==currentSection||t.source_key!==currentFile))}>Remove target</button>}
      <small>Reverb preset is a single room response in this initial release. Wet sends are section-inherited.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
