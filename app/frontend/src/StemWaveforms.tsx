import {useEffect,useMemo,useState} from "react";
import type {MouseEvent} from "react";

type Peaks={bins:number;duration_seconds:number;min:number[];max:number[]};
export type WaveRowData={filename:string;label:string;waveUrl?:string;children?:WaveRowData[]};
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
function WaveRow({jobId,row,duration,position,onSeek,viewStart,viewEnd}:{
  jobId:string;row:WaveRowData;duration:number;position:number;onSeek:(time:number)=>void;viewStart:number;viewEnd:number;
}){
  const [peaks,setPeaks]=useState<Peaks|null>(null);
  const [failed,setFailed]=useState(false);
  useEffect(()=>{
    const controller=new AbortController();
    setPeaks(null);setFailed(false);
    void fetch(row.waveUrl||`/api/jobs/${jobId}/waveform/${encodeURIComponent(row.filename)}`,{signal:controller.signal})
      .then(r=>r.ok?r.json() as Promise<Peaks>:Promise.reject(Error("Waveform unavailable")))
      .then(setPeaks).catch(()=>{if(!controller.signal.aborted)setFailed(true);});
    return ()=>controller.abort();
  },[jobId,row.filename,row.waveUrl]);
  const d=useMemo(()=>peaks?pathFor(peaks):"",[peaks]);
  function seekAt(e:MouseEvent<HTMLButtonElement>){
    if(duration<=0)return;
    const bounds=e.currentTarget.getBoundingClientRect();
    onSeek(Math.max(0,Math.min(duration,viewStart+(e.clientX-bounds.left)/bounds.width*(viewEnd-viewStart))));
  }
  return <div className="waveform-row">
    <span className="waveform-row-label" title={row.label}>{row.label}</span>
    <button type="button" className="waveform-seek" onClick={seekAt}
      aria-label={`Seek within ${row.label} waveform`} title={`Seek within ${row.label}`}>
      {peaks?<svg viewBox={`${duration>0?1000*viewStart/duration:0} 0 ${duration>0?Math.max(0.01,1000*(viewEnd-viewStart)/duration):1000} 40`} preserveAspectRatio="none" width="100%" height="100%" aria-hidden="true">
        <path d={d} stroke="currentColor" strokeWidth="0.7" strokeOpacity=".8" fill="none"/>
      </svg>:<span className="waveform-loading">{failed?"Waveform preview unavailable":"Loading waveform…"}</span>}
      {viewEnd>viewStart && position>=viewStart && position<=viewEnd &&<span className="waveform-playhead" style={{left:`${100*(position-viewStart)/(viewEnd-viewStart)}%`}}/>}
    </button>
  </div>;
}

export function StemWaveforms({jobId,files,duration,position,onSeek,viewStart,viewEnd}:{
  jobId:string;files:WaveRowData[];duration:number;position:number;onSeek:(time:number)=>void;viewStart:number;viewEnd:number;
}){
  return <section className="waveform-overview" aria-label="Aligned stem waveforms">
    <div className="waveform-overview-heading"><strong>Stem waveforms</strong><span>Click to seek · split channels appear below their stem</span></div>
    {files.map(row=><div key={row.filename}>
      <WaveRow jobId={jobId} row={row} duration={duration} position={position} onSeek={onSeek} viewStart={viewStart} viewEnd={viewEnd}/>
      {row.children?.map(child=><div className="waveform-child-row" key={child.filename}>
        <WaveRow jobId={jobId} row={child} duration={duration} position={position} onSeek={onSeek}/>
      </div>)}
    </div>)}
  </section>;
}
