import test from "node:test";
import assert from "node:assert/strict";
import {makeDeclickCandidate} from "../src/LocalizedDeclick.ts";
const rate=24000,length=rate;
function signal(click=true){
  const channels=Array.from({length:2},()=>Float32Array.from({length},(_,i)=>{
    const base=.06*Math.sin(i*2*Math.PI*440/rate);
    return click&&i===12000?base+.9:base;
  }));
  return {length,sampleRate:rate,numberOfChannels:2,getChannelData:i=>channels[i]};
}
test("de-click returns copied PCM, modifies only selected span",()=>{
  const input=signal(),before=input.getChannelData(0).slice();
  const result=makeDeclickCandidate(input,.5,1);
  assert.deepEqual(input.getChannelData(0),before);
  assert.ok(result.afterPeak<result.beforePeak);
  assert.ok(Math.abs(result.channels[0][12000])<.25);
  for(let i=0;i<length;i++){
    if(i<result.startFrame||i>=result.endFrame)
      assert.equal(result.channels[0][i],before[i]);
  }
  assert.equal(result.replacements.length,2);
});
test("click near file edge and invalid windows rejected",()=>{
  const input=signal();
  assert.throws(()=>makeDeclickCandidate(input,-1),/within/);
  assert.throws(()=>makeDeclickCandidate(input,1),/within/);
  assert.throws(()=>makeDeclickCandidate(input,.5,9),/window/);
});
test("smooth sound without click only changes tiny range",()=>{
  const input=signal(false);
  const result=makeDeclickCandidate(input,.5);
  assert.ok(Math.abs(result.channels[0][12000]-input.getChannelData(0)[12000])<.02);
});
