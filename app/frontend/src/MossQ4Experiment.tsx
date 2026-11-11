import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type Q4Job={state:string;error:string;elapsed_seconds:number|null;log_path:string;log_tail:string;result:string;audio:string};
type Q4Discovery={executables:string[];models:string[];configured:{executable:string;model:string};experiment:string;job:Q4Job};

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
  const [approved,setApproved]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  async function refresh(){
    const next=await request<Q4Discovery>("/api/settings/models/q4");
    setInventory(next);setJob(next.job);
    setBinary(value=>value||next.configured.executable||next.executables[0]||"");
    setModel(value=>value||next.configured.model||next.models[0]||"");
  }
  useEffect(()=>{if(!open)return;void refresh().catch(e=>setError(String(e)));},[open]);
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
  return <div className="song-moss-q4">
    <div className="setting-tool-row">
      <strong>Q4 GGUF / CrispASR</strong>
      <Status tone={job?.state==="complete"?"success":job?.state==="failed"?"warning":"neutral"}>Experimental</Status>
      <Button size="compact" variant="secondary" onClick={()=>setOpen(value=>!value)}>{open?"Hide":"Open"}</Button>
    </div>
    {open&&<>
      <div className="setting-tool-row"><a href="https://github.com/CrispStrobe/CrispASR/releases" target="_blank" rel="noopener noreferrer">CrispASR runtime</a><a href="https://huggingface.co/cstr/MOSS-Audio-4B-Instruct-GGUF" target="_blank" rel="noopener noreferrer">Q4 audio model</a></div>
      <div className="setting-controls">
        <label className="setting-path">CrispASR executable
          <input aria-label="CrispASR executable path" list="moss-q4-binaries" value={binary} onChange={e=>setBinary(e.target.value)} placeholder="D:\\Apps\\...\\crispasr.exe"/>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("executable"))}>Browse executable</Button>
          <datalist id="moss-q4-binaries">{inventory?.executables.map(item=><option key={item} value={item}/>)}</datalist>
        </label>
        <label className="setting-path">MOSS-Audio Q4 GGUF
          <input aria-label="MOSS-Audio Q4 model path" list="moss-q4-models" value={model} onChange={e=>setModel(e.target.value)} placeholder="D:\\Apps\\...\\moss-audio-q4.gguf"/>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("model"))}>Browse GGUF</Button>
          <datalist id="moss-q4-models">{inventory?.models.map(item=><option key={item} value={item}/>)}</datalist>
        </label>
        <Button size="compact" variant="secondary" disabled={busy||!binary||!model||job?.state==="running"} onClick={()=>void act(async()=>{
          await request("/api/settings/models/q4/configure","POST",{executable:binary,model});
          await refresh();
        })}>Use local files</Button>
        <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(refresh)}>Discover</Button>
      </div>
      <div className="setting-controls">
        <label className="setting-path">Test WAV copy (not current project)
          <input aria-label="Q4 test WAV path" value={audio} onChange={e=>setAudio(e.target.value)} placeholder="D:\\Audio\\test-clip.wav"/>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(()=>browse("audio"))}>Browse WAV</Button>
        </label>
        <label className="setting-path">Audio question
          <textarea aria-label="Q4 audio question" value={prompt} maxLength={400} rows={2} onChange={e=>setPrompt(e.target.value)}/>
        </label>
        <label className="setting-tool-row"><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>
          Approve experimental local executable and audio test</label>
        {job?.state==="running"?<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{setJob(await request<Q4Job>("/api/settings/models/q4/cancel","POST"));})}>Cancel test</Button>:
        <Button size="compact" variant="primary" disabled={busy||!approved||!audio||!prompt.trim()||!inventory?.configured.model}
          onClick={()=>void act(async()=>{
            setJob(await request<Q4Job>("/api/settings/models/q4/test","POST",{audio,prompt,approved:true}));
            setApproved(false);
          })}>Test Q4 listening</Button>}
      </div>
      {job?.state==="running"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/> Processing test audio... {job.elapsed_seconds??0}s elapsed (10-minute cap)</div>}
      {job?.state==="complete"&&<div role="status">Process exited successfully. Output below is unverified experimental data.</div>}
      {(error||job?.error)&&<p role="alert" className="error-message">{error||job?.error}</p>}
      {job&&["complete","failed","cancelled"].includes(job.state)&&<details><summary>Q4 output and log</summary>
        <div className="setting-path">{job.log_path}</div>
        <pre style={{whiteSpace:"pre-wrap",maxHeight:180,overflow:"auto"}}>{job.log_tail||"No output captured."}</pre>
      </details>}
    </>}
  </div>;
}
