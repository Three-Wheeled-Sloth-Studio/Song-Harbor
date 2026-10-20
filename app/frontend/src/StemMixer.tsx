import { useCallback, useEffect, useRef, useState } from "react";
import { Button, IconButton, Status } from "@tws-ui/core/react";
import { DawHandoff } from "./DawHandoff";
import { AudioIcon } from "./AudioIcons";
import { SectionEditor } from "./SectionEditor";
import { ChannelSplitter } from "./ChannelSplitter";
import { StemWaveforms } from "./StemWaveforms";
import type { SongSection } from "./SectionEditor";

type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
type MixResponse = { url: string; filename: string };
type ChildSet = {active:boolean;export:string;tracks:{left:{url:string;file:string};right:{url:string;file:string}}};
type ChannelSets = Record<string,ChildSet>;
export type SavedStem = {filename: string; gain: number; mute: boolean; solo: boolean};
const names = ["Vocals", "Drums", "Bass", "Guitar", "Piano", "Other"];



function labelOf(filename: string) {
  return names.find(label => filename.includes("(" + label + ")")) || filename;
}
function timecode(seconds: number) {
  const s = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}
function effectiveGain(stem: Stem, anySolo: boolean) {
  return stem.mute || (anySolo && !stem.solo) ? 0 : stem.gain / 100;
}

export function StemMixer({ jobId, files, expectedDuration, onMissingFfmpeg, savedStems, initialSections, initialTitle, onSaved }: {
  jobId: string; files: string[]; expectedDuration?: number;
  onMissingFfmpeg?: (retry: () => void) => void;
  savedStems?: SavedStem[];
  initialSections?: SongSection[];
  initialTitle?: string;
  onSaved?: () => void;
}) {
  const [stems, setStems] = useState<Stem[]>(() => files.map(filename => {
    const saved = savedStems?.find(stem => stem.filename === filename);
    return {
      filename, name: labelOf(filename),
      gain: saved ? Math.round(saved.gain * 100) : 100,
      mute: saved?.mute ?? false, solo: saved?.solo ?? false,
    };
  }).sort((a, b) => names.indexOf(a.name) - names.indexOf(b.name)));
  const [title, setTitle] = useState(initialTitle || "Untitled song");
  const [saving, setSaving] = useState(false);
  const [handoffBusy, setHandoffBusy] = useState(false);
  const [dawOpen, setDawOpen] = useState(false);
  const [handoffFolder, setHandoffFolder] = useState("");
  const [notice, setNotice] = useState("");
  const [playing, setPlaying] = useState(false);
  const [monitorVolume, setMonitorVolume] = useState(75);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(expectedDuration || 0);
  const [exporting, setExporting] = useState(false);
  const [mixUrl, setMixUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [channels,setChannels]=useState<ChannelSets>({});
  const [routingVersion,setRoutingVersion]=useState(0);
  const [channelBusy,setChannelBusy]=useState(false);
  const [loopEnabled,setLoopEnabled]=useState(false);
  const [loopIn,setLoopIn]=useState<number|null>(null);
  const [loopOut,setLoopOut]=useState<number|null>(null);
  const context=useRef<AudioContext|null>(null);
  const audio = useRef<Map<string, HTMLAudioElement>>(new Map());
  const playRef = useRef(false);
  const seekRef = useRef(0);
  const stemsRef = useRef(stems);
  stemsRef.current = stems;
  const anySolo = stems.some(s => s.solo);

  const refreshChannels=useCallback(async()=>{
    const r=await fetch("/api/projects/"+jobId+"/channels");
    if(r.ok){const data=await r.json() as {channels:ChannelSets};setChannels(data.channels||{});setRoutingVersion(v=>v+1);}
  },[jobId]);
  useEffect(()=>{void refreshChannels();},[refreshChannels]);
  async function toggleChannel(filename:string){
    const entry=channels[filename];
    if(!entry||channelBusy)return;
    stop();setChannelBusy(true);setError("");
    try{
      const r=await fetch("/api/projects/"+jobId+"/channels",{method:"PUT",
        headers:{"Content-Type":"application/json"},body:JSON.stringify({filename,active:!entry.active})});
      const data=await r.json() as {channels?:ChannelSets;detail?:string};
      if(!r.ok||!data.channels)throw Error(data.detail||"Routing update failed");
      setChannels(data.channels);setRoutingVersion(v=>v+1);setMixUrl(null);
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setChannelBusy(false);}
  }
  const stop = useCallback(() => {
    playRef.current = false;
    setPlaying(false);
    audio.current.forEach(element => element.pause());
  }, []);

  useEffect(() => {
    const players = new Map<string, HTMLAudioElement>();
    for (const name of files) {
      const element = new Audio("/api/jobs/" + jobId + "/stream/" + encodeURIComponent(name));
      element.preload = "metadata";
      element.addEventListener("loadedmetadata", () => {
        if (Number.isFinite(element.duration)) setDuration(current => Math.max(current, element.duration));
      });
      element.addEventListener("error", () => {
        setError("One of the audio streams could not be loaded. Check the backend and try again.");
        stop();
      });
      players.set(name, element);
    }
    audio.current = players;
    setDuration(expectedDuration || 0);
    setPosition(0);
    setPlaying(false);
    playRef.current = false;
    setMixUrl(null);
    setError("");
    return () => { players.forEach(element => { element.pause(); element.removeAttribute("src"); element.load(); }); players.clear(); };
  }, [files, jobId, expectedDuration, stop]);

  useEffect(() => {
    for (const s of stems) {
      const player = audio.current.get(s.filename);
      if (player) player.volume = Math.min(1, Math.max(0, effectiveGain(s, anySolo) * monitorVolume / 100));
    }
  }, [stems, anySolo, monitorVolume]);

  // Monitoring volume never changes the rendered mix; only stem edits invalidate it.
  useEffect(() => { setMixUrl(null); }, [stems]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      const players = [...audio.current.values()];
      const master = players[0];
      if (!master) return;
      const current = master.currentTime;
      setPosition(current);
      if (master.ended || (duration > 0 && current >= duration - 0.03)) {
        stop();
        return;
      }
      // HTML media streams may drift; correct the followers while keeping memory bounded.
      for (const follower of players.slice(1)) {
        if (follower.readyState >= 1 && Math.abs(follower.currentTime - current) > 0.09) {
          try { follower.currentTime = current; } catch { /* decoder still loading */ }
        }
      }
    }, 120);
    return () => window.clearInterval(timer);
  }, [playing, duration, stop]);

  async function togglePlayback() {
    if (playRef.current) {
      stop();
      return;
    }
    setError("");
    const players = [...audio.current.values()];
    if (players.length !== 6) { setError("Six stems are required for audition."); return; }
    const time = position >= duration - 0.05 && duration > 0 ? 0 : position;
    players.forEach(player => {
      player.pause();
      player.currentTime = time;
    });
    seekRef.current = time;
    try {
      await Promise.all(players.map(player => player.play()));
      playRef.current = true;
      setPlaying(true);
    } catch {
      stop();
      setError("Playback failed. Try pressing Play again after the stems finish loading.");
    }
  }

  function seek(next: number) {
    setPosition(next);
    seekRef.current = next;
    audio.current.forEach(player => {
      try { player.currentTime = next; } catch { /* player metadata not yet ready */ }
    });
  }

  function update(filename: string, changes: Partial<Stem>) {
    setStems(current => current.map(s => s.filename === filename ? { ...s, ...changes } : s));
  }

  async function saveProject(): Promise<boolean> {
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await fetch("/api/projects/" + jobId, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), stems: stemsRef.current.map(s => ({
          filename: s.filename, gain: s.gain / 100, mute: s.mute, solo: s.solo,
        })) }),
      });
      if (!result.ok) {
        const detail = await result.json().catch(() => ({})) as {detail?: string};
        throw new Error(detail.detail || "Could not save song project");
      }
      setNotice("Song project saved.");
      onSaved?.();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save song project");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handoffWaveform() {
    setHandoffBusy(true); setError(""); setNotice("");
    try {
      if (!(await saveProject())) return;
      const response = await fetch("/api/projects/" + jobId + "/waveform", {method: "POST"});
      const result = await response.json() as {directory?: string;detail?: string};
      if (!response.ok || !result.directory) throw new Error(result.detail || "Waveform export failed");
      setHandoffFolder(result.directory);
      setNotice("Waveform folder ready. Import the six WAVs on separate tracks at 0:00.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Waveform export failed");
    } finally {
      setHandoffBusy(false);
    }
  }

  async function openWaveformFolder() {
    try {
      const response = await fetch("/api/projects/" + jobId + "/waveform/open", {method: "POST"});
      if (!response.ok) throw new Error("Could not open Waveform folder");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open folder");
    }
  }

  async function exportMix() {
    stop();
    setExporting(true);
    setMixUrl(null);
    setError("");
    try {
      const response = await fetch("/api/jobs/" + jobId + "/mix", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stems: stemsRef.current.map(s => ({
          filename: s.filename, gain: s.gain / 100, mute: s.mute, solo: s.solo,
        })) }),
      });
      const data = await response.json() as MixResponse & { detail?: string };
      if (!response.ok) {
        if (response.status === 409 && /ffmpeg/i.test(data.detail || "") && onMissingFfmpeg) {
          onMissingFfmpeg(() => { void exportMix(); });
          return;
        }
        throw new Error(data.detail || "Mix export failed");
      }
      setMixUrl(data.url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Mix export failed");
    } finally {
      setExporting(false);
    }
  }

  return <section className="mixer" aria-label="Stem mixer">
    <div className="song-project-controls">
      <label htmlFor="song-project-name">Song project</label>
      <input id="song-project-name" value={title} maxLength={120} onChange={e => setTitle(e.target.value)} />
      <IconButton icon="▣" label="Save song" disabled={saving || !title.trim()} onClick={() => { void saveProject(); }}/>
    </div>
    <div className="mixer-heading">
      <div><h3>Stem mixer</h3></div>
      <IconButton icon="↶" label="Reset mix" onClick={() => {
        setStems(current => current.map(s => ({ ...s, gain: 100, mute: false, solo: false })));
      }}/>
    </div>
    <div className="transport">
      <IconButton icon={playing ? "⏸" : "▶"} label={playing ? "Pause" : "Play"} onClick={togglePlayback}/>
      <span className="timecode">{timecode(position)}</span>
      <input type="range" aria-label="Playback position" min={0} max={Math.max(duration, 1)}
        step={0.05} value={Math.min(position, duration || 1)} onChange={e => seek(Number(e.target.value))} />
      <span className="timecode">{timecode(duration)}</span>
      <label className="master-monitor" title="Monitoring volume; does not change your exported mix">
        <span aria-hidden="true">🔊</span>
        <input type="range" min="0" max="100" step="1" value={monitorVolume}
          aria-label="Playback monitoring volume" onChange={e => setMonitorVolume(Number(e.target.value))} />
      </label>
    </div>
    <StemWaveforms jobId={jobId} files={stems.map(s => ({filename:s.filename,label:s.name}))} duration={duration} position={position} onSeek={seek}/>
    <div className="mixer-tracks">
      {stems.map(s => <div className="mixer-track" key={s.filename}>
        <strong className="stem-icon-name" title={s.name} aria-label={s.name}><AudioIcon kind={s.name} size={32}/><span className="sr-only">{s.name}</span></strong>
        <div className="track-actions">
          <button type="button" className={"track-toggle" + (s.mute ? " is-muted" : "")}
            aria-pressed={s.mute} title={"Mute " + s.name} onClick={() => update(s.filename, { mute: !s.mute })}>M</button>
          <button type="button" className={"track-toggle" + (s.solo ? " is-solo" : "")}
            aria-pressed={s.solo} title={"Solo " + s.name} onClick={() => update(s.filename, { solo: !s.solo })}>S</button>
        </div>
        <input type="range" min="0" max="100" step="1" value={s.gain}
          aria-label={s.name + " volume"} onChange={e => update(s.filename, {gain: Number(e.target.value)})} />
        <span className="track-percent">{s.gain}%</span>
      </div>)}
    </div>
    <SectionEditor jobId={jobId} duration={duration} position={position} initialSections={initialSections} onSeek={seek}/>
    <div className="mix-footer">
      <div className="mix-actions">
        <IconButton icon="⇩" label={exporting ? "Rendering mix WAV" : "Export mix WAV"}
          disabled={exporting} onClick={exportMix}/>
        {mixUrl && <a className="mix-download" href={mixUrl} download="Song Harbor Mix.wav" title="Download mix WAV">⇩ WAV</a>}
      </div>
      {exporting ? <Status tone="info">Export in progress</Status> : mixUrl ? <Status tone="success">Mix ready</Status> : null}
    </div>
    <ChannelSplitter jobId={jobId} files={files} onMissingFfmpeg={onMissingFfmpeg} />
    <div className="daw-handoff">
      <IconButton icon="🎚" label="Export to DAW" onClick={() => setDawOpen(true)}/>
    </div>
    {dawOpen && <DawHandoff jobId={jobId} saveProject={saveProject} onClose={() => setDawOpen(false)} />}
    {notice && <p role="status" className="song-save-notice">{notice}</p>}
    {error && <p role="alert" className="error-message">{error}</p>}

  </section>;
}
