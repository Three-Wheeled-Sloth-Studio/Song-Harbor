"""Non-destructive, bounded specialist separation previews using installed local models."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import uuid

import projects
import track_lifecycle

MODEL_EXTENSIONS = {".onnx", ".ckpt", ".pth", ".yaml"}
MAX_REGION_SECONDS = 60.0
_LOCK = threading.RLock()
_JOBS: dict[str, dict] = {}


def available_models(model_root: Path) -> list[dict]:
    """Bounded, read-only inventory; presence is not an endorsement or weight license."""
    if not model_root.is_dir():
        return []
    found: list[dict] = []
    for root in [model_root, *(p for p in model_root.iterdir() if p.is_dir() and not p.is_symlink())]:
        for path in root.iterdir():
            if (not path.is_file() or path.is_symlink() or path.suffix.lower() not in MODEL_EXTENSIONS
                    or len(found) >= 120):
                continue
            found.append({"id": path.name, "name": path.name, "installed": True,
                          "family": "Demucs" if path.suffix == ".yaml" else
                                    "MDX/VR or other (verify model)", "path": str(path)})
        if len(found) >= 120:
            break
    return sorted(found, key=lambda item: item["name"].lower())


def _verified_model(root: Path, identifier: str) -> Path:
    matches = [Path(m["path"]) for m in available_models(root) if m["id"] == identifier]
    if len(matches) != 1 or not matches[0].resolve().is_relative_to(root.resolve()):
        raise ValueError("Selected local separation model is missing or ambiguous")
    return matches[0]


def _validated_source(data_root: Path, project: dict, track_id: str) -> tuple[Path, dict]:
    folder = data_root / "jobs" / project["id"]
    tracks = track_lifecycle.ensure_identities(project)
    track = next((t for t in tracks if t["track_id"] == track_id), None)
    if track is None:
        raise ValueError("Selected source track is no longer available")
    sources = projects.validated_stems(project, folder)
    source = next((p for p in sources if p.name == track["working_filename"]), None)
    if source is None:
        raise ValueError("Selected source stem is not a canonical file")
    return source, track


def submit(data_root: Path, project: dict, track_id: str, start: float, duration: float,
           model_id: str, model_root: Path, ffmpeg: str, separator: str) -> dict:
    if (not all(math.isfinite(v) for v in (start, duration)) or start < 0
            or not 0.5 <= duration <= MAX_REGION_SECONDS):
        raise ValueError("Choose a finite 0.5 to 60 second test region")
    source, track = _validated_source(data_root, project, track_id)
    clip_start = float(track.get("start_seconds") or 0)
    clip_duration = float(track.get("duration_seconds") or project.get("source_duration_seconds") or 0)
    if start < clip_start - 0.001 or start + duration > clip_start + clip_duration + 0.001:
        raise ValueError("Test region must be inside the selected source clip")
    if not Path(separator).is_file():
        raise ValueError("Audio separator runtime is not installed")
    model = _verified_model(model_root, model_id)
    job_id = uuid.uuid4().hex[:16]
    output = data_root / "jobs" / project["id"] / "exports" / ("Refinement-" + job_id)
    source_hash = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            source_hash.update(block)
    record = {"id": job_id, "project_id": project["id"], "track_id": track_id,
              "source": source.name, "source_sha256": source_hash.hexdigest(),
              "model": model.name, "start_seconds": start, "source_offset_seconds": start - clip_start, "duration_seconds": duration,
              "status": "queued", "message": "Queued", "files": [], "folder": str(output),
              "process": None}
    with _LOCK:
        if any(j["status"] in ("queued", "running") for j in _JOBS.values()):
            raise ValueError("A separation preview is already running")
        _JOBS[job_id] = record
    thread = threading.Thread(target=_worker, args=(record, source, model, model_root, ffmpeg, separator),
                              daemon=True)
    thread.start()
    return public(record)


def _worker(record: dict, source: Path, model: Path, model_root: Path,
            ffmpeg: str, separator: str) -> None:
    output = Path(record["folder"])
    clip = output / "source-region.wav"
    try:
        output.mkdir(parents=True, exist_ok=False)
        with _LOCK:
            record["status"] = "running"
            record["message"] = "Preparing source region"
        subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y",
                        "-ss", str(record["source_offset_seconds"]),
                        "-t", str(record["duration_seconds"]), "-i", str(source),
                        "-c:a", "pcm_f32le", str(clip)],
                       check=True, timeout=180, capture_output=True)
        if not clip.is_file():
            raise RuntimeError("Source region was not produced")
        with _LOCK:
            record["message"] = "Separating with " + model.name
        cmd = [separator, str(clip), "--model_filename", model.name,
               "--model_file_dir", str(model_root), "--output_dir", str(output),
               "--output_format", "WAV", "--sample_rate", "48000"]
        env = os.environ.copy()
        env["PATH"] = str(Path(ffmpeg).parent) + os.pathsep + env.get("PATH", "")
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env)
        with _LOCK:
            record["process"] = proc
        try:
            _, err = proc.communicate(timeout=900)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            proc.communicate()
            raise RuntimeError("Separation preview exceeded the 15 minute limit") from exc
        if proc.returncode != 0:
            raise RuntimeError("Separator returned error " + str(proc.returncode) + ": " +
                               err.decode("utf-8", errors="replace")[-400:])
        files = sorted(p.name for p in output.glob("*.wav") if p.name != clip.name and p.stat().st_size > 44)
        if not files:
            raise RuntimeError("Separator produced no candidate WAVs")
        manifest = {key: record[key] for key in ("id", "project_id", "track_id", "source",
                    "source_sha256", "model", "start_seconds", "source_offset_seconds", "duration_seconds")}
        manifest["candidate_files"] = files
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        with _LOCK:
            record["files"] = files
            record["status"] = "complete"
            record["message"] = "Candidate ready for A/B"
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        with _LOCK:
            record["status"] = "failed"
            record["message"] = "ERROR: " + str(exc)[:600]
    finally:
        with _LOCK:
            record["process"] = None


def public(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in ("folder", "process")}


def status(project_id: str, job_id: str) -> dict:
    with _LOCK:
        record = _JOBS.get(job_id)
        if not record or record["project_id"] != project_id:
            raise ValueError("Unknown separation candidate")
        return public(record)


def audio_path(project_id: str, job_id: str, filename: str) -> Path:
    with _LOCK:
        record = _JOBS.get(job_id)
        if not record or record["project_id"] != project_id or record["status"] != "complete":
            raise ValueError("Separation candidate not ready")
        if filename not in record["files"] and filename != "source-region.wav":
            raise ValueError("Unknown candidate file")
        path = Path(record["folder"]) / filename
    if not path.is_file() or path.is_symlink():
        raise ValueError("Candidate audio missing")
    return path
