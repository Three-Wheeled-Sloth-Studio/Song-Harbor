import {useEffect,useState} from "react";
import {Button,Dialog,Status} from "@tws-ui/core/react";
import {FfmpegSetup} from "./FfmpegSetup";
import {AceServiceControls} from "./AceServiceControls";

type Working = {active_directory:string;configured_directory:string;default_directory:string;restart_required:boolean;warning:string};
type Health = {ready:boolean;separator_ready:boolean;model:string;model_directory:string;ffmpeg?:{directory:string}|null;needs_setup?:string[]};
type FluidSynthSettings={configured_path:string;resolved_path:string|null};

export function AppSettings({open,onOpenChange,health,onReady}:{
  open:boolean;onOpenChange:(value:boolean)=>void;health:Health|null;onReady:(value:Health)=>void;
}) {
  const [data,setData]=useState<Working|null>(null);
  const [path,setPath]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [showTools,setShowTools]=useState(false);
  const [ffmpegOpen,setFfmpegOpen]=useState(false);
  const [fluid,setFluid]=useState<FluidSynthSettings|null>(null);
  const [fluidPath,setFluidPath]=useState("");

  useEffect(()=>{
    if(!open)return;
    setError("");setNotice("");setShowTools(false);
    void fetch("/api/settings/working-files").then(async r=>{
      if(!r.ok)throw Error("Could not read storage settings");
      return await r.json() as Working;
    }).then(x=>{setData(x);setPath(x.configured_directory);}).catch(e=>setError(String(e)));
    void fetch("/api/settings/fluidsynth").then(async r=>{if(!r.ok)throw Error("Could not read FluidSynth settings");return await r.json() as FluidSynthSettings;})
      .then(x=>{setFluid(x);setFluidPath(x.configured_path||x.resolved_path||"");}).catch(e=>setError(String(e)));
  },[open]);
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
          <AceServiceControls open={open&&showTools}/></>}
        </div>
        {notice&&<p role="status" className="song-save-notice">{notice}</p>}
        {error&&<p role="alert" className="error-message">{error}</p>}
      </div>
    </Dialog>
    <FfmpegSetup open={open&&ffmpegOpen} onOpenChange={v=>setFfmpegOpen(v)} onReady={next=>{onReady(next);setFfmpegOpen(false);}}/>
  </>;
}
