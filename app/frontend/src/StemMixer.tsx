import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Status } from "@tws-ui/core/react";

type Stem = { filename: string; name: string; gain: number; mute: boolean; solo: boolean };
type MixResponse = { url: string; filename: string };
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

export function StemMixer({ jobId, files, expectedDuration, onMissingFfmpeg }: {
  jobId: string; files: string[]; expectedDuration?: number;
  onMissingFfmpeg?: (retry: () => void) => void;
}) {
  const [stems, setStems] = useState<Stem[]>(() => files.map(filename => ({
    filename, name: labelOf(filename), gain: 100, mute: false, solo: false,
  })).sort((a, b) => names.indexOf(a.name) - names.indexOf(b.name)));
  const [playing, setPlaying] = useState(false);
  const [position, setPosition] = useState(0);
  const [duration, setDuration] = useState(expectedDuration || 0);
  const [exporting, setExporting] = useState(false);
  const [mixUrl, setMixUrl] = useState<string | null>(null);
  const [error, setError] = useState("");
  const audio = useRef<Map<string, HTMLAudioElement>>(new Map());
  const playRef = useRef(false);
  const seekRef = useRef(0);
  const stemsRef = useRef(stems);
  stemsRef.current = stems;
  const anySolo = stems.some(s => s.solo);

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
      if (player) player.volume = Math.min(1, Math.max(0, effectiveGain(s, anySolo)));
    }
    // Any level adjustment makes the previously exported file stale.
    setMixUrl(null);
  }, [stems, anySolo]);

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
    <div className="mixer-heading">
      <div><h3>Stem mixer</h3><p>Audition the arrangement before exporting a new mix.</p></div>
      <Button variant="subtle" size="compact" onClick={() => {
        setStems(current => current.map(s => ({ ...s, gain: 100, mute: false, solo: false })));
      }}>Reset mix</Button>
    </div>
    <div className="transport">
      <Button variant="primary" onClick={togglePlayback}>{playing ? "Pause" : "Play"}</Button>
      <span className="timecode">{timecode(position)}</span>
      <input type="range" aria-label="Playback position" min={0} max={Math.max(duration, 1)}
        step={0.05} value={Math.min(position, duration || 1)} onChange={e => seek(Number(e.target.value))} />
      <span className="timecode">{timecode(duration)}</span>
    </div>
    <div className="mixer-tracks">
      {stems.map(s => <div className="mixer-track" key={s.filename}>
        <strong>{s.name}</strong>
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
    <div className="mix-footer">
      <div className="mix-actions">
        <Button variant="primary" disabled={exporting} onClick={exportMix}>
          {exporting ? "Rendering WAV…" : "Export mix WAV"}
        </Button>
        {mixUrl && <a className="mix-download" href={mixUrl} download="Song Harbor Mix.wav">Download mix</a>}
      </div>
      {exporting ? <Status tone="info">Export in progress</Status> : mixUrl ? <Status tone="success">Mix ready</Status> : null}
    </div>
    {error && <p role="alert" className="error-message">{error}</p>}
    <p className="mixer-note">Preview uses browser audio streams with periodic synchronization. WAV export is rendered sample-aligned by FFmpeg and preserves the original stems.</p>
  </section>;
}
