import test from "node:test";
import assert from "node:assert/strict";
import {matchEvents,summarizeArtifactCases} from "./artifact-evaluation.mjs";
import {attackRiseFixtures} from "./artifact-fixtures.mjs";
import {runAttackRiseBenchmark} from "./run-artifact-benchmark.mjs";

test("one-to-one matches prevent duplicate detection credit",()=>{
  const m=matchEvents([{timeSeconds:1},{timeSeconds:1.01}],[{timeSeconds:1.005}],.03);
  assert.equal(m.tp,1);assert.equal(m.fp,1);assert.equal(m.fn,0);
});
test("localization tolerance rejects mismatched timestamps",()=>{
  assert.deepEqual(matchEvents([{timeSeconds:.2}],[{timeSeconds:.5}],.05),
    {tp:0,fp:1,fn:1,localizationErrorsSeconds:[]});
});
test("negative controls count case-level false positives separately",()=>{
  const summary=summarizeArtifactCases([
    {id:"a",category:"negative",expectedEvents:[],observations:[{timeSeconds:1},{timeSeconds:1.5}]},
    {id:"b",category:"negative",expectedEvents:[],observations:[]},
    {id:"c",category:"positive",expectedEvents:[{timeSeconds:.5}],observations:[{timeSeconds:.51}]}
  ],.05);
  assert.equal(summary.totals.tp,1);assert.equal(summary.totals.fp,2);
  assert.equal(summary.totals.negativeCases,2);
  assert.equal(summary.totals.negativeCasesWithFalsePositives,1);
  assert.equal(summary.totals.negativeCaseFalsePositiveRate,.5);
  assert.equal(summary.categories.negative.fp,2);
});
test("undefined precision and recall remain null rather than fabricated 100%",()=>{
  const summary=summarizeArtifactCases([{id:"silent",category:"negative",expectedEvents:[],observations:[]}]);
  assert.equal(summary.totals.precision,null);assert.equal(summary.totals.recall,null);
  assert.equal(summary.totals.f1,null);
});
test("malformed timing tolerance is rejected",()=>{
  assert.throws(()=>matchEvents([],[],-1),RangeError);
});
test("fixtures are independently generated and deterministic",()=>{
  const a=attackRiseFixtures(),b=attackRiseFixtures();
  assert.ok(a.length>=8);
  assert.deepEqual(a.map(x=>x.id),b.map(x=>x.id));
  assert.deepEqual(a[0].audio.getChannelData(0),b[0].audio.getChannelData(0));
  assert.notEqual(a[0].audio.getChannelData(0),b[0].audio.getChannelData(0));
});
test("benchmark produces inspectable per-case results with synthetic provenance",()=>{
  const result=runAttackRiseBenchmark();
  assert.equal(result.schemaVersion,1);
  assert.equal(result.kind,"audible-artifact-evaluation");
  assert.equal(result.method,"attack-rise-rms-v1");
  assert.equal(result.dataset,"deterministic-synthetic-v1");
  assert.equal(result.cases.length,attackRiseFixtures().length);
  assert.equal(result.totals.cases,result.cases.length);
  assert.ok(result.cases.some(x=>x.category==="soft-envelope-control"));
  assert.equal(result.totals.tp+result.totals.fn,2);
  assert.ok(result.totals.fp>=0);
});
