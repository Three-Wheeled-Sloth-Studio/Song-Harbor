import test from "node:test";
import assert from "node:assert/strict";
import {bandEvidence} from "../src/StemArtifactAttribution.ts";
const rate=24000,duration=3,length=rate*duration;
const fixture=(name,hz,gain=1)=>{const data=Float32Array.from({length},(_,i)=>.3*Math.sin(2*Math.PI*hz*i/rate));return {
  name,startSeconds:0,level:gain,
  buffer:{sampleRate:rate,length,numberOfChannels:1,getChannelData:()=>data},
  original:data
};};
test("presence-band artifact evidence prioritizes the actual high-band stem",()=>{
  const high=fixture("Guitar",3400),low=fixture("Bass",110);
  const result=bandEvidence([low,high],"harshness",1);
  assert.equal(result.ranked[0].name,"Guitar");
  assert.ok(result.ranked[0].relativeShare>.8);
  assert.equal(result.band,"2.5–4.9 kHz");
});
test("vocal sibilance evidence prioritizes upper frequencies",()=>{
  const high=fixture("Vocals",6800),low=fixture("Other",400);
  assert.equal(bandEvidence([low,high],"sibilance",1).ranked[0].name,"Vocals");
});
test("quiet, inactive, and silent signals stay uncertain",()=>{
  const silent=fixture("Silent",3000,0);
  const result=bandEvidence([silent],"harshness",1);
  assert.equal(result.ranked.length,0);
  assert.equal(result.uncertain,true);
});
test("analysis does not change source samples",()=>{
  const high=fixture("Lead",3000),before=high.original.slice();
  bandEvidence([high],"harshness",1);
  assert.deepEqual(high.original,before);
});
