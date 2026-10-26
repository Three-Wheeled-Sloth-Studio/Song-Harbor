import test from "node:test";
import assert from "node:assert/strict";
import {regionSpectrogram} from "../src/RegionSpectrogram.ts";
const sampleRate=24000,length=sampleRate*6;
function fixture(){
  const data=Float32Array.from({length},(_,i)=>.12*Math.sin(2*Math.PI*500*i/sampleRate));
  return {sampleRate,length,numberOfChannels:1,getChannelData:()=>data};
}
test("bounded region spectrum follows finding timestamp without editing samples",()=>{
  const sound=fixture(),before=sound.getChannelData(0).slice();
  const result=regionSpectrogram(sound,3);
  assert.equal(result.columns,24);
  assert.equal(result.rows,12);
  assert.equal(result.levels.length,288);
  assert.ok(result.levels.every(v=>v>=0&&v<=1));
  assert.ok(result.startSeconds<=3&&result.startSeconds+result.seconds>=3);
  assert.deepEqual(sound.getChannelData(0),before);
});
test("spectrum selection clamps at beginning and end",()=>{
  const sound=fixture();
  assert.equal(regionSpectrogram(sound,0).startSeconds,0);
  assert.equal(regionSpectrogram(sound,6).startSeconds,3);
});
