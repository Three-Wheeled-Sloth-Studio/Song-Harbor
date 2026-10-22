import {useEffect,useRef,useState,type ReactNode,type PointerEvent} from "react";
export type WorkbenchTool="sectionEdit"|"cleanup"|"ab"|"ending"|"zoom"|"loop"|"channels"|"download";
export const TOOL_ITEMS:{id:WorkbenchTool;icon:string;label:string}[]=[
  {id:"sectionEdit",icon:"≡",label:"Edit sections"},
  {id:"cleanup",icon:"◇",label:"Sound cleanup"},
  {id:"ab",icon:"◉",label:"A/B comparison"},
  {id:"ending",icon:"⇥",label:"Ending"},
  {id:"zoom",icon:"⌕",label:"Zoom"},
  {id:"loop",icon:"↻",label:"Region loop"},
  {id:"channels",icon:"◫",label:"Split channels"},
  {id:"download",icon:"⇩",label:"Download"}
];
export function ToolWindow({name,onClose,children,order=0,onFocus}:{name:string;onClose:()=>void;children:ReactNode;order?:number;onFocus?:()=>void}){
  const [pos,setPos]=useState<{x:number;y:number}|null>(null);
  const initialPlacement=useRef({right:75+order*24,top:90+order*26});
  const drag=useRef<{x:number;y:number;startX:number;startY:number}|null>(null);
  const previousFocus=useRef<HTMLElement|null>(null);
  const first=useRef<HTMLButtonElement|null>(null);
  useEffect(()=>{
    previousFocus.current=document.activeElement as HTMLElement;
    // Never steal keyboard transport focus when opening supplementary tools.
    return()=>previousFocus.current?.focus();
  },[]);
  function begin(e:PointerEvent<HTMLElement>){
    if(e.button!==0)return;
    const parent=e.currentTarget.parentElement;
    if(!parent)return;
    const rect=parent.getBoundingClientRect();
    drag.current={x:e.clientX,y:e.clientY,startX:rect.left,startY:rect.top};
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function move(e:PointerEvent<HTMLElement>){
    if(!drag.current)return;
    const nextX=drag.current.startX+e.clientX-drag.current.x;
    const nextY=drag.current.startY+e.clientY-drag.current.y;
    setPos({x:Math.max(0,Math.min(window.innerWidth-80,nextX)),y:Math.max(0,Math.min(window.innerHeight-60,nextY))});
  }
  return <section className="song-floating-tool" role="dialog" aria-label={name}
      onPointerDown={onFocus}
      style={{...(pos?{left:pos.x,top:pos.y,right:"auto"}:initialPlacement.current),zIndex:110+order}}
      onKeyDown={e=>{if(e.key==="Escape"){e.stopPropagation();onClose();}}}>
    <div className="song-floating-tool-header" onPointerDown={begin} onPointerMove={move}
      onPointerUp={()=>{drag.current=null;}} onPointerCancel={()=>{drag.current=null;}}>
      <strong>{name}</strong>
      <button ref={first} type="button" aria-label={"Close "+name} title="Dismiss tool" onPointerDown={e=>e.stopPropagation()} onClick={onClose}>×</button>
    </div>
    <div className="song-floating-tool-content">{children}</div>
  </section>;
}
