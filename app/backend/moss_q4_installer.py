"""Explicit, resumable, checksum-verified CrispASR and MOSS Q4 installers.

The network operations run ONLY after the user approves a button in the MOSS
function. No execution of downloaded code happens during install. Models and
tools are staged below the user's configured shared model directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import moss_q4_experiment

RUNTIME_VERSION = "v0.8.53"
RUNTIME_ASSET = "crispasr-windows-x86_64-cuda126.zip"
RUNTIME_SHA256 = "0ea690630beaa358c7648a952c07f3266501e6daec774d48ea3995067beec13d"
RUNTIME_BYTES = 714327349
RUNTIME_URL = ("https://github.com/CrispStrobe/CrispASR/releases/download/"
               + RUNTIME_VERSION + "/" + RUNTIME_ASSET)
MODEL_REPO = "cstr/MOSS-Audio-4B-Instruct-GGUF"
MODEL_FILE = "moss-audio-4b-instruct-q4_k.gguf"
MODEL_API = "https://huggingface.co/api/models/" + MODEL_REPO + "?blobs=true"
MAX_MODEL_BYTES = 8 * 1024**3
_CHUNK = 1024 * 1024
_LOCK = threading.RLock()
_CANCEL = threading.Event()
_JOB = {"state": "idle", "kind": None, "message": "", "error": "",
        "downloaded": 0, "total": 0, "started": None, "artifact": "",
        "revision": None, "thread": None}


def _destination(model_root: Path, kind: str) -> Path:
    return ((model_root / "tools" / ("crispasr-" + RUNTIME_VERSION) / "crispasr.exe")
            if kind == "runtime" else model_root / "gguf" / MODEL_FILE)


def _manifest_path(model_root: Path, kind: str) -> Path:
    return ((model_root / "tools" / ("crispasr-" + RUNTIME_VERSION) / "song-harbor-install.json")
            if kind == "runtime" else model_root / "gguf" / "moss-q4-install.json")


def _read_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _installed(model_root: Path, kind: str) -> bool:
    manifest = _read_manifest(_manifest_path(model_root, kind))
    dest = _destination(model_root, kind)
    if not dest.is_file() or not manifest.get("verified"):
        return False
    if kind == "runtime":
        return manifest.get("archive_sha256") == RUNTIME_SHA256 and dest.stat().st_size > 0
    return (manifest.get("repo") == MODEL_REPO and manifest.get("file") == MODEL_FILE
            and isinstance(manifest.get("sha256"), str)
            and manifest.get("size") == dest.stat().st_size)


def _metadata() -> tuple[str, str, int, str]:
    request = urllib.request.Request(MODEL_API, headers={"User-Agent": "Song-Harbor-Q4"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(3 * 1024 * 1024 + 1)
    if len(raw) > 3 * 1024 * 1024:
        raise RuntimeError("Model metadata response too large.")
    data = json.loads(raw)
    revision = data.get("sha")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("Hugging Face revision cannot be pinned.")
    siblings = [item for item in data.get("siblings", []) if item.get("rfilename") == MODEL_FILE]
    if len(siblings) != 1:
        raise RuntimeError("Published Q4_K GGUF cannot be identified.")
    item = siblings[0]
    lfs = item.get("lfs") or {}
    digest = lfs.get("sha256") or item.get("blobId")
    size = item.get("size") or lfs.get("size")
    if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
        raise RuntimeError("Provider did not expose the model SHA-256. Download refused.")
    if not isinstance(size, int) or not (1024**3 < size <= MAX_MODEL_BYTES):
        raise RuntimeError("Q4 model size missing or unreasonable. Download refused.")
    url = "https://huggingface.co/" + MODEL_REPO + "/resolve/" + revision + "/" + MODEL_FILE
    return revision, digest, size, url


def _publish_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _status_unlocked(model_root: Path) -> dict:
    return {"state": _JOB["state"], "kind": _JOB["kind"],
            "message": _JOB["message"], "error": _JOB["error"],
            "downloaded_bytes": _JOB["downloaded"], "total_bytes": _JOB["total"],
            "started": _JOB["started"], "artifact": _JOB["artifact"],
            "revision": _JOB["revision"],
            "runtime_installed": _installed(model_root, "runtime"),
            "model_installed": _installed(model_root, "model"),
            "runtime_path": str(_destination(model_root, "runtime")),
            "model_path": str(_destination(model_root, "model")),
            "runtime_size_bytes": RUNTIME_BYTES, "model_size_bytes": 0}


def status(model_root: Path) -> dict:
    with _LOCK:
        return _status_unlocked(model_root)


def _set(**kwargs) -> None:
    with _LOCK:
        _JOB.update(kwargs)


def _cancelled() -> None:
    if _CANCEL.is_set():
        raise InterruptedError("Cancelled by user. Partial download retained for safe resume.")


def _download(url: str, path: Path, expected_size: int, digest: str) -> Path:
    """Resume only with HTTP 206 and complete SHA-256 validation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    if path.exists():
        raise RuntimeError("Installation destination already exists; nothing overwritten.")
    have = part.stat().st_size if part.exists() else 0
    if have > expected_size:
        raise RuntimeError("Existing partial file exceeds expected size. Nothing overwritten.")
    reserve = expected_size - have + (256 * 1024 * 1024)
    if shutil.disk_usage(path.parent).free < reserve:
        raise RuntimeError("Insufficient free disk space on shared model drive.")
    _set(downloaded=have, total=expected_size, message="Downloading and verifying")
    headers = {"User-Agent": "Song-Harbor-Q4/1.0", "Accept-Encoding": "identity"}
    if have:
        headers["Range"] = "bytes=" + str(have) + "-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response:
        if have and response.status != 206:
            raise RuntimeError("Server did not honor resume range; partial file preserved.")
        if have:
            range_header = response.headers.get("Content-Range", "")
            if not range_header.startswith("bytes " + str(have) + "-"):
                raise RuntimeError("Resume response range mismatch; nothing written.")
        elif response.status != 200:
            raise RuntimeError("Unexpected download response.")
        with part.open("ab" if have else "wb") as out:
            while True:
                _cancelled()
                chunk = response.read(_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                have += len(chunk)
                if have > expected_size:
                    raise RuntimeError("Download exceeded published size.")
                _set(downloaded=have)
    if have != expected_size:
        raise RuntimeError("Incomplete download; staged bytes retained for retry.")
    _set(message="Verifying SHA-256")
    sha = hashlib.sha256()
    with part.open("rb") as stream:
        while True:
            _cancelled()
            chunk = stream.read(4 * _CHUNK)
            if not chunk:
                break
            sha.update(chunk)
    if sha.hexdigest() != digest:
        raise RuntimeError("SHA-256 verification failed. Partial download retained for inspection.")
    return part


def _install_runtime(root: Path, downloaded: Path) -> None:
    destination = _destination(root, "runtime")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError("CrispASR installation already present. Nothing overwritten.")
    with zipfile.ZipFile(downloaded) as archive:
        entries = [x for x in archive.infolist() if not x.is_dir()]
        if len(entries) > 100 or sum(x.file_size for x in entries) > 2 * 1024**3:
            raise RuntimeError("CrispASR archive exceeds safe extraction bounds.")
        for info in entries:
            name = Path(info.filename.replace("\\", "/"))
            if (name.is_absolute() or ".." in name.parts or
                    (info.external_attr >> 16) & 0o170000 == 0o120000):
                raise RuntimeError("Unsafe ZIP entry; extraction refused.")
        exe = [x for x in entries if Path(x.filename).name.lower() == "crispasr.exe"]
        if len(exe) != 1:
            raise RuntimeError("CrispASR executable missing or ambiguous.")
        staging = destination.parent.with_name(destination.parent.name + ".installing")
        if staging.exists():
            raise RuntimeError("Existing runtime staging directory requires inspection.")
        staging.mkdir(parents=True)
        try:
            for info in entries:
                _cancelled()
                # Flatten common package root only; retain DLLs beside executable.
                relative = Path(*Path(info.filename.replace("\\", "/")).parts[1:]) if len(Path(info.filename.replace("\\", "/")).parts) > 1 else Path(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError("Unsafe relative installation path.")
                output = staging / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, output.open("wb") as target:
                    shutil.copyfileobj(src, target, _CHUNK)
            if not (staging / "crispasr.exe").is_file():
                raise RuntimeError("Expected CrispASR executable not found in installation staging.")
            _publish_json(staging / "song-harbor-install.json", {
                "verified": True, "version": RUNTIME_VERSION,
                "archive_sha256": RUNTIME_SHA256,
                "source": RUNTIME_URL})
            os.replace(staging, destination.parent)
        except Exception:
            # Keep staging for diagnostics; do not touch another installation.
            raise


def _run(root: Path, kind: str) -> None:
    try:
        if kind == "runtime":
            _set(total=RUNTIME_BYTES, revision=RUNTIME_VERSION)
            part = _download(RUNTIME_URL, root / "downloads" / RUNTIME_ASSET,
                             RUNTIME_BYTES, RUNTIME_SHA256)
            _set(message="Extracting verified CrispASR runtime")
            _install_runtime(root, part)
            part.unlink(missing_ok=True)
        else:
            revision, sha, size, url = _metadata()
            _set(total=size, revision=revision)
            destination = _destination(root, "model")
            part = _download(url, destination, size, sha)
            _cancelled()
            os.replace(part, destination)
            _publish_json(_manifest_path(root, "model"), {
                "verified": True, "repo": MODEL_REPO, "revision": revision,
                "file": MODEL_FILE, "size": size, "sha256": sha,
                "source": url})
        _set(state="completed", message="Verified installation complete", error="")
    except InterruptedError as exc:
        _set(state="cancelled", error="", message=str(exc))
    except Exception as exc:
        _set(state="failed", error="ERROR: " + str(exc), message="Installation failed")
    finally:
        _set(thread=None)


def start(root: Path, kind: str, approved: bool) -> dict:
    if kind not in ("runtime", "model"):
        raise ValueError("ERROR: Unsupported Q4 installation type.")
    if not approved:
        raise ValueError("ERROR: Approve this download explicitly. Nothing installed.")
    if os.name != "nt":
        raise ValueError("ERROR: Q4 installer requires Song Harbor on Windows.")
    if not root.is_dir():
        raise ValueError("ERROR: Shared model folder does not exist.")
    with _LOCK:
        if _JOB["thread"] is not None and _JOB["thread"].is_alive():
            raise ValueError("ERROR: Q4 download already running.")
        if _installed(root, kind) or _destination(root, kind).exists():
            raise ValueError("ERROR: Existing Q4 installation detected. Nothing overwritten.")
        _CANCEL.clear()
        _JOB.update(state="running", kind=kind, message="Checking published artifact",
                    error="", downloaded=0, total=0, started=time.time(),
                    artifact=RUNTIME_ASSET if kind == "runtime" else MODEL_FILE,
                    revision=None)
        thread = threading.Thread(target=_run, args=(root, kind), daemon=True,
                                  name="moss-q4-download-" + kind)
        _JOB["thread"] = thread
        thread.start()
        return _status_unlocked(root)


def cancel(root: Path) -> dict:
    with _LOCK:
        if _JOB["thread"] is not None and _JOB["thread"].is_alive():
            _CANCEL.set()
            _JOB["message"] = "Cancellation requested; finishing current network read"
        return _status_unlocked(root)
