import {scheduleAutomation, type AutomationPoint} from "./SectionAutomation";

/**
 * Width is an M/S matrix around a source's existing stereo image.
 * L' = ((1+w)L + (1-w)R)/2, R' = ((1-w)L + (1+w)R)/2.
 * w=1 is bit-transparent mathematically; w=0 folds down to mono.
 * Unlike Haas/decorrelation widening, this does not invent stereo from mono.
 */
export type StereoWidthStage={
  input:ChannelSplitterNode;
  output:ChannelMergerNode;
  direct:[GainNode,GainNode];
  cross:[GainNode,GainNode];
};
export function createStereoWidthStage(context:BaseAudioContext):StereoWidthStage{
  const input=context.createChannelSplitter(2);
  const output=context.createChannelMerger(2);
  const ll=context.createGain(),rr=context.createGain();
  const lr=context.createGain(),rl=context.createGain();
  input.connect(ll,0); ll.connect(output,0,0);
  input.connect(rr,1); rr.connect(output,0,1);
  input.connect(lr,0); lr.connect(output,0,1);
  input.connect(rl,1); rl.connect(output,0,0);
  ll.gain.value=1;rr.gain.value=1;lr.gain.value=0;rl.gain.value=0;
  return {input,output,direct:[ll,rr],cross:[lr,rl]};
}
export function scheduleStereoWidth(stage:StereoWidthStage,
  points:readonly AutomationPoint[],offset:number,start:number){
  const direct=points.map(p=>({time:p.time,value:(1+p.value)/2}));
  const cross=points.map(p=>({time:p.time,value:(1-p.value)/2}));
  for(const gain of stage.direct)scheduleAutomation(gain.gain,direct,offset,start);
  for(const gain of stage.cross)scheduleAutomation(gain.gain,cross,offset,start);
}
