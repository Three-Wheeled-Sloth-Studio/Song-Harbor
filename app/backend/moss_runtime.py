"""Explicit, optional local SGLang process lifecycle for registered MOSS checkpoints.

No auto-start, no downloads. Load is an intentional user action and runs
model-provided Python code ONLY with an explicit trusted-code acknowledgement.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
import json
import socket
import atexit
from pathlib import Path

import model_registry

LOCK = threading.RLock()
_ACTIVE = {"process": None, "id": None, "started_at": None, "error": "", "log": None, "model_name": None}
PORT = 18791
STARTUP_TIMEOUT_SECONDS = 180


def _probe(expected_name: str | None = None) -> bool:
    try:
        request = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/models")
        with urllib.request.urlopen(request, timeout=1.5) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read(1024 * 1024))
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                return False
            names = [str(item.get("id", "")) for item in payload["data"] if isinstance(item, dict)]
            return any(os.path.normcase(os.path.normpath(expected_name)) == os.path.normcase(os.path.normpath(name)) for name in names) if expected_name else bool(names)
    except (OSError, ValueError, urllib.error.URLError):
        return False


def status() -> dict:
    with LOCK:
        process = _ACTIVE["process"]
        if process is None:
            return {"status": "unloaded", "model_id": None, "error": _ACTIVE["error"]}
        code = process.poll()
        if code is not None:
            _ACTIVE["process"] = None
            _ACTIVE["error"] = f"ERROR: Model process stopped (exit {code}). Model not loaded. See .song-harbor/logs/moss-runtime.log."
            if _ACTIVE["log"] is not None:
                _ACTIVE["log"].close()
                _ACTIVE["log"] = None
            return {"status": "failed", "model_id": _ACTIVE["id"], "error": _ACTIVE["error"]}
        ready = _probe(_ACTIVE["model_name"])
        if not ready and time.time() - _ACTIVE["started_at"] > STARTUP_TIMEOUT_SECONDS:
            try:
                _stop_process(process)
            except Exception as exc:
                _ACTIVE["error"] = f"ERROR: Model startup timed out; shutdown failed: {exc}"
                return {"status": "failed", "model_id": _ACTIVE["id"], "error": _ACTIVE["error"]}
            _ACTIVE["process"] = None
            if _ACTIVE["log"] is not None:
                _ACTIVE["log"].close()
                _ACTIVE["log"] = None
            _ACTIVE["error"] = "ERROR: Model startup timed out after 180 seconds. Model not loaded."
            return {"status": "failed", "model_id": _ACTIVE["id"], "error": _ACTIVE["error"]}
        return {"status": "ready" if ready else "starting", "model_id": _ACTIVE["id"],
                "started_at": _ACTIVE["started_at"], "error": "",
                "port": PORT}


def load(app_root: Path, model_root: Path, identifier: str, python_executable: str,
         custom_code_approved: bool) -> dict:
    if not custom_code_approved:
        raise ValueError("ERROR: MOSS requires custom checkpoint code. Review and explicitly approve before loading.")
    if not Path(python_executable).is_absolute() or not Path(python_executable).is_file() or Path(python_executable).name.lower() not in ("python.exe", "python3.exe", "python"):
        raise ValueError("ERROR: Select an existing isolated SGLang Python executable. Model not loaded.")
    inventory = model_registry.list_models(app_root, model_root)["registered"]
    record = next((m for m in inventory if m["id"] == identifier), None)
    if record is None or record.get("status") != "present-unverified":
        raise ValueError("ERROR: Register a complete supported checkpoint before loading. Model not loaded.")
    with LOCK:
        if _ACTIVE["process"] is not None and _ACTIVE["process"].poll() is None:
            raise ValueError("ERROR: Unload the current model before loading another. Model not loaded.")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                raise ValueError(f"ERROR: Local port {PORT} already in use. Model not loaded.")
        probe = subprocess.run([python_executable, "-c", "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec(\'sglang\') else 2)"],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=12,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if probe.returncode != 0:
            raise ValueError("ERROR: SGLang is not installed in this Python environment. Model not loaded.")
        # Never allow Hugging Face to auto-fetch missing weights or code.
        env = os.environ.copy()
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["HF_HOME"] = str(model_root / ".song-harbor" / "hf-cache")
        env["HUGGINGFACE_HUB_CACHE"] = str(model_root / ".song-harbor" / "hf-cache" / "hub")
        env["XDG_CACHE_HOME"] = str(model_root / ".song-harbor" / "cache")
        env["TORCH_HOME"] = str(model_root / ".song-harbor" / "torch")
        logdir = model_root / ".song-harbor" / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        log = (logdir / "moss-runtime.log").open("ab")
        command = [python_executable, "-m", "sglang.launch_server", "--model-path", record["path"],
                   "--served-model-name", "songharbor-moss-" + identifier,
                   "--host", "127.0.0.1", "--port", str(PORT), "--trust-remote-code"]
        try:
            process = subprocess.Popen(command, cwd=str(model_root), env=env,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            log.close()
            raise
        _ACTIVE.update({"process": process, "id": identifier, "started_at": time.time(),
                        "error": "", "log": log, "model_name": "songharbor-moss-" + identifier})
    return status()


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, text=True, timeout=12)
        if result.returncode != 0 and process.poll() is None:
            raise RuntimeError("ERROR: Unable to stop Windows model process tree.")
    else:
        process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    if process.poll() is None:
        raise RuntimeError("ERROR: Model process is still running. Unload not confirmed.")


def cleanup_on_exit() -> None:
    with LOCK:
        proc = _ACTIVE["process"]
        if proc is not None:
            try:
                _stop_process(proc)
            except Exception:
                pass


atexit.register(cleanup_on_exit)

def unload() -> dict:
    with LOCK:
        process = _ACTIVE["process"]
        if process is None:
            return status()
        _stop_process(process)
        _ACTIVE["process"] = None
        _ACTIVE["id"] = None
        _ACTIVE["error"] = ""
        if _ACTIVE["log"] is not None:
            _ACTIVE["log"].close()
            _ACTIVE["log"] = None
        return {"status": "unloaded", "model_id": None, "error": ""}
