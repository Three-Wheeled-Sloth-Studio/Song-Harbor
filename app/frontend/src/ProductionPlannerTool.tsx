import {useState} from "react";
import {Button,Status} from "@tws-ui/core/react";
import type {SectionInsight} from "./SectionInsights";

type Direction="enhance"|"ominous"|"movement"|"contrast";
type StereoSource={filename:string;balanceDb:number;widthDb:number;correlation:number;hardPan:number;rmsDbfs?:number;channels?:number};
type Suggestion={section_id:string;label:string;directives:string[];measurements:SectionInsight};
type Plan={content:string;profile:{name:string;id:string};suggestions:Suggestion[];
  notes:{section_id:string;note:string}[];stereo_sources?:StereoSource[];analysis_kind:string;disclaimer:string;source:string};

export function ProductionPlannerTool({projectId,analyze,sourceStereo,onReview}:{
  projectId:string;analyze:()=>Promise<readonly SectionInsight[]>;
  sourceStereo:()=>readonly StereoSource[];onReview:(content:string)=>void;
}){
  const [direction,setDirection]=useState<Direction>("enhance");
  const [spatial,setSpatial]=useState(65);
  const [dynamics,setDynamics]=useState(60);
  const [busy,setBusy]=useState(false);
  const [phase,setPhase]=useState("");
  const [error,setError]=useState("");
  const [plan,setPlan]=useState<Plan|null>(null);
  const [copied,setCopied]=useState(false);
  async function generate(){
    setBusy(true);setError("");setPlan(null);setCopied(false);
    try{
      setPhase("Analyzing current processed mix");
      const insights=await analyze();
      if(!insights.length)throw Error("ERROR: Save sections before creating a production proposal.");
      setPhase("Validating section script");
      const response=await fetch("/api/projects/"+encodeURIComponent(projectId)+"/production-plan/preview",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({section_metrics:insights,stereo_sources:sourceStereo(),spatial,dynamics,direction})
      });
      const result=await response.json() as Plan&{detail?:string};
      if(!response.ok)throw Error(result.detail||"ERROR: Production proposal failed.");
      setPlan(result);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);setPhase("");}
  }
  return <div className="setting-tool-section song-production-planner">
    <div className="setting-controls">
      <div className="planner-profile" aria-label="Production profile">Infra Choir</div>
      <label>Direction
        <select aria-label="Production direction" value={direction}
          onChange={e=>setDirection(e.target.value as Direction)}>
          <option value="enhance">Enhance arrangement</option>
          <option value="ominous">More ominous</option>
          <option value="movement">Spatial movement</option>
          <option value="contrast">Dynamic contrast</option>
        </select>
      </label>
      <label>Space {spatial}
        <input aria-label="Spatial ambition" type="range" min={0} max={100}
          value={spatial} onChange={e=>setSpatial(Number(e.target.value))}/>
      </label>
      <label>Dynamics {dynamics}
        <input aria-label="Dynamic ambition" type="range" min={0} max={100}
          value={dynamics} onChange={e=>setDynamics(Number(e.target.value))}/>
      </label>
      <Button size="compact" variant="primary" disabled={busy} onClick={()=>void generate()}>
        {busy?"Analyzing...":"Generate plan"}
      </Button>
    </div>
    {busy&&<p role="status">{phase}</p>}
    {error&&<p className="error-message" role="alert">{error}</p>}
    {plan&&<>
      <div className="setting-tool-row">
        <strong>{plan.suggestions.length} sections adjusted</strong>
        <Status tone="warning">Draft only</Status>
        <Button size="compact" variant="primary" onClick={()=>onReview(plan.content)}>Review in editor</Button>
        <Button size="compact" variant="secondary" onClick={()=>void (async()=>{
          try{
            await navigator.clipboard.writeText(plan.content);
            setCopied(true);setError("");
          }catch{setError("ERROR: Clipboard unavailable. Select and copy the draft text.");}
        })()}>{copied?"Copied":"Copy section text"}</Button>
      </div>
      <textarea aria-label="Proposed whole-song section text"
        value={plan.content} rows={12} readOnly style={{width:"100%"}}/>
      <details><summary>Changes and evidence</summary>
        <p>{plan.stereo_sources?.length||0} source profiles inspected; {(plan.stereo_sources||[]).filter(row=>row.channels===1||(row.widthDb< -35&&row.correlation>.995)).length} near-mono.</p>
        {plan.suggestions.map(item=><p key={item.section_id}>
          <strong>{item.label}</strong>: {item.directives.join(" ")}
          <small> | RMS {item.measurements.rmsDbfs.toFixed(1)} dBFS,
            width {item.measurements.widthDb.toFixed(1)} dB,
            L/R {item.measurements.balanceDb.toFixed(1)} dB</small>
        </p>)}
        {plan.notes.map((item,i)=><p key={item.section_id+"-"+i}>{item.note}</p>)}
        <small>{plan.disclaimer}</small>
      </details>
    </>}
  </div>;
}
