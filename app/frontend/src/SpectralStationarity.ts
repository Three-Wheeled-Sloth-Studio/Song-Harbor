/** Bounded read-only spectral-shape consistency measurement.
 * High consistency can describe intentional drones, pads, noise or resonances;
 * it is not evidence of AI provenance or a watermark.
 */
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;
export type SpectralChange={timeSeconds:number;similarity:number};
export type Stationarity={similarity:number|null;activeWindows:number;sampledWindows:number;changes:readonly SpectralChange[]};
const SIZE=1024;
const PROBES=[150,300,600,1200,2400,4800,8000,11000];

export function spectralStationarity(buffer:AudioLike):Stationarity{
  const rate=buffer.sampleRate;
  if(buffer.length<rate*4||buffer.numberOfChannels<1||rate<8000)
    return {similarity:null,activeWindows:0,sampledWindows:0,changes:[]};
  const channels=Array.from({length:Math.min(2,buffer.numberOfChannels)},(_,i)=>buffer.getChannelData(i));
  const frequencies=PROBES.filter(hz=>hz<rate*.45);
  if(frequencies.length<4)return {similarity:null,activeWindows:0,sampledWindows:0,changes:[]};
  const total=Math.min(160,Math.floor(buffer.length/rate*2));
  const positions=Array.from({length:total},(_,i)=>Math.floor(i*(buffer.length-SIZE)/Math.max(1,total-1)));
  const steps=frequencies.map(hz=>2*Math.PI*hz/rate);
  const cosine=steps.map(step=>Float64Array.from({length:SIZE},(_,i)=>Math.cos(step*i)));
  const sine=steps.map(step=>Float64Array.from({length:SIZE},(_,i)=>Math.sin(step*i)));
  let previous:Float64Array|null=null,similaritySum=0,pairs=0,active=0;
  const candidates:SpectralChange[]=[];
  for(const pos of positions){
    let rms=0;
    const real=new Float64Array(steps.length),imag=new Float64Array(steps.length);
    for(let j=0;j<SIZE;j++){
      let value=0;
      for(const channel of channels)value+=channel[pos+j];
      value/=channels.length;
      if(!Number.isFinite(value))throw Error("Nonfinite source samples");
      rms+=value*value;
      const weighted=value*(.5-.5*Math.cos(2*Math.PI*j/(SIZE-1)));
      for(let k=0;k<steps.length;k++){
        real[k]+=weighted*cosine[k][j];imag[k]+=weighted*sine[k][j];
      }
    }
    if(Math.sqrt(rms/SIZE)<.005){previous=null;continue;}
    active++;
    const powers=new Float64Array(steps.length);
    let norm=0;
    for(let k=0;k<powers.length;k++){
      powers[k]=Math.hypot(real[k],imag[k]);norm+=powers[k]*powers[k];
    }
    if(norm<1e-12){previous=null;continue;}
    norm=Math.sqrt(norm);
    for(let k=0;k<powers.length;k++)powers[k]/=norm;
    if(previous){
      let dot=0;for(let k=0;k<powers.length;k++)dot+=previous[k]*powers[k];
      const similarity=Math.max(0,Math.min(1,dot));
      similaritySum+=similarity;pairs++;
      if(similarity<.72)candidates.push({timeSeconds:(pos+SIZE/2)/rate,
        similarity:Math.round(1000*similarity)/1000});
    }
    previous=powers;
  }
  return {similarity:pairs>=8?Math.round(1000*similaritySum/pairs)/1000:null,
    activeWindows:active,sampledWindows:positions.length,
    changes:pairs>=8?candidates.sort((a,b)=>a.similarity-b.similarity)
      .reduce<SpectralChange[]>((selected,item)=>{
        if(selected.length<3&&selected.every(prev=>Math.abs(prev.timeSeconds-item.timeSeconds)>=2))selected.push(item);
        return selected;
      },[]).sort((a,b)=>a.timeSeconds-b.timeSeconds):[]};
}
