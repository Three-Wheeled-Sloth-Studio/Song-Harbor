import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";

export type SavedSpaceTarget={
  section_id:string;source_key:string;amount:number;transition_seconds:number;
  curve:"linear"|"smooth";
};
type Props={jobId:string;sections:SongSection[];files:string[];
  targets:SavedSpaceTarget[];onChange:(next:SavedSpaceTarget[])=>void};
export function SectionSpaceTool({jobId,sections,files,targets,onChange}:Props){
  const [sectionId,setSectionId]=useState("");
  const [file,setFile]=useState("");
  const [amount,setAmount]=useState(0);
  const [transition,setTransition]=useState(2);
  const [curve,setCurve]=useState<"smooth"|"linear">("smooth");
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const selectedSection=sections.some(s=>s.id===sectionId)?sectionId:sections[0]?.id||"";
  const selectedFile=files.includes(file)?file:files[0]||"";
  const existing=targets.find(t=>t.section_id===selectedSection&&t.source_key===selectedFile);
  useEffect(()=>{
    setAmount(existing?.amount??0);
    setTransition(existing?.transition_seconds??2);
    setCurve(existing?.curve??"smooth");
  },[selectedSection,selectedFile,targets]);
  useEffect(()=>{setError("");setMessage("");},[jobId]);
  async function persist(next:SavedSpaceTarget[]){
    setSaving(true);setError("");setMessage("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/section-space",{
        method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({targets:next})
      });
      const data=await response.json() as {targets?:SavedSpaceTarget[];detail?:string};
      if(!response.ok||!data.targets)throw Error(data.detail||"Could not save early reflections");
      onChange(data.targets);
      setMessage("Spatial reflections saved for audition and WAV export.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  function save(){
    if(!selectedSection||!selectedFile)return;
    void persist([...targets.filter(t=>t.section_id!==selectedSection||t.source_key!==selectedFile),
      {section_id:selectedSection,source_key:selectedFile,amount,transition_seconds:transition,curve}]);
  }
  return <details className="production-tool-detail" open>
    <summary>Spatial reflections</summary>
    <div className="timeline-loop-controls">
      <p>Small offset reflections across the stereo image; creates depth even for near-mono stems. Use modest settings, and check mono compatibility.</p>
      <label>Section
        <select aria-label="Reflection section" value={selectedSection} onChange={e=>setSectionId(e.target.value)}>
          {sections.map(s=><option key={s.id} value={s.id}>{s.kind}{s.number?" "+s.number:""} ({s.start_seconds.toFixed(1)}s)</option>)}
        </select>
      </label>
      <label>Stem
        <select aria-label="Reflection stem" value={selectedFile} onChange={e=>setFile(e.target.value)}>
          {files.map(f=><option key={f} value={f}>{f}</option>)}
        </select>
      </label>
      <label>Spatial reflections: {amount}%
        <input aria-label="Spatial reflection amount" type="range" min="0" max="40" step="1"
          value={amount} onChange={e=>setAmount(Number(e.target.value))}/>
      </label>
      <label>Transition (seconds)
        <input aria-label="Reflection transition seconds" type="number" min=".05" max="30" step=".05"
          value={transition} onChange={e=>setTransition(Number(e.target.value))}/>
      </label>
      <label>Curve
        <select aria-label="Reflection curve" value={curve} onChange={e=>setCurve(e.target.value as "smooth"|"linear")}>
          <option value="smooth">Smooth</option><option value="linear">Linear</option>
        </select>
      </label>
      <button type="button" disabled={saving||!selectedSection||!selectedFile||!Number.isFinite(transition)||transition<.05||transition>30}
        onClick={save}>Save reflection target</button>
      {existing&&<button type="button" disabled={saving} onClick={()=>void persist(
        targets.filter(t=>t.section_id!==selectedSection||t.source_key!==selectedFile)
      )}>Remove target</button>}
      <small>0% is off. Changes inherit into the next sections. Reflections use 13/19ms cross-channel delays with no feedback.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
