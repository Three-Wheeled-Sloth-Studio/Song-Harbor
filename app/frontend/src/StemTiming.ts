export function stemTimelineStart(start:number,offset:number):number{
  if(!Number.isFinite(start)||start<0||!Number.isFinite(offset)||offset<0||offset>.5)
    throw Error("Invalid stem timing offset");
  return start+offset;
}
export function stemPlaybackWindow(seek:number,start:number,duration:number):
  {delay:number;bufferOffset:number}|null{
  if(!Number.isFinite(seek)||!Number.isFinite(start)||start<0||
    !Number.isFinite(duration)||duration<=0)throw Error("Invalid playback window");
  if(seek>=start+duration)return null;
  return {delay:Math.max(0,start-seek),bufferOffset:Math.max(0,seek-start)};
}
