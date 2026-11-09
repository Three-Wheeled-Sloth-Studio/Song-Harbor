import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SectionInsight} from "./SectionInsights";
import {inspectNarrativeShifts,sectionMatchTrim} from "./NarrativeDynamics";

const fmt=(value:number)=> (value>=0?"+":"")+value.toFixed(1)+" dB";
const title=(s:SongSection)=>s.kind+(s.number===null?"":" "+s.number)+" ("+s.start_seconds.toFixed(1)+"s)";
export function NarrativeDynamicsPanel({sections,insights,scanned,stale,analyzing,ready,onAnalyze,onAudition}:
 {sections:readonly SongSection[];insights:readonly SectionInsight[];scanned:boolean;stale:boolean;
  analyzing:boolean;ready:boolean;onAnalyze:()=>void;onAudition:(start:number,end:number)=>void}){
  const byId=new Map(insights.map(i=>[i.sectionId,i]));
  const named=new Map(sections.map(s=>[s.id,s]));
  const [showAll,setShowAll]=useState(false);
  const rows=(!stale&&scanned)?inspectNarrativeShifts(sections.flatMap(s=>{const i=byId.get(s.id);return i?[i]:[]}))
    .filter(row=>showAll||row.tags.length>0):[];
  return <div className="timeline-loop-controls" aria-label="Narrative dynamics analysis">
    <p>Observations about how the rendered mix changes between sections, not judgments about creative intent.</p>
    <div className="production-tool-actions">
      <button type="button" disabled={!ready||analyzing} onClick={onAnalyze}>
        {analyzing?"Analyzing mix...":scanned?"Re-analyze mix":"Analyze mix"}
      </button>
      <label><input type="checkbox" checked={showAll} onChange={e=>setShowAll(e.target.checked)}/> Show small changes</label>
    </div>
    {stale&&<p role="status">Mix changed. Re-analyze to refresh these measurements.</p>}
    {!scanned&&!stale&&<p>Run Analyze mix to populate section transitions.</p>}
    {scanned&&!stale&&<div>
      {rows.length===0?<p>No measured transitions exceed the default thresholds.</p>:rows.map(row=>{
        const first=named.get(row.fromId),second=named.get(row.toId);
        if(!first||!second)return null;
        return <div key={row.fromId+":"+row.toId} className="song-dynamics-meter-row" style={{display:"block",padding:"8px 0"}}>
          <strong>{title(first)} to {title(second)}</strong>
          <div>RMS {fmt(row.rmsDeltaDb)} | Peak {fmt(row.peakDeltaDb)}</div>
          <div>Stereo width {fmt(row.widthDeltaDb)} | L/R shift {fmt(row.balanceDeltaDb)}</div>
          <small>{row.description}</small>
          <div><button type="button" onClick={()=>onAudition(Math.max(first.start_seconds,first.end_seconds-2),Math.min(second.end_seconds,second.start_seconds+2))}>Listen across transition</button></div>
        </div>;
      })}
    </div>}
    <small>RMS is signal level, not LUFS. Width is the side/mid ratio in dB. Changes are descriptive and may be intentional.</small>
  </div>;
}

export function SectionComparisonPanel({sections,insights,scanned,stale,ready,playing,onAnalyze,onAudition,onTrim}:
 {sections:readonly SongSection[];insights:readonly SectionInsight[];scanned:boolean;stale:boolean;
  ready:boolean;playing:boolean;onAnalyze:()=>void;onAudition:(start:number,end:number)=>void;onTrim:(db:number)=>void}){
  const [a,setA]=useState(sections[0]?.id||"");
  const [b,setB]=useState(sections[1]?.id||"");
  const [match,setMatch]=useState(true);
  const [current,setCurrent]=useState<"A"|"B"|null>(null);
  useEffect(()=>{return ()=>onTrim(0);},[onTrim]);
  const first=sections.find(s=>s.id===a),second=sections.find(s=>s.id===b);
  const byId=new Map(insights.map(x=>[x.sectionId,x]));
  const valid=scanned&&!stale&&first&&second&&first.id!==second.id&&byId.has(a)&&byId.has(b);
  const comparison=valid?sectionMatchTrim(byId.get(a)!,byId.get(b)!):null;
  function audition(which:"A"|"B"){
    const target=which==="A"?first:second;
    if(!target)return;
    const trim=which==="B"&&match&&comparison?comparison.suggestedCandidateTrimDb:0;
    onTrim(trim);
    setCurrent(which);
    onAudition(target.start_seconds,target.end_seconds);
  }
  return <div className="timeline-loop-controls" aria-label="Section-to-section comparison">
    <p>Compare two sections using the existing transport. Preview gain never changes the saved mix or WAV export.</p>
    <label>Section A
      <select value={a} onChange={e=>{setA(e.target.value);setCurrent(null);onTrim(0);}}>
        {sections.map(s=><option key={s.id} value={s.id}>{title(s)}</option>)}
      </select>
    </label>
    <label>Section B
      <select value={b} onChange={e=>{setB(e.target.value);setCurrent(null);onTrim(0);}}>
        {sections.map(s=><option key={s.id} value={s.id}>{title(s)}</option>)}
      </select>
    </label>
    <label><input type="checkbox" checked={match} onChange={e=>{setMatch(e.target.checked);setCurrent(null);onTrim(0);}}/> RMS level-match B to A</label>
    {!valid&&<p role="status">{stale?"Analysis is stale. Re-analyze after mix changes.":"Analyze mix for level matching (you can audition without matching)."}</p>}
    <div className="production-tool-actions">
      <button type="button" disabled={!ready||!first||!second||a===b} onClick={()=>audition("A")}>Play A</button>
      <button type="button" disabled={!ready||!first||!second||a===b} onClick={()=>audition("B")}>Play B</button>
      <button type="button" disabled={!ready} onClick={onAnalyze}>Analyze mix</button>
    </div>
    {comparison&&<p>B minus A: {fmt(comparison.differenceDb)} RMS. {match?
      "Preview-only B trim: "+fmt(comparison.suggestedCandidateTrimDb)+". "+comparison.reason:
      "Level matching disabled."}</p>}
    {current&&<small>Selected {current}{playing?" (playing)":" (paused or ready)"}. Playback loops the selected section until stopped or changed. To preserve section contrast, disable matching.</small>}
    <small>RMS matching is not perceptual LUFS matching. Gain is capped at +/-12 dB and bounded by measured sample headroom. Matching can be incomplete.</small>
  </div>;
}
