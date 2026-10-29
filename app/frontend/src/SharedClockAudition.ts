import {solveAutoPan, type AutoPanResult, type AutoStem} from "./AutoPan";
import {replacementCurve, type ReplacementMask} from "./ReplacementMasks";
import {scheduleAutomation, valueAt, type AutomationPoint} from "./SectionAutomation";
import {createStereoWidthStage,scheduleStereoWidth,type StereoWidthStage} from "./StereoWidth";
import {createSpatialReflection,scheduleSpatialReflection,type SpatialReflectionStage} from "./SpatialReflection";
import {createEqStage,scheduleEq,type EqCurves} from "./SectionEq";
import {createDynamicsStage,scheduleCompressor,scheduleDucking,makeDuckingEnvelope,makeDeEssEnvelope,scheduleDeEss,type DynamicsCurves,type DynamicsStage} from "./SectionDynamics";
import {inspectRenderedAudio,type AudioFinding} from "./AudioCleanupAnalyzer";
import {compareAudioStages,type StageComparison} from "./AudioStageComparison";
import {regionSpectrogram} from "./RegionSpectrogram.ts";
import {bandEvidence} from "./StemArtifactAttribution.ts";
import {makeDeclickCandidate} from "./LocalizedDeclick.ts";
import {analyzeSections,type SectionRange,type SectionInsight} from "./SectionInsights.ts";
/**
 * Song Harbor shared-clock audition engine.
 *
 * All decoded stem buffers are scheduled on ONE AudioContext timeline. No
 * HTMLAudioElement clocks, per-stem playbackRate changes, or seeking followers.
 * This intentionally limits the in-memory MVP rather than silently returning
 * to the phase-unsafe multi-stream player.
 */
export type AuditionSource = {key:string;filename:string;url:string;pan:-1|0|1;startSeconds:number;timelinePositioned:boolean};
export type AuditionLevel = {gain:number};
export type DeclickRecipe={id:string;filename:string;source_key:string;time_seconds:number;half_window_ms:number};
type Track = {source:AuditionSource;buffer:AudioBuffer;rawBuffer:AudioBuffer;gain:GainNode;sectionGain:GainNode;scriptVolume:GainNode;replacementGain:GainNode;childGain:GainNode;childEq?:[BiquadFilterNode,BiquadFilterNode,BiquadFilterNode];panner:StereoPannerNode};
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
  private originalPreviewBus:GainNode;
  private sourceDurationSeconds=0;
  private ending={fade_seconds:0,tail_seconds:0,curve:"smooth" as "smooth"|"linear"};
  private tracks:Track[]=[];
  private acceptedDeclick:DeclickRecipe[]=[];
  private previewDeclick:DeclickRecipe|null=null;
  private previewDeclickEnabled=false;
  private repairBuffers=new Map<string,AudioBuffer>();
  private groupPanners=new Map<string,StereoPannerNode>();
  private widthStages=new Map<string,StereoWidthStage>();
  private eqStages=new Map<string,[BiquadFilterNode,BiquadFilterNode,BiquadFilterNode]>();
  private dynamicsStages=new Map<string,DynamicsStage>();
  private spaceStages=new Map<string,SpatialReflectionStage>();
  private reverb:ConvolverNode;
  private reverbDrive:GainNode;
  private referenceOriginal=false;
  private bypassEffects={pan:false,width:false,space:false,reverb:false,ending:false,eq:false,compression:false,ducking:false,deess:false};
  private reverbSends=new Map<string,GainNode>();
  private renderedLevels:Record<string,number>={};
  private monitorLevel=0.75;
  private outputTrimDb=0;
  private nodes:ActiveNode[]=[];
  private candidatePreview:{buffer:AudioBuffer;startSeconds:number;gain:GainNode;source:AudioBufferSourceNode|null;enabled:boolean;blend:number;trimDb:number;solo:boolean}|null=null;
  private replacementMasks:ReplacementMask[]=[];
  private candidateOriginalMix:{filename:string;gain:number}|null=null;
  private automation:Record<string,{gain?:AutomationPoint[];volume?:AutomationPoint[];pan?:AutomationPoint[];reverb?:AutomationPoint[];width?:AutomationPoint[];space?:AutomationPoint[];eq?:EqCurves;dynamics?:DynamicsCurves}>={};
  private duckEnvelopes=new Map<string,AutomationPoint[]>();
  private deessEnvelopes=new Map<string,AutomationPoint[]>();
  get dynamicsMeters(){
    return [...this.dynamicsStages.entries()].map(([filename,stage])=>({filename,
      compressionDb:Math.max(0,-stage.compressor.reduction),
      duckDb:Math.max(0,-20*Math.log10(Math.max(.0001,stage.duckGain.gain.value))),
      deessDb:Math.max(0,-stage.deesser.gain.value)
    }));
  }
  private lastAnalysis:AudioFinding[]=[];
  private lastStageComparison:StageComparison|null=null;
  get stageComparison():StageComparison|null{return this.lastStageComparison;}
  private lastSectionInsights:SectionInsight[]=[];
  get sectionInsights():readonly SectionInsight[]{return this.lastSectionInsights;}
  get cleanupFindings():readonly AudioFinding[]{return this.lastAnalysis;}
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
    this.originalPreviewBus=this.context.createGain();
    this.originalPreviewBus.connect(this.master);
    this.dryMaster=this.context.createGain();
    this.dryMaster.connect(this.originalPreviewBus);
    this.reverb=this.context.createConvolver();
    this.reverb.normalize=false;
    this.reverb.buffer=createRoomImpulse(this.context,0);
    this.reverb.connect(this.originalPreviewBus);
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
  async prepare(sources:AuditionSource[],onProgress?:(ready:number,total:number)=>void,timelineDuration?:number){
    if(this.disposed)throw Error("Audio engine closed");
    if(this.loadController)throw Error("Audio is already loading");
    if(this.tracks.length)throw Error("Audio already prepared");
    if(!sources.length)throw Error("No audio sources");
    this.loadController=new AbortController();
    const signal=this.loadController.signal;
    let bytes=0;
    let maxDuration=0,alignedDuration=0;
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
        if(!src.timelinePositioned&&alignedDuration>0&&Math.abs(buffer.duration-alignedDuration)>0.15){
          throw Error(`Stem lengths differ by more than 150ms (${src.filename}). Re-run separation or repair the source before aligned audition.`);
        }
        if(!src.timelinePositioned)alignedDuration=Math.max(alignedDuration,buffer.duration);
        maxDuration=Math.max(maxDuration,src.startSeconds+buffer.duration);
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
        const sectionGain=this.context.createGain();
        sectionGain.gain.value=1;
        const scriptVolume=this.context.createGain();
        scriptVolume.gain.value=1;
        const replacementGain=this.context.createGain();
        replacementGain.gain.value=1;
        const childGain=this.context.createGain();
        childGain.gain.value=1;
        const childEq=src.key!==src.filename?createEqStage(this.context):undefined;
        gain.connect(sectionGain).connect(scriptVolume).connect(replacementGain).connect(childGain).connect(panner);
        if(childEq){
          panner.connect(childEq[0]);
          childEq[2].connect(this.eqStages.get(src.filename)![0]);
          // A child's send *replaces* the parent's reverb level for that
          // channel, rather than stacking the two sends.
          const childSend=this.context.createGain();
          childSend.gain.value=0;
          childEq[2].connect(childSend).connect(this.reverbDrive);
          this.reverbSends.set(src.key,childSend);
        }else panner.connect(this.eqStages.get(src.filename)![0]);
        gain.gain.value=0;
        this.tracks.push({source:src,buffer,rawBuffer:buffer,gain,sectionGain,scriptVolume,replacementGain,childGain,childEq,panner});
        onProgress?.(i+1,sources.length);
      }
      const duration=timelineDuration&&timelineDuration>0?timelineDuration:maxDuration;
      if(maxDuration>duration+.25)throw Error("A positioned clip extends beyond the song duration.");
      this.sourceDurationSeconds=duration;
      this.durationSeconds=duration+this.ending.tail_seconds;
      this.prepared=true;
    }catch(err){
      this.clearTracks();
      throw err;
    }finally{
      this.loadController=null;
    }
  }
  /** Repair recipes address the source key (including :left/:right split lanes).
   * The immutable decoded source is never edited. Export uses accepted recipes
   * only, while Fix playback can also include an unsaved preview candidate.
   */
  private repairBuffer(track:Track,includeDraft:boolean):AudioBuffer{
    const recipes=[...this.acceptedDeclick,...(includeDraft&&this.previewDeclickEnabled&&this.previewDeclick?[this.previewDeclick]:[])]
      .filter(recipe=>recipe.source_key===track.source.key);
    if(!recipes.length)return track.rawBuffer;
    const source=track.rawBuffer;
    const out=this.context.createBuffer(source.numberOfChannels,source.length,source.sampleRate);
    for(let channel=0;channel<source.numberOfChannels;channel++)
      out.copyToChannel(source.getChannelData(channel),channel);
    for(const recipe of recipes){
      const sourceTime=recipe.time_seconds-track.source.startSeconds;
      if(sourceTime<0||sourceTime>=source.duration)continue;
      const repair=makeDeclickCandidate(out,sourceTime,recipe.half_window_ms,false);
      for(let channel=0;channel<out.numberOfChannels;channel++){
        const row=repair.replacements[channel];
        out.getChannelData(channel).set(row.values,row.startFrame);
      }
    }
    return out;
  }
  setAcceptedDeclick(recipes:readonly DeclickRecipe[]){
    this.acceptedDeclick=[...recipes];
    this.repairBuffers.clear();
    for(const track of this.tracks)track.buffer=this.repairBuffer(track,false);
    this.refreshDuckingEnvelopes();
    this.refreshDeEssEnvelopes();
    if(this.running)this.seek(this.position);
  }
  setPreviewDeclick(recipe:DeclickRecipe|null,enabled:boolean){
    if(JSON.stringify(this.previewDeclick)===JSON.stringify(recipe)&&this.previewDeclickEnabled===enabled)return;
    this.previewDeclick=recipe;
    this.previewDeclickEnabled=enabled;
    this.repairBuffers.clear();
    if(this.running)this.seek(this.position);
  }
  private effectiveBuffer(track:Track):AudioBuffer{
    if(this.referenceOriginal)return track.rawBuffer;
    if(!this.previewDeclick||!this.previewDeclickEnabled||this.previewDeclick.source_key!==track.source.key)
      return track.buffer;
    let buffer=this.repairBuffers.get(track.source.key);
    if(!buffer){buffer=this.repairBuffer(track,true);this.repairBuffers.set(track.source.key,buffer);}
    return buffer;
  }
  /** Return the available physical source lanes for an auditable repair target. */
  get declickSourceKeys():readonly {key:string;filename:string;startSeconds:number}[]{
    return this.tracks.map(t=>({key:t.source.key,filename:t.source.filename,startSeconds:t.source.startSeconds}));
  }
  /** Temporary accompaniment lives only on the shared playback clock, not in project tracks. */
  async loadCandidatePreview(url:string,startSeconds:number){
    if(!this.ready||!Number.isFinite(startSeconds)||startSeconds<0)throw Error("Invalid candidate placement");
    const response=await fetch(url,{cache:"no-store"});
    if(!response.ok)throw Error("Cannot fetch candidate audio");
    const payload=await response.arrayBuffer();
    const buffer=await this.context.decodeAudioData(payload);
    if(this.disposed)throw Error("Audio engine closed");
    if(startSeconds+buffer.duration>this.sourceDurationSeconds+.15)
      throw Error("Candidate extends beyond the song");
    this.clearCandidatePreview();
    const gain=this.context.createGain();
    gain.gain.value=0;
    gain.connect(this.master);
    this.candidatePreview={buffer,startSeconds,gain,source:null,enabled:false,blend:0,trimDb:0,solo:false};
    if(this.running)this.scheduleCandidate(this.context.currentTime+.01,this.position);
  }
  /** A/B the accepted result without attenuating unrelated backing stems.
   * Applies a temporary original-stem region gain during candidate preview only. */
  setCandidateOriginalMix(filename:string,originalPercent:number){
    if(!this.candidatePreview)return;
    const gain=Math.max(0,Math.min(100,originalPercent))/100;
    if(this.candidateOriginalMix?.filename===filename&&this.candidateOriginalMix.gain===gain)return;
    this.candidateOriginalMix={filename,gain};
    if(this.prepared)this.configurePreviewNodes(this.context.currentTime+.03,this.position);
    this.setCandidatePreviewBlend(this.candidatePreview.blend*100);
  }
  setCandidatePreviewEnabled(value:boolean){
    this.setCandidatePreviewBlend(value?100:0);
  }
  /** True Solo is a separate routing state, not a blend approximation. */
  setCandidatePreviewSolo(value:boolean){
    const candidate=this.candidatePreview;
    if(!candidate)return;
    candidate.solo=value;
    this.setCandidatePreviewBlend(candidate.blend*100);
  }
  setCandidatePreviewTrimDb(db:number){
    const candidate=this.candidatePreview;
    if(!candidate)return;
    candidate.trimDb=Math.max(-12,Math.min(9,db));
    this.setCandidatePreviewBlend(candidate.blend*100);
  }
  /** Route every original stem AND wet FX through one mix bus. Solo hard-mutes
   * that bus throughout audition (including preroll); blend attenuates it only
   * inside the candidate interval. No original stems bypass this bus.
   */
  setCandidatePreviewBlend(percent:number,at=this.context.currentTime,offset=this.position){
    const candidate=this.candidatePreview;
    if(!candidate)return;
    const p=Math.max(0,Math.min(100,percent))/100;
    candidate.blend=p;
    candidate.enabled=candidate.solo||p>0;
    const originalLevel=candidate.solo?0:this.candidateOriginalMix?1:Math.cos(p*Math.PI/2);
    const generatedLevel=(candidate.solo?1:Math.sin(p*Math.PI/2))*Math.pow(10,candidate.trimDb/20);
    const now=this.context.currentTime;
    const original=this.originalPreviewBus.gain;
    original.cancelScheduledValues(now);
    // No underlying instrument or reverb can sound while Solo is engaged.
    if(candidate.solo){
      original.setTargetAtTime(0,now,.005);
    }else{
      const clipStart=candidate.startSeconds;
      const clipEnd=clipStart+candidate.buffer.duration;
      const inClip=offset>=clipStart&&offset<clipEnd;
      original.setTargetAtTime(inClip?originalLevel:1,now,.008);
      // Audio nodes are scheduled from a shared future clock, even if the
      // audition was seeking from before the generated clip's beginning.
      if(offset<clipStart){
        const begin=at+clipStart-offset;
        original.setValueAtTime(1,Math.max(now,begin-.02));
        original.linearRampToValueAtTime(originalLevel,begin+.02);
      }
      if(offset<clipEnd){
        const finish=at+clipEnd-offset;
        original.setValueAtTime(originalLevel,Math.max(now,finish-.02));
        original.linearRampToValueAtTime(1,finish+.02);
      }
    }
    candidate.gain.gain.setTargetAtTime(generatedLevel,now,.008);
  }
  candidateWaveform(size=160):number[]{
    const buffer=this.candidatePreview?.buffer;
    if(!buffer)return [];
    const data=buffer.getChannelData(0);
    const peaks:number[]=[];
    for(let i=0;i<size;i++){
      const begin=Math.floor(i*data.length/size),end=Math.max(begin+1,Math.floor((i+1)*data.length/size));
      let peak=0;
      for(let j=begin;j<end;j+=Math.max(1,Math.floor((end-begin)/80)))peak=Math.max(peak,Math.abs(data[j]));
      peaks.push(peak);
    }
    const max=Math.max(.001,...peaks);
    return peaks.map(value=>value/max);
  }
  clearCandidatePreview(){
    const candidate=this.candidatePreview;
    if(!candidate)return;
    try{candidate.source?.stop();}catch{/* already ended */}
    candidate.source?.disconnect();
    candidate.gain.disconnect();
    this.candidatePreview=null;
    this.candidateOriginalMix=null;
    if(this.prepared)this.configurePreviewNodes(this.context.currentTime+.02,this.position);
    this.originalPreviewBus.gain.cancelScheduledValues(this.context.currentTime);
    this.originalPreviewBus.gain.setTargetAtTime(1,this.context.currentTime,.012);
  }
  private scheduleCandidate(at:number,offset:number){
    const candidate=this.candidatePreview;
    if(!candidate)return;
    try{candidate.source?.stop();}catch{/* already ended */}
    candidate.source?.disconnect();
    candidate.source=null;
    const clipEnd=candidate.startSeconds+candidate.buffer.duration;
    if(offset>=clipEnd)return;
    const source=this.context.createBufferSource();
    source.buffer=candidate.buffer;
    source.connect(candidate.gain);
    candidate.source=source;
    this.setCandidatePreviewBlend(candidate.blend*100,at,offset);
    if(offset<=candidate.startSeconds)source.start(at+candidate.startSeconds-offset,0);
    else source.start(at,offset-candidate.startSeconds);
  }

  setLevels(levels:Record<string,AuditionLevel>,monitor:number){
    this.monitorLevel=Math.max(0,Math.min(1,monitor));
    this.updateMasterOutput();
    const nextLevels=Object.fromEntries(Object.entries(levels).map(([key,item])=>[key,Math.max(0,Math.min(2,item.gain))]));
    const changedKeys=new Set(Object.keys(nextLevels).filter(key=>nextLevels[key]!==this.renderedLevels[key]));
    this.renderedLevels=nextLevels;
    for(const track of this.tracks){
      track.gain.gain.setTargetAtTime(nextLevels[track.source.filename]??0,this.context.currentTime,.008);
    }
    // Only a change in the actual key stem requires sidechain recalculation.
    // Never call setAutomation/seek here: fader drags must not restart stems.
    if(changedKeys.size){this.refreshDuckingEnvelopes(changedKeys);this.refreshDeEssEnvelopes();
      if(this.running)this.configurePreviewNodes(this.context.currentTime+.03,this.position);
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
    if(this.ending.fade_seconds===fade_seconds&&this.ending.tail_seconds===tail_seconds&&this.ending.curve===curve)return;
    this.ending={fade_seconds,tail_seconds,curve};
    this.reverb.buffer=createRoomImpulse(this.context,tail_seconds);
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
  /** Wet excitation stays active through the musical fade, then shuts off
   * gently at source end. Convolver return continues into the tail. Unlike
   * the dry fade this envelope does not attenuate the reverberation already
   * generated by earlier notes.
   */
  private wetDrivePoints():AutomationPoint[]{
    if(this.ending.tail_seconds<=0)return this.fadePoints();
    const fadeStart=Math.max(0,this.sourceDurationSeconds-Math.min(0.8,Math.max(.2,this.ending.fade_seconds)));
    return [{time:0,value:1},{time:fadeStart,value:1},
            {time:this.sourceDurationSeconds,value:0}];
  }
  /** Audition-only effect bypass: the saved mix and offline export remain processed. */
  setEffectBypass(effects:{pan:boolean;width:boolean;space:boolean;reverb:boolean;ending:boolean;eq:boolean;compression:boolean;ducking:boolean;deess:boolean}){
    if(Object.keys(effects).every(key=>this.bypassEffects[key as keyof typeof effects]===effects[key as keyof typeof effects]))return;
    this.bypassEffects={...effects};
    if(this.running)this.seek(this.position);
    else this.configurePreviewNodes(this.context.currentTime+0.02,this.offset);
  }
  get comparingOriginal(){return Object.values(this.bypassEffects).every(Boolean);}
  /** Playback-only dry reference for Original/Current/Fix correction comparisons.
   * Retains source timing, static mixer levels, and original L/R routing;
   * omits section gain, EQ, dynamics, width, pan, reflections, reverb and fade.
   * Does not affect offline mix export or saved automation.
   */
  setReferenceOriginal(enabled:boolean){
    if(this.referenceOriginal===enabled)return;
    this.referenceOriginal=enabled;
    if(this.running&&(this.acceptedDeclick.length>0||this.previewDeclick!==null))this.seek(this.position);
    else if(this.prepared)this.configurePreviewNodes(this.context.currentTime+.02,this.position);
  }
  private configurePreviewNodes(at:number,offset:number){
    for(const track of this.tracks){
      const src=track.source;
      scheduleAutomation(track.sectionGain.gain,
        !this.referenceOriginal&&this.automation[src.filename]?.gain||[{time:0,value:1}],offset,at);
      const audition=this.candidatePreview&&this.candidateOriginalMix?.filename===src.filename
        ?[{replacement_track_id:"__audition__",source_track_id:"__audition__",source_filename:src.filename,
            start_seconds:this.candidatePreview.startSeconds,
            end_seconds:this.candidatePreview.startSeconds+this.candidatePreview.buffer.duration,
            fade_seconds:.05,original_gain:this.candidateOriginalMix.gain}]
        :[];
      scheduleAutomation(track.scriptVolume.gain,this.automation[src.filename]?.volume||[{time:0,value:1}],offset,at);
      scheduleAutomation(track.replacementGain.gain,replacementCurve([
        ...this.replacementMasks.filter(mask=>mask.source_filename===src.filename),...audition]),offset,at);
      scheduleAutomation(track.childGain.gain,
        !this.referenceOriginal&&this.automation[src.key]?.gain&&src.key!==src.filename
          ?this.automation[src.key].gain!:[{time:0,value:1}],offset,at);
      scheduleAutomation(track.panner.pan,
        !this.referenceOriginal&&!this.bypassEffects.pan&&src.key!==src.filename&&this.automation[src.key]?.pan
          ?this.automation[src.key].pan!:[{time:0,value:src.pan}],offset,at);
      if(track.childEq)scheduleEq(track.childEq,this.automation[src.key]?.eq||{},
        offset,at,this.referenceOriginal||this.bypassEffects.eq);
      if(src.key!==src.filename){
        const send=this.reverbSends.get(src.key);
        if(send)scheduleAutomation(send.gain,
          !this.referenceOriginal&&!this.bypassEffects.reverb&&
          (this.automation[src.key]?.reverb||this.automation[src.filename]?.reverb)
            ||[{time:0,value:0}],offset,at);
      }
    }
    const bypass=this.referenceOriginal?{pan:true,width:true,space:true,reverb:true,ending:true,eq:true,compression:true,ducking:true,deess:true}:this.bypassEffects;
    for(const [filename,bus] of this.groupPanners){
      const eq=this.eqStages.get(filename);
      if(eq)scheduleEq(eq,this.automation[filename]?.eq||{},offset,at,bypass.eq);
      const dynamics=this.dynamicsStages.get(filename);
      if(dynamics){
        scheduleCompressor(dynamics,bypass.compression?undefined:this.automation[filename]?.dynamics?.compressor,offset,at);
        scheduleDucking(dynamics,bypass.ducking?undefined:this.duckEnvelopes.get(filename),offset,at);
        scheduleDeEss(dynamics,bypass.deess?undefined:this.automation[filename]?.dynamics?.deess,bypass.deess?undefined:this.deessEnvelopes.get(filename),offset,at);
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
        !bypass.reverb&&!this.tracks.some(t=>t.source.filename===filename&&t.source.key!==filename)
          &&this.automation[filename]?.reverb||[{time:0,value:0}],offset,at);
    }
    scheduleAutomation(this.dryMaster.gain,
      bypass.ending?[{time:0,value:1}]:this.fadePoints(),offset,at);
    scheduleAutomation(this.reverbDrive.gain,
      bypass.reverb?[{time:0,value:0}]:bypass.ending?[{time:0,value:1}]:this.wetDrivePoints(),offset,at);
  }
  /** Estimate section dry-bus pan contributions from aligned decoded stems.
   * This is a bounded first-pass solver; final rendered analysis is authoritative.
   */
  solveSectionAutoPan(start:number,end:number,protectedSources:readonly string[],protectedGains:readonly string[],
    curves:Record<string,{gain?:AutomationPoint[];pan?:AutomationPoint[]}>):AutoPanResult{
    const stats=new Map<string,{l:number;r:number;cross:number;n:number}>();
    const fixed=new Set(protectedSources);
    const lockedGains=new Set(protectedGains);
    for(const track of this.tracks){
      const filename=track.source.filename;
      const level=this.renderedLevels[filename]??0;
      if(level<=0)continue;
      const buf=track.buffer,clipStart=track.source.startSeconds;
      const from=Math.max(0,Math.floor((start-clipStart)*buf.sampleRate));
      const to=Math.min(buf.length,Math.ceil((end-clipStart)*buf.sampleRate));
      if(to<=from)continue;
      const step=Math.max(1,Math.floor((to-from)/32000));
      let row=stats.get(filename);
      if(!row){row={l:0,r:0,cross:0,n:0};stats.set(filename,row);}
      const a=buf.getChannelData(0);
      const b=buf.numberOfChannels>1?buf.getChannelData(1):a;
      for(let i=from;i<to;i+=step){
        let l=a[i],r=b[i];
        // Split child tracks arrive as mono; preserve their locked native L/R routing.
        if(track.source.pan===-1){l=a[i];r=0;}
        else if(track.source.pan===1){l=0;r=a[i];}
        row.l+=l*l;row.r+=r*r;row.cross+=l*r;row.n++;
      }
    }
    const time=start+(end-start)*.5;
    const stems:AutoStem[]=[];
    for(const [filename,row] of stats){
      const level=this.renderedLevels[filename]??0;
      const curve=curves[filename];
      const sectionGain=curve?.gain?valueAt(curve.gain,time):1;
      stems.push({filename,leftPower:row.l/Math.max(1,row.n),
        rightPower:row.r/Math.max(1,row.n),
        crossPower:row.cross/Math.max(1,row.n),
        pan:curve?.pan?valueAt(curve.pan,time):0,
        gain:level*sectionGain,locked:fixed.has(filename),gainLocked:lockedGains.has(filename)});
    }
    return solveAutoPan(stems);
  }

  /** Independent non-destructive region mutes, linked to accepted replacement tracks.
   * This is a multiplicative layer, never an edit of the section script's gain curve. */
  setReplacementMasks(masks:ReplacementMask[]){
    // A section automation refresh must not restart playback when masks
    // themselves have not changed.
    if(JSON.stringify(this.replacementMasks)===JSON.stringify(masks))return;
    this.replacementMasks=masks.map(mask=>({...mask}));
    if(this.running)this.seek(this.position);
    else if(this.prepared)this.configurePreviewNodes(this.context.currentTime+.02,this.offset);
  }
  /** Pan the reconstructed per-stem stereo bus. Split L/R children retain native routing. */
  setAutomation(curves:Record<string,{gain?:AutomationPoint[];volume?:AutomationPoint[];pan?:AutomationPoint[];reverb?:AutomationPoint[];width?:AutomationPoint[];space?:AutomationPoint[];eq?:EqCurves;dynamics?:DynamicsCurves}>,liveTrial=false){
    this.automation=curves;
    this.duckEnvelopes.clear();
    this.refreshDuckingEnvelopes();
    this.refreshDeEssEnvelopes();
    if(liveTrial&&this.running){
      // Update existing per-stem AudioParams in place. Do not restart transport
      // on each correction slider movement; offline render still uses saved mix.
      this.configurePreviewNodes(this.context.currentTime+0.03,this.position);
    }else if(this.running)this.seek(this.position);
    else if(this.prepared)this.configurePreviewNodes(this.context.currentTime+0.02,this.offset);
  }
  private refreshDeEssEnvelopes(){
    this.deessEnvelopes.clear();
    for(const [filename,settings] of Object.entries(this.automation)){
      const curve=settings.dynamics?.deess;
      if(!curve)continue;
      const tracks=this.tracks.filter(track=>track.source.filename===filename);
      if(!tracks.length)continue;
      const start=tracks[0].source.startSeconds;
      this.deessEnvelopes.set(filename,makeDeEssEnvelope(
        tracks.map(track=>track.buffer),curve,this.renderedLevels[filename]??0)
        .map(point=>({...point,time:point.time+start})));
    }
  }
  private refreshDuckingEnvelopes(changedKeys?:Set<string>){
    const at=this.context.currentTime+0.03;
    const offset=this.position;
    for(const [filename,settings] of Object.entries(this.automation)){
      const duck=settings.dynamics?.duck;
      if(!duck||changedKeys&&!changedKeys.has(duck.keyFilename))continue;
      const keys=this.tracks.filter(track=>track.source.filename===duck.keyFilename);
      if(!keys.length)continue;
      const gain=this.renderedLevels[duck.keyFilename]??0;
      const start=keys[0].source.startSeconds;
      const envelope=makeDuckingEnvelope(keys.map(track=>track.buffer),duck.depthDb,gain)
        .map(point=>({...point,time:point.time+start}));
      this.duckEnvelopes.set(filename,envelope);
      // Re-schedule only a gain node, never the source/transport graph.
      if(changedKeys&&!this.bypassEffects.ducking){
        const stage=this.dynamicsStages.get(filename);
        if(stage)scheduleDucking(stage,envelope,offset,at);
      }
    }
  }
  /**
   * Deterministic offline bounce from the SAME decoded buffers, stem routing,
   * levels and section curves as playback. Monitoring volume is excluded.
   * Throws rather than silently limiting a clipping mix differently from preview.
   */
  private inspectWithSources(rendered:AudioBuffer):AudioFinding[]{
    const findings=inspectRenderedAudio(rendered,this.outputTrimDb);
    const inputs=this.tracks.map(track=>({
      name:track.source.filename.match(/\\(([^)]+)\\)/)?.[1]||track.source.filename.replace(/\\.[^.]+$/,""),
      startSeconds:track.source.startSeconds,
      level:this.renderedLevels[track.source.filename]??0,
      buffer:track.buffer
    }));
    return findings.map(finding=>{
      const result=bandEvidence(inputs,finding.kind,finding.timeSeconds,finding.durationSeconds);
      return {...finding,sources:result.ranked.map(item=>item.name),
        attribution:result.ranked,attributionUncertain:result.uncertain};
    });
  }

  async analyzeMix(sections:readonly SectionRange[]=[]):Promise<readonly AudioFinding[]>{
    this.lastStageComparison=null;
    const rendered=await this.renderMixBuffer();
    this.lastSectionInsights=analyzeSections(rendered,sections,this.outputTrimDb);
    const processedFindings=this.inspectWithSources(rendered);
    // Independent dry stem reference: no per-section gain/EQ, no pan automation,
    // compression, spatial effects or reverb. Differences are review candidates,
    // not identified regressions until a human evaluates the intent.
    const dry=await this.renderDryReferenceBuffer();
    this.lastStageComparison=compareAudioStages(dry,rendered,this.sourceDurationSeconds);
    this.lastAnalysis=[...processedFindings,...this.lastStageComparison.findings]
      .sort((a,b)=>a.timeSeconds-b.timeSeconds).slice(0,64);
    // Bounded on-demand evidence. Cap tiles and use one already-rendered buffer;
    // never retain a second whole-song PCM copy for the UI.
    for(const finding of this.lastAnalysis.slice(0,20)){
      finding.spectrum=regionSpectrogram(rendered,finding.timeSeconds);
    }
    return this.lastAnalysis;
  }

  private async renderDryReferenceBuffer():Promise<AudioBuffer>{
    if(!this.ready)throw Error("Load audio before creating dry reference");
    const rate=this.context.sampleRate;
    const frames=Math.ceil(this.sourceDurationSeconds*rate);
    if(frames<1||frames>rate*60*15)throw Error("Dry reference exceeds supported duration");
    const context=new OfflineAudioContext(2,frames,rate);
    for(const track of this.tracks){
      const level=this.renderedLevels[track.source.filename]??0;
      if(level<=0||track.source.startSeconds>=this.sourceDurationSeconds)continue;
      const source=context.createBufferSource();
      source.buffer=track.rawBuffer;
      const gain=context.createGain();
      gain.gain.value=level;
      const pan=context.createStereoPanner();
      pan.pan.value=track.source.pan;
      source.connect(gain).connect(pan).connect(context.destination);
      source.start(Math.max(0,track.source.startSeconds));
    }
    return context.startRendering();
  }

  async renderWav24():Promise<Blob>{
    const rendered=await this.renderMixBuffer();
    this.lastStageComparison=null;
    this.lastAnalysis=this.inspectWithSources(rendered);
    return encodeWav24(rendered,this.outputTrimDb);
  }

  private async renderMixBuffer():Promise<AudioBuffer>{
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
    scheduleAutomation(reverbDrive.gain,this.wetDrivePoints(),0,0);
    const convolver=offline.createConvolver();
    convolver.normalize=false;
    convolver.buffer=createRoomImpulse(offline,this.ending.tail_seconds);
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
      const sectionGain=offline.createGain();
      scheduleAutomation(sectionGain.gain,
        this.automation[track.source.filename]?.gain||[{time:0,value:1}],0,0);
      const scriptVolume=offline.createGain();
      scheduleAutomation(scriptVolume.gain,this.automation[track.source.filename]?.volume||[{time:0,value:1}],0,0);
      const replacementGain=offline.createGain();
      scheduleAutomation(replacementGain.gain,replacementCurve(this.replacementMasks.filter(mask=>mask.source_filename===track.source.filename)),0,0);
      const childGain=offline.createGain();
      scheduleAutomation(childGain.gain,
        track.source.key!==track.source.filename&&this.automation[track.source.key]?.gain
          ||[{time:0,value:1}],0,0);
      const childPanCurve=track.source.key!==track.source.filename
        ?this.automation[track.source.key]?.pan:undefined;
      if(childPanCurve)scheduleAutomation(childPan.pan,childPanCurve,0,0);
      source.connect(gain).connect(sectionGain).connect(scriptVolume).connect(replacementGain).connect(childGain).connect(childPan);
      if(track.source.key!==track.source.filename){
        const childEq=createEqStage(offline);
        childPan.connect(childEq[0]);
        scheduleEq(childEq,this.automation[track.source.key]?.eq||{},0,0);
        childEq[2].connect(eqs.get(track.source.filename)![0]);
        const childSend=offline.createGain();
        const wet=this.automation[track.source.key]?.reverb
          ||this.automation[track.source.filename]?.reverb;
        if(wet)scheduleAutomation(childSend.gain,wet,0,0);
        else childSend.gain.value=0;
        childEq[2].connect(childSend).connect(reverbDrive);
      }else childPan.connect(eqs.get(track.source.filename)![0]);
      source.start(track.source.startSeconds);
    }
    for(const [filename,bus] of group){
      const curve=this.automation[filename]?.pan;
      if(curve)scheduleAutomation(bus.pan,curve,0,0);
      const wet=this.automation[filename]?.reverb;
      if(wet&&!this.tracks.some(t=>t.source.filename===filename&&t.source.key!==filename))
        scheduleAutomation(sends.get(filename)!.gain,wet,0,0);
      const width=this.automation[filename]?.width;
      if(width)scheduleStereoWidth(widths.get(filename)!,width,0,0);
      const space=this.automation[filename]?.space;
      if(space)scheduleSpatialReflection(spaces.get(filename)!,space,0,0);
      scheduleEq(eqs.get(filename)!,this.automation[filename]?.eq||{},0,0);
      const dynamics=dynamicsStages.get(filename)!;
      scheduleCompressor(dynamics,this.automation[filename]?.dynamics?.compressor,0,0);
      scheduleDucking(dynamics,this.duckEnvelopes.get(filename),0,0);
      scheduleDeEss(dynamics,this.automation[filename]?.dynamics?.deess,this.deessEnvelopes.get(filename),0,0);
    }
    return offline.startRendering();
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
    const made:{node:ActiveNode;track:Track}[]=[];
    try{
      for(const track of this.tracks){
        const node=this.context.createBufferSource();
        node.buffer=this.effectiveBuffer(track);
        node.connect(track.gain);
        made.push({node,track});
      }
      this.configurePreviewNodes(startAt,offset);
      for(const {node,track} of made){
        const clipStart=track.source.startSeconds,clipEnd=clipStart+track.buffer.duration;
        if(offset>=clipEnd){node.disconnect();continue;}
        if(offset<=clipStart)node.start(startAt+clipStart-offset,0);
        else node.start(startAt,offset-clipStart);
      }
      this.scheduleCandidate(startAt,offset);
      this.nodes=made.map(item=>item.node).filter(node=>node.numberOfOutputs>0);
      this.offset=offset;
      this.startAt=startAt;
      this.running=true;
    }catch(err){
      for(const {node} of made){try{node.stop();}catch{/* not started */}node.disconnect();}
      this.nodes=[];this.running=false;
      throw err;
    }
  }
  private stopSources(){
    if(this.candidatePreview?.source){
      try{this.candidatePreview.source.stop();}catch{/* already stopped */}
      this.candidatePreview.source.disconnect();
      this.candidatePreview.source=null;
    }
    this.running=false;
    this.dryMaster.gain.cancelScheduledValues(this.context.currentTime);
    this.reverbDrive.gain.cancelScheduledValues(this.context.currentTime);
    for(const bus of this.groupPanners.values())bus.pan.cancelScheduledValues(this.context.currentTime);
    for(const send of this.reverbSends.values())send.gain.cancelScheduledValues(this.context.currentTime);
    for(const stage of this.widthStages.values()){
      for(const node of [...stage.direct,...stage.cross])node.gain.cancelScheduledValues(this.context.currentTime);
    }
    for(const stage of this.dynamicsStages.values()){
      for(const param of [stage.compressor.threshold,stage.compressor.ratio,stage.compressor.attack,stage.compressor.release,stage.duckGain.gain,stage.deesser.gain,stage.deesser.frequency,stage.deesser.Q])param.cancelScheduledValues(this.context.currentTime);
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
    this.clearCandidatePreview();
    this.repairBuffers.clear();
    this.prepared=false;
    this.stopSources();
    for(const track of this.tracks){
      track.gain.disconnect();track.sectionGain.disconnect();track.scriptVolume.disconnect();track.replacementGain.disconnect();track.childGain.disconnect();
      track.panner.disconnect();track.childEq?.forEach(eq=>eq.disconnect());
    }
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
      stage.compressor.disconnect();stage.duckGain.disconnect();stage.deesser.disconnect();
    }
    this.dynamicsStages.clear();this.duckEnvelopes.clear();this.deessEnvelopes.clear();
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

/** Repeatable diffuse room response shared by playback and offline exports.
 * With tail enabled, length is extended to retain environmental decay after
 * the dry song ends. Seed, gain, and envelope are deterministic.
 */
function createRoomImpulse(context:BaseAudioContext,tailSeconds=0):AudioBuffer{
  const rate=context.sampleRate;
  const extended=tailSeconds>0;
  const seconds=extended?Math.max(1.7,Math.min(7,tailSeconds+1.25)):1.7;
  const length=Math.round(rate*seconds);
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
      // Existing small room stays unchanged for projects without a tail.
      // Extended atmosphere decays smoothly rather than ending at 1.7 sec.
      const envelope=(1-Math.exp(-time*45))*Math.exp(-time*(extended?1.3:4.2));
      data[i]=random()*envelope;
      energy+=data[i]*data[i];
    }
    const scale=0.65/Math.sqrt(Math.max(energy,0.000001));
    for(let i=0;i<length;i++)data[i]*=scale;
  }
  return buffer;
}
