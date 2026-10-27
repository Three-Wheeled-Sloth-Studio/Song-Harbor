import test from "node:test";
import assert from "node:assert/strict";
import {inspectReverbTail} from "../src/ReverbTailDiagnostic.ts";
import {plannedMethodFixtures} from "./planned-artifact-fixtures.mjs";

const cases=()=>plannedMethodFixtures().reverb;
const byId=id=>cases().find(item=>item.id===id).audio;

test("natural exponential decay has no discontinuity observation",()=>{
  assert.deepEqual(inspectReverbTail(byId("natural-decay")),[]);
});
test("hard tail end is localized",()=>{
  const found=inspectReverbTail(byId("hard-tail-cut"));
  assert.ok(found.some(item=>item.kind==="cutoff"&&Math.abs(item.timeSeconds-1.15)<=.02));
});
test("flat tail after decay is localized",()=>{
  const found=inspectReverbTail(byId("stalled-tail"));
  assert.ok(found.some(item=>item.kind==="stall"&&Math.abs(item.timeSeconds-.8)<=.05));
});
test("identical intentional gate produces identical acoustic evidence",()=>{
  assert.deepEqual(inspectReverbTail(byId("intentional-gated-reverb")),
    inspectReverbTail(byId("hard-tail-cut")));
});
test("silence, a steady tone, and a short buffer remain unflagged",()=>{
  const make=(seconds,render)=>{
    const sampleRate=24000,length=Math.round(seconds*sampleRate);
    const data=Float32Array.from({length},(_,i)=>render(i/sampleRate));
    return {sampleRate,length,numberOfChannels:1,getChannelData:()=>data};
  };
  assert.deepEqual(inspectReverbTail(make(2,()=>0)),[]);
  assert.deepEqual(inspectReverbTail(make(2,t=>.2*Math.sin(2*Math.PI*440*t))),[]);
  assert.deepEqual(inspectReverbTail(make(.2,t=>.2*Math.sin(2*Math.PI*440*t))),[]);
});
test("invalid samples and metadata fail closed",()=>{
  const invalid={sampleRate:24000,length:12000,numberOfChannels:1,
    getChannelData:()=>Float32Array.from({length:12000},(_,i)=>i===4000?NaN:0)};
  assert.deepEqual(inspectReverbTail(invalid),[]);
  assert.deepEqual(inspectReverbTail({...invalid,sampleRate:NaN}),[]);
  assert.deepEqual(inspectReverbTail({...invalid,numberOfChannels:0}),[]);
});
test("inspection leaves source PCM unchanged",()=>{
  const signal=byId("stalled-tail"),before=signal.getChannelData(0).slice();
  inspectReverbTail(signal);
  assert.deepEqual(signal.getChannelData(0),before);
});
