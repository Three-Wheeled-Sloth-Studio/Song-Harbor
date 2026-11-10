"""Isolated, single-job Deshimmer stem candidate runner.

Sources are validated by the server; outputs never replace source media.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import threading
import uuid
import wave
from pathlib import Path
from deshimmer_adapter import resolve_python, DeshimmerUnavailable

WORKER = "\"\"\"Runs within the separately configured Deshimmer Python interpreter.\n\nContract: python -c WORKER input.wav output.wav metadata.json\nNo network, UI, project writes or external file choices.\n\"\"\"\nfrom dataclasses import asdict\nimport json\nimport os\nimport sys\nimport numpy as np\nimport soundfile as sf\nfrom deshimmer.autotune import analyze, refine, pick_regions\nfrom deshimmer.api import process_audio\nfrom deshimmer.core import MasterParams\n\nsource, destination, metadata = sys.argv[1:4]\naudio, rate = sf.read(source, dtype=\"float32\", always_2d=True)\nif rate < 8000 or rate > 192000 or audio.shape[0] < rate or audio.shape[1] not in (1, 2):\n    raise ValueError(\"Unsupported Deshimmer source format\")\nif not np.isfinite(audio).all():\n    raise ValueError(\"Input contains nonfinite samples\")\nprint(\"STAGE:analyzing\", flush=True)\nregions = pick_regions(audio, rate, n=4, dur=min(4.0, max(1.0, audio.shape[0] / rate / 4.0)))\nparams, _master, report = analyze(audio, rate, regions=regions)\nprint(\"STAGE:optimizing\", flush=True)\nparams, optimization = refine(\n    audio, rate, base_params=params, regions=regions,\n    aggressiveness=0.35, n_trials_per_stage=4, refine_dur=2.0,\n    debug_dir=os.path.dirname(metadata), transition_aware=True,\n)\nprint(\"STAGE:rendering\", flush=True)\ncleaned, info = process_audio(audio, rate, params=params,\n    master_params=MasterParams(enabled=False), include_residuals=False)\ncleaned = np.asarray(cleaned)\nif cleaned.ndim == 1:\n    cleaned = cleaned[:, None]\nif cleaned.shape != audio.shape or not np.isfinite(cleaned).all():\n    raise ValueError(\"Deshimmer returned invalid audio dimensions or samples\")\npeak = float(np.max(np.abs(cleaned)))\nif peak > 1.0:\n    raise ValueError(\"Deshimmer candidate exceeds 0 dBFS; no automatic clipping or limiter applied\")\nsf.write(destination, cleaned, rate, subtype=\"PCM_24\")\nwith open(metadata, \"w\", encoding=\"utf-8\") as handle:\n    json.dump({\"sample_rate\":rate,\"frames\":len(audio),\"channels\":audio.shape[1],\n               \"peak\":peak,\"params\":asdict(params),\n               \"optimizer\":{\"aggressiveness\":0.35,\"trials_per_stage\":4}},handle, indent=2)\nprint(\"STAGE:complete\", flush=True)\n"
_state_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_active: str | None = None
STATES = {"queued", "analyzing", "optimizing", "rendering", "ready", "failed", "cancelled"}

def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _public(job: dict) -> dict:
    return {key: job[key] for key in ("id", "status", "message", "source_hash", "filename")}

def start(root: Path, song_id: str, filename: str) -> dict:
    global _active
    if not re.fullmatch(r"[a-f0-9]{12}", song_id):
        raise ValueError("Invalid song identifier")
    if Path(filename).name != filename or not filename.lower().endswith(".wav"):
        raise ValueError("Invalid working stem filename")
    python = resolve_python()
    source = root / "jobs" / song_id / "stems" / filename
    if not source.is_file():
        raise ValueError("Stem audio unavailable")
    source_hash = _sha(source)
    with _state_lock:
        if _active is not None:
            raise RuntimeError("A Deshimmer cleanup is already running")
        job_id = uuid.uuid4().hex
        folder = root / "jobs" / song_id / "cleanup_candidates" / job_id
        folder.mkdir(parents=True, exist_ok=False)
        job = {"id":job_id, "status":"queued", "message":"Preparing stem",
               "song_id":song_id, "filename":filename, "source_hash":source_hash,
               "python":python, "source":source, "folder":folder, "process":None}
        _jobs[job_id] = job
        _active = job_id
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return _public(job)

def _run(job: dict) -> None:
    global _active
    try:
        with _state_lock:
            if job["status"] == "cancelled":
                return
        output = job["folder"] / "candidate.wav"
        metadata = job["folder"] / "recipe.json"
        # Shell-free invocation; the external environment imports its own package.
        process = subprocess.Popen([job["python"], "-c", WORKER,
                   str(job["source"]), str(output), str(metadata)],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                   text=True, bufsize=1, shell=False,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        with _state_lock:
            job["process"] = process
            cancelled = job["status"] == "cancelled"
        if cancelled:
            process.kill()
        assert process.stdout is not None
        for raw in process.stdout:
            line = raw.strip()
            with _state_lock:
                if line.startswith("STAGE:"):
                    stage = line[6:]
                    if stage in STATES and stage != "complete":
                        job["status"] = stage
                        job["message"] = stage.capitalize() + " stem"
                elif line:
                    job["message"] = line[-240:]
        result = process.wait()
        with _state_lock:
            was_cancelled = job["status"] == "cancelled"
        if was_cancelled:
            return
        if result != 0:
            raise RuntimeError("Deshimmer process failed: " + job["message"])
        if not output.is_file() or not metadata.is_file():
            raise RuntimeError("Deshimmer did not write a candidate and recipe")
        with wave.open(str(output), "rb") as wav:
            candidate_format = (wav.getframerate(), wav.getnchannels(), wav.getnframes())
            if wav.getsampwidth() != 3 or wav.getnframes() < 1 or wav.getnchannels() not in (1,2):
                raise RuntimeError("Candidate is not valid 24-bit PCM")
        with wave.open(str(job["source"]), "rb") as wav:
            original_format = (wav.getframerate(), wav.getnchannels(), wav.getnframes())
        if candidate_format != original_format:
            raise RuntimeError("Candidate sample rate, channel layout or length differs from source")
        if _sha(job["source"]) != job["source_hash"]:
            raise RuntimeError("Original stem changed during processing; candidate rejected")
        with _state_lock:
            job["status"] = "ready"
            job["message"] = "Candidate ready for A/B comparison"
    except Exception as exc:
        with _state_lock:
            if job["status"] != "cancelled":
                job["status"] = "failed"
                job["message"] = str(exc)[-400:]
    finally:
        with _state_lock:
            job["process"] = None
            if _active == job["id"]:
                _active = None

def status(song_id: str, candidate_id: str) -> dict:
    with _state_lock:
        job = _jobs.get(candidate_id)
        if not job or job["song_id"] != song_id:
            raise KeyError("Cleanup candidate not found")
        return _public(job)

def candidate(song_id: str, candidate_id: str) -> Path:
    with _state_lock:
        job = _jobs.get(candidate_id)
        if not job or job["song_id"] != song_id or job["status"] != "ready":
            raise KeyError("Candidate is not ready")
        if _sha(job["source"]) != job["source_hash"]:
            raise ValueError("Original stem changed; reprocess before using candidate")
        return job["folder"] / "candidate.wav"

def cancel(song_id: str, candidate_id: str) -> dict:
    with _state_lock:
        job = _jobs.get(candidate_id)
        if not job or job["song_id"] != song_id:
            raise KeyError("Cleanup candidate not found")
        if job["status"] in ("ready", "failed", "cancelled"):
            return _public(job)
        job["status"] = "cancelled"
        job["message"] = "Cancelled by user"
        process = job["process"]
    if process is not None and process.poll() is None:
        process.kill()
    return status(song_id, candidate_id)
