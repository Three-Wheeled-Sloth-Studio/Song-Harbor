import test from "node:test";
import assert from "node:assert/strict";
import {compileSectionAutomation,valueAt} from "../src/SectionAutomation.ts";

test("volume transitions at section start or section end inherit across sections",()=>{
  const sections=[
    {start:0,end:20,value:.1,transitionSeconds:10,curve:"smooth"},
    {start:30,end:40,value:1,transitionSeconds:10,curve:"smooth"},
  ];
  const points=compileSectionAutomation([
    {sectionId:"intro",...sections[0]},
    {sectionId:"chorus",...sections[1]}
  ],1,{min:0,max:1});
  assert.equal(valueAt(points,0),1);
  assert.ok(Math.abs(valueAt(points,10)-.1)<1e-9);
  assert.ok(Math.abs(valueAt(points,25)-.1)<1e-9);
  assert.ok(Math.abs(valueAt(points,30)-.1)<1e-9);
  assert.ok(Math.abs(valueAt(points,35)-.55)<1e-9);
  assert.ok(Math.abs(valueAt(points,40)-1)<1e-9);
  assert.equal(valueAt(points,55),1);
});

test("reverb end-anchoring phases out over final seconds while retaining prior effect",()=>{
  const points=compileSectionAutomation([
    {sectionId:"intro",start:0,end:20,value:.28,transitionSeconds:8,curve:"smooth"},
    {sectionId:"chorus",start:32,end:40,value:0,transitionSeconds:8,curve:"smooth"}
  ],0,{min:0,max:1});
  assert.ok(Math.abs(valueAt(points,20)-.28)<1e-9);
  assert.ok(Math.abs(valueAt(points,31)-.28)<1e-9);
  assert.ok(Math.abs(valueAt(points,36)-.14)<1e-9);
  assert.equal(valueAt(points,40),0);
  assert.equal(valueAt(points,50),0);
});
