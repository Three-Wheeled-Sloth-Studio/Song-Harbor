"""Song Harbor M0 local-only separator service.

Run from the same virtual environment that contains audio-separator.
No external network binding, no destructive source operations.
"""
from __future__ import annotations

import os
import hashlib
import json
import re
import shutil
import subprocess
import math
import sys
import zipfile
import wave
import threading
import time
import uuid
from pathlib import Path
from typing import Literal, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import dependencies
import workspace_settings
import projects
import sections
import section_import
import daw
import audacity_handoff
import channel_split
import waveform_peaks
import track_routing
import app_update
import library
import stem_import
import track_lifecycle
import declick_recipes
import midi_arrangements
import midi_section_slices
import midi_section_composite
import polyphonic_midi
import drum_keymaps
import drum_transcription
import instrument_direction_match
import section_instrument_selection
import midi_proposal_preview
import midi_proposal_mock
import midi_proposal_direction
import sfz_pack
import sfz_sample_recovery
import curated_sfz
import sfz_render_adapter
import sfz_candidate_audio
import deshimmer_stem_jobs
import deshimmer_versions

APP_ROOT = Path(os.environ.get("SONG_HARBOR_HOME", str(Path(__file__).resolve().parents[2]))).resolve()
DATA_ROOT = Path(os.environ.get("SONG_HARBOR_DATA", str(APP_ROOT / "data"))).resolve()
MODEL_ROOT = Path(os.environ.get("SONG_HARBOR_MODELS", str(APP_ROOT / "models"))).resolve()
SEPARATOR = Path(sys.executable).with_name("audio-separator.exe")
MODEL = "htdemucs_6s.yaml"
UI_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
APP_PORT = int(os.environ.get("SONG_HARBOR_PORT", "8765"))
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


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as source:
        while block:=source.read(1024*1024):digest.update(block)
    return digest.hexdigest()


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
    if origin and origin not in {f"http://127.0.0.1:{APP_PORT}", f"http://localhost:{APP_PORT}", "http://127.0.0.1:5173", "http://localhost:5173"}:
        raise HTTPException(403, "Requests must originate from the local Song Harbor UI")


@app.get("/api/health")
def health() -> dict[str, Any]:
    ffmpeg = dependencies.resolve(APP_ROOT)
    return {
        "instance_token": os.environ.get("SONG_HARBOR_INSTANCE_TOKEN", ""),
        "api_features": ["library-v2", "library-remove", "combine-takes", "source-fingerprints"],
        "ready": SEPARATOR.is_file() and bool(ffmpeg),
        "separator_ready": SEPARATOR.is_file(),
        "ffmpeg": ffmpeg,
        "needs_setup": ["ffmpeg"] if not ffmpeg else [],
        "model": MODEL,
        "model_directory": str(MODEL_ROOT),
        "separator": str(SEPARATOR),
    }


@app.get("/api/runtime/status")
def runtime_status() -> dict[str, Any]:
    """Lightweight launcher-friendly status for avoiding mid-job restarts."""
    with lock:
        running = sum(job.get("status") in ("uploading", "queued", "running")
                      or bool(job.get("rendering"))
                      or bool(job.get("exporting_waveform"))
                      for job in jobs.values())
    return {"instance_token": os.environ.get("SONG_HARBOR_INSTANCE_TOKEN", ""),
            "pid": os.getpid(), "busy": running > 0, "active_jobs": running}


class QuitRequest(BaseModel):
    instance_token: str = Field(min_length=16, max_length=100)


@app.post("/api/runtime/quit")
def close_song_harbor(body: QuitRequest, request: Request) -> dict[str, str]:
    """Explicitly stop only this local Song Harbor server after a UI confirmation.

    Instance token + same-origin restrictions defend against drive-by requests.
    Never kill unrelated browser/application processes. Launcher reaps only
    the backend PID it started.
    """
    require_local_origin(request)
    expected=os.environ.get("SONG_HARBOR_INSTANCE_TOKEN","")
    if not expected or body.instance_token!=expected:
        raise HTTPException(403,"Song Harbor instance token is invalid")
    if runtime_status()["busy"]:
        raise HTTPException(409,"An audio processing job is active; finish it before quitting")
    def shutdown():
        time.sleep(.4)  # allow response to reach the browser
        import signal
        os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=shutdown,daemon=True).start()
    return {"status":"closing"}


@app.get("/api/runtime/version")
def runtime_version() -> dict[str, str]:
    return app_update.local_version(Path(__file__).resolve().parents[2])


@app.get("/api/runtime/update")
def inspect_app_update() -> dict[str, Any]:
    state=app_update.git_info(Path(__file__).resolve().parents[2])
    state["busy"]=runtime_status()["busy"]
    return state


class RestartRequest(BaseModel):
    instance_token: str = Field(min_length=16, max_length=100)


@app.post("/api/runtime/update/relaunch")
def restart_with_update(body: RestartRequest, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    expected=os.environ.get("SONG_HARBOR_INSTANCE_TOKEN","")
    if not expected or body.instance_token != expected:
        raise HTTPException(403,"This Song Harbor instance is no longer current")
    if runtime_status()["busy"]:
        raise HTTPException(409,"Processing is active. Finish current work before restarting.")
    repository=Path(__file__).resolve().parents[2]
    state=app_update.git_info(repository)
    if not state.get("supported") or not state.get("can_fast_forward"):
        raise HTTPException(409, state.get("reason") or "Cannot update this checkout safely")
    try:
        app_update.begin_relaunch(repository,APP_ROOT,os.getpid())
    except (OSError,RuntimeError) as exc:
        raise HTTPException(500,f"Could not open update launcher: {exc}") from exc
    app_update.stop_after_response()
    return {"restarting":True,
            "message":"A separate update console will rebuild and reopen Song Harbor. Save unsaved browser edits before using this action."}


def dependency_tool(name: str) -> str:
    pair = dependencies.resolve(APP_ROOT)
    if not pair:
        raise RuntimeError("FFmpeg setup is required. Use the app's Configure FFmpeg action.")
    return pair[name]


class WorkingDirectoryRequest(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


@app.get("/api/settings/working-files")
def working_files_status() -> dict[str, Any]:
    return workspace_settings.status(APP_ROOT, DATA_ROOT)


@app.post("/api/settings/working-files/browse")
def browse_working_files(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"path": workspace_settings.choose_directory()}
    except (OSError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.put("/api/settings/working-files")
def configure_working_files(body: WorkingDirectoryRequest, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    with lock:
        busy = any(j.get("status") in ("uploading", "queued", "running")
                   or j.get("rendering") or j.get("exporting_waveform") for j in jobs.values())
    if busy:
        raise HTTPException(409, "Finish active processing jobs before changing the working files location")
    try:
        return workspace_settings.stage(APP_ROOT, body.path)
    except (OSError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


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


@app.post("/api/jobs/import-tracks")
async def import_tracks(request: Request, files: list[UploadFile] = File(...),
                        title: str = Form("")) -> dict[str, Any]:
    """Import aligned audio tracks without source separation or destructive edits."""
    require_local_origin(request)
    if not 2 <= len(files) <= stem_import.MAX_UPLOADS+1:
        raise HTTPException(400,"Choose 2-64 tracks, or up to 128 channels plus manifest")
    if not dependencies.resolve(APP_ROOT):
        raise HTTPException(409,"Configure FFmpeg before importing tracks")
    manifest_uploads=[item for item in files if Path(item.filename or "").name.lower()=="manifest.json"]
    if len(manifest_uploads)>1:raise HTTPException(400,"Choose only one channel manifest")
    media=[item for item in files if item not in manifest_uploads]
    names=[safe_name(item.filename or "track.wav") for item in media]
    if not 2<=len(names)<=(stem_import.MAX_UPLOADS if manifest_uploads else stem_import.MAX_TRACKS):
        raise HTTPException(400,"Choose 2-64 tracks, or 2-128 files with a split manifest")
    if any(Path(name).suffix not in ALLOWED for name in names):
        raise HTTPException(400,"Unsupported audio format in track selection")
    if len(set(name.casefold() for name in names)) != len(names):
        raise HTTPException(400,"Two tracks have the same filename; rename one and retry")
    manifest_bytes=await manifest_uploads[0].read(256*1024+1) if manifest_uploads else None
    groups=None
    if manifest_bytes is not None:
        try:groups=stem_import.channel_groups(manifest_bytes,names)
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    suggested=stem_import.guess_song_title([group["source"] for group in groups] if groups else names)
    requested=title.strip() or suggested
    if not 1<=len(requested)<=120:
        raise HTTPException(400,"Song title must contain 1-120 characters")
    with lock:
        if any(j["status"] in ("uploading","queued","running") for j in jobs.values()):
            raise HTTPException(409,"Finish the active import or separation first")
        ident=uuid.uuid4().hex[:12]
        folder=DATA_ROOT/"jobs"/ident
        originals=folder/"originals"
        originals.mkdir(parents=True)
        job={"id":ident,"filename":requested+".wav","model":"imported tracks",
             "status":"uploading","message":"Importing original tracks",
             "created_at":time.time(),"elapsed_seconds":None,"files":[],"logs":[],
             "input_path":folder/"originals"/names[0],
             "output_path":folder/"stems","process":None}
        jobs[ident]=job
    try:
        total=0
        for source,name in zip(media,names):
            size=0
            with (originals/name).open("wb") as target:
                while chunk:=await source.read(1024*1024):
                    total+=len(chunk)
                    size+=len(chunk)
                    if size>MAX_UPLOAD or total>MAX_UPLOAD*16:
                        raise HTTPException(413,"Limit 1 GiB per file and 16 GiB per import")
                    target.write(chunk)
            if size==0:raise HTTPException(400,f"Empty track: {name}")
    except Exception:
        shutil.rmtree(folder,ignore_errors=True)
        with lock:jobs.pop(ident,None)
        raise
    finally:
        for source in files:await source.close()
    job["status"]="queued"
    job["message"]="Preparing aligned WAV tracks"
    threading.Thread(target=run_track_import,args=(job,names,requested,manifest_bytes),daemon=True).start()
    return snapshot(job)


def run_track_import(job:dict[str,Any],names:list[str],title:str,manifest_bytes:bytes|None=None)->None:
    started=time.monotonic()
    folder=DATA_ROOT/"jobs"/job["id"]
    output=folder/"stems"
    output.mkdir(exist_ok=True)
    job["status"]="running"
    job["message"]="Converting tracks to aligned WAV"
    try:
        groups=stem_import.channel_groups(manifest_bytes,names) if manifest_bytes else None
        duration=max(probe_duration(folder/"originals"/name) for name in names)
        if duration>60*15:raise ValueError("Imported tracks must be 15 minutes or shorter")
        source_names=[group["source"] for group in groups] if groups else names
        assignments=stem_import.identity_tracks(source_names)
        ffmpeg=dependency_tool("ffmpeg")
        converted=[]
        exported_channels=[]
        export_name="Channels-Imported-"+job["id"]
        channel_folder=folder/"exports"/export_name
        if groups:channel_folder.mkdir(parents=True)
        for idx,entry in enumerate(assignments,start=1):
            alias=entry["stem_alias"]
            filename=f"{idx:02d} ({alias}).wav"
            destination=output/filename
            filters=f"apad,atrim=duration={duration:.6f},asetpts=PTS-STARTPTS"
            if groups:
                group=groups[idx-1]
                left=folder/"originals"/group["left"]
                right=folder/"originals"/group["right"]
                cmd=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
                     "-i",str(left),"-i",str(right),"-filter_complex",
                     f"[0:a:0]aformat=channel_layouts=mono[l];[1:a:0]aformat=channel_layouts=mono[r];[l][r]amerge=inputs=2,{filters}[out]",
                     "-map","[out]","-ac","2","-ar","48000","-c:a","pcm_s24le",str(destination)]
            else:
                name=names[idx-1]
                cmd=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
                     "-i",str(folder/"originals"/name),"-map","0:a:0","-vn",
                     "-af",filters,"-ac","2","-ar","48000","-c:a","pcm_s24le",str(destination)]
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=360,
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if result.returncode:raise RuntimeError((result.stderr or "Audio conversion failed")[-500:])
            if not destination.is_file() or destination.stat().st_size<44:
                raise RuntimeError("Working WAV conversion produced no usable file")
            converted.append(filename)
            entry["working_filename"]=filename
            if groups:
                # Preserve the exact imported mono channels as independently routable children.
                for side in ("left","right"):
                    source_name=groups[idx-1][side]
                    child=f"{idx:02d} - {alias} - {side.capitalize()}.wav"
                    shutil.copy2(folder/"originals"/source_name,channel_folder/child)
                    exported_channels.append({"stem":alias,"source":filename,
                        "channel":side,"file":child,"start_seconds":0.0,"sample_rate_hz":48000})
            job["message"]=f"Prepared track {idx} of {len(assignments)}"
        job["files"]=converted
        job["source_duration_seconds"]=round(duration,3)
        channel_config={}
        if groups:
            (channel_folder/"manifest.json").write_text(json.dumps({
                "format":stem_import.MANIFEST_FORMAT,"version":1,
                "source_project_id":job["id"],"track_count":len(exported_channels),
                "tracks":exported_channels},indent=2),encoding="utf-8")
            channel_config={filename:{"export":export_name,"active":True} for filename in converted}
        projects.write_project(DATA_ROOT,{
            "version":projects.PROJECT_VERSION,"id":job["id"],"filename":job["filename"],
            "title":title,"source_filename":names[0],"created_at":job["created_at"],
            "model":"imported tracks","imported_tracks":True,"files":converted,
            "source_tracks":assignments,"channel_children":channel_config,
            "stems":projects.default_settings(converted),
            "source_duration_seconds":round(duration,3)})
        job["status"]="complete"
        job["message"]=f"{len(converted)} aligned stems imported"+(" with L/R routing restored" if groups else "")
    except Exception as exc:
        job["status"]="error"
        job["message"]=f"Track import failed: {exc}"
        job["logs"].append(str(exc))
    finally:
        job["elapsed_seconds"]=round(time.monotonic()-started,2)


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
    if not record or not record.get("files") or (not record.get("imported_tracks") and len(record["files"]) != 6):
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
        "input_path": folder / "originals" / record["source_filename"] if record.get("imported_tracks") else folder / record["source_filename"],
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
    stems: list[StemState] = Field(min_length=2, max_length=64)

class RenameTrackAlias(BaseModel):
    track_id: str = Field(min_length=1,max_length=80)
    expected_alias: str = Field(min_length=1,max_length=32)
    stem_alias: str = Field(min_length=1,max_length=32)
    display_name: str = Field(min_length=1,max_length=100)

class PositionTrack(BaseModel):
    track_id: str = Field(min_length=1,max_length=80)
    start_seconds: float = Field(ge=0)

class RemoveTrack(BaseModel):
    expected_alias: str = Field(min_length=1,max_length=32)



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
        raise HTTPException(404, "Saved song unavailable; verify its track files")
    return {"project": record, "job": snapshot(job)}


@app.post("/api/projects/{ident}/tracks/add")
async def add_project_track(ident: str, request: Request,
                            file: UploadFile = File(...),
                            stem_alias: str = Form(...),
                            display_name: str = Form(...),
                            start_seconds: float = Form(0.0),
                            section_id: str | None = Form(None),
                            preview_trim_db: float = Form(0.0),
                            accept_mode: str = Form("layer"),
                            replace_source_track_id: str = Form(""),
                            midi_candidate_id: str = Form(""),
                            original_gain_percent: float | None = Form(None)) -> dict[str, Any]:
    """Add a short, timeline-positioned clip without padding or touching sources."""
    require_local_origin(request)
    if not track_lifecycle.ALIAS.fullmatch(stem_alias) or stem_alias.casefold() in track_lifecycle.RESERVED:
        raise HTTPException(400,"Invalid or reserved script alias")
    if not 1<=len(display_name.strip())<=100:
        raise HTTPException(400,"Display name must have 1-100 characters")
    # FastAPI's Form defaults are marker objects when route functions are called
    # directly by unit tests rather than through request binding.
    if not isinstance(section_id,str):section_id=None
    if not isinstance(start_seconds,(int,float)):start_seconds=0.0
    if not isinstance(preview_trim_db,(int,float)):preview_trim_db=0.0
    if not isinstance(accept_mode,str):accept_mode="layer"
    if not isinstance(replace_source_track_id,str):replace_source_track_id=""
    # Existing clients keep their historical Replace=0% / Layer=100% behavior.
    if not isinstance(original_gain_percent,(int,float)):
        original_gain_percent=0 if accept_mode=="replace" else 100
    if not math.isfinite(original_gain_percent) or not 0<=original_gain_percent<=100:
        raise HTTPException(400,"Original stem gain must be between 0 and 100 percent")
    if accept_mode not in ("replace","layer"):
        raise HTTPException(400,"Select Replace or Layer")
    if original_gain_percent<100 and not replace_source_track_id:
        raise HTTPException(400,"Select an original source stem when lowering its region gain")
    if not math.isfinite(preview_trim_db) or not -12<=preview_trim_db<=9:
        raise HTTPException(400,"Candidate level must be between -12 and +9 dB")
    source_name=safe_name(file.filename or "")
    if Path(source_name).suffix not in ALLOWED:
        raise HTTPException(400,"Unsupported audio format")
    if not dependencies.resolve(APP_ROOT):
        raise HTTPException(409,"Configure FFmpeg before adding tracks")
    job=get_job(ident)
    if not job:raise HTTPException(404,"Song unavailable")
    with lock:
        record=projects.read_project(DATA_ROOT,ident)
        if job.get("status")!="complete" or not record:
            raise HTTPException(409,"Song must be complete before adding a stem")
        rows=track_lifecycle.ensure_identities(record)
        if len(rows)>=stem_import.MAX_TRACKS:
            raise HTTPException(400,"Maximum 64 source tracks")
        source_row=next((row for row in rows if row.get("track_id")==replace_source_track_id),None)
        if original_gain_percent<100 and not source_row:
            raise HTTPException(400,"The original stem is no longer available")
        replacement_regions=[]
        if isinstance(midi_candidate_id,str) and midi_candidate_id:
            try:
                verified=bass_midi.read_json(DATA_ROOT/"jobs"/ident,midi_candidate_id)
                if not verified.get("rendered"):
                    raise ValueError("Expected a rendered MIDI candidate")
                if abs(float(verified["start_seconds"])-float(start_seconds))>.005:
                    raise ValueError("MIDI candidate start does not match import position")
                if verified.get("source_track_id")!=replace_source_track_id and original_gain_percent<100:
                    raise ValueError("MIDI candidate must replace its own original stem")
                if verified.get("section_masks"):
                    replacement_regions=[(float(row["start_seconds"]),float(row["end_seconds"]))
                                         for row in verified["section_masks"]]
                    if len(replacement_regions)>64:
                        raise ValueError("Too many section regions")
                else:
                    # A full-score MIDI candidate is one continuous accepted
                    # region; section composites carry sparse explicit masks.
                    replacement_regions=[(float(start_seconds),float(start_seconds)+float(verified["duration_seconds"]))]
                candidate_end=float(start_seconds)+float(verified["duration_seconds"])
                for a,b in replacement_regions:
                    if not (float(start_seconds)-.005<=a<b<=candidate_end+.005):
                        raise ValueError("Replacement section lies outside candidate audio")
                    if original_gain_percent<100:
                        for mask in record.get("replacement_masks",[]):
                            if (mask.get("source_track_id")==replace_source_track_id and
                                float(mask.get("start_seconds",0))<b-.005 and
                                float(mask.get("end_seconds",0))>a+.005):
                                raise ValueError("A source replacement already covers this region")
                if any(replacement_regions[i][0]<replacement_regions[i-1][1]-.005
                       for i in range(1,len(replacement_regions))):
                    raise ValueError("MIDI replacement sections overlap or are out of order")
            except (ValueError,OSError,KeyError,TypeError) as exc:
                raise HTTPException(409,str(exc)) from exc
        if any(x["stem_alias"].casefold()==stem_alias.casefold() for x in rows):
            raise HTTPException(409,"Script alias already belongs to a track")
        if section_id:
            section=next((item for item in record.get("sections",[]) if item.get("id")==section_id),None)
            if not section:raise HTTPException(400,"Selected section no longer exists")
            start_seconds=float(section["start_seconds"])
        if not 0<=start_seconds<float("inf"):
            raise HTTPException(400,"Timeline position must be a non-negative timestamp")
        # Block mixing/export and conflicting operations until media validation
        # and one manifest replacement succeed or roll back.
        job["status"]="running"
        job["message"]="Importing new stem"
    folder=DATA_ROOT/"jobs"/ident
    original_dir=folder/"originals"
    original_dir.mkdir(parents=True,exist_ok=True)
    track_id="trk_"+uuid.uuid4().hex[:16]
    original=original_dir/(track_id+"_"+source_name)
    final_name=track_id+" ("+stem_alias+").wav"
    final=folder/"stems"/final_name
    staging=folder/"stems"/(track_id+".staging")
    try:
        length=0
        with original.open("xb") as target:
            while chunk:=await file.read(1024*1024):
                length+=len(chunk)
                if length>MAX_UPLOAD:
                    raise ValueError("Stem exceeds 1 GiB import limit")
                target.write(chunk)
        if length==0:raise ValueError("Stem audio is empty")
        digest=sha256_file(original)
        original_duration=probe_duration(original)
        song_duration=resolved_song_duration(record,job)
        if start_seconds+original_duration>song_duration+DURATION_TOLERANCE_SECONDS:
            raise ValueError("Placed stem extends beyond the song; choose an earlier timestamp or trim it")
        if original_gain_percent<100:
            original_start=float(source_row.get("start_seconds") or 0)
            original_end=original_start+float(source_row.get("duration_seconds") or song_duration)
            if start_seconds<original_start-.005 or start_seconds+original_duration>original_end+.005:
                raise ValueError("Replacement extends outside the original stem region")
        for row in rows:
            if row.get("content_sha256")==digest and abs(float(row.get("start_seconds",0))-start_seconds)<.001:
                raise ValueError("This audio is already imported at the same timeline position")
        ffmpeg=dependency_tool("ffmpeg")
        command=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
                 "-i",str(original),"-map","0:a:0","-vn",
                 "-af","asetpts=PTS-STARTPTS,volume="+str(preview_trim_db)+"dB",
                 "-ac","2","-ar","48000","-c:a","pcm_s24le","-f","wav",str(staging)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=360,
                              creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode or not staging.is_file() or staging.stat().st_size<44:
            raise ValueError("Audio conversion failed: "+(result.stderr or "")[-300:])
        os.replace(staging,final)
        if isinstance(midi_candidate_id,str) and midi_candidate_id:
            source_candidate=bass_midi.read_json(DATA_ROOT/"jobs"/ident,midi_candidate_id)
            if abs(probe_duration(final)-float(source_candidate["duration_seconds"]))>.06:
                raise ValueError("Section candidate audio duration differs from its approved source-replacement region")
        updated=track_lifecycle.ensure_identities(record)
        if len(updated)>=stem_import.MAX_TRACKS:raise ValueError("Maximum 64 source tracks")
        updated.append({"track_id":track_id,"original_filename":original.name,
                        "working_filename":final_name,"stem_alias":stem_alias,
                        "display_name":display_name.strip(),"imported":True,
                        "start_seconds":round(float(start_seconds),3),
                        "duration_seconds":round(probe_duration(final),3),
                        "content_sha256":digest,"import_trim_db":round(float(preview_trim_db),2)})
        record["source_tracks"]=updated
        if original_gain_percent<100:
            spans=replacement_regions or [(float(start_seconds),float(start_seconds+original_duration))]
            for a,b in spans:
                record.setdefault("replacement_masks",[]).append({
                    "replacement_track_id":track_id,"source_track_id":replace_source_track_id,
                    "source_filename":str(source_row["working_filename"]),
                    "start_seconds":round(a,3),"end_seconds":round(b,3),
                    "fade_seconds":round(min(.05,(b-a)/8),3),
                    "original_gain":round(original_gain_percent/100,4)})
        record["files"]=list(record["files"])+[final_name]
        record["stems"]=list(record.get("stems",[]))+[{"filename":final_name,"gain":1.0,"mute":False,"solo":False}]
        record["imported_tracks"]=True
        record["updated_at"]=time.time()
        with lock:
            # The manifest is replaced once; don't change job file routing first.
            projects.write_project(DATA_ROOT,record)
            job["files"]=record["files"]
            job["status"]="complete"
            job["message"]="New stem added"
        split_warning=""
        if isinstance(midi_candidate_id,str) and midi_candidate_id:
            # Only after the imported stem is safely committed. Channel split
            # is a reversible derivative and must never discard its parent.
            try:
                export=channel_split.split_stems(
                    DATA_ROOT,record,[final_name],
                    dependency_tool("ffmpeg"),dependency_tool("ffprobe"))
                track_routing.attach(DATA_ROOT,record,export,[final_name])
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
                split_warning="Stem was saved, but its L/R channel split failed: "+str(exc)
        return {"project":record,"job":snapshot(job),"channel_split_warning":split_warning}
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        final.unlink(missing_ok=True)
        original.unlink(missing_ok=True)
        status=409 if "already imported at the same timeline position" in str(exc) else 400
        raise HTTPException(status,str(exc)) from exc
    finally:
        staging.unlink(missing_ok=True)
        await file.close()
        with lock:
            if job.get("status")=="running":
                job["status"]="complete"
                job["message"]="Add stem failed; original mix preserved"


class DeclickRepairBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    filename: str
    source_key: str
    time_seconds: float
    half_window_ms: float = Field(default=1, ge=.15, le=3)


def _declick_folder(ident: str) -> tuple[Path, set[str]]:
    if not re.fullmatch(r"[a-f0-9]{12}", ident):
        raise HTTPException(404, "Project not found")
    project=projects.read_project(DATA_ROOT, ident)
    job=get_job(ident)
    if not project or not job or job.get("status") != "complete":
        raise HTTPException(404, "Completed song not found")
    tracks=project.get("source_tracks") or []
    filenames={row.get("working_filename") for row in tracks if isinstance(row, dict)}
    filenames={name for name in filenames if isinstance(name,str)}
    filenames.update(name for name in project.get("files",[]) if isinstance(name,str))
    return DATA_ROOT / "jobs" / ident, filenames


def _declick_source_path(ident: str, filename: str, source_key: str) -> Path:
    project=projects.read_project(DATA_ROOT, ident)
    if not project:
        raise ValueError("Project missing")
    if source_key == filename:
        return DATA_ROOT/"jobs"/ident/"stems"/filename
    if source_key in (filename+":left",filename+":right"):
        return track_routing.child_path(DATA_ROOT,project,filename,source_key.rsplit(":",1)[1])
    raise ValueError("Unrecognized de-click source lane")


@app.get("/api/projects/{ident}/cleanup/declick")
def list_declick_repairs(ident: str) -> dict[str, Any]:
    folder,_=_declick_folder(ident)
    try:
        repairs=declick_recipes.read(folder)
        digests={}
        for item in repairs:
            file=item.get("filename")
            source=_declick_source_path(ident,str(file),str(item.get("source_key") or ""))
            if not source.is_file():
                raise ValueError(f"Saved repair source missing: {file}")
            source_key=item.get("source_key")
            if source_key not in digests:
                digests[source_key]=sha256_file(source)
            if item.get("source_sha256")!=digests[source_key]:
                raise ValueError(f"Saved repair source was replaced or changed: {file}")
        return {"repairs":repairs}
    except (ValueError,OSError) as exc:
        raise HTTPException(409,str(exc)) from exc


@app.post("/api/projects/{ident}/cleanup/declick")
def accept_declick_repair(ident: str, body: DeclickRepairBody, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    folder,filenames=_declick_folder(ident)
    if body.source_key not in (body.filename,body.filename+":left",body.filename+":right"):
        raise HTTPException(400,"Invalid source key")
    project=projects.read_project(DATA_ROOT,ident) or {}
    identities=project.get("source_tracks") or []
    source_start=next((float(row.get("start_seconds") or 0)
                       for row in identities if row.get("working_filename")==body.filename),0.0)
    try:
        wav=_declick_source_path(ident,body.filename,body.source_key)
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    if not wav.is_file():
        raise HTTPException(409,"Repair source is missing")
    duration=probe_duration(wav)
    if not source_start+.01 < body.time_seconds < source_start+duration-.01:
        raise HTTPException(409,"De-click must be inside the source clip, away from its edges")
    try:
        with lock:
            return {"repairs": declick_recipes.append(folder,{**body.model_dump(),"source_sha256":sha256_file(wav)},filenames)}
    except (ValueError,OSError) as exc:
        raise HTTPException(409,str(exc)) from exc


@app.delete("/api/projects/{ident}/cleanup/declick/{repair_id}")
def undo_declick_repair(ident: str, repair_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    folder,_=_declick_folder(ident)
    try:
        with lock:
            return {"repairs":declick_recipes.remove(folder,repair_id)}
    except (ValueError,OSError) as exc:
        raise HTTPException(409,str(exc)) from exc


# CPU-only exploratory bass -> MIDI -> bowed-string reinstrumentation.
# Candidate files live under generated/bass-midi; the original Bass stem never changes.
import bass_midi
import instrument_library


class FluidSynthPathRequest(BaseModel):
    path: str = Field(min_length=1,max_length=2048)


@app.get("/api/settings/fluidsynth")
def get_fluidsynth_settings()->dict[str,Any]:
    return {"configured_path":instrument_library.configured_fluidsynth(APP_ROOT),
            "resolved_path":instrument_library.find_fluidsynth(DATA_ROOT,APP_ROOT)}


@app.put("/api/settings/fluidsynth")
def put_fluidsynth_settings(body:FluidSynthPathRequest,request:Request)->dict[str,Any]:
    require_local_origin(request)
    try:
        resolved=instrument_library.save_fluidsynth(APP_ROOT,body.path)
        return {"configured_path":resolved,"resolved_path":resolved}
    except (ValueError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.post("/api/settings/fluidsynth/browse")
def browse_fluidsynth_settings(request:Request)->dict[str,str|None]:
    require_local_origin(request)
    try:return {"path":instrument_library.browse_fluidsynth()}
    except (ValueError,OSError,RuntimeError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.get("/api/settings/sfizz")
def get_sfizz_settings()->dict[str,Any]:
    return {"configured_path":sfz_render_adapter.configured_sfizz(APP_ROOT),
            "resolved_path":sfz_render_adapter.find_renderer(APP_ROOT)}


@app.put("/api/settings/sfizz")
def put_sfizz_settings(body:FluidSynthPathRequest,request:Request)->dict[str,Any]:
    require_local_origin(request)
    try:
        resolved=sfz_render_adapter.save_renderer(APP_ROOT,body.path)
        return {"configured_path":resolved,"resolved_path":resolved}
    except (ValueError,OSError,sfz_render_adapter.SFZRenderError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.post("/api/settings/sfizz/browse")
def browse_sfizz_settings(request:Request)->dict[str,str|None]:
    require_local_origin(request)
    try:return {"path":sfz_render_adapter.browse_renderer()}
    except (ValueError,OSError,sfz_render_adapter.SFZRenderError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.get("/api/instruments")
def list_instrument_library()->dict[str,Any]:
    result=instrument_library.catalogue(DATA_ROOT)
    result["fluidsynth_ready"]=bool(instrument_library.find_fluidsynth(DATA_ROOT,APP_ROOT))
    result["sfizz_ready"]=bool(sfz_render_adapter.find_renderer(APP_ROOT))
    return result


@app.get("/api/instruments/curated-sfz")
def list_curated_sfz_packs()->dict[str,Any]:
    installed = instrument_library.catalogue(DATA_ROOT)["packs"]
    return {"packs":curated_sfz.curated_catalogue(installed)}


@app.get("/api/instruments/starters")
def list_instrument_starters()->dict[str,Any]:
    return {"starters":instrument_library.starter_catalogue(DATA_ROOT)}


class StarterInstallRequest(BaseModel):
    starter_id: str = Field(min_length=1,max_length=60)


@app.post("/api/instruments/starters/install")
def install_instrument_starter(request:Request,body:StarterInstallRequest)->dict[str,Any]:
    """Install only after user action, from an allowlisted hash-verified source."""
    require_local_origin(request)
    try:
        return instrument_library.install_starter(DATA_ROOT,body.starter_id)
    except (ValueError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.post("/api/instruments/sf2")
async def install_instrument_soundfont(request:Request,
                                      file:UploadFile=File(...),
                                      pack_name:str=Form("Imported SoundFont"))->dict[str,Any]:
    """User-initiated local SF2 import; never download or execute pack contents."""
    require_local_origin(request)
    if not (file.filename or "").lower().endswith(".sf2"):
        raise HTTPException(400,"Choose an .sf2 SoundFont")
    if not 1<=len(pack_name.strip())<=100:
        raise HTTPException(400,"Pack name must be 1–100 characters")
    import tempfile
    root=instrument_library.pack_root(DATA_ROOT)
    root.mkdir(parents=True,exist_ok=True)
    staged=None
    try:
        with tempfile.NamedTemporaryFile(dir=root,suffix=".sf2",delete=False) as temp:
            staged=Path(temp.name)
            total=0
            while chunk:=await file.read(1024*1024):
                total+=len(chunk)
                if total>instrument_library.SOUNDFONT_LIMIT:
                    raise ValueError("SoundFont exceeds 512 MB")
                temp.write(chunk)
        return instrument_library.install_sf2(DATA_ROOT,staged,pack_name.strip())
    except (ValueError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc
    finally:
        if staged is not None:staged.unlink(missing_ok=True)


@app.post("/api/instruments/sfz")
async def install_instrument_sfz(request:Request,
                                 file:UploadFile=File(...),
                                 pack_name:str=Form("Imported SFZ pack"),
                                 curated_id:str=Form(""))->dict[str,Any]:
    """Explicit user-uploaded self-contained ZIP; never extract arbitrary paths."""
    require_local_origin(request)
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400,"Choose a self-contained SFZ ZIP archive")
    if not 1<=len(pack_name.strip())<=100:
        raise HTTPException(400,"Pack name must be 1-100 characters")
    if curated_id and curated_id not in {entry["id"] for entry in curated_sfz.curated_catalogue()}:
        raise HTTPException(400,"Unknown curated instrument pack")
    import tempfile
    root=instrument_library.pack_root(DATA_ROOT)
    root.mkdir(parents=True,exist_ok=True)
    staged=None
    try:
        with tempfile.NamedTemporaryFile(dir=root,suffix=".zip",delete=False) as tmp:
            staged=Path(tmp.name)
            received=0
            while chunk:=await file.read(1024*1024):
                received+=len(chunk)
                if received>sfz_pack.MAX_ARCHIVE_BYTES:
                    raise ValueError("SFZ archive exceeds upload limit")
                tmp.write(chunk)
        return sfz_pack.install_zip(DATA_ROOT,staged,pack_name.strip(),curated_id=curated_id)
    except (ValueError,OSError,zipfile.BadZipFile,UnicodeError) as exc:
        raise HTTPException(400,str(exc)) from exc
    finally:
        if staged is not None:staged.unlink(missing_ok=True)


class SfZRepairRequest(BaseModel):
    pack_id: str = Field(min_length=20,max_length=20)


@app.post("/api/instruments/sfz/repair-missing")
def repair_missing_sfz_samples(body:SfZRepairRequest,request:Request)->dict[str,Any]:
    """Explicit user-initiated recovery from the installed curated publisher."""
    require_local_origin(request)
    try:
        with lock:
            return sfz_sample_recovery.repair(DATA_ROOT,body.pack_id)
    except (ValueError,OSError,UnicodeError) as exc:
        raise HTTPException(400,str(exc)) from exc


class BassMidiAnalyzeRequest(BaseModel):
    track_id: str = Field(min_length=1,max_length=80)
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0,le=600)


class BassMidiNote(BaseModel):
    pitch: int = Field(ge=28,le=76)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    velocity: int = Field(default=85,ge=1,le=127)


class BassMidiRenderRequest(BaseModel):
    notes: list[BassMidiNote] = Field(max_length=4000)
    instrument: Literal["bowed", "plucked", "warm_pad"] = "bowed"
    pack_id: str = Field(default="song-harbor-core",max_length=80)
    instrument_id: str = Field(default="",max_length=120)



@app.post("/api/projects/{ident}/drum-midi/analyze")
def analyze_drum_midi(ident:str,request:Request,body:BassMidiAnalyzeRequest)->dict[str,Any]:
    """Save a reviewable transient estimate; never claim exact drum identification."""
    require_local_origin(request)
    job=get_job(ident)
    record=projects.read_project(DATA_ROOT,ident) if job else None
    if not record or not job or job.get("status")!="complete":
        raise HTTPException(404,"Completed song not found")
    if not dependencies.resolve(APP_ROOT):
        raise HTTPException(409,"FFmpeg setup required to transcribe drums")
    song_duration=resolved_song_duration(record,job)
    if body.duration_seconds>drum_transcription.MAX_REGION or body.start_seconds+body.duration_seconds>song_duration+.005:
        raise HTTPException(400,"Select at most 10 minutes inside the song")
    try:
        rows=track_lifecycle.ensure_identities(record)
        row=next((item for item in rows if item.get("track_id")==body.track_id),None)
        if not row:raise ValueError("Selected drum source is unavailable")
        filename=str(row.get("working_filename",""))
        stem_root=(DATA_ROOT/"jobs"/ident/"stems").resolve()
        source=(stem_root/filename).resolve()
        if source.parent!=stem_root or not source.is_file() or source.suffix.lower()!=".wav":
            raise ValueError("Selected source stem WAV is unavailable")
        track_start=float(row.get("start_seconds") or 0)
        local_start=body.start_seconds-track_start
        track_duration=float(row.get("duration_seconds") or song_duration)
        if local_start<-.005 or local_start+body.duration_seconds>track_duration+.005:
            raise ValueError("Drum region falls outside the selected stem")
        hits=drum_transcription.transcribe_region(source,max(0,local_start),body.duration_seconds,
                                                   dependency_tool("ffmpeg"))
        if not hits:raise ValueError("No convincing drum attacks detected; choose a clearer region")
        asset=midi_arrangements.create(body.track_id,body.start_seconds,body.duration_seconds,hits,
                                       "Exploratory spectral drum-onset estimate; review classifications")
        asset["notes"]=[{**note,"channel":9} for note in asset["notes"]]
        asset["percussion"]={"mode":"drums","keymap":{"schema_version":1,"mapping_kind":"custom",
            "lanes":[{"pitch":pitch,"name":label} for pitch,label in drum_transcription.LANES.items()]}}
        midi_arrangements.save(DATA_ROOT/"jobs"/ident,asset)
        return asset
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.post("/api/projects/{ident}/bass-midi/analyze")
def analyze_bass_midi(ident:str,request:Request,body:BassMidiAnalyzeRequest)->dict[str,Any]:
    require_local_origin(request)
    job=get_job(ident)
    record=projects.read_project(DATA_ROOT,ident) if job else None
    if not record or not job or job.get("status")!="complete":
        raise HTTPException(404,"Completed song not found")
    if not dependencies.resolve(APP_ROOT):
        raise HTTPException(409,"FFmpeg setup required to transcribe bass")
    song_duration=resolved_song_duration(record,job)
    if (body.duration_seconds>bass_midi.MAX_REGION_SECONDS or
        body.start_seconds+body.duration_seconds>song_duration+.005):
        raise HTTPException(400,"Select up to 10 minutes within the song")
    try:
        rows=track_lifecycle.ensure_identities(record)
        row=next((r for r in rows if r.get("track_id")==body.track_id),None)
        if not row:
            raise ValueError("Selected stem does not exist")
        filename=str(row.get("working_filename",""))
        base=(DATA_ROOT/"jobs"/ident/"stems").resolve()
        source=(base/filename).resolve()
        if source.parent!=base or not source.is_file() or source.suffix.lower()!=".wav":
            raise ValueError("Selected stem working WAV unavailable")
        # Imported clips have their own local clock, independent of their song placement.
        track_start=float(row.get("start_seconds") or 0)
        local_start=body.start_seconds-track_start
        track_duration=float(row.get("duration_seconds") or song_duration)
        if local_start < -.005 or local_start+body.duration_seconds > track_duration+.005:
            raise ValueError("Selected region falls outside the stem's playable clip")
        notes=bass_midi.transcribe_region(source,max(0,local_start),body.duration_seconds,dependency_tool("ffmpeg"))
        if not notes:raise ValueError("No pitched notes found; choose a clearer region")
        candidate_id=uuid.uuid4().hex
        folder=bass_midi.candidate_folder(DATA_ROOT/"jobs"/ident,candidate_id)
        out={"candidate_id":candidate_id,"source_track_id":body.track_id,"source_alias":str(row.get("stem_alias") or ""),
             "source_working_filename":filename,"start_seconds":round(body.start_seconds,3),
             "duration_seconds":round(body.duration_seconds,3),
             "notes":notes,"original_notes":notes,"render_kind":"synthetic_bowed_preview",
             "method":"CPU harmonic salience / monophonic pitched-stem estimate"}
        bass_midi.write_json(folder/"candidate.json",out)
        return out
    except (ValueError,OSError,subprocess.TimeoutExpired) as exc:
        raise HTTPException(400,str(exc)) from exc


class MidiArrangementFromCandidateRequest(BaseModel):
    candidate_id: str = Field(pattern=r"^[a-f0-9]{32}$")

class MidiArrangementEditRequest(BaseModel):
    base_revision: int = Field(ge=0)
    operations: list[dict[str,Any]] = Field(default_factory=list,max_length=2000)
    update_percussion: bool = False
    percussion: dict[str,Any] | None = None
    update_instrument_sections: bool = False
    instrument_sections: dict[str,Any] | None = None

class MidiProposalPreviewRequest(BaseModel):
    schema_version: int
    base_revision: int
    source_track_id: str
    target_stem: str
    sections: list[dict[str,Any]]
    operations: list[dict[str,Any]] = Field(default_factory=list,max_length=2000)
    instrument_sections: dict[str,Any] | None = None


@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/proposal-preview")
def preview_midi_proposal(ident:str,asset_id:str,body:MidiProposalPreviewRequest,
                          request:Request)->dict[str,Any]:
    """Validate and diff a provider-neutral plan without writing project state."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        root=DATA_ROOT/"jobs"/ident
        asset=midi_arrangements.read(root,asset_id)
        project=projects.read_project(DATA_ROOT,ident)
        if not project:raise HTTPException(404,"Song unavailable")
        return midi_proposal_preview.preview(
            asset,body.model_dump(),project.get("sections",[]),
            instrument_library.catalogue(DATA_ROOT))
    except HTTPException:raise
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


class MidiDirectionProposalRequest(BaseModel):
    base_revision: int = Field(ge=0)
    source_track_id: str = Field(min_length=1,max_length=100)
    target_stem: str = Field(min_length=1,max_length=20)
    instruction: str = Field(min_length=1,max_length=3000)
    section_ids: list[str] = Field(min_length=1,max_length=64)


@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/proposal-direction")
def direction_midi_proposal(ident:str,asset_id:str,body:MidiDirectionProposalRequest,
                            request:Request)->dict[str,Any]:
    """One action: inspect library, construct bounded preset plan, preview diff."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        root=DATA_ROOT/"jobs"/ident
        asset=midi_arrangements.read(root,asset_id)
        if asset["revision"]!=body.base_revision:
            raise HTTPException(409,"Saved MIDI revision changed; reopen and try again")
        if asset["source"]["track_id"]!=body.source_track_id:
            raise ValueError("Direction source differs from saved arrangement")
        project=projects.read_project(DATA_ROOT,ident)
        if not project:raise HTTPException(404,"Song unavailable")
        track=next((row for row in project.get("source_tracks",[])
                    if isinstance(row,dict) and row.get("track_id")==asset["source"]["track_id"]),None)
        if track and "vocal" in str(track.get("stem_alias","")).casefold():
            raise ValueError("Vocal stems are excluded from instrument replacement proposals")
        timeline=project.get("sections",[])
        catalogue=instrument_library.catalogue(DATA_ROOT)
        proposal,mapping=midi_proposal_direction.propose(
            asset,timeline,body.section_ids,body.target_stem,body.instruction,catalogue)
        review=midi_proposal_preview.preview(asset,proposal,timeline,catalogue)
        return {"provider":"library_mapping","proposal":proposal,
                "review":review,"mapping":mapping,
                "capability":"verified_installed_presets_only"}
    except HTTPException:raise
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


class MidiMockProposalRequest(BaseModel):
    base_revision: int = Field(ge=0)
    source_track_id: str = Field(min_length=1,max_length=100)
    target_stem: str = Field(min_length=1,max_length=20)
    section_ids: list[str] = Field(min_length=1,max_length=64)
    velocity_delta: int = Field(default=5,ge=-20,le=20)


@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/proposal-mock")
def mock_midi_proposal(ident:str,asset_id:str,body:MidiMockProposalRequest,
                       request:Request)->dict[str,Any]:
    """Generate a reproducible local example plan, without writing it."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        root=DATA_ROOT/"jobs"/ident
        asset=midi_arrangements.read(root,asset_id)
        if asset["revision"]!=body.base_revision:
            raise HTTPException(409,"Saved MIDI arrangement revision changed")
        if asset["source"]["track_id"]!=body.source_track_id:
            raise ValueError("Source track differs from saved MIDI arrangement")
        project=projects.read_project(DATA_ROOT,ident)
        if not project:raise HTTPException(404,"Song unavailable")
        plan=midi_proposal_mock.propose(
            asset,project.get("sections",[]),body.section_ids,
            body.target_stem,body.velocity_delta)
        review=midi_proposal_preview.preview(
            asset,plan,project.get("sections",[]),
            instrument_library.catalogue(DATA_ROOT))
        return {"provider":"offline_mock","proposal":plan,"review":review}
    except HTTPException:raise
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


class MidiProposalAcceptRequest(MidiProposalPreviewRequest):
    """Exact proposal accepted after an explicit diff review."""


@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/proposal-accept")
def accept_midi_proposal(ident:str,asset_id:str,body:MidiProposalAcceptRequest,
                         request:Request)->dict[str,Any]:
    """Revalidate under project lock, then persist one MIDI revision; no audio."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        with lock:
            root=DATA_ROOT/"jobs"/ident
            asset=midi_arrangements.read(root,asset_id)
            project=projects.read_project(DATA_ROOT,ident)
            if not project:raise HTTPException(404,"Song unavailable")
            proposal=body.model_dump()
            review=midi_proposal_preview.preview(
                asset,proposal,project.get("sections",[]),
                instrument_library.catalogue(DATA_ROOT))
            updated=midi_arrangements.apply_patch(
                asset,body.base_revision,body.operations,
                instrument_sections=body.instrument_sections,
                update_instrument_sections=body.instrument_sections is not None)
            midi_arrangements.save(root,updated)
        return {"asset":updated,"review":review,"accepted":True}
    except HTTPException:raise
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(409 if "Stale" in str(exc) else 400,str(exc)) from exc


@app.get("/api/projects/{ident}/midi-arrangements")
def list_midi_arrangements(ident:str)->dict[str,Any]:
    _ace_project(ident)
    return {"arrangements":midi_arrangements.list_assets(DATA_ROOT/"jobs"/ident)}

@app.post("/api/projects/{ident}/midi-arrangements/from-candidate")
def arrangement_from_candidate(ident:str,request:Request,
                               body:MidiArrangementFromCandidateRequest)->dict[str,Any]:
    """Freeze edited transcription notes independently of instrument render."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        candidate=bass_midi.read_json(DATA_ROOT/"jobs"/ident,body.candidate_id)
        asset=midi_arrangements.create(
            candidate["source_track_id"],float(candidate["start_seconds"]),
            float(candidate["duration_seconds"]),candidate["notes"],
            str(candidate.get("method","stem transcription")))
        asset["source"]["candidate_id"]=body.candidate_id
        midi_arrangements.save(DATA_ROOT/"jobs"/ident,asset)
        return asset
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc

def _render_saved_midi_candidate(project_root:Path,asset_id:str,asset:dict,
                                  selected:dict,font:Path,revision:int,
                                  section_id:str="", percussion:bool=False,
                                  drum_keymap:dict|None=None)->dict[str,Any]:
    """One independently maskable candidate. Input MIDI score remains immutable."""
    duration=asset["duration_samples"]/midi_arrangements.RATE
    if not .1<=duration<=bass_midi.MAX_REGION_SECONDS:
        raise HTTPException(400,"Arrangement render must be 0.1 to 600 seconds")
    if percussion:
        if drum_keymap is None:
            raise ValueError("Drum rendering requires an explicit kit keymap")
        drum_keymaps.verify_notes(asset,drum_keymap)
    midi=polyphonic_midi.to_midi(asset,selected["program"],selected["bank"],percussion=percussion)
    candidate_id=uuid.uuid4().hex
    folder=bass_midi.candidate_folder(project_root,candidate_id)
    folder.mkdir(parents=True,exist_ok=False)
    try:
        if selected["engine"]=="sf2":
            instrument_library.render_sf2(DATA_ROOT,selected,font,midi,
                folder/"bowed-preview.wav",duration,dependency_tool("ffmpeg"),APP_ROOT)
        else:
            sfz_candidate_audio.render_candidate(
                midi,font,folder/"bowed-preview.wav",duration,
                dependency_tool("ffmpeg"),APP_ROOT)
        (folder/"notes.mid").write_bytes(midi)
        notes=[{"pitch":n["pitch"],"start":round(n["start_sample"]/48000,3),
                "end":round(n["end_sample"]/48000,3),"velocity":n["velocity"]}
               for n in asset["notes"]]
        record={"candidate_id":candidate_id,"source_track_id":asset["source"]["track_id"],
            "start_seconds":asset["source"]["start_sample"]/48000,
            "duration_seconds":duration,"notes":notes,"original_notes":notes,
            "arrangement_id":asset_id,"arrangement_revision":revision,
            "render_kind":selected["engine"]+"_polyphonic_preview","rendered":True,
            "instrument":selected["id"],"pack_id":selected["pack_id"],
            "instrument_sha256":instrument_library.hash_file(font),
            "instrument_engine":selected["engine"],
            "pack_sha256":(json.loads((instrument_library.pack_root(DATA_ROOT)/selected["pack_id"]/"manifest.json").read_text(encoding="utf-8")).get("sha256","")),
            "method":"Saved polyphonic MIDI arrangement",
            "section_id":section_id,
            "percussion":percussion,
            "drum_keymap":drum_keymaps.validate_keymap(drum_keymap) if percussion else None}
        bass_midi.write_json(folder/"candidate.json",record)
        return record
    except Exception:
        shutil.rmtree(folder,ignore_errors=True)
        raise


class InstrumentMatchRequest(BaseModel):
    instruction: str = Field(min_length=1,max_length=3000)


@app.post("/api/instruments/match-direction")
def match_instrument_direction(body:InstrumentMatchRequest,request:Request)->dict[str,Any]:
    """Preview grounded installed-library matches before LLM interpretation."""
    require_local_origin(request)
    try:
        return instrument_direction_match.resolve(body.instruction,instrument_library.catalogue(DATA_ROOT))
    except (ValueError,KeyError,TypeError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.get("/api/instruments/drum-keymap/gm")
def general_midi_drum_keymap()->dict[str,Any]:
    """Expose explicit GM pitch labels for drum lanes and kit setup."""
    return drum_keymaps.default_keymap()


class PolyphonicRenderRequest(BaseModel):
    revision: int = Field(ge=0)
    pack_id: str = Field(min_length=1,max_length=80)
    instrument_id: str = Field(min_length=1,max_length=120)
    percussion: bool = False
    drum_keymap: dict | None = None

@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/render")
def render_polyphonic_arrangement(ident:str,asset_id:str,request:Request,
                                  body:PolyphonicRenderRequest)->dict[str,Any]:
    """Render an immutable saved revision through the existing FluidSynth engine.

    A new candidate is created for each render, leaving the score untouched.
    The regular candidate audition and track-acceptance flow is reused.
    """
    require_local_origin(request)
    _ace_project(ident)
    try:
        project_root=DATA_ROOT/"jobs"/ident
        asset=midi_arrangements.read(project_root,asset_id)
        if asset["revision"]!=body.revision:
            raise HTTPException(409,"Saved MIDI arrangement has changed; reopen its latest revision")
        if asset.get("instrument_sections") is not None:
            raise HTTPException(400,"This arrangement has saved section presets. Render its selected sections as one combined stem.")
        selected,font=instrument_library.resolve_instrument(DATA_ROOT,body.pack_id,body.instrument_id)
        if asset.get("percussion"):
            if not body.percussion or drum_keymaps.validate_keymap(body.drum_keymap) != asset["percussion"]["keymap"]:
                raise ValueError("Saved drum kit mapping differs from render request; reopen the arrangement")
        if selected["engine"] not in ("sf2","sfz"):
            raise HTTPException(400,"Select an installed SF2 or SFZ instrument for arrangement rendering")
        return _render_saved_midi_candidate(project_root,asset_id,asset,selected,font,body.revision,
                                            percussion=body.percussion,drum_keymap=body.drum_keymap)
    except HTTPException:
        raise
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired,sfz_render_adapter.SFZRenderError) as exc:
        raise HTTPException(400,str(exc)) from exc


class SectionInstrumentOverride(BaseModel):
    section_id: str = Field(min_length=1,max_length=100)
    pack_id: str = Field(min_length=1,max_length=80)
    instrument_id: str = Field(min_length=1,max_length=120)


class SectionalMidiRenderRequest(PolyphonicRenderRequest):
    section_ids: list[str] = Field(min_length=1,max_length=64)
    section_instruments: list[SectionInstrumentOverride] = Field(default_factory=list,max_length=64)


@app.post("/api/projects/{ident}/midi-arrangements/{asset_id}/render-sections")
def render_midi_sections(ident:str,asset_id:str,request:Request,
                         body:SectionalMidiRenderRequest)->dict[str,Any]:
    """Render independent section clips; acceptance controls each source mask."""
    require_local_origin(request)
    _ace_project(ident)
    root=DATA_ROOT/"jobs"/ident
    created=[]
    try:
        asset=midi_arrangements.read(root,asset_id)
        if asset["revision"]!=body.revision:
            raise HTTPException(409,"Saved MIDI arrangement revision changed; reopen latest")
        project=projects.read_project(DATA_ROOT,ident)
        if not project:
            raise HTTPException(404,"Song unavailable")
        pieces=midi_section_slices.select_sections(
            asset,project.get("sections",[]),body.section_ids)
        if asset.get("percussion"):
            if not body.percussion or drum_keymaps.validate_keymap(body.drum_keymap) != asset["percussion"]["keymap"]:
                raise ValueError("Saved drum kit mapping differs from render request; reopen the arrangement")
        if asset.get("instrument_sections") is not None:
            saved=asset["instrument_sections"]
            incoming=section_instrument_selection.validate_recipe({
                "schema_version":1,"section_ids":body.section_ids,
                "default":{"pack_id":body.pack_id,"instrument_id":body.instrument_id},
                "overrides":[entry.model_dump() for entry in body.section_instruments]})
            expected={"schema_version":1,"default":saved["default"],
                      "section_ids":saved["section_ids"],
                      "overrides":[row for row in saved["overrides"]
                                   if row["section_id"] in body.section_ids]}
            if incoming!=expected:
                raise ValueError("Rendered section presets differ from saved arrangement; reopen latest revision")
            choices=section_instrument_selection.resolve_recipe(
                saved,body.section_ids,instrument_library.catalogue(DATA_ROOT))
        else:
            choices=section_instrument_selection.resolve(
                body.section_ids,[entry.model_dump() for entry in body.section_instruments],
                body.pack_id,body.instrument_id,instrument_library.catalogue(DATA_ROOT))
        results=[]
        for piece in pieces:
            choice=choices[piece["section_id"]]
            selected,font=instrument_library.resolve_instrument(
                DATA_ROOT,choice["pack_id"],choice["instrument_id"])
            record=_render_saved_midi_candidate(root,asset_id,piece["arrangement"],
                                                selected,font,body.revision,
                                                piece["section_id"],body.percussion,body.drum_keymap)
            created.append(record["candidate_id"])
            results.append(record)
        return {"candidates":results}
    except HTTPException:
        for candidate_id in created:
            shutil.rmtree(bass_midi.candidate_folder(root,candidate_id),ignore_errors=True)
        raise
    except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired,
            sfz_render_adapter.SFZRenderError) as exc:
        for candidate_id in created:
            shutil.rmtree(bass_midi.candidate_folder(root,candidate_id),ignore_errors=True)
        raise HTTPException(400,str(exc)) from exc


@app.get("/api/projects/{ident}/midi-arrangements/{asset_id}")
def get_midi_arrangement(ident:str,asset_id:str)->dict[str,Any]:
    _ace_project(ident)
    try:return midi_arrangements.read(DATA_ROOT/"jobs"/ident,asset_id)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        raise HTTPException(404,str(exc)) from exc

@app.patch("/api/projects/{ident}/midi-arrangements/{asset_id}")
def edit_midi_arrangement(ident:str,asset_id:str,request:Request,
                          body:MidiArrangementEditRequest)->dict[str,Any]:
    """Revision-checked atomic patch. Useful for humans and future LLM proposals."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        with lock:
            root=DATA_ROOT/"jobs"/ident
            current=midi_arrangements.read(root,asset_id)
            if body.update_instrument_sections and body.instrument_sections is not None:
                recipe=section_instrument_selection.validate_recipe(body.instrument_sections)
                project=projects.read_project(DATA_ROOT,ident)
                if not project:raise ValueError("Song unavailable")
                by_id={s.get("id"):s for s in project.get("sections",[]) if isinstance(s,dict)}
                lo=current["source"]["start_sample"]
                hi=lo+current["duration_samples"]
                for section_id in recipe["section_ids"]:
                    section=by_id.get(section_id)
                    if not section:raise ValueError("Preset references missing song section")
                    left=section.get("start_seconds")
                    right=section.get("end_seconds")
                    if not isinstance(left,(int,float)) or not isinstance(right,(int,float)) or right<=left:
                        raise ValueError("Invalid section bounds")
                    if round(left*midi_arrangements.RATE)<lo or round(right*midi_arrangements.RATE)>hi:
                        raise ValueError("Preset section falls outside saved arrangement")
            updated=midi_arrangements.apply_patch(current,body.base_revision,body.operations,
                body.percussion,update_percussion=body.update_percussion,
                instrument_sections=body.instrument_sections,
                update_instrument_sections=body.update_instrument_sections)
            midi_arrangements.save(root,updated)
        return updated
    except (ValueError,KeyError,TypeError,OSError) as exc:
        raise HTTPException(409,str(exc)) from exc


@app.get("/api/projects/{ident}/bass-midi/{candidate_id}")
def get_bass_midi_candidate(ident:str,candidate_id:str)->dict[str,Any]:
    _ace_project(ident)
    try:return bass_midi.read_json(DATA_ROOT/"jobs"/ident,candidate_id)
    except (ValueError,OSError) as exc:raise HTTPException(404,str(exc)) from exc


@app.put("/api/projects/{ident}/bass-midi/{candidate_id}/notes")
def save_stem_midi_notes(ident:str,candidate_id:str,request:Request,
                         body:BassMidiRenderRequest)->dict[str,Any]:
    """Persist editable MIDI independently of reinstrumented audio rendering."""
    require_local_origin(request)
    _ace_project(ident)
    try:
        folder=bass_midi.candidate_folder(DATA_ROOT/"jobs"/ident,candidate_id)
        record=bass_midi.read_json(DATA_ROOT/"jobs"/ident,candidate_id)
        notes=bass_midi.validate_notes([n.model_dump() for n in body.notes],
                                       float(record["duration_seconds"]))
        selected, _=instrument_library.resolve_instrument(
            DATA_ROOT,body.pack_id,body.instrument_id or body.instrument)
        (folder/"notes.mid").write_bytes(bass_midi.midi_bytes(
            notes,float(record["duration_seconds"]),
            program=selected["program"],bank=selected["bank"]))
        record["notes"]=notes
        record["instrument"]=selected["id"]
        record["pack_id"]=selected["pack_id"]
        # Old WAV must not be accepted after MIDI edits without a new render.
        record["rendered"]=False
        (folder/"bowed-preview.wav").unlink(missing_ok=True)
        bass_midi.write_json(folder/"candidate.json",record)
        return record
    except (ValueError,OSError) as exc:
        raise HTTPException(400,str(exc)) from exc


@app.post("/api/projects/{ident}/bass-midi/{candidate_id}/render")
def render_bass_midi_candidate(ident:str,candidate_id:str,request:Request,
                               body:BassMidiRenderRequest)->dict[str,Any]:
    require_local_origin(request)
    _ace_project(ident)
    try:
        folder=bass_midi.candidate_folder(DATA_ROOT/"jobs"/ident,candidate_id)
        record=bass_midi.read_json(DATA_ROOT/"jobs"/ident,candidate_id)
        notes=bass_midi.validate_notes([n.model_dump() for n in body.notes],float(record["duration_seconds"]))
        selected, font=instrument_library.resolve_instrument(
            DATA_ROOT,body.pack_id,body.instrument_id or body.instrument)
        duration=float(record["duration_seconds"])
        midi=bass_midi.midi_bytes(notes,duration,program=selected["program"],bank=selected["bank"])
        if selected["engine"]=="sf2":
            instrument_library.render_sf2(DATA_ROOT,selected,font,midi,
                folder/"bowed-preview.wav",duration,dependency_tool("ffmpeg"),APP_ROOT)
        elif selected["engine"]=="sfz":
            sfz_candidate_audio.render_candidate(
                midi,font,folder/"bowed-preview.wav",duration,
                dependency_tool("ffmpeg"),APP_ROOT)
        elif selected["engine"]=="synthetic":
            bass_midi.render_instrument_wav(folder/"bowed-preview.wav",notes,duration,selected["id"])
        else:
            raise ValueError("Unsupported local instrument engine")
        (folder/"notes.mid").write_bytes(midi)
        record["notes"]=notes
        record["render_kind"]=selected["engine"]+"_"+selected["id"]+"_preview"
        record["instrument_engine"]=selected["engine"]
        if font is not None:
            record["instrument_sha256"]=instrument_library.hash_file(font)
        record["instrument"]=selected["id"]
        record["pack_id"]=selected["pack_id"]
        record["rendered"]=True
        bass_midi.write_json(folder/"candidate.json",record)
        return record
    except (ValueError,OSError,subprocess.TimeoutExpired,sfz_render_adapter.SFZRenderError) as exc:
        raise HTTPException(400,str(exc)) from exc


class ComposeMidiSectionsRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1,max_length=64)


@app.post("/api/projects/{ident}/bass-midi/compose-sections")
def compose_midi_sections(ident:str,request:Request,body:ComposeMidiSectionsRequest)->dict[str,Any]:
    """Build one stereo candidate with silence between previously rendered sections."""
    require_local_origin(request)
    _ace_project(ident)
    root=DATA_ROOT/"jobs"/ident
    if len(set(body.candidate_ids))!=len(body.candidate_ids):
        raise HTTPException(400,"Duplicate MIDI section candidate")
    project=projects.read_project(DATA_ROOT,ident)
    if not project:raise HTTPException(404,"Song unavailable")
    items=[]
    folder=None
    try:
        for ident_candidate in body.candidate_ids:
            candidate=bass_midi.read_json(root,ident_candidate)
            if not candidate.get("section_id") or not candidate.get("rendered"):
                raise ValueError("Only individually rendered MIDI sections can be combined")
            path=bass_midi.candidate_folder(root,ident_candidate)/"bowed-preview.wav"
            if not path.is_file():raise ValueError("Rendered MIDI section WAV is missing")
            items.append((candidate,path))
        common={str(item.get("source_track_id")) for item,_ in items}
        if len(common)!=1:raise ValueError("All selected sections must belong to one source stem")
        arrangement={(item.get("arrangement_id"),item.get("arrangement_revision")) for item,_ in items}
        if len(arrangement)!=1:raise ValueError("Selected sections must come from the same saved MIDI revision")
        if len({item.get("section_id") for item,_ in items})!=len(items):
            raise ValueError("Duplicate song section in composite")
        asset_id,revision=next(iter(arrangement))
        latest=midi_arrangements.read(root,asset_id)
        if latest["revision"]!=revision:
            raise ValueError("MIDI score changed after these sections were rendered; render the latest revision")
        by_section={entry["id"]:entry for entry in project.get("sections",[])}
        for item,_ in items:
            section=by_section.get(item["section_id"])
            if not section or abs(float(section["start_seconds"])-float(item["start_seconds"]))>.005 or abs(
                float(section["end_seconds"])-float(item["start_seconds"])-float(item["duration_seconds"]))>.06:
                raise ValueError("Section boundaries changed after rendering; render the selection again")
        duration=resolved_song_duration(project,get_job(ident))
        if any(float(item["start_seconds"])+float(item["duration_seconds"])>duration+.005 for item,_ in items):
            raise ValueError("Section extends beyond song end")
        candidate_id=uuid.uuid4().hex
        folder=bass_midi.candidate_folder(root,candidate_id)
        folder.mkdir(parents=True,exist_ok=False)
        first,masks=midi_section_composite.compose(
            [(path,float(item["start_seconds"]),float(item["duration_seconds"])) for item,path in items],
            folder/"bowed-preview.wav")
        masks=sorted(masks,key=lambda x:x["start_seconds"])
        for mask in masks:
            if any(mask["start_seconds"]<float(existing["end_seconds"])-.005 and
                   mask["end_seconds"]>float(existing["start_seconds"])+.005 and
                   existing.get("source_track_id")==next(iter(common))
                   for existing in project.get("replacement_masks",[])):
                raise ValueError("Selected region already has an accepted replacement; remove it first")
        # Keep the exact preset used in every region. The resulting WAV is
        # one stem for this part, not one track per (instrument x section).
        variants=[{"section_id":item["section_id"],"pack_id":item.get("pack_id"),
                   "instrument_id":item.get("instrument"),
                   "instrument_engine":item.get("instrument_engine"),
                   "instrument_sha256":item.get("instrument_sha256"),
                   "candidate_id":item["candidate_id"]} for item,_ in items]
        result={"candidate_id":candidate_id,"source_track_id":next(iter(common)),
                "start_seconds":first,
                "duration_seconds":masks[-1]["end_seconds"]-first,
                "rendered":True,"section_masks":masks,
                "section_instruments":variants,
                "arrangement_id":items[0][0].get("arrangement_id"),
                "arrangement_revision":items[0][0].get("arrangement_revision"),
                "method":"Combined MIDI section render",
                "render_kind":"composite_sections",
                "notes":[],"original_notes":[]}
        bass_midi.write_json(folder/"candidate.json",result)
        return result
    except (ValueError,OSError,KeyError,TypeError,EOFError,RuntimeError,wave.Error) as exc:
        if folder is not None:shutil.rmtree(folder,ignore_errors=True)
        raise HTTPException(400,str(exc)) from exc


@app.get("/api/projects/{ident}/bass-midi/{candidate_id}/audio")
def get_bass_midi_audio(ident:str,candidate_id:str)->FileResponse:
    _ace_project(ident)
    try:
        path=bass_midi.candidate_folder(DATA_ROOT/"jobs"/ident,candidate_id)/"bowed-preview.wav"
        if not path.is_file():raise ValueError("Render candidate before audition")
        return FileResponse(path,media_type="audio/wav",filename="bass-bowed-preview.wav")
    except (ValueError,OSError) as exc:raise HTTPException(404,str(exc)) from exc


@app.get("/api/projects/{ident}/bass-midi/{candidate_id}/midi")
def get_bass_midi_file(ident:str,candidate_id:str)->FileResponse:
    _ace_project(ident)
    try:
        path=bass_midi.candidate_folder(DATA_ROOT/"jobs"/ident,candidate_id)/"notes.mid"
        if not path.is_file():raise ValueError("Render candidate before MIDI export")
        return FileResponse(path,media_type="audio/midi",filename="bass-to-cello.mid")
    except (ValueError,OSError) as exc:raise HTTPException(404,str(exc)) from exc


class DeshimmerStemRequest(BaseModel):
    filename: str


@app.post("/api/projects/{ident}/cleanup/deshimmer")
def begin_deshimmer_stem(ident: str, request: Request, body: DeshimmerStemRequest) -> dict:
    """Start asynchronous processing of an existing, server-owned working stem."""
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not record or not job or job.get("status") != "complete":
        raise HTTPException(404, "Completed song not found")
    if body.filename not in record.get("files", []):
        raise HTTPException(400, "Choose a stem in the current song")
    try:
        return deshimmer_stem_jobs.start(DATA_ROOT, ident, body.filename)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ValueError, OSError, ImportError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/projects/{ident}/cleanup/deshimmer/{candidate_id}")
def deshimmer_stem_status(ident: str, candidate_id: str) -> dict:
    if not get_job(ident):
        raise HTTPException(404, "Song not found")
    try:
        return deshimmer_stem_jobs.status(ident, candidate_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/projects/{ident}/cleanup/deshimmer/{candidate_id}/audio")
def deshimmer_stem_audio(ident: str, candidate_id: str) -> FileResponse:
    if not get_job(ident):
        raise HTTPException(404, "Song not found")
    try:
        path = deshimmer_stem_jobs.candidate(ident, candidate_id)
        return FileResponse(path, media_type="audio/wav", filename="deshimmer-candidate.wav")
    except (KeyError, ValueError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/projects/{ident}/cleanup/deshimmer/{candidate_id}/cancel")
def cancel_deshimmer_stem(ident: str, candidate_id: str, request: Request) -> dict:
    require_local_origin(request)
    if not get_job(ident):
        raise HTTPException(404, "Song not found")
    try:
        return deshimmer_stem_jobs.cancel(ident, candidate_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/projects/{ident}/cleanup/deshimmer/{candidate_id}/accept")
def accept_deshimmer_version(ident: str, candidate_id: str, request: Request) -> dict:
    """Replace only the existing stem's working AUDIO VERSION, preserving its identity.

    Never add a Clean_* track, change source alias or add a replacement mask.
    """
    require_local_origin(request)
    job = get_job(ident)
    if not job or job.get("status") != "complete":
        raise HTTPException(409, "Completed song not available")
    with lock:
        record = projects.read_project(DATA_ROOT, ident)
        if not record:
            raise HTTPException(404, "Song not found")
        try:
            candidate = deshimmer_stem_jobs.candidate(ident, candidate_id)
            state = deshimmer_stem_jobs.status(ident, candidate_id)
            filename = state["filename"]
            if filename not in record.get("files", []):
                raise ValueError("Stem no longer exists in project")
            rows = track_lifecycle.ensure_identities(record)
            record["source_tracks"] = rows
            result = deshimmer_versions.adopt(
                DATA_ROOT, record, filename, candidate, state["source_hash"], candidate_id,
                lambda updated: projects.write_project(DATA_ROOT, updated),
                ffmpeg=dependency_tool("ffmpeg"), ffprobe=dependency_tool("ffprobe"))
            deshimmer_stem_jobs.consume(ident, candidate_id)
        except KeyError as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
            raise HTTPException(409, str(exc)) from exc
        job["message"] = "Stem cleanup accepted"
        return {"project": result, "job": snapshot(job), "stem": filename}


class UndoDeshimmerRequest(BaseModel):
    filename: str


@app.post("/api/projects/{ident}/cleanup/deshimmer/undo")
def undo_deshimmer_version(ident: str, request: Request, body: UndoDeshimmerRequest) -> dict:
    """Restore last accepted cleanup for a stem, leaving aliases/scripts intact."""
    require_local_origin(request)
    job = get_job(ident)
    if not job or job.get("status") != "complete":
        raise HTTPException(409, "Song not available")
    with lock:
        record = projects.read_project(DATA_ROOT, ident)
        if not record or body.filename not in record.get("files", []):
            raise HTTPException(404, "Stem unavailable")
        try:
            result = deshimmer_versions.undo(
                DATA_ROOT, record, body.filename,
                lambda updated: projects.write_project(DATA_ROOT, updated))
        except (ValueError, OSError) as exc:
            raise HTTPException(409, str(exc)) from exc
        job["message"] = "Stem cleanup undone"
        return {"project": result, "job": snapshot(job), "stem": body.filename}


@app.get("/api/projects/{ident}/tracks")
def list_project_tracks(ident: str) -> dict[str, Any]:
    """Upgrade legacy stem metadata without modifying the saved WAVs."""
    job=get_job(ident)
    with lock:
        record=projects.read_project(DATA_ROOT,ident) if job else None
        if not job or job.get("status")!="complete" or not record:
            raise HTTPException(404,"Completed song not found")
        try:
            tracks=track_lifecycle.ensure_identities(record)
        except ValueError as exc:
            raise HTTPException(409,str(exc)) from exc
        if tracks!=record.get("source_tracks"):
            record["source_tracks"]=tracks
            projects.write_project(DATA_ROOT,record)
    return {"tracks":tracks}


@app.put("/api/projects/{ident}/tracks/position")
def position_project_track(ident: str, request: Request, body: PositionTrack) -> dict[str, Any]:
    require_local_origin(request)
    job=get_job(ident)
    with lock:
        record=projects.read_project(DATA_ROOT,ident) if job else None
        if not job or job.get("status")!="complete" or not record:
            raise HTTPException(404,"Completed song not found")
        if any(mask.get("replacement_track_id")==body.track_id for mask in record.get("replacement_masks",[])):
            raise HTTPException(409,"Remove or undo replacement before repositioning its linked audio")
        try:
            updated=track_lifecycle.position(record,body.track_id,body.start_seconds,
                                             resolved_song_duration(record,job))
        except (ValueError,TypeError,KeyError) as exc:
            raise HTTPException(400,f"Position rejected: {exc}") from exc
        updated["updated_at"]=time.time()
        projects.write_project(DATA_ROOT,updated)
    return {"project":updated,"job":snapshot(job)}


@app.delete("/api/projects/{ident}/tracks/{track_id}")
def remove_project_track(ident: str, track_id: str, request: Request,
                         body: RemoveTrack) -> dict[str, Any]:
    """Detach an imported clip and archive its project copies for recovery."""
    require_local_origin(request)
    job=get_job(ident)
    with lock:
        record=projects.read_project(DATA_ROOT,ident) if job else None
        if not job or job.get("status")!="complete" or not record:
            raise HTTPException(404,"Completed song not found")
        if any(mask.get("source_track_id")==track_id for mask in record.get("replacement_masks",[])):
            raise HTTPException(409,"Remove its replacement clips before removing this source track")
        try:
            updated,removed=track_lifecycle.remove(record,track_id)
            if removed["stem_alias"]!=body.expected_alias:
                raise ValueError("Track changed since this window loaded; refresh before removing")
        except (ValueError,TypeError,KeyError) as exc:
            raise HTTPException(400,f"Removal rejected: {exc}") from exc
        updated["updated_at"]=time.time()
        projects.write_project(DATA_ROOT,updated)
        job["files"]=updated["files"]
    folder=DATA_ROOT/"jobs"/ident
    archive=folder/"trash"/f"{int(time.time())}-{track_id}"
    archive_warning=None
    try:
        archive.mkdir(parents=True,exist_ok=True)
        for parent,name in (("stems",removed.get("working_filename")),
                            ("originals",removed.get("original_filename"))):
            if isinstance(name,str) and Path(name).name==name:
                source=folder/parent/name
                if source.is_file():shutil.move(str(source),archive/name)
    except OSError as exc:
        # The manifest removal already restored playback. Leave any project
        # copy in place rather than turning a successful detach into a false
        # failure or deleting data during archive recovery.
        archive_warning=f"Track was removed, but a project copy could not be archived: {exc}"
    return {"project":updated,"job":snapshot(job),"archived_to":str(archive),
            "archive_warning":archive_warning}


@app.put("/api/projects/{ident}/tracks/rename")
def rename_project_track(ident: str, request: Request, body: RenameTrackAlias) -> dict[str, Any]:
    """One atomic manifest replacement; no WAV file or other project mutation."""
    require_local_origin(request)
    job = get_job(ident)
    with lock:
        record = projects.read_project(DATA_ROOT, ident) if job else None
        if not job or job.get("status")!="complete" or not record:
            raise HTTPException(404,"Completed song not found")
        try:
            updated=track_lifecycle.rename(record,body.track_id,
                                           body.stem_alias,body.display_name,body.expected_alias)
        except (ValueError,TypeError,KeyError) as exc:
            raise HTTPException(400,f"Rename rejected: {exc}") from exc
        updated["updated_at"]=time.time()
        projects.write_project(DATA_ROOT,updated)
    return {"project":updated}


@app.put("/api/projects/{ident}")
def save_project(ident: str, request: Request, body: SaveProject) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job["status"] != "complete" or not record:
        raise HTTPException(404, "Saved song not found")
    received = [s.filename for s in body.stems]
    if len(received)!=len(job["files"]) or len(set(received))!=len(received) or set(received)!=set(job["files"]):
        raise HTTPException(400,"Settings must include exactly the song tracks")
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


def resolved_song_duration(record: dict[str, Any], job: dict[str, Any]) -> float:
    """Recover legacy song duration from local audio and persist it once.

    The browser is not an authority for media length. Old project manifests
    lacked duration even when recovered WAVs already played successfully.
    """
    known = record.get("source_duration_seconds") or job.get("source_duration_seconds")
    try:
        value = float(known)
        if 0 < value < float("inf"):
            if not record.get("source_duration_seconds"):
                record["source_duration_seconds"] = round(value, 3)
                projects.write_project(DATA_ROOT, record)
            job["source_duration_seconds"] = value
            return value
    except (ValueError, TypeError):
        pass
    folder = DATA_ROOT / "jobs" / record["id"]
    source = folder / str(record.get("source_filename") or record.get("filename") or "")
    candidates = [source] + [folder / "stems" / name for name in record.get("files", [])]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            value = probe_duration(candidate)
        except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired):
            continue
        if 0 < value < float("inf"):
            record["source_duration_seconds"] = round(value, 3)
            job["source_duration_seconds"] = round(value, 3)
            projects.write_project(DATA_ROOT, record)
            return value
    raise ValueError("Could not read this song's audio duration. Check the source or stems and FFprobe setup.")


class SectionRecord(BaseModel):
    id: str | None = None
    kind: str
    number: int | None = None
    start_seconds: float
    end_seconds: float


class SectionsRequest(BaseModel):
    sections: list[SectionRecord] = Field(max_length=256)


@app.put("/api/projects/{ident}/sections")
def save_sections(ident: str, request: Request, body: SectionsRequest) -> dict[str, Any]:
    """Persist editor-owned section boundaries; do not touch source media or stems."""
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job.get("status") != "complete" or not record:
        raise HTTPException(404, "Completed song not found")
    try:
        proposed = sections.validate_sections(
            [item.model_dump() for item in body.sections],
            duration=resolved_song_duration(record, job),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    record["sections"] = proposed
    # Moving a marker preserves its proposal by stable ID; removing a marker
    # also drops its now-orphaned automation proposal.
    keep = {item["id"] for item in proposed}
    record["section_spatial_proposals"] = {
        ident: value for ident, value in
        record.get("section_spatial_proposals", {}).items() if ident in keep
    }
    record["section_pan_automation"] = [
        target for target in record.get("section_pan_automation", [])
        if target.get("section_id") in keep
    ]
    record["section_production"] = {
        key: value for key, value in record.get("section_production", {}).items() if key in keep
    }
    record["section_reverb_automation"] = [
        target for target in record.get("section_reverb_automation", [])
        if target.get("section_id") in keep
    ]
    record["section_width_automation"] = [
        target for target in record.get("section_width_automation", [])
        if target.get("section_id") in keep
    ]
    record["section_space_automation"] = [
        target for target in record.get("section_space_automation", [])
        if target.get("section_id") in keep
    ]
    record["section_auto_pan"] = [
        target for target in record.get("section_auto_pan", []) if target.get("section_id") in keep
    ]
    record["section_gain_automation"] = [
        target for target in record.get("section_gain_automation", []) if target.get("section_id") in keep
    ]
    record["section_volume_automation"] = [
        target for target in record.get("section_volume_automation", []) if target.get("section_id") in keep
    ]
    record["section_eq_automation"] = [
        target for target in record.get("section_eq_automation", [])
        if target.get("section_id") in keep
    ]
    record["section_lyrics"] = {
        ident: value for ident, value in
        record.get("section_lyrics", {}).items() if ident in keep
    }
    import section_production
    try:
        record["section_ending"] = section_production.materialize_ending(
            proposed, record.get("section_production", {}))
    except ValueError as exc:
        raise HTTPException(400, f"Ending must be updated before changing this boundary: {exc}") from exc
    record["updated_at"] = time.time()
    projects.write_project(DATA_ROOT, record)
    return {"sections": proposed, "tags": [sections.display_tag(item) for item in proposed]}


class SectionPanTarget(BaseModel):
    section_id: str
    source_key: str = Field(min_length=1, max_length=260)
    pan: float = Field(ge=-1.0, le=1.0)
    transition_seconds: float = Field(default=1.0, ge=0.05, le=30.0)
    curve: str = "smooth"


class SectionPanRequest(BaseModel):
    targets: list[SectionPanTarget] = Field(max_length=2048)


@app.get("/api/projects/{ident}/section-pan")
def read_section_pan(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    return {"targets": record.get("section_pan_automation", [])}


@app.put("/api/projects/{ident}/section-pan")
def save_section_pan(ident: str, request: Request, body: SectionPanRequest) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    valid_sections = {section["id"] for section in record.get("sections", [])}
    valid_sources = set(record.get("files", []))
    seen: set[tuple[str, str]] = set()
    targets = []
    for target in body.targets:
        key = (target.section_id, target.source_key)
        if target.section_id not in valid_sections or target.source_key not in valid_sources:
            raise HTTPException(400, "Pan targets must reference saved sections and source stems")
        if key in seen or target.curve not in ("linear", "smooth"):
            raise HTTPException(400, "Duplicate target or unsupported pan curve")
        seen.add(key)
        targets.append(target.model_dump())
    record["section_pan_automation"] = targets
    # Legacy structured pan editor remains authoritative for its pan instructions.
    # Remove stale inline block pan for affected sections; preserve reset events.
    import section_production
    blocks = dict(record.get("section_production", {}))
    for section in record.get("sections", []):
        sid = section["id"]
        base = [d for d in blocks.get(sid, []) if d["kind"] in ("reset", "reverb", "width", "space", "eq", "fade", "tail")]
        for item in targets:
            if item["section_id"] != sid:
                continue
            alias = next((a for a in section_production.source_aliases(record["files"],record.get("source_tracks",[])) if "(" + a + ")" in item["source_key"]), None)
            if alias and not any(d["track"] in ("all", alias) for d in base):
                base.append({"kind": "pan", "track": alias, "pan": item["pan"],
                             "transition_seconds": item["transition_seconds"], "curve": item["curve"]})
        if base:
            blocks[sid] = base
        else:
            blocks.pop(sid, None)
    record["section_production"] = blocks
    record["updated_at"] = time.time()
    projects.write_project(DATA_ROOT, record)
    return {"targets": targets}


class SectionReverbTarget(BaseModel):
    section_id: str
    source_key: str = Field(min_length=1, max_length=260)
    wet: float = Field(ge=0, le=1)
    transition_seconds: float = Field(default=1, ge=0.05, le=30)
    curve: str = "smooth"


class SectionReverbRequest(BaseModel):
    targets: list[SectionReverbTarget] = Field(max_length=2048)


@app.get("/api/projects/{ident}/section-reverb")
def read_section_reverb(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    return {"targets": record.get("section_reverb_automation", [])}


@app.put("/api/projects/{ident}/section-reverb")
def save_section_reverb(ident: str, request: Request, body: SectionReverbRequest) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    valid_sections = {item["id"] for item in record.get("sections", [])}
    valid_files = set(record.get("files", []))
    seen: set[tuple[str, str]] = set()
    targets = []
    for item in body.targets:
        key = (item.section_id, item.source_key)
        if item.section_id not in valid_sections or item.source_key not in valid_files:
            raise HTTPException(400, "Reverb target must reference a saved section and stem")
        if key in seen or item.curve not in ("linear", "smooth"):
            raise HTTPException(400, "Duplicate reverb target or invalid curve")
        seen.add(key)
        targets.append(item.model_dump())
    import section_production
    blocks = dict(record.get("section_production", {}))
    for section in record.get("sections", []):
        sid = section["id"]
        base = [d for d in blocks.get(sid, []) if d["kind"] in ("reset", "pan", "width", "space", "eq", "fade", "tail")]
        for item in targets:
            if item["section_id"] != sid:
                continue
            alias = next((a for a in section_production.source_aliases(record["files"],record.get("source_tracks",[])) if "(" + a + ")" in item["source_key"]), None)
            if alias and not any(d["kind"] == "reset" and d["track"] in ("all", alias) for d in base):
                base.append({"kind": "reverb", "track": alias, "wet": item["wet"],
                             "transition_seconds": item["transition_seconds"], "curve": item["curve"]})
        if base:
            blocks[sid] = base
        else:
            blocks.pop(sid, None)
    record["section_production"] = blocks
    record["section_reverb_automation"] = targets
    record["updated_at"] = time.time()
    projects.write_project(DATA_ROOT, record)
    return {"targets": targets}


class EndingRequest(BaseModel):
    fade_seconds: float = Field(default=0, ge=0, le=30)
    tail_seconds: float = Field(default=0, ge=0, le=10)
    curve: str = "smooth"


@app.put("/api/projects/{ident}/ending")
def save_song_ending(ident: str, request: Request, body: EndingRequest) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song unavailable")
    ordered = sorted(record.get("sections", []), key=lambda item: item["start_seconds"])
    if not ordered:
        raise HTTPException(409, "Align at least one song section before adding an ending")
    if body.curve not in ("smooth", "linear"):
        raise HTTPException(400, "Ending curve must be smooth or linear")
    last = ordered[-1]
    if body.fade_seconds > last["end_seconds"] - last["start_seconds"]:
        raise HTTPException(400, "Ending fade cannot exceed the last section's duration")
    import section_production
    blocks = dict(record.get("section_production", {}))
    directives = [d for d in blocks.get(last["id"], []) if d["kind"] not in ("fade", "tail")]
    if body.fade_seconds:
        directives.append({"kind": "fade", "track": "Master", "seconds": body.fade_seconds,
                           "curve": body.curve})
    if body.tail_seconds:
        directives.append({"kind": "tail", "track": "Master", "seconds": body.tail_seconds,
                           "curve": "smooth"})
    if directives:
        blocks[last["id"]] = directives
    else:
        blocks.pop(last["id"], None)
    result = section_production.materialize_ending(ordered, blocks)
    record["section_production"] = blocks
    record["section_ending"] = result
    record["updated_at"] = time.time()
    projects.write_project(DATA_ROOT, record)
    return {"ending": result}


class SectionWidthTarget(BaseModel):
    section_id: str
    source_key: str = Field(min_length=1, max_length=260)
    width: int = Field(ge=0, le=200)
    transition_seconds: float = Field(default=1, ge=0.05, le=30)
    curve: str = "smooth"


class SectionWidthRequest(BaseModel):
    targets: list[SectionWidthTarget] = Field(max_length=2048)


@app.get("/api/projects/{ident}/section-width")
def read_section_width(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    return {"targets": record.get("section_width_automation", [])}


@app.put("/api/projects/{ident}/section-width")
def save_section_width(ident: str, request: Request, body: SectionWidthRequest) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    sections_by_id = {item["id"] for item in record.get("sections", [])}
    files = set(record.get("files", []))
    seen: set[tuple[str, str]] = set()
    targets = []
    for item in body.targets:
        key = (item.section_id, item.source_key)
        if item.section_id not in sections_by_id or item.source_key not in files:
            raise HTTPException(400, "Width target must reference a saved section and source stem")
        if key in seen or item.curve not in ("linear", "smooth"):
            raise HTTPException(400, "Duplicate width target or invalid curve")
        seen.add(key)
        targets.append(item.model_dump())
    import section_production
    blocks = dict(record.get("section_production", {}))
    for section in record.get("sections", []):
        sid = section["id"]
        base = [d for d in blocks.get(sid, []) if d["kind"] != "width"]
        for item in targets:
            if item["section_id"] != sid:
                continue
            alias = next((a for a in section_production.source_aliases(record["files"],record.get("source_tracks",[])) if "(" + a + ")" in item["source_key"]), None)
            if not alias:
                raise HTTPException(400, "Unrecognized width stem")
            if any(d["kind"] == "reset" and d["track"] in ("all", alias) for d in base):
                raise HTTPException(400, "Width target conflicts with reset in same section; edit section script")
            base.append({"kind": "width", "track": alias, "width": item["width"],
                         "transition_seconds": item["transition_seconds"], "curve": item["curve"]})
        if base:
            blocks[sid] = base
        else:
            blocks.pop(sid, None)
    record["section_production"] = blocks
    record["section_width_automation"] = targets
    record["updated_at"] = time.time()
    projects.write_project(DATA_ROOT, record)
    return {"targets": targets}


class SectionSpaceTarget(BaseModel):
    section_id: str
    source_key: str = Field(min_length=1, max_length=260)
    amount: int = Field(ge=0, le=40)
    transition_seconds: float = Field(default=1, ge=0.05, le=30)
    curve: str = "smooth"


class SectionSpaceRequest(BaseModel):
    targets: list[SectionSpaceTarget] = Field(max_length=2048)


@app.get("/api/projects/{ident}/section-space")
def read_section_space(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    return {"targets": record.get("section_space_automation", [])}


@app.put("/api/projects/{ident}/section-space")
def save_section_space(ident: str, request: Request, body: SectionSpaceRequest) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song not found")
    valid_sections = {s["id"] for s in record.get("sections", [])}
    files = set(record.get("files", []))
    seen: set[tuple[str, str]] = set()
    targets=[]
    for item in body.targets:
        key=(item.section_id,item.source_key)
        if item.section_id not in valid_sections or item.source_key not in files:
            raise HTTPException(400, "Spatial reflection target must reference a saved section and stem")
        if key in seen or item.curve not in ("smooth","linear"):
            raise HTTPException(400, "Duplicate reflection target or unsupported curve")
        seen.add(key)
        targets.append(item.model_dump())
    import section_production
    blocks=dict(record.get("section_production", {}))
    for section in record.get("sections", []):
        sid=section["id"]
        base=[d for d in blocks.get(sid, []) if d["kind"] != "space"]
        for item in targets:
            if item["section_id"] != sid:
                continue
            alias=next((a for a in section_production.source_aliases(record["files"],record.get("source_tracks",[])) if "(" + a + ")" in item["source_key"]), None)
            if not alias:
                raise HTTPException(400, "Unrecognized spatial reflection source")
            if any(d["kind"]=="reset" and d["track"] in ("all",alias) for d in base):
                raise HTTPException(400, "Spatial reflection conflicts with reset; edit section script")
            base.append({"kind":"space","track":alias,"amount":item["amount"],
                         "transition_seconds":item["transition_seconds"],"curve":item["curve"]})
        if base:
            blocks[sid]=base
        else:
            blocks.pop(sid,None)
    record["section_production"]=blocks
    record["section_space_automation"]=targets
    record["updated_at"]=time.time()
    projects.write_project(DATA_ROOT,record)
    return {"targets":targets}


class SectionEqTarget(BaseModel):
    section_id: str
    source_key: str = Field(min_length=1,max_length=260)
    band: int = Field(ge=1,le=3)
    frequency: int = Field(ge=30,le=16000)
    q: float = Field(ge=.3,le=12)
    gain_db: float = Field(ge=-12,le=12)
    transition_seconds: float = Field(default=1,ge=.05,le=30)
    curve: str = "smooth"


class SectionEqRequest(BaseModel):
    targets: list[SectionEqTarget] = Field(max_length=2048)


@app.put("/api/projects/{ident}/section-eq")
def save_section_eq(ident:str, request:Request, body:SectionEqRequest)->dict[str,Any]:
    require_local_origin(request)
    record=projects.read_project(DATA_ROOT,ident)
    if not record or not get_job(ident):
        raise HTTPException(404,"Song not found")
    sections_by_id={s["id"] for s in record.get("sections",[])}
    files=set(record.get("files",[]))
    seen=set()
    targets=[]
    for item in body.targets:
        key=(item.section_id,item.source_key,item.band)
        if key in seen or item.curve not in ("smooth","linear"):
            raise HTTPException(400,"Duplicate EQ band or invalid curve")
        if item.section_id not in sections_by_id or item.source_key not in files:
            raise HTTPException(400,"EQ target must reference saved section and stem")
        seen.add(key)
        targets.append(item.model_dump())
    import section_production
    blocks=dict(record.get("section_production",{}))
    for section in record.get("sections",[]):
        sid=section["id"]
        base=[d for d in blocks.get(sid,[]) if d["kind"]!="eq"]
        for item in targets:
            if item["section_id"]!=sid:
                continue
            alias=next((a for a in section_production.source_aliases(record["files"],record.get("source_tracks",[])) if "(" + a + ")" in item["source_key"]), None)
            if not alias:
                raise HTTPException(400,"Unrecognized stem")
            if any(d["kind"]=="reset" and d["track"] in ("all",alias) for d in base):
                raise HTTPException(400,"EQ conflicts with reset in same section")
            base.append({"kind":"eq","track":alias,"band":item["band"],
                         "frequency":item["frequency"],"q":item["q"],
                         "gain_db":item["gain_db"],
                         "transition_seconds":item["transition_seconds"],"curve":item["curve"]})
        if base:blocks[sid]=base
        else:blocks.pop(sid,None)
    record["section_production"]=blocks
    record["section_eq_automation"]=targets
    record["updated_at"]=time.time()
    projects.write_project(DATA_ROOT,record)
    return {"targets":targets}


class SectionImportRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100000)
    mode: str = "replace"


@app.post("/api/projects/{ident}/sections/import")
def import_song_sections(ident: str, request: Request, body: SectionImportRequest) -> dict[str, Any]:
    """Validate every imported line before changing the project manifest."""
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job.get("status") != "complete" or not record:
        raise HTTPException(404, "Completed song not found")
    try:
        changed = section_import.apply(
            record, body.content, body.mode,
            resolved_song_duration(record, job))
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(400, f"Import rejected: {exc}") from exc
    retained_ids = {section["id"] for section in changed["sections"]}
    record["section_production"] = changed["section_production"]
    record["section_pan_automation"] = changed["section_pan_automation"]
    record["section_reverb_automation"] = changed["section_reverb_automation"]
    record["section_width_automation"] = changed["section_width_automation"]
    record["section_space_automation"] = changed["section_space_automation"]
    record["section_eq_automation"] = changed["section_eq_automation"]
    record["section_dynamics_automation"] = changed["section_dynamics_automation"]
    record["section_gain_automation"] = changed["section_gain_automation"]
    record["section_volume_automation"] = changed["section_volume_automation"]
    record["stem_time_offsets"] = changed["stem_time_offsets"]
    record["stem_echo_settings"] = changed["stem_echo_settings"]
    record["section_echo_automation"] = changed["section_echo_automation"]
    record["stem_groups"] = changed["stem_groups"]
    record["section_group_targets"] = changed["section_group_targets"]
    record["replacement_masks"] = changed["replacement_masks"]
    record["section_auto_pan"] = changed["section_auto_pan"]
    record["section_ending"] = changed["section_ending"]
    record.update({"sections": changed["sections"],
                   "section_spatial_proposals": changed["section_spatial_proposals"],
                   "section_lyrics": changed["section_lyrics"],
                   "updated_at": time.time()})
    projects.write_project(DATA_ROOT, record)
    return {"sections": changed["sections"],
            "pan_targets": changed["section_pan_automation"],
            "reverb_targets": changed["section_reverb_automation"],
            "width_targets": changed["section_width_automation"],
            "space_targets": changed["section_space_automation"],
            "eq_targets": changed["section_eq_automation"],
            "dynamics_targets": changed["section_dynamics_automation"],
            "gain_targets": changed["section_gain_automation"],
            "volume_targets": changed["section_volume_automation"],
            "stem_time_offsets": changed["stem_time_offsets"],
            "stem_echo_settings": changed["stem_echo_settings"],
            "echo_targets": changed["section_echo_automation"],
            "stem_groups": changed["stem_groups"],
            "section_group_targets": changed["section_group_targets"],
            "replacement_masks": changed["replacement_masks"],
            "auto_pan_targets": changed["section_auto_pan"],
            "ending": changed["section_ending"],
            "spatial_proposals": changed["section_spatial_proposals"],
            "imported_count": changed["imported_count"],
            "auto_distributed": changed["auto_distributed"],
            "end_terminator_ignored": changed["end_terminator_ignored"]}


@app.get("/api/projects/{ident}/lyrics/captions")
def export_lyric_captions(ident: str) -> dict[str, Any]:
    """Produce an estimated SRT from persisted lyric sections, never unsaved drafts."""
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song unavailable")
    import lyric_captions
    try:
        return lyric_captions.render_srt(record)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/projects/{ident}/sections/export")
def export_song_sections(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or not get_job(ident):
        raise HTTPException(404, "Song unavailable")
    return {"content": section_import.render_tags(record),
            "sections": record.get("sections", []),
            "spatial_proposals": record.get("section_spatial_proposals", {}),
            "section_lyrics": record.get("section_lyrics", {}),
            "section_production": record.get("section_production", {}),
            "reverb_targets": record.get("section_reverb_automation", []),
            "width_targets": record.get("section_width_automation", []),
            "space_targets": record.get("section_space_automation", []),
            "eq_targets": record.get("section_eq_automation", []),
            "dynamics_targets": record.get("section_dynamics_automation", []),
            "gain_targets": record.get("section_gain_automation", []),
            "volume_targets": record.get("section_volume_automation", []),
            "stem_time_offsets": record.get("stem_time_offsets", {}),
            "stem_echo_settings": record.get("stem_echo_settings", {}),
            "echo_targets": record.get("section_echo_automation", []),
            "stem_groups": record.get("stem_groups", []),
            "section_group_targets": record.get("section_group_targets", []),
            "replacement_masks": record.get("replacement_masks", []),
            "auto_pan_targets": record.get("section_auto_pan", []),
            "ending": record.get("section_ending", {"fade_seconds": 0, "tail_seconds": 0, "curve": "smooth"})}


class DawTargetRequest(BaseModel):
    target: str = "waveform"


class DawPathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=2048)


@app.get("/api/daws")
def daw_catalog() -> dict[str, Any]:
    return {"targets": [daw.target(item) for item in daw.TARGETS],
            "selected": daw.selected_target(APP_ROOT),
            "installed": {item: daw.resolve(APP_ROOT, target_id=item) for item in daw.TARGETS}}


@app.post("/api/daws/select")
def daw_select_target(body: DawTargetRequest, request: Request) -> dict[str, str]:
    require_local_origin(request)
    try:
        return {"selected": daw.select_target(APP_ROOT, body.target)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/daws/{target_id}/detect")
def daw_detect_target(target_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"executable": daw.resolve(APP_ROOT, target_id=target_id)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/daws/{target_id}/search")
def daw_search_target(target_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return daw.start_search(APP_ROOT, target_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/daws/search/{search_id}")
def daw_search_progress(search_id: str) -> dict[str, Any]:
    item = daw.search_status(search_id)
    if not item:
        raise HTTPException(404, "Discovery search no longer available")
    return item


@app.post("/api/daws/{target_id}/browse")
def daw_browse_target(target_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return {"path": daw.choose_executable("Locate " + daw.target(target_id)["name"] + " executable")}
    except (ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/daws/{target_id}/locate")
def daw_locate_target(target_id: str, body: DawPathRequest, request: Request) -> dict[str, str]:
    require_local_origin(request)
    try:
        return {"executable": daw.set_location(APP_ROOT, body.path, target_id)}
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/daws/{target_id}/launch")
def daw_launch_target(target_id: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        executable = daw.resolve(APP_ROOT, target_id=target_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not executable:
        return {"status": "setup_required", "target": target_id}
    try:
        subprocess.Popen([executable], cwd=str(Path(executable).parent),
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        raise HTTPException(400, f"Could not launch {daw.target(target_id)['name']}: {exc}") from exc
    return {"status": "started", "target": target_id}


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
        folder = projects.export_daw(DATA_ROOT, record, body.target)
        job["last_daw_export"] = str(folder)
        return {"target": body.target, "directory": str(folder), "message": "DAW stems ready"}
    except (OSError, ValueError) as exc:
        raise HTTPException(400, f"Could not prepare DAW files: {exc}") from exc
    finally:
        job["exporting_waveform"] = False


class ChannelSplitRequest(BaseModel):
    filenames: list[str] = Field(min_length=1, max_length=64)


@app.post("/api/projects/{ident}/channels/split")
def split_stereo_channels(ident: str, request: Request, body: ChannelSplitRequest) -> dict[str, Any]:
    """Export derived L/R mono WAV files; never replace source stems or an existing export."""
    require_local_origin(request)
    job = get_job(ident)
    record = projects.read_project(DATA_ROOT, ident) if job else None
    if not job or job.get("status") != "complete" or not record:
        raise HTTPException(409, "Complete a six-stem song before splitting stereo channels")
    with lock:
        if job.get("splitting_channels"):
            raise HTTPException(409, "A channel split is already running")
        job["splitting_channels"] = True
    try:
        folder = channel_split.split_stems(
            DATA_ROOT, record, body.filenames, dependency_tool("ffmpeg"),
            dependency_tool("ffprobe"))
        track_routing.attach(DATA_ROOT, record, folder, body.filenames)
        job["last_channel_split_export"] = str(folder)
        return {"directory": str(folder), "track_count": 2 * len(body.filenames),
                "message": "Mono left/right channel files exported; originals preserved"}
    except RuntimeError as exc:
        if "FFmpeg setup" in str(exc):
            raise HTTPException(409, str(exc)) from exc
        raise HTTPException(400, f"Channel split failed: {exc}") from exc
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(400, f"Channel split failed: {exc}") from exc
    finally:
        job["splitting_channels"] = False


class ChannelRoutingRequest(BaseModel):
    filename: str
    active: bool


@app.get("/api/projects/{ident}/channels")
def channel_tracks(ident: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    if not record or get_job(ident) is None:
        raise HTTPException(404, "Song unavailable")
    return {"channels": track_routing.valid_children(DATA_ROOT, record)}


@app.put("/api/projects/{ident}/channels")
def set_channel_routing(ident: str, body: ChannelRoutingRequest, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    record = projects.read_project(DATA_ROOT, ident)
    if not record or get_job(ident) is None:
        raise HTTPException(404, "Song unavailable")
    try:
        return {"channels": track_routing.switch(DATA_ROOT, record, body.filename, body.active)}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/projects/{ident}/channels/waveform/{filename}/{channel}")
def child_waveform(ident: str, filename: str, channel: str) -> dict[str, Any]:
    record = projects.read_project(DATA_ROOT, ident)
    job = get_job(ident)
    if not record or not job or job.get("status") != "complete":
        raise HTTPException(404, "Song unavailable")
    try:
        path = track_routing.child_path(DATA_ROOT, record, filename, channel)
        duration = job.get("source_duration_seconds") or probe_duration(path)
        return waveform_peaks.get_or_create(
            path, DATA_ROOT / "jobs" / ident / "waveforms" /
            (filename + "." + channel + "." + path.parent.name + ".json"),
            float(duration), dependency_tool("ffmpeg"))
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(400, f"Channel waveform unavailable: {exc}") from exc


@app.get("/api/projects/{ident}/channels/stream/{filename}/{channel}")
def stream_channel(ident: str, filename: str, channel: str):
    record = projects.read_project(DATA_ROOT, ident)
    if not record or get_job(ident) is None:
        raise HTTPException(404, "Song unavailable")
    try:
        path = track_routing.child_path(DATA_ROOT, record, filename, channel)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return FileResponse(path, media_type="audio/wav")


@app.post("/api/projects/{ident}/channels/open-folder")
def open_channel_split_folder(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    if not job or job.get("status") != "complete":
        raise HTTPException(404, "Completed song not found")
    root = DATA_ROOT / "jobs" / ident / "exports"
    candidates = sorted((p for p in root.glob("Channels-*") if p.is_dir()),
                        key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []
    if not candidates:
        raise HTTPException(404, "Split stereo channels first")
    if os.name != "nt":
        raise HTTPException(501, "Opening export folders requires Windows")
    os.startfile(str(candidates[0]))  # type: ignore[attr-defined]
    return {"status": "opened", "directory": str(candidates[0])}


class DawLaunchRequest(BaseModel):
    target: str = "waveform"
    directory: str = Field(min_length=1, max_length=4096)


@app.post("/api/projects/{ident}/daw/launch")
def daw_launch_project(ident: str, request: Request, body: DawLaunchRequest) -> dict[str, Any]:
    """Launch a validated, already-prepared song export in its selected editor."""
    require_local_origin(request)
    if body.target not in daw.TARGETS:
        raise HTTPException(400, "Unsupported DAW target")
    job = get_job(ident)
    if not job or job.get("status") != "complete":
        raise HTTPException(409, "Complete a song before DAW handoff")
    base = (DATA_ROOT / "jobs" / ident / "exports").resolve()
    folder = Path(body.directory).resolve()
    if folder.parent != base or not folder.is_dir():
        raise HTTPException(400, "Export folder does not belong to this song")
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HTTPException(400, "Reprepare stems: export manifest missing") from exc
    if manifest.get("source_project_id") != ident or manifest.get("target") != body.target:
        raise HTTPException(400, "Export does not match the selected song and DAW")
    executable = daw.resolve(APP_ROOT, target_id=body.target)
    if not executable:
        return {"status": "setup_required", "target": body.target}
    try:
        if body.target == "audacity":
            return audacity_handoff.launch_audacity(executable, folder)
        subprocess.Popen([executable], cwd=str(Path(executable).parent),
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return {"status": "started", "target": body.target,
                "message": "Waveform launched; import the six WAVs as separate tracks."}
    except (OSError, ValueError) as exc:
        raise HTTPException(400, f"Could not launch DAW: {exc}") from exc


@app.post("/api/projects/{ident}/daw/open-folder")
def daw_open_folder(ident: str, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    job = get_job(ident)
    if not job or job["status"] != "complete":
        raise HTTPException(409, "Select a completed song first")
    root = DATA_ROOT / "jobs" / ident / "exports"
    candidate = Path(job["last_daw_export"]) if job.get("last_daw_export") else None
    if not candidate or not candidate.is_dir() or root.resolve() not in candidate.resolve().parents:
        candidates = sorted((p for p in root.iterdir()
                             if p.is_dir() and (p.name.startswith("Waveform") or p.name.startswith("Audacity"))),
                            key=lambda p: p.stat().st_mtime, reverse=True) if root.is_dir() else []
        candidate = candidates[0] if candidates else None
    if candidate is None:
        return {"status": "export_required", "message": "Prepare DAW files first"}
    if os.name != "nt":
        raise HTTPException(501, "Opening folders requires Windows")
    os.startfile(str(candidate))  # type: ignore[attr-defined]
    return {"status": "opened", "directory": str(candidate)}


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
    stems: list[StemMixSetting] = Field(min_length=1, max_length=64)


def validate_mix(job: dict[str, Any], settings: list[StemMixSetting]) -> list[tuple[str, float]]:
    """Produce safe effective gains for every known source track."""
    known = set(job["files"])
    received = [setting.filename for setting in settings]
    if not known or len(received)!=len(known) or set(received)!=known or len(set(received))!=len(received):
        raise ValueError("Mix must contain each existing track exactly once")
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
    try:
        record = projects.read_project(DATA_ROOT, ident)
        if not record:
            raise ValueError("Saved project is needed to render")
        inputs = track_routing.audio_inputs(DATA_ROOT, record, body.stems)
        if not inputs:
            raise ValueError("No renderable audio tracks")
    except (ValueError, OSError, KeyError) as exc:
        job["rendering"] = False
        raise HTTPException(409, f"Cannot prepare mix: {exc}") from exc
    for path, _, _, _ in inputs:
        command.extend(["-i", str(path)])
    filters = []
    for index, (_, gain, channel, start) in enumerate(inputs):
        delay=f",adelay={round(start*1000)}|{round(start*1000)}" if start>0 else ""
        if channel == "left":
            filters.append(f"[{index}:a]pan=stereo|c0=c0|c1=0*c0,volume={gain:.6f}{delay}[s{index}]")
        elif channel == "right":
            filters.append(f"[{index}:a]pan=stereo|c0=0*c0|c1=c0,volume={gain:.6f}{delay}[s{index}]")
        else:
            filters.append(f"[{index}:a]volume={gain:.6f}{delay}[s{index}]")
    audio_links = "".join(f"[s{index}]" for index in range(len(inputs)))
    source_duration=resolved_song_duration(record,job)
    filters.append(f"{audio_links}amix=inputs={len(inputs)}:duration=longest:dropout_transition=0:normalize=0,atrim=duration={source_duration:.6f},alimiter=limit=0.98:level=0[mix]")
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


@app.get("/api/jobs/{ident}/waveform/{filename}")
def stem_waveform(ident: str, filename: str) -> dict[str, Any]:
    """Read-only cached overview; no media changes and no browser-size PCM arrays."""
    job = get_job(ident)
    if not job or job.get("status") != "complete" or filename not in job["files"]:
        raise HTTPException(404, "Stem unavailable")
    folder = DATA_ROOT / "jobs" / ident
    path = folder / "stems" / filename
    try:
        record=projects.read_project(DATA_ROOT,ident) or {}
        identity=next((row for row in record.get("source_tracks",[])
                       if row.get("working_filename")==filename),{})
        length = probe_duration(path) if identity.get("imported") else job.get("source_duration_seconds") or probe_duration(path)
        data=waveform_peaks.get_or_create(
            path, folder / "waveforms" / (filename + ".json"), float(length),
            dependency_tool("ffmpeg"))
        return {**data,"start_seconds":float(identity.get("start_seconds",0)),
                "clip_duration_seconds":float(length)}
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(400, f"Waveform unavailable: {exc}") from exc


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



# Managed local ACE runtime: start without model initialization, stop only owned PID.
import ace_service
import ace_locations

import ace_install

ACE_HOME = ace_locations.discover_installation(APP_ROOT) or (APP_ROOT / "ace-not-configured")
ace_manager = ace_service.AceServiceManager(
    ACE_HOME, log_directory=DATA_ROOT / "logs")
ace_installer = ace_install.Installer(ACE_HOME)


@app.get("/api/ace/models/install")
def ace_model_install_status() -> dict[str, Any]:
    return ace_installer.inspect()


@app.post("/api/ace/models/install/base")
def ace_model_install_base(request: Request) -> dict[str, Any]:
    """Explicit opt-in. Download only official Base into ACE's own checkpoint root."""
    require_local_origin(request)
    try:
        return ace_installer.install()
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.get("/api/ace/service")
def ace_service_status() -> dict[str, Any]:
    return ace_manager.status()


@app.post("/api/ace/service/start")
def ace_service_start(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return ace_manager.start()
    except ace_service.AceServiceError as exc:
        raise HTTPException(409, str(exc)) from exc


class AceModelRequest(BaseModel):
    model: str = Field(default="acestep-v15-turbo", min_length=1, max_length=100)


@app.post("/api/ace/service/initialize")
def ace_service_initialize(body: AceModelRequest, request: Request) -> dict[str, Any]:
    require_local_origin(request)
    try:
        return ace_manager.initialize_model(body.model)
    except ace_service.AceServiceError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/ace/service/stop")
def ace_service_stop(request: Request) -> dict[str, Any]:
    require_local_origin(request)
    # Do not terminate an in-flight candidate run.
    for record_path in (DATA_ROOT / "jobs").glob("*/generated/ace-candidates/*/candidate.json"):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            if record.get("state") in ("generating", "processing"):
                raise HTTPException(409, "ACE generation is active. Finish or cancel it before stopping ACE.")
        except (OSError, ValueError):
            continue
    try:
        return ace_manager.stop()
    except ace_service.AceServiceError as exc:
        raise HTTPException(409, str(exc)) from exc


# ACE accompaniment candidates are project-owned assets, not imported tracks.
# Runtime startup and model switching remain a separate, explicitly gated step.
import ace_adapter
import ace_candidates
import ace_transport
import ace_isolation


class AceCandidateRequest(BaseModel):
    from_section_id: str = Field(min_length=32, max_length=32)
    to_section_id: str = Field(min_length=32, max_length=32)
    context_before: float = Field(default=0, ge=0, le=240)
    context_after: float = Field(default=0, ge=0, le=240)
    model: str = Field(default="acestep-v15-turbo", max_length=100)
    prompt: str = Field(min_length=1, max_length=2000)
    seed: int = Field(default=150719, ge=0, le=4294967295)
    bpm: int | None = Field(default=None, ge=30, le=300)
    key: str = Field(default="", max_length=80)
    task_type: str = Field(default="cover", pattern="^(cover|lego)$")
    instrument: str = Field(default="", max_length=32)
    vocal_phrase: str = Field(default="", max_length=200)
    operation: str = Field(default="add", pattern="^(add|replace)$")


@app.get("/api/ace/discovery")
def ace_discovery() -> dict[str, Any]:
    return ace_adapter.AceClient().discover()


def _ace_project(ident: str) -> tuple[dict[str, Any], Path, Path]:
    project = projects.read_project(DATA_ROOT, ident)
    folder = DATA_ROOT / "jobs" / ident
    if not project:
        raise HTTPException(404, "Song Harbor project not found")
    original = folder / str(project.get("source_filename") or "")
    if not original.is_file() or original.resolve().parent != folder.resolve():
        raise HTTPException(409, "Project original recording is unavailable")
    return project, folder, original


def _run_ace_candidate(folder: Path, candidate_id: str, bpm: int | None, key: str) -> None:
    """Detached Song Harbor job; never writes a source-track manifest."""
    directory = ace_candidates.candidate_directory(folder, candidate_id)
    record = ace_candidates.load_record(folder, candidate_id)
    client = ace_adapter.AceClient(timeout=10)
    try:
        record["state"] = "generating"
        ace_candidates.save_record(directory, record)
        context = directory / record["context_file"]
        task_id = ace_transport.submit_instrument(
            client, context, record["model"], record["prompt"], record["seed"],
            bpm=bpm, key=key, duration=(record["samples"]["context_end"] -
            record["samples"]["context_start"]) / 48000,
            task_type=record["task_type"], track_name=record.get("instrument", ""),
            lyrics=record.get("vocal_phrase") or "[Instrumental]")
        record["ace_task_id"] = task_id
        ace_candidates.save_record(directory, record)
        # Poll for a bounded time; unknown ACE IDs are never considered success.
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            result = ace_transport.poll_cover(client, task_id)
            state = result["state"]
            if state == "ready":
                if not result["assets"]:
                    raise ace_adapter.AceError("ACE completed without an audio artifact")
                record["state"] = "processing"
                ace_candidates.save_record(directory, record)
                source = ace_transport.download_candidate(client, result["assets"][0],
                                                          directory / "generated.wav")
                ready = ace_candidates.crop_generated_candidate(folder, candidate_id, source,
                                                                 dependency_tool("ffmpeg"))
                if ready["task_type"] == "lego":
                    _audit_lego_isolation(folder, candidate_id)
                return
            if state in ("failed", "cancelled"):
                raise ace_adapter.AceError("ACE " + state + ": " +
                                           str(result.get("error") or result.get("stage") or "unknown"))
            time.sleep(1)
        raise ace_adapter.AceError("ACE candidate generation timed out")
    except Exception as exc:
        # Retain prepared context and metadata for debugging/retry.
        record = ace_candidates.load_record(folder, candidate_id)
        record["state"] = "failed"
        record["error"] = str(exc)[:500]
        ace_candidates.save_record(directory, record)


def _audit_lego_isolation(folder: Path, candidate_id: str) -> dict[str, Any]:
    directory = ace_candidates.candidate_directory(folder, candidate_id)
    record = ace_candidates.load_record(folder, candidate_id)
    if record.get("task_type") != "lego" or record.get("state") not in ("ready", "review_required"):
        raise ValueError("Only finished Lego candidates can be checked")
    bounds = record["samples"]
    duration = (bounds["context_end"] - bounds["context_start"]) / record["sample_rate_hz"]
    audit = ace_isolation.assess_context_leakage(
        dependency_tool("ffmpeg"),
        directory / record["context_file"],
        directory / "generated.wav", duration)
    record["source_similarity"] = audit
    if audit["status"] == "suspected_source_leakage":
        record["state"] = "review_required"
        record["error"] = ("Generated audio closely matches the source mix; "
                           "not suitable for acceptance as an isolated instrument.")
    elif audit["status"] == "not_detected":
        record["state"] = "ready"
        record.pop("error", None)
    else:
        record["state"] = "review_required"
        record["error"] = "Cannot verify the generated instrument is distinct from the backing."
    ace_candidates.save_record(directory, record)
    return record


@app.post("/api/projects/{ident}/ace/candidates/{candidate_id}/check-isolation")
def check_ace_candidate_isolation(ident: str, candidate_id: str,
                                  request: Request) -> dict[str, Any]:
    require_local_origin(request)
    _, folder, _ = _ace_project(ident)
    try:
        return _audit_lego_isolation(folder, candidate_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/projects/{ident}/ace/candidates")
def prepare_ace_candidate(ident: str, body: AceCandidateRequest,
                          request: Request) -> dict[str, Any]:
    require_local_origin(request)
    project, folder, original = _ace_project(ident)
    client = ace_adapter.AceClient()
    capabilities = client.discover()
    if capabilities["status"] != "connected":
        raise HTTPException(409, "ACE API is not connected; start ACE first")
    if not capabilities.get("ready") or capabilities.get("loaded_model") != body.model:
        raise HTTPException(409, "Selected ACE model must be loaded before generation")
    try:
        if body.operation != "add":
            raise ValueError("Instrument replacement is not enabled until regional A/B and undo are implemented")
        if body.task_type == "lego":
            import instrument_generation
            if body.instrument == "backing_vocals":
                raise ValueError("Backing-vocal Lego is temporarily disabled after a system freeze; resource preflight and emergency-stop recovery are required")
            else:
                instrument_generation.validate_intent("add", body.instrument, body.prompt, None, [])
            if body.model != "acestep-v15-base":
                raise ValueError("Native Lego requires ACE Base")
        elif body.model != "acestep-v15-turbo":
            raise ValueError("Experimental Cover requires ACE Turbo")
        record = ace_candidates.create_candidate(
            project, folder, original, body.from_section_id, body.to_section_id,
            body.context_before, body.context_after, body.model, body.prompt,
            body.task_type, capabilities, dependency_tool("ffmpeg"), body.seed)
        record["instrument"] = body.instrument if body.task_type == "lego" else ""
        record["vocal_phrase"] = body.vocal_phrase.strip() if body.task_type == "lego" and body.instrument == "backing_vocals" else ""
        record["operation"] = "add"
        ace_candidates.save_record(ace_candidates.candidate_directory(folder, record["candidate_id"]), record)
    except (ValueError, OSError, ace_adapter.AceError) as exc:
        raise HTTPException(400, str(exc)) from exc
    threading.Thread(target=_run_ace_candidate,
                     args=(folder, record["candidate_id"], body.bpm, body.key),
                     daemon=True).start()
    return record


@app.get("/api/projects/{ident}/ace/candidates")
def list_ace_candidates(ident: str) -> dict[str, Any]:
    """List durable candidates so a failed generation survives app relaunch."""
    _, folder, _ = _ace_project(ident)
    root = folder / "generated" / ace_candidates.CANDIDATE_FOLDER
    found = []
    for item in sorted(root.glob("*/candidate.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]:
        try:
            record = ace_candidates.load_record(folder, item.parent.name)
            found.append(record)
        except (ValueError, OSError, KeyError):
            continue
    return {"candidates": found}


@app.get("/api/projects/{ident}/ace/candidates/{candidate_id}")
def ace_candidate_status(ident: str, candidate_id: str) -> dict[str, Any]:
    _, folder, _ = _ace_project(ident)
    try:
        return ace_candidates.load_record(folder, candidate_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(404, "ACE candidate not found") from exc


@app.post("/api/projects/{ident}/ace/candidates/{candidate_id}/recover")
def recover_ace_candidate(ident: str, candidate_id: str, request: Request) -> dict[str, Any]:
    """Reprocess the preserved ACE WAV without rerunning costly generation."""
    require_local_origin(request)
    _, folder, _ = _ace_project(ident)
    try:
        directory = ace_candidates.candidate_directory(folder, candidate_id)
        with lock:
            record = ace_candidates.load_record(folder, candidate_id)
            if record.get("state") != "failed":
                raise HTTPException(409, "Only failed candidates can be recovered")
            source = directory / "generated.wav"
            if not source.is_file():
                raise HTTPException(409, "No generated audio was preserved for recovery")
            record["state"] = "processing"
            ace_candidates.save_record(directory, record)
        try:
            return ace_candidates.crop_generated_candidate(
                folder, candidate_id, source, dependency_tool("ffmpeg"))
        except Exception as exc:
            record = ace_candidates.load_record(folder, candidate_id)
            record["state"] = "failed"
            record["error"] = str(exc)[:500]
            ace_candidates.save_record(directory, record)
            raise HTTPException(400, str(exc)) from exc
    except (ValueError, OSError) as exc:
        raise HTTPException(404, "ACE candidate unavailable") from exc


@app.get("/api/projects/{ident}/ace/candidates/{candidate_id}/audio")
def ace_candidate_audio(ident: str, candidate_id: str):
    _, folder, _ = _ace_project(ident)
    try:
        record = ace_candidates.load_record(folder, candidate_id)
        if record.get("state") not in ("ready", "review_required"):
            raise HTTPException(409, "Candidate has not finished processing")
        path = ace_candidates.candidate_directory(folder, candidate_id) / "target.wav"
        if not path.is_file():
            raise HTTPException(404, "Candidate audio unavailable")
        return FileResponse(path, media_type="audio/wav")
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


class FrontendStaticFiles(StaticFiles):
    """Serve compiled modules with explicit MIME, independent of Windows registry.

    Python's mimetypes database can inherit machine-specific Windows mappings;
    browsers reject ES modules served as text/plain, even if the bytes are valid.
    """
    async def get_response(self, path: str, scope: dict[str, Any]):
        response = await super().get_response(path, scope)
        extension = Path(path).suffix.lower()
        if response.status_code == 200:
            if extension in (".js", ".mjs"):
                response.headers["content-type"] = "text/javascript; charset=utf-8"
            elif extension == ".css":
                response.headers["content-type"] = "text/css; charset=utf-8"
            # The build's JS/CSS filenames are content-hashed. Avoid caching a
            # stale module across updater relaunches and in-place UI rebuilds.
            response.headers["cache-control"] = "no-store"
        return response


# The installed build and API share ONE HTTP server. Vite is build-time only;
# no Vite proxy, hot-reload server, or fixed second port is needed to launch.
if UI_DIST.is_dir():
    assets = UI_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", FrontendStaticFiles(directory=str(assets)), name="ui-assets")


@app.get("/favicon.svg", include_in_schema=False)
def ui_favicon():
    icon=UI_DIST / "favicon.svg"
    if not icon.is_file():
        raise HTTPException(404,"Icon unavailable")
    return FileResponse(icon,media_type="image/svg+xml")


@app.get("/", include_in_schema=False)
def ui_index():
    index = UI_DIST / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Song Harbor UI has not been built. Relaunch to build the interface.")
    return FileResponse(index, media_type="text/html",
                        headers={"Cache-Control": "no-store"})


@app.get("/{route:path}", include_in_schema=False)
def ui_fallback(route: str):
    # Never turn a missing API endpoint into a successful HTML response.
    if route.startswith(("api/", "assets/")):
        raise HTTPException(404, "Not Found")
    if route and "." in Path(route).name:
        raise HTTPException(404, "Asset not found")
    return ui_index()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=APP_PORT)
