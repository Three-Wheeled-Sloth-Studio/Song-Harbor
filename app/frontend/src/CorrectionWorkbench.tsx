import type {AudioFinding} from "./AudioCleanupAnalyzer";
export type CorrectionDraft={
  finding:AudioFinding;
  sectionId:string;
  file:string;
  kind:"comp"|"duck"|"deess"|"trim";
  frequency:number;
  q:number;
  maxReduction:number;
  auditionBoost:number;
  threshold:number;
  ratio:number;
  depth:number;
  trimDelta:number;
  transition:number;
  proposed:boolean;
  compare:"original"|"current"|"fix";
};
export function CorrectionWorkbench({draft,files,trimBase,busy,reduction,onChange,onAccept,onCancel}:{
  draft:CorrectionDraft;
  files:string[];
  trimBase:number;
  busy:boolean;
  reduction?:{compressionDb:number;duckDb:number;deessDb:number};
  onChange:(next:CorrectionDraft)=>void;
  onAccept:()=>void;
  onCancel:()=>void;
}){
  const edit=(patch:Partial<CorrectionDraft>)=>onChange({...draft,...patch});
  const reductionItems=[["Compression",reduction?.compressionDb||0],["Ducking",reduction?.duckDb||0],["De-esser",reduction?.deessDb||0]] as const;
  return <section className="song-correction-workbench" aria-label="Correction trial">
    <div className="song-correction-heading">
      <strong>Correction trial · {draft.finding.label}</strong>
      <button type="button" onClick={onCancel} title="Discard trial" aria-label="Close correction trial">×</button>
    </div>
    <div className="song-correction-switch" role="group" aria-label="Correction comparison">
      <button type="button" aria-pressed={draft.compare==="original"} onClick={()=>edit({compare:"original",proposed:false})}>Original</button>
      <button type="button" aria-pressed={draft.compare==="current"} onClick={()=>edit({compare:"current",proposed:false})}>Current</button>
      <button type="button" aria-pressed={draft.compare==="fix"} onClick={()=>edit({compare:"fix",proposed:true})}>Fix</button>
    </div>
    {draft.kind!=="trim"&&<>
      <div className="song-dynamics-meter" aria-label="Live dynamics gain reduction">
        {reductionItems.map(([name,value])=><div key={name} className="song-dynamics-meter-row">
          <span>{name}</span><meter min={0} max={12} value={Math.min(12,value)}/><output>{value.toFixed(1)} dB</output>
        </div>)}
      </div>
      <label className="song-audition-strength">Audition strength
        <select value={draft.auditionBoost} onChange={e=>edit({auditionBoost:Number(e.target.value),proposed:true,compare:"fix"})}>
          <option value={1}>Actual setting · 1×</option><option value={3}>Exaggerated audition · 3×</option>
        </select>
      </label>
      <label>Effect<select value={draft.kind} onChange={e=>edit({kind:e.target.value as "comp"|"duck"|"deess"})}>
        <option value="comp">Compression</option>
        <option value="duck">Vocal-keyed ducking</option>
        <option value="deess">Targeted de-esser</option>
      </select></label>
      <label>Track<select value={draft.file} onChange={e=>edit({file:e.target.value})}>
        {files.filter(f=>draft.kind!=="duck"||!f.includes("(Vocals)")).map(f=>
          <option key={f} value={f}>{f.match(/\(([^)]+)\)/)?.[1]||f}</option>)}
      </select></label>
      {draft.kind==="deess"?<>
        <label>Frequency <strong>{draft.frequency} Hz</strong><input type="range" min="3000" max="11000" step="100" value={draft.frequency}
          onChange={e=>edit({frequency:Number(e.target.value),proposed:true})}/></label>
        <label>Bandwidth / Q <strong>{draft.q.toFixed(1)}</strong><input type="range" min=".4" max="8" step=".1" value={draft.q}
          onChange={e=>edit({q:Number(e.target.value),proposed:true})}/></label>
        <label>Threshold <strong>{draft.threshold} dBFS</strong><input type="range" min="-70" max="-10" step="1" value={draft.threshold}
          onChange={e=>edit({threshold:Number(e.target.value),proposed:true})}/></label>
        <label>Maximum reduction <strong>{draft.maxReduction} dB</strong><input type="range" min="0" max="12" step=".5" value={draft.maxReduction}
          onChange={e=>edit({maxReduction:Number(e.target.value),proposed:true})}/></label>
      </>:draft.kind==="comp"?<>
        <label>Threshold <strong>{draft.threshold} dBFS</strong>
          <input type="range" min="-40" max="-6" step="1" value={draft.threshold}
            onChange={e=>edit({threshold:Number(e.target.value),proposed:true})}/></label>
        <label>Ratio <strong>{draft.ratio.toFixed(1)}:1</strong>
          <input type="range" min="1" max="4" step=".1" value={draft.ratio}
            onChange={e=>edit({ratio:Number(e.target.value),proposed:true})}/></label>
      </>:<label>Vocal-keyed reduction <strong>{draft.depth} dB</strong>
        <input type="range" min="0" max="12" step=".5" value={draft.depth}
          onChange={e=>edit({depth:Number(e.target.value),proposed:true})}/></label>}
      <label>Transition <strong>{draft.transition.toFixed(1)} s</strong>
        <input type="range" min=".5" max="5" step=".5" value={draft.transition}
          onChange={e=>edit({transition:Number(e.target.value),proposed:true})}/></label>
    </>}
    {draft.kind==="trim"&&<label>Output trim <strong>{(trimBase+draft.trimDelta).toFixed(1)} dB</strong>
      <input type="range" min="-12" max="0" step=".1" value={draft.trimDelta}
        onChange={e=>edit({trimDelta:Number(e.target.value),proposed:true})}/></label>}
    <div className="song-correction-actions">
      <button type="button" disabled={busy||!draft.proposed} onClick={onAccept}>{busy?"Saving…":"Accept correction"}</button>
      <button type="button" onClick={onCancel}>Discard</button>
    </div>
    {draft.kind==="trim"&&<small>Output trim is session-only until project persistence is implemented.</small>}
  </section>;
}
