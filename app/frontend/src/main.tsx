import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, FormField, Panel, Status } from "@tws-ui/core/react";
import { StemMixer } from "./StemMixer";
import type { SavedStem } from "./StemMixer";
import { FfmpegSetup } from "./FfmpegSetup";
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
type SongProject = {id: string; title: string; stems: SavedStem[]; source_duration_seconds?: number | null};
type Health = { ready: boolean; separator_ready: boolean; model: string; model_directory: string; ffmpeg?: {directory:string} | null; needs_setup?: string[] };
const API = "/api";

function App() {
  const [file, setFile] = useState<File | null>(null);
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

  async function openSong() {
    if (!recentChoice || openingSong) return;
    setOpeningSong(true);
    setError("");
    try {
      const response = await fetch(API + "/projects/" + recentChoice);
      const payload = await response.json() as {job?: Job; project?: SongProject; detail?: string};
      if (!response.ok || !payload.job || !payload.project) throw new Error(payload.detail || "Could not reopen song");
      setJob(null); // release previous mixer and streams before restoring
      setFile(null);
      setProject(payload.project);
      setJob(payload.job);
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
      } catch (e) {
        setError(e instanceof Error ? e.message : "Status check failed");
      }
    }, 1000);
    return () => clearInterval(poll);
  }, [job?.id, job?.status]);

  async function separate() {
    if (!file || busy || job && ["queued", "running"].includes(job.status)) return;
    if (!health?.ffmpeg) {
      pendingSeparation.current = true;
      setSetupOpen(true);
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
  const canStart = !!file && !!health?.separator_ready && !busy && !running;
  const missingCount = health?.needs_setup?.length ?? 0;
  function completedSetup(next: Health) {
    setHealth(next);
    setSetupOpen(false);
    if (pendingSeparation.current && next.ffmpeg) {
      pendingSeparation.current = false;
      void startSeparation();
    }
    if (next.ffmpeg && pendingMixRetry.current) {
      const retry = pendingMixRetry.current;
      pendingMixRetry.current = null;
      retry();
    }
  }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">◈</span><span>TWS STUDIOS</span><span className="brand-divider">/</span><strong>Song Harbor</strong></div>
      <div className="header-actions">
        <Status tone={health?.separator_ready ? "success" : "warning"}>{health?.separator_ready ? "Local engine" : "Engine unavailable"}</Status>
        <button type="button" className="dependency-indicator" title={missingCount ? `${missingCount} component(s) need setup` : "Component settings"}
          aria-label={missingCount ? `Components: ${missingCount} missing. Open setup.` : "Open component settings"}
          onClick={() => setSetupOpen(true)}>
          <span aria-hidden="true">⚙</span>
          {missingCount > 0 && <span className="dependency-count">{missingCount}</span>}
        </button>
      </div>
    </header>
    <main className="workspace">
      <section className="workspace-heading">
        <div><p className="eyebrow">AUDIO WORKBENCH / SEPARATION</p><h1>Make room for every instrument.</h1><p>Turn a finished recording into six editable stems, right here on your machine.</p></div>
        <span className="edition">M1 · STEM MIXER</span>
      </section>
      <FfmpegSetup open={setupOpen} onOpenChange={next => { setSetupOpen(next); if (!next) { pendingSeparation.current = false; pendingMixRetry.current = null; } }} onReady={completedSetup} />
      <div className="workspace-grid">
        <Panel elevation="raised" className="task-panel">
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
          <FormField label="Choose a recording" hint="WAV, FLAC, MP3, M4A, AIFF, or OGG · Up to 1 GiB">
            <input className="source-picker" type="file" accept=".wav,.flac,.mp3,.m4a,.aiff,.aif,.ogg,audio/*"
              disabled={!!running || busy} onChange={e => { setFile(e.target.files?.[0] || null); setJob(null); setProject(null); setError(""); }} />
          </FormField>
          {file && <div className="selected-file"><span title={file.name}>{file.name}</span><small>{(file.size / 1048576).toFixed(1)} MB</small></div>}
          <div className="separator-rule"/>
          <div className="section-label"><span>02</span><h2>Separation</h2></div>
          <div className="model-row"><div><strong>Demucs · Six stems</strong><small>Vocals · Drums · Bass · Guitar · Piano · Other</small></div><Status tone="neutral">Baseline</Status></div>
          <div className="action-row">
            <Button variant="primary" disabled={!canStart} onClick={separate}>{busy ? "Importing…" : running ? "Separating…" : "Separate stems"}</Button>
            {running && <Button variant="secondary" onClick={cancel}>Cancel</Button>}
          </div>
          {error && <div className="error-message" role="alert">{error}</div>}

        </Panel>
        <Panel elevation="raised" className="results-panel">
          <div className="section-label"><span>03</span><h2>Output stems</h2></div>
          <div className="job-status" role="status" aria-live="polite">
            <Status tone={statusTone}>{job ? job.status : "Ready for a song"}</Status>
            <span>{job?.message || "Choose a recording to get started."}</span>
          </div>
          {running && <div className="progress-indeterminate" aria-label="Separation in progress"><span/></div>}
          {finished && job && <>
            <StemMixer key={job.id} jobId={job.id} files={job.files} expectedDuration={job.source_duration_seconds ?? undefined} initialTitle={project?.id === job.id ? project.title : job.filename.replace(/\.[^.]+$/, "")} savedStems={project?.id === job.id ? project.stems : undefined} onSaved={() => { void refreshSongs(); }} onMissingFfmpeg={retry => { pendingMixRetry.current = retry; setSetupOpen(true); }} />
            <details className="stem-download-details"><summary>Individual stem files</summary>
              <div className="stems">
                {job.files.map(name => <div className="stem" key={name}>
                  <div className="stem-symbol">♫</div><span title={name}>{name}</span>
                  <a href={API + "/jobs/" + job.id + "/files/" + encodeURIComponent(name)} download={name} title={"Download " + name}>Download</a>
                </div>)}
              </div>
            </details>
          </>}
          {!finished && !running && <div className="empty-result"><div className="waveform" aria-hidden="true">▂▃▅▇▆▄▂▁▃▆▇▅▂</div><p>Your separated tracks will appear here.</p></div>}
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
      <p className="footnote">Local processing · Original recording preserved · Six-stem Demucs baseline</p>
    </main>
  </div>;
}

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);
