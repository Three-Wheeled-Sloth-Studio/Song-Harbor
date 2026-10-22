import {scheduleAutomation,valueAt,type AutomationPoint} from "./SectionAutomation";

export type CompressorCurves={
  threshold?:AutomationPoint[];ratio?:AutomationPoint[];
  attack?:AutomationPoint[];release?:AutomationPoint[];
};
export type DuckCurves={depthDb:AutomationPoint[];keyFilename:string};
export type DeEssCurves={frequency:AutomationPoint[];q:AutomationPoint[];threshold:AutomationPoint[];maxReduction:AutomationPoint[]};
export type DynamicsCurves={compressor?:CompressorCurves;duck?:DuckCurves;deess?:DeEssCurves};
export type DynamicsStage={
  compressor:DynamicsCompressorNode;
  duckGain:GainNode;
  deesser:BiquadFilterNode;
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
  const deesser=context.createBiquadFilter();
  deesser.type="peaking";deesser.frequency.value=6500;deesser.Q.value=2;deesser.gain.value=0;
  compressor.connect(deesser).connect(duckGain);
  return {compressor,duckGain,deesser};
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
export function makeDuckingEnvelope(key:AudioBuffer|readonly AudioBuffer[],depthDb:readonly AutomationPoint[],
    gain:number,stepSeconds=.02):AutomationPoint[]{
  if(!Number.isFinite(stepSeconds)||stepSeconds<.01||stepSeconds>.1)throw Error("Invalid detector resolution");
  const buffers=Array.isArray(key)?key:[key as AudioBuffer];
  if(!buffers.length)return [{time:0,value:1}];
  const sampleRate=buffers[0].sampleRate;
  const length=Math.min(...buffers.map(buffer=>buffer.length));
  if(buffers.some(buffer=>buffer.sampleRate!==sampleRate))throw Error("Sidechain sample rates differ");
  const channels=buffers.reduce((n,buffer)=>n+buffer.numberOfChannels,0);
  const step=Math.max(1,Math.round(sampleRate*stepSeconds));
  const points:AutomationPoint[]=[{time:0,value:1}];
  let detector=0;
  const attack=.035,release=.25;
  for(let pos=0;pos<length;pos+=step){
    const end=Math.min(length,pos+step);
    let power=0;
    for(const buffer of buffers)for(let c=0;c<buffer.numberOfChannels;c++){
      const data=buffer.getChannelData(c);
      for(let i=pos;i<end;i++)power+=data[i]*data[i];
    }
    const rms=Math.sqrt(power/Math.max(1,(end-pos)*channels))*Math.max(0,gain);
    const delta=(end-pos)/sampleRate;
    const tau=rms>detector?attack:release;
    detector+= (rms-detector)*(1-Math.exp(-delta/tau));
    const time=end/sampleRate;
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

/** Frequency-selective sibilance envelope for a peaking EQ band. This is
 * deterministic and identical in preview and offline export. A first-order
 * high-pass detector follows HF activity; the Biquad applies localized gain
 * rather than broad full-range compression. Max attenuation 0..12 dB.
 */
export function makeDeEssEnvelope(buffers:readonly AudioBuffer[],curve:DeEssCurves,
  level:number,stepSeconds=.025):AutomationPoint[]{
  if(!buffers.length)return [{time:0,value:0}];
  const sr=buffers[0].sampleRate;
  if(buffers.some(buffer=>buffer.sampleRate!==sr))throw Error("De-esser sample rates differ");
  const length=Math.min(...buffers.map(buffer=>buffer.length));
  const step=Math.max(1,Math.floor(sr*stepSeconds));
  const result:AutomationPoint[]=[{time:0,value:0}];
  const state=buffers.map(buffer=>Array.from({length:buffer.numberOfChannels},()=>({previous:0,filtered:0})));
  let envelope=0;
  for(let start=0;start<length;start+=step){
    const end=Math.min(length,start+step),time=end/sr;
    const frequency=valueAt(curve.frequency,time);
    const cutoff=Math.min(sr*.42,Math.max(1500,frequency*.72));
    const rc=1/(2*Math.PI*cutoff);
    const alpha=rc/(rc+1/sr);
    let power=0,count=0;
    for(let b=0;b<buffers.length;b++){
      const buffer=buffers[b];
      for(let c=0;c<buffer.numberOfChannels;c++){
        const samples=buffer.getChannelData(c),filter=state[b][c];
        for(let i=start;i<end;i++){
          const sample=samples[i];
          filter.filtered=alpha*(filter.filtered+sample-filter.previous);
          filter.previous=sample;
          power+=filter.filtered*filter.filtered;
          count++;
        }
      }
    }
    const detected=Math.sqrt(power/Math.max(1,count))*Math.max(0,level);
    const dt=(end-start)/sr;
    envelope+=(detected-envelope)*(1-Math.exp(-dt/(detected>envelope?.012:.12)));
    const thresholdDb=valueAt(curve.threshold,time);
    const excess=Math.max(0,20*Math.log10(Math.max(1e-8,envelope))-thresholdDb);
    const reduction=Math.min(valueAt(curve.maxReduction,time),excess*.6);
    result.push({time,value:-Math.max(0,reduction)});
  }
  return result;
}
export function scheduleDeEss(stage:DynamicsStage,curve:DeEssCurves|undefined,
  points:readonly AutomationPoint[]|undefined,offset:number,start:number){
  scheduleAutomation(stage.deesser.frequency,curve?.frequency||[{time:0,value:6500}],offset,start);
  scheduleAutomation(stage.deesser.Q,curve?.q||[{time:0,value:2}],offset,start);
  scheduleAutomation(stage.deesser.gain,points||[{time:0,value:0}],offset,start);
}
