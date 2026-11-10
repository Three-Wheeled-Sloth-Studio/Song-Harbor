"""User-triggered WSL MOSS installation orchestrator. No implicit work on startup."""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import model_registry
import wsl_model_bridge

_LOCK = threading.RLock()
_JOB = {"process": None, "operation": None, "model": None, "distro": None,
        "log": None, "state": "idle", "error": ""}

CATALOG = [
    {"id": "moss-audio-4b", "name": "MOSS-Audio-4B-Instruct",
     "repo": "OpenMOSS-Team/MOSS-Audio-4B-Instruct", "license": "Apache-2.0",
     "fit": "Unverified on 12 GB GPU; smaller evaluation candidate"},
    {"id": "moss-music-8b", "name": "MOSS-Music-8B-Instruct",
     "repo": "OpenMOSS-Team/MOSS-Music-8B-Instruct", "license": "Apache-2.0",
     "fit": "8B unquantized likely exceeds 12 GB GPU; do not load without validated profile"},
]


def _log_tail(logfile: Path) -> str:
    try:
        with logfile.open("rb") as stream:
            stream.seek(max(0, logfile.stat().st_size - 2048))
            return stream.read().decode("utf-8", errors="replace")[-1200:]
    except OSError:
        return ""


def status(app_root: Path, model_root: Path, distro: str | None = None) -> dict:
    with _LOCK:
        process = _JOB["process"]
        if process is not None and process.poll() is not None:
            code = process.returncode
            _JOB["state"] = "finished" if code == 0 else "failed"
            _JOB["error"] = "" if code == 0 else "ERROR: MOSS setup failed. See job log for details."
            _JOB["process"] = None
            if _JOB["log"] is not None:
                _JOB["log"].close()
                _JOB["log"] = None
        state = _JOB["state"]
        name = _JOB["model"]
        operation = _JOB["operation"]
        active_distro = _JOB["distro"]
    found = []
    for item in CATALOG:
        folder = model_root / "checkpoints" / item["id"]
        manifest = folder / "song-harbor-install.json"
        installed = bool(manifest.is_file() and model_registry.inspect(folder))
        found.append({**item, "installed": installed, "path": str(folder) if installed else ""})
    runtime_found = (model_root / "runtime-manifest.json").is_file() and (model_root / "runtime").is_dir()
    python_path = ""
    if distro and runtime_found:
        try:
            linux_root = wsl_model_bridge.linux_path(distro, str(model_root))
            python_path = linux_root + "/runtime/bin/python"
        except (ValueError, OSError, subprocess.TimeoutExpired):
            pass
    logpath = model_root / ".song-harbor" / "logs" / "moss-setup.log"
    return {"state": state, "operation": operation, "model": name,
            "distro": active_distro, "runtime_installed": runtime_found,
            "runtime_python": python_path, "catalog": found,
            "error": _JOB["error"], "log_tail": _log_tail(logpath)}


def start(app_root: Path, model_root: Path, distro: str,
          operation: str, model: str | None, approved: bool) -> dict:
    if not approved:
        raise ValueError("ERROR: Approve the selected installation and network downloads. Nothing installed.")
    if operation not in ("runtime", "checkpoint"):
        raise ValueError("ERROR: Unsupported installation operation.")
    if operation == "checkpoint" and model not in {item["id"] for item in CATALOG}:
        raise ValueError("ERROR: Unsupported checkpoint selection.")
    if not model_root.is_dir():
        raise ValueError("ERROR: Configure an existing shared model directory on D: first.")
    wsl_model_bridge.validate_distro(distro)
    linux_root = wsl_model_bridge.linux_path(distro, str(model_root))
    script = wsl_model_bridge.linux_path(distro, str(Path(__file__).with_name("moss_setup_worker.py")))
    with _LOCK:
        if _JOB["process"] is not None and _JOB["process"].poll() is None:
            raise ValueError("ERROR: MOSS setup already running. No duplicate installation.")
        logdir = model_root / ".song-harbor" / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        log = (logdir / "moss-setup.log").open("ab")
        command = ["wsl.exe", "-d", distro, "--exec", "python3",
                   script, operation, linux_root, model or "none"]
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            log.close()
            raise
        _JOB.update({"process": process, "operation": operation, "model": model,
                     "distro": distro, "log": log, "state": "running", "error": ""})
    return status(app_root, model_root, distro)
