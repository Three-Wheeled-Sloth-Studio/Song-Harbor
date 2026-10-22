/** Local, non-destructive acoustic signal screening.
 * These are anomalous signal observations, NOT fingerprint/watermark verification.
 * A normal sustained synthesizer, cymbal resonance or mastering artifact may
 * trigger a finding. Original and exported audio buffers are never modified.
 */
export type SignalObservation={
  timeSeconds:number;
  durationSeconds:number;
  frequencyHz:number;
  prominenceDb:number;
  persistence:number;
  label:string;
  detail:string;
};
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
const FFT=4096;
const window=Float64Array.from({length:FFT},(_,i)=>.5-.5*Math.cos(2*Math.PI*i/(FFT-1)));
const bitReverse=new Uint16Array(FFT);
for(let i=1,j=0;i<FFT;i++){
  let bit=FFT>>1;
  for(;j&bit;bit>>=1)j^=bit;
  j^=bit;
  bitReverse[i]=j;
}
const twiddles=Array.from({length:12},(_,stage)=>{
  const size=1<<(stage+1);
  return {
    cos:Float64Array.from({length:size/2},(_,i)=>Math.cos(-2*Math.PI*i/size)),
    sin:Float64Array.from({length:size/2},(_,i)=>Math.sin(-2*Math.PI*i/size))
  };
});
function transform(real:Float64Array,imag:Float64Array){
  for(let i=0;i<FFT;i++){const j=bitReverse[i];if(i<j){
    let tmp=real[i];real[i]=real[j];real[j]=tmp;
    tmp=imag[i];imag[i]=imag[j];imag[j]=tmp;
  }}
  for(let length=2,stage=0;length<=FFT;length*=2,stage++){
    const half=length/2,{cos,sin}=twiddles[stage];
    for(let base=0;base<FFT;base+=length)
      for(let j=0;j<half;j++){
        const a=base+j,b=a+half;
        const tr=cos[j]*real[b]-sin[j]*imag[b];
        const ti=sin[j]*real[b]+cos[j]*imag[b];
        real[b]=real[a]-tr;imag[b]=imag[a]-ti;
        real[a]+=tr;imag[a]+=ti;
      }
  }
}
function median(values:number[]){
  if(!values.length)return 0;
  values.sort((a,b)=>a-b);
  return values[Math.floor(values.length/2)];
}
/** Screen high-frequency fixed-line persistence using narrow spectral peaks
 * relative to their surrounding spectral bins in active half-second windows.
 * We deliberately do not classify normal music as a watermark or fingerprint.
 *
 * Memory O(FFT + candidate count). CPU bounded by at most 600 windows, sampled
 * across the entire recording rather than only the introduction.
 */
export function screenAcousticSignals(audio:AudioLike):SignalObservation[]{
  if(audio.length<Math.round(audio.sampleRate*12)||audio.numberOfChannels<1)return [];
  const rate=audio.sampleRate,channels=Array.from({length:audio.numberOfChannels},
    (_,i)=>audio.getChannelData(i));
  const minHz=4000,maxHz=Math.min(11500,rate*.46);
  if(minHz>=maxHz)return [];
  const lowBin=Math.ceil(minHz*FFT/rate),highBin=Math.min(FFT/2-26,Math.floor(maxHz*FFT/rate));
  if(highBin<=lowBin)return [];
  const hop=Math.max(FFT,Math.floor(rate*.5));
  const samples=Math.floor((audio.length-FFT)/hop)+1;
  const stride=Math.max(1,Math.ceil(samples/600));
  const real=new Float64Array(FFT),imag=new Float64Array(FFT);
  const power=new Float64Array(FFT/2);
  const counts=new Uint16Array(highBin+1);
  let inspected=0;
  const firstTime=new Float64Array(highBin+1).fill(-1);
  const lastTime=new Float64Array(highBin+1);
  const strengths=new Float64Array(highBin+1);
  let active=0;
  for(let index=0;index<samples;index+=stride){
    const start=index*hop;
    let energy=0;
    for(let j=0;j<FFT;j++){
      // Use the strongest individual stereo channel to avoid anti-phase
      // cancellation and avoid averaging unrelated high-frequency content.
      let sample=channels[0][start+j];
      for(let channel=1;channel<channels.length;channel++){
        const other=channels[channel][start+j];
        if(Math.abs(other)>Math.abs(sample))sample=other;
      }
      energy+=sample*sample;
      real[j]=sample*window[j];imag[j]=0;
    }
    if(Math.sqrt(energy/FFT)<.006)continue;
    active++;
    transform(real,imag);
    for(let k=lowBin-26;k<=highBin+26;k++)
      power[k]=real[k]*real[k]+imag[k]*imag[k];
    const second=start/rate;
    for(let k=lowBin;k<=highBin;k++){
      if(power[k]<1e-5)continue;
      // Nearby bins estimate the local noise/music floor, excluding the
      // current three-bin lobe. The guard helps reject normal broad spectra.
      const surround=[];
      for(let d=5;d<=24;d+=2){
        surround.push(power[k-d],power[k+d]);
      }
      const floor=median(surround);
      const prominence=10*Math.log10(power[k]/Math.max(1e-12,floor));
      if(prominence<22 || power[k]<=power[k-1]*1.4 || power[k]<=power[k+1]*1.4)continue;
      counts[k]++;
      strengths[k]+=prominence;
      if(firstTime[k]<0)firstTime[k]=second;
      lastTime[k]=second;
    }
    inspected++;
  }
  if(inspected<15||active<15)return [];
  const minMatches=Math.max(12,Math.ceil(active*.62));
  const results:SignalObservation[]=[];
  for(let k=lowBin;k<=highBin;k++){
    if(counts[k]<minMatches)continue;
    // Neighboring leakage bins must not create duplicate reports.
    if((k>lowBin&&counts[k-1]>counts[k])||(k<highBin&&counts[k+1]>counts[k]))continue;
    const persistence=counts[k]/active;
    if(lastTime[k]-firstTime[k]<10)continue;
    const hz=k*rate/FFT;
    const db=strengths[k]/counts[k];
    results.push({
      timeSeconds:firstTime[k],
      durationSeconds:lastTime[k]-firstTime[k],
      frequencyHz:Math.round(hz),
      prominenceDb:Math.round(db*10)/10,
      persistence:Math.round(persistence*100)/100,
      label:"Persistent narrowband signal",
      detail:"A stable spectral line near "+Math.round(hz)+" Hz appears in "+
        Math.round(persistence*100)+"% of active sampled windows, around "+
        db.toFixed(1)+" dB above its local spectral surroundings. This may be "+
        "a synthesizer, resonance, tonal noise or another intentional feature. "+
        "It does not identify an acoustic watermark or fingerprint."
    });
  }
  return results.sort((a,b)=>b.persistence-a.persistence||b.prominenceDb-a.prominenceDb).slice(0,3);
}
