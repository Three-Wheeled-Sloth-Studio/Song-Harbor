import {useEffect,useRef,useState} from "react";

type Model={id:string;name:string;installed:boolean;family:string;recommended?:boolean;purpose?:string;source?:string;license_note?:string};
type Install={id:string;status:string;message:string;model_id:string;elapsed_seconds?:number;sha256?:string};
type Candidate={id:string;status:string;message:string;model:string;files:string[];start_seconds:number;duration_seconds:number};
type Props={jobId:string;trackId:string;start:number;duration:number};

async function responseJson<T extends {detail?:string}>(response:Response, operation:string):Promise<T>{
  const body=await response.text();
  let parsed:T;
  try { parsed=JSON.parse(body) as T; }
  catch {
    const snippet=body.trim().slice(0,160);
    throw Error(response.ok
      ? operation+": server returned an invalid response. Update and Reload Song Harbor."
      : operation+": server returned HTTP "+response.status+
        (snippet&&snippet!=="Internal Server Error"?": "+snippet:"")+
        ". Check the Song Harbor server log or restart the app.");
  }
  if(!response.ok)throw Error(parsed.detail||operation+" failed (HTTP "+response.status+")");
  return parsed;
}

export function SeparationPreviewTool({jobId,trackId,start,duration}:Props) {
  const [models,setModels]=useState<Model[]>([]);
  const [model,setModel]=useState("");
  const [candidate,setCandidate]=useState<Candidate|null>(null);
  const [selectedFile,setSelectedFile]=useState("");
  const [reference,setReference]=useState(true);
  const [busy,setBusy]=useState(false);
  const [install,setInstall]=useState<Install|null>(null);
  const [installApproved,setInstallApproved]=useState(false);
  const [error,setError]=useState("");
  const player=useRef<HTMLAudioElement>(null);
  const base="/api/projects/"+encodeURIComponent(jobId)+"/separation";
  useEffect(()=>{
    let live=true;setCandidate(null);setSelectedFile("");setError("");setBusy(false);setInstall(null);setInstallApproved(false);
    void fetch(base+"/models").then(async r=>{return await responseJson<{models:Model[];detail?:string}>(r,"Model discovery");})
      .then(data=>{if(live){setModels(data.models);setModel(old=>data.models.some(m=>m.id===old)?old:(data.models[0]?.id||""));}})
      .catch(e=>{if(live)setError(String(e));});
    return ()=>{live=false;};
  },[base,trackId]);
  useEffect(()=>{
    if(!install||!["queued","running"].includes(install.status))return;
    let live=true;
    const refresh=async()=>{
      try{
        const r=await fetch(base+"/models/install/"+install.id);
        const data=await responseJson<Install&{detail?:string}>(r,"Install status");
        if(!live)return;
        setInstall(data);
        if(data.status==="complete"){
          const catalog=await fetch(base+"/models");
          const listing=await responseJson<{models:Model[];detail?:string}>(catalog,"Model discovery");
          if(live){setModels(listing.models);setModel(data.model_id);setInstallApproved(false);}
        }
      }catch(e){if(live)setError(String(e));}
    };
    const timer=window.setInterval(()=>{void refresh();},1500);
    return ()=>{live=false;window.clearInterval(timer);};
  },[base,install?.id,install?.status]);
  useEffect(()=>{
    if(!candidate||!["queued","running"].includes(candidate.status))return;
    let live=true;
    const poll=async()=>{
      try{
        const r=await fetch(base+"/previews/"+candidate.id);
        const data=await responseJson<Candidate&{detail?:string}>(r,"Preview status");
        if(live){setCandidate(data);if(data.status==="complete")setSelectedFile(old=>old||data.files[0]||"");}
      }catch(e){if(live)setError(String(e));}
    };
    const timer=window.setInterval(()=>{void poll();},1500);
    return ()=>{live=false;window.clearInterval(timer);};
  },[base,candidate?.id,candidate?.status]);
  async function installSelected(){
    if(!model||install?.status==="running"||install?.status==="queued")return;
    setError("");setInstall(null);
    try{
      const r=await fetch(base+"/models/install",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({model_id:model,acknowledged:true})});
      const data=await responseJson<Install&{detail?:string}>(r,"Model installation");
      setInstall(data);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  }
  async function generate(){
    if(busy||!trackId||!model)return;
    setBusy(true);setError("");setCandidate(null);setSelectedFile("");setReference(true);
    try{
      const region=Math.min(30,duration);
      if(!Number.isFinite(start)||region<.5)throw Error("Select at least half a second inside this stem");
      const r=await fetch(base+"/previews",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({track_id:trackId,start_seconds:start,duration_seconds:region,model_id:model})});
      const data=await responseJson<Candidate&{detail?:string}>(r,"Separation preview");
      setCandidate(data);
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  }
  const chosen=models.find(m=>m.id===model);
  const ready=candidate?.status==="complete"&&Boolean(selectedFile);
  const audioUrl=candidate?base+"/previews/"+candidate.id+"/audio/"+encodeURIComponent(reference?"source-region.wav":selectedFile):"";
  function toggle(source:boolean){
    const audio=player.current;const position=audio?.currentTime||0;const wasPlaying=audio&&!audio.paused;
    setReference(source);
    if(audio)window.setTimeout(()=>{audio.currentTime=Math.min(position,audio.duration||position);if(wasPlaying)void audio.play().catch(()=>{});},0);
  }
  return <div className="song-separation-preview">
    <div className="song-midi-region">
      <label title="Specialist separation model">Model <select value={model} onChange={e=>{setModel(e.target.value);setCandidate(null);setInstall(null);setInstallApproved(false);}} aria-label="Separation model">
        {models.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}
      </select></label>
      <button type="button" title="Generate a non-destructive 30-second separation comparison" disabled={busy||!chosen?.installed||!trackId||candidate?.status==="running"||candidate?.status==="queued"} onClick={()=>void generate()}>
        {busy||candidate?.status==="queued"||candidate?.status==="running"?"◌ Processing":"✦ Compare"}
      </button>
    </div>
    {chosen&&!chosen.installed&&<div className="song-separation-install" role="status">
      <p style={{color:"#d79536"}}>⚠ Model not installed</p>
      <p>{chosen.purpose||"Specialist model comparison"}</p>
      {chosen.source&&<a href={chosen.source} target="_blank" rel="noreferrer" title="Review source and licensing">Model source ↗</a>}
      <small>{chosen.license_note||"Verify checkpoint licensing before commercial distribution."}</small>
      {!installApproved?<button type="button" title="Review installation approval" disabled={install?.status==="running"} onClick={()=>setInstallApproved(true)}>↓ Install model</button>:
       <div><span>Downloads this model locally; existing stems stay untouched.</span>
       <button type="button" disabled={install?.status==="queued"||install?.status==="running"} title="Approve local model download" onClick={()=>void installSelected()}>✓ Approve install</button>
       <button type="button" title="Cancel model installation approval" onClick={()=>setInstallApproved(false)}>×</button></div>}
    </div>}
    {install&&<p role={install.status==="failed"?"alert":"status"} className={install.status==="failed"?"error-message":"song-save-notice"}
      style={{color:install.status==="complete"?"#46b879":install.status==="failed"?"#eb6262":"#d79536"}}>
      {install.status==="complete"?"✓ Model installed":install.status==="running"?"◌ Installing model...":install.message}
    </p>}

    {candidate&&<p role={candidate.status==="failed"?"alert":"status"} className={candidate.status==="failed"?"error-message":"song-save-notice"}>
      {candidate.status==="complete"?"✓ Candidate ready":candidate.message}
    </p>}
    {ready&&<div className="song-stem-hub-mix">
      <label title="Choose one of the model's candidate outputs">Candidate <select value={selectedFile} onChange={e=>{setSelectedFile(e.target.value);setReference(false);}}>
        {candidate!.files.map(file=><option key={file} value={file}>{file}</option>)}
      </select></label>
      <div className="song-stem-hub-tabs" role="group" aria-label="Compare original and separated candidate">
        <button type="button" aria-pressed={reference} title="Original unprocessed source region" onClick={()=>toggle(true)}>A Original</button>
        <button type="button" aria-pressed={!reference} title="Specialist model separation candidate" onClick={()=>toggle(false)}>B Candidate</button>
      </div>
      <audio key={audioUrl} ref={player} controls preload="none" src={audioUrl} aria-label="Separation A/B player"/>
      <small>Preview only. Original stems and script remain unchanged.</small>
    </div>}
    {error&&<p role="alert" className="error-message">ERROR: {error}</p>}
  </div>;
}
