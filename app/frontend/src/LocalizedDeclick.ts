/** Reversible, sample-local de-click candidate.
 * It never mutates input PCM and never runs without a user-selected location.
 * This is an audio repair primitive, not an automatic transient classifier.
 */
export type DeclickCandidate={
  startFrame:number;endFrame:number;sampleRate:number;
  beforePeak:number;afterPeak:number;
  channels:Float32Array[];
  /** Original sample indices and replacements permit precise undo/recipe export. */
  replacements:{channel:number;startFrame:number;values:Float32Array}[];
};
export type DeclickSource=Pick<AudioBuffer,"length"|"sampleRate"|"numberOfChannels"|"getChannelData">;

/** Replace only a narrow impulse window with shape-preserving interpolation.
 * Caller selects a verified isolated click; a drum transient is NOT eligible
 * without a musical audition.
 */
export function makeDeclickCandidate(audio:DeclickSource,timeSeconds:number,
  halfWindowMs=1):DeclickCandidate{
  if(!Number.isFinite(timeSeconds)||timeSeconds<0||timeSeconds>=audio.length/audio.sampleRate)
    throw Error("Select a click within the recording");
  if(halfWindowMs<.15||halfWindowMs>3)
    throw Error("Repair window must be 0.15–3 ms");
  const center=Math.round(timeSeconds*audio.sampleRate);
  const half=Math.max(2,Math.round(halfWindowMs*.001*audio.sampleRate));
  const startFrame=Math.max(2,center-half);
  const endFrame=Math.min(audio.length-3,center+half+1);
  if(endFrame-startFrame<2)throw Error("Not enough audio around click");
  let beforePeak=0,afterPeak=0;
  const replacements:{channel:number;startFrame:number;values:Float32Array}[]=[];
  const channels:Array<Float32Array>=[];
  for(let channel=0;channel<audio.numberOfChannels;channel++){
    const source=audio.getChannelData(channel);
    const output=source.slice();
    const values=new Float32Array(endFrame-startFrame);
    const left=source[startFrame-1],right=source[endFrame];
    // Cubic Hermite with slope estimates on both sides provides a smoother
    // join than linear interpolation for a small dropout/click interval.
    const leftSlope=.5*(source[startFrame]-source[startFrame-2]);
    const rightSlope=.5*(source[endFrame+1]-source[endFrame-1]);
    for(let i=startFrame;i<endFrame;i++){
      const t=(i-startFrame+1)/(endFrame-startFrame+1);
      const t2=t*t,t3=t2*t;
      const interpolated=(2*t3-3*t2+1)*left+(t3-2*t2+t)*leftSlope+
        (-2*t3+3*t2)*right+(t3-t2)*rightSlope;
      const original=source[i];
      // Equal weighting is deliberately not used: full replacement only
      // occurs in the middle, with smooth edges to prevent new discontinuities.
      const taper=Math.sin(Math.PI*t)**2;
      const sample=original*(1-taper)+interpolated*taper;
      values[i-startFrame]=sample;
      output[i]=sample;
      beforePeak=Math.max(beforePeak,Math.abs(original));
      afterPeak=Math.max(afterPeak,Math.abs(sample));
    }
    channels.push(output);
    replacements.push({channel,startFrame,values});
  }
  return {startFrame,endFrame,sampleRate:audio.sampleRate,beforePeak,afterPeak,channels,replacements};
}
