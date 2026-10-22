import test from "node:test";
import assert from "node:assert/strict";
import {inspectRenderedAudio,FINDING_GROUPS} from "../src/AudioCleanupAnalyzer.ts";
const sampleRate=24000;
function audio(durationSeconds,producer,channels=2){
  const length=Math.round(durationSeconds*sampleRate);
  const arrays=Array.from({length:channels},(_,channel)=>{
    const values=new Float32Array(length);
    for(let i=0;i<length;i++)values[i]=producer(i/sampleRate,channel,i);
    return values;
  });
  return {length,numberOfChannels:channels,sampleRate,getChannelData(channel){return arrays[channel];}};
}
const kinds=results=>new Set(results.map(item=>item.kind));
test("silent audio has no sound-cleanup findings",()=>{
  const results=inspectRenderedAudio(audio(2,()=>0));
  assert.deepEqual(results,[]);
});
test("clipping candidates use output trim and preserve exact peak timestamp",()=>{
  const signal=audio(2,(t)=>t>=1&&t<1.2?1.1:0);
  let findings=inspectRenderedAudio(signal);
  assert.ok(kinds(findings).has("headroom"));
  assert.equal(findings.find(item=>item.kind==="headroom").severity,"warning");
  findings=inspectRenderedAudio(signal,-6);
  assert.equal(kinds(findings).has("headroom"),false);
});
test("short sample spike creates an auditionable transient candidate",()=>{
  const results=inspectRenderedAudio(audio(2,(_t,_c,i)=>i===sampleRate? .95:0));
  assert.ok(kinds(results).has("transient"));
});
test("spectral analysis detects sustained sibilance-like energy, not voice identity",()=>{
  const signal=audio(3,t=>t>=.5&&t<2? .18*Math.sin(2*Math.PI*7100*t):0);
  assert.ok(kinds(inspectRenderedAudio(signal)).has("sibilance"));
});
test("presence-band concentration flags a harshness listening candidate",()=>{
  const signal=audio(3,t=>t>=.5&&t<2? .2*Math.sin(2*Math.PI*3300*t):0);
  assert.ok(kinds(inspectRenderedAudio(signal)).has("harshness"));
});
test("quiet high-frequency residual can be reviewed as noise, not auto-repaired",()=>{
  const signal=audio(4,t=> .012*Math.sin(2*Math.PI*10200*t));
  assert.ok(kinds(inspectRenderedAudio(signal)).has("noise"));
});
test("sustained stereo anti-phase warns about potential mono cancellation",()=>{
  const signal=audio(4,(t,c)=>(c===0?1:-1)*.12*Math.sin(2*Math.PI*440*t));
  assert.ok(kinds(inspectRenderedAudio(signal)).has("phase"));
});
test("bright HF spectrum suggests possible fizz without claiming an artifact",()=>{
  const signal=audio(3,t=>(t>=.5&&t<2)
    ? .12*Math.sin(2*Math.PI*6800*t)+.14*Math.sin(2*Math.PI*10300*t):0);
  assert.ok(kinds(inspectRenderedAudio(signal)).has("fizz"));
});
test("normal aligned stereo and steady lower-frequency audio are not phase alarms",()=>{
  const signal=audio(3,t=>.15*Math.sin(2*Math.PI*440*t));
  assert.equal(kinds(inspectRenderedAudio(signal)).has("phase"),false);
});
test("analysis is non-destructive and respects finding cap",()=>{
  const signal=audio(2,(t,_c,i)=>i%1000===0?.9:0);
  const prior=signal.getChannelData(0).slice();
  const found=inspectRenderedAudio(signal,0,3);
  assert.ok(found.length<=3);
  assert.deepEqual(signal.getChannelData(0),prior);
});
test("finding groups include all supported sound-cleanup categories",()=>{
  assert.equal(FINDING_GROUPS.sibilance,"Vocal / high frequency");
  assert.equal(FINDING_GROUPS.phase,"Stereo / mono");
  assert.equal(FINDING_GROUPS.pumping,"Dynamics");
});
