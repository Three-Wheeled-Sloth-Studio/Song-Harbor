import {useEffect,useState} from "react";
import {Button,Dialog,Status} from "@tws-ui/core/react";
import {FfmpegSetup} from "./FfmpegSetup";
import {AceServiceControls} from "./AceServiceControls";

type Working = {active_directory:string;configured_directory:string;default_directory:string;restart_required:boolean;warning:string};
type Health = {ready:boolean;separator_ready:boolean;model:string;model_directory:string;ffmpeg?:{directory:string}|null;needs_setup?:string[]};
type ModelSettings={configured_directory:string;active_directory:string;restart_required:boolean;exists:boolean;downloads_enabled:boolean;models_loaded:boolean};
type DiscoveredModel={id?:string;name:string;path:string;family?:string;status:string;registered?:boolean;files?:number;bytes_present?:number};
type ModelInventory={registered:DiscoveredModel[];discovered:DiscoveredModel[];scan_limit:number};
type ModelRuntime={status:"unloaded"|"starting"|"ready"|"connected"|"failed";model_id:string|null;error:string;port?:number};
type FluidSynthSettings={configured_path:string;resolved_path:string|null};

export function AppSettings({open,onOpenChange,health,onReady,focus}:{
  open:boolean;onOpenChange:(value:boolean)=>void;health:Health|null;onReady:(value:Health)=>void;
  focus?:"fluidsynth"|"sfizz"|null;
}) {
  const [models,setModels]=useState<ModelSettings|null>(null);
  const [inventory,setInventory]=useState<ModelInventory|null>(null);
  const [runtime,setRuntime]=useState<ModelRuntime|null>(null);
  const [locatePath,setLocatePath]=useState("");
  const [runtimePython,setRuntimePython]=useState("");
  const [savedRuntimePython,setSavedRuntimePython]=useState("");
  const [approveCode,setApproveCode]=useState(false);
  const [modelPath,setModelPath]=useState("");
  const [showModels,setShowModels]=useState(false);
  const [data,setData]=useState<Working|null>(null);
  const [path,setPath]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [showTools,setShowTools]=useState(false);
  const [ffmpegOpen,setFfmpegOpen]=useState(false);
  const [fluid,setFluid]=useState<FluidSynthSettings|null>(null);
  const [fluidPath,setFluidPath]=useState("");
  const [sfizz,setSfizz]=useState<FluidSynthSettings|null>(null);
  const [sfizzPath,setSfizzPath]=useState("");

  useEffect(()=>{
    if(!open)return;
    setError("");setNotice("");setShowTools(focus==="fluidsynth"||focus==="sfizz");
    void fetch("/api/settings/working-files").then(async r=>{
      if(!r.ok)throw Error("Could not read storage settings");
      return await r.json() as Working;
    }).then(x=>{setData(x);setPath(x.configured_directory);}).catch(e=>setError(String(e)));
    void fetch("/api/settings/models").then(async r=>{if(!r.ok)throw Error("Could not read model settings");return await r.json() as ModelSettings;}).then(x=>{setModels(x);setModelPath(x.configured_directory);}).catch(e=>setError(String(e)));
    void refreshModels();
    void response<{python_executable:string}>("/api/settings/models/runtime/config","GET").then(x=>{setRuntimePython(x.python_executable);setSavedRuntimePython(x.python_executable);}).catch(e=>setError(String(e)));
    void fetch("/api/settings/fluidsynth").then(async r=>{if(!r.ok)throw Error("Could not read FluidSynth settings");return await r.json() as FluidSynthSettings;})
      .then(x=>{setFluid(x);setFluidPath(x.configured_path||x.resolved_path||"");}).catch(e=>setError(String(e)));
    void fetch("/api/settings/sfizz").then(async r=>{
      if(!r.ok)throw Error("Could not read sfizz settings");
      return await r.json() as FluidSynthSettings;
    }).then(x=>{setSfizz(x);setSfizzPath(x.configured_path||x.resolved_path||"");})
      .catch(e=>setError(String(e)));
  },[open,focus]);
  async function refreshModels(){
    try {
      const [found,state]=await Promise.all([
        response<ModelInventory>("/api/settings/models/discover","GET"),
        response<ModelRuntime>("/api/settings/models/runtime","GET")
      ]);
      setInventory(found);setRuntime(state);
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
  }
  useEffect(()=>{
    if(!open||!showModels||runtime?.status!=="starting")return;
    const handle=window.setInterval(()=>{void refreshModels();},3000);
    return ()=>window.clearInterval(handle);
  },[open,showModels,runtime?.status]);
  async function act(operation:()=>Promise<void>){
    setBusy(true);setError("");setNotice("");
    try{await operation();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function response<T>(url:string,method:string,body?:object):Promise<T>{
    const r=await fetch(url,{method,headers:body?{"Content-Type":"application/json"}:undefined,body:body?JSON.stringify(body):undefined});
    const x=await r.json() as T&{detail?:string};
    if(!r.ok)throw Error(x.detail||"Settings operation failed");
    return x;
  }
  return <>
    <Dialog open={open&&!ffmpegOpen} onOpenChange={onOpenChange} title="Settings" description="Workspace and local component preferences">
      <div className="app-settings">
        <div className="setting-heading"><strong>Working files</strong><Status tone={data?.restart_required?"warning":"neutral"}>{data?.restart_required?"Restart needed":"Local"}</Status></div>
        <p className="setting-description">Song projects, imported recordings, stems, exports, and the Library index. Models, application files and caches stay on this computer.</p>
        <div className="setting-path" title={data?.active_directory}>Active: {data?.active_directory||"Loading..."}</div>
        <div className="setting-controls">
          <input aria-label="Working files directory" value={path} onChange={e=>setPath(e.target.value)} placeholder="Select a working files folder"/>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
            const x=await response<{path:string|null}>("/api/settings/working-files/browse","POST");
            if(x.path)setPath(x.path);
          })}>Browse</Button>
        </div>
        <div className="setting-controls">
          <Button size="compact" variant="primary" disabled={busy||!path.trim()||path===data?.configured_directory} onClick={()=>void act(async()=>{
            const x=await response<{configured_directory:string;restart_required:boolean; migration_performed:boolean}>("/api/settings/working-files","PUT",{path});
            setData(prev=>prev?{...prev,configured_directory:x.configured_directory,restart_required:x.restart_required}:prev);
            setNotice("Location saved. Close Song Harbor and relaunch to use it. Existing files were not moved.");
          })}>Save location</Button>
          <Button size="compact" variant="secondary" disabled={busy||!data} onClick={()=>setPath(data?.default_directory||"")}>Use default</Button>
        </div>
        <p className="setting-warning">Changing locations does not migrate existing songs. To share between computers, use a Google Drive mirrored folder and allow synchronization to finish before opening Song Harbor on another PC. Do not run two copies against the same synced Library database simultaneously.</p>
        <div className="setting-tools">
          <button type="button" className="setting-tools-toggle" aria-expanded={showModels} onClick={()=>setShowModels(v=>!v)}>Models <span>{showModels?"▴":"▾"}</span></button>
          {showModels&&<>
            <div className="setting-tool-row"><span>Shared model folder <Status tone={models?.restart_required?"warning":"neutral"}>{models?.restart_required?"Restart needed":"Local"}</Status></span></div>
            <div className="setting-path" title={models?.active_directory}>Active: {models?.active_directory||"Loading..."}</div>
            <div className="setting-controls setting-component-path">
              <input aria-label="Shared model directory" value={modelPath} onChange={e=>setModelPath(e.target.value)} placeholder="Dedicated model directory"/>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
                const x=await response<{path:string|null}>("/api/settings/models/browse","POST");
                if(x.path)setModelPath(x.path);
              })}>Browse</Button>
            </div>
            <div className="setting-controls">
              <Button size="compact" variant="primary" disabled={busy||!modelPath.trim()||modelPath===models?.configured_directory} onClick={()=>void act(async()=>{
                const x=await response<ModelSettings>("/api/settings/models","PUT",{path:modelPath});
                setModels(x);setModelPath(x.configured_directory);
                setNotice("Model folder saved. Relaunch to activate. No models moved or downloaded.");
              })}>Save location</Button>
            </div>
            <div className="setting-tool-row">
              <span>Local checkpoints <Status tone="neutral">{(inventory?.registered.length||0)} registered</Status></span>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(refreshModels)}>Scan folder</Button>
            </div>
            {(inventory?.registered||[]).map(item=><div className="setting-tool-row" key={item.id} title={item.path}>
              <span>{item.name} <Status tone={item.status==="present-unverified"?"neutral":"warning"}>{runtime?.model_id===item.id?runtime?.status:item.status}</Status></span>
              <div className="setting-controls">
                {runtime?.model_id===item.id&&runtime?.status!=="failed"
                  ?<Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{setRuntime(await response<ModelRuntime>("/api/settings/models/runtime/unload","POST"));})}>{runtime?.status==="connected"?"Disconnect":"Unload"}</Button>
                  :<Button size="compact" variant="secondary" disabled={busy||item.status!=="present-unverified"||runtime?.status==="starting"||runtime?.status==="ready"||runtime?.status==="connected"||!runtimePython.trim()||!approveCode}
                    title="Explicitly start isolated offline SGLang. Requires reviewed custom model code and a configured runtime."
                    onClick={()=>void act(async()=>{setRuntime(await response<ModelRuntime>("/api/settings/models/runtime/load","POST",{model_id:item.id,python_executable:runtimePython,custom_code_approved:approveCode}));})}>Load</Button>}
                <Button size="compact" variant="secondary" title="Connect to an existing WSL2 MOSS server on localhost:18791; this does not start or stop WSL." disabled={busy||item.status!=="present-unverified"||runtime?.status==="starting"||runtime?.status==="ready"||runtime?.status==="connected"} onClick={()=>void act(async()=>{
                  setRuntime(await response<ModelRuntime>("/api/settings/models/runtime/attach","POST",{model_id:item.id}));
                })}>Connect WSL</Button>
                <Button size="compact" variant="secondary" disabled={busy||runtime?.model_id===item.id} onClick={()=>void act(async()=>{
                  await response<{unregistered:boolean}>("/api/settings/models/register/"+encodeURIComponent(item.id||""),"DELETE");
                  await refreshModels();
                })}>Unlink</Button>
              </div>
            </div>)}
            {(inventory?.discovered||[]).map(item=><div className="setting-tool-row" key={item.path} title={item.path}>
              <span>{item.name} <Status tone={item.status==="incomplete"?"warning":"neutral"}>{item.status}</Status></span>
              <Button size="compact" variant="secondary" disabled={busy||item.status!=="present-unverified"} onClick={()=>void act(async()=>{
                await response<DiscoveredModel>("/api/settings/models/register","POST",{path:item.path});await refreshModels();
              })}>Register</Button>
            </div>)}
            <div className="setting-controls setting-component-path">
              <input aria-label="Existing MOSS checkpoint directory" value={locatePath} onChange={e=>setLocatePath(e.target.value)} placeholder="Existing checkpoint folder"/>
              <Button size="compact" variant="secondary" disabled={busy||!locatePath.trim()} onClick={()=>void act(async()=>{
                await response<DiscoveredModel>("/api/settings/models/register","POST",{path:locatePath});setLocatePath("");await refreshModels();
              })}>Register path</Button>
            </div>
            <div className="setting-controls setting-component-path">
              <input aria-label="SGLang Python executable" value={runtimePython} onChange={e=>setRuntimePython(e.target.value)} placeholder="Isolated SGLang python.exe (existing)"/>
              <Button size="compact" variant="secondary" disabled={busy||!runtimePython.trim()||runtimePython===savedRuntimePython} onClick={()=>void act(async()=>{
                const x=await response<{python_executable:string}>("/api/settings/models/runtime/config","PUT",{path:runtimePython});
                setSavedRuntimePython(x.python_executable);setRuntimePython(x.python_executable);
                setNotice("Runtime executable saved. No model started.");
              })}>Save runtime</Button>
            </div>
            <label className="setting-tool-row"><input type="checkbox" checked={approveCode} onChange={e=>setApproveCode(e.target.checked)}/> I reviewed and approve this checkpoint's custom Python code</label>
            {runtime?.status==="starting"&&<p role="status">Starting model. Readiness check pending...</p>}
            {runtime?.status==="connected"&&<p role="status">Connected to external WSL model. Disconnect leaves the external server running.</p>}
            {runtime?.status==="failed"&&<p role="alert" className="error-message">{runtime.error}</p>}
            {runtime?.status==="ready"&&<p role="status">Local model endpoint responding on port {runtime.port}. Audio inference not yet validated.</p>}
          </>}
        </div>
        <div className="setting-tools">
          <button type="button" className="setting-tools-toggle" aria-expanded={showTools} onClick={()=>setShowTools(v=>!v)}>Components <span>{showTools?"▴":"▾"}</span></button>
          {showTools&&<><div className="setting-tool-row">
            <span>FFmpeg <Status tone={health?.ffmpeg?"success":"warning"}>{health?.ffmpeg?"Ready":"Setup needed"}</Status></span>
            <Button size="compact" variant="secondary" onClick={()=>setFfmpegOpen(true)}>Configure</Button>
          </div>
          <div className="setting-tool-row">
            <span>FluidSynth <Status tone={fluid?.resolved_path?"success":"warning"}>{fluid?.resolved_path?"Ready":"Not configured"}</Status></span>
          </div>
          <div className="setting-controls setting-component-path">
            <input aria-label="FluidSynth executable path" value={fluidPath}
              onChange={e=>setFluidPath(e.target.value)} placeholder="Path to fluidsynth.exe or its bin folder"/>
            <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
              const x=await response<{path:string|null}>("/api/settings/fluidsynth/browse","POST");
              if(x.path)setFluidPath(x.path);
            })}>Browse</Button>
          </div>
          <div className="setting-controls">
            <Button size="compact" variant="primary" disabled={busy||!fluidPath.trim()||fluidPath===fluid?.configured_path} onClick={()=>void act(async()=>{
              const x=await response<FluidSynthSettings>("/api/settings/fluidsynth","PUT",{path:fluidPath});
              setFluid(x);setFluidPath(x.configured_path);
              setNotice("FluidSynth verified and saved. Ready for SF2 rendering.");
            })}>Verify & save</Button>
            <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
              const x=await response<FluidSynthSettings>("/api/settings/fluidsynth","GET");
              setFluid(x);setFluidPath(x.configured_path||x.resolved_path||"");
              setNotice(x.resolved_path?"FluidSynth detected.":"FluidSynth not detected in standard locations.");
            })}>Detect</Button>
          </div>
          <div className="setting-tool-row">
            <span>SFZ renderer <Status tone={sfizz?.resolved_path?"success":"warning"}>{sfizz?.resolved_path?"Ready":"Not configured"}</Status></span>
          </div>
          <div className="setting-controls setting-component-path">
            <input aria-label="sfizz renderer executable path" value={sfizzPath}
              onChange={e=>setSfizzPath(e.target.value)} placeholder="Path to sfizz_render.exe"/>
            <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
              const x=await response<{path:string|null}>("/api/settings/sfizz/browse","POST");
              if(x.path)setSfizzPath(x.path);
            })}>Browse</Button>
          </div>
          <div className="setting-controls">
            <Button size="compact" variant="primary" disabled={busy||!sfizzPath.trim()||sfizzPath===sfizz?.configured_path}
              onClick={()=>void act(async()=>{
                const x=await response<FluidSynthSettings>("/api/settings/sfizz","PUT",{path:sfizzPath});
                setSfizz(x);setSfizzPath(x.configured_path);
                setNotice("sfizz renderer verified and saved for SFZ rendering.");
              })}>Verify & save</Button>
            <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
              const x=await response<FluidSynthSettings>("/api/settings/sfizz","GET");
              setSfizz(x);setSfizzPath(x.configured_path||x.resolved_path||"");
              setNotice(x.resolved_path?"sfizz renderer detected.":"sfizz renderer not detected in configured path or PATH.");
            })}>Detect</Button>
          </div>
          <AceServiceControls open={open&&showTools}/></>}
        </div>
        {notice&&<p role="status" className="song-save-notice">{notice}</p>}
        {error&&<p role="alert" className="error-message">{error}</p>}
      </div>
    </Dialog>
    <FfmpegSetup open={open&&ffmpegOpen} onOpenChange={v=>setFfmpegOpen(v)} onReady={next=>{onReady(next);setFfmpegOpen(false);}}/>
  </>;
}
