import type {DeclickRecipe} from "./SharedClockAudition.ts";
export type DeclickDraft={recipe:DeclickRecipe;compare:"original"|"current"|"fix"};
export function DeclickWorkbench({draft,sources,locked,onChange,onAccept,onCancel}:{
  draft:DeclickDraft;sources:readonly {key:string;filename:string;startSeconds:number}[];
  locked:boolean;onChange:(draft:DeclickDraft)=>void;onAccept:()=>void;onCancel:()=>void;
}){
  const chosen=sources.find(item=>item.key===draft.recipe.source_key);
  const change=(value:Partial<DeclickRecipe>)=>onChange({...draft,compare:"fix",recipe:{...draft.recipe,...value}});
  return <section className="song-correction-workbench song-declick-trial" aria-label="Localized de-click audition">
    <div className="song-correction-heading"><strong>De-click · {draft.recipe.time_seconds.toFixed(2)}s</strong></div>
    <div className="song-correction-toolbar">
      <div className="song-correction-switch" role="group" aria-label="De-click comparison">
        {(["original","current","fix"] as const).map(mode=><button key={mode}
          aria-pressed={draft.compare===mode} type="button" onClick={()=>onChange({...draft,compare:mode})}>
          {mode.charAt(0).toUpperCase()+mode.slice(1)}
        </button>)}
      </div>
      <div className="song-correction-primary-actions">
        <button type="button" disabled={locked||draft.compare!=="fix"||!chosen} onClick={onAccept}>Accept</button>
        <button type="button" onClick={onCancel}>Discard</button>
      </div>
    </div>
    <div className="song-correction-selects">
      <label>Source <select aria-label="De-click source lane" value={draft.recipe.source_key}
          onChange={e=>{const source=sources.find(s=>s.key===e.target.value);if(source)change({source_key:source.key,filename:source.filename});}}>
        {sources.map(item=><option key={item.key} value={item.key}>{item.key.split("/").at(-1)}</option>)}
      </select></label>
      <label>Half-window <select value={draft.recipe.half_window_ms} onChange={e=>change({half_window_ms:Number(e.target.value)})}>
        <option value={.5}>0.5 ms</option><option value={1}>1.0 ms</option>
        <option value={2}>2.0 ms</option><option value={3}>3.0 ms</option>
      </select></label>
      <span className="song-cleanup-stale" title="Transient detector may also flag intentional drum hits. Listen before accepting.">Manual verification required</span>
    </div>
  </section>;
}
