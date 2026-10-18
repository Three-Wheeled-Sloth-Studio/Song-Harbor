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
import projects
import daw
import library

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
        "separator_ready": SEPARATOR.is_file(),
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
                projects.write_project(DATA_ROOT, {
                    "version": projects.PROJECT_VERSION, "id": job["id"],
                    "filename": job["filename"], "title": Path(job["filename"]).stem,
                    "source_filename": job["filename"], "created_at": job["created_at"],
                    "model": MODEL, "files": files,
                    "stems": projects.default_settings(files),
                    "source_duration_seconds": job["source_duration_seconds"],
                })
        else:
            job["status"] = "error"
            job["message"] = f"Separation exited with code {rc}; found {len(files)} of 6 stems"
    except Exception as exc:
        job["status"] = "error"
        job["message"] = f"Failed to run separator: {exc}"
    finally:
        job["elapsed_seconds"] = round(time.monotonic() - started, 2)
        job["process"] = None


def get_job(ident: str) -> dict[str, Any] | None:
    """Recover completed jobs on demand after backend restart."""
    if not re.fullmatch(r"[a-f0-9]{12}", ident):
        return None
    if ident in jobs:
        return jobs[ident]
    record = projects.read_project(DATA_ROOT, ident)
    if not record or len(record.get("files", [])) != 6:
        return None
    folder = DATA_ROOT / "jobs" / ident
    if not all((folder / "stems" / f).is_file() for f in record["files"]):
        return None
    recovered = {
        "id": ident, "filename": record["filename"], "model": record.get("model", MODEL),
        "status": "complete", "message": "Saved song ready",
        "created_at": record.get("created_at"), "elapsed_seconds": None,
        "files": record["files"], "logs": [],
        "source_duration_seconds": record.get("source_duration_seconds"),
        "input_path": folder / record["source_filename"],
        "output_path": folder / "stems", "process": None,
    }
    with lock:
        return jobs.setdefault(ident, recovered)


class StemState(BaseModel):
    filename: str
    gain: float = Field(ge=0, le=2)
    mute: bool = False
    solo: bool = False


class SaveProject(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    stems: list[StemState] = Field(min_length=6, max_length=6)


class RenameLibrarySong(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class NewCollection(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None


class AssignCollection(BaseModel):
    song_id: str


@app.get("/api/library")
def library_index(query: str = "", collection_id: str | None = None) -> dict[str, Any]:
    library.adopt_jobs(DATA_ROOT)
    return {"songs": library.list_songs(DATA_ROOT, collection_id, query),
            "collections": library.list_collections(DATA_ROOT)}


@app.get("/api/library/trash")
def library_trash() -> dict[str, Any]:
    library.adopt_jobs(DATA_ROOT)
    return {"songs": [item for item in library.list_songs(DATA_ROOT, include_deleted=True)
                      if item["removed"]]}


class CombineTakesRequest(BaseModel):
    parent_song_id: str


@app.post("/api/library/songs/{song_id}/combine")
def library_combine(song_id: str, body: CombineTakesRequest, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return library.combine_takes(DATA_ROOT, body.parent_song_id, song_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/library/songs/{song_id}/remove")
def library_remove(song_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return library.remove_song(DATA_ROOT, song_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/library/songs/{song_id}/restore")
def library_restore(song_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return library.restore_song(DATA_ROOT, song_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.patch("/api/library/songs/{song_id}")
def library_rename(song_id: str, body: RenameLibrarySong, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    library.adopt_jobs(DATA_ROOT)
    try:
        return library.rename_song(DATA_ROOT, song_id, body.title)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/library/collections")
def library_create_collection(body: NewCollection, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return library.create_collection(DATA_ROOT, body.title, body.parent_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/library/collections/{collection_id}/songs")
def library_add_song(collection_id: str, body: AssignCollection, request: Request) -> dict[str, bool]:
    require_local_origin(request)
    try:
        library.assign_song(DATA_ROOT, body.song_id, collection_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"added": True}


@app.get("/api/projects")
def recent_projects() -> dict[str, Any]:
    return {"projects": projects.list_projects(DATA_ROOT)}


@app.get("/api/projects/{ident}")
def load_project(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident) if re.fullmatch(r"[a-f0-9]{12}", ident) else None
    job = get_job(ident)
    if not record or not job:
        raise HTTPException(404, "Saved song unavailable; verify its six stem files")
    return {"project": record, "job": snapshot(job)}


@app.put("/api/projects/{ident}")
def save_project(ident: str, request: Request, body: SaveProject) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job["status"] != "complete" or not record:
        raise HTTPException(404, "Saved song not found")
    received = [s.filename for s in body.stems]
    if len(set(received)) != 6 or set(received) != set(job["files"]):
        raise HTTPException(400, "Settings must contain exactly the six source stems")
    record["title"] = body.title.strip()
    if not record["title"]:
        raise HTTPException(400, "Song title cannot be blank")
    record["stems"] = [s.model_dump() for s in body.stems]
    record["updated_at"] = time.time()
    saved = projects.write_project(DATA_ROOT, record)
    library.adopt_jobs(DATA_ROOT)
    for song in library.list_songs(DATA_ROOT):
        if song["legacy_job_id"] == ident:
            library.rename_song(DATA_ROOT, song["id"], record["title"])
            break
    return {"project": saved}


class DawTargetRequest(BaseModel):
    target: str = "waveform"


class DawPathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2048)


@app.get("/api/daws")
def daw_catalog() -> dict[str, Any]:
    return {"targets": [daw.target("waveform")], "selected": "waveform",
            "installed": {"waveform": daw.resolve(APP_ROOT)}}


@app.post("/api/daws/waveform/detect")
def daw_detect(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    return {"executable": daw.resolve(APP_ROOT)}


@app.post("/api/daws/waveform/browse")
def daw_browse(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    return {"path": daw.choose_executable("Select installed Waveform executable")}


@app.post("/api/daws/waveform/locate")
def daw_locate(request: Request, body: DawPathRequest) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"executable": daw.set_location(APP_ROOT, body.path)}
    except (OSError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/daws/waveform/browse-installer")
def daw_browse_installer(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    return {"path": daw.choose_executable("Select downloaded Waveform installer", installer=True)}


@app.post("/api/daws/waveform/run-installer")
def daw_run_installer(request: Request, body: DawPathRequest) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return daw.start_installer(body.path)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/projects/{ident}/daw/export")
def export_to_daw(ident: str, request: Request, body: DawTargetRequest) -> dict[str, Any]:
    require_local_origin(request)
    if body.target not in daw.TARGETS:
        raise HTTPException(400, "Choose a supported DAW")
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job["status"] != "complete" or not record:
        raise HTTPException(409, "A completed song is required for DAW export")
    with lock:
        if job.get("exporting_waveform"):
            raise HTTPException(409, "An export is already running")
        job["exporting_waveform"] = True
    try:
        folder = projects.export_waveform(DATA_ROOT, record)
        job["last_daw_export"] = str(folder)
        return {"target": body.target, "directory": str(folder), "message": "DAW stems ready"}
    except (OSError, ValueError) as exc:
        raise HTTPException(400, f"Could not prepare DAW files: {exc}") from exc
    finally:
        job["exporting_waveform"] = False


@app.post("/api/projects/{ident}/daw/open-folder")
def daw_open_folder(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    if not job or job["status"] != "complete":
        raise HTTPException(409, "Select a completed song first")
    root = DATA_ROOT / "jobs" / ident / "exports"
    candidates = sorted((p for p in root.glob("Waveform*") if p.is_dir()),
                        key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []
    if not candidates:
        return {"status": "export_required", "message": "Prepare DAW files first"}
    if os.name != "nt":
        raise HTTPException(501, "Opening folders requires Windows")
    os.startfile(str(candidates[0]))  # type: ignore[attr-defined]
    return {"status": "opened", "directory": str(candidates[0])}


@app.post("/api/daws/waveform/launch")
def daw_launch(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    executable = daw.resolve(APP_ROOT)
    if not executable:
        return {"status": "setup_required", "target": "waveform"}
    try:
        subprocess.Popen([executable], cwd=str(Path(executable).parent),
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise HTTPException(400, f"Waveform couldn't launch: {exc}") from exc
    return {"status": "started", "target": "waveform"}


@app.post("/api/projects/{ident}/waveform")
def waveform_handoff(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job["status"] != "complete" or not record:
        raise HTTPException(404, "Saved song not found")
    with lock:
        if job.get("exporting_waveform"):
            raise HTTPException(409, "Waveform export already running")
        job["exporting_waveform"] = True
    try:
        output = projects.export_waveform(DATA_ROOT, record)
        return {"directory": str(output), "message": "Waveform import folder ready"}
    except (ValueError, OSError) as exc:
        raise HTTPException(500, f"Waveform export failed: {exc}") from exc
    finally:
        job["exporting_waveform"] = False


@app.post("/api/projects/{ident}/waveform/open")
def waveform_open(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    if not job or job["status"] != "complete":
        raise HTTPException(404, "Song not found")
    folder = DATA_ROOT / "jobs" / ident / "exports"
    candidates = sorted(
        (p for p in folder.glob("Waveform*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime, reverse=True,
    ) if folder.exists() else []
    if not candidates:
        raise HTTPException(404, "Export stems to Waveform first")
    if os.name != "nt":
        raise HTTPException(501, "Opening folders requires Windows")
    os.startfile(str(candidates[0]))  # type: ignore[attr-defined]
    return {"opened": True, "directory": str(candidates[0])}


@app.get("/api/jobs/{ident}")
def status(ident: str) -> dict[str, Any]:
    job = get_job(ident)
    if job is None:
        raise HTTPException(404, "Job not found")
    return snapshot(job)


@app.post("/api/jobs/{ident}/cancel")
def cancel(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    if job is None:
        raise HTTPException(404, "Job not found")
    proc = job.get("process")
    if job["status"] == "running" and proc is not None:
        job["status"] = "cancelled"
        proc.terminate()
    return snapshot(job)


@app.get("/api/jobs/{ident}/files/{filename}")
def download(ident: str, filename: str):
    job = get_job(ident)
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
    job = get_job(ident)
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
    job = get_job(ident)
    if job is None or job["status"] != "complete":
        raise HTTPException(404, "Mix unavailable")
    target = job["output_path"] / "Song Harbor Mix.wav"
    if not target.is_file():
        raise HTTPException(404, "Mix has not been exported")
    return FileResponse(target, filename=target.name, media_type="audio/wav")


@app.get("/api/jobs/{ident}/stream/{filename}")
def stream_stem(ident: str, filename: str):
    job = get_job(ident)
    if job is None or job["status"] != "complete" or filename not in job["files"]:
        raise HTTPException(404, "Stem not available")
    # Inline streaming supports browser media playback, including seeking via byte ranges.
    return FileResponse(job["output_path"] / filename, media_type="audio/wav")


@app.post("/api/jobs/{ident}/open-folder")
def open_folder(ident: str, request: Request) -> dict[str, bool]:
    require_local_origin(request)
    job = get_job(ident)
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
