/** CPU-bounded, non-destructive tail-envelope observations.
 * These measurements cannot distinguish an unintended render fault from an
 * intentional gate/freeze and are not an AI-origin classifier.
 */
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
export type ReverbTailObservation={
  kind:"cutoff"|"stall";
  timeSeconds:number;
  durationSeconds:number;
  rmsBefore:number;
  rmsAfter:number;
};

const average=(values:Float64Array,start:number,end:number)=>{
  let sum=0;
  for(let i=start;i<end;i++)sum+=values[i];
  return sum/Math.max(1,end-start);
};

/** Inspect 10 ms across-channel RMS frames for an abrupt end or a decay that
 * becomes unusually flat. Results describe only the rendered envelope.
 */
export function inspectReverbTail(buffer:AudioLike,maxObservations=6):ReverbTailObservation[]{
  if(!Number.isFinite(buffer.sampleRate)||buffer.sampleRate<4000||
    !Number.isInteger(buffer.length)||buffer.length<1||
    !Number.isInteger(buffer.numberOfChannels)||buffer.numberOfChannels<1||
    !Number.isFinite(maxObservations)||maxObservations<=0)return [];
  const rate=buffer.sampleRate,frame=Math.max(1,Math.round(rate*.01));
  const count=Math.floor(buffer.length/frame);
  if(count<45)return [];
  let channels:Float32Array[];
  try{
    channels=Array.from({length:buffer.numberOfChannels},(_,channel)=>buffer.getChannelData(channel));
  }catch{return [];}
  if(channels.some(channel=>channel.length<buffer.length))return [];
  const envelope=new Float64Array(count);
  let maximum=0;
  for(let block=0;block<count;block++){
    let energy=0;
    const start=block*frame,end=start+frame;
    for(let i=start;i<end;i++)for(const channel of channels){
      const sample=channel[i];
      if(!Number.isFinite(sample))return [];
      energy+=sample*sample;
    }
    envelope[block]=Math.sqrt(energy/(frame*channels.length));
    maximum=Math.max(maximum,envelope[block]);
  }
  if(maximum<.01)return [];
  const observations:ReverbTailObservation[]=[];
  const push=(value:ReverbTailObservation)=>{
    if(observations.some(item=>Math.abs(item.timeSeconds-value.timeSeconds)<.5))return;
    observations.push(value);
  };

  // A cutoff needs a decaying lead-in and at least 100 ms of near-silence.
  const decayLookback=20,silenceHold=10;
  for(let i=decayLookback;i+silenceHold<=count;i++){
    const before=average(envelope,i-3,i);
    let after=0;
    for(let j=i;j<i+silenceHold;j++)after=Math.max(after,envelope[j]);
    const earlier=average(envelope,i-decayLookback,i-decayLookback+5);
    if(before>Math.max(.004,maximum*.025)&&earlier>before*1.25&&
      after<=Math.max(.0008,before*.1)){
      push({kind:"cutoff",timeSeconds:i*frame/rate,durationSeconds:silenceHold*frame/rate,
        rmsBefore:before,rmsAfter:after});
      if(observations.length>=maxObservations)return observations;
      i+=silenceHold;
    }
  }

  // A stall needs a decaying lead-in followed by at least 800 ms whose level
  // and variance remain nearly constant. A steady tone from time zero fails
  // the lead-in condition.
  const plateauHold=80;
  for(let i=decayLookback;i+plateauHold<=count;i++){
    const earlier=average(envelope,i-decayLookback,i-decayLookback+5);
    const recent=average(envelope,i-5,i);
    const first=average(envelope,i,i+10),last=average(envelope,i+plateauHold-10,i+plateauHold);
    const openingA=average(envelope,i,i+5),openingB=average(envelope,i+5,i+10);
    const mean=average(envelope,i,i+plateauHold);
    if(mean<Math.max(.004,maximum*.025)||earlier<=recent*1.25||
      first<=0||openingB/openingA<.97||last/first<.88||last/first>1.12)continue;
    let variance=0;
    for(let j=i;j<i+plateauHold;j++)variance+=(envelope[j]-mean)**2;
    const coefficient=Math.sqrt(variance/plateauHold)/mean;
    if(coefficient>.08)continue;
    push({kind:"stall",timeSeconds:i*frame/rate,durationSeconds:plateauHold*frame/rate,
      rmsBefore:recent,rmsAfter:mean});
    if(observations.length>=maxObservations)return observations;
    i+=plateauHold;
  }
  return observations;
}
