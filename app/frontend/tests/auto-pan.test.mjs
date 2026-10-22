import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import ts from "typescript";

const source=fs.readFileSync(new URL("../src/AutoPan.ts",import.meta.url),"utf8");
const javascript=ts.transpileModule(source,{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext
}}).outputText;
const {solveAutoPan}=await import("data:text/javascript;base64,"+
  Buffer.from(javascript).toString("base64"));

const stem=(filename,leftPower,rightPower,locked=false)=>({
  filename,leftPower,rightPower,crossPower:0,pan:0,gain:1,locked
});

test("auto-pan reduces imbalance when free complementary stems exist",()=>{
  const result=solveAutoPan([
    stem("locked-vocal",2,1,true),
    stem("free-strings",1,1),
    stem("free-drums",1,1)
  ]);
  assert.ok(Math.abs(result.predictedDb)<Math.abs(result.beforeDb));
  assert.ok(result.adjustments.every(item=>item.filename!=="locked-vocal"));
  assert.ok(result.adjustments.every(item=>Math.abs(item.pan)<=.241));
  assert.ok(result.adjustments.every(item=>Math.abs(item.gainDb)<=.351));
});

test("solver does not move protected stems or conceal unachievable target",()=>{
  const result=solveAutoPan([stem("vocal",3,1,true)]);
  assert.equal(result.adjustments.length,0);
  assert.equal(result.reached,false);
  assert.match(result.reason,/No eligible/);
});

test("explicit gain is protected even if a stem is free to pan",()=>{
  const fixedGain={...stem("balanced",1,1),gainLocked:true};
  const result=solveAutoPan([stem("vocal",3,1,true),fixedGain]);
  assert.ok(result.adjustments.every(item=>item.gainDb===0));
});

test("silent or absent stems do not introduce non-finite corrections",()=>{
  const result=solveAutoPan([stem("silence",0,0),stem("audible",1,1)]);
  assert.ok(Number.isFinite(result.predictedDb));
  assert.equal(result.reached,true);
});
