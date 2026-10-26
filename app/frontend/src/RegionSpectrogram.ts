/** Small bounded, diagnostic-only time/frequency tile grid.
 * Goertzel probes across 12 logarithmic bands and 24 time bins for a
 * three-second region. Never changes audio or claims to recognize fingerprints.
 */
export type SpectralPreview={startSeconds:number;seconds:number;columns:number;rows:number;levels:number[]};
type AudioLike=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;

export function regionSpectrogram(audio:AudioLike,centerSeconds:number):SpectralPreview{
  const columns=24,rows=12,seconds=3;
  const rate=audio.sampleRate;
  const startSeconds=Math.max(0,Math.min(Math.max(0,audio.length/rate-seconds),centerSeconds-1));
  const levels:number[]=[];
  const channel=audio.getChannelData(0);
  const windowSize=Math.min(512,Math.max(64,Math.round(rate/100)));
  const maxFrequency=Math.min(rate*.45,12000);
  for(let x=0;x<columns;x++){
    const mid=(startSeconds+(x+.5)*seconds/columns)*rate;
    const begin=Math.max(0,Math.min(channel.length-windowSize,Math.round(mid-windowSize/2)));
    for(let y=0;y<rows;y++){
      const freq=120*Math.pow(maxFrequency/120,(y+.5)/rows);
      const step=2*Math.PI*freq/rate;
      let cosine=0,sine=0;
      for(let i=0;i<windowSize;i++){
        const envelope=.5-.5*Math.cos(2*Math.PI*i/(windowSize-1));
        const value=channel[begin+i]*envelope;
        cosine+=value*Math.cos(step*i);
        sine+=value*Math.sin(step*i);
      }
      const magnitude=Math.sqrt(cosine*cosine+sine*sine)/windowSize;
      const db=20*Math.log10(Math.max(1e-9,magnitude));
      levels.push(Math.max(0,Math.min(1,(db+72)/62)));
    }
  }
  return {startSeconds,seconds,columns,rows,levels};
}
