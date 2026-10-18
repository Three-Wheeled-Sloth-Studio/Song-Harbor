import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, FormField, Panel, Status } from "@tws-ui/core/react";
import { StemMixer } from "./StemMixer";
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
type Health = { ready: boolean; model: string; model_directory: string; ffmpeg?: {directory:string} | null; needs_setup?: string[] };
const API = "/api";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    fetch(API + "/health").then(r => r.ok ? r.json() : Promise.reject())
      .then((data: Health) => setHealth(data))
      .catch(() => setError("Local Song Harbor backend is unavailable. Use the launcher to set up the application."));
  }, []);

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
    setBusy(true);
    setJob(null);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(API + "/jobs", { method: "POST", body });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({})) as { detail?: string };
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
  const canStart = !!file && !!health?.ready && !busy && !running;
  const ffmpegMissing = !!health && !health.ffmpeg;

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">◈</span><span>TWS STUDIOS</span><span className="brand-divider">/</span><strong>Song Harbor</strong></div>
      <Status tone={health?.ready ? "success" : "warning"}>{health?.ready ? "Local engine ready" : "Engine unavailable"}</Status>
    </header>
    <main className="workspace">
      <section className="workspace-heading">
        <div><p className="eyebrow">AUDIO WORKBENCH / SEPARATION</p><h1>Make room for every instrument.</h1><p>Turn a finished recording into six editable stems, right here on your machine.</p></div>
        <span className="edition">M1 · STEM MIXER</span>
      </section>
      {ffmpegMissing && <FfmpegSetup onReady={setHealth} />}
      <div className="workspace-grid">
        <Panel elevation="raised" className="task-panel">
          <div className="section-label"><span>01</span><h2>Source audio</h2></div>
          <FormField label="Choose a recording" hint="WAV, FLAC, MP3, M4A, AIFF, or OGG · Up to 1 GiB">
            <input className="source-picker" type="file" accept=".wav,.flac,.mp3,.m4a,.aiff,.aif,.ogg,audio/*"
              disabled={!!running || busy} onChange={e => { setFile(e.target.files?.[0] || null); setJob(null); setError(""); }} />
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
          {health?.ffmpeg && <div className="dependency-configured"><span>FFmpeg: {health.ffmpeg.directory}</span><Button size="compact" variant="subtle" onClick={() => setHealth({...health, ffmpeg: null})}>Change</Button></div>}
        </Panel>
        <Panel elevation="raised" className="results-panel">
          <div className="section-label"><span>03</span><h2>Output stems</h2></div>
          <div className="job-status" role="status" aria-live="polite">
            <Status tone={statusTone}>{job ? job.status : "Ready for a song"}</Status>
            <span>{job?.message || "Choose a recording to get started."}</span>
          </div>
          {running && <div className="progress-indeterminate" aria-label="Separation in progress"><span/></div>}
          {finished && job && <>
            <StemMixer jobId={job.id} files={job.files} expectedDuration={job.source_duration_seconds} />
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
