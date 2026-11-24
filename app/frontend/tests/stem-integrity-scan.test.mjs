import test from "node:test";
import assert from "node:assert/strict";
import {scanStemSource} from "../src/StemIntegrityScan.ts";

function buffer(channels,rate=48000){
  return {length:channels[0].length,sampleRate:rate,numberOfChannels:channels.length,
    getChannelData(index){return channels[index];}};
}

test("all-stem source observations retain identity and song timeline offset",()=>{
  const samples=new Float32Array(48000);
  samples[12000]=1;samples[12001]=-1;
  const original=samples.slice();
  const result=scanStemSource("Vocals-left","vocals.wav",12.5,buffer([samples]));
  assert.equal(result.key,"Vocals-left");
  assert.equal(result.filename,"vocals.wav");
  assert.ok(result.findings.some(item=>item.kind==="transient"&&item.timeSeconds>=12.5));
  assert.ok(result.findings.every(item=>item.sources?.[0]==="Vocals-left"));
  assert.deepEqual(samples,original,"scan must not change source PCM");
});

test("silent source yields no findings and bad offsets are rejected",()=>{
  const source=buffer([new Float32Array(48000)]);
  assert.deepEqual(scanStemSource("Other","other.wav",0,source).findings,[]);
  assert.throws(()=>scanStemSource("Other","other.wav",-1,source),/offset/);
});
