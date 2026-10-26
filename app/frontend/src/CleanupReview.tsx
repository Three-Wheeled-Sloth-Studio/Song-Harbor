import {useEffect,useMemo,useState} from "react";
import {FINDING_GROUPS,type AudioFinding,type AudioFindingKind} from "./AudioCleanupAnalyzer";
import type {StageComparison} from "./AudioStageComparison";

const FILTERS=["All","Levels","Transitions","Vocal / high frequency","Quiet passages","Stereo / mono","Dynamics","Signal audit"] as const;
const stamp=(seconds:number)=>{
  const whole=Math.floor(Math.max(0,seconds));
  return String(Math.floor(whole/60)).padStart(2,"0")+":"+String(whole%60).padStart(2,"0");
};
export function CleanupReview({
  findings,comparison,scanned,stale=false,analyzing,error,ready,busy,onAnalyze,onSeek,onLoop,onTryCorrection,onTryDeclick
}:{
  findings:readonly AudioFinding[];
  comparison?:StageComparison|null;
  scanned:boolean;stale?:boolean;analyzing:boolean;error:string;ready:boolean;busy:boolean;
  onAnalyze:()=>void;
  onSeek:(seconds:number)=>void;
  onLoop:(start:number,end:number)=>void;
  onTryCorrection:(finding:AudioFinding)=>void;
  onTryDeclick:(finding:AudioFinding)=>void;
}){
  const [filter,setFilter]=useState<string>("All");
  const [reviewed,setReviewed]=useState<Set<string>>(()=>new Set());
  const [showReviewed,setShowReviewed]=useState(false);
  const [markedIntentional,setMarkedIntentional]=useState<Set<string>>(()=>new Set());
  const keyOf=(finding:AudioFinding)=>finding.kind+":"+finding.timeSeconds.toFixed(2);
  // New scan invalidates previous decisions about which candidates are reviewed.
  useEffect(()=>{setReviewed(new Set());setMarkedIntentional(new Set());},[findings]);
  const categories=useMemo(()=>new Set(findings.map(item=>FINDING_GROUPS[item.kind])),[findings]);
  const visible=useMemo(()=>findings.filter(item=>
    (filter==="All"||FINDING_GROUPS[item.kind]===filter) &&
    (showReviewed||!reviewed.has(keyOf(item)))),[findings,filter,reviewed,showReviewed]);
  const warningCount=findings.filter(item=>item.severity==="warning").length;
  const nextItem=visible[0];
  return <details className="production-tool-detail song-cleanup-panel" aria-label="Sound cleanup analyzer" open>
    <summary>◇ Sound cleanup <span className="song-cleanup-summary-counter">{scanned?findings.length:"Scan"}</span></summary>
    <div className="song-cleanup-review">
      <div className="song-cleanup-toolbar">
        <button type="button" className="song-cleanup-run" disabled={!ready||busy||analyzing}
          onClick={onAnalyze}>{analyzing?"Analyzing…":scanned?"Re-analyze mix":"Analyze mix"}</button>
        {scanned&&<small>{warningCount} warnings · {findings.length} findings</small>}
      </div>
      {error&&<p role="alert" className="song-cleanup-error">{error}</p>}
      {scanned&&<>
        {stale&&<small role="status" className="song-cleanup-stale">Previous scan · mix changed. Re-analyze to refresh.</small>}
        <label className="song-cleanup-filter">Findings
          <select aria-label="Filter sound cleanup findings" value={filter} onChange={e=>setFilter(e.target.value)}>
            {FILTERS.filter(item=>item==="All"||categories.has(item)).map(item=><option key={item}>{item}</option>)}
          </select>
        </label>
        <label className="song-cleanup-toggle">
          <input type="checkbox" checked={showReviewed} onChange={e=>setShowReviewed(e.target.checked)}/> Show reviewed ({reviewed.size})
        </label>
        {findings.length===0?<p className="song-cleanup-empty">No candidates at current thresholds. This does not guarantee the audio is artifact-free.</p>:
          visible.length===0?<p className="song-cleanup-empty">No unreviewed candidates in this category.</p>:
          <div className="song-cleanup-list" role="list" aria-label="Sound cleanup findings">
            {visible.map(item=>{
              const id=keyOf(item),isReviewed=reviewed.has(id);
              return <article key={id} role="listitem" className={"song-cleanup-item"+(isReviewed?" is-reviewed":"")}>
                <div className="song-cleanup-item-top">
                  <button type="button" className="song-cleanup-time" title="Seek to finding"
                    onClick={()=>onSeek(item.timeSeconds)}>{stamp(item.timeSeconds)}</button>
                  <div className="song-cleanup-item-title">
                    <strong>{item.label}</strong>
                    <small>{FINDING_GROUPS[item.kind as AudioFindingKind]} · {item.severity==="warning"?"Warning":"Review"}</small>
                  </div>
                </div>
                <details className="song-finding-detail"><summary>Details</summary>
                  {item.spectrum&&<svg role="img" aria-label="Three-second time-frequency energy view, bass at bottom and treble at top"
                    viewBox="0 0 240 96" preserveAspectRatio="none" style={{width:"100%",height:"84px",background:"#101a25",borderRadius:"5px"}}>
                    {item.spectrum.levels.map((intensity,index)=>{
                      const x=Math.floor(index/item.spectrum!.rows),y=index%item.spectrum!.rows;
                      return <rect key={index} x={x*10} y={(item.spectrum!.rows-y-1)*8} width="10" height="8"
                        fill="#74c7cc" opacity={Math.max(.05,intensity)}/>;
                    })}
                    <line x1={Math.max(0,Math.min(240,240*(item.timeSeconds-item.spectrum.startSeconds)/item.spectrum.seconds))}
                      x2={Math.max(0,Math.min(240,240*(item.timeSeconds-item.spectrum.startSeconds)/item.spectrum.seconds))}
                      y1="0" y2="96" stroke="#ffb967" strokeWidth="1.5"/>
                  </svg>}
                  <p>{item.detail}</p>{item.suggestion&&<p>{item.suggestion}</p>}
                </details>
                {!!item.attribution?.length&&<details className="song-cleanup-attribution">
                  <summary>{item.attribution[0].name} · spectral evidence{item.attributionUncertain?" (uncertain)":""}</summary>
                  <div>{item.attribution.map(e=><div key={e.name}>
                    {e.name} · {(e.relativeShare*100).toFixed(0)}% of sampled source-band energy ({e.band})
                  </div>)}</div>
                </details>}
                {!item.attribution?.length&&!!item.sources?.length&&<p className="song-cleanup-sources">Likely: {item.sources.join(", ")}</p>}
                <div className="song-cleanup-actions">
                  {item.kind==="harshness"&&<small title="Targeted band-specific EQ repair is not implemented yet. Inspect the suspect stem and listen before changing the mix.">Diagnostic only</small>}

                  <button type="button" onClick={()=>onLoop(Math.max(0,item.timeSeconds-1),item.timeSeconds+Math.max(2,item.durationSeconds||0)+1)}>Loop ± context</button>
                  {item.kind==="transient"&&<button type="button" onClick={()=>onTryDeclick(item)}>Try de-click</button>}
                  {(["headroom","pumping","sibilance"].includes(item.kind))&&
                    <button type="button" onClick={()=>onTryCorrection(item)}>Try Fix</button>}
                  {comparison?.findings.includes(item)&&<button type="button"
                    aria-pressed={markedIntentional.has(id)}
                    onClick={()=>{setMarkedIntentional(current=>{const next=new Set(current);if(next.has(id))next.delete(id);else next.add(id);return next;});
                      setReviewed(current=>new Set(current).add(id));}}>
                    {markedIntentional.has(id)?"Intentional ✓":"Mark intentional"}
                  </button>}
                  <button type="button" onClick={()=>setReviewed(existing=>{
                    const next=new Set(existing);if(next.has(id))next.delete(id);else next.add(id);return next;
                  })}>{isReviewed?"Unmark":"Mark reviewed"}</button>
                </div>
              </article>;
            })}
          </div>}
        {nextItem&&<button type="button" className="song-cleanup-next"
          onClick={()=>onSeek(nextItem.timeSeconds)}>Jump to first unreviewed finding</button>}
      </>}
    </div>
  </details>;
}
