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
  const edit=(patch:Partial<CorrectionDraft>)=>onChange({...draft,...patch,...(patch.proposed===true?{compare:"fix" as const}:{})});
  const reductionItems=[["Compression",reduction?.compressionDb||0],["Ducking",reduction?.duckDb||0],["De-esser",reduction?.deessDb||0]] as const;
  return <section className="song-correction-workbench" aria-label="Correction trial">
    <div className="song-correction-heading">
      <strong>Correction trial · {draft.finding.label}</strong>
      <button type="button" onClick={onCancel} title="Discard trial" aria-label="Close correction trial">×</button>
    </div>
    <div className="song-correction-toolbar">
      <div className="song-correction-switch" role="group" aria-label="Correction comparison">
        <button type="button" aria-pressed={draft.compare==="original"} onClick={()=>edit({compare:"original",proposed:false})}>Original</button>
        <button type="button" aria-pressed={draft.compare==="current"} onClick={()=>edit({compare:"current",proposed:false})}>Current</button>
        <button type="button" aria-pressed={draft.compare==="fix"} onClick={()=>edit({compare:"fix",proposed:true})}>Fix</button>
      </div>
      <div className="song-correction-primary-actions">
        <button type="button" disabled={busy||!draft.proposed} onClick={onAccept}>{busy?"Saving…":"Accept"}</button>
        <button type="button" onClick={onCancel}>Discard</button>
      </div>
    </div>
    {draft.kind!=="trim"&&<>
      <details className="song-correction-meter-detail"><summary>Live reduction</summary>      <div className="song-dynamics-meter" aria-label="Live dynamics gain reduction">
        {reductionItems.map(([name,value])=><div key={name} className="song-dynamics-meter-row">
          <span>{name}</span><meter min={0} max={12} value={Math.min(12,value)}/><output>{value.toFixed(1)} dB</output>
        </div>)}
      </div>
</details>
      <div className="song-correction-selects">
        <label>Strength <select value={draft.auditionBoost} onChange={e=>edit({auditionBoost:Number(e.target.value),proposed:true})}>
          <option value={1}>1×</option><option value={3}>3× preview</option>
        </select></label>
        <label>Effect <select value={draft.kind} onChange={e=>edit({kind:e.target.value as "comp"|"duck"|"deess",proposed:true})}>
          <option value="comp">Compression</option><option value="duck">Ducking</option><option value="deess">De-esser</option>
        </select></label>
        <label>Track <select value={draft.file} onChange={e=>edit({file:e.target.value,proposed:true})}>
          {files.filter(f=>draft.kind!=="duck"||!f.includes("(Vocals)")).map(f=>
            <option key={f} value={f}>{f.match(/\(([^)]+)\)/)?.[1]||f}</option>)}
        </select></label>
      </div>
      <div className="song-correction-knobs">
        {draft.kind==="deess"?<>
          <Knob label="Frequency" value={draft.frequency} min={3000} max={11000} step={100} suffix="Hz" onChange={value=>edit({frequency:value,proposed:true})}/>
          <Knob label="Q" value={draft.q} min={.4} max={8} step={.1} onChange={value=>edit({q:value,proposed:true})}/>
          <Knob label="Threshold" value={draft.threshold} min={-70} max={-10} step={1} suffix="dB" onChange={value=>edit({threshold:value,proposed:true})}/>
          <Knob label="Reduction" value={draft.maxReduction} min={0} max={12} step={.5} suffix="dB" onChange={value=>edit({maxReduction:value,proposed:true})}/>
        </>:draft.kind==="comp"?<>
          <Knob label="Threshold" value={draft.threshold} min={-40} max={-6} step={1} suffix="dB" onChange={value=>edit({threshold:value,proposed:true})}/>
          <Knob label="Ratio" value={draft.ratio} min={1} max={4} step={.1} suffix=":1" onChange={value=>edit({ratio:value,proposed:true})}/>
        </>:<Knob label="Reduction" value={draft.depth} min={0} max={12} step={.5} suffix="dB" onChange={value=>edit({depth:value,proposed:true})}/>}
        <Knob label="Transition" value={draft.transition} min={.5} max={5} step={.5} suffix="s" onChange={value=>edit({transition:value,proposed:true})}/>
      </div>
    </>}
    {draft.kind==="trim"&&<div className="song-correction-knobs">
      <Knob label="Output trim" value={draft.trimDelta} min={-12} max={0} step={.1} suffix="dB" onChange={value=>edit({trimDelta:value,proposed:true})}/>
      <small>Applied trim: {(trimBase+draft.trimDelta).toFixed(1)} dB</small>
    </div>}
    {draft.kind==="trim"&&<small>Output trim is session-only until project persistence is implemented.</small>}
  </section>;
}

/** Accessible compact dial; horizontal dragging and arrow keys change value. */
function Knob({label,value,min,max,step,suffix="",onChange}:{
  label:string;value:number;min:number;max:number;step:number;suffix?:string;
  onChange:(value:number)=>void;
}){
  const fraction=Math.max(0,Math.min(1,(value-min)/(max-min)));
  const angle=-135+fraction*270;
  return <label className="song-correction-knob">
    <span>{label}</span>
    <span className="song-correction-knob-face" style={{background:`conic-gradient(from 225deg,#74c7cc 0deg ${fraction*270}deg,#34424a ${fraction*270}deg 270deg,transparent 270deg)`}}>
      <span className="song-correction-knob-indicator" style={{transform:`rotate(${angle}deg)`}}/>
      <input type="range" min={min} max={max} step={step} value={value} aria-label={label}
        onChange={e=>onChange(Number(e.target.value))}/>
    </span>
    <output>{Number.isInteger(value)?value:value.toFixed(1)}{suffix}</output>
  </label>;
}
