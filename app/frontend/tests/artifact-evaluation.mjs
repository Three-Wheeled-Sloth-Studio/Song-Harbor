/**
 * Artifact detection evaluation only. No generator identity, watermark, or repair scoring.
 * Truth is time-localized annotated acoustic events, not "AI music".
 */

/** Match observations to truth events one-to-one at bounded timing tolerance.
 * Greedy minimum-error match avoids counting duplicate hits as multiple recalls.
 * @param {{timeSeconds:number}[]} observations
 * @param {{timeSeconds:number}[]} truth
 * @param {number} toleranceSeconds
 */
export function matchEvents(observations,truth,toleranceSeconds=.05){
  if(!Number.isFinite(toleranceSeconds)||toleranceSeconds<0)throw new RangeError("Invalid time tolerance");
  // Maximum-cardinality matching: nearest-first greedy alone can lose a valid
  // match when one observation can explain either of two nearby truth events.
  const candidates=observations.map((o,i)=>{
    if(!Number.isFinite(o.timeSeconds))throw new TypeError("Invalid observation timestamp");
    return truth.map((t,j)=>{
      if(!Number.isFinite(t.timeSeconds))throw new TypeError("Invalid truth timestamp");
      return {i,j,error:Math.abs(o.timeSeconds-t.timeSeconds)};
    }).filter(pair=>pair.error<=toleranceSeconds)
      .sort((a,b)=>a.error-b.error||a.j-b.j);
  });
  const matchForTruth=new Array(truth.length).fill(-1);
  function assign(observation,visited){
    for(const pair of candidates[observation]){
      if(visited.has(pair.j))continue;
      visited.add(pair.j);
      const prior=matchForTruth[pair.j];
      if(prior===-1||assign(prior,visited)){
        matchForTruth[pair.j]=observation;
        return true;
      }
    }
    return false;
  }
  const order=candidates.map((_,i)=>i)
    .sort((a,b)=>candidates[a].length-candidates[b].length||a-b);
  for(const i of order)assign(i,new Set());
  const errors=[];
  matchForTruth.forEach((i,j)=>{
    if(i>=0)errors.push(Math.abs(observations[i].timeSeconds-truth[j].timeSeconds));
  });
  const tp=errors.length,fp=observations.length-tp,fn=truth.length-tp;
  return {tp,fp,fn,localizationErrorsSeconds:errors};
}

/** @param {{id:string;category:string;expectedEvents:{timeSeconds:number}[];observations:{timeSeconds:number}[]}[]} evaluated */
export function summarizeArtifactCases(evaluated,toleranceSeconds=.05){
  const categories={};
  let tp=0,fp=0,fn=0,negativeCases=0,negativeCasesWithFalsePositives=0;
  const cases=evaluated.map(item=>{
    const score=matchEvents(item.observations,item.expectedEvents,toleranceSeconds);
    const negative=item.expectedEvents.length===0;
    if(negative){negativeCases++;if(score.fp)negativeCasesWithFalsePositives++;}
    const group=categories[item.category]??={cases:0,tp:0,fp:0,fn:0,negativeCases:0,negativeCasesWithFalsePositives:0};
    group.cases++;group.tp+=score.tp;group.fp+=score.fp;group.fn+=score.fn;
    if(negative){group.negativeCases++;if(score.fp)group.negativeCasesWithFalsePositives++;}
    tp+=score.tp;fp+=score.fp;fn+=score.fn;
    return {id:item.id,category:item.category,negative,...score};
  });
  const ratio=(a,b)=>b? a/b:null;
  return {
    schemaVersion:1,kind:"audible-artifact-evaluation",toleranceSeconds,
    totals:{cases:cases.length,tp,fp,fn,precision:ratio(tp,tp+fp),
      recall:ratio(tp,tp+fn),f1:tp+fp&&tp+fn?2*tp/(2*tp+fp+fn):null,
      negativeCases,negativeCasesWithFalsePositives,
      negativeCaseFalsePositiveRate:ratio(negativeCasesWithFalsePositives,negativeCases)},
    categories,cases
  };
}
