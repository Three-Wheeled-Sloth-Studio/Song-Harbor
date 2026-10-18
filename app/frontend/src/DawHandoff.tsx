import { useEffect, useState } from "react";
import { Button, Dialog, Status } from "@tws-ui/core/react";

type Catalog = {
  targets: {id: string; name: string; free: boolean; download_url: string}[];
  selected: string;
  installed: {waveform: string | null};
};
type DawResponse = {detail?: string; directory?: string; executable?: string | null; path?: string | null;
  status?: string; message?: string};
const API = "/api";

async function post(url: string, body?: object): Promise<DawResponse> {
  const response = await fetch(API + url, {
    method: "POST", headers: body ? {"Content-Type": "application/json"} : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const result = await response.json().catch(() => ({})) as DawResponse;
  if (!response.ok) throw new Error(result.detail || "Operation could not complete");
  return result;
}

export function DawHandoff({jobId, saveProject, onClose}: {
  jobId: string;
  saveProject: () => Promise<boolean>;
  onClose: () => void;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [target, setTarget] = useState("waveform");
  const [location, setLocation] = useState("");
  const [installer, setInstaller] = useState("");
  const [folder, setFolder] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const installed = catalog?.installed.waveform || null;

  async function refresh() {
    const response = await fetch(API + "/daws");
    if (!response.ok) throw new Error("DAW integration API unavailable. Relaunch the updated Song Harbor backend.");
    const data = await response.json() as Catalog;
    setCatalog(data);
    setTarget(data.selected || "waveform");
    setLocation(data.installed.waveform || "");
  }

  useEffect(() => { void refresh().catch(e => setError(String(e))); }, []);

  async function perform(task: () => Promise<void>) {
    setBusy(true); setError(""); setMessage("");
    try { await task(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  async function prepare() {
    if (!await saveProject()) throw new Error("Save this song before exporting.");
    const result = await post("/projects/" + jobId + "/daw/export", {target});
    if (!result.directory) throw new Error("DAW export didn't return a folder");
    setFolder(result.directory);
    setMessage("Six aligned stems prepared.");
  }

  async function detect() {
    const result = await post("/daws/waveform/detect");
    await refresh();
    if (!result.executable) setMessage("Waveform not found in common installation locations. Browse or install below.");
    else setMessage("Waveform found and configured.");
  }

  async function browseInstalled() {
    const result = await post("/daws/waveform/browse");
    if (result.path) setLocation(result.path);
  }

  async function locate() {
    const result = await post("/daws/waveform/locate", {path: location});
    if (!result.executable) throw new Error("Waveform executable not found at that location");
    await refresh();
    setMessage("Waveform location saved.");
  }

  async function runInstaller() {
    if (!installer) throw new Error("Choose the downloaded publisher installer first");
    const result = await post("/daws/waveform/run-installer", {path: installer});
    setMessage(result.message || "Installer launched. Detect Waveform when installation completes.");
  }

  async function launch() {
    const result = await post("/daws/waveform/launch");
    if (result.status === "setup_required") {
      await refresh();
      setMessage("Waveform needs configuration. Find it or use the installation options below.");
      return;
    }
    setMessage("Waveform opened. Import the six stems as separate tracks at 0:00.");
  }

  return <Dialog open onOpenChange={next => { if (!next && !busy) onClose(); }}
    title="DAW handoff" description="Target, files, launch.">
    <div className="daw-setup">
      <div className="daw-controls">
        <select aria-label="DAW target" value={target} onChange={e => setTarget(e.target.value)}
          disabled={busy || !catalog}>
          {(catalog?.targets || [{id:"waveform",name:"Waveform Free"}]).map(item =>
            <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {installed ? <Status tone="success">Ready</Status> : <Status tone="neutral">Not configured</Status>}
      </div>
      <div className="daw-controls">
        <Button variant="primary" disabled={busy} onClick={() => { void perform(folder ? launch : prepare); }}>
          {busy ? "Working…" : folder ? "Launch" : "Prepare stems"}
        </Button>
        {folder && <>
          <Button variant="secondary" disabled={busy} onClick={() => {
            void perform(async () => {
              const result = await post("/projects/" + jobId + "/daw/open-folder");
              if (result.status !== "opened") throw new Error(result.message || "Could not open export folder");
            });
          }}>Files</Button>
          <Button variant="subtle" disabled={busy} onClick={() => { void perform(prepare); }}>Reprepare</Button>
        </>}
      </div>
      {folder && <p className="daw-path" title={folder}>{folder}</p>}
      {!installed && <>
        <div className="daw-section">
          <div className="daw-section-heading"><strong>Locate DAW</strong>
            <Button variant="subtle" size="compact" disabled={busy} onClick={() => { void perform(detect); }}>Detect</Button>
          </div>
          <div className="daw-controls">
            <input value={location} onChange={e => setLocation(e.target.value)}
              placeholder="Waveform.exe or installation folder" aria-label="Installed Waveform path"/>
            <Button size="compact" variant="secondary" disabled={busy} onClick={() => { void perform(browseInstalled); }}>Browse</Button>
            <Button size="compact" variant="secondary" disabled={busy || !location.trim()} onClick={() => { void perform(locate); }}>Use</Button>
          </div>
        </div>
        <div className="daw-section">
          <strong>Install Waveform Free</strong>
          <p>Waveform's publisher handles its account and license steps. Song Harbor can launch the downloaded, signed installer, then detect the result.</p>
          <div className="daw-controls">
            <Button variant="secondary" disabled={busy} onClick={() => {
              window.open(catalog?.targets.find(item => item.id === target)?.download_url ||
                "https://www.tracktion.com/products/waveform-free", "_blank", "noopener,noreferrer");
            }}>Download</Button>
            <Button variant="subtle" disabled={busy} onClick={() => { void perform(async () => {
              const result = await post("/daws/waveform/browse-installer");
              if (result.path) setInstaller(result.path);
            }); }}>Find installer</Button>
            {installer && <Button variant="primary" disabled={busy} onClick={() => { void perform(runInstaller); }}>
              Run installer
            </Button>}
          </div>
          {installer && <p className="daw-path">{installer}</p>}
        </div>
      </>}
      {message && <p role="status" className="song-save-notice">{message}</p>}
      {error && <p role="alert" className="error-message">{error}</p>}
    </div>
  </Dialog>;
}
