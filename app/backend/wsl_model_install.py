"""Optional explicit WSL distro installation on a user-selected non-system drive.

Never invoked on startup or by discovery. No distro is overwritten or unregistered.
"""
from __future__ import annotations

import ntpath
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
import wsl_model_bridge

_LOCK = threading.RLock()
_JOB = {"process": None, "log": None, "state": "idle", "message": "", "destination": ""}
_DISTRO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def _destination(value: str) -> str:
    if not isinstance(value, str) or not value or not ntpath.isabs(value):
        raise ValueError("ERROR: Choose an absolute WSL installation folder. Installation not started.")
    normalized = ntpath.normpath(value)
    drive, tail = ntpath.splitdrive(normalized)
    system_drive = os.environ.get("SystemDrive", "C:").upper()
    if not drive or drive.upper() == system_drive or normalized == drive + "\\" or tail in ("", "\\"):
        raise ValueError("ERROR: Choose a dedicated folder on a non-system drive. Installation not started.")
    if Path(normalized).exists():
        raise ValueError("ERROR: Installation destination already exists. Choose a new empty folder.")
    return normalized


def status() -> dict:
    with _LOCK:
        p = _JOB["process"]
        if p is not None:
            code = p.poll()
            if code is None:
                return {"state": "installing", "destination": _JOB["destination"],
                        "message": "WSL installation in progress. No model downloaded by Song Harbor."}
            _JOB["state"] = "completed" if code == 0 else "failed"
            _JOB["message"] = ("Distribution installation finished. Detect WSL to verify it."
                               if code == 0 else "ERROR: WSL install command failed. Review installer log and Windows permissions.")
            _JOB["process"] = None
            log = _JOB["log"]
            if log:
                log.close()
                _JOB["log"] = None
        return {"state": _JOB["state"], "destination": _JOB["destination"],
                "message": _JOB["message"]}


def install(model_root: Path, distro: str, destination: str, approved: bool) -> dict:
    if not approved:
        raise ValueError("ERROR: Approve the WSL distribution installation and download explicitly.")
    if os.name != "nt" or not shutil.which("wsl.exe"):
        raise ValueError("ERROR: WSL command unavailable. Set up Windows WSL prerequisites first.")
    if not _DISTRO.fullmatch(distro):
        raise ValueError("ERROR: Invalid WSL distribution name. Installation not started.")
    # Restrict this initial installer to the official Ubuntu package.
    if distro != "Ubuntu":
        raise ValueError("ERROR: Only the official Ubuntu distribution is enabled for in-app installation.")
    path = _destination(destination)
    if distro in wsl_model_bridge.distros()["distros"]:
        raise ValueError("ERROR: Ubuntu already registered. Select the existing WSL distribution instead.")
    helper = subprocess.run(["wsl.exe", "--help"], capture_output=True, timeout=8,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    help_text = (helper.stdout.decode("utf-16-le", errors="replace") if b"\\x00" in helper.stdout else helper.stdout.decode(errors="replace"))
    if "--location" not in help_text:
        raise ValueError("ERROR: Installed WSL version does not support --location. Update WSL first; nothing installed.")
    with _LOCK:
        if _JOB["process"] is not None and _JOB["process"].poll() is None:
            raise ValueError("ERROR: Another WSL install is already running.")
        logdir = model_root / ".song-harbor" / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        log = (logdir / "wsl-install.log").open("ab")
        try:
            process = subprocess.Popen(["wsl.exe", "--install", "--distribution", distro,
                                        "--location", path, "--no-launch"],
                                       stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            log.close()
            raise
        _JOB.update({"process": process, "log": log, "state": "installing",
                     "message": "", "destination": path})
    return status()
