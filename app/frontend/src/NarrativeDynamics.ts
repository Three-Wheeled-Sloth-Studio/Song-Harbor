import type {SectionInsight} from "./SectionInsights.ts";

/** Narrative mix observations only. Never applies audio changes. */
export type NarrativeShift = {
  fromId:string;
  toId:string;
  rmsDeltaDb:number;
  peakDeltaDb:number;
  widthDeltaDb:number;
  balanceDeltaDb:number;
  tags:("level-rise"|"level-drop"|"width-rise"|"width-drop"|"density-rise"|"density-drop"|"balance-shift")[];
  description:string;
};

export type SectionComparison = {
  referenceId:string;
  candidateId:string;
  differenceDb:number;
  suggestedCandidateTrimDb:number;
  matched:boolean;
  reason:string;
};

const round=(value:number)=>Math.round(value*10)/10;
const finite=(value:number)=>Number.isFinite(value);
const crest=(row:SectionInsight)=>row.peakDbfs-row.rmsDbfs;

/** Compare adjacent sections without declaring a creative choice to be a defect. */
export function inspectNarrativeShifts(rows:readonly SectionInsight[]):NarrativeShift[]{
  const result:NarrativeShift[]=[];
  for(let i=1;i<rows.length;i++){
    const a=rows[i-1],b=rows[i];
    if(![a.rmsDbfs,b.rmsDbfs,a.peakDbfs,b.peakDbfs,a.widthDb,b.widthDb,a.balanceDb,b.balanceDb].every(finite))continue;
    const loud=b.rmsDbfs-a.rmsDbfs;
    const width=b.widthDb-a.widthDb;
    const balance=b.balanceDb-a.balanceDb;
    const density=crest(b)-crest(a);
    const tags:NarrativeShift["tags"]=[];
    if(loud>=2)tags.push("level-rise");
    if(loud<=-2)tags.push("level-drop");
    if(width>=3)tags.push("width-rise");
    if(width<=-3)tags.push("width-drop");
    if(density<=-2)tags.push("density-rise");
    if(density>=2)tags.push("density-drop");
    if(Math.abs(balance)>=2)tags.push("balance-shift");
    if(tags.length===0)continue;
    result.push({
      fromId:a.sectionId,toId:b.sectionId,
      rmsDeltaDb:round(loud),peakDeltaDb:round(b.peakDbfs-a.peakDbfs),
      widthDeltaDb:round(width),balanceDeltaDb:round(balance),
      tags,
      description:tags.map(t=>({
        "level-rise":"average level rises","level-drop":"average level falls",
        "width-rise":"stereo side/mid ratio increases","width-drop":"stereo side/mid ratio decreases",
        "density-rise":"crest factor decreases","density-drop":"crest factor increases",
        "balance-shift":"left/right balance shifts"
      })[t]).join("; ")
    });
  }
  return result;
}

/**
 * Estimate gain to RMS-match one section to another for an audition preview.
 * This is not gated LUFS or perceptual loudness matching.
 * Never apply the gain to project automation or the final render.
 */
export function sectionMatchTrim(reference:SectionInsight,candidate:SectionInsight,maxAbsTrimDb=12):SectionComparison{
  const output:SectionComparison={referenceId:reference.sectionId,candidateId:candidate.sectionId,
    differenceDb:0,suggestedCandidateTrimDb:0,matched:false,reason:""};
  if(!finite(reference.rmsDbfs)||!finite(candidate.rmsDbfs)||!finite(reference.peakDbfs)||!finite(candidate.peakDbfs)){
    return {...output,reason:"Invalid section measurements"};
  }
  if(reference.rmsDbfs<=-85||candidate.rmsDbfs<=-85){
    return {...output,reason:"One or both sections are effectively silent"};
  }
  const needed=reference.rmsDbfs-candidate.rmsDbfs;
  const bounded=Math.max(-Math.abs(maxAbsTrimDb),Math.min(Math.abs(maxAbsTrimDb),needed));
  // Avoid gain-up clipping: sample peak must stay at or below -1 dBFS.
  const safe=Math.min(bounded,-1-candidate.peakDbfs);
  const trim=Math.min(0,Math.max(-Math.abs(maxAbsTrimDb),safe))===safe?safe:Math.max(-Math.abs(maxAbsTrimDb),safe);
  const matched=Math.abs(needed-trim)<0.25;
  return {...output,differenceDb:round(candidate.rmsDbfs-reference.rmsDbfs),
    suggestedCandidateTrimDb:round(trim),matched,
    reason:matched?"RMS levels matched within 0.25 dB":
      trim<needed?"Gain capped by headroom or adjustment limit":"Gain limited by adjustment range"};
}
