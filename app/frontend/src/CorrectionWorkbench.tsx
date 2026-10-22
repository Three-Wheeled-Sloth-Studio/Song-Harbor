import type {AudioFinding} from "./AudioCleanupAnalyzer";
export type CorrectionDraft={
  finding:AudioFinding;
  sectionId:string;
  file:string;
  kind:"comp"|"duck"|"trim";
  threshold:number;
  ratio:number;
  depth:number;
  trimDelta:number;
  transition:number;
  proposed:boolean;
};
export function CorrectionWorkbench({draft,files,trimBase,busy,onChange,onAccept,onCancel}:{
  draft:CorrectionDraft;
  files:string[];
  trimBase:number;
  busy:boolean;
  onChange:(next:CorrectionDraft)=>void;
  onAccept:()=>void;
  onCancel:()=>void;
}){
  const edit=(patch:Partial<CorrectionDraft>)=>onChange({...draft,...patch});
  return <section className="song-correction-workbench" aria-label="Correction trial">
    <div className="song-correction-heading">
      <strong>Correction trial · {draft.finding.label}</strong>
      <button type="button" onClick={onCancel} title="Discard trial" aria-label="Close correction trial">×</button>
    </div>
    <small>Loop audition compares saved mix (A) to an unsaved proposed change (B).
      Only Accept writes a production directive. No source WAV is modified. Mix export is unavailable during an unsaved trial.</small>
    <div className="song-correction-switch" role="group" aria-label="Correction comparison">
      <button type="button" aria-pressed={!draft.proposed} onClick={()=>edit({proposed:false})}>A · Saved</button>
      <button type="button" aria-pressed={draft.proposed} onClick={()=>edit({proposed:true})}>B · Proposed</button>
    </div>
    {draft.kind!=="trim"&&<>
      <label>Effect<select value={draft.kind} onChange={e=>edit({kind:e.target.value as "comp"|"duck"})}>
        <option value="comp">Compression</option>
        <option value="duck">Vocal-keyed ducking</option>
      </select></label>
      <label>Track<select value={draft.file} onChange={e=>edit({file:e.target.value})}>
        {files.filter(f=>draft.kind!=="duck"||!f.includes("(Vocals)")).map(f=>
          <option key={f} value={f}>{f.match(/\(([^)]+)\)/)?.[1]||f}</option>)}
      </select></label>
      {draft.kind==="comp"?<>
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
    {draft.kind==="trim"&&<small>Master output trim is currently session-only.
      Accept changes the active mix/export setting but cannot persist it across restarts.</small>}
  </section>;
}
