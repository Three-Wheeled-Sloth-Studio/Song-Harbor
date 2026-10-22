/** Post-processing visual diagnostics from the actual offline stereo mix.
 * Computed on explicit song-section boundaries; observational, never DSP.
 */
export type SectionRange={id:string;start_seconds:number;end_seconds:number};
export type SectionInsight={
  sectionId:string;
  rmsDbfs:number;
  peakDbfs:number;
  balanceDb:number; // positive = louder left, negative = louder right
  widthDb:number;   // 20 log10(side RMS / mid RMS)
  intensity:number; // 0..1 relative to song's active section range
};
type AudioLike=Pick<AudioBuffer,"numberOfChannels"|"length"|"sampleRate"|"getChannelData">;
const toDb=(amplitude:number)=>20*Math.log10(Math.max(1e-10,amplitude));
const clamp=(v:number,a:number,b:number)=>Math.min(b,Math.max(a,v));
export function analyzeSections(buffer:AudioLike,ranges:readonly SectionRange[],outputTrimDb=0):SectionInsight[]{
  if(buffer.numberOfChannels<2||buffer.length===0||!ranges.length)return [];
  const rate=buffer.sampleRate;
  const left=buffer.getChannelData(0),right=buffer.getChannelData(1);
  const gain=Math.pow(10,outputTrimDb/20);
  const rows=ranges.map(section=>{
    const from=clamp(Math.floor(section.start_seconds*rate),0,buffer.length);
    const to=clamp(Math.ceil(section.end_seconds*rate),from,buffer.length);
    let l=0,r=0,mid=0,side=0,peak=0;
    const step=Math.max(1,Math.floor((to-from)/120000));
    let n=0;
    for(let i=from;i<to;i+=step){
      const a=left[i]*gain,b=right[i]*gain;
      l+=a*a;r+=b*b;
      mid+=(a+b)*(a+b)*.25;side+=(a-b)*(a-b)*.25;
      peak=Math.max(peak,Math.abs(a),Math.abs(b));n++;
    }
    return {
      sectionId:section.id,
      rmsDbfs:toDb(Math.sqrt((l+r)/Math.max(1,2*n))),
      peakDbfs:toDb(peak),
      balanceDb:10*Math.log10(Math.max(1e-14,l)/Math.max(1e-14,r)),
      widthDb:toDb(Math.sqrt(side/Math.max(1e-14,mid))),
      intensity:0
    };
  });
  // Absolute listening-level metrics appear in tooltips; relative intensity
  // uses 5th-95th percentile section RMS for robust color contrast.
  const sorted=rows.map(x=>x.rmsDbfs).filter(Number.isFinite).sort((a,b)=>a-b);
  const low=sorted[Math.floor((sorted.length-1)*.05)]??-60;
  const high=sorted[Math.ceil((sorted.length-1)*.95)]??-12;
  return rows.map(x=>({...x,intensity:clamp((x.rmsDbfs-low)/Math.max(1,high-low),0,1)}));
}
