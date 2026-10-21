import {scheduleAutomation,valueAt,type AutomationPoint} from "./SectionAutomation";

export type CompressorCurves={
  threshold?:AutomationPoint[];ratio?:AutomationPoint[];
  attack?:AutomationPoint[];release?:AutomationPoint[];
};
export type DuckCurves={depthDb:AutomationPoint[];keyFilename:string};
export type DynamicsCurves={compressor?:CompressorCurves;duck?:DuckCurves};
export type DynamicsStage={
  compressor:DynamicsCompressorNode;
  duckGain:GainNode;
};
/** Disabled by default (ratio=1) for existing mastered songs. */
export function createDynamicsStage(context:BaseAudioContext):DynamicsStage{
  const compressor=context.createDynamicsCompressor();
  compressor.threshold.value=-18;
  compressor.knee.value=12;
  compressor.ratio.value=1;
  compressor.attack.value=.012;
  compressor.release.value=.18;
  const duckGain=context.createGain();
  compressor.connect(duckGain);
  return {compressor,duckGain};
}
export function scheduleCompressor(stage:DynamicsStage,curve:CompressorCurves|undefined,
  offset:number,start:number){
  scheduleAutomation(stage.compressor.threshold,curve?.threshold||[{time:0,value:-18}],offset,start);
  scheduleAutomation(stage.compressor.ratio,curve?.ratio||[{time:0,value:1}],offset,start);
  scheduleAutomation(stage.compressor.attack,curve?.attack||[{time:0,value:.012}],offset,start);
  scheduleAutomation(stage.compressor.release,curve?.release||[{time:0,value:.18}],offset,start);
}
/** Deterministic, bounded RMS detector. Preview and WAV schedule identical gain points.
 * The detector reads the immutable decoded vocal AudioBuffer; it does not alter it.
 * It operates at 50Hz, so this is envelope ducking, not sample-rate sidechaining.
 */
export function makeDuckingEnvelope(key:AudioBuffer,depthDb:readonly AutomationPoint[],
    gain:number,stepSeconds=.02):AutomationPoint[]{
  if(!Number.isFinite(stepSeconds)||stepSeconds<.01||stepSeconds>.1)throw Error("Invalid detector resolution");
  const channels=key.numberOfChannels;
  const step=Math.max(1,Math.round(key.sampleRate*stepSeconds));
  const points:AutomationPoint[]=[{time:0,value:1}];
  let detector=0;
  const attack=.035,release=.25;
  for(let pos=0;pos<key.length;pos+=step){
    const end=Math.min(key.length,pos+step);
    let power=0;
    for(let c=0;c<channels;c++){
      const data=key.getChannelData(c);
      for(let i=pos;i<end;i++)power+=data[i]*data[i];
    }
    const rms=Math.sqrt(power/Math.max(1,(end-pos)*channels))*Math.max(0,gain);
    const delta=(end-pos)/key.sampleRate;
    const tau=rms>detector?attack:release;
    detector+= (rms-detector)*(1-Math.exp(-delta/tau));
    const time=end/key.sampleRate;
    const depth=valueAt(depthDb,time);
    // A gentle onset above -30 dBFS; full requested depth above -15 dBFS.
    const activity=Math.min(1,Math.max(0,(detector-.0316)/(.1778-.0316)));
    const db=Math.min(0,Math.max(-12,depth))*activity;
    points.push({time,value:Math.pow(10,db/20)});
  }
  return points;
}
export function scheduleDucking(stage:DynamicsStage,points:readonly AutomationPoint[]|undefined,
  offset:number,start:number){
  scheduleAutomation(stage.duckGain.gain,points||[{time:0,value:1}],offset,start);
}
