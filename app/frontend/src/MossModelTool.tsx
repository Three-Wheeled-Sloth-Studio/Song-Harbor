import {useCallback,useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type Model={id:string;name:string;status:string};
type Inventory={registered:Model[]};
type Runtime={status:string;model_id:string|null;error:string;port?:number};
type Setup={state:string;runtime_installed:boolean;runtime_python:string;error:string};

async function api<T>(path:string,method="GET",body?:object):Promise<T>{
  const response=await fetch(path,{method,headers:body?{"Content-Type":"application/json"}:undefined,
    body:body?JSON.stringify(body):undefined});
  const result=await response.json() as T&{detail?:string};
  if(!response.ok)throw Error(result.detail||"MOSS request failed");
  return result;
}

/** In-workbench model control. Never edits song state or triggers inference. */
export function MossModelTool({onConfigure}:{onConfigure:()=>void}){
  const [models,setModels]=useState<Model[]>([]);
  const [model,setModel]=useState("");
  const [distro,setDistro]=useState("");
  const [runtime,setRuntime]=useState<Runtime|null>(null);
  const [setup,setSetup]=useState<Setup|null>(null);
  const [approved,setApproved]=useState(false);
  const [confirmLoad,setConfirmLoad]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const refresh=useCallback(async()=>{
    try{
      const [inventory,rt,distros]=await Promise.all([
        api<Inventory>("/api/settings/models/discover"),
        api<Runtime>("/api/settings/models/runtime"),
        api<{distros:string[]}>("/api/settings/models/wsl")
      ]);
      const valid=inventory.registered.filter(item=>item.status==="present-unverified");
      setModels(valid);setModel(current=>valid.some(x=>x.id===current)?current:valid[0]?.id||"");
      setRuntime(rt);
      setDistro(current=>distros.distros.includes(current)?current:distros.distros[0]||"");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  },[]);
  useEffect(()=>{void refresh();},[refresh]);
  useEffect(()=>{
    if(!distro)return;
    void api<Setup>("/api/settings/models/setup?distro="+encodeURIComponent(distro)).then(setSetup)
      .catch(e=>setError(e instanceof Error?e.message:String(e)));
  },[distro]);
  useEffect(()=>{
    if(runtime?.status!=="starting"&&runtime?.status!=="ready"&&runtime?.status!=="connected")return;
    const handle=window.setInterval(()=>{void api<Runtime>("/api/settings/models/runtime").then(setRuntime).catch(()=>{});},3000);
    return ()=>window.clearInterval(handle);
  },[runtime?.status]);
  async function act(action:()=>Promise<void>){
    setBusy(true);setError("");
    try{await action();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  const active=runtime?.status==="starting"||runtime?.status==="ready"||runtime?.status==="connected";
  return <div className="song-moss-tool">
    <div className="setting-tool-row"><strong>MOSS music understanding</strong>
      <Status tone={runtime?.status==="ready"||runtime?.status==="connected"?"success":runtime?.status==="failed"?"warning":"neutral"}>
        {runtime?.status||"Checking"}
      </Status></div>
    <div className="setting-controls">
      <select aria-label="MOSS model" value={model} onChange={e=>{setModel(e.target.value);setConfirmLoad(false);setApproved(false);}}>
        {!models.length&&<option value="">No installed MOSS models</option>}
        {models.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
      </select>
      <Button size="compact" variant="secondary" disabled={busy} onClick={onConfigure}>Set up models</Button>
      <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void refresh()}>Refresh</Button>
    </div>
    {active?<div className="setting-controls">
      <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
        setRuntime(await api<Runtime>("/api/settings/models/runtime/unload","POST"));
      })}>{runtime?.status==="connected"?"Disconnect":"Unload MOSS"}</Button>
    </div>:<>
      <Button size="compact" variant="primary"
        disabled={busy||!model||!distro||!setup?.runtime_python||!setup?.runtime_installed}
        onClick={()=>setConfirmLoad(true)}>Load MOSS</Button>
      {confirmLoad&&<div className="song-moss-confirm" role="group" aria-label="Confirm MOSS model loading">
        <strong>Load {models.find(item=>item.id===model)?.name||"selected MOSS model"}?</strong>
        <label><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>
          I approve running this checkpoint's custom code in WSL.</label>
        <div className="setting-controls">
          <Button size="compact" variant="primary" disabled={busy||!approved} onClick={()=>void act(async()=>{
            setRuntime(await api<Runtime>("/api/settings/models/runtime/load-wsl","POST",{
              model_id:model,distro,python_path:setup?.runtime_python,custom_code_approved:true
            }));
            setApproved(false);setConfirmLoad(false);
          })}>Confirm load</Button>
          <Button size="compact" variant="secondary" onClick={()=>{setConfirmLoad(false);setApproved(false);}}>Cancel</Button>
        </div>
      </div>}
    </>}
    {!models.length&&<div className="setting-path" role="status">Install or register a model in Settings to enable Load.</div>}
    {!!models.length&&!setup?.runtime_installed&&<div className="setting-path" role="status">Install the MOSS WSL runtime in Settings before loading.</div>}
    {runtime?.status==="ready"&&<div role="status">Model service ready. Audio listening is not connected yet.</div>}
    {runtime?.status==="starting"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/> Starting model service...</div>}
    {error&&<p role="alert" className="error-message">{error}</p>}
    {runtime?.status==="failed"&&<p role="alert" className="error-message">{runtime.error}</p>}
  </div>;
}
