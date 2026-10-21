import {scheduleAutomation,type AutomationPoint} from "./SectionAutomation";

/**
 * Bounded cross-channel first reflections, no feedback.
 * A left impulse yields low-level right reflection at 19ms and vice versa
 * at 13ms. 0 send is bypass, 0.4 is maximum. Stereo-difference creation
 * is intentionally modest and must be checked in mono.
 */
export type SpatialReflectionStage={
  input:ChannelSplitterNode;
  output:ChannelMergerNode;
  sends:[GainNode,GainNode];
  delays:[DelayNode,DelayNode];
};
export function createSpatialReflection(context:BaseAudioContext):SpatialReflectionStage{
  const input=context.createChannelSplitter(2);
  const output=context.createChannelMerger(2);
  const left=context.createDelay(.1),right=context.createDelay(.1);
  left.delayTime.value=.013;
  right.delayTime.value=.019;
  const leftSend=context.createGain(),rightSend=context.createGain();
  leftSend.gain.value=0;rightSend.gain.value=0;
  // Cross reflection: left source feeds delayed RIGHT, right source delayed LEFT.
  input.connect(left,0);left.connect(rightSend);rightSend.connect(output,0,1);
  input.connect(right,1);right.connect(leftSend);leftSend.connect(output,0,0);
  return {input,output,sends:[leftSend,rightSend],delays:[left,right]};
}
export function scheduleSpatialReflection(stage:SpatialReflectionStage,
  points:readonly AutomationPoint[],offset:number,start:number){
  for(const send of stage.sends)scheduleAutomation(send.gain,points,offset,start);
}
