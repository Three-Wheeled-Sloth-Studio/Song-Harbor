/** CPU-bounded, non-destructive isolated-attack envelope measurement.
 * Acoustic evidence only, not an AI-origin or quality classifier.
 */
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
export type AttackRiseObservation={timeSeconds:number;peakSeconds:number;riseMs:number;peakRms:number};
export function inspectAttackRise(buffer:AudioLike,maxObservations=6):AttackRiseObservation[]{
  if(!Number.isFinite(buffer.sampleRate)||buffer.sampleRate<4000||buffer.length<1||buffer.numberOfChannels<1||maxObservations<=0)return [];
  const rate=buffer.sampleRate,hop=Math.max(1,Math.round(rate*.002));
  const n=Math.floor(buffer.length/hop);
  if(n<30)return [];
  const channels=Array.from({length:buffer.numberOfChannels},(_,c)=>buffer.getChannelData(c));
  const envelope=new Float64Array(n);
  let maximum=0;
  for(let j=0;j<n;j++){
    let sum=0;
    for(let i=j*hop;i<(j+1)*hop;i++)for(const channel of channels){const v=channel[i];sum+=v*v;}
    envelope[j]=Math.sqrt(sum/(hop*channels.length));
    maximum=Math.max(maximum,envelope[j]);
  }
  if(maximum<.015)return [];
  const smooth=new Float64Array(n);
  for(let i=1;i<n-1;i++)smooth[i]=(envelope[i-1]+envelope[i]+envelope[i+1])/3;
  const span=Math.round(.15*rate/hop),gap=Math.round(.3*rate/hop);
  const results:AttackRiseObservation[]=[];
  let previous=-gap;
  for(let peak=span;peak<n-1;peak++){
    const height=smooth[peak];
    if(height<Math.max(.018,maximum*.12)||height<smooth[peak-1]||height<=smooth[peak+1]||peak-previous<gap)continue;
    const start=peak-span;
    let low=start;
    while(low<peak&&smooth[low]<height*.1)low++;
    if(low===start||low>=peak||low-start<Math.round(.01*rate/hop))continue;
    let high=low;
    while(high<=peak&&smooth[high]<height*.9)high++;
    if(high>peak)continue;
    const riseMs=(high-low)*hop*1000/rate;
    if(riseMs<35||riseMs>140)continue;
    results.push({timeSeconds:low*hop/rate,peakSeconds:peak*hop/rate,riseMs:Math.round(riseMs*10)/10,peakRms:Math.round(height*1000)/1000});
    previous=peak;
    if(results.length>=maxObservations)break;
  }
  return results;
}
