import {scheduleAutomation,type AutomationPoint} from "./SectionAutomation";

export type EqBandCurve={frequency:AutomationPoint[];q:AutomationPoint[];gain:AutomationPoint[]};
export type EqCurves=Partial<Record<1|2|3,EqBandCurve>>;

/** Three neutral peaking filters; source channels remain linked and phase-coherent.
 * Default 0 dB is nominally transparent. Dynamics and saturation are not included.
 */
export function createEqStage(context:BaseAudioContext):[BiquadFilterNode,BiquadFilterNode,BiquadFilterNode]{
  const nodes=[1,2,3].map(()=>{
    const filter=context.createBiquadFilter();
    filter.type="peaking";filter.frequency.value=1000;filter.Q.value=1;filter.gain.value=0;
    return filter;
  }) as [BiquadFilterNode,BiquadFilterNode,BiquadFilterNode];
  nodes[0].connect(nodes[1]);nodes[1].connect(nodes[2]);
  return nodes;
}
export function scheduleEq(nodes:readonly BiquadFilterNode[],curves:EqCurves,
                           offset:number,start:number,bypass=false){
  for(let index=0;index<3;index++){
    const c=curves[(index+1) as 1|2|3];
    const filter=nodes[index];
    scheduleAutomation(filter.frequency,c?.frequency||[{time:0,value:1000}],offset,start);
    scheduleAutomation(filter.Q,c?.q||[{time:0,value:1}],offset,start);
    scheduleAutomation(filter.gain,!bypass&&c?.gain||[{time:0,value:0}],offset,start);
  }
}
