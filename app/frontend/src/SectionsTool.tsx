import {useCallback,useEffect,useRef,useState} from "react";
import type {SongSection} from "./SectionEditor";
import {exportSongLyrics,type LyricExportFormat} from "./LyricPromptExport";

type Mode="replace"|"append";
/** Convert a server "Line N: ..." validation error to a specific editor span.
 * Preserve line numbers in the message; selection never alters the draft.
 */
export function errorLocation(content:string,message:string):{start:number;end:number;line:number}|null{
  const result=/\bline\s+(\d+)\b/i.exec(message);
  if(!result)return null;
  const line=Number(result[1]);
  if(!Number.isSafeInteger(line)||line<1)return null;
  const lines=content.split("\n");
  if(line>lines.length)return null;
  let start=0;
  for(let i=0;i<line-1;i++)start+=lines[i].length+1;
  const raw=lines[line-1].replace(/\r$/,"");
  const offset=raw.length-raw.trimStart().length;
  start+=offset;
  return {start,end:start+Math.max(1,raw.trim().length),line};
}

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
type SavedAutoPanTarget={section_id:string;target:"center";protected_sources:string[];transition_seconds:number;curve:"smooth"|"linear"};
type SavedEnding={fade_seconds:number;tail_seconds:number;curve:"smooth"|"linear"};
export function SectionsTool({jobId,songTitle,open,onClose,focused,revision,onApplied}:{
  jobId:string;songTitle:string;open:boolean;onClose:()=>void;focused:SongSection|null;
  revision:number;onApplied:(sections:SongSection[],targets:SavedPanTarget[],reverb:SavedReverbTarget[],width:SavedWidthTarget[],space:SavedSpaceTarget[],eq:SavedEqTarget[],dynamics:SavedDynamicsTarget[],gain:SavedGainTarget[],auto:SavedAutoPanTarget[],ending:SavedEnding)=>void;
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
  const [captions,setCaptions]=useState("");
  const [captionStatus,setCaptionStatus]=useState("");
  const [captionWarnings,setCaptionWarnings]=useState<string[]>([]);
  const [captionBusy,setCaptionBusy]=useState(false);
  const editor=useRef<HTMLTextAreaElement|null>(null);
  const errorTarget=errorLocation(content,error);
  function jumpToError(){
    if(!errorTarget)return;
    const node=editor.current;
    if(!node)return;
    node.focus();
    node.setSelectionRange(errorTarget.start,errorTarget.end);
    // setSelectionRange normally scrolls to the caret in modern browsers;
    // position the editor explicitly for multiline documents as a fallback.
    const style=window.getComputedStyle(node);
    const lineHeight=parseFloat(style.lineHeight)||parseFloat(style.fontSize)*1.4||18;
    const targetTop=(errorTarget.line-1)*lineHeight;
    if(targetTop<node.scrollTop||targetTop>node.scrollTop+node.clientHeight-lineHeight*2){
      node.scrollTop=Math.max(0,targetTop-lineHeight*3);
    }
  }

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
      const result=await r.json() as {sections?:SongSection[];detail?:string;auto_distributed?:boolean;imported_count?:number;pan_targets?:SavedPanTarget[];reverb_targets?:SavedReverbTarget[];width_targets?:SavedWidthTarget[];space_targets?:SavedSpaceTarget[];eq_targets?:SavedEqTarget[];dynamics_targets?:SavedDynamicsTarget[];gain_targets?:SavedGainTarget[];auto_pan_targets?:SavedAutoPanTarget[];ending?:SavedEnding};
      if(!r.ok||!result.sections)throw Error(result.detail||"Import failed");
      onApplied(result.sections,result.pan_targets||[],result.reverb_targets||[],result.width_targets||[],result.space_targets||[],result.eq_targets||[],result.dynamics_targets||[],result.gain_targets||[],result.auto_pan_targets||[],result.ending||{fade_seconds:0,tail_seconds:0,curve:"smooth"});
      setDirty(false);setStale(false);setCaptions("");setCaptionStatus("");
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
  async function prepareCaptions(){
    if(captionBusy)return;
    setCaptionBusy(true);setError("");setCaptionStatus("");
    try{
      if(dirty)throw Error("Apply or discard unsaved section-script changes before generating captions.");
      const response=await fetch(`/api/projects/${jobId}/lyrics/captions`,{cache:"no-store"});
      const data=await response.json() as {content?:string;cue_count?:number;excluded_directions?:number;
        warnings?:string[];timing?:string;detail?:string};
      if(!response.ok||!data.content)throw Error(data.detail||"No saved lyrics available");
      setCaptions(data.content);
      setCaptionWarnings(data.warnings||[]);
      setCaptionStatus((data.cue_count||0)+" captions generated from saved section timing. "+
        (data.excluded_directions||0)+" performance directions excluded. Review against playback.");
    }catch(e){setError(e instanceof Error?e.message:"Could not generate lyric captions");}
    finally{setCaptionBusy(false);}
  }
  async function copyModelLyrics(format:LyricExportFormat){
    try{
      if(!content.trim())throw Error("Load the whole-song section text before exporting.");
      const exported=exportSongLyrics(content,format);
      await navigator.clipboard.writeText(exported);
      setError("");
      setMessage((format==="yue2"?"YuE2":"ACE")+" lyrics copied. "+
        (dirty?"Includes unapplied section-text edits. ":"")+
        (format==="yue2"?"Set song-level style and ABC controls separately.":"Stage directions retained."));
    }catch(e){
      setMessage("");
      setError(e instanceof Error?e.message:"Could not copy lyrics to clipboard");
    }
  }
  function downloadCaptions(){
    if(!captions.trim())return;
    const blob=new Blob([captions],{type:"application/x-subrip;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;
    a.download=(songTitle.replace(/[\\/:*?"<>|]/g,"").trim()||"Song Harbor")+" - Lyrics.srt";
    document.body.appendChild(a);a.click();a.remove();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
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
      <button type="button" disabled={captionBusy||saving} title="Generate timestamped YouTube SRT subtitles from saved sections" onClick={()=>{void prepareCaptions();}}>
        {captionBusy?"Generating...":"Lyrics SRT"}
      </button>
      <button type="button" disabled={!content.trim()||saving} title="Copy YuE2 lyrics: section tags and lyrics only, without Song Harbor effects or stage directions" onClick={()=>{void copyModelLyrics("yue2");}}>Copy YuE2</button>
      <button type="button" disabled={!content.trim()||saving} title="Copy ACE lyrics: section tags, lyrics and performance notes; no Song Harbor effects" onClick={()=>{void copyModelLyrics("ace");}}>Copy ACE</button>
      <button type="button" disabled={saving||!content.trim()} onClick={()=>{void apply();}}>
        {saving?"…":"Apply"}
      </button>
    </div>
    {captions&&<div className="song-caption-export">
      <div className="production-tool-heading">
        <strong>YouTube lyric captions (.srt)</strong>
        <button type="button" onClick={()=>{setCaptions("");setCaptionStatus("");setCaptionWarnings([]);}} title="Close lyric export preview">×</button>
      </div>
      <small>Estimated lyric timing is evenly distributed within each saved section. Edit caption text and times below before uploading as YouTube subtitles.</small>
      <textarea aria-label="Editable YouTube SRT lyrics" spellCheck={false} value={captions} rows={12}
        onChange={e=>setCaptions(e.target.value)}/>
      {captionStatus&&<small role="status">{captionStatus}</small>}
      {captionWarnings.map((item,i)=><small role="status" key={i}>{item}</small>)}
      <button type="button" disabled={!captions.trim()} onClick={downloadCaptions}>Download .srt</button>
    </div>}
    {stale&&<small role="status">Timeline changed; reload to see new timestamps (unsaved text preserved).</small>}
    {message&&<small role="status">{message}</small>}
    {error&&<div role="alert" className="song-section-validation-error">
      <small>{error}</small>
      {errorTarget&&<button type="button" className="song-section-error-jump"
        onClick={jumpToError} title={"Jump to offending text on line "+errorTarget.line}>
        Go to line {errorTarget.line} ↗
      </button>}
    </div>}
    <details className="production-tool-help">
      <summary>Section notation</summary>
      <small>One [Intro], [Verse 1], [Chorus], etc. per section; lyrics can appear beneath their header. Production directives inside a single {`{...}`} block can be separated by spaces, LF, or Windows CRLF line breaks; use one directive per line for readability. Leave lyric lines outside the braces. Untimed sections are evenly distributed on import. Visual edits update the saved timestamps. Production blocks like <code>{"{Other.pan:right.60@2s:smooth}"}</code> support pan, and <code>{"{all.reset@2s:smooth}"}</code> restores defaults. Reverb sends use syntax such as <code>{"{Vocals.reverb:30@2s:smooth}"}</code>. Ending instructions belong to the last section: <code>{"{Master.fade:6s:smooth Master.tail:3s}"}</code>. Width uses <code>{"{Vocals.width:125@2s:smooth}"}</code> (0-200%, 100% unchanged). Early reflections use <code>{"{Vocals.space:20@2s:smooth}"}</code> (0-40%). Three EQ bands per stem use <code>{"{Vocals.eq1:320,1.2,-2@2s:smooth}"}</code> (30-16000 Hz, Q .3-12, gain -12 to +12 dB). Compression and vocal-keyed ducking are available via section script (Other.comp:-18,2 and Guitar.duck:3). De-essing is available as Vocals.deess:6500,2,-40,4@2s:smooth. Stem gain uses Drums.gain:+0.75@2s:smooth, relative to the saved mixer fader. Broadcast defaults such as all.gain:-1, all.pan:center, all.width:110, all.reverb:15, all.space:10, and all.eq1:1000,1,+1 apply to eligible stems unless explicitly overridden in that section. Auto.pan:center@8s:smooth performs bounded per-section balancing using eligible stems; explicit and inherited stem pans are protected. Auto.gain is not yet available. Live gain-reduction meters appear in the A/B tool. This editor contains the complete song script (all sections and lyrics), not just the currently selected section. Apply validates and persists the entire song. Width cues in legacy headers remain proposals.</small>
    </details>
  </section>;
}

function timeStamp(seconds:number){
  const min=Math.floor(seconds/60);
  const sec=(seconds%60).toFixed(3).padStart(6,"0").replace(/0+$/,"").replace(/\.$/,"");
  return min+":"+sec;
}
