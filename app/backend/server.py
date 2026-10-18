"""Song Harbor M0 local-only separator service.

Run from the same virtual environment that contains audio-separator.
No external network binding, no destructive source operations.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

APP_ROOT = Path(os.environ.get("SONG_HARBOR_HOME", str(Path(__file__).resolve().parents[2]))).resolve()
DATA_ROOT = Path(os.environ.get("SONG_HARBOR_DATA", str(APP_ROOT / "data"))).resolve()
MODEL_ROOT = Path(os.environ.get("SONG_HARBOR_MODELS", str(APP_ROOT / "models"))).resolve()
SEPARATOR = Path(sys.executable).with_name("audio-separator.exe")
MODEL = "htdemucs_6s.yaml"
MAX_UPLOAD = 1024 * 1024 * 1024
ALLOWED = {".wav", ".flac", ".mp3", ".m4a", ".aiff", ".aif", ".ogg"}
DURATION_TOLERANCE_SECONDS = 0.25
for folder in (DATA_ROOT, MODEL_ROOT):
    folder.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Song Harbor local separator", docs_url=None, redoc_url=None)
lock = threading.Lock()
jobs: dict[str, dict[str, Any]] = {}
active: dict[str, subprocess.Popen[str] | None] = {"process": None}


def snapshot(job: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in job.items() if k not in ("process", "input_path", "output_path")}


def safe_name(name: str) -> str:
    basename = Path(name.replace("\\", "/")).name
    stem = re.sub(r"[^a-zA-Z0-9_. -]", "_", Path(basename).stem).strip(". ")[:100] or "song"
    return stem + Path(basename).suffix.lower()


def probe_duration(path: Path) -> float:
    """Use the actual decoded-audio duration, never the UI's assumed duration."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required to validate complete stems; install FFmpeg on PATH")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, text=True, capture_output=True, timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    value = float(result.stdout.strip())
    if not 0 < value < float("inf"):
        raise ValueError(f"Invalid audio duration: {path.name}")
    return value


def validate_stem_lengths(source_duration: float, durations: dict[str, float],
                          tolerance: float = DURATION_TOLERANCE_SECONDS) -> list[str]:
    """Return human-readable output mismatches for caller to reject."""
    return [
        f"{name}: {duration:.2f}s vs source {source_duration:.2f}s"
        for name, duration in durations.items()
        if abs(duration - source_duration) > tolerance
    ]


def require_local_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:5173", "http://localhost:5173"}:
        raise HTTPException(403, "Requests must originate from the local Song Harbor UI")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ready": SEPARATOR.is_file(),
        "model": MODEL,
        "model_directory": str(MODEL_ROOT),
        "separator": str(SEPARATOR),
    }


@app.post("/api/jobs")
async def submit(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    require_local_origin(request)
    name = safe_name(file.filename or "song.wav")
    if Path(name).suffix not in ALLOWED:
        raise HTTPException(400, "Unsupported audio format")
    with lock:
        if any(j["status"] in ("uploading", "queued", "running") for j in jobs.values()):
            raise HTTPException(409, "A separation is already running")
        if not SEPARATOR.is_file():
            raise HTTPException(503, "audio-separator.exe not found in this Python environment")
        ident = uuid.uuid4().hex[:12]
        folder = DATA_ROOT / "jobs" / ident
        folder.mkdir(parents=True)
        input_path = folder / name
        job = {
            "id": ident, "filename": name, "model": MODEL,
            "status": "uploading", "message": "Importing audio",
            "created_at": time.time(), "elapsed_seconds": None,
            "files": [], "logs": [], "input_path": input_path,
            "output_path": folder / "stems", "process": None,
        }
        jobs[ident] = job
    try:
        size = 0
        with input_path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, "Maximum audio file size is 1 GiB")
                target.write(chunk)
        job["bytes"] = size
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        with lock:
            jobs.pop(ident, None)
        raise
    finally:
        await file.close()
    if size == 0:
        shutil.rmtree(folder, ignore_errors=True)
        with lock:
            jobs.pop(ident, None)
        raise HTTPException(400, "Audio file is empty")
    job["status"] = "queued"
    job["message"] = "Waiting to start"
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return snapshot(job)


def run_job(job: dict[str, Any]) -> None:
    output = job["output_path"]
    output.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(SEPARATOR), str(job["input_path"]),
        "--model_filename", MODEL,
        "--model_file_dir", str(MODEL_ROOT),
        "--output_dir", str(output),
        "--output_format", "WAV",
        "--sample_rate", "48000",
    ]
    started = time.monotonic()
    job["status"] = "running"
    job["message"] = "Separating six stems"
    try:
        source_duration = probe_duration(job["input_path"])
        job["source_duration_seconds"] = round(source_duration, 3)
        # No shell=True; all paths passed as distinct arguments.
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        job["process"] = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                job["logs"] = (job["logs"] + [line])[-80:]
        rc = proc.wait()
        files = sorted(p.name for p in output.glob("*.wav") if p.is_file())
        job["files"] = files
        if job["status"] == "cancelled":
            job["message"] = "Cancelled"
        elif rc == 0 and len(files) == 6:
            durations = {name: probe_duration(output / name) for name in files}
            job["stem_durations_seconds"] = {name: round(value, 3) for name, value in durations.items()}
            mismatches = validate_stem_lengths(source_duration, durations)
            if mismatches:
                job["status"] = "error"
                job["message"] = "Truncated or mismatched output: " + "; ".join(mismatches)
            else:
                job["status"] = "complete"
                job["message"] = f"Six full-length stems ready ({source_duration:.1f}s)"
        else:
            job["status"] = "error"
            job["message"] = f"Separation exited with code {rc}; found {len(files)} of 6 stems"
    except Exception as exc:
        job["status"] = "error"
        job["message"] = f"Failed to run separator: {exc}"
    finally:
        job["elapsed_seconds"] = round(time.monotonic() - started, 2)
        job["process"] = None


@app.get("/api/jobs/{ident}")
def status(ident: str) -> dict[str, Any]:
    job = jobs.get(ident)
    if job is None:
        raise HTTPException(404, "Job not found")
    return snapshot(job)


@app.post("/api/jobs/{ident}/cancel")
def cancel(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = jobs.get(ident)
    if job is None:
        raise HTTPException(404, "Job not found")
    proc = job.get("process")
    if job["status"] == "running" and proc is not None:
        job["status"] = "cancelled"
        proc.terminate()
    return snapshot(job)


@app.get("/api/jobs/{ident}/files/{filename}")
def download(ident: str, filename: str):
    job = jobs.get(ident)
    if job is None or job["status"] != "complete" or filename not in job["files"]:
        raise HTTPException(404, "Stem not available")
    return FileResponse(job["output_path"] / filename, filename=filename, media_type="audio/wav")


@app.post("/api/jobs/{ident}/open-folder")
def open_folder(ident: str, request: Request) -> dict[str, bool]:
    require_local_origin(request)
    job = jobs.get(ident)
    if job is None or job["status"] != "complete":
        raise HTTPException(404, "Output folder not available")
    if os.name == "nt":
        os.startfile(str(job["output_path"]))  # type: ignore[attr-defined]
    else:
        raise HTTPException(501, "Open folder is currently Windows-only")
    return {"opened": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
