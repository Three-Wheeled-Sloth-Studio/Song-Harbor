import {useEffect,useRef,useState} from "react";
import type {SongSection} from "./SectionEditor";
import type {SharedClockAudition} from "./SharedClockAudition";

type Runtime={status:string;ready?:boolean;loaded_model?:string|null;models?:{name:string;validated_tasks?:string[];reported_tasks?:string[];loaded?:boolean}[]};
type Candidate={candidate_id:string;state:string;error?:string;target_start_seconds:number;target_end_seconds:number;model:string;isolation:string;prompt:string;seed:number;task_type?:string;instrument?:string;operation?:string;source_similarity?:{status:string;correlations?:number[];reason?:string};};
type ImportResult={project:unknown;job:unknown};
type Props={jobId:string;sections:SongSection[];engine:SharedClockAudition|null;
 sourceTracks?:{track_id:string;display_name:string}[];
  playing:boolean;position:number;onSeek:(time:number)=>void;onPlay:()=>Promise<void>;
  onPause:()=>void;onInserted:(result:ImportResult)=>void;saveProject:()=>Promise<boolean>;
  onError:(message:string)=>void};

function timelineTime(seconds:number):string{
  const millis=Math.max(0,Math.round(seconds*1000));
  const minutes=Math.floor(millis/60000);
  const remaining=Math.floor(millis%60000/1000);
  return minutes+":"+String(remaining).padStart(2,"0")+"."+String(millis%1000).padStart(3,"0");
}
function sectionLabel(section:SongSection):string{
  return section.kind+(section.number?" "+section.number:"")+" ("+timelineTime(section.start_seconds)+")";
}
async function jsonResponse<T>(url:string,init?:RequestInit):Promise<T>{
  const response=await fetch(url,init);
  const data=await response.json() as T & {detail?:string};
  if(!response.ok)throw Error(data.detail||"ACE request failed");
  return data;
}

export function AccompanimentGenerator({jobId,sections,engine,sourceTracks=[],playing,position,onSeek,onPlay,onPause,onInserted,saveProject,onError}:Props){
  const [fromId,setFromId]=useState("");
  const [toId,setToId]=useState("");
  const [before,setBefore]=useState(15);
  const [after,setAfter]=useState(0);
  const [preRoll,setPreRoll]=useState(5);
  const [prompt,setPrompt]=useState("");
  const [mode,setMode]=useState<"lego"|"cover">("lego");
  const [instrument,setInstrument]=useState("strings");
  const [vocalPhrase,setVocalPhrase]=useState("Mmm, mmm, mmm");
  const [alias,setAlias]=useState("Accompaniment");
  const [acceptMode,setAcceptMode]=useState<"layer"|"replace">("layer");
  const [replaceTrackId,setReplaceTrackId]=useState("");
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
  const [soloPreview,setSoloPreview]=useState(false);
  const [priorBlend,setPriorBlend]=useState(35);
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
    if(!candidate||candidate.state==="ready"||candidate.state==="failed"||candidate.state==="review_required")return;
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
    setSoloPreview(false);
    setPreviewTrimDb(0);
    setPreviewPeaks([]);
    setLoadedId(null);
    setPreviewBusy(false);
  },[candidate?.candidate_id,engine]);
  const fromIndex=sections.findIndex(s=>s.id===fromId);
  const toIndex=sections.findIndex(s=>s.id===toId);
  const previewProgress=candidate?Math.max(0,Math.min(100,100*(position-candidate.target_start_seconds)/Math.max(.001,candidate.target_end_seconds-candidate.target_start_seconds))):0;
  const validRange=fromIndex>=0&&toIndex>=fromIndex;
  const currentModel=mode==="lego"?"acestep-v15-base":"acestep-v15-turbo";
  const modelReady=!!runtime?.ready&&runtime.loaded_model===currentModel;
  const legoSupported=runtime?.models?.some(m=>m.name==="acestep-v15-base"&&m.reported_tasks?.includes("lego"));
  const backingHumBlocked=mode==="lego"&&instrument==="backing_vocals";
  const ready=modelReady&&(mode==="cover"||!!legoSupported)&&!backingHumBlocked;
  const audioUrl=candidate?base+"/"+candidate.candidate_id+"/audio":null;
  async function generate(){
    if(!validRange||!ready)return;
    setBusy(true);setError("");setNotice("");
    try{
      engine?.clearCandidatePreview();
      setBlend(35);
      const body={from_section_id:fromId,to_section_id:toId,context_before:before,context_after:after,
                  prompt,model:currentModel,task_type:mode,operation:"add",instrument:mode==="lego"?instrument:"",vocal_phrase:mode==="lego"&&instrument==="backing_vocals"?vocalPhrase:"",seed:Number(seed),
                  bpm:bpm.trim()?Number(bpm):null,key};
      const result=await jsonResponse<Candidate>(base,{method:"POST",headers:{"Content-Type":"application/json"},
                                                       body:JSON.stringify(body)});
      setCandidate(result);
      setHistory(current=>[result,...current.filter(item=>item.candidate_id!==result.candidate_id)].slice(0,12));
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  }
  async function checkIsolation(){
    if(!candidate||candidate.task_type!=="lego"||busy)return;
    setBusy(true);setError("");
    try{
      const result=await jsonResponse<Candidate>(base+"/"+candidate.candidate_id+"/check-isolation",{method:"POST"});
      setCandidate(result);
      setHistory(current=>current.map(item=>item.candidate_id===result.candidate_id?result:item));
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
  async function audition(solo=false){
    if(!candidate||!audioUrl||!engine?.ready)return;
    setPreviewBusy(true);setError("");
    try{
      await engine.loadCandidatePreview(audioUrl,candidate.target_start_seconds);
      engine.setCandidatePreviewBlend(blend);
      engine.setCandidatePreviewTrimDb(previewTrimDb);
      engine.setCandidatePreviewSolo(solo||soloPreview);
      if(solo)setSoloPreview(true);
      setPreviewPeaks(engine.candidateWaveform());
      setLoadedId(candidate.candidate_id);
      onSeek(Math.max(0,candidate.target_start_seconds-preRoll));
      if(!playing)await onPlay();
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setPreviewBusy(false);}
  }
  async function accept(){
    if(!candidate||candidate.state!=="ready"||!audioUrl||busy||
       (candidate.task_type==="lego"&&candidate.source_similarity?.status!=="not_detected"))return;
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
      form.append("preview_trim_db",String(previewTrimDb));
      form.append("accept_mode",acceptMode);
      if(acceptMode==="replace")form.append("replace_source_track_id",replaceTrackId);
      const result=await jsonResponse<ImportResult>("/api/projects/"+jobId+"/tracks/add",{method:"POST",body:form});
      engine?.clearCandidatePreview();
      setBlend(35);
      setNotice("Candidate accepted and inserted at "+timelineTime(candidate.target_start_seconds)+".");
      onInserted(result);
    }catch(e){const message=e instanceof Error?e.message:String(e);setError(message);onError(message);}
    finally{setBusy(false);}
  }
  return <div className="song-accompaniment-tool" style={{display:"grid",gap:"0.55rem",minWidth:"min(400px,76vw)",maxWidth:"100%"}}>
    <div className="song-ace-method-row">
      <label htmlFor="ace-generation-mode">Method</label>
      <select id="ace-generation-mode" value={mode} onChange={e=>setMode(e.target.value as "lego"|"cover")}>
        <option value="lego">Lego · Base</option>
        <option value="cover">Cover · Turbo</option>
      </select>
      <label htmlFor="ace-operation">Operation</label>
      <select id="ace-operation" value="add" disabled aria-label="Operation">
        <option value="add">Add layer</option>
      </select>
    </div>
    {mode==="lego"&&<div className="song-ace-family-row">
      <label htmlFor="ace-instrument-family">Instr Family</label>
      <select id="ace-instrument-family" value={instrument} onChange={e=>setInstrument(e.target.value)}>
        {["strings","bass","guitar","drums","percussion","keyboard","synth","woodwinds","brass","fx","backing_vocals"].map(name=><option key={name} value={name}>{name.charAt(0).toUpperCase()+name.slice(1)}</option>)}
      </select>
    </div>}
    {mode==="lego"&&instrument==="backing_vocals"&&<div style={{display:"grid",gap:"0.25rem"}}>
      <small role="alert">Backing-vocal generation temporarily disabled after a reported system freeze. Resource preflight and emergency-stop recovery are required before another GPU test.</small>
      <label>Nonverbal vocal phrase <input value={vocalPhrase} maxLength={200} onChange={e=>setVocalPhrase(e.target.value)}/></label>
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
    {!validRange&&<small role="alert">To must follow From.</small>}
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
    <button type="button" disabled={!ready||!validRange||!prompt.trim()||(mode==="lego"&&instrument==="backing_vocals"&&!vocalPhrase.trim())||busy} onClick={()=>void generate()}>{busy?"Working...":mode==="lego"?(instrument==="backing_vocals"?"Generate experimental hum":"Generate Lego instrument"):"Generate experimental Cover"}</button>
    {candidate&&<section style={{display:"grid",gap:"0.45rem"}}>
      <strong>Candidate: {candidate.state}</strong>
      {candidate.error&&<small role="alert">{candidate.error}</small>}
      {candidate.task_type==="lego"&&["ready","review_required"].includes(candidate.state)&&<small>
        Isolation: {candidate.source_similarity?.status==="not_detected"?"No direct source duplication detected":candidate.source_similarity?.status==="suspected_source_leakage"?"Source audio detected in generated track":"Not checked"}
        {" "}<button type="button" disabled={busy} onClick={()=>void checkIsolation()}>Check isolation</button>
      </small>}
      {candidate.state==="failed"&&<button type="button" disabled={busy} onClick={()=>void recover()}>Recover preserved audio</button>}
      {["ready","review_required"].includes(candidate.state)&&<>
        <div className="song-ace-preview-line">
          <button type="button" disabled={previewBusy||!engine?.ready} onClick={()=>void audition()}>{previewBusy?"Loading...":"Preview"}</button>
          <button type="button" aria-pressed={soloPreview} title="Listen to generated audio only" onClick={()=>{
            if(loadedId!==candidate.candidate_id){setPriorBlend(blend);void audition(true);return;}
            if(!soloPreview){setPriorBlend(blend);setSoloPreview(true);engine?.setCandidatePreviewSolo(true);}
            else{setSoloPreview(false);setBlend(priorBlend);engine?.setCandidatePreviewSolo(false);engine?.setCandidatePreviewBlend(priorBlend);}
          }}>♫ Solo</button>
          <label className="song-ace-knob" title={"Original / generated blend: "+(soloPreview?100:blend)+"%"} aria-label="Original to generated blend">
            <span aria-hidden="true">◉</span>
            <input type="range" min="0" max="100" step="1" aria-label="Original to generated audition blend"
              disabled={loadedId!==candidate.candidate_id} value={soloPreview?100:blend}
              onChange={e=>{const value=Number(e.target.value);setBlend(value);setSoloPreview(false);engine?.setCandidatePreviewSolo(false);engine?.setCandidatePreviewBlend(value);}}/>
            <output>{soloPreview?100:blend}%</output>
          </label>
          <details className="song-ace-preroll">
            <summary>⋯</summary>
            <label>Pre-roll (s) <input type="number" min="0" max="30" step="1" value={preRoll} onChange={e=>setPreRoll(Math.max(0,Math.min(30,Number(e.target.value))))}/></label>
          </details>
        </div>
        {previewPeaks.length>0&&<svg role="img" aria-label="Generated candidate waveform and playback position" viewBox="0 0 320 66" preserveAspectRatio="none" className="song-ace-preview-waveform">
          {previewPeaks.map((height,i)=><line key={i} x1={i*2+1} x2={i*2+1} y1={33-height*29} y2={33+height*29} stroke="#73c4cb" strokeWidth="1.6"/>)}
          <line x1={previewProgress*3.2} x2={previewProgress*3.2} y1="0" y2="66" stroke="#f4c177" strokeWidth="1.8"/>
        </svg>}
        <div className="song-candidate-volume" title="Candidate level, carried into accepted track">
          ◖ <input type="range" aria-label="Generated candidate volume" min="-12" max="9" step="1" value={previewTrimDb}
            onChange={e=>{const db=Number(e.target.value);setPreviewTrimDb(db);engine?.setCandidatePreviewTrimDb(db);}}/>
          <output>{previewTrimDb>0?"+":""}{previewTrimDb} dB</output>
          <button type="button" title="Reset candidate volume" aria-label="Reset candidate volume"
            onClick={()=>{setPreviewTrimDb(0);engine?.setCandidatePreviewTrimDb(0);}}>↺</button>
        </div>
        <label>New track alias <input value={alias} onChange={e=>setAlias(e.target.value)}/></label>
        <div className="song-candidate-accept">
          <select aria-label="ACE acceptance mode" title="Layer keeps the original. Replace region mutes selected source." value={acceptMode} onChange={e=>setAcceptMode(e.target.value as "layer"|"replace")}>
            <option value="layer">Layer</option><option value="replace">Replace</option>
          </select>
          {acceptMode==="replace"&&<select aria-label="Original stem to replace" value={replaceTrackId} onChange={e=>setReplaceTrackId(e.target.value)}>
            <option value="">Source stem…</option>{sourceTracks.map(track=><option key={track.track_id} value={track.track_id}>{track.display_name}</option>)}
          </select>}
          <button type="button" disabled={busy||candidate.state!=="ready"||(acceptMode==="replace"&&!replaceTrackId)||(candidate.task_type==="lego"&&candidate.source_similarity?.status!=="not_detected")} onClick={()=>void accept()}>✓ Add</button>
        </div>
      </>}
    </section>}
    <details><summary>Generation parameters</summary>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"0.5rem"}}>
        <label>Seed<input type="number" min="0" max="4294967295" value={seed} onChange={e=>setSeed(e.target.value)}/></label>
        <label>BPM (optional)<input type="number" min="30" max="300" value={bpm} onChange={e=>setBpm(e.target.value)}/></label>
        <label>Key (optional)<input value={key} onChange={e=>setKey(e.target.value)}/></label>
      </div>
    </details>

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

    {(busy||candidate&&["prepared","generating","processing"].includes(candidate.state))&&<div role="status" aria-live="polite" className="song-ace-generation-overlay">
      <div className="song-ace-generation-message"><span className="song-ace-spinner" aria-hidden="true"/> <strong>{busy?"Preparing generation":candidate?.state==="prepared"?"Queued":candidate?.state==="generating"?"Generating instrument":"Processing audio"}</strong>

      </div>
    </div>}
    {notice&&<small role="status">{notice}</small>}
    {error&&<small role="alert">{error}</small>}
  </div>;
}
