import {useMemo,useState} from "react";
import type {AudioFinding,AudioFindingKind} from "./AudioCleanupAnalyzer";

/** Experimental view of existing, CPU-only offline QC evidence.
 * Not a trained AI music detector, watermark scanner, or "human" rating.
 * Intentional artistic effects may trigger any of these screens.
 */
const DOMAINS=[
  {id:"spectral",label:"Spectral texture",kinds:["sibilance","harshness","fizz","noise","signal_audit"]},
  {id:"timing",label:"Attacks & dynamics",kinds:["transient","pumping"]},
  {id:"spatial",label:"Stereo compatibility",kinds:["phase"]},
  {id:"levels",label:"Peak integrity",kinds:["headroom","clip_shape"]}
] as const;
const stamp=(seconds:number)=>{
  const time=Math.max(0,Math.floor(seconds));
  return `${String(Math.floor(time/60)).padStart(2,"0")}:${String(time%60).padStart(2,"0")}`;
};

export function ForensicsReview({
  findings,scanned,analyzing,error,ready,busy,onAnalyze,onSeek,onLoop
}:{
  findings:readonly AudioFinding[];scanned:boolean;analyzing:boolean;error:string;
  ready:boolean;busy:boolean;onAnalyze:()=>void;
  onSeek:(seconds:number)=>void;onLoop:(start:number,end:number)=>void;
}){
  const [domain,setDomain]=useState("all");
  const counts=useMemo(()=>DOMAINS.map(item=>({
    ...item, count:findings.filter(f=>item.kinds.some(k=>(k as AudioFindingKind)===f.kind)).length
  })),[findings]);
  const visible=useMemo(()=>findings.filter(item=>domain==="all"||
    DOMAINS.find(group=>group.id===domain)?.kinds.some(k=>(k as AudioFindingKind)===item.kind)),
    [findings,domain]);
  const warnings=visible.filter(f=>f.severity==="warning").length;
  return <section className="song-forensics" aria-label="Experimental audio forensics">
    <p className="song-forensics-intro">Inspect the current effects-processed mix for
      audible quality risks and persistent spectral features. This reuses Song Harbor's
      local signal audit and runs only when requested. It does not change any audio.</p>
    <div className="song-forensics-controls">
      <button type="button" disabled={!ready||busy||analyzing} onClick={onAnalyze}>
        {analyzing?"Scanning mix…":scanned?"Rescan current mix":"Scan current mix"}
      </button>
      <span>{scanned?`${findings.length} listening candidates`:"Not scanned"}</span>
    </div>
    {error&&<p role="alert" className="song-cleanup-error">{error}</p>}
    <div className="song-forensics-status" aria-label="Forensics scan domains">
      {counts.map(group=><button key={group.id} type="button"
        className={domain===group.id?"is-selected":""}
        aria-pressed={domain===group.id} onClick={()=>setDomain(current=>current===group.id?"all":group.id)}>
        <strong>{group.label}</strong><span>{scanned?group.count:"—"}</span>
      </button>)}
    </div>
    {scanned&&<div className="song-forensics-results">
      <div className="song-forensics-result-heading">
        <strong>{domain==="all"?"All flagged regions":DOMAINS.find(g=>g.id===domain)?.label}</strong>
        <small>{warnings} warnings · {visible.length} candidates</small>
      </div>
      {visible.length===0?<p className="song-cleanup-empty">No observations met the current
        thresholds in this category. This does not verify the absence of defects or fingerprints.</p>:
        <div role="list" className="song-forensics-list">
          {visible.map((finding,index)=><article role="listitem" key={finding.kind+":"+finding.timeSeconds+":"+index}>
            <div className="song-forensics-result-heading"><strong>{finding.label}</strong>
              <button type="button" onClick={()=>onSeek(finding.timeSeconds)}>
                {stamp(finding.timeSeconds)} · Seek</button></div>
            <p>{finding.detail}</p>
            {finding.suggestion&&<small>{finding.suggestion}</small>}
            <div className="song-forensics-actions">
              <button type="button" onClick={()=>onLoop(Math.max(0,finding.timeSeconds-1),
                finding.timeSeconds+Math.max(2,finding.durationSeconds||0)+1)}>Audition region</button>
            </div>
          </article>)}
        </div>}
    </div>}
    <p className="song-forensics-caveat">
      <strong>Experimental scope:</strong> signal-level screening only. No pretrained
      generator classifier, provenance watermark verification or automated fingerprint
      removal is active. Persistent tones may be normal instruments. Results cannot
      establish whether audio is AI-generated or whether a fix will sound better.
      Source-to-output delta comparison is planned for a later iteration.
    </p>
  </section>;
}
