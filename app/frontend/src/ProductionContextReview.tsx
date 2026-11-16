import {useCallback,useEffect,useState} from "react";
import {Button} from "@tws-ui/core/react";

type Tone="intimate"|"restrained"|"ominous"|"rising"|"expansive"|"driving"|"suspended"|"neutral";
type Entry={tone:Tone;origin:"author"|"q4-reviewed";note:string;source_run_id?:string;source_sha256?:string};
type Context={schema_version:1;revision:number;sections:Record<string,Entry>};
type Listening={available:boolean;section_id?:string;run_id?:string;source_sha256?:string;review?:string;warning?:string};
type Section={id:string;kind:string;number:number|null};
const TONES:Tone[]=["intimate","restrained","ominous","rising","expansive","driving","suspended","neutral"];
const LABELS:Record<Tone,string>={
  intimate:"Intimate",restrained:"Restrained",ominous:"Ominous",
  rising:"Rising",expansive:"Expansive",driving:"Driving",
  suspended:"Suspended",neutral:"Neutral"
};
export function ProductionContextReview({projectId,sections,onSaved}:{
  projectId:string;sections:readonly Section[];onSaved:()=>void;
}){
  const [selected,setSelected]=useState("");
  const [current,setCurrent]=useState<Context|null>(null);
  const [listening,setListening]=useState<Listening>({available:false});
  const [tone,setTone]=useState<Tone>("neutral");
  const [note,setNote]=useState("");
  const [source,setSource]=useState<"author"|"q4-reviewed">("author");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [message,setMessage]=useState("");
  const route="/api/projects/"+encodeURIComponent(projectId);
  const reload=useCallback(async()=>{
    const [ctxResponse,listenResponse]=await Promise.all([
      fetch(route+"/production-context",{cache:"no-store"}),
      fetch(route+"/production-listening",{cache:"no-store"})]);
    const context=await ctxResponse.json() as Context&{detail?:string};
    const observation=await listenResponse.json() as Listening&{detail?:string};
    if(!ctxResponse.ok||!listenResponse.ok)
      throw Error(context.detail||observation.detail||"ERROR: Could not load listening context.");
    setCurrent(context);setListening(observation);
    return context;
  },[route]);
  useEffect(()=>{
    let alive=true;
    setBusy(true);setError("");
    void reload().catch(e=>{if(alive)setError(String(e));})
      .finally(()=>{if(alive)setBusy(false);});
    return()=>{alive=false;};
  },[reload]);
  useEffect(()=>{
    if(!selected||!sections.some(section=>section.id===selected))
      setSelected(sections[0]?.id||"");
  },[sections,selected]);
  useEffect(()=>{
    const item=current?.sections[selected];
    setTone(item?.tone||"neutral");
    setNote(item?.note||"");
    setSource(item?.origin||"author");
  },[current,selected]);
  const q4=!!listening.available&&listening.section_id===selected&&
    !!listening.run_id&&!!listening.source_sha256;
  async function save(remove=false){
    if(!current||!selected)return;
    setBusy(true);setError("");setMessage("");
    try{
      if(!remove&&source==="q4-reviewed"&&!q4)
        throw Error("ERROR: No complete, section-matched Q4 review is available.");
      const sectionsNext={...current.sections};
      if(remove)delete sectionsNext[selected];
      else sectionsNext[selected]={
        tone,origin:source,note:note.trim(),
        ...(source==="q4-reviewed"?{
          source_run_id:listening.run_id,source_sha256:listening.source_sha256}: {})
      } as Entry;
      const response=await fetch(route+"/production-context",{
        method:"PATCH",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({revision:current.revision,sections:sectionsNext})
      });
      const result=await response.json() as Context&{detail?:string};
      if(!response.ok)throw Error(result.detail||"ERROR: Could not save reviewed context.");
      setCurrent(result);
      setMessage(remove?"Review cleared.":"Reviewed direction saved.");
      onSaved();
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  return <details className="planner-context">
    <summary>Reviewed listening context ({Object.keys(current?.sections||{}).length})</summary>
    <div className="setting-controls">
      <label>Section
        <select value={selected} aria-label="Production context section" onChange={e=>setSelected(e.target.value)}>
          {sections.map(section=><option key={section.id} value={section.id}>
            {section.kind}{section.number?" "+section.number:""}
          </option>)}
        </select>
      </label>
      <label>Direction
        <select value={tone} aria-label="Reviewed production tone"
          onChange={e=>setTone(e.target.value as Tone)}>
          {TONES.map(value=><option key={value} value={value}>{LABELS[value]}</option>)}
        </select>
      </label>
      <label>Basis
        <select value={source} aria-label="Listening direction evidence" onChange={e=>setSource(e.target.value as "author"|"q4-reviewed")}>
          <option value="author">My listening / intent</option>
          {q4&&<option value="q4-reviewed">Q4 reviewed by me</option>}
        </select>
      </label>
      <label>Note (optional)
        <input value={note} maxLength={240} aria-label="Reviewed production note" placeholder="Short production intent"
          onChange={e=>setNote(e.target.value)}/>
      </label>
    </div>
    {q4&&<details><summary>Q4 review for this section (unverified)</summary>
      <p className="setting-path">{listening.warning}</p>
      <div className="setting-path" style={{maxHeight:150,overflow:"auto",whiteSpace:"pre-wrap"}}>{listening.review}</div>
    </details>}
    <div className="setting-tool-row">
      <Button size="compact" variant="primary" disabled={busy||!current||!selected}
        onClick={()=>void save()}>Save direction</Button>
      <Button size="compact" variant="secondary" disabled={busy||!current?.sections[selected]}
        onClick={()=>void save(true)}>Clear</Button>
      <Button size="compact" variant="secondary" disabled={busy}
        onClick={()=>{setBusy(true);void reload().then(()=>setMessage("Context refreshed."))
          .catch(e=>setError(String(e))).finally(()=>setBusy(false));}}>Refresh</Button>
    </div>
    {message&&<small role="status">{message}</small>}
    {error&&<p className="error-message" role="alert">{error}</p>}
  </details>;
}
