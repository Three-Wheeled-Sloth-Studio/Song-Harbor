/** Non-destructive, mix-level QC. These are listening candidates, never a diagnosis.
 * Runs on the exact rendered float mix used for WAV packing, before output trim.
 * Analysis uses bounded windows: O(frames + (frames/4096)*2048*log(2048)).
 * No cloud access or modification of audio buffers.
 */
export type AudioFindingKind=
  "headroom"|"transient"|"clip_shape"|"sibilance"|"harshness"|
  "fizz"|"noise"|"phase"|"pumping";
export type AudioFinding={
  kind:AudioFindingKind;
  timeSeconds:number;
  durationSeconds?:number;
  sources?:string[];
  severity:"warning"|"review";
  label:string;
  detail:string;
  /** A listening starting point, not proof of any particular audio artifact. */
  suggestion?:string;
};
export const FINDING_GROUPS:Record<AudioFindingKind,string>={
  headroom:"Levels",clip_shape:"Levels",transient:"Transitions",
  sibilance:"Vocal / high frequency",harshness:"Vocal / high frequency",
  fizz:"Vocal / high frequency",noise:"Quiet passages",
  phase:"Stereo / mono",pumping:"Dynamics"
};
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
const db=(level:number)=>20*Math.log10(Math.max(1e-10,level));
const WINDOW=2048;
const hann=Float64Array.from({length:WINDOW},(_,i)=>.5-.5*Math.cos(2*Math.PI*i/(WINDOW-1)));
const twiddles=Array.from({length:11},(_,stage)=>{
  const size=2**(stage+1),half=size/2;
  return {
    cos:Float64Array.from({length:half},(_,i)=>Math.cos(-2*Math.PI*i/size)),
    sin:Float64Array.from({length:half},(_,i)=>Math.sin(-2*Math.PI*i/size))
  };
});
const makeFrequencyBands=(rate:number)=>{
  const nyquist=rate/2;
  const bounds:[[number,number],[number,number],[number,number],[number,number]]=[
    [150,2200],[2500,4900],[5000,9500],[9500,Math.min(nyquist-100,11500)]
  ];
  return bounds.map(([lo,hi])=>[Math.ceil(lo*WINDOW/rate),Math.min(WINDOW/2-1,Math.floor(hi*WINDOW/rate))]);
};
function fftEnergy(re:Float64Array,im:Float64Array,binBands:number[][]){
  // In-place iterative radix-2 FFT. Reused buffers keep memory bounded.
  for(let i=1,j=0;i<WINDOW;i++){
    let bit=WINDOW>>1;
    for(;j&bit;bit>>=1)j^=bit;
    j^=bit;
    if(i<j){let v=re[i];re[i]=re[j];re[j]=v;v=im[i];im[i]=im[j];im[j]=v;}
  }
  for(let size=2,stage=0;size<=WINDOW;size*=2,stage++){
    const half=size/2;
    const {cos,sin}=twiddles[stage];
    for(let base=0;base<WINDOW;base+=size){
      for(let j=0;j<half;j++){
        const a=base+j,b=a+half;
        const tre=cos[j]*re[b]-sin[j]*im[b],tim=sin[j]*re[b]+cos[j]*im[b];
        re[b]=re[a]-tre;im[b]=im[a]-tim;
        re[a]+=tre;im[a]+=tim;
      }
    }
  }
  let total=0;
  const bands=[0,0,0,0];
  for(let bin=1;bin<WINDOW/2;bin++){
    const energy=re[bin]*re[bin]+im[bin]*im[bin];
    total+=energy;
    for(let k=0;k<binBands.length;k++)if(bin>=binBands[k][0]&&bin<=binBands[k][1])bands[k]+=energy;
  }
  return {total,bands};
}

/** Deterministic offline analyzer. Defaults prioritize fewer, actionable candidates. */
export function inspectRenderedAudio(buffer:AudioLike,outputTrimDb=0,maxFindings=48):AudioFinding[]{
  if(buffer.length===0||buffer.numberOfChannels===0||maxFindings<1)return [];
  const channels=Array.from({length:buffer.numberOfChannels},(_,c)=>buffer.getChannelData(c));
  const rate=buffer.sampleRate;
  const gain=Math.pow(10,outputTrimDb/20);
  const findings:AudioFinding[]=[];
  const lastByKind=new Map<AudioFindingKind,number>();
  const countByKind=new Map<AudioFindingKind,number>();
  const offer=(finding:AudioFinding,cooldown=3)=>{
    const count=countByKind.get(finding.kind)||0;
    if(count>=6||finding.timeSeconds-(lastByKind.get(finding.kind)??-999)<cooldown)return;
    countByKind.set(finding.kind,count+1);
    lastByKind.set(finding.kind,finding.timeSeconds);
    findings.push(finding);
  };
  let highestPeak=0,highestPosition=0,flatTop=0,flatHits=0,flatPosition=0;
  const transientGap=Math.max(1,Math.floor(rate*.12));
  let lastTransient=-transientGap;
  const corrFrame=Math.max(1,Math.round(rate*1.0));
  let corrL=0,corrR=0,corrLR=0;
  let phaseStreak=0,phaseStart=0;
  // 100ms loudness envelope for possible sustained gain oscillation.
  const rmsSize=Math.max(1,Math.floor(rate*.1));
  let rmsSum=0,rmsCount=0;
  const levels:number[]=[];
  for(let i=0;i<buffer.length;i++){
    let peak=0,delta=0,energy=0;
    for(const channel of channels){
      const sample=channel[i]*gain;
      peak=Math.max(peak,Math.abs(sample));
      energy+=sample*sample;
      if(i>0)delta=Math.max(delta,Math.abs((channel[i]-channel[i-1])*gain));
    }
    if(peak>highestPeak){highestPeak=peak;highestPosition=i;}
    if(peak>=.998){flatTop++;if(flatTop===4){flatHits++;flatPosition=i;}}
    else flatTop=0;
    if(i>0&&delta>=.7&&i-lastTransient>=transientGap){
      offer({kind:"transient",timeSeconds:i/rate,severity:"review",
        label:"Abrupt sample transition",
        detail:"A sharp waveform jump could be a click, a drum transient, or deliberate distortion.",
        suggestion:"Loop around this point and compare with the original stems."},.3);
      lastTransient=i;
    }
    rmsSum+=energy/channels.length;rmsCount++;
    if(rmsCount>=rmsSize||i===buffer.length-1){
      levels.push(Math.sqrt(rmsSum/rmsCount));
      rmsSum=0;rmsCount=0;
    }
    if(channels.length>=2){
      const left=channels[0][i],right=channels[1][i];
      corrL+=left*left;corrR+=right*right;corrLR+=left*right;
      if((i+1)%corrFrame===0||i===buffer.length-1){
        const strength=Math.sqrt(corrL*corrR);
        const correlation=strength>1e-6?corrLR/strength:1;
        const loud=Math.sqrt((corrL+corrR)/Math.max(1,2*Math.min(corrFrame,i+1)));
        if(correlation<-.35&&loud>.02){
          if(phaseStreak===0)phaseStart=Math.max(0,(i+1)/rate-1);
          phaseStreak++;
          if(phaseStreak===2)offer({kind:"phase",timeSeconds:phaseStart,
            durationSeconds:phaseStreak,severity:"warning",label:"Potential mono cancellation",
            detail:"Stereo correlation remained negative ("+correlation.toFixed(2)+") across consecutive active windows. Wide intentional effects can cause this.",
            suggestion:"Audition the passage in mono before changing width or stereo effects."},10);
        }else phaseStreak=0;
        corrL=0;corrR=0;corrLR=0;
      }
    }
  }
  if(highestPeak>=.98)offer({kind:"headroom",timeSeconds:highestPosition/rate,
    severity:highestPeak>1?"warning":"review",
    label:highestPeak>1?"Peak exceeds 0 dBFS":"Peak close to digital ceiling",
    detail:"Highest output-trim-adjusted rendered sample: "+db(highestPeak).toFixed(1)+" dBFS.",
    suggestion:"To aim for a -1 dBFS sample-peak ceiling, reduce master output trim by "+Math.max(0,1+db(highestPeak)).toFixed(1)+" dB and re-render. This is not a true-peak measurement."});
  if(flatHits>=4)offer({kind:"clip_shape",timeSeconds:flatPosition/rate,
    severity:"review",label:"Possible flattened waveform peaks",
    detail:flatHits+" repeated flat-topped sample runs near full scale; hard limiting or deliberate distortion may look similar.",
    suggestion:"Audition for crunchy distortion, particularly on loud choruses."});

  // Level-pumping heuristic: find repeated >=6 dB troughs between sustained
  // louder 100-ms blocks. Does not claim to isolate the compressor from music.
  for(let i=2;i<levels.length-2;i++){
    const before=(levels[i-2]+levels[i-1])/2;
    const after=(levels[i+1]+levels[i+2])/2;
    if(before>.07&&after>.07&&levels[i]<Math.min(before,after)*.48){
      const moment=i*.1;
      const previous=lastByKind.get("pumping")??-999;
      if(moment-previous>6){
        const neighbors=levels.slice(Math.max(0,i-18),Math.min(levels.length,i+19));
        let dips=0;
        for(let j=2;j<neighbors.length-2;j++)if(neighbors[j]<.48*Math.min(
          (neighbors[j-2]+neighbors[j-1])/2,(neighbors[j+1]+neighbors[j+2])/2))dips++;
        if(dips>=3)offer({kind:"pumping",timeSeconds:moment,severity:"review",
          label:"Repeated loudness dips",
          detail:"Several rapid level troughs between louder passages; could be sidechain pumping, rhythmic arrangement, or deliberate gating.",
          suggestion:"Audition with compression and ducking bypassed independently."},6);
      }
    }
  }

  // Spectral listening candidates: mono average of 2 channels, 24 kHz maximum,
  // Hann windows and exact energy band fractions. Never claims voice identity.
  const stride=Math.max(1,Math.round(rate/24000));
  const spectralRate=rate/stride;
  const hop=WINDOW*stride;
  const re=new Float64Array(WINDOW),im=new Float64Array(WINDOW);
  const bands=makeFrequencyBands(spectralRate);
  const sustain={sibilance:0,harshness:0,fizz:0,noise:0};
  const start={sibilance:0,harshness:0,fizz:0,noise:0};
  for(let position=0;position+hop<=buffer.length;position+=hop){
    let power=0;
    for(let i=0;i<WINDOW;i++){
      const index=position+i*stride;
      let mixed=0;
      for(const channel of channels)mixed+=channel[index];
      mixed=mixed/channels.length*gain;
      re[i]=mixed*hann[i];im[i]=0;
      power+=mixed*mixed;
    }
    const rms=Math.sqrt(power/WINDOW);
    if(rms<.001){for(const key of Object.keys(sustain) as (keyof typeof sustain)[])sustain[key]=0;continue;}
    const {total,bands:energies}=fftEnergy(re,im,bands);
    const [mid,presence,high,air]=energies.map(e=>e/Math.max(1e-12,total));
    const active={
      sibilance:rms>.018&&high>.44&&high>presence*1.5,
      harshness:rms>.045&&presence>.53&&presence>mid*.85,
      fizz:rms>.028&&air>.28&&high>.38,
      noise:rms<.02&&rms>.003&&high>.37&&air>.13
    };
    const rules=[
      ["sibilance",3,"Sibilance-like high-frequency burst","Energy from roughly 5–9.5 kHz dominates an audible passage; this could be sibilants, cymbals or synth texture.","Compare the vocal stem and try localized de-essing only if voices sound harsh."],
      ["harshness",3,"Strong presence-band emphasis","Persistent 2.5–4.9 kHz energy is unusually dominant; voice, guitar, brass or synth may contribute.","Loop this region and compare targeted EQ without removing desired clarity."],
      ["fizz",3,"Bright high-frequency texture","Persistent near-upper-band energy; could be an encoding/separation artifact or intentional noise, cymbals or distortion.","Solo suspect stems before making corrective changes."],
      ["noise",6,"High-frequency energy in a quiet passage","Sustained high-frequency activity at low overall loudness may indicate hiss, ambience, reverb or separation residue.","Listen to the isolated quiet region and source stems; preserve intended ambience."]
    ] as const;
    for(const [kind,minimum,label,detail,suggestion] of rules){
      if(active[kind]){
        if(sustain[kind]===0)start[kind]=position/rate;
        sustain[kind]++;
        if(sustain[kind]===minimum)offer({kind,timeSeconds:start[kind],
          durationSeconds:minimum*hop/rate,severity:"review",label,
          detail,suggestion},6);
      }else sustain[kind]=0;
    }
  }
  return findings.sort((a,b)=>a.severity===b.severity?a.timeSeconds-b.timeSeconds:
    a.severity==="warning"?-1:1).slice(0,maxFindings);
}
