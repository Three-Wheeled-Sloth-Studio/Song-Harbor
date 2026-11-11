import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type Q4Review={answer:string;slices:number|null;duration_seconds:number|null;warnings:string[];validated:boolean;aligned:boolean;format:string};
type Q4Job={review?:Q4Review|null;state:string;error:string;elapsed_seconds:number|null;log_path:string;log_tail:string;result:string;audio:string;run_id?:string|null;output_truncated?:boolean;output_path?:string|null};
type Q4Install={state:string;kind:string|null;message:string;error:string;downloaded_bytes:number;total_bytes:number;started:number|null;artifact:string;runtime_installed:boolean;model_installed:boolean;runtime_path:string;model_path:string};
type Q4Discovery={executables:string[];models:string[];configured:{executable:string;model:string};experiment:string;job:Q4Job;installer:Q4Install};

async function request<T>(path:string,method="GET",body?:object):Promise<T>{
  const response=await fetch(path,{method,headers:body?{"Content-Type":"application/json"}:undefined,
    body:body?JSON.stringify(body):undefined});
  const result=await response.json() as T&{detail?:string};
  if(!response.ok)throw Error(result.detail||"Q4 experiment request failed");
  return result;
}

/** Separate, optional runtime. Never reads or edits the active project implicitly. */
export function MossQ4Experiment(){
  const [open,setOpen]=useState(false);
  const [inventory,setInventory]=useState<Q4Discovery|null>(null);
  const [binary,setBinary]=useState("");
  const [model,setModel]=useState("");
  const [audio,setAudio]=useState("");
  const [prompt,setPrompt]=useState("Describe the audible instruments, rhythm, arrangement, and changes in this excerpt.");
  const [job,setJob]=useState<Q4Job|null>(null);
  const [confirmTest,setConfirmTest]=useState(false);
  const [pendingInstall,setPendingInstall]=useState<"runtime"|"model"|null>(null);
  const [advanced,setAdvanced]=useState(false);
  const [installer,setInstaller]=useState<Q4Install|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function refresh(){
    const next=await request<Q4Discovery>("/api/settings/models/q4");
    setInventory(next);setJob(next.job);setInstaller(next.installer);
    setBinary(value=>next.installer.runtime_installed?next.installer.runtime_path:value||next.configured.executable||next.executables[0]||"");
    setModel(value=>next.installer.model_installed?next.installer.model_path:value||next.configured.model||next.models[0]||"");
  }
  useEffect(()=>{if(!open)return;void refresh().catch(e=>setError(String(e)));},[open]);
  useEffect(()=>{
    if(!open||installer?.state!=="running")return;
    const timer=window.setInterval(()=>{void refresh().catch(e=>setError(String(e)));},1500);
    return ()=>window.clearInterval(timer);
  },[open,installer?.state]);
  useEffect(()=>{
    if(!open||job?.state!=="running")return;
    const timer=window.setInterval(()=>{void refresh().catch(e=>setError(String(e)));},2500);
    return ()=>window.clearInterval(timer);
  },[open,job?.state]);
  async function browse(kind:"executable"|"model"|"audio"){
    const result=await request<{path:string|null}>("/api/settings/models/q4/browse","POST",{kind});
    if(!result.path)return;
    if(kind==="executable")setBinary(result.path);
    else if(kind==="model")setModel(result.path);
    else setAudio(result.path);
  }
  async function act(fn:()=>Promise<void>){
    setBusy(true);setError("");
    try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  const installed=!!installer?.runtime_installed&&!!installer?.model_installed;
  const ready=installed&&!!inventory?.configured.model;
  return <div className="song-moss-q4">
    <div className="setting-tool-row">
      <strong>Q4 listening</strong>
      <Status tone={job?.state==="running"?"neutral":job?.state==="failed"?"warning":ready?"success":"neutral"}>{job?.state==="running"?"Analyzing":ready?"Ready (experimental)":installed?"Installed":"Setup needed"}</Status>
      <Button size="compact" variant="secondary" onClick={()=>setOpen(value=>!value)}>{open?"Hide":"Open"}</Button>
    </div>
    {open&&<>
      <div className="setting-controls">
        <Button size="compact" variant="secondary" onClick={()=>setAdvanced(value=>!value)}>{advanced?"Hide setup":"Model & diagnostics"}</Button>
        {!ready&&<span role="status">Configure the local Q4 runtime and model before testing.</span>}
      </div>
      {advanced&&<>
        <div className="setting-tool-row">
          <a href="https://github.com/CrispStrobe/CrispASR/releases" target="_blank" rel="noopener noreferrer">Runtime publisher</a>
          <a href="https://huggingface.co/cstr/MOSS-Audio-4B-Instruct-GGUF" target="_blank" rel="noopener noreferrer">Model publisher</a>
        </div>
        {!installed&&<div className="song-moss-confirm">
          <strong>Local setup</strong>
          <div className="setting-controls">
            {!installer?.runtime_installed&&<Button size="compact" variant="secondary" disabled={busy||installer?.state==="running"}
              onClick={()=>setPendingInstall("runtime")}>Install CrispASR (~714 MB)</Button>}
            {!installer?.model_installed&&<Button size="compact" variant="secondary" disabled={busy||installer?.state==="running"}
              onClick={()=>setPendingInstall("model")}>Download Q4 model (~4.1 GB)</Button>}
          </div>
        </div>}
        {pendingInstall&&<div className="song-moss-confirm" role="group" aria-label="Confirm model download">
          <strong>Approve {pendingInstall==="runtime"?"CrispASR runtime":"Q4 model"} download?</strong>
          <span>Download and verify the selected artifact in the configured shared model folder. No binary will run as part of installation.</span>
          <div className="setting-controls">
            <Button size="compact" variant="primary" disabled={busy} onClick={()=>void act(async()=>{
              const kind=pendingInstall;setPendingInstall(null);
              setInstaller(await request<Q4Install>("/api/settings/models/q4/install","POST",{kind,approved:true}));
            })}>Approve download</Button>
            <Button size="compact" variant="secondary" onClick={()=>setPendingInstall(null)}>Cancel</Button>
          </div>
        </div>}
        {installer?.state==="running"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/>
          <span>{installer.message}: {installer.artifact}
            <small>{(installer.downloaded_bytes/(1024**2)).toFixed(0)} / {installer.total_bytes?(installer.total_bytes/(1024**2)).toFixed(0)+" MiB":"size checking"} {installer.total_bytes?"("+Math.min(100,installer.downloaded_bytes/installer.total_bytes*100).toFixed(1)+"%)":""}</small>
          </span>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{setInstaller(await request<Q4Install>("/api/settings/models/q4/install/cancel","POST"));})}>Cancel</Button>
        </div>}
        {installer?.state==="failed"&&<p role="alert" className="error-message">ERROR: {installer.error.replace(/^ERROR:\s*/,"")}. Installation not completed.</p>}
        <details>
          <summary>Local files and advanced configuration</summary>
          <div className="setting-controls">
            <label className="setting-path">CrispASR executable
              <input aria-label="CrispASR executable path" list="moss-q4-binaries" value={binary} onChange={e=>setBinary(e.target.value)}/>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("executable"))}>Browse executable</Button>
              <datalist id="moss-q4-binaries">{inventory?.executables.map(item=><option key={item} value={item}/>)}</datalist>
            </label>
            <label className="setting-path">MOSS-Audio Q4 GGUF
              <input aria-label="MOSS-Audio Q4 model path" list="moss-q4-models" value={model} onChange={e=>setModel(e.target.value)}/>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("model"))}>Browse GGUF</Button>
              <datalist id="moss-q4-models">{inventory?.models.map(item=><option key={item} value={item}/>)}</datalist>
            </label>
            <Button size="compact" variant="secondary" disabled={busy||!binary||!model||job?.state==="running"} onClick={()=>void act(async()=>{
              await request("/api/settings/models/q4/configure","POST",{executable:binary,model});
              await refresh();
            })}>Use local files</Button>
            <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(refresh)}>Discover</Button>
          </div>
        </details>
      </>}
      <div className="setting-controls">
        <label className="setting-path">Test WAV copy (not current project)
          <input aria-label="Q4 test WAV path" value={audio} onChange={e=>setAudio(e.target.value)} placeholder="D:\\Audio\\test-clip.wav"/>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("audio"))}>Browse WAV</Button>
        </label>
        {advanced&&<label className="setting-path">Audio question
          <textarea aria-label="Q4 audio question" value={prompt} maxLength={400} rows={2} onChange={e=>setPrompt(e.target.value)}/>
        </label>}
        {job?.state==="running"?<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{setJob(await request<Q4Job>("/api/settings/models/q4/cancel","POST"));})}>Cancel test</Button>:
        <Button size="compact" variant="primary" disabled={busy||!audio.trim()||!prompt.trim()||!inventory?.configured.model}
          onClick={()=>setConfirmTest(true)}>Analyze WAV</Button>}
      </div>
      {open&&confirmTest&&job?.state!=="running"&&<div className="song-moss-confirm" role="group" aria-label="Confirm experimental Q4 test">
        <strong>Run experimental Q4 listening test?</strong>
        <span>This will execute the selected local CrispASR program using your WAV test file. It will not modify the audio or active Song Harbor project.</span>
        <div className="setting-controls">
          <Button size="compact" variant="primary" disabled={busy} onClick={()=>void act(async()=>{
            setJob(await request<Q4Job>("/api/settings/models/q4/test","POST",{audio,prompt,approved:true}));
            setConfirmTest(false);
          })}>Approve and run test</Button>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>setConfirmTest(false)}>Cancel</Button>
        </div>
      </div>}
      {job?.state==="running"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/> Processing test audio... {job.elapsed_seconds??0}s elapsed (10-minute cap)</div>}
      {job?.state==="complete"&&<div role="status">Q4 finished processing. Musical claims are unverified.</div>}
      {job&&["complete","failed","cancelled"].includes(job.state)&&<div className="song-moss-confirm">
        <strong>Listening review (unverified)</strong>
        <div className="setting-path">Source: {job.audio}{job.run_id?" | Run: "+job.run_id.slice(0,8):""}</div>
        {job.output_truncated&&<p role="alert" className="error-message">ERROR: Output exceeded 2 MiB. Review is incomplete; inspect the per-run log. No verified analysis produced.</p>}
        {!!job.review?.slices&&<div role="status">{job.review.slices} model slices{job.review.duration_seconds?" | "+job.review.duration_seconds.toFixed(1)+"s source":""}. Not time-aligned.</div>}
        {job.review?.warnings.map((warning,i)=><p key={i}>{warning}</p>)}
        {job.review?.answer?<div style={{whiteSpace:"pre-wrap",maxHeight:260,overflow:"auto",overflowWrap:"anywhere"}}>{job.review.answer}</div>:
          <p>No separate final model answer detected. Inspect the raw run log.</p>}
        <details><summary>Raw model output and diagnostics</summary>
          <pre style={{whiteSpace:"pre-wrap",maxHeight:240,overflow:"auto",overflowWrap:"anywhere"}}>{job.result||"No output captured."}</pre>
          <div className="setting-path">Run log: {job.output_path||job.log_path}</div>
        </details>
      </div>}
      {(error||job?.error)&&<p role="alert" className="error-message">{error||job?.error}</p>}
    </>}
  </div>;
}
