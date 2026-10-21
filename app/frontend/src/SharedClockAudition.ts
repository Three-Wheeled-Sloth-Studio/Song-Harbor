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
  private nodes:ActiveNode[]=[];
  private automation:Record<string,{pan?:AutomationPoint[]}>={};
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
    for(const track of this.tracks){
      track.gain.gain.value=Math.max(0,Math.min(1,levels[track.source.filename]?.gain??0));
    }
  }
  /** Pan the reconstructed per-stem stereo bus. Split L/R children retain native routing. */
  setAutomation(curves:Record<string,{pan?:AutomationPoint[]}>){
    this.automation=curves;
    if(this.running)this.seek(this.position);
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
    this.groupPanners.clear();
    this.tracks=[];
    this.durationSeconds=0;this.offset=0;
  }
  async dispose(){
    this.disposed=true;
    this.loadController?.abort();
    this.clearTracks();
    this.master.disconnect();
    await this.context.close().catch(()=>{});
  }
}
