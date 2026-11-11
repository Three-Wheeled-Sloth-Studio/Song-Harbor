import {useEffect,useState} from "react";
import {Button,Status} from "@tws-ui/core/react";

type Anchor={id:string;sample:number;bpm:number;transition:"step"|"linear";origin:"author"|"accepted-candidate";meter:[number,number];section_id?:string};
type Observation={id:string;start_sample:number;end_sample:number;method:string;bpm:number|null;status:string;alternatives:number[];confidence?:number|null;source_sha256?:string;provider?:string;source_revision?:string;evidence?:string};
type TempoMap={schema_version:1;asset_id:string;revision:number;sample_rate:number;duration_samples:number;anchors:Anchor[];observations:Observation[]};
type Section={id:string;kind:string;number:number|null;start_seconds:number;end_seconds:number};

function identifier():string{
  return Array.from(crypto.getRandomValues(new Uint8Array(16))).map(byte=>byte.toString(16).padStart(2,"0")).join("");
}
function stamp(sample:number){const seconds=sample/48000;return Math.floor(seconds/60)+":"+String(Math.floor(seconds%60)).padStart(2,"0")+"."+String(Math.round(seconds%1*1000)).padStart(3,"0");}

export function TempoMapTool({projectId,durationSeconds,sections}:{projectId:string;durationSeconds:number;sections:Section[]}){
  const [asset,setAsset]=useState<TempoMap|null>(null);
  const [draft,setDraft]=useState<Anchor[]>([]);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [seconds,setSeconds]=useState("0");
  const [bpm,setBpm]=useState("");
  const [transition,setTransition]=useState<"step"|"linear">("step");
  const [meter,setMeter]=useState("4/4");
  const [selectedSection,setSelectedSection]=useState("");
  const url="/api/projects/"+encodeURIComponent(projectId)+"/tempo-map";
  async function api<T>(method:string,body?:object):Promise<T>{
    const response=await fetch(url,{method,headers:body?{"Content-Type":"application/json"}:undefined,
      body:body?JSON.stringify(body):undefined});
    const data=await response.json() as T&{detail?:string};
    if(!response.ok)throw Error(data.detail||"Tempo map request failed");
    return data;
  }
  async function reload(){
    const result=await api<{asset:TempoMap|null}>("GET");
    setAsset(result.asset);setDraft(result.asset?.anchors||[]);
  }
  useEffect(()=>{
    let alive=true;
    setLoading(true);
    void fetch(url).then(async response=>{
      const data=await response.json() as {asset:TempoMap|null;detail?:string};
      if(!response.ok)throw Error(data.detail||"Could not load tempo map");
      if(alive){setAsset(data.asset);setDraft(data.asset?.anchors||[]);}
    }).catch(e=>{if(alive)setError(String(e));}).finally(()=>{if(alive)setLoading(false);});
    return()=>{alive=false;};
  },[url]);
  async function action(fn:()=>Promise<void>){
    setBusy(true);setError("");setNotice("");
    try{await fn();}catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  function addAnchor(){
    setError("");setNotice("");
    const time=Number(seconds),value=Number(bpm);
    const length=asset?.duration_samples||Math.round(durationSeconds*48000);
    const point=Math.round(time*48000);
    if(!Number.isFinite(time)||point<0||point>=length){setError("ERROR: Anchor time must fall within the song.");return;}
    if(!Number.isFinite(value)||value<20||value>320){setError("ERROR: BPM must be between 20 and 320.");return;}
    if(draft.some(row=>row.sample===point)){setError("ERROR: That time already has a tempo anchor.");return;}
    const [top,bottom]=meter.split("/").map(Number);
    if(!Number.isInteger(top)||top<1||top>32||![1,2,4,8,16,32].includes(bottom)){setError("ERROR: Invalid meter.");return;}
    if(point!==0&&!draft.some(row=>row.sample===0)){setError("ERROR: Establish the initial tempo at 0:00 first.");return;}
    setDraft(rows=>[...rows,{id:identifier(),sample:point,bpm:value,transition,
      origin:"author",meter:[top,bottom],...(selectedSection?{section_id:selectedSection}:{})}].sort((a,b)=>a.sample-b.sample));
  }
  const dirty=JSON.stringify(draft)!==JSON.stringify(asset?.anchors||[]);
  return <div className="setting-tool-section song-tempo-map">
    <div className="setting-tool-row"><strong>Tempo map</strong>
      <Status tone={dirty?"warning":asset?.anchors.length?"success":"neutral"}>{dirty?"Unsaved edits":asset?.anchors.length?"Saved revision "+asset.revision:"Not established"}</Status>
    </div>
    <p className="setting-path">Composition timing asset. Does not change playback speed, MIDI notes or stems. No BPM is inferred until an analyzer supplies evidence.</p>
    {loading?<p role="status">Loading tempo map...</p>:!asset?
      <Button size="compact" variant="primary" disabled={busy||!durationSeconds} onClick={()=>void action(async()=>{
        const fresh=await api<TempoMap>("POST",{duration_samples:Math.round(durationSeconds*48000)});
        setAsset(fresh);setDraft(fresh.anchors);setNotice("Empty map created. Add and save the initial tempo anchor.");
      })}>Create tempo map</Button>:
      <>
        <div className="setting-controls">
          <label>Time (seconds)<input aria-label="Tempo anchor time seconds" type="number" min="0" max={durationSeconds} step=".001" value={seconds} onChange={e=>setSeconds(e.target.value)}/></label>
          <label>BPM<input aria-label="Tempo BPM" type="number" min="20" max="320" step=".01" placeholder="Enter measured or authored BPM" value={bpm} onChange={e=>setBpm(e.target.value)}/></label>
          <label>Next transition<select aria-label="Tempo transition" value={transition} onChange={e=>setTransition(e.target.value as "step"|"linear")}>
            <option value="step">Step</option><option value="linear">Ramp toward next anchor</option>
          </select></label>
          <label>Meter<select aria-label="Tempo meter" value={meter} onChange={e=>setMeter(e.target.value)}>
            {["4/4","3/4","6/8","5/4","7/8","2/4","12/8"].map(value=><option key={value} value={value}>{value}</option>)}
          </select></label>
          <label>Section (optional)<select aria-label="Tempo section" value={selectedSection} onChange={e=>{setSelectedSection(e.target.value);const row=sections.find(x=>x.id===e.target.value);if(row)setSeconds(String(row.start_seconds));}}>
            <option value="">No section</option>{sections.map(row=><option key={row.id} value={row.id}>{row.kind}{row.number?" "+row.number:""}</option>)}
          </select></label>
          <Button size="compact" variant="secondary" disabled={busy} onClick={addAnchor}>Add anchor</Button>
        </div>
        <div style={{maxHeight:250,overflow:"auto"}}>
          {draft.length===0?<p>No accepted tempos yet. Set the initial anchor at 0:00.</p>:draft.map(row=>
            <div key={row.id} className="setting-tool-row">
              <span>{stamp(row.sample)} | {row.bpm} BPM | {row.meter.join("/")} | {row.transition}</span>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>setDraft(items=>items.filter(item=>item.id!==row.id))}>Remove</Button>
            </div>)}
        </div>
        <div className="setting-controls">
          <Button size="compact" variant="primary" disabled={busy||!dirty} onClick={()=>void action(async()=>{
            const saved=await api<TempoMap>("PATCH",{asset_id:asset.asset_id,base_revision:asset.revision,anchors:draft});
            setAsset(saved);setDraft(saved.anchors);setNotice("Tempo-map revision saved. Project audio was not modified.");
          })}>Save tempo map</Button>
          <Button size="compact" variant="secondary" disabled={busy||!dirty} onClick={()=>{setDraft(asset.anchors);setError("");}}>Discard edits</Button>
          <Button size="compact" variant="secondary" disabled={busy} onClick={()=>void action(async()=>{await reload();setNotice("Latest revision loaded.");})}>Reload</Button>
        </div>
        <details><summary>Candidate tempo evidence ({asset.observations.length})</summary>
          {asset.observations.length===0?<p>No measured or model candidate tempos have been recorded. MIDI and DSP providers will feed this list.</p>:
            asset.observations.map(row=><p key={row.id}>{stamp(row.start_sample)} to {stamp(row.end_sample)}: {row.bpm??"Unknown"} BPM ({row.method}, {row.status})</p>)}
        </details>
      </>}
    {notice&&<p role="status">{notice}</p>}
    {error&&<p role="alert" className="error-message">{error}</p>}
  </div>;
}
