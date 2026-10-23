import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, FormField, IconButton, Panel, Status } from "@tws-ui/core/react";
import { StemMixer } from "./StemMixer";
import type { SavedStem } from "./StemMixer";
import type { SongSection } from "./SectionEditor";
import { FfmpegSetup } from "./FfmpegSetup";
import { AppSettings } from "./AppSettings";
import { HelpDialog } from "./HelpDialog";
import { UpdateControl } from "./UpdateControl";
import { LibraryHome } from "./LibraryHome";
import "@tws-ui/core/tokens.css";
import "@tws-ui/core/react/styles.css";
import "./song-harbor.css";

type Job = {
  id: string;
  filename: string;
  model: string;
  status: "uploading" | "queued" | "running" | "complete" | "error" | "cancelled";
  message: string;
  files: string[];
  logs: string[];
  elapsed_seconds: number | null;
  source_duration_seconds?: number;
};
type RecentSong = {id: string; title: string; filename: string; created_at: number; recovered?: boolean};
type SongProject = {id: string; title: string; stems: SavedStem[]; sections?: SongSection[]; source_tracks?: {original_filename:string;working_filename:string;stem_alias:string;track_id?:string;display_name?:string}[]; source_duration_seconds?: number | null};
type Health = { instance_token?:string;ready: boolean; separator_ready: boolean; model: string; model_directory: string; ffmpeg?: {directory:string} | null; needs_setup?: string[] };
const API = "/api";

function suggestTrackTitle(files:File[]):string{
  if(!files.length)return "";
  const roles=/[\s._-]*\(?(?:vocals?|vox|voice|drums?|percussion|perc|beats|bass|guitars?|gtr|piano|keys|keyboard|other|instrumental|instruments|music)\)?(?:[\s._-]*\d{1,2})?$/i;
  const parts=files.map(file=>file.name.replace(/\.[^.]+$/,"").replace(roles,"").split(/[\s._-]+/).filter(Boolean));
  const words:string[]=[];
  for(const matches of Array.from({length:Math.min(...parts.map(p=>p.length))},(_,i)=>parts.map(p=>p[i]))){
    if(matches.some(word=>word.toLowerCase()!==matches[0].toLowerCase()))break;
    words.push(matches[0]);
  }
  return words.join(" ")||"Imported song";
}

function App() {
  const [view, setView] = useState<"library"|"song">("library");
  const [file, setFile] = useState<File | null>(null);
  const [importMode,setImportMode]=useState<"recording"|"tracks">("recording");
  const [trackFiles,setTrackFiles]=useState<File[]>([]);
  const [trackTitle,setTrackTitle]=useState("");
  const [suggestedTitle,setSuggestedTitle]=useState("");
  const [titleManuallyEdited,setTitleManuallyEdited]=useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);
  const [recentSongs, setRecentSongs] = useState<RecentSong[]>([]);
  const [recentChoice, setRecentChoice] = useState("");
  const [openingSong, setOpeningSong] = useState(false);
  const [project, setProject] = useState<SongProject | null>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const pendingSeparation = useRef(false);
  const pendingMixRetry = useRef<(() => void) | null>(null);

  useEffect(() => {
    fetch(API + "/health").then(r => r.ok ? r.json() : Promise.reject())
      .then((data: Health) => setHealth(data))
      .catch(() => setError("Local Song Harbor backend is unavailable. Use the launcher to set up the application."));
  }, []);

  async function refreshSongs() {
    try {
      const response = await fetch(API + "/projects");
      if (!response.ok) return;
      const data = await response.json() as {projects: RecentSong[]};
      setRecentSongs(data.projects);
    } catch { /* Recent songs are supplemental; keep current work available. */ }
  }

  useEffect(() => { void refreshSongs(); }, []);

  useEffect(() => {
    if (!job || job.status !== "complete") return;
    let cancelled = false;
    void fetch(API + "/projects/" + job.id)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then((data: {project: SongProject}) => { if (!cancelled) setProject(data.project); })
      .catch(() => { /* Song can still be mixed if the manifest is unavailable. */ });
    void refreshSongs();
    return () => { cancelled = true; };
  }, [job?.id, job?.status]);

  async function openSongById(ident: string) {
    if (!ident || openingSong) return;
    setOpeningSong(true);
    setError("");
    try {
      const response = await fetch(API + "/projects/" + ident);
      const payload = await response.json() as {job?: Job; project?: SongProject; detail?: string};
      if (!response.ok || !payload.job || !payload.project) throw new Error(payload.detail || "Could not reopen song");
      setJob(null); // release previous mixer and streams before restoring
      setFile(null);
      setProject(payload.project);
      setJob(payload.job);
      setView("song");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reopen song");
    } finally {
      setOpeningSong(false);
    }
  }

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const poll = setInterval(async () => {
      try {
        const response = await fetch(API + "/jobs/" + job.id);
        if (!response.ok) throw new Error("Could not read separation status");
        setJob(await response.json() as Job);
      setView("song");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Status check failed");
      }
    }, 1000);
    return () => clearInterval(poll);
  }, [job?.id, job?.status]);

  async function openSong() {
    await openSongById(recentChoice);
  }

  async function separate() {
    if (!file || busy || job && ["queued", "running"].includes(job.status)) return;
    // This is a recoverable feature action: do not disable it for missing FFmpeg.
    if (!health?.ffmpeg) {
      pendingSeparation.current = true;
      setSetupOpen(true);
      return;
    }
    if (!health.separator_ready) {
      setError("The stem separator is not installed in this runtime yet. Relaunch Song Harbor to run environment setup.");
      return;
    }
    await startSeparation();
  }

  async function startSeparation() {
    if (!file || busy) return;
    setBusy(true);
    setJob(null);
    setProject(null);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(API + "/jobs", { method: "POST", body });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({})) as { detail?: string };
        if (response.status === 409 && /ffmpeg/i.test(detail.detail || "")) {
          pendingSeparation.current = true;
          setSetupOpen(true);
          const latest = await fetch(API + "/health").then(r => r.json() as Promise<Health>);
          setHealth(latest);
          return;
        }
        throw new Error(detail.detail || "Could not start separation");
      }
      setJob(await response.json() as Job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function importSelectedTracks(){
    if(busy||trackFiles.length<2||trackFiles.length>129)return;
    setBusy(true);setError("");setJob(null);setProject(null);
    const data=new FormData();
    for(const track of trackFiles)data.append("files",track);
    data.append("title",trackTitle.trim()||suggestedTitle);
    try{
      const response=await fetch(API+"/jobs/import-tracks",{method:"POST",body:data});
      if(!response.ok){
        const details=await response.json().catch(()=>({})) as {detail?:string};
        throw Error(details.detail||"Track import failed");
      }
      setJob(await response.json() as Job);
    }catch(e){setError(e instanceof Error?e.message:"Track import failed");}
    finally{setBusy(false);}
  }

  async function openFolder() {
    if (!job) return;
    const result = await fetch(API + "/jobs/" + job.id + "/open-folder", { method: "POST" });
    if (!result.ok) setError("Could not open output folder.");
  }

  async function cancel() {
    if (!job) return;
    try {
      const response = await fetch(API + "/jobs/" + job.id + "/cancel", { method: "POST" });
      if (!response.ok) throw new Error("Could not cancel job");
      setJob(await response.json() as Job);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    }
  }

  const running = job && ["queued", "running"].includes(job.status);
  const finished = job?.status === "complete";
  const statusTone = finished ? "success" : job?.status === "error" ? "danger" : running ? "info" : "neutral";
  const canStart = !!file && !!health && !busy && !running;
  const ffmpegNeeded = !!file && !!health && !health.ffmpeg;
  const missingCount = health?.needs_setup?.length ?? 0;
  function completedSetup(next: Health) {
    setHealth(next);
    setSetupOpen(false);
    if (pendingSeparation.current && next.ffmpeg) {
      pendingSeparation.current = false;
      if (next.separator_ready) {
        void startSeparation();
      } else {
        setError("FFmpeg is configured, but the separator engine is missing. Relaunch Song Harbor to repair its Python environment.");
      }
    }
    if (next.ffmpeg && pendingMixRetry.current) {
      const retry = pendingMixRetry.current;
      pendingMixRetry.current = null;
      retry();
    }
  }

  const [quitting,setQuitting]=useState(false);
  async function quitApplication(){
    // Confirmation guards unsaved browser edits; backend rejects active jobs.
    if(!window.confirm("Close Song Harbor? Apply/save any unsaved section or mixer changes first."))return;
    if(!health?.instance_token){window.alert("This browser is not linked to a dedicated Song Harbor instance. Close its window manually.");return;}
    setQuitting(true);
    try{
      const response=await fetch("/api/runtime/quit",{method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({instance_token:health.instance_token})});
      if(!response.ok){
        const error=await response.json() as {detail?:string};
        throw Error(error.detail||"Cannot close this Song Harbor instance");
      }
      window.close();
      // Browsers may forbid script closing a user-owned tab.
      document.body.innerHTML="<main style='font:18px system-ui;padding:12vh 12vw'>Song Harbor has closed. You can close this browser tab.</main>";
    }catch(error){window.alert(error instanceof Error?error.message:"Could not close Song Harbor");}
    finally{setQuitting(false);}
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">◈</span><span>TWS STUDIOS</span><span className="brand-divider">/</span><strong>Song Harbor</strong></div>
      <div className="header-actions">
        <UpdateControl instanceToken={health?.instance_token||""}/>
        <Status tone={health?.separator_ready ? "success" : "warning"}>{health?.separator_ready ? "Local engine" : "Engine unavailable"}</Status>
        <button type="button" className="dependency-indicator" title={missingCount ? `${missingCount} component(s) need setup. Open settings.` : "Settings"}
          aria-label={missingCount ? `Settings, ${missingCount} missing component(s)` : "Open settings"}
          onClick={() => setSettingsOpen(true)}>
          <span aria-hidden="true">⚙</span>
          {missingCount > 0 && <span className="dependency-count">{missingCount}</span>}
        </button>
        <button type="button" className="dependency-indicator song-help-trigger" title="Help and user guide"
          aria-label="Open Song Harbor help" aria-haspopup="dialog" onClick={()=>setHelpOpen(true)}>
          <span aria-hidden="true">i</span>
        </button>
        <button type="button" className="song-close-app" aria-label="Close Song Harbor"
          title="Close Song Harbor" disabled={quitting} onClick={()=>{void quitApplication();}}>×</button>
      </div>
    </header>
    <HelpDialog open={helpOpen} onOpenChange={setHelpOpen}/>
    <AppSettings open={settingsOpen} onOpenChange={setSettingsOpen} health={health} onReady={next => setHealth(next)} />
    <FfmpegSetup open={setupOpen} onOpenChange={next => { setSetupOpen(next); if (!next) { pendingSeparation.current = false; pendingMixRetry.current = null; } }} onReady={completedSetup} />
    {view === "library" ? <LibraryHome onOpenSong={ident => {void openSongById(ident);}}
      onImport={() => {setFile(null);setJob(null);setProject(null);setView("song");}}/> : <main className={"workspace"+(job?" workspace--song-session":"")}>
      <button className="back-to-library" title="Back to Library" onClick={() => setView("library")}>← Library</button>
      <section className="song-session-heading">
        <div className="session-breadcrumb">{job ? "LIBRARY / SONG" : "LIBRARY / IMPORT"}</div>
        <h1>{job ? (project?.title || job.filename.replace(/\\.[^.]+$/, "")) : "Import song"}</h1>
      </section>

      <div className={"workspace-grid" + (job ? " is-session" : "")}>
        {!job && <Panel elevation="raised" className="task-panel">
          <div className="section-label"><span>01</span><h2>Source audio</h2></div>
          {recentSongs.length > 0 && <details className="recent-songs">
            <summary>Open saved song ({recentSongs.length})</summary>
            <div className="recent-song-controls">
              <select aria-label="Saved songs" value={recentChoice} disabled={!!running || busy || openingSong}
                onChange={e => setRecentChoice(e.target.value)}>
                <option value="">Choose a saved song…</option>
                {recentSongs.map(song => <option key={song.id} value={song.id}>{song.title}</option>)}
              </select>
              <Button variant="secondary" size="compact" disabled={!recentChoice || !!running || busy || openingSong}
                onClick={openSong}>{openingSong ? "Opening…" : "Open"}</Button>
            </div>
          </details>}
          <div className="song-import-mode" role="group" aria-label="Import source type">
            <button type="button" aria-pressed={importMode==="recording"}
              onClick={()=>setImportMode("recording")}>Single recording · separate stems</button>
            <button type="button" aria-pressed={importMode==="tracks"}
              onClick={()=>setImportMode("tracks")}>Multiple tracks · already separated</button>
          </div>
          {importMode==="recording"?<>
          <FormField label="Choose a recording" hint="WAV, FLAC, MP3, M4A, AIFF, or OGG · Up to 1 GiB">
            <input className="source-picker" type="file" accept=".wav,.flac,.mp3,.m4a,.aiff,.aif,.ogg,audio/*"
              disabled={!!running || busy} onChange={e => { setFile(e.target.files?.[0] || null); setJob(null); setProject(null); setError(""); }} />
          </FormField>
          {file && <div className="selected-file"><span title={file.name}>{file.name}</span><small>{(file.size / 1048576).toFixed(1)} MB</small></div>}
          <div className="separator-rule"/>
          <div className="section-label"><span>02</span><h2>Separation</h2></div>
          <div className="model-row"><div><strong>Demucs · Six stems</strong><small>Vocals · Drums · Bass · Guitar · Piano · Other</small></div><Status tone="neutral">Baseline</Status></div>
          <div className="action-row">
            <span className={"separator-action" + (ffmpegNeeded ? " needs-setup" : "")}
              title={ffmpegNeeded ? "FFmpeg required — click to locate or install, then separation will begin." : "Separate audio into six stems"}>
              <IconButton className="separator-trigger" icon={<svg viewBox="0 0 32 32" width="28" height="28"
                  fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                  aria-hidden="true">
                  <path d="M4 9h5m3 0h16M4 16h12m4 0h8M4 23h18m4 0h2" />
                  <path d="M9 5v8M16 12v8M22 19v8" />
                </svg>}
                label={ffmpegNeeded ? "Separate stems — FFmpeg needed; click to install or locate FFmpeg" : busy ? "Importing audio" : "Separate stems"}
                disabled={!canStart} onClick={() => {void separate();}} />
              {ffmpegNeeded && <span className="separator-requirement" aria-hidden="true">!</span>}
            </span>
            {running && <Button variant="secondary" onClick={cancel}>Cancel</Button>}
          </div>

          </>:<>
            <FormField label="Choose aligned tracks" hint="2-64 audio tracks, or a channel-split export (12 mono WAVs + manifest.json) · starts at 0:00">
              <input className="source-picker" type="file" multiple accept=".wav,.flac,.mp3,.m4a,.aiff,.aif,.ogg,.json,audio/*"
                disabled={busy} onChange={event=>{
                  const chosen=Array.from(event.target.files||[]);
                  const manifest=chosen.find(file=>file.name.toLowerCase()==="manifest.json");
                  const audio=chosen.filter(file=>file!==manifest);
                  setTrackFiles(chosen);setError("");
                  const updateTitle=(suggestion:string)=>{
                    setSuggestedTitle(suggestion);
                    if(!titleManuallyEdited)setTrackTitle(suggestion);
                  };
                  if(manifest){
                    void manifest.text().then(text=>{
                      const parsed=JSON.parse(text) as {format?:string;tracks?:{source?:string}[]};
                      if(parsed.format!=="song-harbor-stereo-channel-split")throw Error("Unsupported channel manifest");
                      const sources=[...new Set((parsed.tracks||[]).map(t=>t.source).filter((value):value is string=>!!value))];
                      updateTitle(suggestTrackTitle(sources.map(name=>({name} as File))));
                    }).catch(()=>setError("Invalid split-channel manifest; include the original manifest.json"));
                  }else updateTitle(suggestTrackTitle(audio));
                }}/>
            </FormField>
            {trackFiles.length>0&&<>
              <label className="song-track-title-label" htmlFor="import-tracks-title">Song title <small>(suggested, editable)</small></label>
              <input id="import-tracks-title" className="song-track-title" value={trackTitle}
                maxLength={120} onChange={event=>{setTrackTitle(event.target.value);setTitleManuallyEdited(true);}}
                placeholder="Song title"/>
              <div className="song-import-track-list" aria-label="Selected tracks">
                {trackFiles.map((track,i)=><div key={i} className="selected-file">
                  <span title={track.name}>{i+1}. {track.name}</span>
                  <small>{(track.size/1048576).toFixed(1)} MB</small>
                </div>)}
              </div>
              <small>{trackFiles.some(item=>item.name.toLowerCase()==="manifest.json")?"Channel-split manifest selected: complete L/R pairs will be reconstructed as their parent stems with L/R routing active.":"Working copies align at 0:00; original files stay intact. Include manifest.json with an L/R channel export to reconstruct original parent stems."}</small>
            </>}
            <div className="action-row">
              <Button variant="primary" size="compact" disabled={busy||trackFiles.length<2||trackFiles.length>129||!trackTitle.trim()}
                onClick={()=>{void importSelectedTracks();}}>{busy?"Importing tracks…":"Import selected tracks as one song"}</Button>
            </div>
          </>}
          {error && <div className="error-message" role="alert">{error}</div>}

        </Panel>}
        <Panel elevation="raised" className="results-panel">
          <div className="section-label"><span>♫</span><h2>{finished ? "Stem workspace" : "Session"}</h2></div>
          <div className="job-status" role="status" aria-live="polite">
            <Status tone={statusTone}>{job ? job.status : "Ready for a song"}</Status>
            <span>{job?.message || "Choose a recording to get started."}</span>
          </div>
          {running && <div className="progress-indeterminate" aria-label="Separation in progress"><span/></div>}
          {finished && job && <>
            <StemMixer key={job.id+":"+(project?.source_tracks||[]).map(t=>t.stem_alias).join("|")} jobId={job.id} files={job.files} expectedDuration={job.source_duration_seconds ?? undefined} initialTitle={project?.id === job.id ? project.title : job.filename.replace(/\.[^.]+$/, "")} savedStems={project?.id === job.id ? project.stems : undefined} trackLabels={project?.id===job.id ? Object.fromEntries((project.source_tracks||[]).map(t=>[t.working_filename,(t.display_name||t.original_filename.replace(/\.[^.]+$/,""))])):undefined} trackAliases={project?.id===job.id ? Object.fromEntries((project.source_tracks||[]).map(t=>[t.working_filename,t.stem_alias])):undefined} initialSections={project?.id === job.id ? project.sections : undefined} onSaved={() => { void refreshSongs(); }} onTrackRenamed={updated=>setProject(updated as SongProject)} onMissingFfmpeg={retry => { pendingMixRetry.current = retry; setSetupOpen(true); }} />
            <details className="stem-download-details"><summary>Individual stem files</summary>
              <div className="stems">
                {job.files.map(name => <div className="stem" key={name}>
                  <div className="stem-symbol">♫</div><span title={name}>{name}</span>
                  <a href={API + "/jobs/" + job.id + "/files/" + encodeURIComponent(name)} download={name} title={"Download " + name}>Download</a>
                </div>)}
              </div>
            </details>
          </>}
          {!finished && !running && !job && <div className="empty-result"><div className="waveform" aria-hidden="true">▂▃▅▇▆▄▂▁▃▆▇▅▂</div><p>Your separated tracks will appear here.</p></div>}
          {job && <footer className="result-footer">
            {job.elapsed_seconds != null && <small>Elapsed: {job.elapsed_seconds.toFixed(2)} s</small>}
            <div className="result-actions">
              {finished && <Button variant="secondary" onClick={openFolder}>Open folder</Button>}
              <Button variant="subtle" onClick={() => setShowDetails(v => !v)}>{showDetails ? "Hide details" : "Details"}</Button>
            </div>
          </footer>}
          {showDetails && job && <pre className="job-logs">{job.logs.length ? job.logs.join("\n") : "No logs yet."}</pre>}
        </Panel>
      </div>

    </main>}
  </div>;
}

class RootGuard extends React.Component<{children:React.ReactNode},{failure:string|null}>{
  state:{failure:string|null}={failure:null};
  static getDerivedStateFromError(error:unknown){
    return {failure:error instanceof Error?error.message:String(error)};
  }
  componentDidCatch(error:unknown,details:React.ErrorInfo){
    console.error("Song Harbor UI rendering failed",error,details.componentStack);
  }
  render(){
    if(this.state.failure){
      return <main role="alert" style={{fontFamily:"system-ui",maxWidth:760,margin:"10vh auto",
        padding:26,background:"#fff",border:"1px solid #cbb",borderRadius:10,color:"#232323"}}>
        <h1>Song Harbor encountered a startup error</h1>
        <p>No project or audio files have been changed. Copy this message into the issue report
          and try Ctrl+Shift+R once.</p>
        <pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{this.state.failure}</pre>
      </main>;
    }
    return this.props.children;
  }
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><RootGuard><App /></RootGuard></React.StrictMode>);
