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
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

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
                            section_id: str | None = Form(None)) -> dict[str, Any]:
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
        for row in rows:
            if row.get("content_sha256")==digest and abs(float(row.get("start_seconds",0))-start_seconds)<.001:
                raise ValueError("This audio is already imported at the same timeline position")
        ffmpeg=dependency_tool("ffmpeg")
        command=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
                 "-i",str(original),"-map","0:a:0","-vn",
                 "-af","asetpts=PTS-STARTPTS",
                 "-ac","2","-ar","48000","-c:a","pcm_s24le","-f","wav",str(staging)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=360,
                              creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode or not staging.is_file() or staging.stat().st_size<44:
            raise ValueError("Audio conversion failed: "+(result.stderr or "")[-300:])
        os.replace(staging,final)
        updated=track_lifecycle.ensure_identities(record)
        if len(updated)>=stem_import.MAX_TRACKS:raise ValueError("Maximum 64 source tracks")
        updated.append({"track_id":track_id,"original_filename":original.name,
                        "working_filename":final_name,"stem_alias":stem_alias,
                        "display_name":display_name.strip(),"imported":True,
                        "start_seconds":round(float(start_seconds),3),
                        "duration_seconds":round(probe_duration(final),3),
                        "content_sha256":digest})
        record["source_tracks"]=updated
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
        return {"project":record,"job":snapshot(job)}
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
    width: int = Field(ge=0, le=150)
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

ACE_HOME = Path(os.environ.get("SONG_HARBOR_ACE_HOME", r"D:\\Apps\\Tools\\ACE-Step-1.5"))
ace_manager = ace_service.AceServiceManager(
    ACE_HOME, log_directory=DATA_ROOT / "logs")


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
        task_id = ace_transport.submit_cover(
            client, context, record["model"], record["prompt"], record["seed"],
            bpm=bpm, key=key, duration=record["samples"]["context_end"] / 48000 -
            record["samples"]["context_start"] / 48000)
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
                ace_candidates.crop_generated_candidate(folder, candidate_id, source,
                                                        dependency_tool("ffmpeg"))
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
        record = ace_candidates.create_candidate(
            project, folder, original, body.from_section_id, body.to_section_id,
            body.context_before, body.context_after, body.model, body.prompt,
            "cover", capabilities, dependency_tool("ffmpeg"), body.seed)
    except (ValueError, OSError, ace_adapter.AceError) as exc:
        raise HTTPException(400, str(exc)) from exc
    threading.Thread(target=_run_ace_candidate,
                     args=(folder, record["candidate_id"], body.bpm, body.key),
                     daemon=True).start()
    return record


@app.get("/api/projects/{ident}/ace/candidates/{candidate_id}")
def ace_candidate_status(ident: str, candidate_id: str) -> dict[str, Any]:
    _, folder, _ = _ace_project(ident)
    try:
        return ace_candidates.load_record(folder, candidate_id)
    except (ValueError, OSError) as exc:
        raise HTTPException(404, "ACE candidate not found") from exc


@app.get("/api/projects/{ident}/ace/candidates/{candidate_id}/audio")
def ace_candidate_audio(ident: str, candidate_id: str):
    _, folder, _ = _ace_project(ident)
    try:
        record = ace_candidates.load_record(folder, candidate_id)
        if record.get("state") != "ready":
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
