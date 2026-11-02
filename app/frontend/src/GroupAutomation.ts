/** Pure, deterministic group automation solver. No changes to source audio or user directives.
 * Inputs are per-stem RMS power estimates measured on the offset-aware section timeline.
 * The caller must apply derived gain envelopes consistently to audition and export.
 */
import {solveAutoPan,type AutoStem,type AutoPanResult} from "./AutoPan";

export type GroupMember = {
  filename:string;
  baselinePower:number;
  currentPower:number;
  gainDb:number;
  gainLocked:boolean;
  active:boolean;
};
export type GroupGainAdjustment={filename:string;gainDb:number;changeDb:number};
export type GroupGainResult={
  baselinePower:number;beforePower:number;predictedPower:number;
  residualDb:number;reached:boolean;reason:string;
  adjustments:GroupGainAdjustment[];
};
const EPS=1e-12;
const db=(ratio:number)=>10*Math.log10(Math.max(EPS,ratio));
const finiteNonnegative=(n:number)=>Number.isFinite(n)&&n>=0;
const powerAfterDb=(power:number,deltaDb:number)=>power*10**(deltaDb/10);

/** Target: preserve the group's reference power, adjusting unlocked members only.
 * The baseline MUST be captured before the user's current section adjustments.
 * Does not increase gains in the presence of silence or while compensating a boost.
 */
export function solveGroupGain(
  members:GroupMember[], maxCorrectionDb=6, toleranceDb=.25
):GroupGainResult{
  if(!Number.isFinite(maxCorrectionDb)||maxCorrectionDb<0||maxCorrectionDb>24)
    throw Error("Invalid maximum group correction");
  if(!Number.isFinite(toleranceDb)||toleranceDb<0)
    throw Error("Invalid group gain tolerance");
  const names=new Set<string>();
  for(const m of members){
    if(!m.filename||names.has(m.filename.toLowerCase())||
      !finiteNonnegative(m.baselinePower)||!finiteNonnegative(m.currentPower)||
      !Number.isFinite(m.gainDb))throw Error("Invalid group member");
    names.add(m.filename.toLowerCase());
  }
  const active=members.filter(m=>m.active);
  const baselinePower=active.reduce((s,m)=>s+m.baselinePower,0);
  const beforePower=active.reduce((s,m)=>s+m.currentPower,0);
  if(baselinePower<=EPS||beforePower<=EPS)return {
    baselinePower,beforePower,predictedPower:beforePower,residualDb:0,reached:baselinePower<=EPS&&beforePower<=EPS,
    reason:"Insufficient audible group energy for safe compensation",adjustments:[]
  };
  const adjustable=active.filter(m=>!m.gainLocked&&m.currentPower>EPS);
  const fixedPower=active.filter(m=>m.gainLocked||m.currentPower<=EPS)
    .reduce((s,m)=>s+m.currentPower,0);
  const adjustablePower=adjustable.reduce((s,m)=>s+m.currentPower,0);
  // All eligible members receive the same correction: relative balance is preserved.
  const requiredRatio=(baselinePower-fixedPower)/Math.max(EPS,adjustablePower);
  let correction=requiredRatio>0?10*Math.log10(requiredRatio):-maxCorrectionDb;
  correction=Math.max(-maxCorrectionDb,Math.min(maxCorrectionDb,correction));
  if(!adjustable.length)correction=0;
  const predictedPower=fixedPower+powerAfterDb(adjustablePower,correction);
  const residualDb=db(predictedPower/baselinePower);
  return {
    baselinePower,beforePower,predictedPower,residualDb,
    reached:Math.abs(residualDb)<=toleranceDb,
    reason:Math.abs(residualDb)<=toleranceDb?"Group baseline level retained":
      adjustable.length?"Group correction bounded or blocked by locked members":
      "No eligible unlocked group members",
    adjustments:adjustable.filter(()=>Math.abs(correction)>.001)
      .map(m=>({filename:m.filename,gainDb:m.gainDb+correction,changeDb:correction}))
  };
}

/** Reuse the standard restrained auto-pan solver, strictly scoped to group members. */
export function solveGroupPan(stems:AutoStem[]):AutoPanResult{
  return solveAutoPan(stems);
}
