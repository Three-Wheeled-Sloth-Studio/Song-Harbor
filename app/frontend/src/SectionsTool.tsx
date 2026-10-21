import {useCallback,useEffect,useRef,useState} from "react";
import type {SongSection} from "./SectionEditor";

type Mode="replace"|"append";
type ExportData={content:string;sections:SongSection[];detail?:string};
import type {SavedPanTarget} from "./SectionPanTool";
type SavedReverbTarget={section_id:string;source_key:string;wet:number;transition_seconds:number;curve:"linear"|"smooth"};
type SavedEnding={fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"};
export function SectionsTool({jobId,open,onClose,focused,revision,onApplied}:{
  jobId:string;open:boolean;onClose:()=>void;focused:SongSection|null;
  revision:number;onApplied:(sections:SongSection[],targets:SavedPanTarget[],reverb:SavedReverbTarget[],ending:SavedEnding)=>void;
}){
  const [content,setContent]=useState("");
  const [dirty,setDirty]=useState(false);
  const [mode,setMode]=useState<Mode>("replace");
  const [saving,setSaving]=useState(false);
  const [message,setMessage]=useState("");
  const [error,setError]=useState("");
  const [stale,setStale]=useState(false);
  const editor=useRef<HTMLTextAreaElement|null>(null);
  const loadedRevision=useRef(-1);
  const focusSection=useRef<SongSection|null>(null);
  focusSection.current=focused;
  const load=useCallback(async(force=false)=>{
    if(!open)return;
    if(dirty&&!force){setStale(true);return;}
    try{
      const r=await fetch(`/api/projects/${jobId}/sections/export`);
      const data=await r.json() as ExportData;
      if(!r.ok)throw Error(data.detail||"Could not read section text");
      setContent(data.content||"");
      setDirty(false);setStale(false);setError("");
      const section=focusSection.current;
      if(section){
        const index=data.sections.findIndex(s=>s.id===section.id);
        const matches=[...(data.content||"").matchAll(/^\[[^\n]*\]/gm)];
        const target=matches[index];
        if(target){
          requestAnimationFrame(()=>{
            const node=editor.current;
            if(!node)return;
            node.focus();
            node.setSelectionRange(target.index||0,(target.index||0)+target[0].length);
          });
        }
      }
      loadedRevision.current=revision;
    }catch(e){setError(e instanceof Error?e.message:String(e));}
  },[jobId,open,dirty,revision]);
  useEffect(()=>{
    if(!open)return;
    if(loadedRevision.current===revision)return;
    void load();
  },[open,revision,load]);
  useEffect(()=>{loadedRevision.current=-1;setContent("");setDirty(false);},[jobId]);
  useEffect(()=>{
    if(!open||!focused)return;
    const node=editor.current;
    if(!node)return;
    const tags=[...content.matchAll(/^\[[^\n]*\]/gm)];
    const match=tags.find(x=>x[0].startsWith("["+focused.kind) &&
      x[0].includes(focused.start_seconds>=0?" "+timeStamp(focused.start_seconds)+"-":"\uffff"));
    if(match){
      node.focus();
      node.setSelectionRange(match.index||0,(match.index||0)+match[0].length);
    }
  },[focused,open,content]);

  async function apply(){
    if(!content.trim()||saving)return;
    setSaving(true);setError("");setMessage("");
    try{
      const r=await fetch(`/api/projects/${jobId}/sections/import`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content,mode})
      });
      const result=await r.json() as {sections?:SongSection[];detail?:string;auto_distributed?:boolean;imported_count?:number;pan_targets?:SavedPanTarget[];reverb_targets?:SavedReverbTarget[];ending?:SavedEnding};
      if(!r.ok||!result.sections)throw Error(result.detail||"Import failed");
      onApplied(result.sections,result.pan_targets||[],result.reverb_targets||[],result.ending||{fade_seconds:0,tail_seconds:0,curve:"smooth"});
      setDirty(false);setStale(false);
      setMessage(result.auto_distributed?"Sections placed · align on timeline":"Saved · timestamps updated");
      loadedRevision.current=-1;
      setMode("replace");
      const reload=await fetch(`/api/projects/${jobId}/sections/export`);
      if(reload.ok){
        const saved=await reload.json() as ExportData;
        setContent(saved.content||"");
      }
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setSaving(false);}
  }
  async function readFile(file:File|undefined){
    if(!file)return;
    if(file.size>100000){setError("Section file exceeds 100 KB");return;}
    try{setContent(await file.text());setDirty(true);setError("");}
    catch{setError("Cannot read section file");}
  }
  if(!open)return null;
  return <section className="production-section-tool" aria-label="Section script editor">
    <div className="production-tool-heading">
      <strong>Section script</strong>
      <button type="button" title="Close section script" aria-label="Close section script" onClick={onClose}>×</button>
    </div>
    <textarea ref={editor} aria-label="Section script" spellCheck={false}
      value={content} rows={10} placeholder={"[Intro]\n[Verse 1]\n{Other.pan:left.60@2s:smooth}\n[Chorus]\n{Other.pan:right.60@2s:smooth}\n[Outro]"}
      onChange={e=>{setContent(e.target.value);setDirty(true);setMessage("");}}/>
    <div className="production-tool-actions">
      <label title="Import a section/lyrics text or JSON file">▣
        <input type="file" accept=".txt,.json,text/plain,application/json"
          aria-label="Open section or lyric file"
          onChange={e=>{void readFile(e.target.files?.[0]);e.target.value="";}}/>
      </label>
      <label title="Append new sections"><input type="checkbox" checked={mode==="append"}
        onChange={e=>setMode(e.target.checked?"append":"replace")}/> Append</label>
      <button type="button" title="Restore authoritative saved section text" onClick={()=>{void load(true);}}>↺</button>
      <button type="button" disabled={saving||!content.trim()} onClick={()=>{void apply();}}>
        {saving?"…":"Apply"}
      </button>
    </div>
    {stale&&<small role="status">Timeline changed; reload to see new timestamps (unsaved text preserved).</small>}
    {message&&<small role="status">{message}</small>}
    {error&&<small role="alert">{error}</small>}
    <details className="production-tool-help">
      <summary>Section notation</summary>
      <small>One [Intro], [Verse 1], [Chorus], etc. per section; lyrics can appear beneath their header. Untimed sections are evenly distributed on import. Visual edits update the saved timestamps. Production blocks like <code>{"{Other.pan:right.60@2s:smooth}"}</code> support pan, and <code>{"{all.reset@2s:smooth}"}</code> restores defaults. Reverb sends use syntax such as <code>{"{Vocals.reverb:30@2s:smooth}"}</code>. Ending instructions belong to the last section: <code>{"{Master.fade:6s:smooth Master.tail:3s}"}</code>. Width, delay and other effects are not implemented yet. Width cues in legacy headers remain proposals.</small>
    </details>
  </section>;
}

function timeStamp(seconds:number){
  const min=Math.floor(seconds/60);
  const sec=(seconds%60).toFixed(3).padStart(6,"0").replace(/0+$/,"").replace(/\.$/,"");
  return min+":"+sec;
}
