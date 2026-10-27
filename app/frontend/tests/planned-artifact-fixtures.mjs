/**
 * Planned-method synthetic signal library. Describes expected acoustic events,
 * but does not pretend that the corresponding detector has been implemented.
 * Reproducible, independent of ML / provenance tests.
 */
const rate=24000;
export function makeSignal(id,category,seconds,render,annotations=[]){
  const length=Math.round(seconds*rate);
  const channels=Array.from({length:2},(_,c)=>Float32Array.from({length},(_,i)=>render(i/rate,c)));
  return {id,category,annotations,audio:{length,numberOfChannels:2,sampleRate:rate,getChannelData:c=>channels[c]}};
}
const wave=(t,f)=>Math.sin(2*Math.PI*f*t);
function tail(t,start,decay,channel=0){
  const age=t-start;
  return age<0?0:.28*Math.exp(-decay*age)*wave(t,channel?443:440);
}
export function plannedMethodFixtures(){
  return {
    reverb:[
      makeSignal("natural-decay","reverb-negative",3,(t,c)=>tail(t,.5,3,c)),
      makeSignal("hard-tail-cut","reverb-positive",3,(t,c)=>t<1.15?tail(t,.5,3,c):0,
        [{kind:"tail_cut",timeSeconds:1.15}]),
      makeSignal("stalled-tail","reverb-positive",3,(t,c)=>{
        const age=t-.5;
        return age<0?0:.28*Math.exp(-3*Math.min(age,.3))*wave(t,c?443:440);
      },[{kind:"tail_stall",timeSeconds:.8}]),
      makeSignal("intentional-gated-reverb","reverb-negative",3,(t,c)=>t<1.15?tail(t,.5,3,c):0)
    ],
    spatial:[
      makeSignal("aligned-stereo","phase-negative",3,t=>.2*wave(t,440)),
      makeSignal("antiphase-stereo","phase-positive",3,(t,c)=>(c?-.2:.2)*wave(t,440),
        [{kind:"mono_cancellation",timeSeconds:.5}]),
      makeSignal("intentional-wide-spatial","phase-negative",3,(t,c)=>.14*wave(t,c?443:440))
    ],
    spectral:[
      makeSignal("harmonic-tone","spectral-negative",3,t=>.2*wave(t,440)+.04*wave(t,880)),
      makeSignal("strong-upper-band-line","spectral-review",3,t=>.15*wave(t,6200),
        [{kind:"upper_band_line",timeSeconds:.5}]),
      makeSignal("deliberate-industrial-harmonics","spectral-negative",3,t=>.22*Math.tanh(8*wave(t,330)))
    ],
    vocal:[
      makeSignal("breath-like-noise","vocal-control",3,t=>{
        const age=t-.7;
        const window=age>=0&&age<.17?Math.sin(Math.PI*age/.17):0;
        return window*.02*(wave(t,7200)+wave(t,5701));
      })
    ]
  };
}
