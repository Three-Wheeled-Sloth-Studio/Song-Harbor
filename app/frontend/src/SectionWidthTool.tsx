import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";

export type SavedWidthTarget={
  section_id:string;source_key:string;width:number;transition_seconds:number;
  curve:"linear"|"smooth";
};
type Props={
  jobId:string;sections:SongSection[];files:string[]; initialSectionId?:string;
  targets:SavedWidthTarget[];onChange:(targets:SavedWidthTarget[])=>void;
};
export function SectionWidthTool({jobId,sections,files,targets,onChange,initialSectionId}:Props){
  const [sectionId,setSectionId]=useState(initialSectionId||"");
  useEffect(()=>{if(initialSectionId)setSectionId(initialSectionId);},[initialSectionId]);
  const [file,setFile]=useState("");
  const [width,setWidth]=useState(100);
  const [transition,setTransition]=useState(2);
  const [curve,setCurve]=useState<"linear"|"smooth">("smooth");
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const selectedSection=sections.some(s=>s.id===sectionId)?sectionId:sections[0]?.id||"";
  const selectedFile=files.includes(file)?file:files[0]||"";
  const existing=targets.find(t=>t.section_id===selectedSection&&t.source_key===selectedFile);
  useEffect(()=>{
    setWidth(existing?.width??100);
    setTransition(existing?.transition_seconds??2);
    setCurve(existing?.curve??"smooth");
  },[selectedSection,selectedFile,targets]);
  useEffect(()=>{setError("");setMessage("");},[jobId]);
  async function persist(next:SavedWidthTarget[]){
    setSaving(true);setError("");setMessage("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/section-width",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({targets:next})
      });
      const data=await response.json() as {targets?:SavedWidthTarget[];detail?:string};
      if(!response.ok||!data.targets)throw Error(data.detail||"Could not save section width");
      onChange(data.targets);
      setMessage("Width saved for audition and WAV export.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  function save(){
    if(!selectedSection||!selectedFile)return;
    void persist([...targets.filter(t=>t.section_id!==selectedSection||t.source_key!==selectedFile),
      {section_id:selectedSection,source_key:selectedFile,width,transition_seconds:transition,curve}]);
  }
  return <details className="production-tool-detail" open>
    <summary>Section stereo width</summary>
    <div className="timeline-loop-controls">
      <p>Mid/side width for each reconstructed stereo stem. 100% is original; 0% mono; above 100% expands existing stereo differences.</p>
      <label className="subtool-section-picker">Section
        <select aria-label="Width section" value={selectedSection} onChange={e=>setSectionId(e.target.value)}>
          {sections.map(s=><option key={s.id} value={s.id}>
            {s.kind}{s.number?" "+s.number:""} ({s.start_seconds.toFixed(1)}s)
          </option>)}
        </select>
      </label>
      <label>Stem
        <select aria-label="Width stem" value={selectedFile} onChange={e=>setFile(e.target.value)}>
          {files.map(f=><option key={f} value={f}>{f}</option>)}
        </select>
      </label>
      <label>Width: {width}%
        <input aria-label="Stereo width percent" type="range" min="0" max="150" step="5"
          value={width} onChange={e=>setWidth(Number(e.target.value))}/>
      </label>
      <label>Transition (seconds)
        <input aria-label="Width transition seconds" type="number" min=".05" max="30" step=".05"
          value={transition} onChange={e=>setTransition(Number(e.target.value))}/>
      </label>
      <label>Curve
        <select aria-label="Width curve" value={curve} onChange={e=>setCurve(e.target.value as "smooth"|"linear")}>
          <option value="smooth">Smooth</option><option value="linear">Linear</option>
        </select>
      </label>
      <button type="button" disabled={saving||!selectedSection||!selectedFile||
        !Number.isFinite(transition)||transition<.05||transition>30} onClick={save}>Save width target</button>
      {existing&&<button type="button" disabled={saving} onClick={()=>void persist(
        targets.filter(t=>t.section_id!==selectedSection||t.source_key!==selectedFile)
      )}>Remove target</button>}
      <small>Unchanged sections inherit prior values. Narrow/mono checks are meaningful; near-mono stems may not become perceptibly wider above 100%. Check mono compatibility and headroom after widening.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
