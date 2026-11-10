import {useEffect,useState} from "react";
import type {SharedClockAudition} from "./SharedClockAudition";

type Job={id:string;status:string;message:string;filename:string;source_hash:string};
type Track={track_id:string;working_filename:string;stem_alias:string;display_name:string};
const isRunning=(status:string)=>["queued","analyzing","optimizing","rendering"].includes(status);
export function DeshimmerCleanup({
  jobId,tracks,engine,playing,onPlay,onLocked,onJobId,onInserted,onPause,onError
}:{
  jobId:string;tracks:readonly Track[];engine:SharedClockAudition|null;
  playing:boolean;onPlay:()=>Promise<void>|void;
  onLocked:(locked:boolean)=>void;onJobId:(id:string|null)=>void;onInserted:(value:{project:unknown;job:unknown})=>void;
  onPause:()=>void;onError:(value:string)=>void;
}){
  const [selected,setSelected]=useState("");
  const [job,setJob]=useState<Job|null>(null);
  const [busy,setBusy]=useState(false);
  const [previewBusy,setPreviewBusy]=useState(false);
  const [error,setError]=useState("");
  const [loadedId,setLoadedId]=useState<string|null>(null);
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
    setJob(null);setError("");setLoadedId(null);setListen("original");
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
  /** Load only once. Keep this on the existing Song Harbor shared clock. */
  async function ensurePreview():Promise<boolean>{
    if(!job||job.status!=="ready"||!engine?.ready)return false;
    if(loadedId===job.id)return true;
    setPreviewBusy(true);setError("");
    try{
      await engine.loadCandidatePreview(base+"/"+job.id+"/audio",0);
      engine.setCandidateOriginalMix(job.filename,0);
      engine.setCandidatePreviewSolo(false);
      engine.setCandidatePreviewBlend(listen==="cleaned"?100:0);
      setLoadedId(job.id);
      return true;
    }catch(e){
      setError(e instanceof Error?e.message:String(e));
      return false;
    }finally{setPreviewBusy(false);}
  }
  async function togglePlayback(){
    if(!engine?.ready||!job||job.status!=="ready")return;
    if(playing){onPause();return;}
    if(!await ensurePreview())return;
    await onPlay();
  }
  async function switchVersion(next:"original"|"cleaned"){
    if(!engine?.ready||!job||job.status!=="ready")return;
    if(!await ensurePreview())return;
    engine.setCandidatePreviewBlend(next==="cleaned"?100:0);
    setListen(next);
  }
  async function discard(){
    if(locked)return;
    engine?.clearCandidatePreview();
    setJob(null);setLoadedId(null);
    setListen("original");
  }
  async function accept(){
    if(!job||job.status!=="ready"||locked)return;
    setBusy(true);setError("");
    try{
      onPause();
      const saved=await fetch(base+"/"+job.id+"/accept",{method:"POST"});
      const value=await saved.json() as {project?:unknown;job?:unknown;detail?:string};
      if(!saved.ok||!value.project||!value.job)
        throw Error(value.detail||"Could not accept cleaned stem");
      engine?.clearCandidatePreview();
      // Preserve the tool/window; only candidate context is cleared.
      setJob(null);setLoadedId(null);setListen("original");setSelected("");
      onInserted({project:value.project,job:value.job});
    }catch(e){const message=e instanceof Error?e.message:String(e);setError(message);onError(message);}
    finally{setBusy(false);}
  }
  const candidateReady=job?.status==="ready";
  return <section aria-label="Deshimmer stem cleanup" className="song-deshimmer-tool"
      style={{display:"grid",gap:"0.5rem",padding:"0.25rem 0"}}>
    <div className="song-deshimmer-setup">
      <label htmlFor="deshimmer-source">Stem</label>
      <select id="deshimmer-source" aria-label="Stem to clean" disabled={locked}
        value={selected} onChange={e=>setSelected(e.target.value)}>
        <option value="">Select stem</option>
        {tracks.map(track=><option key={track.track_id} value={track.working_filename}>{track.display_name}</option>)}
      </select>
      <button type="button" disabled={locked||!selected||!engine?.ready}
        onClick={()=>void start()}>Optimize</button>
    </div>
    {candidateReady&&<div className="song-deshimmer-audition" aria-label="Cleanup audition">
      <button type="button" className="song-deshimmer-play"
        aria-label={playing?"Pause cleanup audition":"Play cleanup audition"}
        title={playing?"Pause":"Play"} disabled={locked}
        onClick={()=>void togglePlayback()}>{playing?"⏸":"▶"}</button>
      <div className="song-deshimmer-switch" role="group" aria-label="Audition version">
        <button type="button" title="Original" aria-label="Original audio"
          aria-pressed={listen==="original"} className={listen==="original"?"is-active":""}
          disabled={locked} onClick={()=>void switchVersion("original")}>◯ <span>Original</span></button>
        <button type="button" title="Cleaned" aria-label="Cleaned audio"
          aria-pressed={listen==="cleaned"} className={listen==="cleaned"?"is-active":""}
          disabled={locked} onClick={()=>void switchVersion("cleaned")}>✦ <span>Cleaned</span></button>
      </div>
      <button type="button" title="Accept cleaned replacement" disabled={locked}
        onClick={()=>void accept()}>Accept</button>
      <button type="button" title="Discard candidate" disabled={locked}
        onClick={()=>void discard()}>Discard</button>
    </div>}
    {job?.status==="failed"&&<p role="alert">{job.message}</p>}
    {error&&<p role="alert">{error}</p>}
  </section>;
}
