/** Stage-to-stage QC: dry aligned stems versus effects-rendered mix.
 * This is not a null test or an assertion that intended processing is bad.
 * Only explicit on-demand scans use it; no storage, models, or audio mutation.
 */
import type {AudioFinding} from "./AudioCleanupAnalyzer";

type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
export type StageComparison={
  referenceStage:"aligned-dry-stems";
  outputStage:"effects-rendered-mix";
  windowSeconds:number;
  analyzedSeconds:number;
  findings:AudioFinding[];
};
const EPS=1e-10;
const dB=(v:number)=>20*Math.log10(Math.max(EPS,v));

/** Aligned references must have matching sample rate and time origin.
 * End/tail samples present only in the processed mix are ignored.
 */
export function compareAudioStages(reference:AudioLike,output:AudioLike,
                                   durationSeconds:number,windowSeconds=1):StageComparison{
  if(reference.sampleRate!==output.sampleRate||reference.numberOfChannels!==output.numberOfChannels||
     reference.numberOfChannels<1||reference.numberOfChannels>2)
    throw Error("Stage comparison requires identical sample rate and channel layout");
  if(!Number.isFinite(durationSeconds)||durationSeconds<0||
     !Number.isFinite(windowSeconds)||windowSeconds<.1||windowSeconds>10)
    throw Error("Invalid comparison time range");
  const rate=output.sampleRate, count=reference.numberOfChannels;
  const frames=Math.min(reference.length,output.length,Math.floor(durationSeconds*rate));
  const step=Math.max(1,Math.round(windowSeconds*rate));
  const refs=Array.from({length:count},(_,i)=>reference.getChannelData(i));
  const outs=Array.from({length:count},(_,i)=>output.getChannelData(i));
  const findings:AudioFinding[]=[];
  const last=new Map<string,number>();
  const offer=(kind:AudioFinding["kind"],timeSeconds:number,label:string,detail:string,severity:"warning"|"review"="review",cooldown=5)=>{
    if(findings.length>=24||timeSeconds-(last.get(label)??-1000)<cooldown)return;
    last.set(label,timeSeconds);
    findings.push({kind,severity,timeSeconds,durationSeconds:windowSeconds,label,
      detail,suggestion:"Loop this location and compare dry against processed audio at matched loudness; intentional effects can explain this change."});
  };
  for(let start=0;start+step<=frames;start+=step){
    const stop=start+step, t=start/rate;
    let dry=0,wet=0,dryL=0,dryR=0,wetL=0,wetR=0;
    for(let j=start;j<stop;j++){
      for(let c=0;c<count;c++){
        const a=refs[c][j],b=outs[c][j];
        dry+=a*a;wet+=b*b;
        if(count===2){
          if(c===0){dryL+=a*a;wetL+=b*b;}
          else {dryR+=a*a;wetR+=b*b;}
        }
      }
    }
    const normalizer=step*count;
    const refRms=Math.sqrt(dry/normalizer),outRms=Math.sqrt(wet/normalizer);
    if(refRms<.008)continue; // ignore intentional silence and near-silent regions
    const change=dB(outRms/refRms);
    // Do not flag ordinary 1-5dB musical automation changes.
    if(change < -9&&outRms>.001){
      offer("pumping",t,"Large level reduction since dry stems",
        "Processed RMS is "+change.toFixed(1)+" dB below the aligned dry reference. Ducking, intentional fades, or compression may explain this.");
    }
    if(change > 9&&outRms>.03){
      offer("headroom",t,"Large level increase since dry stems",
        "Processed RMS is +"+change.toFixed(1)+" dB above the aligned dry reference. Check intended gain and peak headroom.");
    }
    if(count===2&&Math.min(dryL,dryR)>.000001*step&&Math.min(wetL,wetR)>.000001*step){
      const dryBalance=dB(Math.sqrt(dryR/dryL));
      const wetBalance=dB(Math.sqrt(wetR/wetL));
      const delta=wetBalance-dryBalance;
      if(Math.abs(delta)>9&&outRms>.02){
        offer("phase",t,"Large L/R balance shift",
          "Processed right-minus-left balance changed by "+(delta>0?"+":"")+delta.toFixed(1)+" dB versus dry stems. Pan choreography may be intentional.", "review",6);
      }
    }
  }
  return {referenceStage:"aligned-dry-stems",outputStage:"effects-rendered-mix",
          windowSeconds,analyzedSeconds:frames/rate,findings};
}
