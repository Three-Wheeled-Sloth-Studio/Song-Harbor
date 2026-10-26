/** Bounded, frequency-aware evidence ranking for a flagged sound.
 * Operates on already decoded source channels; never claims causal isolation.
 * Overlapping spectral energy and separation bleed are explicit uncertainty.
 */
import type {AudioFindingKind} from "./AudioCleanupAnalyzer";

export type AttributionInput={
  name:string;startSeconds:number;level:number;
  buffer:Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
};
export type AttributionEvidence={name:string;band:string;relativeShare:number;scoreDb:number;confidence:"low"|"moderate"};
export type AttributionResult={band:string;ranked:AttributionEvidence[];uncertain:boolean};

const BAND:Partial<Record<AudioFindingKind,{lo:number;hi:number;label:string}>>={
  harshness:{lo:2500,hi:4900,label:"2.5–4.9 kHz"},
  sibilance:{lo:5000,hi:9500,label:"5–9.5 kHz"},
  fizz:{lo:7500,hi:11500,label:"7.5–11.5 kHz"},
  noise:{lo:6000,hi:11500,label:"6–11.5 kHz"},
  signal_audit:{lo:4000,hi:11500,label:"4–11.5 kHz"}
};
const EPS=1e-12;
const WINDOW=256;

/** Goertzel power estimated in a short fixed frequency band at sparse offsets.
 * The identical normalized procedure is applied to every source.
 */
export function bandEvidence(inputs:readonly AttributionInput[],
                             kind:AudioFindingKind,timeSeconds:number,
                             durationSeconds=0.25):AttributionResult{
  const band=BAND[kind]||{lo:55,hi:Math.max(kind==="phase"?3000:1800,1800),
    label:kind==="phase"?"55–3000 Hz":"55–1800 Hz"};
  const end=Math.max(timeSeconds+0.15,timeSeconds+Math.min(durationSeconds,1));
  const scored=inputs.map(input=>{
    const rate=input.buffer.sampleRate;
    const low=Math.max(1,band.lo),high=Math.min(rate*.46,band.hi);
    if(input.level<=0||low>=high)return {name:input.name,score:0};
    const from=Math.max(0,Math.round((timeSeconds-input.startSeconds)*rate));
    const to=Math.min(input.buffer.length,Math.round((end-input.startSeconds)*rate));
    if(to-from<WINDOW)return {name:input.name,score:0};
    const channels=Array.from({length:input.buffer.numberOfChannels},(_,i)=>input.buffer.getChannelData(i));
    const samples=Math.min(4,Math.max(1,Math.floor((to-from)/WINDOW)));
    const probes=7;
    let total=0;
    for(let k=0;k<samples;k++){
      const pos=from+Math.floor(k*(to-from-WINDOW)/Math.max(1,samples-1));
      for(const channel of channels){
        for(let b=0;b<probes;b++){
          const freq=low+(b+.5)*(high-low)/probes;
          const step=2*Math.PI*freq/rate;
          let re=0,im=0;
          for(let i=0;i<WINDOW;i++){
            const value=channel[pos+i]*(.5-.5*Math.cos(2*Math.PI*i/(WINDOW-1)));
            re+=value*Math.cos(step*i);
            im+=value*Math.sin(step*i);
          }
          total+=(re*re+im*im)/(WINDOW*WINDOW);
        }
      }
    }
    return {name:input.name,score:total*input.level*input.level/Math.max(1,samples*channels.length)};
  }).filter(x=>x.score>EPS).sort((a,b)=>b.score-a.score);
  const sum=scored.reduce((n,x)=>n+x.score,0);
  const ranked=scored.slice(0,3).map(x=>({
    name:x.name,band:band.label,relativeShare:x.score/Math.max(EPS,sum),
    scoreDb:Math.round(10*Math.log10(Math.max(EPS,x.score))*10)/10,
    confidence:(x.score/sum>.65?"moderate":"low") as "moderate"|"low"
  }));
  return {band:band.label,ranked,uncertain:ranked.length===0||ranked[0].relativeShare<.7};
}
