import test from "node:test";
import assert from "node:assert/strict";
import {stemTimelineStart,stemPlaybackWindow} from "../src/StemTiming.ts";
test("taiko follows primary drums without echoing",()=>{
  assert.equal(stemTimelineStart(0,.2),.2);
  assert.deepEqual(stemPlaybackWindow(0,.2,20),{delay:.2,bufferOffset:0});
});
test("seek after delay skips precisely to the correct source sample",()=>{
  assert.deepEqual(stemPlaybackWindow(5,.2,20),{delay:0,bufferOffset:4.8});
  assert.deepEqual(stemPlaybackWindow(.1,.2,20),{delay:.1,bufferOffset:0});
  assert.equal(stemPlaybackWindow(20.2,.2,20),null);
});
test("offset applies after a positioned clip start",()=>{
  assert.equal(stemTimelineStart(4,.15),4.15);
  assert.ok(Math.abs(stemPlaybackWindow(4,4.15,1).delay-.15)<1e-8);
});
test("negative and excessive offsets rejected",()=>{
  for(const value of [-.01,.501,NaN,Infinity])
    assert.throws(()=>stemTimelineStart(0,value),/offset/);
});
