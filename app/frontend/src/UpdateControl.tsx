import {useEffect,useState} from "react";

type UpdateState={supported:boolean;reason?:string;branch?:string;current?:string;
  latest?:string;update_available?:boolean;can_fast_forward?:boolean;busy?:boolean};

export function UpdateControl({instanceToken}:{instanceToken:string}){
  const [state,setState]=useState<UpdateState|null>(null);
  const [installedVersion,setInstalledVersion]=useState("0.1.0:1:local");
  const [versionDetail,setVersionDetail]=useState("Development build");
  useEffect(()=>{
    let active=true;
    void fetch("/api/runtime/version",{cache:"no-store"})
      .then(async response=>{if(!response.ok)throw Error("Version unavailable");return response.json() as Promise<{label?:string;branch?:string;commit?:string}>;})
      .then(version=>{if(active){setInstalledVersion(version.label||"0.1.0:1:local");setVersionDetail([version.branch,version.commit].filter(Boolean).join(" · ")||"Local development build");}})
      .catch(()=>{});
    return ()=>{active=false;};
  },[]);
  const [checking,setChecking]=useState(false);
  const [restarting,setRestarting]=useState(false);
  const [error,setError]=useState("");
  async function check(){
    setChecking(true);setError("");
    try{
      const response=await fetch("/api/runtime/update",{cache:"no-store"});
      const data=await response.json() as UpdateState & {detail?:string};
      if(!response.ok)throw Error(data.detail||"Cannot check updates");
      setState(data);
      if(data.current&&data.branch)setVersionDetail(data.branch+" · "+data.current.slice(0,8));
    }catch(e){setError(e instanceof Error?e.message:"Cannot check updates");}
    finally{setChecking(false);}
  }
  async function install(){
    if(!state?.supported||!state.can_fast_forward||!instanceToken||state.busy)return;
    if(!window.confirm("Save any edits not yet applied inside Song Harbor before restarting. A separate console will update the checkout, rebuild the interface and reopen the app. Continue?"))return;
    setRestarting(true);setError("");
    try{
      const response=await fetch("/api/runtime/update/relaunch",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({instance_token:instanceToken})
      });
      const data=await response.json() as {detail?:string};
      if(!response.ok)throw Error(data.detail||"Could not start update");
    }catch(e){
      setRestarting(false);
      setError(e instanceof Error?e.message:"Update could not start");
    }
  }
  return <div className="song-update-control">
    <small className="song-version-badge" aria-label={"Installed Song Harbor version "+installedVersion}
      title={"Version:Revision:Build · "+installedVersion+" · "+versionDetail}>{installedVersion}</small>
    <button type="button" className="dependency-indicator" title="Check Song Harbor updates"
      aria-label="Check Song Harbor updates" disabled={checking||restarting}
      onClick={()=>{void check();}}>{checking?"…":"↻"}</button>
    {state&&<div className="song-update-status" role="status">
      {state.supported
        ?<><strong>{state.update_available?"Update available":"Up to date"}</strong>
            <small>{state.branch} · {state.current} → {state.latest}</small>
            {state.busy&&<small>Processing active; restart unavailable.</small>}
            {!state.can_fast_forward&&<small>{state.reason||"Local history diverged"}</small>}
            {state.update_available&&state.can_fast_forward&&!state.busy&&<button type="button"
              disabled={restarting} onClick={()=>{void install();}}>Install &amp; relaunch</button>}
          </>
        :<small>{state.reason||"Update unavailable"}</small>}
      {restarting&&<small>Update launched. This window will disconnect; use the new Song Harbor window when it opens.</small>}
      <button type="button" title="Close update status" aria-label="Close update status" onClick={()=>setState(null)}>×</button>
    </div>}
    {error&&<small role="alert" className="song-update-error">{error}</small>}
  </div>;
}
