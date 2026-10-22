import test from "node:test";
import assert from "node:assert/strict";
import {analyzeSections} from "../src/SectionInsights.ts";
const rate=4800;
function audio(channels,seconds=6){
  const length=rate*seconds;
  const a=channels.map(producer=>{
    const data=new Float32Array(length);
    for(let i=0;i<length;i++)data[i]=producer(i/rate);
    return data;
  });
  return {length,sampleRate:rate,numberOfChannels:a.length,getChannelData:i=>a[i]};
}
const ranges=[{id:"a",start_seconds:0,end_seconds:2},{id:"b",start_seconds:2,end_seconds:4},{id:"c",start_seconds:4,end_seconds:6}];
test("section metrics show loud left image and unbiased centered image",()=>{
  const mix=audio([
    t=>t<2?.2:t<4?.1:.4,
    t=>t<2?.05:t<4?.1:.4
  ]);
  const result=analyzeSections(mix,ranges);
  assert.equal(result.length,3);
  assert.ok(result[0].balanceDb>8,"left-heavy section has positive balance");
  assert.ok(Math.abs(result[1].balanceDb)<.01,"centered sections balanced");
  assert.ok(Math.abs(result[2].balanceDb)<.01,"both channels same level");
  assert.ok(result[2].intensity>result[0].intensity);
  assert.ok(result[0].intensity>result[1].intensity);
});
test("output trim influences absolute metrics but not intensity ranking or balance",()=>{
  const mix=audio([t=>t<3?.1:.3,t=>t<3?.2:.3]);
  const untrimmed=analyzeSections(mix,ranges);
  const trimmed=analyzeSections(mix,ranges,-6);
  for(let i=0;i<ranges.length;i++){
    assert.ok(Math.abs(untrimmed[i].rmsDbfs-trimmed[i].rmsDbfs-6)<.01);
    assert.ok(Math.abs(untrimmed[i].balanceDb-trimmed[i].balanceDb)<.01);
    assert.ok(Math.abs(untrimmed[i].intensity-trimmed[i].intensity)<.0001);
  }
});
test("does not change sample buffers and refuses nonstereo",()=>{
  const mix=audio([t=>t/12,t=>-t/12]);
  const before=mix.getChannelData(0).slice();
  analyzeSections(mix,ranges);
  assert.deepEqual(mix.getChannelData(0),before);
  assert.deepEqual(analyzeSections(audio([()=>.2]),ranges),[]);
});
