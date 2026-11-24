import test from "node:test";
import assert from "node:assert/strict";
import {spectralStationarity} from "../src/SpectralStationarity.ts";

function mono(samples,rate=24000){
  return {length:samples.length,sampleRate:rate,numberOfChannels:1,getChannelData(){return samples;}};
}
const rate=24000,duration=12,length=rate*duration;

test("sustained synthesizer is highly consistent but not labeled a defect",()=>{
  const source=Float32Array.from({length},(_,i)=>.25*Math.sin(2*Math.PI*600*i/rate));
  const original=source.slice();
  const result=spectralStationarity(mono(source));
  assert.ok(result.similarity>.95,JSON.stringify(result));
  assert.equal(result.sampledWindows,24);
  assert.equal(result.changes.length,0);
  assert.deepEqual(source,original);
});

test("changing musical notes have less spectral consistency than a fixed drone",()=>{
  const fixed=Float32Array.from({length},(_,i)=>.2*Math.sin(2*Math.PI*600*i/rate));
  const moving=Float32Array.from({length},(_,i)=>{
    const hz=[300,600,1200,2400][Math.floor(i/rate)%4];
    return .2*Math.sin(2*Math.PI*hz*i/rate);
  });
  const a=spectralStationarity(mono(fixed)),b=spectralStationarity(mono(moving));
  assert.ok(b.similarity<a.similarity-.08,JSON.stringify({a,b}));
  assert.ok(b.changes.length>0,"localized change evidence is available for seeking");
  assert.ok(b.changes.every(item=>item.timeSeconds>=0&&item.timeSeconds<=duration));
});

test("silence and short clips return no classification",()=>{
  assert.equal(spectralStationarity(mono(new Float32Array(length))).similarity,null);
  assert.equal(spectralStationarity(mono(new Float32Array(rate))).similarity,null);
  assert.deepEqual(spectralStationarity(mono(new Float32Array(length))).changes,[]);
});

test("industrial-style distortion and gating remain descriptive measurements",()=>{
  const source=Float32Array.from({length},(_,i)=>{
    const carrier=Math.sin(2*Math.PI*150*i/rate)+.6*Math.sin(2*Math.PI*2400*i/rate);
    const gated=(Math.floor(i/(rate*.125))%4)===0?0:1;
    return gated*.28*Math.tanh(5*carrier);
  });
  const result=spectralStationarity(mono(source));
  assert.ok(result.similarity!==null&&result.similarity>=0&&result.similarity<=1);
  assert.ok(!("severity" in result),"no defect verdict is derived from deliberately distorted music");
});
