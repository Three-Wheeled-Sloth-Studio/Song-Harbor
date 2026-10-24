"""Explicit, non-destructive ACE checkpoint installation.

Downloads only a user-approved, allowlisted model into ACE native checkpoint
root, not Song Harbor model storage. Never changes ACE running model.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

MODEL = "acestep-v15-base"
REPOSITORY = "ACE-Step/acestep-v15-base"
MIN_FREE_BYTES = 9 * 1024**3

def checkpoint_root(installation: Path, environment: dict[str,str] | None = None) -> Path:
    env = environment if environment is not None else os.environ
    value = env.get("ACESTEP_CHECKPOINTS_DIR", "").strip()
    if not value:
        dotenv = installation / ".env"
        if dotenv.is_file():
            for line in dotenv.read_text(encoding="utf-8-sig").splitlines():
                row = line.strip()
                if row.startswith("export "): row = row[7:].strip()
                if row.startswith("ACESTEP_CHECKPOINTS_DIR="):
                    value = row.split("=", 1)[1].strip().strip(chr(34)).strip(chr(39))
                    break
    if not value:
        return (installation / "checkpoints").resolve()
    path = Path(os.path.expandvars(os.path.expanduser(value)))
    return (path if path.is_absolute() else installation / path).resolve()

def model_complete(folder: Path) -> bool:
    config = folder / "config.json"
    if not config.is_file(): return False
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if data.get("is_turbo") is not False: return False
    return any(folder.glob("*.safetensors"))

class Installer:
    def __init__(self, ace_home: Path):
        self.ace_home = ace_home.resolve()
        self.lock = threading.Lock()
        self.state: dict[str,Any] = {"phase":"idle","model":MODEL,"error":None}
        self.thread: threading.Thread | None = None

    def inspect(self) -> dict[str,Any]:
        root = checkpoint_root(self.ace_home)
        with self.lock:
            return {**self.state, "checkpoint_root":str(root),
                    "installed":model_complete(root / MODEL),
                    "running":bool(self.thread and self.thread.is_alive())}

    def install(self) -> dict[str,Any]:
        root = checkpoint_root(self.ace_home)
        target = root / MODEL
        python = self.ace_home / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.is_file() or not (self.ace_home / "acestep" / "api_server.py").is_file():
            raise ValueError("ACE installation must be configured before downloading models")
        if model_complete(target):
            return self.inspect()
        if target.exists():
            raise ValueError("Base checkpoint directory already exists but is incomplete. Preserve it for recovery; installation did not overwrite it.")
        if not root.parent.is_dir():
            raise ValueError("ACE checkpoint parent directory is missing")
        if shutil.disk_usage(root.parent).free < MIN_FREE_BYTES:
            raise ValueError("At least 9 GiB free space is required before installing ACE Base")
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError("ACE model installation already running")
            self.state = {"phase":"downloading","model":MODEL,"error":None}
            self.thread = threading.Thread(target=self._worker,args=(python,root,target),daemon=True)
            self.thread.start()
        return self.inspect()

    def _worker(self, python: Path, root: Path, target: Path) -> None:
        staging = root / (".songharbor-"+MODEL+"-"+uuid.uuid4().hex[:12])
        # Fixed code, fixed repository, no shell or user-controlled Python.
        script = ("import sys; from huggingface_hub import snapshot_download; "
                  "snapshot_download(repo_id=sys.argv[1], local_dir=sys.argv[2])")
        try:
            root.mkdir(parents=True,exist_ok=True)
            cmd = [str(python),"-c",script,REPOSITORY,str(staging)]
            with (root / ".songharbor-ace-install.log").open("ab") as log:
                result = subprocess.run(cmd,cwd=str(self.ace_home),stdin=subprocess.DEVNULL,
                    stdout=log,stderr=subprocess.STDOUT,timeout=7200,check=False,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if result.returncode != 0:
                raise RuntimeError("ACE Base download failed; check install log in checkpoint directory")
            if not model_complete(staging):
                raise RuntimeError("Downloaded checkpoint failed config/weights validation")
            if target.exists():
                raise RuntimeError("ACE Base destination appeared during download; refusing overwrite")
            staging.rename(target)
            with self.lock:
                self.state={"phase":"installed","model":MODEL,"error":None}
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            with self.lock:
                self.state={"phase":"failed","model":MODEL,"error":str(exc)[:400]}
        finally:
            # Preserve incomplete staged files for diagnostics/recovery.
            pass
