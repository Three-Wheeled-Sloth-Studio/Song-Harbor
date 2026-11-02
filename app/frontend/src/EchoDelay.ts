/** Non-destructive echo send, separate from whole-stem timeline offset.
 * Dry source remains untouched. Feedback is strictly bounded for stability.
 */
export type EchoSettings={
  delayMs:number;wet:number;feedback:number;lowpassHz:number;
};
export type EchoStage={
  input:GainNode;delay:DelayNode;feedback:GainNode;filter:BiquadFilterNode;wet:GainNode;
};
export const DEFAULT_ECHO:EchoSettings={delayMs:180,wet:0,feedback:.25,lowpassHz:6500};
export function validateEcho(value:EchoSettings):EchoSettings{
  const {delayMs,wet,feedback,lowpassHz}=value;
  if(![delayMs,wet,feedback,lowpassHz].every(Number.isFinite)||
    delayMs<20||delayMs>2000||wet<0||wet>1||feedback<0||feedback>.8||
    lowpassHz<200||lowpassHz>18000)
    throw Error("Echo requires 20-2000ms delay, 0-100% wet, 0-80% feedback, 200-18000Hz lowpass");
  return {...value};
}
export function echoTailSeconds(echo:EchoSettings):number{
  const e=validateEcho(echo);
  if(e.wet===0)return 0;
  // Stop at -60 dB feedback or a conservative maximum of 8 seconds.
  const repeats=e.feedback===0?1:
    Math.max(1,Math.ceil(Math.log(.001)/Math.log(e.feedback)));
  return Math.min(8,e.delayMs/1000*repeats);
}
export function createEchoStage(ctx:BaseAudioContext,output:AudioNode):EchoStage{
  const input=ctx.createGain(),delay=ctx.createDelay(2.05);
  const feedback=ctx.createGain(),filter=ctx.createBiquadFilter(),wet=ctx.createGain();
  filter.type="lowpass";
  input.connect(delay);
  delay.connect(filter);
  filter.connect(wet).connect(output);
  filter.connect(feedback).connect(delay);
  wet.gain.value=0;
  feedback.gain.value=0;
  delay.delayTime.value=.18;
  filter.frequency.value=6500;
  return {input,delay,feedback,filter,wet};
}
export function configureEcho(stage:EchoStage,echo:EchoSettings|undefined,time:number):void{
  const settings=echo?validateEcho(echo):DEFAULT_ECHO;
  stage.delay.delayTime.setValueAtTime(settings.delayMs/1000,time);
  stage.feedback.gain.setValueAtTime(echo?settings.feedback:0,time);
  stage.filter.frequency.setValueAtTime(settings.lowpassHz,time);
  stage.wet.gain.setValueAtTime(echo?settings.wet:0,time);
}
export function disconnectEcho(stage:EchoStage):void{
  for(const node of Object.values(stage))node.disconnect();
}
