/** Deterministic synthetic acoustic controls. These are not real music benchmarks.
 * Each truth event is an audible attack-envelope observation, not an AI label.
 */
export const sampleRate=24000;
export function fixture(id,category,seconds,producer,expectedEvents=[]){
  const length=Math.round(seconds*sampleRate);
  const arrays=Array.from({length:2},(_,channel)=>Float32Array.from({length},(_,i)=>producer(i/sampleRate,channel)));
  return {id,category,expectedEvents,
    audio:{sampleRate,length,numberOfChannels:2,getChannelData(channel){return arrays[channel];}}};
}
const sine=(t,hz)=>Math.sin(2*Math.PI*hz*t);
function onset(t,start,rise,frequency=440){
  const age=t-start;
  return age<0?0:.28*Math.min(1,age/rise)*sine(t,frequency);
}
/** Individual controls are narrow by design; report failures without hiding them. */
export function attackRiseFixtures(){
  return [
    fixture("slow-attack-mono","positive",2,t=>onset(t,.5,.085),[{timeSeconds:.51}]),
    fixture("slow-attack-antiphase","positive",2,(t,c)=>onset(t,.5,.085)*(c===0?1:-1),[{timeSeconds:.51}]),
    fixture("sharp-percussion-onset","sharp-control",2,t=>onset(t,.5,.004)),
    fixture("industrial-distortion-onset","industrial-control",2,t=>Math.tanh(8*onset(t,.5,.003))*.4),
    fixture("silence","silence-control",2,()=>0),
    fixture("sustained-low-tone","sustain-control",2,t=>.18*sine(t,440)),
    fixture("intentional-pad-envelope","soft-envelope-control",2,t=>onset(t,.5,.09)),
    fixture("bright-cymbal-like-burst","cymbal-control",2,t=>{
      const age=t-.5;
      if(age<0)return 0;
      const noise=Math.sin(2*Math.PI*6337*t)+.6*Math.sin(2*Math.PI*8711*t);
      return .13*Math.exp(-age*13)*noise;
    }),
    fixture("wide-reverb-like-tail","spatial-tail-control",2,(t,c)=>{
      const age=t-.5;
      return age<0?0:.11*Math.exp(-age*3)*sine(t,(c===0?440:443));
    })
  ];
}
