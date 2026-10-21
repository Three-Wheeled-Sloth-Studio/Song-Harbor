import {scheduleAutomation, type AutomationPoint} from "./SectionAutomation";
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

export class SharedClockAudition {
  readonly context:AudioContext;
  private master:GainNode;
  private tracks:Track[]=[];
  private groupPanners=new Map<string,StereoPannerNode>();
  private reverb:ConvolverNode;
  private reverbSends=new Map<string,GainNode>();
  private renderedLevels:Record<string,number>={};
  private nodes:ActiveNode[]=[];
  private automation:Record<string,{pan?:AutomationPoint[];reverb?:AutomationPoint[]}>={};
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
    this.reverb=this.context.createConvolver();
    this.reverb.normalize=false;
    this.reverb.buffer=createRoomImpulse(this.context);
    this.reverb.connect(this.master);
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
          bus.connect(this.master);
          const send=this.context.createGain();
          send.gain.value=0;
          bus.connect(send).connect(this.reverb);
          this.reverbSends.set(src.filename,send);
          this.groupPanners.set(src.filename,bus);
        }
        let panner:StereoPannerNode|undefined;
        panner=this.context.createStereoPanner();
        panner.pan.value=src.pan;
        gain.connect(panner).connect(bus);
        gain.gain.value=0;
        this.tracks.push({source:src,buffer,gain,panner});
        onProgress?.(i+1,sources.length);
      }
      this.durationSeconds=maxDuration;
      this.prepared=true;
    }catch(err){
      this.clearTracks();
      throw err;
    }finally{
      this.loadController=null;
    }
  }
  setLevels(levels:Record<string,AuditionLevel>,monitor:number){
    this.master.gain.value=Math.max(0,Math.min(1,monitor));
    this.renderedLevels=Object.fromEntries(Object.entries(levels).map(([key,item])=>[key,Math.max(0,Math.min(2,item.gain))]));
    for(const track of this.tracks){
      track.gain.gain.value=Math.max(0,Math.min(1,levels[track.source.filename]?.gain??0));
    }
  }
  /** Pan the reconstructed per-stem stereo bus. Split L/R children retain native routing. */
  setAutomation(curves:Record<string,{pan?:AutomationPoint[];reverb?:AutomationPoint[]}>){
    this.automation=curves;
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
    const convolver=offline.createConvolver();
    convolver.normalize=false;
    convolver.buffer=createRoomImpulse(offline);
    convolver.connect(offline.destination);
    const sends=new Map<string,GainNode>();
    for(const track of this.tracks){
      let bus=group.get(track.source.filename);
      if(!bus){
        bus=offline.createStereoPanner();
        bus.pan.value=0;
        bus.connect(offline.destination);
        const send=offline.createGain();
        send.gain.value=0;
        bus.connect(send).connect(convolver);
        sends.set(track.source.filename,send);
        group.set(track.source.filename,bus);
      }
      const source=offline.createBufferSource();
      source.buffer=track.buffer;
      const gain=offline.createGain();
      gain.gain.value=this.renderedLevels[track.source.filename]??0;
      const childPan=offline.createStereoPanner();
      childPan.pan.value=track.source.pan;
      source.connect(gain).connect(childPan).connect(bus);
      source.start(0);
    }
    for(const [filename,bus] of group){
      const curve=this.automation[filename]?.pan;
      if(curve)scheduleAutomation(bus.pan,curve,0,0);
      const wet=this.automation[filename]?.reverb;
      if(wet)scheduleAutomation(sends.get(filename)!.gain,wet,0,0);
    }
    const rendered=await offline.startRendering();
    return encodeWav24(rendered);
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
      for(const [filename,bus] of this.groupPanners){
        const curve=this.automation[filename]?.pan;
        if(curve)scheduleAutomation(bus.pan,curve,offset,startAt);
        else{
          bus.pan.cancelScheduledValues(startAt);
          bus.pan.setValueAtTime(0,startAt);
        }
        const send=this.reverbSends.get(filename);
        if(send){
          const wet=this.automation[filename]?.reverb;
          if(wet)scheduleAutomation(send.gain,wet,offset,startAt);
          else{send.gain.cancelScheduledValues(startAt);send.gain.setValueAtTime(0,startAt);}
        }
      }
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
    for(const bus of this.groupPanners.values())bus.pan.cancelScheduledValues(this.context.currentTime);
    for(const send of this.reverbSends.values())send.gain.cancelScheduledValues(this.context.currentTime);
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
    this.groupPanners.clear();
    this.reverbSends.clear();
    this.tracks=[];
    this.durationSeconds=0;this.offset=0;
  }
  async dispose(){
    this.disposed=true;
    this.loadController?.abort();
    this.clearTracks();
    this.reverb.disconnect();
    this.master.disconnect();
    await this.context.close().catch(()=>{});
  }
}

/** Stereo 24-bit PCM WAV. No normalizer/limiter: audible mix and export match. */
function encodeWav24(buffer:AudioBuffer):Blob{
  const left=buffer.getChannelData(0),right=buffer.getChannelData(1);
  const frames=buffer.length;
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
  let peak=0;
  for(let i=0;i<frames;i++){
    peak=Math.max(peak,Math.abs(left[i]),Math.abs(right[i]));
  }
  if(!Number.isFinite(peak)||peak>1.00001)
    throw Error("Rendered mix peaks above 0 dBFS. Lower stem gains and retry to avoid clipping.");
  for(let i=0;i<frames;i++){
    const samples=[left[i],right[i]];
    for(let ch=0;ch<2;ch++){
      const sample=Math.max(-1,Math.min(1,samples[ch]));
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
