import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type AceRuntime={status:string;ready?:boolean;loaded_model?:string|null;models?:{name:string;loaded?:boolean;validated_tasks?:string[]}[];error?:string};
type AceInstallState={phase:string;model:string;checkpoint_root:string;installed:boolean;running:boolean;error?:string|null};
type AceServiceState={state:string;installed:boolean;owned:boolean;pid:number|null;installation:string;can_start:boolean;can_stop:boolean;runtime:AceRuntime};

function label(state:string):string{
  switch(state){
    case "running_ready":return "Model ready";
    case "running_uninitialized":return "Connected, model not loaded";
    case "installed_stopped":return "Installed, stopped";
    case "starting":return "Starting";
    case "not_installed":return "Not installed";
    default:return "Unavailable";
  }
}

export function AceServiceControls({open}:{open:boolean}){
  const [status,setStatus]=useState<AceServiceState|null>(null);
  const [busy,setBusy]=useState(false);
  const [install,setInstall]=useState<AceInstallState|null>(null);
  const [error,setError]=useState("");
  async function refresh(){
    try{
      const result=await fetch("/api/ace/service",{cache:"no-store"});
      if(!result.ok)throw Error("ACE status unavailable");
      setStatus(await result.json() as AceServiceState);
      const modelResponse=await fetch("/api/ace/models/install",{cache:"no-store"});
      if(modelResponse.ok)setInstall(await modelResponse.json() as AceInstallState);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  }
  useEffect(()=>{
    if(!open)return;
    void refresh();
    const id=window.setInterval(()=>{void refresh();},3000);
    return()=>window.clearInterval(id);
  },[open]);
  async function change(action:"start"|"stop"|"initialize",model="acestep-v15-turbo"){
    setBusy(true);setError("");
    try{
      const response=await fetch("/api/ace/service/"+action,{method:"POST",headers:action==="initialize"?{"Content-Type":"application/json"}:undefined,body:action==="initialize"?JSON.stringify({model}):undefined});
      const data=await response.json() as AceServiceState&{detail?:string};
      if(!response.ok)throw Error(data.detail||"ACE "+action+" failed");
      setStatus(data);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function installBase(){
    if(!install||install.installed||install.running||busy)return;
    if(!window.confirm("Download ACE-Step Base into ACE's existing checkpoints folder?\n"+install.checkpoint_root+"\n\nThis downloads several GB from the official ACE-Step Hugging Face repository. Existing Turbo files will not be changed."))return;
    setBusy(true);setError("");
    try{
      const response=await fetch("/api/ace/models/install/base",{method:"POST"});
      const result=await response.json() as AceInstallState&{detail?:string};
      if(!response.ok)throw Error(result.detail||"Base installation could not start");
      setInstall(result);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  const state=status?.state||"unknown";
  const activeModel=status?.runtime?.ready?status.runtime.loaded_model:null;
  const activeLabel=activeModel==="acestep-v15-base"?"Base":activeModel==="acestep-v15-turbo"?"Turbo":activeModel||null;
  return <div className="setting-tool-row" style={{alignItems:"center",gap:"0.65rem",flexWrap:"wrap"}}>
    <strong>ACE-Step</strong>
    <Status tone={state==="running_ready"?"success":state==="not_installed"?"warning":"neutral"}>{activeLabel?activeLabel+" active":label(state)}</Status>
    <div className="setting-controls" style={{marginLeft:"auto"}}>
      {status?.can_start&&<Button size="compact" variant="primary" disabled={busy} onClick={()=>void change("start")}>Enable</Button>}
      {state==="running_uninitialized"&&status?.runtime?.models?.some(m=>m.name==="acestep-v15-turbo")&&<Button size="compact" variant="primary" disabled={busy} onClick={()=>void change("initialize")}>Load Turbo</Button>}
      {install?.installed&&status?.runtime?.status==="connected"&&status.runtime.loaded_model!=="acestep-v15-base"&&<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void change("initialize","acestep-v15-base")}>Switch to Base</Button>}
      {status?.can_stop&&<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void change("stop")}>Stop</Button>}
      <details>
        <summary style={{cursor:"pointer",fontSize:"0.82rem"}}>Details</summary>
        <div style={{padding:"0.4rem 0",maxWidth:"26rem"}}>
          <small style={{display:"block",overflowWrap:"anywhere"}}>Installation: {status?.installed?status.installation:"Not found"}</small>
          <small style={{display:"block"}}>Service: {status?.owned?"Managed by Song Harbor":status?.runtime?.status==="connected"?"External connection":"Not running"}{status?.pid?" (PID "+status.pid+")":""}</small>
          <small style={{display:"block"}}>Models: {status?.runtime?.models?.map(m=>m.name+(m.name===activeModel?" (active)":"")).join(", ")||"None reported"}</small>
          {status?.runtime?.error&&<small style={{display:"block",overflowWrap:"anywhere"}}>{status.runtime.error}</small>}
          <small style={{display:"block",overflowWrap:"anywhere"}}>ACE checkpoints: {install?.checkpoint_root||"Checking..."}</small>
          {install?.installed?<small style={{display:"block"}}>Base checkpoint installed</small>
            :<Button size="compact" variant="secondary" disabled={busy||install?.running||!status?.installed}
                 onClick={()=>void installBase()}>{install?.running?"Downloading Base...":"Install Base model"}</Button>}
          {install?.phase==="failed"&&<small role="alert" style={{display:"block"}}>{install.error||"Model download failed"}</small>}
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void refresh()}>Refresh</Button>
        </div>
      </details>
    </div>
    {error&&<small role="alert" className="error-message">{error}</small>}
  </div>;
}
