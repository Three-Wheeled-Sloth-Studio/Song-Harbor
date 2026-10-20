import { useEffect, useState } from "react";
import { Button, Dialog, Status } from "@tws-ui/core/react";

type FfmpegPair = {directory: string; ffmpeg: string; ffprobe: string};
type Health = { ready: boolean; separator_ready: boolean; model: string; model_directory: string; ffmpeg?: FfmpegPair | null; needs_setup?: string[] };
type Settings = {found: FfmpegPair | null; suggested_install_directory: string; config_path: string};
type InstallStatus = {id: string; status: string; message: string; phase?: string; progress_percent?: number | null};
const BASE = "/api/dependencies/ffmpeg";

async function json<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const result = await response.json() as T & {detail?: string};
  if (!response.ok) throw new Error(result.detail || "Operation failed");
  return result;
}
async function post<T>(url: string, payload?: object): Promise<T> {
  return json<T>(url, {method: "POST", headers: payload ? {"Content-Type": "application/json"} : undefined,
    body: payload ? JSON.stringify(payload) : undefined});
}

export function FfmpegSetup({open, onOpenChange, onReady}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onReady: (health: Health) => void;
}) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [path, setPath] = useState("");
  const [installPath, setInstallPath] = useState("");
  const [matches, setMatches] = useState<FfmpegPair[]>([]);
  const [action, setAction] = useState("");
  const [installJob, setInstallJob] = useState<InstallStatus | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refresh(closeAfterSetup = false) {
    const data = await json<Settings>(BASE);
    setSettings(data);
    setInstallPath(current => current || data.suggested_install_directory);
    if (data.found) {
      setMessage("FFmpeg detected and saved at " + data.found.directory);
      if (closeAfterSetup) {
        const health = await json<Health>("/api/health");
        onReady(health);
      }
    }
  }
  useEffect(() => { if (open) refresh(false).catch(e => setError(String(e))); }, [open]);
  useEffect(() => {
    if (!installJob || !["queued", "running"].includes(installJob.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const result = await json<InstallStatus>(BASE + "/install/" + installJob.id);
        setInstallJob(result);
        if (result.status === "complete") {
          await refresh(true);
        } else if (result.status === "error") {
          setError(result.message);
        }
      } catch (e) { setError(String(e)); }
    }, 900);
    return () => window.clearInterval(timer);
  }, [installJob?.id, installJob?.status]);

  async function perform(name: string, operation: () => Promise<void>) {
    setAction(name); setError(""); setMessage("");
    try { await operation(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setAction(""); }
  }

  const installing = !!installJob && ["queued", "running"].includes(installJob.status);
  return <Dialog open={open} onOpenChange={next => { if (!installing) onOpenChange(next); }}
    title={settings?.found ? "FFmpeg settings" : "FFmpeg not found"}
    description="Used for separation and mix export. Expand only the action you need.">
    <div className="dependency-panel">
    {settings?.found && <div className="dependency-found"><Status tone="success">Configured</Status><span>{settings.found.directory}</span></div>}

    <details className="dependency-choice" open={undefined}>
      <summary>Locate existing installation</summary>
      <div className="dependency-inline">
        <input aria-label="Existing FFmpeg folder" value={path} onChange={e => setPath(e.target.value)}
          placeholder="Paste the FFmpeg folder or path to ffmpeg.exe" />
        <Button size="compact" variant="secondary" disabled={!!action} onClick={() => perform("browse", async () => {
          const result = await post<{path: string | null}>(BASE + "/browse");
          if (result.path) setPath(result.path);
        })}>Browse…</Button>
      </div>
      <div className="dependency-inline">
        <Button variant="primary" disabled={!path.trim() || !!action} onClick={() => perform("locate", async () => {
          await post(BASE + "/locate", {path: path.trim()});
          await refresh(true);
        })}>Use this location</Button>
        <Button variant="secondary" disabled={!!action} onClick={() => perform("search", async () => {
          const result = await post<{matches: FfmpegPair[]}>(BASE + "/search");
          setMatches(result.matches);
          if (!result.matches.length) setMessage("No existing FFmpeg found in common app locations. Choose a folder below to install.");
        })}>{action === "search" ? "Searching…" : "Search computer"}</Button>
      </div>
      {matches.length > 0 && <div className="dependency-matches">{matches.map(m => <button key={m.directory}
        onClick={() => perform("locate", async () => { await post(BASE + "/locate", {path: m.directory}); await refresh(true); })}>
        Use {m.directory}</button>)}</div>}
    </details>

    <details className="dependency-choice">
      <summary>Install FFmpeg</summary>
      <p>Installs the Windows essentials build to a folder you choose. Download requires your confirmation, and the archive is checked against its publisher's SHA-256.</p>
      <div className="dependency-inline">
        <input aria-label="FFmpeg installation folder" value={installPath} onChange={e => setInstallPath(e.target.value)}
          placeholder="Choose an empty folder to install FFmpeg" />
        <Button variant="secondary" size="compact" disabled={!!action} onClick={() => perform("choose", async () => {
          const result = await post<{path:string | null}>(BASE + "/browse");
          if (result.path) setInstallPath(result.path);
        })}>Choose folder…</Button>
      </div>
      <Button variant="primary" disabled={!installPath.trim() || !!action || !!installJob && ["queued","running"].includes(installJob.status)}
        onClick={() => perform("install", async () => {
          const result = await post<InstallStatus>(BASE + "/install", {path: installPath.trim()});
          setInstallJob(result);
        })}>Download and install here</Button>
      {installJob && <div className="ffmpeg-install-progress" role="status">
        <p>{installJob.message}</p>
        {installJob.status === "running" && (installJob.progress_percent == null
          ? <div className="ffmpeg-progress-track indeterminate" aria-label="Installing FFmpeg"><span /></div>
          : <progress aria-label="FFmpeg download progress" max={100} value={installJob.progress_percent} />)}
      </div>}
    </details>
    {message && <p role="status">{message}</p>}
    {error && <div className="error-message" role="alert">{error}</div>}
    </div>
  </Dialog>;
}
