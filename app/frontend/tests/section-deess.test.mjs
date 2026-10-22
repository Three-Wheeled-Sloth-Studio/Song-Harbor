import test from "node:test";
import assert from "node:assert/strict";
import {build} from "esbuild";
import {resolve} from "node:path";
const artifact=await build({entryPoints:[resolve("app/frontend/src/SectionDynamics.ts")],
  bundle:true,platform:"node",format:"esm",target:"es2022",write:false});
const engine=await import("data:text/javascript;base64,"+Buffer.from(artifact.outputFiles[0].text).toString("base64"));
const fixed=(value)=>[{time:0,value}];
const makeBuffer=(frequency,amplitude=.35,seconds=1)=>{
  const sampleRate=24000,length=sampleRate*seconds,channels=2;
  const values=Float32Array.from({length},(_,i)=>amplitude*Math.sin(2*Math.PI*frequency*i/sampleRate));
  return {sampleRate,length,numberOfChannels:channels,getChannelData:()=>values};
};
const settings=(maxReduction)=>({
  frequency:fixed(6500),q:fixed(2),threshold:fixed(-45),maxReduction:fixed(maxReduction)
});
test("sibilant HF triggers reduction of a targeted frequency band",()=>{
  const points=engine.makeDeEssEnvelope([makeBuffer(7200)],settings(6),1);
  assert.ok(points.length>20);
  assert.ok(points.some(item=>item.value<-.4),"High-frequency detector must trigger");
  assert.ok(points.every(item=>item.value>=-6&&item.value<=0),"Respect maximum reduction");
});
test("ordinary low-frequency vocal body does not trigger aggressive de-essing",()=>{
  const points=engine.makeDeEssEnvelope([makeBuffer(350)],settings(6),1);
  assert.ok(Math.min(...points.map(x=>x.value))>-.6);
});
test("zero maximum reduction and zero input level leave the audio neutral",()=>{
  const original=makeBuffer(7200);
  const neutral=engine.makeDeEssEnvelope([original],settings(0),1);
  assert.ok(neutral.every(x=>x.value===0));
  const muted=engine.makeDeEssEnvelope([original],settings(6),0);
  assert.ok(muted.every(x=>x.value===0));
});
test("split L/R channels share a bounded detector and do not require six stems",()=>{
  const signal=makeBuffer(7200);
  const points=engine.makeDeEssEnvelope([signal,signal],settings(6),1);
  assert.ok(points.some(x=>x.value<0));
  assert.ok(points.at(-1).time<=1.001);
});
