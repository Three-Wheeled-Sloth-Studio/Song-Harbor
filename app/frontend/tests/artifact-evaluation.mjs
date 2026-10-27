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
  const pairs=[];
  observations.forEach((o,i)=>{
    if(!Number.isFinite(o.timeSeconds))throw new TypeError("Invalid observation timestamp");
    truth.forEach((t,j)=>{
      if(!Number.isFinite(t.timeSeconds))throw new TypeError("Invalid truth timestamp");
      const error=Math.abs(o.timeSeconds-t.timeSeconds);
      if(error<=toleranceSeconds)pairs.push({i,j,error});
    });
  });
  pairs.sort((a,b)=>a.error-b.error||a.i-b.i||a.j-b.j);
  const usedObs=new Set(),usedTruth=new Set(),errors=[];
  for(const pair of pairs){
    if(usedObs.has(pair.i)||usedTruth.has(pair.j))continue;
    usedObs.add(pair.i);usedTruth.add(pair.j);errors.push(pair.error);
  }
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
