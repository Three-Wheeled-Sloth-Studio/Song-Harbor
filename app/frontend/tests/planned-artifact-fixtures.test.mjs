import test from "node:test";
import assert from "node:assert/strict";
import {plannedMethodFixtures} from "./planned-artifact-fixtures.mjs";

test("planned acoustic categories include intentionally confounding controls",()=>{
  const groups=plannedMethodFixtures();
  for(const key of ["reverb","spatial","spectral","vocal"])assert.ok(groups[key].length);
  assert.ok(groups.reverb.some(x=>x.id==="intentional-gated-reverb"));
  assert.ok(groups.spatial.some(x=>x.id==="intentional-wide-spatial"));
  assert.ok(groups.spectral.some(x=>x.id==="deliberate-industrial-harmonics"));
});
test("all planned acoustic fixtures have valid finite bounded PCM",()=>{
  for(const entries of Object.values(plannedMethodFixtures()))for(const item of entries){
    assert.equal(item.audio.sampleRate,24000);
    assert.equal(item.audio.numberOfChannels,2);
    for(let c=0;c<2;c++){
      const data=item.audio.getChannelData(c);
      assert.equal(data.length,item.audio.length);
      for(const value of data)assert.ok(Number.isFinite(value)&&Math.abs(value)<=1,
        item.id+" contains invalid sample");
    }
    for(const event of item.annotations){
      assert.ok(event.timeSeconds>=0&&event.timeSeconds<item.audio.length/item.audio.sampleRate);
      assert.ok(event.kind.length>0);
    }
  }
});
test("reverb cutoff and intentional gated reverb have identical PCM: intent is not inferable",()=>{
  const cases=plannedMethodFixtures().reverb;
  const cutoff=cases.find(x=>x.id==="hard-tail-cut");
  const gated=cases.find(x=>x.id==="intentional-gated-reverb");
  assert.deepEqual(cutoff.audio.getChannelData(0),gated.audio.getChannelData(0));
  assert.notDeepEqual(cutoff.annotations,gated.annotations);
});
test("positive antiphase control has negligible mono sum and aligned control does not",()=>{
  const {spatial}=plannedMethodFixtures();
  const anti=spatial.find(x=>x.id==="antiphase-stereo").audio;
  const aligned=spatial.find(x=>x.id==="aligned-stereo").audio;
  const rms=a=>Math.sqrt(a.reduce((sum,v)=>sum+v*v,0)/a.length);
  const mono=a=>Float32Array.from(a.getChannelData(0),(v,i)=>(v+a.getChannelData(1)[i])/2);
  assert.ok(rms(mono(anti))<1e-6);
  assert.ok(rms(mono(aligned))>.05);
});
