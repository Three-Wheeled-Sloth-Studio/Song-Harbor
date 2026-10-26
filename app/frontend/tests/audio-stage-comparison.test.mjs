import test from "node:test";
import assert from "node:assert/strict";
import {compareAudioStages} from "../src/AudioStageComparison.ts";

const rate=8000;
function audio(duration,render,channels=2){
  const length=duration*rate;
  const arrays=Array.from({length:channels},(_,c)=>Float32Array.from({length},(_,i)=>render(i/rate,c)));
  return {length,sampleRate:rate,numberOfChannels:channels,getChannelData(c){return arrays[c];}};
}
const tone=(t)=>.1*Math.sin(2*Math.PI*220*t);

test("unchanged stages produce no regression findings",()=>{
  const original=audio(8,t=>tone(t));
  const outcome=compareAudioStages(original,original,8);
  assert.equal(outcome.findings.length,0);
  assert.equal(outcome.referenceStage,"aligned-dry-stems");
});
test("large gain decrease introduced during processing is localized",()=>{
  const original=audio(10,t=>tone(t));
  const processed=audio(10,t=>tone(t)*(t>=3&&t<5?.18:1));
  const outcome=compareAudioStages(original,processed,10);
  const change=outcome.findings.find(f=>f.label.includes("reduction"));
  assert.ok(change);
  assert.ok(change.timeSeconds>=3&&change.timeSeconds<5);
});
test("large one-sided processing flags L/R movement without alleging defect",()=>{
  const original=audio(10,t=>tone(t));
  const processed=audio(10,(t,c)=>tone(t)*(t>=4&&t<7&&c===0?.16:1));
  const change=compareAudioStages(original,processed,10).findings.find(f=>f.label.includes("L/R"));
  assert.ok(change);
  assert.match(change.detail,/intentional/i);
});
test("silence is excluded, stereo/sample-rate mismatches are rejected",()=>{
  const silent=audio(3,()=>0);
  assert.deepEqual(compareAudioStages(silent,silent,3).findings,[]);
  assert.throws(()=>compareAudioStages(silent,{...silent,sampleRate:44100},3),/identical sample rate/);
});
test("does not mutate either audio buffer",()=>{
  const original=audio(6,t=>tone(t)), processed=audio(6,t=>tone(t)*.25);
  const before=processed.getChannelData(0).slice();
  compareAudioStages(original,processed,6);
  assert.deepEqual(processed.getChannelData(0),before);
});
