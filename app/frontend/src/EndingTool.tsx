import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";

export type SavedEnding={fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"};
type Props={jobId:string;sections:SongSection[];ending:SavedEnding;onChange:(value:SavedEnding)=>void};

export function EndingTool({jobId,sections,ending,onChange}:Props){
  const [fade,setFade]=useState(ending.fade_seconds);
  const [tail,setTail]=useState(ending.tail_seconds);
  const [curve,setCurve]=useState<"smooth"|"linear">(ending.curve);
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  useEffect(()=>{setFade(ending.fade_seconds);setTail(ending.tail_seconds);setCurve(ending.curve);},[ending,jobId]);
  const final=[...sections].sort((a,b)=>a.start_seconds-b.start_seconds).at(-1);
  const maxFade=final?Math.min(30,final.end_seconds-final.start_seconds):0;
  async function save(){
    setSaving(true);setError("");setMessage("");
    try{
      const response=await fetch("/api/projects/"+jobId+"/ending",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({fade_seconds:fade,tail_seconds:tail,curve})
      });
      const data=await response.json() as {ending?:SavedEnding;detail?:string};
      if(!response.ok||!data.ending)throw Error(data.detail||"Could not save ending");
      onChange(data.ending);
      setMessage("Ending saved in the final section. Preview and WAV export use the same treatment.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  return <details className="production-tool-detail">
    <summary>Ending treatments</summary>
    <div className="timeline-loop-controls">
      <p>Fade the dry mix into the final section boundary, preserving the reverb return into optional post-roll.</p>
      <small>Final section: {final?final.kind+" ("+final.end_seconds.toFixed(3)+"s)":"None yet"}</small>
      <label>Dry fade duration (seconds)
        <input aria-label="Ending dry fade seconds" type="number" min="0" max={maxFade} step=".1"
          value={fade} onChange={e=>setFade(Number(e.target.value))}/>
      </label>
      <label>Fade curve
        <select aria-label="Ending fade curve" value={curve} onChange={e=>setCurve(e.target.value as "smooth"|"linear")}>
          <option value="smooth">Smooth</option><option value="linear">Linear</option>
        </select>
      </label>
      <label>Reverb tail after song (seconds)
        <input aria-label="Ending reverb tail seconds" type="number" min="0" max="10" step=".1"
          value={tail} onChange={e=>setTail(Number(e.target.value))}/>
      </label>
      <button type="button" disabled={saving||!final||!Number.isFinite(fade)||!Number.isFinite(tail)||fade<0||fade>maxFade||tail<0||tail>10}
        onClick={()=>{void save();}}>Save ending</button>
      <small>Tail length extends the rendered WAV. Existing stems and original song audio remain unchanged.</small>
      {message&&<p role="status">{message}</p>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </details>;
}
