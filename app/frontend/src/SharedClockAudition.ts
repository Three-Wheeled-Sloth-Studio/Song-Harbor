import {scheduleAutomation, type AutomationPoint} from "./SectionAutomation";
import {createStereoWidthStage,scheduleStereoWidth,type StereoWidthStage} from "./StereoWidth";
import {createSpatialReflection,scheduleSpatialReflection,type SpatialReflectionStage} from "./SpatialReflection";
import {createEqStage,scheduleEq,type EqCurves} from "./SectionEq";
import {createDynamicsStage,scheduleCompressor,scheduleDucking,makeDuckingEnvelope,type DynamicsCurves,type DynamicsStage} from "./SectionDynamics";
/**
 * Song Harbor shared-clock audition engine.
 *
 * All decoded stem buffers are scheduled on ONE AudioContext timeline. No
 * HTMLAudioElement clocks, per-stem playbackRate changes, or seeking followers.
 * This intentionally limits the in-memory MVP rather than silently returning
 * to the phase-unsafe multi-stream player.
 */
export type AuditionSource = {key:string;filename:string;url:string;pan:-1|0|1};
export type AuditionLevel = {gain:number};
type Track = {source:AuditionSource;buffer:AudioBuffer;gain:GainNode;panner?:StereoPannerNode};
type ActiveNode = AudioBufferSourceNode;

export const MAX_DECODED_AUDIO_BYTES=768*1024*1024;
export const SAFE_EXPORT_CEILING_DBFS=-1;
export class MixHeadroomError extends Error{
  constructor(readonly measuredPeakDbfs:number,readonly recommendedAdditionalTrimDb:number){
    super("Mix exceeds 0 dBFS ("+measuredPeakDbfs.toFixed(1)+" dBFS). Apply "+Math.abs(recommendedAdditionalTrimDb).toFixed(1)+" dB of master output trim to target "+SAFE_EXPORT_CEILING_DBFS+" dBFS.");
    this.name="MixHeadroomError";
  }
}


export class SharedClockAudition {
  readonly context:AudioContext;
  private master:GainNode;
  private dryMaster:GainNode;
  private sourceDurationSeconds=0;
  private ending={fade_seconds:0,tail_seconds:0,curve:"smooth" as "smooth"|"linear"};
  private tracks:Track[]=[];
  private groupPanners=new Map<string,StereoPannerNode>();
  private widthStages=new Map<string,StereoWidthStage>();
  private eqStages=new Map<string,[BiquadFilterNode,BiquadFilterNode,BiquadFilterNode]>();
  private dynamicsStages=new Map<string,DynamicsStage>();
  private spaceStages=new Map<string,SpatialReflectionStage>();
  private reverb:ConvolverNode;
  private reverbDrive:GainNode;
  private bypassEffects={pan:false,width:false,space:false,reverb:false,ending:false,eq:false};
  private reverbSends=new Map<string,GainNode>();
  private renderedLevels:Record<string,number>={};
  private monitorLevel=0.75;
  private outputTrimDb=0;
  private nodes:ActiveNode[]=[];
  private automation:Record<string,{pan?:AutomationPoint[];reverb?:AutomationPoint[];width?:AutomationPoint[];space?:AutomationPoint[];eq?:EqCurves;dynamics?:DynamicsCurves}>={};
  private duckEnvelopes=new Map<string,AutomationPoint[]>();
  private loadController:AbortController|null=null;
  private offset=0;
  private startAt=0;
  private running=false;
  private disposed=false;
  private prepared=false;
  private durationSeconds=0;
  constructor(){
    this.context=new AudioContext();
    this.master=this.context.createGain();
    this.master.connect(this.context.destination);
    this.dryMaster=this.context.createGain();
    this.dryMaster.connect(this.master);
    this.reverb=this.context.createConvolver();
    this.reverb.normalize=false;
    this.reverb.buffer=createRoomImpulse(this.context);
    this.reverb.connect(this.master);
    this.reverbDrive=this.context.createGain();
    this.reverbDrive.connect(this.reverb);
  }
  get duration(){return this.durationSeconds;}
  get ready(){return this.prepared&&this.tracks.length>0&&!this.disposed;}
  get playing(){return this.running;}
  get position(){
    if(!this.running)return this.offset;
    return Math.min(this.durationSeconds,Math.max(0,this.offset+Math.max(0,this.context.currentTime-this.startAt)));
  }
  async prepare(sources:AuditionSource[],onProgress?:(ready:number,total:number)=>void){
    if(this.disposed)throw Error("Audio engine closed");
    if(this.loadController)throw Error("Audio is already loading");
    if(this.tracks.length)throw Error("Audio already prepared");
    if(!sources.length)throw Error("No audio sources");
    this.loadController=new AbortController();
    const signal=this.loadController.signal;
    let bytes=0;
    let maxDuration=0;
    try{
      // Sequential decode bounds temporary compressed/decoded peak allocations.
      for(let i=0;i<sources.length;i++){
        if(signal.aborted||this.disposed)throw Error("Audio load cancelled");
        const src=sources[i];
        const response=await fetch(src.url,{signal});
        if(!response.ok)throw Error(`Cannot load ${src.filename} (${response.status})`);
        const payload=await response.arrayBuffer();
        if(signal.aborted||this.disposed)throw Error("Audio load cancelled");
        const buffer=await this.context.decodeAudioData(payload);
        if(signal.aborted||this.disposed)throw Error("Audio load cancelled");
        bytes+=buffer.length*buffer.numberOfChannels*Float32Array.BYTES_PER_ELEMENT;
        if(bytes>MAX_DECODED_AUDIO_BYTES){
          throw Error("This song exceeds the 768 MiB decoded-audio audition limit. Use a DAW export until chunked shared-clock streaming is available.");
        }
        if(maxDuration>0&&Math.abs(buffer.duration-maxDuration)>0.15){
          throw Error(`Stem lengths differ by more than 150ms (${src.filename}). Re-run separation or repair the source before aligned audition.`);
        }
        maxDuration=Math.max(maxDuration,buffer.duration);
        const gain=this.context.createGain();
        let bus=this.groupPanners.get(src.filename);
        if(!bus){
          bus=this.context.createStereoPanner();
          bus.pan.value=0;
          const eq=createEqStage(this.context);
          this.eqStages.set(src.filename,eq);
          const stage=createStereoWidthStage(this.context);
          const dynamics=createDynamicsStage(this.context);
          this.dynamicsStages.set(src.filename,dynamics);
          eq[2].connect(dynamics.compressor);
          dynamics.duckGain.connect(stage.input);
          stage.output.connect(bus);
          const space=createSpatialReflection(this.context);
          stage.output.connect(space.input);
          space.output.connect(bus);
          this.spaceStages.set(src.filename,space);
          this.widthStages.set(src.filename,stage);
          bus.connect(this.dryMaster);
          const send=this.context.createGain();
          send.gain.value=0;
          bus.connect(send).connect(this.reverbDrive);
          this.reverbSends.set(src.filename,send);
          this.groupPanners.set(src.filename,bus);
        }
        let panner:StereoPannerNode|undefined;
        panner=this.context.createStereoPanner();
        panner.pan.value=src.pan;
        gain.connect(panner).connect(this.eqStages.get(src.filename)![0]);
        gain.gain.value=0;
        this.tracks.push({source:src,buffer,gain,panner});
        onProgress?.(i+1,sources.length);
      }
      this.sourceDurationSeconds=maxDuration;
      this.durationSeconds=maxDuration+this.ending.tail_seconds;
      this.prepared=true;
    }catch(err){
      this.clearTracks();
      throw err;
    }finally{
      this.loadController=null;
    }
  }
  setLevels(levels:Record<string,AuditionLevel>,monitor:number){
    this.monitorLevel=Math.max(0,Math.min(1,monitor));
    this.updateMasterOutput();
    this.renderedLevels=Object.fromEntries(Object.entries(levels).map(([key,item])=>[key,Math.max(0,Math.min(2,item.gain))]));
    if(Object.values(this.automation).some(item=>item.dynamics?.duck))this.setAutomation(this.automation);
    for(const track of this.tracks){
      track.gain.gain.value=Math.max(0,Math.min(2,levels[track.source.filename]?.gain??0));
    }
  }
  /** Non-destructive master trim, downstream of all stem and effect sends. */
  setOutputTrimDb(value:number){
    if(!Number.isFinite(value)||value>0||value< -60)throw Error("Master trim must be between -60 and 0 dB");
    this.outputTrimDb=value;
    this.updateMasterOutput();
  }
  private updateMasterOutput(){
    this.master.gain.setTargetAtTime(
      this.monitorLevel*Math.pow(10,this.outputTrimDb/20),
      this.context.currentTime,0.015);
  }
  /** End-anchored fade attenuates the dry mix and reverb excitation; existing wet decay survives. */
  setEnding(settings:{fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"}){
    const {fade_seconds,tail_seconds,curve}=settings;
    if(!Number.isFinite(fade_seconds)||fade_seconds<0||fade_seconds>30||
       !Number.isFinite(tail_seconds)||tail_seconds<0||tail_seconds>10||
       !["linear","smooth"].includes(curve))throw Error("Invalid ending treatment");
    this.ending={fade_seconds,tail_seconds,curve};
    if(this.prepared)this.durationSeconds=this.sourceDurationSeconds+tail_seconds;
    if(this.running)this.seek(this.position);
  }
  private fadePoints():AutomationPoint[]{
    const {fade_seconds,curve}=this.ending;
    if(fade_seconds<=0)return [{time:0,value:1}];
    const start=Math.max(0,this.sourceDurationSeconds-fade_seconds);
    const points:AutomationPoint[]=[{time:0,value:1},{time:start,value:1}];
    const steps=curve==="smooth"?16:1;
    for(let i=1;i<=steps;i++){
      const x=i/steps;
      points.push({time:start+fade_seconds*x,value:curve==="smooth"?1-x*x*(3-2*x):1-x});
    }
    return points;
  }
  /** Audition-only effect bypass: the saved mix and offline export remain processed. */
  setEffectBypass(effects:{pan:boolean;width:boolean;space:boolean;reverb:boolean;ending:boolean;eq:boolean}){
    if(Object.keys(effects).every(key=>this.bypassEffects[key as keyof typeof effects]===effects[key as keyof typeof effects]))return;
    this.bypassEffects={...effects};
    if(this.running)this.seek(this.position);
    else this.configurePreviewNodes(this.context.currentTime+0.02,this.offset);
  }
  get comparingOriginal(){return Object.values(this.bypassEffects).every(Boolean);}
  private configurePreviewNodes(at:number,offset:number){
    const bypass=this.bypassEffects;
    for(const [filename,bus] of this.groupPanners){
      const eq=this.eqStages.get(filename);
      if(eq)scheduleEq(eq,this.automation[filename]?.eq||{},offset,at,bypass.eq);
      const dynamics=this.dynamicsStages.get(filename);
      if(dynamics){
        scheduleCompressor(dynamics,this.automation[filename]?.dynamics?.compressor,offset,at);
        scheduleDucking(dynamics,this.duckEnvelopes.get(filename),offset,at);
      }
      scheduleAutomation(bus.pan,
        !bypass.pan&&this.automation[filename]?.pan||[{time:0,value:0}],offset,at);
      const width=this.widthStages.get(filename);
      if(width)scheduleStereoWidth(width,
        !bypass.width&&this.automation[filename]?.width||[{time:0,value:1}],offset,at);
      const reflection=this.spaceStages.get(filename);
      if(reflection)scheduleSpatialReflection(reflection,
        !bypass.space&&this.automation[filename]?.space||[{time:0,value:0}],offset,at);
      const send=this.reverbSends.get(filename);
      if(send)scheduleAutomation(send.gain,
        !bypass.reverb&&this.automation[filename]?.reverb||[{time:0,value:0}],offset,at);
    }
    scheduleAutomation(this.dryMaster.gain,
      bypass.ending?[{time:0,value:1}]:this.fadePoints(),offset,at);
    scheduleAutomation(this.reverbDrive.gain,
      bypass.reverb?[{time:0,value:0}]:bypass.ending?[{time:0,value:1}]:this.fadePoints(),offset,at);
  }
  /** Pan the reconstructed per-stem stereo bus. Split L/R children retain native routing. */
  setAutomation(curves:Record<string,{pan?:AutomationPoint[];reverb?:AutomationPoint[];width?:AutomationPoint[];space?:AutomationPoint[];eq?:EqCurves;dynamics?:DynamicsCurves}>){
    this.automation=curves;
    this.duckEnvelopes.clear();
    for(const [filename,settings] of Object.entries(curves)){
      const duck=settings.dynamics?.duck;
      if(!duck)continue;
      const key=this.tracks.find(track=>track.source.filename===duck.keyFilename);
      if(!key)continue;
      const gain=this.renderedLevels[duck.keyFilename]??0;
      this.duckEnvelopes.set(filename,makeDuckingEnvelope(key.buffer,duck.depthDb,gain));
    }
    if(this.running)this.seek(this.position);
  }
  /**
   * Deterministic offline bounce from the SAME decoded buffers, stem routing,
   * levels and section curves as playback. Monitoring volume is excluded.
   * Throws rather than silently limiting a clipping mix differently from preview.
   */
  async renderWav24():Promise<Blob>{
    if(!this.ready)throw Error("Synchronized audio must finish loading before export");
    const sampleRate=this.context.sampleRate;
    const frames=Math.ceil(this.durationSeconds*sampleRate);
    if(frames<1||frames>sampleRate*60*15)throw Error("Offline export supports up to 15 minutes");
    const offline=new OfflineAudioContext(2,frames,sampleRate);
    const group=new Map<string,StereoPannerNode>();
    const dry=offline.createGain();
    dry.connect(offline.destination);
    scheduleAutomation(dry.gain,this.fadePoints(),0,0);
    const reverbDrive=offline.createGain();
    scheduleAutomation(reverbDrive.gain,this.fadePoints(),0,0);
    const convolver=offline.createConvolver();
    convolver.normalize=false;
    convolver.buffer=createRoomImpulse(offline);
    reverbDrive.connect(convolver);
    convolver.connect(offline.destination);
    const sends=new Map<string,GainNode>();
    const widths=new Map<string,StereoWidthStage>();
    const eqs=new Map<string,[BiquadFilterNode,BiquadFilterNode,BiquadFilterNode]>();
    const dynamicsStages=new Map<string,DynamicsStage>();
    const spaces=new Map<string,SpatialReflectionStage>();
    for(const track of this.tracks){
      let bus=group.get(track.source.filename);
      if(!bus){
        bus=offline.createStereoPanner();
        bus.pan.value=0;
        const eq=createEqStage(offline);
        eqs.set(track.source.filename,eq);
        const stage=createStereoWidthStage(offline);
        const dynamics=createDynamicsStage(offline);
        dynamicsStages.set(track.source.filename,dynamics);
        eq[2].connect(dynamics.compressor);
        dynamics.duckGain.connect(stage.input);
        stage.output.connect(bus);
        const space=createSpatialReflection(offline);
        stage.output.connect(space.input);
        space.output.connect(bus);
        spaces.set(track.source.filename,space);
        widths.set(track.source.filename,stage);
        bus.connect(dry);
        const send=offline.createGain();
        send.gain.value=0;
        bus.connect(send).connect(reverbDrive);
        sends.set(track.source.filename,send);
        group.set(track.source.filename,bus);
      }
      const source=offline.createBufferSource();
      source.buffer=track.buffer;
      const gain=offline.createGain();
      gain.gain.value=this.renderedLevels[track.source.filename]??0;
      const childPan=offline.createStereoPanner();
      childPan.pan.value=track.source.pan;
      source.connect(gain).connect(childPan).connect(eqs.get(track.source.filename)![0]);
      source.start(0);
    }
    for(const [filename,bus] of group){
      const curve=this.automation[filename]?.pan;
      if(curve)scheduleAutomation(bus.pan,curve,0,0);
      const wet=this.automation[filename]?.reverb;
      if(wet)scheduleAutomation(sends.get(filename)!.gain,wet,0,0);
      const width=this.automation[filename]?.width;
      if(width)scheduleStereoWidth(widths.get(filename)!,width,0,0);
      const space=this.automation[filename]?.space;
      if(space)scheduleSpatialReflection(spaces.get(filename)!,space,0,0);
      scheduleEq(eqs.get(filename)!,this.automation[filename]?.eq||{},0,0);
      const dynamics=dynamicsStages.get(filename)!;
      scheduleCompressor(dynamics,this.automation[filename]?.dynamics?.compressor,0,0);
      scheduleDucking(dynamics,this.duckEnvelopes.get(filename),0,0);
    }
    const rendered=await offline.startRendering();
    return encodeWav24(rendered,this.outputTrimDb);
  }

  async play(){
    if(!this.ready)throw Error("Audio still loading");
    if(this.running)return;
    await this.context.resume();
    if(this.disposed)throw Error("Audio engine closed");
    if(this.offset>=this.durationSeconds-0.01)this.offset=0;
    this.launch(this.offset);
  }
  pause(){
    if(!this.running)return;
    const time=this.position;
    this.stopSources();
    this.offset=time;
  }
  seek(seconds:number){
    const target=Math.max(0,Math.min(this.durationSeconds,Number.isFinite(seconds)?seconds:0));
    const wasRunning=this.running;
    this.stopSources();
    this.offset=target;
    if(wasRunning&&target<this.durationSeconds)this.launch(target);
  }
  stop(){this.stopSources();this.offset=0;}
  private launch(offset:number){
    this.stopSources();
    // Every node is scheduled with the exact same context timestamp and offset.
    const startAt=this.context.currentTime+0.025;
    const made:ActiveNode[]=[];
    try{
      for(const track of this.tracks){
        const node=this.context.createBufferSource();
        node.buffer=track.buffer;
        node.connect(track.gain);
        made.push(node);
      }
      this.configurePreviewNodes(startAt,offset);
      for(const node of made)node.start(startAt,offset);
      this.nodes=made;
      this.offset=offset;
      this.startAt=startAt;
      this.running=true;
    }catch(err){
      for(const node of made){try{node.stop();}catch{/* not started */}node.disconnect();}
      this.nodes=[];this.running=false;
      throw err;
    }
  }
  private stopSources(){
    this.running=false;
    this.dryMaster.gain.cancelScheduledValues(this.context.currentTime);
    this.reverbDrive.gain.cancelScheduledValues(this.context.currentTime);
    for(const bus of this.groupPanners.values())bus.pan.cancelScheduledValues(this.context.currentTime);
    for(const send of this.reverbSends.values())send.gain.cancelScheduledValues(this.context.currentTime);
    for(const stage of this.widthStages.values()){
      for(const node of [...stage.direct,...stage.cross])node.gain.cancelScheduledValues(this.context.currentTime);
    }
    for(const stage of this.dynamicsStages.values()){
      for(const param of [stage.compressor.threshold,stage.compressor.ratio,stage.compressor.attack,stage.compressor.release,stage.duckGain.gain])param.cancelScheduledValues(this.context.currentTime);
    }
    for(const filters of this.eqStages.values())for(const filter of filters){
      filter.frequency.cancelScheduledValues(this.context.currentTime);
      filter.Q.cancelScheduledValues(this.context.currentTime);
      filter.gain.cancelScheduledValues(this.context.currentTime);
    }
    for(const stage of this.spaceStages.values())
      for(const send of stage.sends)send.gain.cancelScheduledValues(this.context.currentTime);
    for(const node of this.nodes){
      try{node.stop();}catch{/* node may have ended */}
      node.disconnect();
    }
    this.nodes=[];
  }
  private clearTracks(){
    this.prepared=false;
    this.stopSources();
    for(const track of this.tracks){track.gain.disconnect();track.panner?.disconnect();}
    for(const bus of this.groupPanners.values())bus.disconnect();
    for(const send of this.reverbSends.values())send.disconnect();
    for(const stage of this.widthStages.values()){
      stage.input.disconnect();stage.output.disconnect();
      for(const node of [...stage.direct,...stage.cross])node.disconnect();
    }
    this.widthStages.clear();
    for(const eq of this.eqStages.values())for(const filter of eq)filter.disconnect();
    this.eqStages.clear();
    for(const stage of this.dynamicsStages.values()){
      stage.compressor.disconnect();stage.duckGain.disconnect();
    }
    this.dynamicsStages.clear();this.duckEnvelopes.clear();
    for(const stage of this.spaceStages.values()){
      stage.input.disconnect();stage.output.disconnect();
      for(const node of [...stage.sends,...stage.delays])node.disconnect();
    }
    this.spaceStages.clear();
    this.groupPanners.clear();
    this.reverbSends.clear();
    this.tracks=[];
    this.durationSeconds=0;this.sourceDurationSeconds=0;this.offset=0;
  }
  async dispose(){
    this.disposed=true;
    this.loadController?.abort();
    this.clearTracks();
    this.reverb.disconnect();
    this.reverbDrive.disconnect();
    this.dryMaster.disconnect();
    this.master.disconnect();
    await this.context.close().catch(()=>{});
  }
}

/** Stereo 24-bit PCM WAV. No normalizer/limiter: audible mix and export match. */
function encodeWav24(buffer:AudioBuffer,outputTrimDb:number):Blob{
  const left=buffer.getChannelData(0),right=buffer.getChannelData(1);
  const frames=buffer.length;
  let peak=0;
  for(let i=0;i<frames;i++){
    peak=Math.max(peak,Math.abs(left[i]),Math.abs(right[i]));
  }
  if(!Number.isFinite(peak))throw Error("Rendered audio contains invalid samples; export cancelled.");
  const gain=Math.pow(10,outputTrimDb/20);
  if(peak*gain>1){
    const dbfs=20*Math.log10(peak);
    const needed=SAFE_EXPORT_CEILING_DBFS-dbfs-outputTrimDb;
    // Round safely toward more attenuation, not toward clipping.
    const additional=Math.floor((needed-0.05)*10)/10;
    throw new MixHeadroomError(dbfs,additional);
  }
  const bytes=44+frames*6;
  const array=new ArrayBuffer(bytes);
  const view=new DataView(array);
  const ascii=(offset:number,value:string)=>{
    for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));
  };
  ascii(0,"RIFF");view.setUint32(4,bytes-8,true);ascii(8,"WAVE");
  ascii(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);
  view.setUint16(22,2,true);view.setUint32(24,buffer.sampleRate,true);
  view.setUint32(28,buffer.sampleRate*6,true);view.setUint16(32,6,true);
  view.setUint16(34,24,true);ascii(36,"data");view.setUint32(40,frames*6,true);
  for(let i=0;i<frames;i++){
    const samples=[left[i],right[i]];
    for(let ch=0;ch<2;ch++){
      const sample=Math.max(-1,Math.min(1,samples[ch]*gain));
      const signed=Math.round(sample<0?sample*8388608:sample*8388607);
      const off=44+i*6+ch*3;
      view.setUint8(off,signed&255);
      view.setUint8(off+1,(signed>>8)&255);
      view.setUint8(off+2,(signed>>16)&255);
    }
  }
  return new Blob([array],{type:"audio/wav"});
}

/** Repeatable, band-limited-looking decaying diffuse room response, shared
 * identically by real-time and offline graphs. A deliberately simple MVP IR.
 * No dynamic reverb type changes until profile presets are modeled explicitly.
 */
function createRoomImpulse(context:BaseAudioContext):AudioBuffer{
  const rate=context.sampleRate;
  const length=Math.round(rate*1.7);
  const buffer=context.createBuffer(2,length,rate);
  let seed=0x136597af;
  const random=()=>{
    seed=(Math.imul(1664525,seed)+1013904223)>>>0;
    return (seed/4294967296)*2-1;
  };
  for(let channel=0;channel<2;channel++){
    const data=buffer.getChannelData(channel);
    let energy=0;
    for(let i=0;i<length;i++){
      const time=i/rate;
      const envelope=(1-Math.exp(-time*45))*Math.exp(-time*4.2);
      data[i]=random()*envelope;
      energy+=data[i]*data[i];
    }
    const scale=0.65/Math.sqrt(Math.max(energy,0.000001));
    for(let i=0;i<length;i++)data[i]*=scale;
  }
  return buffer;
}
