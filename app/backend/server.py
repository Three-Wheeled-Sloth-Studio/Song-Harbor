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
from pydantic import BaseModel, Field
import dependencies

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
    ffprobe = dependency_tool("ffprobe")
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
    ffmpeg = dependencies.resolve(APP_ROOT)
    return {
        "ready": SEPARATOR.is_file() and bool(ffmpeg),
        "ffmpeg": ffmpeg,
        "needs_setup": ["ffmpeg"] if not ffmpeg else [],
        "model": MODEL,
        "model_directory": str(MODEL_ROOT),
        "separator": str(SEPARATOR),
    }


def dependency_tool(name: str) -> str:
    pair = dependencies.resolve(APP_ROOT)
    if not pair:
        raise RuntimeError("FFmpeg setup is required. Use the app's Configure FFmpeg action.")
    return pair[name]


class FfmpegLocation(BaseModel):
    path: str = Field(min_length=1, max_length=2048)


@app.get("/api/dependencies/ffmpeg")
def ffmpeg_status() -> dict[str, Any]:
    return {"found": dependencies.resolve(APP_ROOT),
            "suggested_install_directory": str(APP_ROOT / "tools" / "ffmpeg"),
            "config_path": str(dependencies.config_file(APP_ROOT))}


@app.post("/api/dependencies/ffmpeg/locate")
def ffmpeg_locate(body: FfmpegLocation, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"found": {k: str(v) for k, v in dependencies.save_binary(APP_ROOT, Path(body.path)).items()}}
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/dependencies/ffmpeg/browse")
def ffmpeg_browse(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"path": dependencies.browse()}
    except (RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/dependencies/ffmpeg/search")
def ffmpeg_search(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    return {"matches": dependencies.search(APP_ROOT)}


@app.post("/api/dependencies/ffmpeg/install")
def ffmpeg_install(body: FfmpegLocation, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return dependencies.start_install(APP_ROOT, body.path)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/dependencies/ffmpeg/install/{ident}")
def ffmpeg_install_status(ident: str) -> dict[str, Any]:
    job = dependencies.jobs.get(ident)
    if job is None:
        raise HTTPException(404, "Installation not found")
    return job.copy()


@app.post("/api/jobs")
async def submit(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    require_local_origin(request)
    if not dependencies.resolve(APP_ROOT):
        raise HTTPException(409, "Configure FFmpeg in Song Harbor before separating audio")
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
        # Inject the selected FFmpeg bin directory into subprocess environment,
        # because audio-separator also invokes FFmpeg internally.
        env = os.environ.copy()
        env["PATH"] = str(dependencies.resolve(APP_ROOT)["directory"]) + os.pathsep + env.get("PATH", "")
        # No shell=True; all paths passed as distinct arguments.
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=env,
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


class StemMixSetting(BaseModel):
    filename: str
    gain: float = Field(ge=0, le=2)
    mute: bool = False
    solo: bool = False


class MixRequest(BaseModel):
    stems: list[StemMixSetting] = Field(min_length=6, max_length=6)


def validate_mix(job: dict[str, Any], settings: list[StemMixSetting]) -> list[tuple[str, float]]:
    """Produce the safe, ordered effective gains for exactly six known stems."""
    known = set(job["files"])
    received = [setting.filename for setting in settings]
    if len(known) != 6 or len(received) != 6 or set(received) != known or len(set(received)) != 6:
        raise ValueError("Mix must contain each of the six existing stems exactly once")
    any_solo = any(setting.solo for setting in settings)
    return [
        (setting.filename, 0.0 if setting.mute or (any_solo and not setting.solo) else setting.gain)
        for setting in settings
    ]


@app.post("/api/jobs/{ident}/mix")
def render_mix(ident: str, request: Request, body: MixRequest) -> dict[str, str]:
    require_local_origin(request)
    job = jobs.get(ident)
    if job is None or job["status"] != "complete":
        raise HTTPException(409, "A completed separation is required before mixing")
    try:
        levels = validate_mix(job, body.stems)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Prevent simultaneous writes of the same output; don't block the audio workbench.
    with lock:
        if job.get("rendering", False):
            raise HTTPException(409, "Mix export is already in progress")
        job["rendering"] = True

    target = job["output_path"] / "Song Harbor Mix.wav"
    temporary = job["output_path"] / "Song Harbor Mix.partial.wav"
    try:
        ffmpeg = dependency_tool("ffmpeg")
    except RuntimeError as exc:
        job["rendering"] = False
        raise HTTPException(409, str(exc)) from exc

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
    for filename, _ in levels:
        command.extend(["-i", str(job["output_path"] / filename)])
    filters = []
    for index, (_, gain) in enumerate(levels):
        filters.append(f"[{index}:a]volume={gain:.6f}[s{index}]")
    inputs = "".join(f"[s{index}]" for index in range(len(levels)))
    filters.append(f"{inputs}amix=inputs=6:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.98:level=0[mix]")
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[mix]", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le", str(temporary),
    ])
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=1800,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-1200:] or f"FFmpeg exited {result.returncode}")
        source_duration = job.get("source_duration_seconds") or probe_duration(job["input_path"])
        rendered_duration = probe_duration(temporary)
        if abs(rendered_duration - source_duration) > DURATION_TOLERANCE_SECONDS:
            raise RuntimeError(f"Export length mismatch: {rendered_duration:.2f}s vs {source_duration:.2f}s")
        temporary.replace(target)
        return {"filename": target.name, "url": f"/api/jobs/{ident}/mix-file"}
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(500, f"Mix export failed: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
        job["rendering"] = False


@app.get("/api/jobs/{ident}/mix-file")
def download_mix(ident: str):
    job = jobs.get(ident)
    if job is None or job["status"] != "complete":
        raise HTTPException(404, "Mix unavailable")
    target = job["output_path"] / "Song Harbor Mix.wav"
    if not target.is_file():
        raise HTTPException(404, "Mix has not been exported")
    return FileResponse(target, filename=target.name, media_type="audio/wav")


@app.get("/api/jobs/{ident}/stream/{filename}")
def stream_stem(ident: str, filename: str):
    job = jobs.get(ident)
    if job is None or job["status"] != "complete" or filename not in job["files"]:
        raise HTTPException(404, "Stem not available")
    # Inline streaming supports browser media playback, including seeking via byte ranges.
    return FileResponse(job["output_path"] / filename, media_type="audio/wav")


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
