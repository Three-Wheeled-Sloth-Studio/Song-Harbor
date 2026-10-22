/** Deterministic, bounded source-energy approximation for automatic stereo balancing.
 * Estimates dry stem contributions, not the effects-processed final bounce.
 * User-authored pan positions are immutable; optimization acts on free sources only.
 */
export type AutoStem={
  filename:string;leftPower:number;rightPower:number;crossPower:number;
  pan:number;gain:number;locked:boolean
};
export type AutoPanAdjustment={filename:string;pan:number;gainDb:number};
export type AutoPanResult={
  beforeDb:number;predictedDb:number;adjustments:AutoPanAdjustment[];
  reached:boolean;reason:string;
};
const clamp=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
const balance=(stems:AutoStem[],pans:Map<string,number>,gains:Map<string,number>)=>{
  let left=0,right=0;
  for(const s of stems){
    const pan=pans.get(s.filename)??s.pan;
    const db=gains.get(s.filename)??0;
    const g2=Math.pow(s.gain*10**(db/20),2);
    const theta=Math.PI*.5*Math.abs(pan);
    const c=Math.cos(theta),t=Math.sin(theta);
    // WebAudio StereoPanner's stereo downmix approximation, including L/R covariance.
    if(pan>=0){
      left+=g2*c*c*s.leftPower;
      right+=g2*(s.rightPower+t*t*s.leftPower+2*t*s.crossPower);
    }else{
      left+=g2*(s.leftPower+t*t*s.rightPower+2*t*s.crossPower);
      right+=g2*c*c*s.rightPower;
    }
  }
  return 10*Math.log10(Math.max(1e-12,left)/Math.max(1e-12,right));
};
export function solveAutoPan(stems:AutoStem[],maxPanMove=.24,maxGainDb=.35):AutoPanResult{
  const active=stems.filter(s=>s.gain>0&&(s.leftPower+s.rightPower)>1e-10);
  const pans=new Map(active.map(s=>[s.filename,s.pan]));
  const gains=new Map(active.map(s=>[s.filename,0]));
  const beforeDb=balance(active,pans,gains);
  const free=active.filter(s=>!s.locked);
  if(!free.length)return {beforeDb,predictedDb:beforeDb,adjustments:[],
    reached:Math.abs(beforeDb)<=.25,reason:"No eligible stems: inherited explicit pans are protected"};
  // Penalize movement more than remaining imbalance. Cap the perceptual footprint.
  const score=()=> {
    const error=balance(active,pans,gains);
    let movement=0;
    for(const s of free){
      movement+=1.8*((pans.get(s.filename)!-s.pan)/maxPanMove)**2;
      movement+=2.8*((gains.get(s.filename)??0)/Math.max(.01,maxGainDb))**2;
    }
    return error*error*3+movement;
  };
  // Deterministic coordinate descent. Pan first, then minor gain compensation.
  // No rapid frame-wise servo and no non-reproducible stochastic search.
  for(let iter=0;iter<4;iter++){
    for(const s of free){
      const start=s.pan;
      let best=pans.get(s.filename)!,cost=score();
      for(let i=-8;i<=8;i++){
        const candidate=clamp(start+i*maxPanMove/8,-1,1);
        pans.set(s.filename,candidate);
        const next=score();
        if(next<cost){cost=next;best=candidate;}
      }
      pans.set(s.filename,best);
    }
  }
  if(Math.abs(balance(active,pans,gains))>.25){
    for(let iter=0;iter<2;iter++){
      for(const s of free){
        let best=0,cost=score();
        for(let i=-4;i<=4;i++){
          const candidate=i*maxGainDb/4;
          gains.set(s.filename,candidate);
          const next=score();
          if(next<cost){cost=next;best=candidate;}
        }
        gains.set(s.filename,best);
      }
    }
  }
  const predictedDb=balance(active,pans,gains);
  const adjustments=free.map(s=>({
    filename:s.filename,pan:pans.get(s.filename)!,
    gainDb:gains.get(s.filename)??0
  })).filter(x=>Math.abs(x.pan-(active.find(s=>s.filename===x.filename)?.pan??0))>.005||Math.abs(x.gainDb)>.025);
  return {beforeDb,predictedDb,adjustments,reached:Math.abs(predictedDb)<=.25,
    reason:Math.abs(predictedDb)<=.25?"Estimated dry-stem balance within 0.25 dB":
      "Balance target not reached within restrained pan/gain limits; review rendered section measurement"};
}
