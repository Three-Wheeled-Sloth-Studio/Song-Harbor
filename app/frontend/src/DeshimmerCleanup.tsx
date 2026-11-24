import {useEffect,useRef,useState} from "react";
import type {SharedClockAudition} from "./SharedClockAudition";

type Job={id:string;status:string;message:string;filename:string;source_hash:string};
type Track={track_id:string;working_filename:string;stem_alias:string;display_name:string};
type BatchItem={filename:string;name:string;job:Job|null;status:"pending"|"running"|"ready"|"failed"|"cancelled";error?:string};
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
  const [batch,setBatch]=useState<BatchItem[]>([]);
  const [batchRunning,setBatchRunning]=useState(false);
  const [batchIndex,setBatchIndex]=useState(-1);
  const stopBatch=useRef(false);
  const base="/api/projects/"+encodeURIComponent(jobId)+"/cleanup/deshimmer";
  const locked=busy||previewBusy||batchRunning||Boolean(job&&isRunning(job.status));
  useEffect(()=>{onLocked(locked);},[locked,onLocked]);
  useEffect(()=>{onJobId(locked?job?.id||null:null);},[locked,job?.id,onJobId]);
  useEffect(()=>()=>{stopBatch.current=true;onLocked(false);onJobId(null);engine?.clearCandidatePreview();},[engine,onLocked,onJobId]);
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
  async function startAll(){
    if(locked||!tracks.length||!engine?.ready)return;
    stopBatch.current=false;
    engine.clearCandidatePreview();setLoadedId(null);setJob(null);setError("");
    const items:BatchItem[]=tracks.map(track=>({filename:track.working_filename,name:track.display_name,job:null,status:"pending"}));
    setBatch(items);setBatchRunning(true);setBatchIndex(0);
    const update=(index:number,patch:Partial<BatchItem>)=>setBatch(old=>old.map((item,i)=>i===index?{...item,...patch}:item));
    try{
      for(let i=0;i<items.length;i++){
        if(stopBatch.current)break;
        setBatchIndex(i);update(i,{status:"running"});
        try{
          const response=await fetch(base,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:items[i].filename})});
          const started=await response.json() as Job&{detail?:string};
          if(!response.ok)throw Error(started.detail||"Unable to start optimization");
          update(i,{job:started});
          let latest=started;
          while(isRunning(latest.status)&&!stopBatch.current){
            await new Promise(resolve=>window.setTimeout(resolve,1000));
            const polled=await fetch(base+"/"+started.id,{cache:"no-store"});
            const data=await polled.json() as Job&{detail?:string};
            if(!polled.ok)throw Error(data.detail||"Optimization status unavailable");
            latest=data;update(i,{job:latest});
          }
          if(stopBatch.current){
            if(isRunning(latest.status))await fetch(base+"/"+started.id+"/cancel",{method:"POST"});
            update(i,{job:latest,status:"cancelled"});
          }else if(latest.status==="ready")update(i,{job:latest,status:"ready"});
          else update(i,{job:latest,status:"failed",error:latest.message});
        }catch(e){update(i,{status:"failed",error:e instanceof Error?e.message:String(e)});}
      }
    }finally{
      if(stopBatch.current)setBatch(old=>old.map(item=>item.status==="pending"?{...item,status:"cancelled"}:item));
      setBatchRunning(false);setBatchIndex(-1);
    }
  }
  function cancelAll(){
    stopBatch.current=true;
    // The batch loop cancels the active candidate and preserves completed results.
  }
  function reviewCandidate(item:BatchItem){
    if(locked||!item.job||item.status!=="ready")return;
    onPause();engine?.clearCandidatePreview();setLoadedId(null);setListen("original");
    setSelected(item.filename);setJob(item.job);setError("");
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
      setBatch(old=>old.filter(item=>item.job?.id!==job.id));
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
      <button type="button" disabled={locked||!tracks.length||!engine?.ready}
        onClick={()=>void startAll()}>Optimize all stems</button>
    </div>
    {(batchRunning||batch.length>0)&&<div className="song-deshimmer-batch" aria-label="All stems optimization progress">
      <div role="status" aria-live="polite">
        <strong>{batchRunning?"Optimizing all stems":"Batch optimization complete"}</strong>
        {" - "}{batch.filter(item=>["ready","failed","cancelled"].includes(item.status)).length} of {batch.length} processed
        {batchRunning&&batchIndex>=0&&"; current: "+batch[batchIndex]?.name}
      </div>
      <progress max={batch.length||1} value={batch.filter(item=>["ready","failed","cancelled"].includes(item.status)).length}
        aria-label="Stems processed" style={{width:"100%"}}/>
      {batchRunning&&<button type="button" onClick={cancelAll}>Stop batch</button>}
      <ul style={{margin:"0.25rem 0",paddingLeft:"1.4rem",maxHeight:"12rem",overflowY:"auto"}}>
        {batch.map(item=><li key={item.filename}>
          {item.name}: {item.status==="running"?(item.job?.message||"Starting"):item.status}
          {item.error&&<span role="alert"> - ERROR: {item.error}. Stem not updated.</span>}
          {item.status==="ready"&&<button type="button" disabled={locked} onClick={()=>reviewCandidate(item)}>Review candidate</button>}
        </li>)}
      </ul>
    </div>}
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
    {job?.status==="failed"&&<p role="alert" className="song-deshimmer-error">
      <strong>ERROR:</strong> {job.message}. Stem not updated.
    </p>}
    {error&&<p role="alert" className="song-deshimmer-error">
      <strong>ERROR:</strong> {error.replace(/[.! ]+$/,"")}. Stem not updated.
    </p>}
  </section>;
}
