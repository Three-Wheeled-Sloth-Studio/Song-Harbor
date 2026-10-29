/** Non-destructive replacement mute layer. Multiplies, never rewrites, user automation. */
import type {AutomationPoint} from "./SectionAutomation";
export type ReplacementMask={
  replacement_track_id:string;
  source_track_id:string;
  source_filename:string;
  start_seconds:number;
  end_seconds:number;
  fade_seconds:number;
};
function gainAt(masks:readonly ReplacementMask[],time:number):number{
  let gain=1;
  for(const item of masks){
    const fade=Math.max(.001,Math.min(item.fade_seconds,(item.end_seconds-item.start_seconds)/4));
    if(time<item.start_seconds||time>item.end_seconds)continue;
    if(time<item.start_seconds+fade)gain*=Math.max(0,1-(time-item.start_seconds)/fade);
    else if(time>item.end_seconds-fade)gain*=Math.max(0,1-(item.end_seconds-time)/fade);
    else gain=0;
  }
  return gain;
}
export function replacementGainAt(masks:readonly ReplacementMask[],time:number):number{
  return gainAt(masks,time);
}
export function replacementCurve(masks:readonly ReplacementMask[]):AutomationPoint[]{
  if(!masks.length)return [{time:0,value:1}];
  const stamps=new Set<number>([0]);
  for(const mask of masks){
    const fade=Math.max(.001,Math.min(mask.fade_seconds,(mask.end_seconds-mask.start_seconds)/4));
    for(const t of [mask.start_seconds,mask.start_seconds+fade,mask.end_seconds-fade,mask.end_seconds])
      stamps.add(Math.max(0,t));
  }
  return [...stamps].sort((a,b)=>a-b).map(time=>({time,value:gainAt(masks,time)}));
}
