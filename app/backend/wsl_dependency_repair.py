"""Explicit repair of one known system dependency in an existing Ubuntu WSL distro.

Never launched on startup, and does not touch model weights or song projects.
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import app_logs
import wsl_model_bridge

_LOCK = threading.RLock()
_JOB = {"process": None, "log": None, "state": "idle", "distro": None, "error": ""}


def status() -> dict:
    with _LOCK:
        process = _JOB["process"]
        if process is not None and process.poll() is not None:
            code = process.returncode
            _JOB["process"] = None
            _JOB["state"] = "completed" if code == 0 else "failed"
            _JOB["error"] = "" if code == 0 else "ERROR: libnuma1 package install failed. See repair log."
            if _JOB["log"] is not None:
                _JOB["log"].close()
                _JOB["log"] = None
        return {"state": _JOB["state"], "distro": _JOB["distro"], "error": _JOB["error"]}


def start(app_root: Path, distro: str, approved: bool) -> dict:
    if not approved:
        raise ValueError("ERROR: Approval required to install libnuma1 in Ubuntu. No changes made.")
    wsl_model_bridge.validate_distro(distro)
    if not distro.lower().startswith("ubuntu"):
        raise ValueError("ERROR: Automatic libnuma1 repair currently supports Ubuntu WSL only.")
    check = wsl_model_bridge.libnuma_status(distro)
    if check["ready"]:
        return {"state": "completed", "distro": distro, "error": "", "already_present": True}
    if check["missing_package"] != "libnuma1":
        raise ValueError("ERROR: Missing libnuma1 was not confirmed. No package installed.")
    with _LOCK:
        if _JOB["process"] is not None and _JOB["process"].poll() is None:
            raise ValueError("ERROR: A WSL repair is already running. No duplicate operation.")
        log = app_logs.open_log(app_root, "moss-repair.log")
        # Fixed, allowlisted command. WSL root runs apt only after a user click.
        command = ["wsl.exe", "-d", distro, "-u", "root", "--exec",
                   "/usr/bin/apt-get", "install", "-y", "libnuma1"]
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            log.close()
            raise
        _JOB.update({"process": process, "log": log, "state": "running",
                     "distro": distro, "error": ""})
    return status()
