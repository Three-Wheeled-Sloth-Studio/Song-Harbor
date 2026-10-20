import {useEffect,useMemo,useState} from "react";
import type {MouseEvent} from "react";

type Peaks={bins:number;duration_seconds:number;min:number[];max:number[]};
type Row={filename:string;label:string};
function pathFor(peaks:Peaks):string {
  const count=Math.min(peaks.bins,peaks.min.length,peaks.max.length);
  if(count<=0)return "";
  const parts:string[]=[];
  for(let i=0;i<count;i++){
    const x=(i/(count-1||1)*1000).toFixed(2);
    const lo=(20-peaks.min[i]*17).toFixed(2);
    const hi=(20-peaks.max[i]*17).toFixed(2);
    parts.push(`M${x},${hi}V${lo}`);
  }
  return parts.join("");
}
function WaveRow({jobId,row,duration,position,onSeek}:{
  jobId:string;row:Row;duration:number;position:number;onSeek:(time:number)=>void;
}){
  const [peaks,setPeaks]=useState<Peaks|null>(null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();
    setPeaks(null);setFailed(false);
    void fetch(`/api/jobs/${jobId}/waveform/${encodeURIComponent(row.filename)}`,{signal:controller.signal})
      .then(r=>r.ok?r.json() as Promise<Peaks>:Promise.reject(Error("Waveform unavailable")))
      .then(setPeaks).catch(()=>{if(!controller.signal.aborted)setFailed(true);});
    return ()=>controller.abort();
  },[jobId,row.filename]);
  const d=useMemo(()=>peaks?pathFor(peaks):"",[peaks]);
  function seekAt(e:MouseEvent<HTMLButtonElement>){
    if(duration<=0)return;
    const bounds=e.currentTarget.getBoundingClientRect();
    onSeek(Math.max(0,Math.min(duration,(e.clientX-bounds.left)/bounds.width*duration)));
  }
  return <div className="waveform-row">
    <span className="waveform-row-label" title={row.label}>{row.label}</span>
    <button type="button" className="waveform-seek" onClick={seekAt}
      aria-label={`Seek within ${row.label} waveform`} title={`Seek within ${row.label}`}>
      {peaks?<svg viewBox="0 0 1000 40" preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true">
        <path d={d} stroke="currentColor" strokeWidth="0.7" strokeOpacity=".8" fill="none"/>
      </svg>:<span className="waveform-loading">{failed?"Waveform preview unavailable":"Loading waveform…"}</span>}
      {duration>0&&<span className="waveform-playhead" style={{left:`${100*Math.min(position,duration)/duration}%`}}/>}
    </button>
  </div>;
}

export function StemWaveforms({jobId,files,duration,position,onSeek}:{
  jobId:string;files:Row[];duration:number;position:number;onSeek:(time:number)=>void;
}){
  return <section className="waveform-overview" aria-label="Aligned stem waveforms">
    <div className="waveform-overview-heading"><strong>Waveform overview</strong><span>Click to seek · same time axis on all stems</span></div>
    {files.map(row=><WaveRow key={row.filename} jobId={jobId} row={row}
      duration={duration} position={position} onSeek={onSeek}/>)}
  </section>;
}
