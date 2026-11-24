import {inspectRenderedAudio,type AudioFinding} from "./AudioCleanupAnalyzer.ts";
import {spectralStationarity} from "./SpectralStationarity.ts";

export type SourceMetrics={peakDbfs:number;rmsDbfs:number;dcPercent:number;stereoCorrelation:number|null;sideToMidDb:number|null;
  spectralConsistency:number|null;sampledSpectralWindows:number};
export type StemIntegrityResult={key:string;filename:string;startSeconds:number;findings:readonly AudioFinding[];metrics:SourceMetrics};
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
const db=(value:number)=>20*Math.log10(Math.max(1e-10,value));

/** Bounded PCM sampling: level, DC and stereo measurements are indicators, not diagnoses. */
export function sourceMetrics(buffer:AudioLike):SourceMetrics{
  const channels=Array.from({length:Math.min(2,buffer.numberOfChannels)},(_,i)=>buffer.getChannelData(i));
  if(!channels.length||!buffer.length)return {peakDbfs:-200,rmsDbfs:-200,dcPercent:0,stereoCorrelation:null,sideToMidDb:null,
    spectralConsistency:null,sampledSpectralWindows:0};
  const stride=Math.max(1,Math.floor(buffer.length/120000));
  let peak=0,energy=0,mean=0,left=0,right=0,cross=0,mid=0,side=0,count=0;
  for(let i=0;i<buffer.length;i+=stride){
    const a=channels[0][i],b=channels.length>1?channels[1][i]:a;
    if(!Number.isFinite(a)||!Number.isFinite(b))throw Error("Nonfinite source samples");
    peak=Math.max(peak,Math.abs(a),Math.abs(b));
    energy+=(a*a+b*b)/2;mean+=(a+b)/2;
    left+=a*a;right+=b*b;cross+=a*b;
    mid+=(a+b)*(a+b)/4;side+=(a-b)*(a-b)/4;count++;
  }
  const stereo=channels.length>1&&left>1e-12&&right>1e-12;
  const spectral=spectralStationarity(buffer);
  return {peakDbfs:db(peak),rmsDbfs:db(Math.sqrt(energy/count)),dcPercent:100*mean/count,
    stereoCorrelation:stereo?Math.max(-1,Math.min(1,cross/Math.sqrt(left*right))):null,
    sideToMidDb:stereo?10*Math.log10(Math.max(1e-12,side)/Math.max(1e-12,mid)):null,
    spectralConsistency:spectral.similarity,sampledSpectralWindows:spectral.sampledWindows};
}

/** Read-only per-source analysis; timestamps are expressed on the song timeline. */
export function scanStemSource(key:string,filename:string,startSeconds:number,
  buffer:AudioLike,maxFindings=12):StemIntegrityResult{
  if(!Number.isFinite(startSeconds)||startSeconds<0)throw Error("Invalid source timeline offset");
  const findings=inspectRenderedAudio(buffer,0,maxFindings).map(finding=>({
    ...finding,timeSeconds:finding.timeSeconds+startSeconds,sources:[key]
  }));
  return {key,filename,startSeconds,findings,metrics:sourceMetrics(buffer)};
}
