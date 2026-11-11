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
import wsl_model_bridge
import app_logs

LOCK = threading.RLock()
_ACTIVE = {"process": None, "id": None, "started_at": None, "error": "", "log": None, "model_name": None, "kind": None, "distro": None, "worker_state": None, "supervisor": None}
_ATTACHED = {"id": None, "model_name": None}
PORT = 18791
STARTUP_TIMEOUT_SECONDS = 900
_LOG_PATH: Path | None = None


def _runtime_log(app_root: Path, kind: str) -> Path:
    return app_logs.log_path(app_root, "moss-wsl.log" if kind == "wsl" else "moss-runtime.log")


def _tail(path: Path | None, limit: int = 5000) -> str:
    if path is None or not path.is_file():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(max(0, path.stat().st_size - limit))
            return handle.read().decode("utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def diagnostics() -> dict:
    with LOCK:
        path = _LOG_PATH
        return {"log_path": str(path) if path else None,
                "log_tail": _tail(path),
                "runtime_kind": _ACTIVE.get("kind"),
                "model_id": _ACTIVE.get("id")}



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
            if _ATTACHED["id"] is not None:
                if _probe(_ATTACHED["model_name"]):
                    return {"status": "connected", "model_id": _ATTACHED["id"], "external": True, "port": PORT, "error": ""}
                _ATTACHED.update({"id": None, "model_name": None})
                return {"status": "failed", "model_id": None, "error": "ERROR: External MOSS service disconnected."}
            if _ACTIVE["error"]:
                return {"status": "failed", "model_id": _ACTIVE["id"], "error": _ACTIVE["error"]}
            return {"status": "unloaded", "model_id": None, "error": ""}
        code = process.poll()
        if code is not None:
            if _ACTIVE.get("kind") == "wsl" and _ACTIVE.get("worker_state") is not None:
                try:
                    if _ACTIVE["worker_state"].is_file():
                        _stop_wsl_worker()
                except Exception as exc:
                    _ACTIVE["error"] = "ERROR: WSL launcher exited but child cleanup is unverified: " + str(exc)
                    return {"status": "failed", "model_id": _ACTIVE["id"], "error": _ACTIVE["error"]}
            _ACTIVE["process"] = None
            details = diagnostics()
            log_location = details["log_path"] or "unknown"
            causes = [text.strip() for text in details["log_tail"].splitlines()
                      if any(keyword in text.lower() for keyword in ("error:", "exception:", "out of memory", "oom", "killed"))]
            cause = (" Reason: " + causes[-1][:250]) if causes else " Open Failure details to inspect startup output."
            _ACTIVE["error"] = f"ERROR: MOSS exited with code {code}. Model not loaded. Log: {log_location}." + cause
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
            _ACTIVE["error"] = "ERROR: MOSS was not ready after 15 minutes. Owned worker shutdown requested. Model not loaded."
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
        if _ATTACHED["id"] is not None:
            raise ValueError("ERROR: Disconnect external MOSS before loading. Model not loaded.")
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
        global _LOG_PATH
        _LOG_PATH = _runtime_log(app_root, "native")
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log = _LOG_PATH.open("ab")
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
                        "error": "", "log": log, "model_name": "songharbor-moss-" + identifier, "kind": "native", "distro": None})
    return status()



def load_wsl(app_root: Path, model_root: Path, identifier: str, distro: str,
             python_path: str, custom_code_approved: bool) -> dict:
    """Start preinstalled WSL SGLang. Never install or download anything."""
    if not custom_code_approved:
        raise ValueError("ERROR: Approve checkpoint custom code before loading. Model not loaded.")
    records = model_registry.list_models(app_root, model_root)["registered"]
    record = next((item for item in records if item["id"] == identifier), None)
    if record is None or record.get("status") != "present-unverified":
        raise ValueError("ERROR: Register a complete checkpoint first. Model not loaded.")
    dependencies = wsl_model_bridge.libnuma_status(distro)
    if not dependencies["ready"]:
        if dependencies["missing_package"] == "libnuma1":
            raise ValueError("ERROR: Ubuntu is missing libnuma.so.1 (libnuma1). Use Repair dependency in MOSS, then retry. Model not loaded.")
        raise ValueError("ERROR: WSL system dependencies could not be verified. Model not loaded: " + dependencies["message"])
    wsl_model_bridge.preflight(distro, python_path)
    if record.get("storage") == "wsl":
        if record.get("distro") != distro:
            raise ValueError("ERROR: The checkpoint belongs to a different WSL distribution. Model not loaded.")
        linux_model = record["path"]
    else:
        linux_model = wsl_model_bridge.linux_path(distro, record["path"])
    linux_root = wsl_model_bridge.linux_path(distro, str(model_root))
    served = "songharbor-moss-" + identifier
    with LOCK:
        if _ATTACHED["id"] is not None or (_ACTIVE["process"] is not None and _ACTIVE["process"].poll() is None):
            raise ValueError("ERROR: Another model worker is active. Model not loaded.")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                raise ValueError("ERROR: Port 18791 is already in use. Model not loaded.")
        global _LOG_PATH
        _LOG_PATH = _runtime_log(app_root, "wsl")
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        log = _LOG_PATH.open("ab")
        cache = linux_root + "/.song-harbor"
        state = app_root / "logs" / "moss-wsl-worker.json"
        supervisor_file = Path(__file__).with_name("moss_wsl_supervisor.py")
        linux_supervisor = wsl_model_bridge.linux_path(distro, str(supervisor_file))
        linux_app_root = wsl_model_bridge.linux_path(distro, str(app_root))
        linux_state = linux_app_root + "/logs/moss-wsl-worker.json"
        if state.exists():
            raise ValueError("ERROR: Unresolved MOSS worker state exists. Inspect or unload it before a new load.")
        state.parent.mkdir(parents=True, exist_ok=True)
        command = ["wsl.exe", "-d", distro, "--exec", "python3",
                   linux_supervisor, "run", "--python", python_path,
                   "--model", linux_model, "--served", served,
                   "--port", str(PORT), "--cache", cache,
                   "--state", linux_state]
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            log.close()
            raise
        _ACTIVE.update({"process": process, "id": identifier, "started_at": time.time(),
                        "error": "", "log": log, "model_name": served,
                        "kind": "wsl", "distro": distro,
                        "worker_state": state, "supervisor": linux_supervisor})
    return status()


def _stop_wsl_worker() -> None:
    """Stop only the exact owned SGLang service identified by its served-model ID."""
    distro = _ACTIVE.get("distro")
    served = _ACTIVE.get("model_name")
    if not distro or not served or not served.startswith("songharbor-moss-"):
        raise RuntimeError("ERROR: Cannot safely identify the WSL worker to unload.")
    script = (
        "import os,signal,sys,time;"
        "needle=sys.argv[1].encode();"
        "targets=[];"
        "[(targets.append(int(d)) if d.isdigit() and int(d)!=os.getpid()"
        " and (lambda a: b'sglang.launch_server' in a and b'--served-model-name' in a and needle in a)"
        "(open('/proc/'+d+'/cmdline','rb').read().split(b'\\0')) else None)"
        " for d in os.listdir('/proc') if d.isdigit()"
        " and os.path.isfile('/proc/'+d+'/cmdline')];"
        "[(os.kill(p,signal.SIGTERM)) for p in targets];"
        "time.sleep(1);"
        "sys.exit(0)"
    )
    result = subprocess.run(["wsl.exe", "-d", distro, "--exec", "python3", "-c", script, served],
                            capture_output=True, text=True, timeout=12,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("ERROR: WSL worker shutdown command failed. Model not confirmed unloaded.")


def _stop_process(process: subprocess.Popen) -> None:
    if _ACTIVE.get("process") is process and _ACTIVE.get("kind") == "wsl":
        _stop_wsl_worker()
    if process.poll() is not None:
        if _ACTIVE.get("kind") == "wsl" and _probe(_ACTIVE.get("model_name")):
            raise RuntimeError("ERROR: WSL model endpoint remains active. Unload not confirmed.")
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
    if process.poll() is None or (_ACTIVE.get("kind") == "wsl" and _probe(_ACTIVE.get("model_name"))):
        raise RuntimeError("ERROR: Model process or service is still running. Unload not confirmed.")


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
            if _ATTACHED["id"] is not None:
                _ATTACHED.update({"id": None, "model_name": None})
                return {"status": "unloaded", "model_id": None, "external": True, "service_stopped": False, "error": ""}
            return status()
        _stop_process(process)
        _ACTIVE["process"] = None
        _ACTIVE["id"] = None
        _ACTIVE["error"] = ""
        if _ACTIVE["log"] is not None:
            _ACTIVE["log"].close()
            _ACTIVE["log"] = None
        return {"status": "unloaded", "model_id": None, "error": ""}


def attach(app_root: Path, model_root: Path, identifier: str) -> dict:
    """Connect to external localhost WSL service; never spawn or kill it."""
    registered = model_registry.list_models(app_root, model_root)["registered"]
    record = next((item for item in registered if item["id"] == identifier), None)
    if record is None or record.get("status") != "present-unverified":
        raise ValueError("ERROR: Register a complete MOSS checkpoint first. Model not connected.")
    expected = "songharbor-moss-" + identifier
    with LOCK:
        if _ACTIVE["process"] is not None and _ACTIVE["process"].poll() is None:
            raise ValueError("ERROR: Unload managed MOSS before connecting. Model not connected.")
        if _ATTACHED["id"] is not None:
            raise ValueError("ERROR: Disconnect current service first. Model not connected.")
        if not _probe(expected):
            raise ValueError("ERROR: No matching MOSS service at localhost:18791. Set --served-model-name " + expected + ". Model not connected.")
        _ATTACHED.update({"id": identifier, "model_name": expected})
    return status()
