import { useEffect, useState } from "react";
import { Button, Dialog, Status } from "@tws-ui/core/react";

type Catalog = {
  targets: {id: string; name: string; free: boolean; download_url: string}[];
  selected: string;
  installed: Record<string, string | null>;
};
type DawResponse = {detail?: string; directory?: string; executable?: string | null; path?: string | null;
  status?: string; message?: string; id?: string; scanned?: number};
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
  const [searchJob, setSearchJob] = useState<{id:string;target:string;status:string;message:string;scanned:number}|null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const installed = catalog?.installed[target] || null;
  const targetName = catalog?.targets.find(item => item.id === target)?.name || target;

  async function refresh() {
    const response = await fetch(API + "/daws");
    if (!response.ok) throw new Error("DAW integration API unavailable. Relaunch the updated Song Harbor backend.");
    const data = await response.json() as Catalog;
    setCatalog(data);
    setTarget(data.selected || "waveform");
    setLocation(data.installed[data.selected] || "");
  }

  useEffect(() => { void refresh().catch(e => setError(String(e))); }, []);
  useEffect(() => {
    if (!searchJob || searchJob.status !== "running") return;
    let active = true;
    const poll = async () => {
      try {
        const response = await fetch(API + "/daws/search/" + searchJob.id);
        if (!response.ok) throw new Error("Search status is unavailable");
        const data = await response.json() as {id:string;target:string;status:string;message:string;scanned:number;executable?:string};
        if (!active) return;
        setSearchJob(data);
        if (data.status === "found") {
          setMessage(data.message);
          await refresh();
        } else if (data.status === "not_found" || data.status === "error") {
          setMessage(data.message);
        }
      } catch (e) {
        if (active) {setSearchJob(null);setError(e instanceof Error ? e.message : String(e));}
      }
    };
    const timer = setInterval(() => {void poll();}, 900);
    return () => {active = false;clearInterval(timer);};
  }, [searchJob?.id, searchJob?.status]);

  async function searchComputer() {
    setError("");setMessage("");
    const result = await post("/daws/" + target + "/search");
    if (!result.id) throw new Error("DAW search could not start");
    setSearchJob({id:result.id,target,status:result.status || "running",
      scanned:result.scanned || 0,message:result.message || "Searching…"});
  }



  async function chooseTarget(value: string) {
    setTarget(value);
    setLocation(catalog?.installed[value] || "");
    setFolder("");
    setInstaller("");
    setSearchJob(null);
    setError("");
    setMessage("");
    await perform(async () => {
      await post("/daws/select", {target: value});
    });
  }

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
    setMessage("Aligned tracks exported to local folder.");
  }

  async function detect() {
    const result = await post("/daws/" + target + "/detect");
    await refresh();
    if (!result.executable) setMessage(targetName + " not found yet. Browse or install below.");
    else setMessage(targetName + " found and configured.");
  }

  async function browseInstalled() {
    const result = await post("/daws/" + target + "/browse");
    if (result.path) setLocation(result.path);
  }

  async function locate() {
    const result = await post("/daws/" + target + "/locate", {path: location});
    if (!result.executable) throw new Error(targetName + " not found at that location");
    await refresh();
    setMessage(targetName + " location saved.");
  }

  async function runInstaller() {
    if (!installer) throw new Error("Choose the downloaded publisher installer first");
    const result = await post("/daws/waveform/run-installer", {path: installer});
    setMessage(result.message || "Installer launched. Detect Waveform when installation completes.");
  }

  async function launch() {
    if (!folder) throw new Error("Prepare stems before launching.");
    const result = await post("/projects/" + jobId + "/daw/launch", {target, directory: folder});
    if (result.status === "setup_required") {
      await refresh();
      setMessage(targetName + " needs configuration. Find it or install below.");
      return;
    }
    setMessage(result.message || (targetName + " opened."));
  }

  return <Dialog open onOpenChange={next => { if (!next && !busy) onClose(); }}
    title="Download tracks" description="Export aligned track files to a local folder; optional DAW launch is separate.">
    <div className="daw-setup">
      <div className="daw-controls">
        <select aria-label="DAW target" value={target} onChange={e => { void chooseTarget(e.target.value); }}
          disabled={busy || !catalog}>
          {(catalog?.targets || [{id:"waveform",name:"Waveform Free"}]).map(item =>
            <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        {installed ? <Status tone="success">Ready</Status> : <Status tone="neutral">Not configured</Status>}
      </div>
      <div className="daw-controls">
        <Button variant="primary" disabled={busy} onClick={() => { void perform(folder ? launch : prepare); }}>
          {busy ? "Working…" : folder ? "Launch DAW" : "Export tracks"}
        </Button>
        {folder && <>
          <Button variant="secondary" disabled={busy} onClick={() => {
            void perform(async () => {
              const result = await post("/projects/" + jobId + "/daw/open-folder");
              if (result.status !== "opened") throw new Error(result.message || "Could not open export folder");
            });
          }}>Open folder</Button>
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
              placeholder={target === "audacity" ? "Audacity.exe or installation folder" : target === "morningdaw" ? "MorningDAW.exe or installation folder" : "Waveform.exe or installation folder"} aria-label={"Installed " + targetName + " path"}/>
            <Button size="compact" variant="secondary" disabled={busy} onClick={() => { void perform(browseInstalled); }}>Browse</Button>
            <Button size="compact" variant="secondary" disabled={busy || !location.trim()} onClick={() => { void perform(locate); }}>Use</Button>
          </div>
          <div className="daw-controls">
            <Button variant="secondary" disabled={busy || searchJob?.status === "running"}
              onClick={() => {void perform(searchComputer);}}>
              {searchJob?.status === "running" ? "Searching…" : "Search this PC"}
            </Button>
            {searchJob && <span role="status" className="daw-scan-status">
              {searchJob.message}
            </span>}
          </div>
        </div>
        <div className="daw-section">
          <strong>Install {targetName}</strong>
          <p>{target === "audacity" ? "Use the official Audacity installer, then Detect. Your song stays here." : target === "morningdaw" ? "Install MorningDAW from its publisher, then Detect. Stem import is manual." : "Tracktion handles account and license steps. Song Harbor can run a verified installer."}</p>
          <div className="daw-controls">
            <Button variant="secondary" disabled={busy} onClick={() => {
              const address = catalog?.targets.find(item => item.id === target)?.download_url;
              if (address) window.open(address, "_blank", "noopener,noreferrer");
            }}>Download</Button>
            {target === "waveform" && <>
              <Button variant="subtle" disabled={busy} onClick={() => { void perform(async () => {
                const result = await post("/daws/waveform/browse-installer");
                if (result.path) setInstaller(result.path);
              }); }}>Find installer</Button>
              {installer && <Button variant="primary" disabled={busy} onClick={() => { void perform(runInstaller); }}>
                Run installer
              </Button>}
            </>}
            <Button variant="secondary" disabled={busy} onClick={() => { void perform(detect); }}>Detect again</Button>
          </div>
          {installer && <p className="daw-path">{installer}</p>}
        </div>
      </>}
      {message && <p role="status" className="song-save-notice">{message}</p>}
      {error && <p role="alert" className="error-message">{error}</p>}
    </div>
  </Dialog>;
}
