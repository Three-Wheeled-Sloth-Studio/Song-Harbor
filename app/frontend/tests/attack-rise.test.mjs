import test from 'node:test';
import assert from 'node:assert/strict';
import {inspectAttackRise} from '../src/AttackRiseDiagnostic.ts';
const rate=24000;
function make(seconds,fn,channels=2){const length=Math.round(seconds*rate);const data=Array.from({length:channels},(_,c)=>Float32Array.from({length},(_,i)=>fn(i/rate,c)));return {length,sampleRate:rate,numberOfChannels:channels,getChannelData:c=>data[c]};}
const tone=(t,start,rise)=>t<start?0:.28*Math.min(1,(t-start)/rise)*Math.sin(2*Math.PI*440*t);
test('isolated slow attack is located and measured',()=>{const events=inspectAttackRise(make(2,t=>tone(t,.5,.085)));assert.ok(events.some(x=>Math.abs(x.timeSeconds-.51)<.035&&x.riseMs>=35));});
test('sharp attack is not mislabeled',()=>assert.deepEqual(inspectAttackRise(make(2,t=>tone(t,.5,.004))),[]));
test('silence has no observation',()=>assert.deepEqual(inspectAttackRise(make(2,()=>0)),[]));
test('sustained tone from beginning has no isolated onset',()=>assert.deepEqual(inspectAttackRise(make(2,t=>.18*Math.sin(2*Math.PI*440*t)),6),[]));
test('distorted industrial bass sharp onset stays unflagged',()=>assert.deepEqual(inspectAttackRise(make(2,t=>Math.tanh(8*tone(t,.5,.003))*.4)),[]));
test('wide antiphase stereo does not cancel detection',()=>{const events=inspectAttackRise(make(2,(t,c)=>tone(t,.5,.085)*(c===0?1:-1)));assert.ok(events.length>0);});
test('input samples remain unchanged',()=>{const a=make(2,t=>tone(t,.5,.085));const prior=a.getChannelData(0).slice();inspectAttackRise(a);assert.deepEqual(a.getChannelData(0),prior);});
