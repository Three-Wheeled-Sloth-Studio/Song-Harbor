import test from "node:test";
import assert from "node:assert/strict";
import {inspectNarrativeShifts,sectionMatchTrim} from "../src/NarrativeDynamics.ts";
const section=(id,rms,peak,width=0,balance=0)=>({sectionId:id,rmsDbfs:rms,peakDbfs:peak,widthDb:width,balanceDb:balance,intensity:0.5});
test("reports transitions without labeling artistic decisions defects",()=>{
  const changes=inspectNarrativeShifts([
    section("intro",-20,-4,4),
    section("chorus",-14,-2,-1),
    section("bridge",-18,-3,-6,3)
  ]);
  assert.equal(changes.length,2);
  assert.deepEqual(changes[0].tags.includes("level-rise"),true);
  assert.deepEqual(changes[0].tags.includes("width-drop"),true);
  assert.deepEqual(changes[1].tags.includes("level-drop"),true);
  assert.equal(changes[0].toId,"chorus");
});
test("silence and invalid values are not matched",()=>{
  assert.equal(sectionMatchTrim(section("a",-90,-90),section("b",-15,-2)).matched,false);
  assert.equal(sectionMatchTrim(section("a",NaN,-2),section("b",-15,-2)).matched,false);
});
test("candidate louder than reference gets bounded attenuation",()=>{
  const comparison=sectionMatchTrim(section("a",-18,-5),section("b",-14,-2));
  assert.equal(comparison.suggestedCandidateTrimDb,-4);
  assert.equal(comparison.matched,true);
});
test("candidate quieter than reference cannot be boosted into clipping",()=>{
  const comparison=sectionMatchTrim(section("a",-12,-2),section("b",-18,-1.5));
  assert.equal(comparison.suggestedCandidateTrimDb,0.5);
  assert.equal(comparison.matched,false);
});
test("large gaps respect the maximum trim",()=>{
  const comparison=sectionMatchTrim(section("a",-30,-8),section("b",-10,-2),12);
  assert.equal(comparison.suggestedCandidateTrimDb,-12);
  assert.equal(comparison.matched,false);
});
