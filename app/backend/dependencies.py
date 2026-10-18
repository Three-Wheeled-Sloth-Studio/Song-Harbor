"""User-owned FFmpeg dependency discovery, verified installation and persisted paths.

Windows-first local service. No shell PATH modifications, no admin privileges and no
software downloads without an explicit user request. Both ffmpeg and ffprobe are
validated and saved in Song Harbor's user configuration.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.request
import uuid
import zipfile
from pathlib import Path

ARCHIVE_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
CHECKSUM_URL = ARCHIVE_URL + ".sha256"
MAX_ARCHIVE_BYTES = 650 * 1024 * 1024
jobs: dict[str, dict] = {}
install_lock = threading.Lock()


def config_file(root: Path) -> Path:
    return root / "config" / "settings.json"


def load_config(root: Path) -> dict:
    path = config_file(root)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def save_binary(root: Path, directory: Path) -> dict:
    paths = verify_pair(directory)
    if not paths:
        raise ValueError("Folder must contain working ffmpeg.exe and ffprobe.exe (directly or in bin)")
    settings = load_config(root)
    settings["ffmpeg"] = {
        "bin_directory": str(paths["directory"]),
        "source": "configured",
    }
    target = config_file(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                     suffix=".tmp", delete=False) as f:
        json.dump(settings, f, indent=2)
        temp_name = f.name
    os.replace(temp_name, target)
    return paths


def verify_pair(folder: Path) -> dict | None:
    folder = folder.expanduser()
    if folder.is_file():
        folder = folder.parent
    candidates = [folder, folder / "bin"]
    for parent in candidates:
        ffmpeg = parent / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        ffprobe = parent / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if not (ffmpeg.is_file() and ffprobe.is_file()):
            continue
        try:
            for tool in (ffmpeg, ffprobe):
                checked = subprocess.run(
                    [str(tool), "-version"], capture_output=True, text=True,
                    timeout=8, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if checked.returncode != 0 or "ffmpeg" not in checked.stdout.lower() and "ffprobe" not in checked.stdout.lower():
                    raise ValueError("Executable version probe failed")
            return {"directory": parent.resolve(), "ffmpeg": ffmpeg.resolve(), "ffprobe": ffprobe.resolve()}
        except (OSError, subprocess.TimeoutExpired, ValueError):
            continue
    return None


def likely_locations(root: Path) -> list[Path]:
    candidates: list[Path] = []
    configured = load_config(root).get("ffmpeg", {})
    if isinstance(configured, dict) and configured.get("bin_directory"):
        candidates.append(Path(configured["bin_directory"]))
    for name in ("ffmpeg", "ffprobe"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found).parent)
    local = [
        root / "tools" / "ffmpeg", root / "ffmpeg",
        root.parent / "ffmpeg", root.parent / "tools" / "ffmpeg",
        Path.home() / "scoop" / "apps" / "ffmpeg" / "current",
        Path.home() / "scoop" / "apps" / "ffmpeg-essentials" / "current",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "ffmpeg",
        Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Microsoft" / "WinGet" / "Links",
    ]
    candidates.extend(local)
    return list(dict.fromkeys(candidates))


def resolve(root: Path, save_discovered: bool = True) -> dict | None:
    for candidate in likely_locations(root):
        pair = verify_pair(candidate)
        if pair:
            if save_discovered:
                saved = load_config(root).get("ffmpeg", {}).get("bin_directory")
                if saved != str(pair["directory"]):
                    save_binary(root, pair["directory"])
            return {key: str(value) for key, value in pair.items()}
    return None


def search(root: Path) -> list[dict]:
    """Bounded, opt-in search of common install locations and work drives."""
    found: list[dict] = []
    seen: set[str] = set()
    roots = [root, root.parent, Path.home() / "scoop", Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet"]
    if os.name == "nt":
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        for index in range(26):
            if mask & (1 << index):
                drive = Path(chr(65 + index) + ":\\")
                roots.extend([drive / "Apps", drive / "Tools", drive / "Program Files"])
    roots.extend(likely_locations(root))
    checked = 0
    for base in roots:
        if not base.is_dir():
            continue
        for current, dirs, _ in os.walk(base):
            checked += 1
            # Avoid inspecting huge arbitrary trees and user documents.
            dirs[:] = [d for d in dirs if d.lower() not in {
                ".git", "node_modules", ".venv", "cache", "temp", "windows", "system32",
                "users", "documents", "downloads", "models", "data", "$recycle.bin"
            } and not d.startswith(".")][:80]
            pair = verify_pair(Path(current))
            if pair and str(pair["directory"]).lower() not in seen:
                seen.add(str(pair["directory"]).lower())
                found.append({key: str(value) for key, value in pair.items()})
            if checked >= 12000 or len(found) >= 16:
                break
        if checked >= 12000 or len(found) >= 16:
            break
    return found


def browse() -> str | None:
    if os.name != "nt":
        raise RuntimeError("Native folder picker currently requires Windows")
    import tkinter
    from tkinter import filedialog
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(title="Select FFmpeg folder (contains bin\\ffmpeg.exe and bin\\ffprobe.exe)")
        return selected or None
    finally:
        root.destroy()


def install(root: Path, target_directory: Path, job: dict) -> None:
    try:
        # Must be a user-selected folder. Do not overwrite existing installations.
        if os.name != "nt":
            raise RuntimeError("Automatic FFmpeg installation currently supports Windows only")
        if target_directory.exists() and any(target_directory.iterdir()):
            existing = verify_pair(target_directory)
            if existing:
                save_binary(root, existing["directory"])
                job.update(status="complete", message="Existing installation located and configured")
                return
            raise ValueError("The installation folder is not empty. Choose a new/empty folder or locate an existing installation.")
        job.update(status="running", message="Downloading FFmpeg archive and checksum")
        # Download from official publisher endpoint, then SHA-256 verify before unpacking.
        with urllib.request.urlopen(CHECKSUM_URL, timeout=30) as response:
            expected_content = response.read(4096).decode("utf-8").strip()
        match = re.search(r"\b[a-fA-F0-9]{64}\b", expected_content)
        if not match:
            raise ValueError("Unable to read publisher SHA-256 checksum")
        expected_hash = match.group(0).lower()
        with tempfile.TemporaryDirectory(prefix="songharbor-ffmpeg-") as tmp:
            archive = Path(tmp) / "ffmpeg.zip"
            hasher = hashlib.sha256()
            size = 0
            with urllib.request.urlopen(ARCHIVE_URL, timeout=90) as response, archive.open("wb") as dest:
                length_header = response.headers.get("Content-Length")
                total_bytes = int(length_header) if length_header and length_header.isdigit() else 0
                if total_bytes > MAX_ARCHIVE_BYTES:
                    raise ValueError("FFmpeg archive exceeded safety limit")
                job.update(phase="download", downloaded_bytes=0, total_bytes=total_bytes or None, progress_percent=0 if total_bytes else None)
                while data := response.read(1024 * 1024):
                    size += len(data)
                    if size > MAX_ARCHIVE_BYTES:
                        raise ValueError("FFmpeg archive exceeded safety limit")
                    hasher.update(data)
                    dest.write(data)
                    job["downloaded_bytes"] = size
                    if total_bytes:
                        job["progress_percent"] = min(99, round(size / total_bytes * 100))
                        job["message"] = f"Downloading FFmpeg ({size // 1048576} / {total_bytes // 1048576} MiB)"
                    else:
                        job["message"] = f"Downloading FFmpeg ({size // 1048576} MiB)"
            if hasher.hexdigest() != expected_hash:
                raise ValueError("Publisher SHA-256 verification failed; archive rejected")
            job.update(phase="extract", progress_percent=None, message="Verified download; extracting FFmpeg and FFprobe")
            target_directory.mkdir(parents=True, exist_ok=True)
            binaries = {}
            with zipfile.ZipFile(archive) as zf:
                for entry in zf.infolist():
                    if entry.is_dir():
                        continue
                    name = entry.filename.replace("\\", "/").lower()
                    basename = name.rsplit("/", 1)[-1]
                    if basename in ("ffmpeg.exe", "ffprobe.exe") and "/bin/" in name:
                        if entry.file_size > 250 * 1024 * 1024:
                            raise ValueError("Unexpected executable size")
                        binaries[basename] = entry
                if len(binaries) != 2:
                    raise ValueError("Archive did not contain FFmpeg and FFprobe")
                bindir = target_directory / "bin"
                bindir.mkdir(exist_ok=True)
                for name, entry in binaries.items():
                    with zf.open(entry) as source, (bindir / name).open("wb") as dest:
                        shutil.copyfileobj(source, dest)
            pair = save_binary(root, target_directory)
            job.update(status="complete", phase="complete", progress_percent=100, message=f"FFmpeg configured: {pair['directory']}")
    except Exception as exc:
        job.update(status="error", message=str(exc))
    finally:
        install_lock.release()


def start_install(root: Path, directory: str) -> dict:
    if not directory or not Path(directory).is_absolute():
        raise ValueError("Select an absolute installation folder")
    target = Path(directory).expanduser().resolve()
    if str(target) in (str(Path(target.anchor)), str(root), str(Path.home())):
        raise ValueError("Select a dedicated FFmpeg subfolder, not a drive, work root or home directory")
    if not install_lock.acquire(blocking=False):
        raise ValueError("An FFmpeg installation is already running")
    key = uuid.uuid4().hex[:12]
    job = {"id": key, "status": "queued", "phase": "prepare", "progress_percent": None, "message": "Preparing installation"}
    jobs[key] = job
    threading.Thread(target=install, args=(root, target, job), daemon=True).start()
    return job.copy()
