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

export function TempoMapTool({projectId,durationSeconds,sections,renderMix}:{projectId:string;durationSeconds:number;sections:Section[];renderMix:()=>Promise<Blob>}){
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
  const [measured,setMeasured]=useState<Observation[]>([]);
  const [measureState,setMeasureState]=useState("");
  const [measureSection,setMeasureSection]=useState("");
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
    finally{setBusy(false);setMeasureState("");}
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
    const newAnchor:Anchor={id:identifier(),sample:point,bpm:value,transition,
      origin:"author",meter:[top,bottom],...(selectedSection?{section_id:selectedSection}:{})};
    setDraft(rows=>[...rows,newAnchor].sort((a,b)=>a.sample-b.sample));
  }
  async function measureTempo(){
    if(!asset)throw Error("ERROR: Create the tempo map first.");
    setMeasureState("Rendering current mix with saved production effects");
    const blob=await renderMix();
    if(blob.size>600*1024*1024)throw Error("ERROR: Mix is too large for snapshot transfer.");
    setMeasureState("Creating hashed analysis snapshot");
    const sha=await crypto.subtle.digest("SHA-256",await blob.arrayBuffer());
    const digest=Array.from(new Uint8Array(sha)).map(x=>x.toString(16).padStart(2,"0")).join("");
    const section=sections.find(row=>row.id===measureSection);
    const form=new FormData();
    form.append("audio",blob,"tempo-measurement.wav");
    form.append("project_id",projectId);
    form.append("recipe_revision",digest);
    form.append("section_ids",JSON.stringify(section?[section.id]:[]));
    if(section){
      form.append("start_seconds",String(section.start_seconds));
      form.append("end_seconds",String(section.end_seconds));
    }
    const upload=await fetch("/api/settings/models/q4/snapshot",{method:"POST",body:form});
    const snapshot=await upload.json() as {snapshot_id?:string;detail?:string};
    if(!upload.ok||!snapshot.snapshot_id)throw Error(snapshot.detail||"ERROR: Snapshot unavailable.");
    setMeasureState("Measuring local onset periodicity");
    const response=await fetch(url+"/measure",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({snapshot_id:snapshot.snapshot_id})});
    const result=await response.json() as {windows?:Observation[];detail?:string};
    if(!response.ok||!result.windows)throw Error(result.detail||"ERROR: Tempo measurement failed.");
    setMeasured(result.windows);
    setNotice(result.windows.length+" measurement windows ready for review. No tempos accepted.");
    setMeasureState("");
  }
  function stageCandidate(row:Observation){
    if(row.bpm===null){setError("ERROR: This window has no reliable pulse candidate.");return;}
    if(draft.some(anchor=>anchor.sample===row.start_sample)){setError("ERROR: A map anchor already occupies this position.");return;}
    const newAnchor:Anchor={id:identifier(),sample:row.start_sample,bpm:row.bpm,
      transition:"step",origin:"accepted-candidate",meter:[4,4]};
    setDraft(items=>[...items,newAnchor].sort((a,b)=>a.sample-b.sample));
    setNotice("Candidate staged. Save the tempo map to accept it; meter and timing remain editable.");
    setError("");
  }
  async function saveEvidence(){
    if(!asset||!measured.length)return;
    if(dirty)throw Error("ERROR: Save or discard pending tempo anchors before saving measurements.");
    const previous=asset.observations.filter(row=>!measured.some(item=>
      row.source_sha256===item.source_sha256&&row.method===item.method&&
      row.start_sample===item.start_sample&&row.end_sample===item.end_sample));
    const saved=await api<TempoMap>("PATCH",{asset_id:asset.asset_id,base_revision:asset.revision,
      observations:[...previous,...measured]});
    setAsset(saved);setDraft(saved.anchors);
    setMeasured([]);
    setNotice("Measured candidates saved as unverified evidence. No tempo anchors changed.");
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
        <div className="song-moss-confirm">
          <div className="setting-tool-row"><strong>Measure pulse</strong>
            <Status tone="neutral">Candidate estimates only</Status>
          </div>
          <div className="setting-controls">
            <label>Scope
              <select aria-label="Tempo measurement scope" value={measureSection} disabled={busy}
                onChange={e=>{setMeasureSection(e.target.value);setMeasured([]);}}>
                <option value="">Whole current mix</option>
                {sections.map(row=><option key={row.id} value={row.id}>{row.kind}{row.number?" "+row.number:""}</option>)}
              </select>
            </label>
            <Button size="compact" variant="primary" disabled={busy||dirty} onClick={()=>void action(measureTempo)}>
              Measure tempo
            </Button>
          </div>
          {busy&&measureState&&<div role="status" className="song-moss-progress">
            <span className="song-sfz-spinner" aria-hidden="true"/>{measureState}
          </div>}
          {!!measured.length&&<>
            <div className="setting-tool-row"><strong>Measured windows ({measured.length})</strong>
              <Button size="compact" variant="secondary" disabled={busy||dirty}
                onClick={()=>void action(saveEvidence)}>Save evidence</Button>
              <Button size="compact" variant="secondary" disabled={busy} onClick={()=>setMeasured([])}>Discard</Button>
            </div>
            <div style={{maxHeight:240,overflow:"auto"}}>
              {measured.map(row=><div key={row.id} className="setting-tool-row">
                <span>{stamp(row.start_sample)} to {stamp(row.end_sample)}: {row.bpm===null?"No reliable pulse":row.bpm+" BPM"}
                  {row.alternatives.length?" | alternatives "+row.alternatives.join(", "):""}
                  {row.evidence?" | "+row.evidence:""}</span>
                {row.bpm!==null&&<Button size="compact" variant="secondary" disabled={busy||draft.some(a=>a.sample===row.start_sample)}
                  onClick={()=>stageCandidate(row)}>Stage anchor</Button>}
              </div>)}
            </div>
          </>}
          <small>Windows overlap. Half/double-time alternatives and sparse passages require listening. No automated changes to the song or accepted tempo map.</small>
        </div>
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
          {draft.length===0?<p>No accepted tempos yet. Add the first anchor where the pulse becomes known.</p>:draft.map(row=>
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
