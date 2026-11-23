import {useEffect,useRef,useState} from "react";

type Model={id:string;name:string;installed:boolean;family:string};
type Candidate={id:string;status:string;message:string;model:string;files:string[];start_seconds:number;duration_seconds:number};
type Props={jobId:string;trackId:string;start:number;duration:number};

export function SeparationPreviewTool({jobId,trackId,start,duration}:Props) {
  const [models,setModels]=useState<Model[]>([]);
  const [model,setModel]=useState("");
  const [candidate,setCandidate]=useState<Candidate|null>(null);
  const [selectedFile,setSelectedFile]=useState("");
  const [reference,setReference]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const player=useRef<HTMLAudioElement>(null);
  const base="/api/projects/"+encodeURIComponent(jobId)+"/separation";
  useEffect(()=>{
    let live=true;setCandidate(null);setSelectedFile("");setError("");setBusy(false);
    void fetch(base+"/models").then(async r=>{const data=await r.json();if(!r.ok)throw Error(data.detail||"Model lookup failed");return data as {models:Model[]};})
      .then(data=>{if(live){setModels(data.models);setModel(old=>data.models.some(m=>m.id===old)?old:(data.models[0]?.id||""));}})
      .catch(e=>{if(live)setError(String(e));});
    return ()=>{live=false;};
  },[base,trackId]);
  useEffect(()=>{
    if(!candidate||!["queued","running"].includes(candidate.status))return;
    let live=true;
    const poll=async()=>{
      try{
        const r=await fetch(base+"/previews/"+candidate.id);
        const data=await r.json() as Candidate&{detail?:string};
        if(!r.ok)throw Error(data.detail||"Preview status unavailable");
        if(live){setCandidate(data);if(data.status==="complete")setSelectedFile(old=>old||data.files[0]||"");}
      }catch(e){if(live)setError(String(e));}
    };
    const timer=window.setInterval(()=>{void poll();},1500);
    return ()=>{live=false;window.clearInterval(timer);};
  },[base,candidate?.id,candidate?.status]);
  async function generate(){
    if(busy||!trackId||!model)return;
    setBusy(true);setError("");setCandidate(null);setSelectedFile("");setReference(true);
    try{
      const region=Math.min(30,duration);
      if(!Number.isFinite(start)||region<.5)throw Error("Select at least half a second inside this stem");
      const r=await fetch(base+"/previews",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({track_id:trackId,start_seconds:start,duration_seconds:region,model_id:model})});
      const data=await r.json() as Candidate&{detail?:string};
      if(!r.ok)throw Error(data.detail||"Separation preview failed");
      setCandidate(data);
    }catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}
  }
  const ready=candidate?.status==="complete"&&Boolean(selectedFile);
  const audioUrl=candidate?base+"/previews/"+candidate.id+"/audio/"+encodeURIComponent(reference?"source-region.wav":selectedFile):"";
  function toggle(source:boolean){
    const audio=player.current;const position=audio?.currentTime||0;const wasPlaying=audio&&!audio.paused;
    setReference(source);
    if(audio)window.setTimeout(()=>{audio.currentTime=Math.min(position,audio.duration||position);if(wasPlaying)void audio.play().catch(()=>{});},0);
  }
  return <div className="song-separation-preview">
    <div className="song-midi-region">
      <label title="Installed local separation model">Model <select value={model} onChange={e=>{setModel(e.target.value);setCandidate(null);}} aria-label="Separation model">
        {models.map(m=><option key={m.id} value={m.id}>{m.name}</option>)}
      </select></label>
      <button type="button" title="Generate a non-destructive 30-second separation comparison" disabled={busy||!model||!trackId||candidate?.status==="running"||candidate?.status==="queued"} onClick={()=>void generate()}>
        {busy||candidate?.status==="queued"||candidate?.status==="running"?"◌ Processing":"✦ Compare"}
      </button>
    </div>
    {!models.length&&<p role="status" className="song-save-notice">No installed separator models found. No downloads were started.</p>}
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
