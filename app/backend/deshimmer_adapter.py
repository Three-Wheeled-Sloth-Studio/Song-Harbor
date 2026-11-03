"""Optional Deshimmer dependency handshake, without processing project audio.

Use a configured Python executable from a separately installed environment.
This does not execute project files or import Gradio. A successful handshake
does not establish that the external processor's parameters or output schema
are compatible; those require a pinned upstream version and an audio fixture.
"""
from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path


class DeshimmerUnavailable(RuntimeError):
    pass


PROBE = (
    "import importlib, json, sys; "
    "m=importlib.import_module('deshimmer.api'); "
    "fn=getattr(m, 'process_audio', None); "
    "print(json.dumps({'available': callable(fn), "
    "'module': str(getattr(m,'__file__','')), "
    "'python': sys.version.split()[0]}))"
)


def probe(python_executable: str | None = None, timeout_seconds: int = 15) -> dict:
    configured = python_executable or os.environ.get("SONG_HARBOR_DESHIMMER_PYTHON")
    if not configured:
        raise DeshimmerUnavailable(
            "Configure SONG_HARBOR_DESHIMMER_PYTHON to the Deshimmer environment's Python executable"
        )
    executable = Path(configured).expanduser().resolve()
    if not executable.is_file():
        raise DeshimmerUnavailable("Configured Deshimmer Python executable does not exist")
    if not 1 <= timeout_seconds <= 30:
        raise DeshimmerUnavailable("Invalid Deshimmer probe timeout")
    try:
        outcome = subprocess.run(
            [str(executable), "-c", PROBE],
            capture_output=True, text=True, shell=False, timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeshimmerUnavailable("Deshimmer environment probe failed or timed out") from exc
    if outcome.returncode:
        raise DeshimmerUnavailable(
            "Deshimmer API cannot be imported in configured Python environment: "
            + outcome.stderr[-500:]
        )
    try:
        value = json.loads(outcome.stdout.strip())
    except (ValueError, TypeError) as exc:
        raise DeshimmerUnavailable("Deshimmer probe returned invalid JSON") from exc
    if not isinstance(value, dict) or value.get("available") is not True:
        raise DeshimmerUnavailable("deshimmer.api.process_audio is not callable")
    module = value.get("module")
    if not isinstance(module, str) or not module:
        raise DeshimmerUnavailable("Deshimmer module provenance unavailable")
    return {
        "available": True, "module": module,
        "python": str(value.get("python", "")),
        "configured_python": str(executable),
    }
