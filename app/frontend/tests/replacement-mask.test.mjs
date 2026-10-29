import test from "node:test";
import assert from "node:assert/strict";
import {replacementCurve,replacementGainAt} from "../src/ReplacementMasks.ts";

test("replacement mutes only its time range with short reversible boundary ramps",()=>{
  const masks=[{replacement_track_id:"trk_new",source_track_id:"trk_orig",
    source_filename:"Bass.wav",start_seconds:12,end_seconds:18,fade_seconds:.05}];
  assert.equal(replacementGainAt(masks,10),1);
  assert.equal(replacementGainAt(masks,12),1);
  assert.ok(replacementGainAt(masks,12.025)>0&&replacementGainAt(masks,12.025)<1);
  assert.equal(replacementGainAt(masks,12.06),0);
  assert.equal(replacementGainAt(masks,17),0);
  assert.equal(replacementGainAt(masks,18),1);
  assert.equal(replacementGainAt([],15),1);
  assert.deepEqual(replacementCurve([]),[{time:0,value:1}]);
  assert.equal(replacementCurve(masks).at(-1).value,1);
});

test("overlapping replacements preserve complete muting and do not change input",()=>{
  const a={replacement_track_id:"a",source_track_id:"src",source_filename:"Bass.wav",
    start_seconds:4,end_seconds:12,fade_seconds:.05};
  const b={...a,replacement_track_id:"b",start_seconds:8,end_seconds:16};
  const before=JSON.stringify([a,b]);
  assert.equal(replacementGainAt([a,b],10),0);
  assert.equal(replacementGainAt([a,b],12),0);
  assert.equal(replacementGainAt([b],5),1);
  assert.equal(JSON.stringify([a,b]),before);
});

test("relative original-stem gain preserves 10% without overwriting script envelope",()=>{
  const original={replacement_track_id:"cello",source_track_id:"bass",
    source_filename:"Bass.wav",start_seconds:12,end_seconds:18,fade_seconds:.05,original_gain:.10};
  const masks=[original];
  assert.equal(replacementGainAt(masks,11),1);
  assert.equal(replacementGainAt(masks,13),.1);
  assert.ok(Math.abs(replacementGainAt(masks,12.025)-.55)<1e-8);
  assert.equal(replacementGainAt(masks,19),1);
  assert.equal(replacementGainAt([{...original,original_gain:1}],14),1);
  assert.equal(replacementGainAt([{...original,original_gain:0}],14),0);
  assert.equal(replacementGainAt([{...original}],14),0); // legacy masks default to Replace=0
  const savedScriptGain=.65;
  assert.ok(Math.abs(savedScriptGain*replacementGainAt(masks,13)-.065)<1e-8);
  assert.deepEqual(masks[0],original);
});

test("overlapping partial replacements multiply relative gains without affecting unrelated regions",()=>{
  const first={replacement_track_id:"a",source_track_id:"src",source_filename:"Bass.wav",start_seconds:4,end_seconds:12,fade_seconds:.05,original_gain:.25};
  const second={...first,replacement_track_id:"b",start_seconds:8,end_seconds:16,original_gain:.5};
  assert.equal(replacementGainAt([first,second],10),.125);
  assert.equal(replacementGainAt([first,second],3),1);
  assert.equal(replacementGainAt([first,second],14),.5);
});
