/** Non-destructive, post-render QC. Findings are candidates, not automatic repairs.
 * Uses the exact floating-point buffer passed to WAV encoding, before master trim.
 */
export type AudioFinding={
  kind:"headroom"|"transient";
  timeSeconds:number;
  severity:"warning"|"review";
  label:string;
  detail:string;
};
export function inspectRenderedAudio(buffer:AudioBuffer,outputTrimDb=0,maxFindings=16):AudioFinding[]{
  if(buffer.length===0||buffer.numberOfChannels===0)return [];
  const channels=Array.from({length:buffer.numberOfChannels},(_,c)=>buffer.getChannelData(c));
  const rate=buffer.sampleRate;
  const gain=Math.pow(10,outputTrimDb/20);
  const findings:AudioFinding[]=[];
  let highestPeak=0,highestPosition=0;
  let transientCount=0;
  const minGap=Math.max(1,Math.floor(rate*.08));
  let lastTransient=-minGap;
  // 0.7 sample discontinuity is deliberately conservative. Normal attacks,
  // kick transients and clipping may be false positives: manually audition.
  for(let i=0;i<buffer.length;i++){
    let peak=0,delta=0;
    for(const channel of channels){
      const sample=channel[i]*gain;
      peak=Math.max(peak,Math.abs(sample));
      if(i>0)delta=Math.max(delta,Math.abs((channel[i]-channel[i-1])*gain));
    }
    if(peak>highestPeak){highestPeak=peak;highestPosition=i;}
    if(i>0&&delta>=.7&&i-lastTransient>=minGap){
      transientCount++;
      if(findings.length<maxFindings-1){
        findings.push({kind:"transient",timeSeconds:i/rate,severity:"review",
          label:"Sharp sample transition",
          detail:"Possible click or intentional transient; audition around this timestamp."});
      }
      lastTransient=i;
    }
  }
  if(highestPeak>=.98){
    findings.unshift({kind:"headroom",timeSeconds:highestPosition/rate,
      severity:highestPeak>1?"warning":"review",
      label:highestPeak>1?"Peak exceeds 0 dBFS":"Peak close to digital ceiling",
      detail:"Highest rendered sample: "+(20*Math.log10(highestPeak)).toFixed(1)+" dBFS. Review output trim."});
  }
  if(transientCount>maxFindings-1){
    findings.push({kind:"transient",timeSeconds:lastTransient/rate,severity:"review",
      label:"Additional abrupt transitions",
      detail:String(transientCount-(maxFindings-1))+" more candidates omitted; this scan does not classify percussion or distortion."});
  }
  return findings.sort((a,b)=>a.timeSeconds-b.timeSeconds).slice(0,maxFindings);
}
