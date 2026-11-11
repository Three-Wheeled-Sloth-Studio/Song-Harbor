"""Read-only WSL2 discovery and safe argument assembly for the optional MOSS worker.

No installs, distro creation, downloads, model loads, or user-supplied shell commands.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

_DISTRO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
_TIMEOUT = 8


def _run(args: list[str], timeout: int = _TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, errors="replace",
                          stdin=subprocess.DEVNULL, timeout=timeout,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def distros() -> dict:
    if os.name != "nt" or not shutil.which("wsl.exe"):
        return {"available": False, "distros": [], "message": "WSL is unavailable on this host."}
    try:
        # --list --quiet may emit UTF-16LE on some Windows builds.
        result = subprocess.run(["wsl.exe", "--list", "--quiet"], capture_output=True,
                                stdin=subprocess.DEVNULL, timeout=_TIMEOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        raw = result.stdout
        decoded = raw.decode("utf-16-le", errors="replace") if b"\x00" in raw else raw.decode(errors="replace")
        names = [name.strip().replace("\ufeff", "") for name in decoded.splitlines()]
        names = list(dict.fromkeys(name for name in names if _DISTRO.fullmatch(name)))
        if result.returncode:
            return {"available": True, "distros": [], "message": "WSL installed but distribution discovery failed."}
        return {"available": True, "distros": names, "message": "" if names else "No registered Linux distributions."}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": True, "distros": [], "message": "WSL discovery timed out or failed."}


def validate_distro(name: str) -> str:
    if not isinstance(name, str) or not _DISTRO.fullmatch(name):
        raise ValueError("ERROR: Invalid WSL distribution. Model not loaded.")
    if name not in distros()["distros"]:
        raise ValueError("ERROR: WSL distribution not found. Model not loaded.")
    return name


def linux_path(distro: str, windows_path: str) -> str:
    validate_distro(distro)
    candidate = Path(windows_path)
    if not candidate.is_absolute() or not candidate.exists():
        raise ValueError("ERROR: Model path does not exist on Windows. Model not loaded.")
    result = _run(["wsl.exe", "-d", distro, "--exec", "wslpath", "-a", "-u", str(candidate)])
    translated = result.stdout.strip()
    if result.returncode or not translated.startswith("/"):
        raise ValueError("ERROR: Cannot access model folder from WSL. Model not loaded.")
    return translated


def discover_runtime(distro: str) -> dict:
    validate_distro(distro)
    # Only fixed commands; no shell text from the user.
    result = _run(["wsl.exe", "-d", distro, "--exec", "sh", "-c",
                   'command -v python3; command -v nvidia-smi; test -x "$HOME/.venv/bin/python" && echo "$HOME/.venv/bin/python"; true'], timeout=12)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("/")]
    lines = sorted(set(lines), key=lambda item: ("/.venv/" not in item, item))
    return {"distro": distro, "python_candidates": lines[:6], "probe_ok": result.returncode == 0,
            "gpu_visible": "nvidia-smi" in result.stdout,
            "message": "" if result.returncode == 0 else "WSL runtime probe incomplete."}


def preflight(distro: str, python_path: str) -> None:
    validate_distro(distro)
    if not isinstance(python_path, str) or not python_path.startswith("/") or any(c in python_path for c in "\r\n\x00"):
        raise ValueError("ERROR: Select an absolute Linux Python executable. Model not loaded.")
    check = _run(["wsl.exe", "-d", distro, "--exec", python_path, "-c",
                  "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('sglang') else 2)"], timeout=15)
    if check.returncode:
        raise ValueError("ERROR: SGLang is unavailable in the selected WSL Python environment. Model not loaded.")


def inspect_checkpoint(distro: str, linux_folder: str) -> dict | None:
    """Read only model metadata and shard presence inside an existing WSL directory."""
    validate_distro(distro)
    if not isinstance(linux_folder, str) or not linux_folder.startswith("/") or any(c in linux_folder for c in "\r\n\x00"):
        raise ValueError("ERROR: Enter an absolute Linux model directory. Model not registered.")
    script = """
import json,sys
from pathlib import Path
p=Path(sys.argv[1]).expanduser().resolve()
cfg=p/'config.json'
if not p.is_dir() or not cfg.is_file() or cfg.is_symlink() or cfg.stat().st_size>1048576: sys.exit(3)
data=json.loads(cfg.read_text())
if not isinstance(data,dict): sys.exit(3)
type_text=' '.join(str(data.get(k,'')) for k in ('model_type','architectures','auto_map')).lower()
family=('moss_music' if any(x in type_text for x in ('moss_music','moss-music','mossmusic')) else
        'moss_audio' if any(x in type_text for x in ('moss_audio','moss-audio','mossaudio')) else None)
if not family: sys.exit(3)
index=p/'model.safetensors.index.json'
if index.is_file() and not index.is_symlink() and index.stat().st_size<4194304:
    files=list(set(json.loads(index.read_text())['weight_map'].values()))
else:
    files=['model.safetensors'] if (p/'model.safetensors').is_file() else []
if not files or len(files)>64 or any(not isinstance(n,str) or Path(n).name!=n or not n.endswith('.safetensors') for n in files): sys.exit(3)
complete=all((p/n).is_file() and not (p/n).is_symlink() for n in files)
print(json.dumps({'path':str(p),'name':p.name,'family':family,'status':'present-unverified' if complete else 'incomplete','files':len(files),'bytes_present':sum((p/n).stat().st_size for n in files if (p/n).is_file())}))
"""
    result = _run(["wsl.exe", "-d", distro, "--exec", "python3", "-c", script, linux_folder], timeout=15)
    if result.returncode:
        return None
    try:
        value = __import__("json").loads(result.stdout)
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


def libnuma_status(distro: str) -> dict:
    """Check loader presence without importing GPU extensions or starting inference."""
    validate_distro(distro)
    result = _run(["wsl.exe", "-d", distro, "--exec", "python3", "-c",
                   "import ctypes; ctypes.CDLL('libnuma.so.1')"], timeout=12)
    if result.returncode == 0:
        return {"ready": True, "missing_package": None, "message": "libnuma.so.1 available"}
    # An unrelated Python/WSL failure is not evidence that libnuma is missing.
    details = (result.stderr or "") + (result.stdout or "")
    if "libnuma.so.1" in details and ("No such file" in details or "cannot open shared object" in details):
        return {"ready": False, "missing_package": "libnuma1",
                "message": "Missing Ubuntu library libnuma.so.1 (package libnuma1)."}
    return {"ready": False, "missing_package": None,
            "message": "WSL dependency probe failed; check WSL Python before loading."}
