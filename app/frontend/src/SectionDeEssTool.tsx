import {useEffect,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SavedPanTarget} from "./SectionPanTool";
import type {SavedReverbTarget} from "./SectionReverbTool";
import type {SavedWidthTarget} from "./SectionWidthTool";
import type {SavedSpaceTarget} from "./SectionSpaceTool";
import type {SavedEqTarget} from "./SectionEqTool";

type Target={section_id:string;source_key:string;kind:"comp"|"duck"|"deess";
  frequency?:number;q?:number;threshold_db:number;max_reduction_db?:number;
  ratio:number;depth_db:number;transition_seconds:number;curve:"smooth"|"linear"};
type Result={sections:SongSection[];pan_targets:SavedPanTarget[];reverb_targets:SavedReverbTarget[];
  width_targets:SavedWidthTarget[];space_targets:SavedSpaceTarget[];eq_targets:SavedEqTarget[];
  dynamics_targets:Target[];ending:{fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"}};
export function SectionDeEssTool({jobId,sections,files,initialSectionId,targets,onSaved}:{
  jobId:string;sections:SongSection[];files:string[];initialSectionId?:string;
  targets:Target[];onSaved:(result:Result)=>void;
}){
  const [source,setSource]=useState(files.find(file=>file.includes("(Vocals)"))||files[0]||"");
  const [frequency,setFrequency]=useState(6500);
  const [q,setQ]=useState(2);
  const [threshold,setThreshold]=useState(-40);
  const [maxReduction,setMaxReduction]=useState(4);
  const [transition,setTransition]=useState(2);
  const [saving,setSaving]=useState(false);
  const [status,setStatus]=useState("");
  const sectionId=initialSectionId||sections[0]?.id||"";
  useEffect(()=>{
    const target=targets.filter(item=>item.kind==="deess"&&item.source_key===source&&item.section_id===sectionId).at(-1);
    setFrequency(target?.frequency??6500);
    setQ(target?.q??2);
    setThreshold(target?.threshold_db??-40);
    setMaxReduction(target?.max_reduction_db??4);
    setTransition(target?.transition_seconds??2);
  },[sectionId,source,targets]);
  async function apply(){
    if(!source||!sectionId)return;
    setSaving(true);setStatus("");
    try{
      const alias=source.match(/\(([^)]+)\)/)?.[1];
      if(!alias)throw Error("This track has no production script alias.");
      const response=await fetch("/api/projects/"+jobId+"/sections/export",{cache:"no-store"});
      const existing=await response.json() as {content?:string;detail?:string};
      if(!response.ok||!existing.content)throw Error(existing.detail||"Could not read section script.");
      const lines=existing.content.split("\n");
      const headers=lines.flatMap((line,i)=>/^\[[^\n]+\]$/.test(line.trim())?[i]:[]);
      const index=sections.findIndex(item=>item.id===sectionId);
      const start=headers[index];
      if(start===undefined)throw Error("Section ordering changed. Reload and retry.");
      const end=headers[index+1]??lines.length;
      let block=-1;
      for(let i=start+1;i<end;i++)if(/^\{.*\}$/.test(lines[i].trim())){block=i;break;}
      const instruction=`${alias}.deess:${frequency},${q},${threshold},${maxReduction}@${transition}s:smooth`;
      if(block<0)lines.splice(start+1,0,"{"+instruction+"}");
      else {
        const tokens=lines[block].trim().slice(1,-1).trim().split(/\s+/).filter(Boolean);
        lines[block]="{"+[...tokens.filter(token=>!token.toLowerCase().startsWith(alias.toLowerCase()+".deess:")),instruction].join(" ")+"}";
      }
      const imported=await fetch("/api/projects/"+jobId+"/sections/import",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content:lines.join("\n"),mode:"replace"})
      });
      const data=await imported.json() as Result & {detail?:string};
      if(!imported.ok)throw Error(data.detail||"De-esser script validation failed.");
      onSaved(data);
      setStatus("Saved to this section's production script.");
    }catch(error){setStatus(error instanceof Error?error.message:"Could not save de-esser.");}
    finally{setSaving(false);}
  }
  const control=(label:string,value:number,min:number,max:number,step:number,change:(next:number)=>void,units="")=>
    <label className="song-deess-control">{label} <strong>{value}{units}</strong>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e=>change(Number(e.target.value))}/>
    </label>;
  return <div className="song-section-deess" aria-label="Section de-esser">
    <label>Track
      <select value={source} onChange={e=>setSource(e.target.value)}>
        {files.map(file=><option key={file} value={file}>{file.match(/\(([^)]+)\)/)?.[1]||file}</option>)}
      </select>
    </label>
    {control("Center frequency",frequency,3000,11000,100,setFrequency," Hz")}
    {control("Bandwidth (Q)",q,.4,8,.1,setQ)}
    {control("Detector threshold",threshold,-70,-10,1,setThreshold," dBFS")}
    {control("Maximum reduction",maxReduction,0,12,.5,setMaxReduction," dB")}
    {control("Transition",transition,.5,5,.5,setTransition," s")}
    <button type="button" disabled={!sectionId||saving} onClick={()=>{void apply();}}>
      {saving?"Applying…":"Apply to section"}
    </button>
    {status&&<small role="status">{status}</small>}
    <small>This filter is driven by high-frequency energy. Test it against cymbals and intended industrial texture before accepting.</small>
  </div>;
}
