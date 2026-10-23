"""Non-destructive ACE candidate preparation and persistent job assets.

All source paths are derived from the Song Harbor project folder. This module
never inserts a stem; a separate user acceptance action owns that mutation.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from ace_adapter import AceError, AceClient, Selection, resolve_sections, normalize_poll, unwrap

CANDIDATE_FOLDER = "ace-candidates"
ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
MAX_CONTEXT_SECONDS = 240.0
MAX_CANDIDATES = 4


def sample_bounds(selection: Selection, rate: int = 48000) -> dict[str, int]:
    """Use integer samples throughout cropping/alignment; no cumulative ms drift."""
    if rate <= 0:
        raise ValueError("Invalid audio sample rate")
    context_start = round(selection.context.start * rate)
    context_end = round(selection.context.end * rate)
    target_start = round(selection.target.start * rate)
    target_end = round(selection.target.end * rate)
    if context_start > target_start or target_end > context_end or target_end <= target_start:
        raise ValueError("Target must fall inside reference context")
    return {"context_start": context_start, "context_end": context_end,
            "target_start": target_start, "target_end": target_end,
            "crop_start": target_start - context_start,
            "crop_end": target_end - context_start}


def validate_generation(project: dict[str, Any], from_section_id: str,
                        to_section_id: str, before: float, after: float,
                        model: str, prompt: str, task_type: str,
                        capabilities: dict[str, Any]) -> tuple[Selection, dict[str, int]]:
    sections = project.get("sections") or []
    identifiers = [s.get("id") for s in sections]
    if from_section_id not in identifiers or to_section_id not in identifiers:
        raise ValueError("Select existing song section IDs")
    duration = project.get("source_duration_seconds")
    selection = resolve_sections(sections, identifiers.index(from_section_id),
                                 identifiers.index(to_section_id), duration, before, after)
    if selection.context.duration > MAX_CONTEXT_SECONDS:
        raise ValueError("Reference context must not exceed four minutes")
    if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 2000:
        raise ValueError("An accompaniment prompt of 1-2000 characters is required")
    available = next((m for m in capabilities.get("models", []) if m["name"] == model), None)
    if available is None or task_type not in available.get("validated_tasks", []):
        raise ValueError("Model or generation mode is not verified and available")
    if task_type not in ("cover", "lego"):
        raise ValueError("Only cover and verified Lego modes may create accompaniment candidates")
    return selection, sample_bounds(selection)


def source_fingerprint(project: dict[str, Any], audio_path: Path) -> str:
    """Capture a snapshot of both the section arrangement and source audio."""
    signature = {"sections": project.get("sections", []),
                 "source_duration_seconds": project.get("source_duration_seconds"),
                 "source": audio_path.name, "source_size": audio_path.stat().st_size}
    digest = hashlib.sha256()
    with audio_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    signature["source_sha256"] = digest.hexdigest()
    return hashlib.sha256(json.dumps(signature, sort_keys=True).encode("utf-8")).hexdigest()


def candidate_directory(project_folder: Path, candidate_id: str) -> Path:
    if not ID_PATTERN.fullmatch(candidate_id):
        raise ValueError("Invalid candidate identifier")
    return project_folder / "generated" / CANDIDATE_FOLDER / candidate_id


def save_record(directory: Path, record: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "candidate.json"
    handle, temp = tempfile.mkstemp(prefix=".candidate-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)
        os.replace(temp, destination)
    finally:
        Path(temp).unlink(missing_ok=True)


def load_record(project_folder: Path, candidate_id: str) -> dict[str, Any]:
    directory = candidate_directory(project_folder, candidate_id)
    with (directory / "candidate.json").open(encoding="utf-8") as stream:
        record = json.load(stream)
    if record.get("candidate_id") != candidate_id:
        raise ValueError("Candidate metadata does not match its directory")
    return record


def ffmpeg_extract(ffmpeg: str, source: Path, destination: Path,
                   start_sample: int, end_sample: int, rate: int = 48000) -> None:
    """Sample-bounded trim; outputs WAV suitable for ACE upload and audition."""
    if end_sample <= start_sample or start_sample < 0:
        raise ValueError("Invalid audio interval")
    destination.parent.mkdir(parents=True, exist_ok=True)
    filters = (f"aresample={rate},atrim=start_sample={start_sample}:"
               f"end_sample={end_sample},asetpts=PTS-STARTPTS")
    try:
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                        "-i", str(source), "-vn", "-af", filters, "-ac", "2",
                        "-ar", str(rate), "-c:a", "pcm_s24le", str(destination)],
                       check=True, capture_output=True, timeout=180,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        destination.unlink(missing_ok=True)
        raise AceError("Failed to prepare bounded ACE audio interval") from exc


def create_candidate(project: dict[str, Any], project_folder: Path, source_audio: Path,
                     from_id: str, to_id: str, before: float, after: float,
                     model: str, prompt: str, task_type: str, capabilities: dict[str, Any],
                     ffmpeg: str, seed: int = 150719) -> dict[str, Any]:
    """Prepare source context and metadata, but do not submit or alter tracks."""
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Seed must be a non-negative 32-bit integer")
    selection, samples = validate_generation(project, from_id, to_id, before, after,
                                               model, prompt, task_type, capabilities)
    if not source_audio.is_file() or source_audio.resolve().parent != project_folder.resolve():
        raise ValueError("Source audio must be a project-owned original recording")
    candidate_id = uuid.uuid4().hex
    directory = candidate_directory(project_folder, candidate_id)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        ffmpeg_extract(ffmpeg, source_audio, directory / "context.wav",
                       samples["context_start"], samples["context_end"])
        record = {"candidate_id": candidate_id, "project_id": project["id"],
                  "state": "prepared", "engine": "ace-step", "model": model,
                  "task_type": task_type, "prompt": prompt.strip(), "seed": seed,
                  "from_section_id": from_id, "to_section_id": to_id,
                  "samples": samples, "sample_rate_hz": 48000,
                  "target_start_seconds": selection.target.start,
                  "target_end_seconds": selection.target.end,
                  "source_fingerprint": source_fingerprint(project, source_audio),
                  "context_file": "context.wav", "variants": [],
                  "isolation": "native-unverified" if task_type == "lego"
                               else "cover-mix-not-isolated"}
        save_record(directory, record)
        return record
    except Exception:
        # Never leave a candidate directory that looks successfully prepared.
        for path in directory.glob("*"):
            path.unlink(missing_ok=True)
        directory.rmdir()
        raise


def probe_audio_duration(ffmpeg: str, source: Path) -> float:
    """Use FFprobe instead of wave.open: ACE may emit IEEE float WAV (format 3)."""
    tool = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe")
    try:
        result = subprocess.run(
            [str(tool), "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
            capture_output=True, text=True, check=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        duration = float(result.stdout.strip())
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise AceError("Cannot inspect generated audio duration with FFprobe") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise AceError("Generated candidate has invalid audio duration")
    return duration


def crop_generated_candidate(project_folder: Path, candidate_id: str,
                             generated_file: Path, ffmpeg: str) -> dict[str, Any]:
    """Materialize the requested target from a context-aligned ACE output."""
    record = load_record(project_folder, candidate_id)
    if record["state"] not in ("prepared", "generating", "processing"):
        raise ValueError("Candidate state is not suitable for processing")
    directory = candidate_directory(project_folder, candidate_id)
    if generated_file.resolve().parent != directory.resolve() or not generated_file.is_file():
        raise ValueError("Generated audio must already be copied into its candidate directory")
    samples = record["samples"]
    from_start = samples["crop_start"]
    to_end = samples["crop_end"]
    destination = directory / "target.wav"
    # Decode any valid WAV encoding, including ACE's IEEE float (format 3).
    # ffmpeg_extract resamples before applying sample-accurate 48 kHz bounds.
    duration = probe_audio_duration(ffmpeg, generated_file)
    required_seconds = to_end / record["sample_rate_hz"]
    if duration + 0.002 < required_seconds:
        raise AceError(
            f"Generated context is too short ({duration:.3f}s; needs {required_seconds:.3f}s)")
    ffmpeg_extract(ffmpeg, generated_file, destination, from_start, to_end)
    actual = probe_audio_duration(ffmpeg, destination)
    expected = (to_end - from_start) / record["sample_rate_hz"]
    if abs(actual - expected) > 0.003:
        destination.unlink(missing_ok=True)
        raise AceError(f"Candidate crop length mismatch ({actual:.3f}s vs {expected:.3f}s)")
    record["variants"].append({"kind": "raw-cover-crop" if record["task_type"] == "cover"
                               else "native-generated", "file": destination.name,
                               "isolation": record["isolation"]})
    record["state"] = "ready"
    save_record(directory, record)
    return record
