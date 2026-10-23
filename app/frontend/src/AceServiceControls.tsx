import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type AceRuntime={status:string;ready?:boolean;loaded_model?:string|null;models?:{name:string;loaded?:boolean;validated_tasks?:string[]}[];error?:string};
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
  const [error,setError]=useState("");
  async function refresh(){
    try{
      const result=await fetch("/api/ace/service",{cache:"no-store"});
      if(!result.ok)throw Error("ACE status unavailable");
      setStatus(await result.json() as AceServiceState);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  }
  useEffect(()=>{
    if(!open)return;
    void refresh();
    const id=window.setInterval(()=>{void refresh();},3000);
    return()=>window.clearInterval(id);
  },[open]);
  async function change(action:"start"|"stop"|"initialize"){
    setBusy(true);setError("");
    try{
      const response=await fetch("/api/ace/service/"+action,{method:"POST",headers:action==="initialize"?{"Content-Type":"application/json"}:undefined,body:action==="initialize"?JSON.stringify({model:"acestep-v15-turbo"}):undefined});
      const data=await response.json() as AceServiceState&{detail?:string};
      if(!response.ok)throw Error(data.detail||"ACE "+action+" failed");
      setStatus(data);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  const state=status?.state||"unknown";
  return <div className="setting-tool-row" style={{alignItems:"flex-start",gap:"0.75rem"}}>
    <div style={{flex:"1 1 260px",minWidth:0}}>
      <strong>ACE-Step</strong>{" "}
      <Status tone={state==="running_ready"?"success":state==="not_installed"?"warning":"neutral"}>{label(state)}</Status>
      <p className="setting-description" style={{margin:"0.35rem 0"}}>
        {state==="running_uninitialized"?"API connected. Model loads on first generation or explicit initialization.":
         state==="starting"?"Local API starting. Model initialization may take longer.":
         state==="installed_stopped"?"Ready to start the local ACE API without a separate console.":
         state==="not_installed"?"No supported ACE installation was detected at the configured location.":
         state==="running_ready"?"Generation model initialized and available.":
         "Local ACE generator connection."}
      </p>
      <small style={{overflowWrap:"anywhere"}}>Installation: {status?.installation||"Checking..."}</small>
      {status?.runtime?.models?.length? <div><small>Models: {status.runtime.models.map(m=>m.name+(m.loaded?" (loaded)":"")).join(", ")}</small></div>:null}
      {status?.runtime?.status==="connected"&&!status.owned?<div><small>External ACE instance. Song Harbor will not stop it.</small></div>:null}
      {status?.runtime?.error&&state==="running_uninitialized"?<div><small>{status.runtime.error}</small></div>:null}
    </div>
    <div className="setting-controls">
      {status?.can_start&&<Button size="compact" variant="primary" disabled={busy} onClick={()=>void change("start")}>Enable ACE</Button>}
      {state==="running_uninitialized"&&status?.runtime?.models?.some(m=>m.name==="acestep-v15-turbo")&&<Button size="compact" variant="primary" disabled={busy} onClick={()=>void change("initialize")}>Load turbo model</Button>}
      {status?.can_stop&&<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void change("stop")}>Stop ACE</Button>}
      <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void refresh()}>Refresh</Button>
    </div>
    {error&&<small role="alert" className="error-message">{error}</small>}
  </div>;
}
