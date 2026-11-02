import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";

// GroupAutomation imports AutoPan. Compile both with TypeScript's NodeNext module
// resolution into a temporary in-memory data URL by replacing the import reference.
const auto=fs.readFileSync(new URL("../src/AutoPan.ts",import.meta.url),"utf8");
const group=fs.readFileSync(new URL("../src/GroupAutomation.ts",import.meta.url),"utf8");
const options={compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}};
const jsAuto=ts.transpileModule(auto,options).outputText;
const autoUrl="data:text/javascript;base64,"+Buffer.from(jsAuto).toString("base64");
const jsGroup=ts.transpileModule(group.replace(
  /from ["']\.\/AutoPan["'];?/,
  'from "'+autoUrl+'";'
),options).outputText;
const {solveGroupGain,solveGroupPan}=await import(
  "data:text/javascript;base64,"+Buffer.from(jsGroup).toString("base64")
);
const member=(filename,baselinePower,currentPower,gainLocked=false)=>({
  filename,baselinePower,currentPower,gainDb:0,gainLocked,active:true
});

test("boosted locked drum is compensated only by free taiko",()=>{
  const result=solveGroupGain([
    member("Drums",1,1.5,true),member("Taiko",2,2)
  ]);
  assert.ok(result.reached);
  assert.deepEqual(result.adjustments.map(x=>x.filename),["Taiko"]);
  assert.ok(result.adjustments[0].changeDb<0);
  assert.ok(Math.abs(result.predictedPower-3)<1e-9);
});

test("unrelated stem is outside group and untouched",()=>{
  const result=solveGroupGain([member("Drums",1,1.2,true),member("Taiko",1,1)]);
  assert.ok(result.adjustments.every(x=>x.filename!=="Vocals"));
});

test("all-locked group returns useful residual rather than changing it",()=>{
  const result=solveGroupGain([member("Drums",1,2,true),member("Taiko",1,1,true)]);
  assert.equal(result.adjustments.length,0);
  assert.equal(result.reached,false);
  assert.ok(result.residualDb>0);
});

test("silent members do not cause unbounded amplification",()=>{
  const result=solveGroupGain([member("Drums",0,0),member("Taiko",0,0)]);
  assert.equal(result.adjustments.length,0);
  assert.ok(Number.isFinite(result.residualDb));
});

test("large boosts produce bounded correction and explicit unmet target",()=>{
  const result=solveGroupGain([member("Drums",1,100,true),member("Taiko",10,10)]);
  assert.equal(result.reached,false);
  assert.ok(result.adjustments.every(x=>Math.abs(x.changeDb)<=6));
});

test("inactive members do not contribute to group baseline",()=>{
  const absent={...member("Muted",100,100),active:false};
  const result=solveGroupGain([member("Drums",1,1,true),member("Taiko",2,2),absent]);
  assert.equal(result.baselinePower,3);
  assert.equal(result.adjustments.length,0);
});

test("duplicate aliases and invalid powers reject deterministically",()=>{
  assert.throws(()=>solveGroupGain([member("Drums",1,1),member("drums",1,1)]));
  assert.throws(()=>solveGroupGain([member("Drums",-1,1)]));
});

test("group pan reuses existing solver and protects explicit pan",()=>{
  const result=solveGroupPan([
    {filename:"Drums",leftPower:2,rightPower:1,crossPower:0,pan:0,gain:1,locked:true},
    {filename:"Taiko",leftPower:1,rightPower:1,crossPower:0,pan:0,gain:1,locked:false}
  ]);
  assert.ok(result.adjustments.every(x=>x.filename!=="Drums"));
});
