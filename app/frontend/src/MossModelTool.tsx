import {useCallback,useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type Model={id:string;name:string;status:string};
type Inventory={registered:Model[]};
type Runtime={status:string;model_id:string|null;error:string;port?:number};
type Setup={state:string;runtime_installed:boolean;runtime_python:string;error:string};
type Trust={model_id:string;trusted:boolean;persistent_trust_available:boolean};
type Diagnostics={log_path:string|null;log_tail:string;runtime_kind:string|null;model_id:string|null};
type DependencyStatus={dependencies:{ready:boolean;missing_package:string|null;message:string};repair:{state:string;error:string};repair_log_path:string};

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
  const [trust,setTrust]=useState<Trust|null>(null);
  const [diagnostics,setDiagnostics]=useState<Diagnostics|null>(null);
  const [dependency,setDependency]=useState<DependencyStatus|null>(null);
  const [confirmRepair,setConfirmRepair]=useState(false);
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
      const valid=inventory.registered.filter(item=>item.status==="present-unverified").sort((a,b)=>{
        const rank=(name:string)=>name.toLowerCase().includes("audio-4b")?0:1;
        return rank(a.name)-rank(b.name);
      });
      setModels(valid);setModel(current=>valid.some(x=>x.id===current)?current:valid[0]?.id||"");
      setRuntime(rt);
      setDistro(current=>distros.distros.includes(current)?current:distros.distros[0]||"");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  },[]);
  useEffect(()=>{void refresh();},[refresh]);
  useEffect(()=>{
    if(!model){setTrust(null);return;}
    let alive=true;
    void api<Trust>("/api/settings/models/"+encodeURIComponent(model)+"/trust")
      .then(value=>{if(alive)setTrust(value);})
      .catch(e=>{if(alive)setError(e instanceof Error?e.message:String(e));});
    return ()=>{alive=false;};
  },[model]);
  useEffect(()=>{
    if(runtime?.status!=="failed"&&!runtime?.error)return;
    void api<Diagnostics>("/api/settings/models/runtime/diagnostics").then(setDiagnostics)
      .catch(e=>setError(e instanceof Error?e.message:String(e)));
  },[runtime?.status,runtime?.error]);
  useEffect(()=>{
    if(!distro)return;
    void api<DependencyStatus>("/api/settings/models/wsl/dependencies?distro="+encodeURIComponent(distro)).then(setDependency)
      .catch(e=>setError(e instanceof Error?e.message:String(e)));
  },[distro]);
  useEffect(()=>{
    if(!distro||dependency?.repair.state!=="running")return;
    const handle=window.setInterval(()=>{
      void api<DependencyStatus>("/api/settings/models/wsl/dependencies?distro="+encodeURIComponent(distro))
        .then(setDependency).catch(e=>setError(e instanceof Error?e.message:String(e)));
    },2500);
    return ()=>window.clearInterval(handle);
  },[distro,dependency?.repair.state]);
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
        disabled={busy||!model||!distro||!setup?.runtime_python||!setup?.runtime_installed||dependency?.dependencies.ready===false}
        onClick={()=>{if(trust?.trusted){void act(async()=>{setRuntime(await api<Runtime>("/api/settings/models/runtime/load-wsl","POST",{model_id:model,distro,python_path:setup?.runtime_python,custom_code_approved:false}));});}else{setConfirmLoad(true);}}}>Load MOSS</Button>
      {confirmLoad&&<div className="song-moss-confirm" role="group" aria-label="Confirm MOSS model loading">
        <strong>Trust and load {models.find(item=>item.id===model)?.name||"selected MOSS model"}?</strong>
        <label><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>
          I approve this checkpoint's custom code in WSL. For a verified installed model, this approval is remembered until the checkpoint changes.</label>
        <div className="setting-controls">
          <Button size="compact" variant="primary" disabled={busy||!approved} onClick={()=>void act(async()=>{
            setRuntime(await api<Runtime>("/api/settings/models/runtime/load-wsl","POST",{
              model_id:model,distro,python_path:setup?.runtime_python,custom_code_approved:true
            }));
            setApproved(false);setConfirmLoad(false);
            setTrust(current=>current?.persistent_trust_available?{...current,trusted:true}:current);
          })}>Confirm load</Button>
          <Button size="compact" variant="secondary" onClick={()=>{setConfirmLoad(false);setApproved(false);}}>Cancel</Button>
        </div>
      </div>}
    </>}
    {dependency&&!dependency.dependencies.ready&&<div className="song-moss-confirm" role="group" aria-label="WSL missing dependency">
      <strong>{dependency.dependencies.missing_package==="libnuma1"?"Missing Ubuntu dependency: libnuma1":"WSL dependency check failed"}</strong>
      <span>{dependency.dependencies.message}</span>
      {dependency.dependencies.missing_package==="libnuma1"&&dependency.repair.state!=="running"&&<>
        {!confirmRepair?<Button size="compact" variant="secondary" disabled={busy} onClick={()=>setConfirmRepair(true)}>Repair dependency</Button>:
        <>
          <span>Install the Ubuntu system package libnuma1 using WSL root? No model files or songs will be modified.</span>
          <div className="setting-controls">
            <Button size="compact" variant="primary" disabled={busy} onClick={()=>void act(async()=>{
              const result=await api<{state:string;error:string}>("/api/settings/models/wsl/dependencies/repair","POST",{distro,approved:true});
              setDependency(previous=>previous?{...previous,repair:result}:previous);setConfirmRepair(false);
            })}>Install libnuma1</Button>
            <Button size="compact" variant="secondary" onClick={()=>setConfirmRepair(false)}>Cancel</Button>
          </div>
        </>}
      </>}
      {dependency.repair.state==="running"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/> Installing libnuma1 in WSL...</div>}
      {dependency.repair.state==="failed"&&<><div role="alert" className="error-message">{dependency.repair.error} Log: {dependency.repair_log_path}</div>
        <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{await api<{requested:boolean}>("/api/settings/logs/open","POST");})}>Open logs folder</Button></>}
      {dependency.repair.state==="completed"&&!dependency.dependencies.ready&&<div role="status">Verifying dependency installation...</div>}
    </div>}
    {!models.length&&<div className="setting-path" role="status">Install or register a model in Settings to enable Load.</div>}
    {!!models.length&&!setup?.runtime_installed&&<div className="setting-path" role="status">Install the MOSS WSL runtime in Settings before loading.</div>}
    {runtime?.status==="ready"&&<div role="status">Model service ready. Audio listening is not connected yet.</div>}
    {runtime?.status==="starting"&&<div role="status" className="song-moss-progress"><span className="song-sfz-spinner" aria-hidden="true"/> Starting model service...</div>}
    {error&&<p role="alert" className="error-message">{error}</p>}
    {runtime?.error&&<p role="alert" className="error-message">{runtime.error}</p>}
    {diagnostics?.log_path&&runtime?.error&&<details className="song-moss-diagnostics"><summary>Failure details</summary>
      <div className="setting-path">Log: {diagnostics.log_path}</div>
      <Button size="compact" variant="secondary" onClick={()=>void navigator.clipboard?.writeText(diagnostics.log_path||"")}>Copy path</Button>
      <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{await api<{requested:boolean}>("/api/settings/logs/open","POST");})}>Open logs folder</Button>
      <pre>{diagnostics.log_tail||"Log empty. Process may have exited before writing diagnostics."}</pre>
    </details>}
  </div>;
}
