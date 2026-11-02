import test from "node:test";
import assert from "node:assert/strict";
import {solveGroupGain} from "../src/GroupGain.ts";
test("boosted drums stay fixed and taiko compensates for group loudness",()=>{
  const members=[
    {filename:"Drums.wav",baselinePower:1,currentPower:10**(.75/10),locked:true},
    {filename:"Taiko.wav",baselinePower:1,currentPower:1,locked:false}
  ];
  const result=solveGroupGain(members);
  assert.equal(result.adjustments.length,1);
  assert.equal(result.adjustments[0].filename,"Taiko.wav");
  assert.ok(result.adjustments[0].gainDb<0);
  assert.ok(Math.abs(result.predictedDb)<.01);
});
test("protected stems cannot be adjusted",()=>{
  const r=solveGroupGain([{filename:"Drums",baselinePower:1,currentPower:2,locked:true}]);
  assert.deepEqual(r.adjustments,[]);
  assert.equal(r.reached,false);
});
test("bounded correction cannot overcompensate a dominant locked stem",()=>{
  const result=solveGroupGain([
    {filename:"Drums",baselinePower:1,currentPower:5,locked:true},
    {filename:"Taiko",baselinePower:1,currentPower:1,locked:false}
  ]);
  assert.ok(result.adjustments[0].gainDb>=-4-1e-8);
  assert.equal(result.reached,false);
});
test("unchanged group requires no compensation",()=>{
  const r=solveGroupGain([{filename:"A",baselinePower:1,currentPower:1,locked:false},
    {filename:"B",baselinePower:.5,currentPower:.5,locked:false}]);
  assert.deepEqual(r.adjustments,[]);
  assert.equal(r.reached,true);
});
