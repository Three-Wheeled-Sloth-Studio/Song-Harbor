import {spawnSync} from "node:child_process";
import {resolve} from "node:path";
import {inspectRenderedAudio} from "../app/frontend/src/AudioCleanupAnalyzer.ts";

const paths=process.argv.slice(2).map(path=>resolve(path));
if(!paths.length){
  process.stderr.write("Usage: node --experimental-strip-types scripts/run-real-audio-diagnostics.mjs <audio> [...]\n");
  process.exit(2);
}

function decode(path){
  const rate=24000,channels=2;
  const run=spawnSync("ffmpeg",["-v","error","-i",path,"-map","0:a:0","-ar",String(rate),
    "-ac",String(channels),"-f","f32le","-acodec","pcm_f32le","pipe:1"],
  {encoding:null,maxBuffer:1024*1024*512,windowsHide:true});
  if(run.error)throw run.error;
  if(run.status!==0)throw new Error(`FFmpeg failed for ${path}: ${run.stderr.toString("utf8")}`);
  const frames=Math.floor(run.stdout.length/(4*channels));
  const interleaved=new Float32Array(run.stdout.buffer,run.stdout.byteOffset,frames*channels);
  const data=Array.from({length:channels},()=>new Float32Array(frames));
  for(let frame=0;frame<frames;frame++)for(let channel=0;channel<channels;channel++)
    data[channel][frame]=interleaved[frame*channels+channel];
  return {length:frames,sampleRate:rate,numberOfChannels:channels,getChannelData:c=>data[c]};
}

const results=[];
for(const path of paths){
  const started=performance.now();
  const audio=decode(path);
  const findings=inspectRenderedAudio(audio,0,100);
  results.push({path,sampleRate:audio.sampleRate,channels:audio.numberOfChannels,
    durationSeconds:audio.length/audio.sampleRate,
    processingSeconds:(performance.now()-started)/1000,findings});
}
process.stdout.write(JSON.stringify({schemaVersion:1,kind:"song-harbor-real-audio-diagnostics",
  generatedAt:new Date().toISOString(),results},null,2)+"\n");
