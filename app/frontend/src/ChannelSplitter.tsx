import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

const LABELS=["Vocals","Drums","Bass","Guitar","Piano","Other"];
function label(filename:string){return LABELS.find(x=>filename.includes("("+x+")"))||filename;}
export function ChannelSplitter({jobId,files,onMissingFfmpeg}:{
  jobId:string;files:string[];onMissingFfmpeg?:(retry:()=>void)=>void;
}) {
  const [expanded,setExpanded]=useState(false);
  const [chosen,setChosen]=useState<string[]>(files);
  const [busy,setBusy]=useState(false);
  const [folder,setFolder]=useState("");
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  useEffect(()=>{setChosen(files);setFolder("");setError("");setNotice("");setExpanded(false);},[jobId,files]);
  async function split(){
    if(!chosen.length||busy)return;
    setBusy(true);setError("");setNotice("");
    try {
      const response=await fetch(`/api/projects/${jobId}/channels/split`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({filenames:chosen})
      });
      const result=await response.json() as {directory?:string;track_count?:number;detail?:string};
      if(!response.ok) {
        if(response.status===409&&/ffmpeg/i.test(result.detail||"")&&onMissingFfmpeg){
          onMissingFfmpeg(()=>{void split();});return;
        }
        throw Error(result.detail||"Could not split channels");
      }
      setFolder(result.directory||"");
      setNotice(`${result.track_count} mono WAV files exported. Original stereo stems unchanged.`);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function openFolder(){
    try {
      const response=await fetch(`/api/projects/${jobId}/channels/open-folder`,{method:"POST"});
      if(!response.ok)throw Error("Could not open channel export folder");
    } catch(e){setError(e instanceof Error?e.message:String(e));}
  }
  return <div className="channel-split-tool">
    <button type="button" className="channel-split-toggle" aria-expanded={expanded} onClick={()=>setExpanded(x=>!x)}>
      <span>Split stereo channels</span><span aria-hidden="true">{expanded?"▴":"▾"}</span>
    </button>
    {expanded&&<>
      <p className="channel-split-hint">Extract original left and right channels as individual aligned mono tracks. This is not instrument separation or stereo widening.</p>
      <div className="channel-split-options">
        {files.map(filename=><label key={filename}><input type="checkbox" checked={chosen.includes(filename)} disabled={busy}
          onChange={e=>setChosen(old=>e.target.checked?[...old,filename]:old.filter(x=>x!==filename))}/>{label(filename)}</label>)}
      </div>
      <div className="channel-split-actions">
        <Button size="compact" variant="primary" disabled={busy||chosen.length===0} onClick={()=>{void split();}}>
          {busy?"Splitting…":`Split selected (${chosen.length})`}
        </Button>
        {folder&&<Button size="compact" variant="secondary" onClick={()=>{void openFolder();}}>Open files</Button>}
        {folder&&<Status tone="success">Exported</Status>}
      </div>
      {notice&&<p role="status" className="song-save-notice">{notice}</p>}
      {error&&<p role="alert" className="error-message">{error}</p>}
    </>}
  </div>;
}
