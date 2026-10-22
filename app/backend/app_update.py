"""Windows local-first self-update entrypoint. Never writes project/media files."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any



def local_version(repository: Path) -> dict[str, str]:
    """Human-readable Version:Revision:Build identifier, with Git details for support.

    Version comes from the frontend package. Revision is the product's current
    development revision (1); build is the monotonically increasing Git history
    count within the checked-out branch. Never show a bare hash as the badge.
    """
    import json
    version = "0.1.0"
    manifest = repository / "app" / "frontend" / "package.json"
    try:
        version = str(json.loads(manifest.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    revision = "1"
    result = {"version": version, "revision": revision, "build": "local",
              "label": f"{version}:{revision}:local", "branch": "", "commit": ""}
    if not (repository / ".git").exists():
        return result
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        def read(*args: str) -> str:
            response = subprocess.run(["git", "-C", str(repository), *args],
                                      text=True, capture_output=True, timeout=5,
                                      creationflags=flags)
            if response.returncode:
                raise RuntimeError("Could not inspect checkout revision")
            return response.stdout.strip()
        build = read("rev-list", "--count", "HEAD")
        branch = read("branch", "--show-current") or "detached"
        commit = read("rev-parse", "--short=8", "HEAD")
        if not build.isdigit():
            raise ValueError("Invalid build number")
        result.update(build=build, branch=branch, commit=commit,
                      label=f"{version}:{revision}:{build}")
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError):
        pass
    return result


def git_info(repository: Path) -> dict[str, Any]:
    if sys.platform != "win32":
        return {"supported": False, "reason": "In-app relaunch currently supports Windows only"}
    if not (repository / ".git").exists():
        return {"supported": False, "reason": "No Git checkout detected"}
    def run(*args: str, timeout: int = 12) -> str:
        result = subprocess.run(["git", "-C", str(repository), *args],
                                text=True, capture_output=True, timeout=timeout,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip()[:300] or "Git failed")
        return result.stdout.strip()
    try:
        branch=run("branch", "--show-current")
        if not branch:
            return {"supported": False, "reason": "Detached HEAD"}
        before=run("rev-parse", "HEAD")
        # Fetch updates the Git metadata, but never changes working tree files.
        run("fetch", "--quiet", "origin", branch, timeout=25)
        remote=run("rev-parse", "FETCH_HEAD")
        can_fast_forward=before==remote or run("merge-base", "HEAD", "FETCH_HEAD")==before
        return {"supported": True, "branch": branch, "current": before[:12],
                "latest": remote[:12], "update_available": before!=remote,
                "can_fast_forward": can_fast_forward,
                "reason": "" if can_fast_forward else "Local and remote history diverged; inspect Git before updating"}
    except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
        return {"supported": False, "reason": f"Could not check Git safely: {exc}"[:350]}


def begin_relaunch(repository: Path, runtime_root: Path, previous_pid: int) -> None:
    """Start separate terminal before backend exits. Refuse if script is absent."""
    script=repository / "scripts" / "relaunch-song-harbor.ps1"
    if sys.platform != "win32" or not script.is_file():
        raise RuntimeError("Windows relaunch helper unavailable")
    flags=(getattr(subprocess,"CREATE_NEW_CONSOLE",0) |
           getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0))
    subprocess.Popen(["pwsh", "-NoProfile", "-File", str(script),
                      "-Repository",str(repository),"-RuntimeRoot",str(runtime_root),
                      "-PreviousPid",str(previous_pid)],
                     cwd=str(repository), creationflags=flags, close_fds=True)


def stop_after_response(delay_seconds: float = 0.8) -> None:
    """Exit only the web backend; the existing launcher then terminates normally."""
    def finish() -> None:
        time.sleep(delay_seconds)
        os._exit(0)
    threading.Thread(target=finish,daemon=True).start()
