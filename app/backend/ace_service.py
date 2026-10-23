"""Song Harbor-owned ACE-Step process lifecycle.

Only the exact subprocess spawned by this manager may be terminated. This
manager never invokes ACE installers, interactive batch files, or model init.
"""
from __future__ import annotations

import atexit
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from ace_adapter import AceClient

class AceServiceError(RuntimeError):
    pass

class AceServiceManager:
    def __init__(self, installation: Path, client: AceClient | None = None,
                 log_directory: Path | None = None):
        self.installation = installation.expanduser().resolve()
        self.client = client or AceClient()
        self.log_directory = log_directory or self.installation / "logs"
        self._process: subprocess.Popen | None = None
        self._lock = threading.RLock()
        atexit.register(self.cleanup)

    def _command(self) -> list[str]:
        python = self.installation / ".venv" / "Scripts" / "python.exe" if os.name == "nt" else self.installation / ".venv" / "bin" / "python"
        script = self.installation / "acestep" / "api_server.py"
        if not python.is_file() or not script.is_file():
            raise AceServiceError("ACE-Step installation or virtual environment not found")
        return [str(python), str(script), "--host", "127.0.0.1", "--port", "8001", "--no-init"]

    def status(self) -> dict[str, Any]:
        with self._lock:
            owned = self._process is not None and self._process.poll() is None
            if self._process is not None and not owned:
                self._process = None
            installation_ready = self._is_installed()
            info = self.client.discover()
            connected = info.get("status") == "connected"
            if connected:
                state = "running_ready" if info.get("ready") else "running_uninitialized"
            elif owned:
                state = "starting"
            elif installation_ready:
                state = "installed_stopped"
            else:
                state = "not_installed"
            return {"state": state, "installed": installation_ready,
                    "owned": owned, "pid": self._process.pid if owned else None,
                    "installation": str(self.installation),
                    "can_start": installation_ready and not owned and not connected,
                    "can_stop": owned, "runtime": info}

    def _is_installed(self) -> bool:
        try:
            self._command()
            return True
        except AceServiceError:
            return False

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self._process and self._process.poll() is None:
                return self.status()
            existing = self.client.discover()
            if existing.get("status") == "connected":
                # A pre-existing instance is not owned by Song Harbor.
                return self.status()
            cmd = self._command()
            self.log_directory.mkdir(parents=True, exist_ok=True)
            log_path = self.log_directory / "song-harbor-ace.log"
            env = os.environ.copy()
            env["ACESTEP_ON_DEMAND_MODEL_LOAD"] = "false"
            env["ACESTEP_NO_INIT"] = "true"
            try:
                with log_path.open("ab") as log:
                    self._process = subprocess.Popen(
                        cmd, cwd=str(self.installation), stdin=subprocess.DEVNULL,
                        stdout=log, stderr=subprocess.STDOUT, env=env,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        shell=False)
            except OSError as exc:
                raise AceServiceError(f"Cannot start local ACE-Step API: {exc}") from exc
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None:
                self._process = None
                raise AceServiceError("Song Harbor does not own a running ACE process")
            # Cancellation is experimental in local ACE; do not rely on it for
            # hard GPU cleanup. Exact process termination is authoritative.
            self._terminate(process)
            self._process = None
            return self.status()

    @staticmethod
    def _terminate(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def cleanup(self) -> None:
        with self._lock:
            process = self._process
            if process is not None:
                try:
                    self._terminate(process)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                self._process = None
