"""Experimental, opt-in native MOSS-Audio Q4 hook via CrispASR CLI.

The hook is deliberately separate from SGLang. It does not alter projects,
download binaries/weights, or claim useful musical understanding before QA.
"""
from __future__ import annotations

import json
import re
import os
import subprocess
import threading
import uuid
import time
from pathlib import Path

LOCK = threading.RLock()
_JOB = {"process": None, "log": None, "started": None, "state": "idle",
        "error": "", "result": "", "audio": "", "log_start": 0,
        "run_file": None, "run_id": None, "output_truncated": False,
        "review": None}
MAX_AUDIO_BYTES = 200 * 1024 * 1024
MAX_MODEL_BYTES = 16 * 1024**3
TIMEOUT_SECONDS = 600


def _config_path(app_root: Path) -> Path:
    return app_root / "settings" / "moss-q4-experiment.json"


def config(app_root: Path) -> dict:
    try:
        data = json.loads(_config_path(app_root).read_text(encoding="utf-8"))
        return {key: str(data.get(key, "")) for key in ("executable", "model")}
    except (OSError, ValueError, TypeError):
        return {"executable": "", "model": ""}


def discover(app_root: Path, model_root: Path) -> dict:
    """Bounded discovery. No recursive scan of drives, no executable launch."""
    roots = [app_root / "tools", model_root / "tools", model_root / "checkpoints",
             model_root / "gguf"]
    binaries: list[str] = []
    checkpoints: list[str] = []
    for root in roots:
        if not root.is_dir():
            continue
        for folder in [root] + [entry for entry in root.iterdir() if entry.is_dir() and not entry.is_symlink()][:80]:
            for name in ("crispasr.exe", "crispasr", "crispasr-cli.exe", "crispasr-cli"):
                candidate = folder / name
                if candidate.is_file() and not candidate.is_symlink():
                    binaries.append(str(candidate))
            for item in list(folder.glob("*.gguf"))[:80]:
                if "moss" in item.name.lower() and "audio" in item.name.lower() and not item.is_symlink():
                    checkpoints.append(str(item))
    return {"executables": sorted(set(binaries)), "models": sorted(set(checkpoints)),
            "configured": config(app_root),
            "experiment": "CrispASR MOSS-Audio Q4; audio encoder support unverified on this machine"}


def _validate(executable: str, model: str) -> tuple[Path, Path]:
    binary, gguf = Path(executable), Path(model)
    if not binary.is_absolute() or not binary.is_file() or binary.is_symlink():
        raise ValueError("ERROR: Select an existing local CrispASR executable. Nothing launched.")
    if binary.name.lower() not in ("crispasr.exe", "crispasr"):
        raise ValueError("ERROR: Only a CrispASR executable is accepted.")
    if not gguf.is_absolute() or not gguf.is_file() or gguf.is_symlink():
        raise ValueError("ERROR: Select an existing MOSS-Audio GGUF. Nothing launched.")
    if not (gguf.suffix.lower() == ".gguf" and "moss" in gguf.name.lower() and
            "audio" in gguf.name.lower() and "q4" in gguf.name.lower()):
        raise ValueError("ERROR: Model must be a MOSS-Audio GGUF, not text-only MOSS-Music.")
    size = gguf.stat().st_size
    if not (1024 * 1024 <= size <= MAX_MODEL_BYTES):
        raise ValueError("ERROR: GGUF file size is invalid; inspect model before use.")
    with gguf.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise ValueError("ERROR: Invalid GGUF header. Model not configured.")
    return binary, gguf


def configure(app_root: Path, executable: str, model: str) -> dict:
    binary, gguf = _validate(executable, model)
    path = _config_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(".tmp")
    staging.write_text(json.dumps({"executable": str(binary.resolve()),
                                   "model": str(gguf.resolve())}, indent=2), encoding="utf-8")
    os.replace(staging, path)
    return {"configured": config(app_root), "verified": False,
            "message": "Paths saved; authenticity and inference still unverified."}


def _log(app_root: Path) -> Path:
    return app_root / "logs" / "moss-q4-experiment.log"


def _read_run_output(path: Path | None, limit: int = 2 * 1024 * 1024) -> tuple[str, bool]:
    """Keep a complete single-run response or mark it explicitly truncated.

    Never slice from the end of model output: that drops the opening sentence
    and makes a mid-word fragment look like a complete musical observation.
    """
    if path is None or not path.is_file():
        return "", False
    size = path.stat().st_size
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    return raw[:limit].decode("utf-8", errors="replace"), size > limit



def _review_output(raw: str) -> dict:
    """Separate a CrispASR diagnostic transcript from its user-facing answer.

    CrispASR's multi-slice output is unlabelled, so its merged answer must
    NOT be represented as a single coherent caption or mapped to sections.
    The original log is retained untouched for troubleshooting.
    """
    lines = raw.splitlines()
    slice_count = None
    duration = None
    for line in lines:
        matched = re.search(r"crispasr: processing (\d+) slice\(s\)", line)
        if matched:
            slice_count = int(matched.group(1))
        matched = re.search(r"crispasr: audio: .*?\(([\d.]+) s\)", line)
        if matched:
            duration = float(matched.group(1))
    # This marker precedes the complete merged model response in tested CLI
    # builds. An absent marker must not cause debug output to be mislabelled.
    boundaries = [i for i, line in enumerate(lines)
                  if re.search(r"^crispasr: transcribed .*? audio in ", line)]
    answer = "\n".join(lines[boundaries[-1] + 1:]).strip() if boundaries else ""
    warnings = []
    if slice_count and slice_count > 1:
        warnings.append(f"CrispASR processed {slice_count} overlapping/unlabelled slices; "
                        "their combined response is not a section-aligned analysis.")
    if not boundaries:
        warnings.append("No recognized final-answer delimiter; inspect raw log.")
    if re.search(r"(?:\b[A-G](?:#|b)?(?:m|maj|dim|sus|7)?\s*,\s*){20,}", answer):
        warnings.append("Long repeated chord sequence detected; harmonic claims require verification.")
    if re.search(r"\b(?:BPM|beats per minute)\b", answer, flags=re.I):
        warnings.append("Tempo claims are model estimates, not measured BPM.")
    return {"answer": answer, "slices": slice_count, "duration_seconds": duration,
            "warnings": warnings, "validated": False, "aligned": False,
            "format": "crispasr-unsegmented-v1"}


def status(app_root: Path) -> dict:
    with LOCK:
        process = _JOB["process"]
        if process is not None and process.poll() is None and time.monotonic() - _JOB["started"] >= TIMEOUT_SECONDS:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=8)
            _JOB["state"] = "failed"
            _JOB["error"] = "ERROR: Q4 test exceeded 10 minutes. Process stopped; no recommendation produced."
        if process is not None and process.poll() is not None:
            code = process.returncode
            if _JOB["state"] == "running":
                _JOB["state"] = "complete" if code == 0 else "failed"
                _JOB["error"] = "" if code == 0 else f"ERROR: CrispASR exited with code {code}. No verified analysis."
            if _JOB["log"] is not None:
                _JOB["log"].close()
                _JOB["log"] = None
            _JOB["process"] = None
            result, truncated = _read_run_output(_JOB.get("run_file"))
            _JOB["result"] = result
            _JOB["review"] = _review_output(result)
            _JOB["output_truncated"] = truncated
        return {"state": _JOB["state"], "error": _JOB["error"],
                "elapsed_seconds": round(time.monotonic() - _JOB["started"]) if _JOB["state"] == "running" else None,
                "log_path": str(_JOB["run_file"] or _log(app_root)),
                "log_tail": _tail(_JOB["run_file"], 0) if _JOB.get("run_file") else "",
                "result": _JOB["result"], "review": _JOB.get("review"),
                "audio": _JOB["audio"],
                "run_id": _JOB.get("run_id"),
                "output_truncated": _JOB.get("output_truncated", False),
                "output_path": str(_JOB["run_file"]) if _JOB.get("run_file") else None}


def _tail(path: Path, offset: int, limit: int = 5000) -> str:
    try:
        with path.open("rb") as f:
            end = f.seek(0, os.SEEK_END)
            f.seek(min(end, max(offset, end - limit)))
            return f.read(limit).decode("utf-8", errors="replace")
    except OSError:
        return ""


def _watch_process(app_root: Path, process: subprocess.Popen) -> None:
    """Enforce timeout even when the user closes the MOSS tool."""
    while process.poll() is None:
        time.sleep(3)
        with LOCK:
            if _JOB["process"] is not process:
                return
        status(app_root)
    status(app_root)


def start(app_root: Path, audio: str, prompt: str, approved: bool) -> dict:
    if not approved:
        raise ValueError("ERROR: Explicit approval is required before experimental Q4 inference.")
    settings = config(app_root)
    executable, model = _validate(settings["executable"], settings["model"])
    source = Path(audio)
    if (not source.is_absolute() or not source.is_file() or source.is_symlink()
            or source.suffix.lower() != ".wav" or not 44 <= source.stat().st_size <= MAX_AUDIO_BYTES):
        raise ValueError("ERROR: Select a local WAV test clip no larger than 200 MB. Nothing launched.")
    if not prompt.strip() or len(prompt) > 400:
        raise ValueError("ERROR: Provide a short audio question (1-400 characters).")
    with source.open("rb") as stream:
        riff = stream.read(4)
        stream.seek(8)
        wave = stream.read(4)
        if riff != b"RIFF" or wave != b"WAVE":
            raise ValueError("ERROR: Test input is not a RIFF/WAVE audio file.")
    with LOCK:
        if _JOB["process"] is not None and _JOB["process"].poll() is None:
            raise ValueError("ERROR: Q4 test already running. No duplicate inference.")
        path = _log(app_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        offset = path.stat().st_size if path.exists() else 0
        run_id = uuid.uuid4().hex
        run_file = path.parent / ("moss-q4-" + run_id + ".txt")
        # Exact local files only: no '-m auto', no network download, no project edits.
        cmd = [str(executable), "--backend", "moss-audio", "-m", str(model),
               "-f", str(source), "--prompt", prompt.strip()]
        handle = run_file.open("xb")
        try:
            process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                       stdout=handle, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:
            handle.close()
            run_file.unlink(missing_ok=True)
            raise
        handle.close()  # child retains its own output descriptor
        _JOB.update({"process": process, "log": None, "started": time.monotonic(),
                     "state": "running", "error": "", "result": "", "audio": str(source),
                     "run_file": run_file, "run_id": run_id, "output_truncated": False,
                     "review": None,
                     "log_start": offset})
        threading.Thread(target=_watch_process, args=(app_root, process),
                         name="moss-q4-experiment-watchdog", daemon=True).start()
    return status(app_root)


def cancel(app_root: Path) -> dict:
    with LOCK:
        process = _JOB["process"]
        if process is None or process.poll() is not None:
            return status(app_root)
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=8)
        _JOB["state"] = "cancelled"
        _JOB["error"] = ""
    return status(app_root)


def cleanup() -> None:
    with LOCK:
        process = _JOB["process"]
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=8)


def browse(kind: str) -> dict:
    """Native picker invoked only by an explicit Windows UI action."""
    if os.name != "nt":
        raise RuntimeError("ERROR: Q4 file browsing requires Windows.")
    if kind not in ("executable", "model", "audio"):
        raise ValueError("ERROR: Unsupported Q4 file selection.")
    import tkinter
    from tkinter import filedialog
    filters = {
        "executable": [("CrispASR executable", "*.exe"), ("All files", "*.*")],
        "model": [("MOSS-Audio Q4 GGUF", "*.gguf"), ("All files", "*.*")],
        "audio": [("WAV test clip", "*.wav")],
    }
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askopenfilename(
            title={"executable": "Select CrispASR executable",
                   "model": "Select full-audio MOSS Q4 GGUF",
                   "audio": "Select non-active test WAV"}[kind],
            filetypes=filters[kind])
        return {"path": path or None}
    finally:
        root.destroy()
