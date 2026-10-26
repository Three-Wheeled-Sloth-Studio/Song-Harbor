import {useEffect,useRef,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SharedClockAudition} from "./SharedClockAudition";

type Runtime={status:string;ready?:boolean;loaded_model?:string|null;models?:{name:string;validated_tasks?:string[];reported_tasks?:string[];loaded?:boolean}[]};
type Candidate={candidate_id:string;state:string;error?:string;target_start_seconds:number;target_end_seconds:number;model:string;isolation:string;prompt:string;seed:number;task_type?:string;instrument?:string;operation?:string};
type ImportResult={project:unknown;job:unknown};
type Props={jobId:string;sections:SongSection[];engine:SharedClockAudition|null;
  playing:boolean;position:number;onSeek:(time:number)=>void;onPlay:()=>Promise<void>;
  onPause:()=>void;onInserted:(result:ImportResult)=>void;saveProject:()=>Promise<boolean>;
  onError:(message:string)=>void};

function sectionLabel(section:SongSection):string{
  return section.kind+(section.number?" "+section.number:"")+" ("+section.start_seconds.toFixed(1)+"s)";
}
async function jsonResponse<T>(url:string,init?:RequestInit):Promise<T>{
  const response=await fetch(url,init);
  const data=await response.json() as T & {detail?:string};
  if(!response.ok)throw Error(data.detail||"ACE request failed");
  return data;
}

export function AccompanimentGenerator({jobId,sections,engine,playing,onSeek,onPlay,onPause,onInserted,saveProject,onError}:Props){
  const [fromId,setFromId]=useState("");
  const [toId,setToId]=useState("");
  const [before,setBefore]=useState(15);
  const [after,setAfter]=useState(0);
  const [preRoll,setPreRoll]=useState(5);
  const [prompt,setPrompt]=useState("");
  const [mode,setMode]=useState<"lego"|"cover">("lego");
  const [instrument,setInstrument]=useState("strings");
  const [alias,setAlias]=useState("Accompaniment");
  const [bpm,setBpm]=useState("");
  const [key,setKey]=useState("");
  const [seed,setSeed]=useState("150719");
  const [runtime,setRuntime]=useState<Runtime|null>(null);
  const [candidate,setCandidate]=useState<Candidate|null>(null);
  const [history,setHistory]=useState<Candidate[]>([]);
  const [busy,setBusy]=useState(false);
  const [previewBusy,setPreviewBusy]=useState(false);
  const [blend,setBlend]=useState(35);
  const [previewTrimDb,setPreviewTrimDb]=useState(0);
  const [previewPeaks,setPreviewPeaks]=useState<number[]>([]);
  const [loadedId,setLoadedId]=useState<string|null>(null);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const candidateRef=useRef<string|null>(null);
  const base="/api/projects/"+jobId+"/ace/candidates";
  useEffect(()=>{
    let alive=true;
    void jsonResponse<{candidates:Candidate[]}>(base).then(data=>{
      if(!alive)return;
      setHistory((data.candidates||[]).slice(0,12));
      setCandidate(existing=>existing||(data.candidates||[])[0]||null);
    }).catch(()=>{});
    return()=>{alive=false;};
  },[base]);
  useEffect(()=>{
    if(!sections.length)return;
    setFromId(v=>sections.some(s=>s.id===v)?v:sections[0].id);
    setToId(v=>sections.some((s,i)=>s.id===v&&i>=sections.findIndex(item=>item.id===fromId))?v:sections[0].id);
  },[sections]);
  useEffect(()=>{
    let mounted=true;
    const refresh=()=>{void jsonResponse<Runtime>("/api/ace/discovery")
      .then(value=>{if(mounted)setRuntime(value);})
      .catch(e=>{if(mounted)setError(String(e));});};
    refresh();
    const timer=window.setInterval(refresh,5000);
    return()=>{mounted=false;window.clearInterval(timer);engine?.clearCandidatePreview();};
  },[jobId]);
  useEffect(()=>{
    if(!candidate||candidate.state==="ready"||candidate.state==="failed")return;
    let active=true;
    const check=async()=>{
      try{
        const result=await jsonResponse<Candidate>(base+"/"+candidate.candidate_id);
        if(active){setCandidate(result);setHistory(current=>current.map(item=>item.candidate_id===result.candidate_id?result:item));}
      }catch(e){if(active)setError(String(e));}
    };
    const timer=window.setInterval(()=>{void check();},1200);
    return()=>{active=false;window.clearInterval(timer);};
  },[base,candidate?.candidate_id,candidate?.state]);
  useEffect(()=>{
    if(candidateRef.current===candidate?.candidate_id)return;
    candidateRef.current=candidate?.candidate_id||null;
    engine?.clearCandidatePreview();
    setBlend(35);
    setPreviewTrimDb(0);
    setPreviewPeaks([]);
    setLoadedId(null);
    setPreviewBusy(false);
  },[candidate?.candidate_id,engine]);
  const fromIndex=sections.findIndex(s=>s.id===fromId);
  const toIndex=sections.findIndex(s=>s.id===toId);
  const start=fromIndex>=0?sections[fromIndex].start_seconds:0;
  const end=toIndex>=0?sections[toIndex].end_seconds:0;
  const validRange=fromIndex>=0&&toIndex>=fromIndex;
  const currentModel=mode==="lego"?"acestep-v15-base":"acestep-v15-turbo";
  const modelReady=!!runtime?.ready&&runtime.loaded_model===currentModel;
  const legoSupported=runtime?.models?.some(m=>m.name==="acestep-v15-base"&&m.reported_tasks?.includes("lego"));
  const ready=modelReady&&(mode==="cover"||!!legoSupported);
  const audioUrl=candidate?base+"/"+candidate.candidate_id+"/audio":null;
  async function generate(){
    if(!validRange||!ready)return;
    setBusy(true);setError("");setNotice("");
    try{
      engine?.clearCandidatePreview();
      setBlend(35);
      const body={from_section_id:fromId,to_section_id:toId,context_before:before,context_after:after,
                  prompt,model:currentModel,task_type:mode,operation:"add",instrument:mode==="lego"?instrument:"",seed:Number(seed),
                  bpm:bpm.trim()?Number(bpm):null,key};
      const result=await jsonResponse<Candidate>(base,{method:"POST",headers:{"Content-Type":"application/json"},
                                                       body:JSON.stringify(body)});
      setCandidate(result);
      setHistory(current=>[result,...current.filter(item=>item.candidate_id!==result.candidate_id)].slice(0,12));
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function recover(){
    if(!candidate||candidate.state!=="failed"||busy)return;
    setBusy(true);setError("");
    try{
      const restored=await jsonResponse<Candidate>(base+"/"+candidate.candidate_id+"/recover",{method:"POST"});
      setCandidate(restored);
      setHistory(current=>current.map(item=>item.candidate_id===restored.candidate_id?restored:item));
      setNotice("Preserved audio recovered. No new generation was needed.");
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function audition(){
    if(!candidate||!audioUrl||!engine?.ready)return;
    setPreviewBusy(true);setError("");
    try{
      await engine.loadCandidatePreview(audioUrl,candidate.target_start_seconds);
      engine.setCandidatePreviewBlend(blend);
      engine.setCandidatePreviewTrimDb(previewTrimDb);
      setPreviewPeaks(engine.candidateWaveform());
      setLoadedId(candidate.candidate_id);
      onSeek(Math.max(0,candidate.target_start_seconds-preRoll));
      if(!playing)await onPlay();
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setPreviewBusy(false);}
  }
  async function accept(){
    if(!candidate||candidate.state!=="ready"||!audioUrl||busy)return;
    if(!/^[A-Za-z][A-Za-z0-9_-]{0,31}$/.test(alias)){setError("Use a script-safe track alias.");return;}
    setBusy(true);setError("");
    try{
      if(!await saveProject())throw Error("Save the current project before accepting accompaniment");
      onPause();
      const response=await fetch(audioUrl,{cache:"no-store"});
      if(!response.ok)throw Error("Could not retrieve selected accompaniment");
      const blob=await response.blob();
      const form=new FormData();
      form.append("file",new File([blob],"ACE-"+candidate.candidate_id.slice(0,8)+".wav",{type:"audio/wav"}));
      form.append("stem_alias",alias);
      form.append("display_name","ACE accompaniment ("+alias+")");
      form.append("start_seconds",String(candidate.target_start_seconds));
      const result=await jsonResponse<ImportResult>("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
      engine?.clearCandidatePreview();
      setBlend(35);
      setNotice("Candidate accepted and inserted at "+candidate.target_start_seconds.toFixed(3)+"s.");
      onInserted(result);
    }catch(e){const message=e instanceof Error?e.message:String(e);setError(message);onError(message);}
    finally{setBusy(false);}
  }
  return <div className="song-accompaniment-tool" style={{display:"grid",gap:"0.7rem",minWidth:"min(400px,76vw)",maxWidth:"480px"}}>
    <small>ACE: {ready?(mode==="lego"?"Base ready for Lego (experimental)":"Turbo ready for Cover"):runtime?.status==="connected"?(mode==="lego"&&!legoSupported?"Base Lego not reported by ACE inventory":"Switch to "+(mode==="lego"?"Base":"Turbo")+" in Settings > Components"):"Not connected; enable ACE in Settings"}</small>
    <div style={{display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(0,1fr)",gap:"0.6rem",minWidth:0}}>
      <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
        <label htmlFor="ace-generation-mode">Method</label>
        <select id="ace-generation-mode" style={{width:"100%",minWidth:0}} value={mode} onChange={e=>setMode(e.target.value as "lego"|"cover")}>
          <option value="lego">Lego · isolated instrument (Base)</option>
          <option value="cover">Experimental Cover · full mix (Turbo)</option>
        </select>
      </div>
      <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
        <label htmlFor="ace-operation">Operation</label>
        <select id="ace-operation" style={{width:"100%",minWidth:0}} value="add" onChange={()=>{}}>
          <option value="add">Add instrument</option>
          <option value="replace" disabled>Replace instrument (next stage)</option>
        </select>
      </div>
    </div>
    {mode==="lego"&&<div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
      <label htmlFor="ace-instrument-family">Instrument family</label>
      <select id="ace-instrument-family" value={instrument} style={{width:"100%",minWidth:0}} onChange={e=>setInstrument(e.target.value)}>
        {["strings","bass","guitar","drums","percussion","keyboard","synth","woodwinds","brass","fx"].map(name=><option key={name} value={name}>{name.charAt(0).toUpperCase()+name.slice(1)}</option>)}
      </select>
      <small>For violin or cello, choose Strings and describe the part in Direction.</small>
    </div>}
    <div style={{display:"grid",gridTemplateColumns:"minmax(0,1fr) minmax(0,1fr)",columnGap:"0.65rem",alignItems:"start",width:"100%",minWidth:0}}>
      <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
        <span>From section</span>
        <select aria-label="From section" style={{display:"block",width:"100%",minWidth:0,boxSizing:"border-box",height:"2rem"}}
          value={fromId} onChange={e=>{const next=e.target.value;setFromId(next);if(sections.findIndex(s=>s.id===next)>toIndex)setToId(next);}}>
          {sections.map(s=><option value={s.id} key={s.id}>{sectionLabel(s)}</option>)}
        </select>
      </div>
      <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
        <span>To section</span>
        <select aria-label="To section" style={{display:"block",width:"100%",minWidth:0,boxSizing:"border-box",height:"2rem"}}
          value={toId} onChange={e=>setToId(e.target.value)}>
          {sections.map((s,i)=><option value={s.id} key={s.id} disabled={i<fromIndex}>{sectionLabel(s)}</option>)}
        </select>
      </div>
    </div>
    {validRange?<small>Target: {start.toFixed(3)}s to {end.toFixed(3)}s ({(end-start).toFixed(1)}s)</small>:<small role="alert">To section must follow From section.</small>}
    <div style={{display:"flex",gap:"0.5rem",flexWrap:"wrap"}}>
      <label>Context before (s) <input type="number" min="0" max="240" step="1" value={before} onChange={e=>setBefore(Number(e.target.value))}/></label>
      <label>After (s) <input type="number" min="0" max="240" step="1" value={after} onChange={e=>setAfter(Number(e.target.value))}/></label>
    </div>
    <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",width:"100%",minWidth:0}}>
      <label htmlFor="ace-accompaniment-direction">Direction</label>
      <textarea id="ace-accompaniment-direction" rows={4} style={{display:"block",width:"100%",minWidth:0,boxSizing:"border-box",resize:"vertical"}}
        value={prompt} placeholder="Instrument, musical role, mood, and constraints"
        onChange={e=>setPrompt(e.target.value)}/>
    </div>
    <details><summary>Generation parameters</summary>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"0.5rem"}}>
        <label>Seed<input type="number" min="0" max="4294967295" value={seed} onChange={e=>setSeed(e.target.value)}/></label>
        <label>BPM (optional)<input type="number" min="30" max="300" value={bpm} onChange={e=>setBpm(e.target.value)}/></label>
        <label>Key (optional)<input value={key} onChange={e=>setKey(e.target.value)}/></label>
      </div>
    </details>
    <button type="button" disabled={!ready||!validRange||!prompt.trim()||busy} onClick={()=>void generate()}>{busy?"Working...":mode==="lego"?"Generate Lego instrument":"Generate experimental Cover"}</button>
    {history.length>0&&<details>
      <summary>Saved candidates ({history.length})</summary>
      <div style={{display:"flex",flexDirection:"column",gap:"0.25rem",minWidth:0}}>
      <label htmlFor="ace-candidate-history">Candidate</label>
      <select id="ace-candidate-history" style={{width:"100%",minWidth:0}} value={candidate?.candidate_id||""}
        onChange={e=>setCandidate(history.find(item=>item.candidate_id===e.target.value)||null)}>
        {history.map(item=><option value={item.candidate_id} key={item.candidate_id}>
          {item.prompt.slice(0,48)} · {item.state} · {item.candidate_id.slice(0,8)}
        </option>)}
      </select>
      </div>
    </details>}
    {candidate&&<section style={{display:"grid",gap:"0.45rem"}}>
      <strong>Candidate: {candidate.state}</strong>
      <small>{candidate.isolation==="cover-mix-not-isolated"?"Experimental full-mix Cover; not an isolated instrument.":"Lego instrument candidate · isolation awaits listening QA."}</small>
      {candidate.error&&<small role="alert">{candidate.error}</small>}
      {candidate.state==="failed"&&<button type="button" disabled={busy} onClick={()=>void recover()}>Recover preserved audio</button>}
      {candidate.state==="ready"&&<>
        <div style={{display:"flex",gap:"0.5rem",alignItems:"center"}}>
          <button type="button" disabled={previewBusy||!engine?.ready} onClick={()=>void audition()}>{previewBusy?"Loading...":"Audition with pre-roll"}</button>
          <label>Pre-roll (s) <input type="number" min="0" max="30" step="1" value={preRoll} onChange={e=>setPreRoll(Math.max(0,Math.min(30,Number(e.target.value))))}/></label>
        </div>
        {previewPeaks.length>0&&<svg role="img" aria-label="Generated candidate waveform" viewBox="0 0 320 66" preserveAspectRatio="none" style={{display:"block",width:"100%",height:"66px",background:"#121f28",borderRadius:"5px"}}>
          {previewPeaks.map((height,i)=><line key={i} x1={i*2+1} x2={i*2+1} y1={33-height*29} y2={33+height*29} stroke="#73c4cb" strokeWidth="1.6"/>)}
        </svg>}
        <label style={{display:"grid",gap:"0.3rem"}}>
          <span>Audition blend · {blend}% generated</span>
          <input type="range" min="0" max="100" step="1" aria-label="Original to generated audition blend"
            disabled={loadedId!==candidate.candidate_id} value={blend} onChange={e=>{const value=Number(e.target.value);setBlend(value);engine?.setCandidatePreviewBlend(value);}}/>
        </label>
        <small>0 original · 100 generated only · equal-power preview. Audition first to enable blend.</small>
        <details>
          <summary>Audition level correction</summary>
          <label style={{display:"grid",gap:"0.2rem"}}>Generated trim · {previewTrimDb>0?"+":""}{previewTrimDb} dB
            <input type="range" min="-12" max="9" step="1" value={previewTrimDb}
              disabled={loadedId!==candidate.candidate_id}
              onChange={e=>{const db=Number(e.target.value);setPreviewTrimDb(db);engine?.setCandidatePreviewTrimDb(db);}}/>
          </label>
          <small>Preview-only; positive trim may clip. Not applied to accepted track.</small>
        </details>
        <label>New track alias <input value={alias} onChange={e=>setAlias(e.target.value)}/></label>
        <button type="button" disabled={busy} onClick={()=>void accept()}>Accept and insert</button>
      </>}
    </section>}
    {(busy||candidate&&["prepared","generating","processing"].includes(candidate.state))&&<div role="status" aria-live="polite" className="song-ace-generation-overlay">
      <div className="song-ace-generation-message"><span className="song-ace-spinner" aria-hidden="true"/> <strong>{busy?"Preparing generation":candidate?.state==="prepared"?"Queued":candidate?.state==="generating"?"Generating instrument":"Processing audio"}</strong>
        <small>ACE is working. The song and original stems remain unchanged.</small>
      </div>
    </div>}
    {notice&&<small role="status">{notice}</small>}
    {error&&<small role="alert">{error}</small>}
  </div>;
}
