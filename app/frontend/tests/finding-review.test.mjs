import test from "node:test";
import assert from "node:assert/strict";
import {findingReviewKey,markReviewed,toggleReviewed} from "../src/FindingReview.ts";

test("accepted fix marks only its original finding without clearing other findings",()=>{
  const first=findingReviewKey({kind:"transient",timeSeconds:12.34});
  const other=findingReviewKey({kind:"sibilance",timeSeconds:12.34});
  const initial=new Set([other]);
  const reviewed=markReviewed(initial,first);
  assert.deepEqual([...reviewed].sort(),[first,other].sort());
  assert.deepEqual([...initial],[other]);
  const findings=[{kind:"transient",timeSeconds:12.34},{kind:"sibilance",timeSeconds:12.34},{kind:"noise",timeSeconds:25}];
  const active=findings.filter(f=>!reviewed.has(findingReviewKey(f)));
  assert.equal(active.length,1);
  assert.equal(active[0].kind,"noise");
});
test("review keys survive regenerated finding objects and are independent of detail text",()=>{
  const before={kind:"pumping",timeSeconds:41.556,label:"Old"};
  const after={kind:"pumping",timeSeconds:41.556,label:"Refreshed"};
  assert.equal(findingReviewKey(before),findingReviewKey(after));
  assert.notEqual(findingReviewKey(before),findingReviewKey({kind:"headroom",timeSeconds:41.556}));
});
test("manual reviewed toggle can undo a review",()=>{
  const key="noise:5.00";
  const marked=toggleReviewed(new Set(),key);
  assert.ok(marked.has(key));
  assert.ok(!toggleReviewed(marked,key).has(key));
});
