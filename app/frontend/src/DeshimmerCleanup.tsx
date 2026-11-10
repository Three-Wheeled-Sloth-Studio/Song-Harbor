import {useEffect,useState} from "react";
import type {SharedClockAudition} from "./SharedClockAudition";

type Job={id:string;status:string;message:string;filename:string;source_hash:string};
type Track={track_id:string;working_filename:string;stem_alias:string;display_name:string};
const isRunning=(status:string)=>["queued","analyzing","optimizing","rendering"].includes(status);
export function DeshimmerCleanup({
  jobId,tracks,engine,onLocked,onJobId,onInserted,onPause,onError
}:{
  jobId:string;tracks:readonly Track[];engine:SharedClockAudition|null;
  onLocked:(locked:boolean)=>void;onJobId:(id:string|null)=>void;onInserted:(value:{project:unknown;job:unknown})=>void;
  onPause:()=>void;onError:(value:string)=>void;
}){
  const [selected,setSelected]=useState("");
  const [job,setJob]=useState<Job|null>(null);
  const [busy,setBusy]=useState(false);
  const [previewBusy,setPreviewBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [listen,setListen]=useState<"original"|"cleaned">("original");
  const base="/api/projects/"+encodeURIComponent(jobId)+"/cleanup/deshimmer";
  const locked=busy||previewBusy||Boolean(job&&isRunning(job.status));
  useEffect(()=>{onLocked(locked);},[locked,onLocked]);
  useEffect(()=>{onJobId(locked?job?.id||null:null);},[locked,job?.id,onJobId]);
  useEffect(()=>()=>{onLocked(false);onJobId(null);engine?.clearCandidatePreview();},[engine,onLocked,onJobId]);
  useEffect(()=>{
    if(!job||!isRunning(job.status))return;
    let alive=true;
    const check=async()=>{
      try{
        const response=await fetch(base+"/"+job.id,{cache:"no-store"});
        const result=await response.json() as Job&{detail?:string};
        if(!response.ok)throw Error(result.detail||"Deshimmer status unavailable");
        if(alive)setJob(result);
      }catch(e){if(alive){setError(e instanceof Error?e.message:String(e));setJob(old=>old?{...old,status:"failed"}:old);}}
    };
    const id=window.setInterval(()=>{void check();},1000);
    void check();
    return()=>{alive=false;window.clearInterval(id);};
  },[base,job?.id,job?.status]);
  async function start(){
    if(locked||!selected||!engine?.ready)return;
    engine.clearCandidatePreview();
    setJob(null);setError("");setNotice("");setListen("original");
    setBusy(true);
    try{
      const response=await fetch(base,{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({filename:selected})});
      const result=await response.json() as Job&{detail?:string};
      if(!response.ok)throw Error(result.detail||"Cannot start Deshimmer");
      setJob(result);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function preview(cleaned:boolean){
    if(!job||job.status!=="ready"||!engine?.ready||previewBusy)return;
    setPreviewBusy(true);setError("");
    try{
      const url=base+"/"+job.id+"/audio";
      await engine.loadCandidatePreview(url,0);
      engine.setCandidateOriginalMix(job.filename,0);
      engine.setCandidatePreviewBlend(cleaned?100:0);
      engine.setCandidatePreviewSolo(false);
      setListen(cleaned?"cleaned":"original");
      setNotice(cleaned?"Cleaned stem active in mix preview":"Original stem active in mix preview");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setPreviewBusy(false);}
  }
  function toggle(cleaned:boolean){
    if(!job||job.status!=="ready"||!engine?.ready)return;
    if(listen==="original"&&cleaned){void preview(true);return;}
    engine.setCandidatePreviewBlend(cleaned?100:0);
    setListen(cleaned?"cleaned":"original");
  }
  async function discard(){
    if(locked)return;
    engine?.clearCandidatePreview();
    setJob(null);setNotice("Candidate discarded. Original stem unchanged.");
    setListen("original");
  }
  async function accept(){
    if(!job||job.status!=="ready"||locked)return;
    const source=tracks.find(t=>t.working_filename===job.filename);
    if(!source){setError("Source stem identity missing; reopen the song.");return;}
    setBusy(true);setError("");
    try{
      onPause();
      const response=await fetch(base+"/"+job.id+"/audio",{cache:"no-store"});
      if(!response.ok)throw Error("Candidate audio unavailable");
      const blob=await response.blob();
      const alias=("Clean_"+source.stem_alias).replace(/[^a-zA-Z0-9_-]/g,"").slice(0,32);
      const form=new FormData();
      form.append("file",new File([blob],"deshimmer-"+job.id.slice(0,8)+".wav",{type:"audio/wav"}));
      form.append("stem_alias",alias);
      form.append("display_name","Cleaned "+source.display_name);
      form.append("start_seconds","0");
      form.append("original_gain_percent","0");
      form.append("replace_source_track_id",source.track_id);
      const saved=await fetch("/api/projects/"+encodeURIComponent(jobId)+"/tracks/add",{method:"POST",body:form});
      const value=await saved.json() as {project?:unknown;job?:unknown;detail?:string};
      if(!saved.ok||!value.project||!value.job)throw Error(value.detail||"Could not accept cleaned stem");
      engine?.clearCandidatePreview();
      setNotice("Cleaned stem accepted as a replacement layer; original remains recoverable.");
      setJob(null);
      onInserted({project:value.project,job:value.job});
    }catch(e){const message=e instanceof Error?e.message:String(e);setError(message);onError(message);}
    finally{setBusy(false);}
  }
  const candidateReady=job?.status==="ready";
  return <section aria-label="Deshimmer stem cleanup" className="song-deshimmer-tool"
      style={{position:"relative",display:"grid",gap:"0.6rem",padding:"0.5rem 0"}}>
    <strong>Deshimmer: optimize and clean stem</strong>
    <small>Local CPU processing. The source is preserved. No mastering or automatic acceptance.</small>
    <label>Source stem
      <select aria-label="Stem to clean" disabled={locked} value={selected} onChange={e=>setSelected(e.target.value)}>
        <option value="">Select a stem</option>
        {tracks.map(track=><option key={track.track_id} value={track.working_filename}>{track.display_name}</option>)}
      </select>
    </label>
    <button type="button" disabled={locked||!selected||!engine?.ready} onClick={()=>void start()}>Optimize and clean</button>
    {candidateReady&&<>
      <div className="production-tool-actions">
        <button type="button" aria-pressed={listen==="original"} onClick={()=>toggle(false)}>A: Original</button>
        <button type="button" aria-pressed={listen==="cleaned"} onClick={()=>toggle(true)}>B: Cleaned</button>
      </div>
      <small>Use the main transport to audition in context. A/B uses the shared audio clock.</small>
      <div className="production-tool-actions">
        <button type="button" disabled={locked} onClick={()=>void accept()}>Accept replacement</button>
        <button type="button" disabled={locked} onClick={()=>void discard()}>Discard</button>
      </div>
    </>}
    {job&&!candidateReady&&<p role="status">{job.message}</p>}
    {notice&&<p role="status">{notice}</p>}
    {error&&<p role="alert">{error}</p>}
    {locked&&<div className="song-deshimmer-lock" role="status" aria-live="polite" aria-label="Deshimmer working, cleanup controls locked">
      <div className="song-deshimmer-spinner" aria-hidden="true"/>
      <strong>Deshimmer working</strong>
      <span>{job?.message||"Preparing cleanup"}</span>
      <small>Cleanup controls locked while processing. Existing audio is untouched.</small>
    </div>}
  </section>;
}
