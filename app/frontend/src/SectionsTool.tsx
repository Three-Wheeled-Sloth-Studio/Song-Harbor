import {useCallback,useEffect,useRef,useState} from "react";
import type {SongSection} from "./SectionEditor";

type Mode="replace"|"append";
// Retain unapplied editor drafts while a user switches between floating tools.
// Deliberately in-memory: edits are not silently written to a project or disk.
const temporarySectionDrafts=new Map<string,string>();
type ExportData={content:string;sections:SongSection[];detail?:string};
import type {SavedPanTarget} from "./SectionPanTool";
type SavedReverbTarget={section_id:string;source_key:string;wet:number;transition_seconds:number;curve:"linear"|"smooth"};
type SavedWidthTarget={section_id:string;source_key:string;width:number;transition_seconds:number;curve:"linear"|"smooth"};
type SavedSpaceTarget={section_id:string;source_key:string;amount:number;transition_seconds:number;curve:"linear"|"smooth"};
type SavedEqTarget={section_id:string;source_key:string;band:number;frequency:number;q:number;gain_db:number;transition_seconds:number;curve:"linear"|"smooth"};
export type SavedDynamicsTarget={section_id:string;source_key:string;kind:"comp"|"duck"|"deess";threshold_db:number;ratio:number;depth_db:number;frequency?:number;q?:number;max_reduction_db?:number;transition_seconds:number;curve:"smooth"|"linear"};
type SavedGainTarget={section_id:string;source_key:string;gain_db:number;transition_seconds:number;curve:"smooth"|"linear"};
type SavedEnding={fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"};
export function SectionsTool({jobId,open,onClose,focused,revision,onApplied}:{
  jobId:string;open:boolean;onClose:()=>void;focused:SongSection|null;
  revision:number;onApplied:(sections:SongSection[],targets:SavedPanTarget[],reverb:SavedReverbTarget[],width:SavedWidthTarget[],space:SavedSpaceTarget[],eq:SavedEqTarget[],dynamics:SavedDynamicsTarget[],gain:SavedGainTarget[],ending:SavedEnding)=>void;
}){
  const [content,setContent]=useState(()=>temporarySectionDrafts.get(jobId)||"");
  const [dirty,setDirty]=useState(()=>temporarySectionDrafts.has(jobId));
  useEffect(()=>{
    if(dirty)temporarySectionDrafts.set(jobId,content);
    else temporarySectionDrafts.delete(jobId);
  },[content,dirty,jobId]);
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
      const r=await fetch(`/api/projects/${jobId}/sections/export`,{cache:"no-store"});
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
    if(!open){
      // A closed editor must never rely on the previous cached revision.
      loadedRevision.current=-1;
      return;
    }
    if(loadedRevision.current===revision)return;
    void load();
  },[open,revision,load]);
  useEffect(()=>{loadedRevision.current=-1;
    setContent(temporarySectionDrafts.get(jobId)||"");
    setDirty(temporarySectionDrafts.has(jobId));
  },[jobId]);
  // Focus a section only when the navigation target changes, never on typing.
  // React re-renders with each keystroke; watching content here forced the
  // caret back to the header and made the script effectively uneditable.
  const navigationKey=focused?focused.id:null;
  useEffect(()=>{
    if(!open||!focused||dirty)return;
    const node=editor.current;
    if(!node)return;
    const tags=[...node.value.matchAll(/^\[[^\n]*\]/gm)];
    const match=tags.find(x=>x[0].startsWith("["+focused.kind) &&
      x[0].includes(" "+timeStamp(focused.start_seconds)+"-"));
    if(match){
      node.focus();
      node.setSelectionRange(match.index||0,(match.index||0)+match[0].length);
    }
  // Section navigation depends on selected ID and opening the tool, not editor content.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[navigationKey,open]);

  async function apply(){
    if(!content.trim()||saving)return;
    setSaving(true);setError("");setMessage("");
    try{
      const r=await fetch(`/api/projects/${jobId}/sections/import`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content,mode})
      });
      const result=await r.json() as {sections?:SongSection[];detail?:string;auto_distributed?:boolean;imported_count?:number;pan_targets?:SavedPanTarget[];reverb_targets?:SavedReverbTarget[];width_targets?:SavedWidthTarget[];space_targets?:SavedSpaceTarget[];eq_targets?:SavedEqTarget[];dynamics_targets?:SavedDynamicsTarget[];gain_targets?:SavedGainTarget[];ending?:SavedEnding};
      if(!r.ok||!result.sections)throw Error(result.detail||"Import failed");
      onApplied(result.sections,result.pan_targets||[],result.reverb_targets||[],result.width_targets||[],result.space_targets||[],result.eq_targets||[],result.dynamics_targets||[],result.gain_targets||[],result.ending||{fade_seconds:0,tail_seconds:0,curve:"smooth"});
      setDirty(false);setStale(false);
      loadedRevision.current=-1;
      setMode("replace");
      const reload=await fetch(`/api/projects/${jobId}/sections/export`,{cache:"no-store"});
      if(!reload.ok)throw Error("Saved, but verification reload failed. Reopen the section tool before further edits.");
      const saved=await reload.json() as ExportData;
      if(!saved.content||saved.sections.length!==result.sections.length)
        throw Error("Saved, but the reloaded script did not match. Further editing blocked pending inspection.");
      setContent(saved.content);
      setDirty(false);
      loadedRevision.current=revision+1;
      setMessage(result.auto_distributed?"Sections placed · saved reload verified":"Saved · section sheet reloaded from disk");
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
      <strong>Whole-song script · all sections and lyrics</strong>
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
      <small>One [Intro], [Verse 1], [Chorus], etc. per section; lyrics can appear beneath their header. Untimed sections are evenly distributed on import. Visual edits update the saved timestamps. Production blocks like <code>{"{Other.pan:right.60@2s:smooth}"}</code> support pan, and <code>{"{all.reset@2s:smooth}"}</code> restores defaults. Reverb sends use syntax such as <code>{"{Vocals.reverb:30@2s:smooth}"}</code>. Ending instructions belong to the last section: <code>{"{Master.fade:6s:smooth Master.tail:3s}"}</code>. Width uses <code>{"{Vocals.width:125@2s:smooth}"}</code> (0-150%, 100% unchanged). Early reflections use <code>{"{Vocals.space:20@2s:smooth}"}</code> (0-40%). Three EQ bands per stem use <code>{"{Vocals.eq1:320,1.2,-2@2s:smooth}"}</code> (30-16000 Hz, Q .3-12, gain -12 to +12 dB). Compression and vocal-keyed ducking are available via section script (Other.comp:-18,2 and Guitar.duck:3). De-essing is available as Vocals.deess:6500,2,-40,4@2s:smooth. Stem gain uses Drums.gain:+0.75@2s:smooth, relative to the saved mixer fader. Broadcast defaults such as all.gain:-1, all.pan:center, all.width:110, all.reverb:15, all.space:10, and all.eq1:1000,1,+1 apply to eligible stems unless explicitly overridden in that section. Automatic compensation via auto.* is not yet available. Live gain-reduction meters appear in the A/B tool. This editor contains the complete song script (all sections and lyrics), not just the currently selected section. Apply validates and persists the entire song. Width cues in legacy headers remain proposals.</small>
    </details>
  </section>;
}

function timeStamp(seconds:number){
  const min=Math.floor(seconds/60);
  const sec=(seconds%60).toFixed(3).padStart(6,"0").replace(/0+$/,"").replace(/\.$/,"");
  return min+":"+sec;
}
