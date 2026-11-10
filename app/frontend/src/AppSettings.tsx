import {useEffect,useState} from "react";
import {Button,Dialog,Status} from "@tws-ui/core/react";
import {FfmpegSetup} from "./FfmpegSetup";
import {AceServiceControls} from "./AceServiceControls";

type Working = {active_directory:string;configured_directory:string;default_directory:string;restart_required:boolean;warning:string};
type Health = {ready:boolean;separator_ready:boolean;model:string;model_directory:string;ffmpeg?:{directory:string}|null;needs_setup?:string[]};
type ModelSettings={configured_directory:string;active_directory:string;restart_required:boolean;exists:boolean;downloads_enabled:boolean;models_loaded:boolean};
type DiscoveredModel={id?:string;name:string;path:string;family?:string;storage?:string;distro?:string;status:string;registered?:boolean;files?:number;bytes_present?:number};
type ModelInventory={registered:DiscoveredModel[];discovered:DiscoveredModel[];scan_limit:number};
type ModelRuntime={status:"unloaded"|"starting"|"ready"|"connected"|"failed";model_id:string|null;error:string;port?:number};
type WslStatus={available:boolean;distros:string[];message:string};
type MossSetupCatalog={id:string;name:string;repo:string;license:string;fit:string;installed:boolean;path:string};
type MossSetup={state:"idle"|"running"|"finished"|"failed";operation:string|null;model:string|null;distro:string|null;runtime_installed:boolean;runtime_python:string;catalog:MossSetupCatalog[];error:string;log_tail:string};
type WslInstall={state:"idle"|"installing"|"completed"|"failed";destination:string;message:string};
type WslProbe={distro:string;python_candidates:string[];probe_ok:boolean;gpu_visible:boolean;message:string};
type FluidSynthSettings={configured_path:string;resolved_path:string|null};

export function AppSettings({open,onOpenChange,health,onReady,focus}:{
  open:boolean;onOpenChange:(value:boolean)=>void;health:Health|null;onReady:(value:Health)=>void;
  focus?:"fluidsynth"|"sfizz"|"models"|null;
}) {
  const [models,setModels]=useState<ModelSettings|null>(null);
  const [inventory,setInventory]=useState<ModelInventory|null>(null);
  const [runtime,setRuntime]=useState<ModelRuntime|null>(null);
  const [locatePath,setLocatePath]=useState("");
  const [wslModelPath,setWslModelPath]=useState("");
  const [runtimePython,setRuntimePython]=useState("");
  const [savedRuntimePython,setSavedRuntimePython]=useState("");
  const [approveCode,setApproveCode]=useState(false);
  const [modelPath,setModelPath]=useState("");
  const [showModels,setShowModels]=useState(true);
  const [wsl,setWsl]=useState<WslStatus|null>(null);
  const [mossSetup,setMossSetup]=useState<MossSetup|null>(null);
  const [setupModel,setSetupModel]=useState("moss-audio-4b");
  const [approveSetup,setApproveSetup]=useState(false);
  const [wslInstall,setWslInstall]=useState<WslInstall|null>(null);
  const [wslInstallFolder,setWslInstallFolder]=useState("");
  const [wslInstallApproved,setWslInstallApproved]=useState(false);
  const [showWslInstall,setShowWslInstall]=useState(false);
  const [wslDistro,setWslDistro]=useState("");
  const [wslProbe,setWslProbe]=useState<WslProbe|null>(null);
  const [wslPython,setWslPython]=useState("");
  const [selectedModel,setSelectedModel]=useState("");
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
    setError("");setNotice("");setShowTools(focus==="fluidsynth"||focus==="sfizz");if(focus==="models")setShowModels(true);
    void fetch("/api/settings/working-files").then(async r=>{
      if(!r.ok)throw Error("Could not read storage settings");
      return await r.json() as Working;
    }).then(x=>{setData(x);setPath(x.configured_directory);}).catch(e=>setError(String(e)));
    void fetch("/api/settings/models").then(async r=>{if(!r.ok)throw Error("Could not read model settings");return await r.json() as ModelSettings;}).then(x=>{setModels(x);setModelPath(x.configured_directory);}).catch(e=>setError(String(e)));
    void refreshModels();
    void response<MossSetup>("/api/settings/models/setup","GET").then(setMossSetup).catch(e=>setError(String(e)));
    void response<WslInstall>("/api/settings/models/wsl/install","GET").then(setWslInstall).catch(e=>setError(String(e)));
    void response<WslStatus>("/api/settings/models/wsl","GET").then(x=>{
      setWsl(x);setWslDistro(v=>x.distros.includes(v)?v:x.distros[0]||"");
    }).catch(e=>setError(String(e)));
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
      setSelectedModel(current=>found.registered.some(item=>item.id===current&&item.status==="present-unverified")?current:found.registered.find(item=>item.status==="present-unverified")?.id||"");
    } catch(e) {setError(e instanceof Error?e.message:String(e));}
  }
  useEffect(()=>{
    if(!open||!showModels||runtime?.status!=="starting")return;
    const handle=window.setInterval(()=>{void refreshModels();},3000);
    return ()=>window.clearInterval(handle);
  },[open,showModels,runtime?.status]);
  useEffect(()=>{
    if(!open||!showModels||mossSetup?.state!=="running")return;
    const handle=window.setInterval(()=>{
      void response<MossSetup>("/api/settings/models/setup?distro="+encodeURIComponent(wslDistro),"GET").then(next=>{
        setMossSetup(next);
        if(next.state==="finished"){
          if(next.runtime_python)setWslPython(next.runtime_python);
          void refreshModels();
        }
      }).catch(e=>setError(String(e)));
    },2500);
    return ()=>window.clearInterval(handle);
  },[open,showModels,mossSetup?.state,wslDistro]);
  async function startMossSetup(operation:"runtime"|"checkpoint"){
    if(!wslDistro)throw Error("ERROR: Select an installed WSL distribution.");
    const x=await response<MossSetup>("/api/settings/models/setup","POST",{
      distro:wslDistro,operation,model:operation==="checkpoint"?setupModel:null,approved:approveSetup
    });
    setMossSetup(x);setApproveSetup(false);
  }
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
              <strong>MOSS loader</strong>
              <Status tone={runtime?.status==="ready"||runtime?.status==="connected"?"success":runtime?.status==="failed"?"warning":"neutral"}>{runtime?.status||"Checking"}</Status>
            </div>
            <div className="setting-controls">
              <span>WSL</span>
              <select aria-label="WSL distribution" value={wslDistro} onChange={e=>{setWslDistro(e.target.value);setWslProbe(null);setWslPython("");}}>
                <option value="">Select distribution</option>
                {(wsl?.distros||[]).map(name=><option key={name} value={name}>{name}</option>)}
              </select>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
                const x=await response<WslStatus>("/api/settings/models/wsl","GET");setWsl(x);setWslDistro(v=>x.distros.includes(v)?v:x.distros[0]||"");
              })}>Detect WSL</Button>
              <Button size="compact" variant="secondary" disabled={busy||!wslDistro} onClick={()=>void act(async()=>{
                const x=await response<WslProbe>("/api/settings/models/wsl/probe","POST",{distro:wslDistro});
                setWslProbe(x);setWslPython(x.python_candidates[0]||"");
              })}>Inspect</Button>
            </div>
            {wsl?.message&&<p role="status">{wsl.message}</p>}
            <div className="setting-tool-row">
              <span>WSL setup <Status tone={wsl?.distros.length?"success":"warning"}>{wsl?.distros.length?"Installed":"Check setup"}</Status></span>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>setShowWslInstall(v=>!v)}>{showWslInstall?"Hide setup":"Install WSL"}</Button>
            </div>
            {showWslInstall&&<div className="setting-tools">
              <div className="setting-controls setting-component-path">
                <input aria-label="New Ubuntu WSL installation directory" value={wslInstallFolder}
                  onChange={e=>setWslInstallFolder(e.target.value)} placeholder="D:\\WSL\\SongHarborUbuntu (new folder)"/>
                <Button size="compact" variant="primary" disabled={busy||wslInstall?.state==="installing"||!wsl?.available||!wslInstallFolder.trim()||!wslInstallApproved||(wsl?.distros||[]).includes("Ubuntu")}
                  onClick={()=>void act(async()=>{
                    const x=await response<WslInstall>("/api/settings/models/wsl/install","POST",{distro:"Ubuntu",destination:wslInstallFolder,approved:wslInstallApproved});
                    setWslInstall(x);
                  })}>Install Ubuntu</Button>
              </div>
              <label className="setting-tool-row"><input type="checkbox" checked={wslInstallApproved}
                onChange={e=>setWslInstallApproved(e.target.checked)}/> Approve Ubuntu download and installation in selected folder</label>
              {wslInstall?.message&&<p role="status">{wslInstall.message}</p>}
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
                setWslInstall(await response<WslInstall>("/api/settings/models/wsl/install","GET"));
                const x=await response<WslStatus>("/api/settings/models/wsl","GET");setWsl(x);
              })}>Check installation</Button>
            </div>}

            {wslProbe&&<div className="setting-controls setting-component-path">
              <input aria-label="WSL SGLang Python path" value={wslPython} onChange={e=>setWslPython(e.target.value)} placeholder="/home/user/.venv/bin/python"/>
              <Status tone={wslProbe.gpu_visible?"success":"warning"}>{wslProbe.gpu_visible?"GPU visible":"GPU unverified"}</Status>
            </div>}
            <div className="setting-tool-row">
              <strong>Install MOSS</strong>
              <Status tone={mossSetup?.state==="failed"?"warning":mossSetup?.runtime_installed?"success":"neutral"}>
                {mossSetup?.state==="running"?"Installing":mossSetup?.runtime_installed?"Runtime installed":"Setup needed"}
              </Status>
            </div>
            <div className="setting-controls">
              <Button size="compact" variant="secondary"
                disabled={busy||!wslDistro||!approveSetup||mossSetup?.state==="running"||!!mossSetup?.runtime_installed}
                onClick={()=>void act(async()=>{await startMossSetup("runtime");})}>Install MOSS runtime</Button>
              <select aria-label="MOSS checkpoint to download" value={setupModel} onChange={e=>setSetupModel(e.target.value)}>
                {(mossSetup?.catalog||[]).map(item=><option key={item.id} value={item.id}>{item.name}{item.installed?" (installed)":""}</option>)}
              </select>
              <Button size="compact" variant="secondary"
                disabled={busy||!wslDistro||!approveSetup||!mossSetup?.runtime_installed||mossSetup?.state==="running"||!!mossSetup?.catalog.find(x=>x.id===setupModel)?.installed}
                onClick={()=>void act(async()=>{await startMossSetup("checkpoint");})}>Download model</Button>
            </div>
            <label className="setting-tool-row"><input type="checkbox" checked={approveSetup} onChange={e=>setApproveSetup(e.target.checked)}/>
              Approve selected download/install to the shared model drive</label>
            {mossSetup?.state==="running"&&<div role="status" className="setting-path">Installing {mossSetup.operation==="runtime"?"MOSS runtime":mossSetup.model}. View current log below.</div>}
            {mossSetup?.state==="failed"&&<div role="alert" className="error-message">{mossSetup.error}</div>}
            {(mossSetup?.state==="running"||mossSetup?.state==="failed")&&<details><summary>Installation log</summary>
              <pre style={{whiteSpace:"pre-wrap",maxHeight:"150px",overflow:"auto"}}>{mossSetup.log_tail||"Initializing..."}</pre>
            </details>}
            <div className="setting-controls setting-component-path">
              <select aria-label="MOSS model to load" value={selectedModel} onChange={e=>setSelectedModel(e.target.value)}>
                <option value="">Select registered MOSS model</option>
                {(inventory?.registered||[]).filter(item=>item.status==="present-unverified").map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
              <Button size="compact" variant="primary" disabled={busy||!selectedModel||!wslDistro||!wslPython.trim()||!approveCode||runtime?.status==="ready"||runtime?.status==="starting"||runtime?.status==="connected"}
                title={!selectedModel?"Register a checkpoint first":!wslPython?"Inspect WSL or select its Python environment":!approveCode?"Approve reviewed checkpoint code first":"Start MOSS in WSL explicitly"}
                onClick={()=>void act(async()=>{
                  setRuntime(await response<ModelRuntime>("/api/settings/models/runtime/load-wsl","POST",{model_id:selectedModel,distro:wslDistro,python_path:wslPython,custom_code_approved:approveCode}));
                })}>Load MOSS</Button>
              {(runtime?.status==="ready"||runtime?.status==="starting"||runtime?.status==="connected")&&
                <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(async()=>{
                  setRuntime(await response<ModelRuntime>("/api/settings/models/runtime/unload","POST"));
                })}>Unload</Button>}
            </div>
            {!inventory?.registered.length&&<div role="status" className="setting-path">No registered MOSS model. Scan or register a checkpoint below to enable Load.</div>}
            {wsl&&!wsl.available&&<div role="alert" className="error-message">ERROR: WSL is not installed or wsl.exe is unavailable. No model loaded.</div>}
            {wsl?.available&&!wsl.distros.length&&<div role="status" className="setting-path">No WSL distribution detected. Use WSL setup below; existing D: installations will not be replaced.</div>}
            {!!wslDistro&&!wslProbe&&<div role="status" className="setting-path">Inspect the selected WSL distribution to locate Python and check GPU visibility.</div>}
            {!!wslProbe&&!wslPython&&<div role="status" className="setting-path">Enter the existing SGLang Python path inside WSL to enable Load.</div>}
            {!!selectedModel&&!!wslPython&&!approveCode&&<div role="status" className="setting-path">Review and approve the registered model's custom code before loading.</div>}

            <div className="setting-tool-row">
              <span>Local checkpoints <Status tone="neutral">{(inventory?.registered.length||0)} registered</Status></span>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void act(refreshModels)}>Scan folder</Button>
            </div>
            {(inventory?.registered||[]).map(item=><div className="setting-tool-row" key={item.id} title={item.path}>
              <span>{item.name}{item.storage==="wsl"?" (WSL "+item.distro+")":""} <Status tone={item.status==="present-unverified"?"neutral":"warning"}>{runtime?.model_id===item.id?runtime?.status:item.status}</Status></span>
              <div className="setting-controls">
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
              <input aria-label="Existing checkpoint path inside WSL" value={wslModelPath} onChange={e=>setWslModelPath(e.target.value)}
                placeholder="/home/user/models/MOSS-Music-8B-Instruct"/>
              <Button size="compact" variant="secondary" disabled={busy||!wslDistro||!wslModelPath.trim()} onClick={()=>void act(async()=>{
                await response<DiscoveredModel>("/api/settings/models/register-wsl","POST",{distro:wslDistro,path:wslModelPath});
                setWslModelPath("");await refreshModels();
              })}>Register WSL path</Button>
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
