/** Deterministic bounded group loudness compensation.
 * Target: sum of untreated member powers, at the same source-audio moment.
 * Explicitly authored members are locked; only peers can compensate.
 */
export type GroupGainMember={
  filename:string;baselinePower:number;currentPower:number;locked:boolean
};
export type GroupGainAdjustment={filename:string;gainDb:number};
export type GroupGainResult={
  beforeDb:number;predictedDb:number;adjustments:GroupGainAdjustment[];
  reached:boolean;reason:string
};
export function solveGroupGain(members:readonly GroupGainMember[],limitDb=4):GroupGainResult{
  const finite=members.filter(m=>Number.isFinite(m.baselinePower)&&m.baselinePower>=0&&
    Number.isFinite(m.currentPower)&&m.currentPower>=0);
  const baseline=finite.reduce((sum,m)=>sum+m.baselinePower,0);
  const current=finite.reduce((sum,m)=>sum+m.currentPower,0);
  if(baseline<1e-10)return {beforeDb:0,predictedDb:0,adjustments:[],reached:true,
    reason:"Group is silent in this section"};
  const db=(power:number)=>10*Math.log10(Math.max(1e-12,power)/baseline);
  const locked=finite.filter(m=>m.locked).reduce((sum,m)=>sum+m.currentPower,0);
  const free=finite.filter(m=>!m.locked&&m.currentPower>1e-12);
  const available=free.reduce((sum,m)=>sum+m.currentPower,0);
  if(available<1e-12)return {beforeDb:db(current),predictedDb:db(current),adjustments:[],
    reached:Math.abs(db(current))<.25,reason:"No eligible group members to compensate"};
  const wanted=Math.max(0,baseline-locked);
  const ideal=Math.sqrt(wanted/available);
  const bounded=Math.max(10**(-limitDb/20),Math.min(10**(limitDb/20),ideal));
  const gainDb=20*Math.log10(bounded);
  const predicted=locked+available*bounded*bounded;
  return {beforeDb:db(current),predictedDb:db(predicted),
    adjustments:Math.abs(gainDb)>.025?free.map(m=>({filename:m.filename,gainDb})):[],
    reached:Math.abs(db(predicted))<=.25,
    reason:Math.abs(db(predicted))<=.25?"Group loudness within 0.25 dB of untreated baseline":
      "Group could not reach baseline within bounded corrections; explicit member gains protected"};
}
