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
