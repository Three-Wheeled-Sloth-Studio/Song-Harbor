import {useRef,useState,type PointerEvent} from "react";

export type CaptionCue={start:number;end:number;text:string};
const TIMING=/^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})$/;
const MIN=.1;
function seconds(h:string,m:string,s:string,ms:string){return Number(h)*3600+Number(m)*60+Number(s)+Number(ms)/1000;}
export function parseSrt(content:string):CaptionCue[]{
  return content.replace(/\r/g,"").trim().split(/\n\s*\n/).filter(Boolean).map((block,index)=>{
    const lines=block.split("\n");
    const stamp=lines[1]?.match(TIMING);
    if(!/^\d+$/.test(lines[0]||"")||!stamp||lines.length<3)throw Error("Invalid SRT caption block "+(index+1));
    const start=seconds(stamp[1],stamp[2],stamp[3],stamp[4]);
    const end=seconds(stamp[5],stamp[6],stamp[7],stamp[8]);
    if(end-start<MIN||!lines.slice(2).join("\n").trim())throw Error("Invalid SRT caption duration or text at block "+(index+1));
    return {start,end,text:lines.slice(2).join("\n")};
  });
}
function srtStamp(value:number){
  const ms=Math.round(Math.max(0,value)*1000);
  return [Math.floor(ms/3600000),Math.floor(ms/60000)%60,Math.floor(ms/1000)%60].map(n=>String(n).padStart(2,"0")).join(":")+","+String(ms%1000).padStart(3,"0");
}
export function renderSrt(cues:CaptionCue[]):string{
  return cues.map((cue,index)=>(index+1)+"\n"+srtStamp(cue.start)+" --> "+srtStamp(cue.end)+"\n"+cue.text.trim()).join("\n\n")+"\n";
}
function clock(value:number){const m=Math.floor(value/60);return m+":"+String(Math.floor(value%60)).padStart(2,"0")+"."+String(Math.round((value%1)*1000)).padStart(3,"0");}
export function SrtTimelineEditor({value,onChange,position,duration,playing,onSeek,onTogglePlay,onSave,saving}:{
 value:string;onChange:(next:string)=>void;position:number;duration:number;playing:boolean;onSeek:(time:number)=>void;onTogglePlay:()=>void;onSave:()=>void;saving:boolean;
}){
 const [selected,setSelected]=useState(0);
 const [zoom,setZoom]=useState(1);
 const [scroll,setScroll]=useState(0);
 const [error,setError]=useState("");
 const drag=useRef<{index:number;edge:"start"|"end";rect:DOMRect;rangeStart:number;rangeEnd:number}|null>(null);
 let cues:CaptionCue[]=[];
 try{cues=parseSrt(value);}
 catch(e){return <div role="alert">Cannot show timing editor: {String(e)}. Repair SRT text below.</div>;}
 const full=Math.max(duration,...cues.map(c=>c.end),1);
 const windowSize=Math.min(full,Math.max(8,full/zoom));
 const left=Math.min(Math.max(0,scroll),Math.max(0,full-windowSize));
 const right=left+windowSize;
 const active=cues.findIndex(c=>position>=c.start&&position<c.end);
 function commit(next:CaptionCue[]){onChange(renderSrt(next));}
 function adjust(index:number,edge:"start"|"end",value:number){
   const next=cues.map(c=>({...c}));
   const cue=next[index];if(!cue)return;
   if(edge==="start")cue.start=Math.max(index?next[index-1].end:0,Math.min(value,cue.end-MIN));
   else cue.end=Math.min(index+1<next.length?next[index+1].start:full,Math.max(value,cue.start+MIN));
   commit(next);
 }
 function begin(event:PointerEvent<HTMLButtonElement>,index:number,edge:"start"|"end"){
   event.preventDefault();event.stopPropagation();
   const rect=event.currentTarget.parentElement?.parentElement?.getBoundingClientRect();
   if(!rect)return;
   drag.current={index,edge,rect,rangeStart:left,rangeEnd:right};
   event.currentTarget.setPointerCapture(event.pointerId);
 }
 function move(event:PointerEvent<HTMLButtonElement>){
   const d=drag.current;if(!d)return;
   const next=d.rangeStart+(event.clientX-d.rect.left)/d.rect.width*(d.rangeEnd-d.rangeStart);
   adjust(d.index,d.edge,Math.round(next*1000)/1000);
 }
 function add(){const at=Math.max(0,Math.min(position,full-MIN));const insertion=cues.findIndex(c=>c.start>at);
   const idx=insertion<0?cues.length:insertion;
   const start=idx>0?Math.max(at,cues[idx-1].end):at;
   const end=idx<cues.length?Math.min(start+2,cues[idx].start):Math.min(full,start+2);
   if(end-start<MIN){setError("No gap here. Adjust neighboring captions before adding.");return;}
   const next=[...cues];next.splice(idx,0,{start,end,text:"New lyric"});commit(next);setSelected(idx);setError("");
 }
 function merge(){const a=cues[selected],b=cues[selected+1];if(!a||!b)return;
   const lines=(a.text+"\n"+b.text).split("\n");
   if(lines.length>3){setError("Maximum three lyric lines per block. Edit text before merging.");return;}
   const next=cues.slice();next.splice(selected,2,{start:a.start,end:b.end,text:lines.join("\n")});commit(next);setError("");
 }
 function remove(){if(!cues[selected])return;commit(cues.filter((_,i)=>i!==selected));setSelected(Math.max(0,selected-1));}
 function split(){const c=cues[selected];if(!c||position<=c.start+MIN||position>=c.end-MIN)return;
   const rows=c.text.split("\n");if(rows.length<2){setError("Split needs at least two lyric lines.");return;}
   const n=cues.slice();n.splice(selected,1,{start:c.start,end:position,text:rows[0]},{start:position,end:c.end,text:rows.slice(1).join("\n")});commit(n);setError("");
 }
 return <div className="song-srt-editor">
   <div className="song-srt-toolbar">
     <strong>Lyric timeline</strong>
     <button type="button" onClick={onTogglePlay}>{playing?"Pause":"Play"}</button>
     <span className="timecode">{clock(position)} / {clock(full)}</span>
     <label>Zoom <select value={zoom} onChange={e=>{setZoom(Number(e.target.value));setScroll(Math.max(0,position-8));}}>{[1,2,4,8,16].map(n=><option key={n} value={n}>{n}x</option>)}</select></label>
     <button type="button" onClick={()=>{setScroll(Math.max(0,position-windowSize/2));}}>Follow playhead</button>
     <button type="button" onClick={add}>Add</button>
     <button type="button" onClick={split} disabled={selected<0}>Split at playhead</button>
     <button type="button" onClick={merge} disabled={selected>=cues.length-1}>Merge next</button>
     <button type="button" onClick={remove} disabled={!cues.length}>Remove</button>
     <button type="button" onClick={onSave} disabled={saving||!cues.length}>{saving?"Saving...":"Save timing"}</button>
   </div>
   <input aria-label="Lyric timeline scroll" type="range" min="0" max={Math.max(0,full-windowSize)} step=".1" value={left} onChange={e=>setScroll(Number(e.target.value))} disabled={zoom===1}/>
   <div className="song-srt-track" role="group" aria-label="Drag lyric cue edges to align with playback" onClick={e=>{const r=e.currentTarget.getBoundingClientRect();onSeek(left+(e.clientX-r.left)/r.width*windowSize);}}>
     {cues.map((cue,i)=>{if(cue.end<left||cue.start>right)return null;
       return <div key={i} className={"song-srt-cue"+(i===active?" is-active":"")+(i===selected?" is-selected":"")}
         style={{left:Math.max(0,(cue.start-left)/windowSize*100)+"%",width:Math.min(100,Math.max(.3,(Math.min(cue.end,right)-Math.max(cue.start,left))/windowSize*100))+"%"}}
         onClick={e=>{e.stopPropagation();setSelected(i);onSeek(cue.start);}}>
         <button type="button" aria-label={"Drag start of caption "+(i+1)} className="song-srt-handle" onPointerDown={e=>begin(e,i,"start")} onPointerMove={move} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}/>
         <span>{cue.text.replace(/\n/g," / ")}</span>
         <button type="button" aria-label={"Drag end of caption "+(i+1)} className="song-srt-handle" onPointerDown={e=>begin(e,i,"end")} onPointerMove={move} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}/>
       </div>;
     })}
     <div className="song-srt-playhead" style={{left:((position-left)/windowSize*100)+"%"}}/>
   </div>
   <div className="song-srt-cue-list">
     {cues.map((c,i)=><button key={i} type="button" className={"song-srt-list-cue"+(i===active?" is-active":"")+(i===selected?" is-selected":"")}
      onClick={()=>{setSelected(i);onSeek(c.start);setScroll(Math.max(0,c.start-2));}}>
      <span>{clock(c.start)} - {clock(c.end)}</span><span>{c.text.replace(/\n/g," / ")}</span></button>)}
   </div>
   {cues[selected]&&<div className="song-srt-selected">
     <label>Start <input aria-label="Selected caption start seconds" type="number" step=".001" min="0" value={cues[selected].start} onChange={e=>adjust(selected,"start",Number(e.target.value))}/></label>
     <label>End <input aria-label="Selected caption end seconds" type="number" step=".001" min="0" value={cues[selected].end} onChange={e=>adjust(selected,"end",Number(e.target.value))}/></label>
     <label>Lyrics (up to three lines) <textarea value={cues[selected].text} rows={3} onChange={e=>{const rows=e.target.value.split("\n");if(rows.length>3)return;const next=cues.slice();next[selected]={...next[selected],text:e.target.value};commit(next);}}/></label>
   </div>}
   {error&&<small role="alert">{error}</small>}
 </div>;
}
