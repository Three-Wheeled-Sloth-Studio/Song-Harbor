"""Immutable, project-rendered Q4 analysis inputs, isolated from user exports."""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
import wave
from pathlib import Path

MAX_SNAPSHOT_BYTES = 200 * 1024 * 1024
MAX_TRANSFER_BYTES = 600 * 1024 * 1024


def _root(app_root: Path) -> Path:
    return app_root / "cache" / "moss-q4-snapshots"


def _load(app_root: Path, snapshot_id: str) -> dict:
    if not isinstance(snapshot_id, str) or len(snapshot_id) != 32 or any(c not in "0123456789abcdef" for c in snapshot_id):
        raise ValueError("ERROR: Invalid analysis snapshot reference. No inference started.")
    folder = _root(app_root)
    path = folder / (snapshot_id + ".json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("ERROR: Analysis snapshot missing. Render the current mix again.") from None
    audio = folder / (snapshot_id + ".wav")
    if not audio.is_file() or audio.is_symlink() or audio.stat().st_size != data.get("bytes"):
        raise ValueError("ERROR: Analysis snapshot is missing or changed. Render again.")
    digest = hashlib.sha256()
    with audio.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != data.get("sha256"):
        raise ValueError("ERROR: Analysis snapshot checksum changed. Render again.")
    return {**data, "audio_path": str(audio)}


def read(app_root: Path, snapshot_id: str) -> dict:
    return _load(app_root, snapshot_id)


def create(app_root: Path, stream, *, project_id: str, recipe_revision: str,
           start_seconds: float | None, end_seconds: float | None,
           section_ids: list[str]) -> dict:
    if not project_id or not recipe_revision or len(project_id) > 200 or len(recipe_revision) > 200:
        raise ValueError("ERROR: Project and render revision required. Nothing saved.")
    if len(section_ids) > 200 or any(not isinstance(x, str) or len(x) > 200 for x in section_ids):
        raise ValueError("ERROR: Invalid section selection.")
    selected = start_seconds is not None or end_seconds is not None
    if selected and (start_seconds is None or end_seconds is None or
                     not 0 <= start_seconds < end_seconds or end_seconds - start_seconds > 900):
        raise ValueError("ERROR: Invalid selected range. Nothing saved.")
    folder = _root(app_root)
    folder.mkdir(parents=True, exist_ok=True)
    # Retain recent snapshots for review; only reclaim old immutable cache files.
    for candidate in folder.glob("*.json"):
        try:
            if time.time() - candidate.stat().st_mtime > 7 * 24 * 3600:
                stem = candidate.stem
                if len(stem) == 32 and all(c in "0123456789abcdef" for c in stem):
                    (folder / (stem + ".wav")).unlink(missing_ok=True)
                    candidate.unlink(missing_ok=True)
        except OSError:
            pass
    snapshot_id = uuid.uuid4().hex
    staging = folder / (snapshot_id + ".part")
    final = folder / (snapshot_id + ".wav")
    metadata_path = folder / (snapshot_id + ".json")
    try:
        with staging.open("xb") as output:
            total = 0
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_TRANSFER_BYTES:
                    raise ValueError("ERROR: Offline mix transfer exceeds 600 MiB. Snapshot not saved.")
                output.write(chunk)
        try:
            with wave.open(str(staging), "rb") as wav:
                channels, width, rate, frames = (wav.getnchannels(), wav.getsampwidth(),
                                                   wav.getframerate(), wav.getnframes())
                if channels != 2 or width != 3 or rate < 8000 or rate > 192000 or frames == 0:
                    raise ValueError("ERROR: Expected Song Harbor stereo 24-bit WAV snapshot.")
                if selected:
                    first = round(start_seconds * rate)
                    last = round(end_seconds * rate)
                    if first < 0 or last > frames or first >= last:
                        raise ValueError("ERROR: Selected sections exceed the rendered audio length.")
                    wav.setpos(first)
                    selected_pcm = (first, last)
                else:
                    selected_pcm = None
        except (wave.Error, EOFError) as exc:
            raise ValueError("ERROR: Invalid offline mix WAV; snapshot not saved.") from exc
        source_digest = hashlib.sha256()
        with staging.open("rb") as raw:
            for block in iter(lambda: raw.read(1024 * 1024), b""):
                source_digest.update(block)
        if source_digest.hexdigest() != recipe_revision:
            raise ValueError("ERROR: Rendered mix hash changed during transfer; snapshot not saved.")
        if selected_pcm is not None:
            # Copy in bounded chunks; do not keep a whole selected region in RAM.
            trimmed = folder / (snapshot_id + ".trim")
            first, last = selected_pcm
            with wave.open(str(staging), "rb") as source_wav, wave.open(str(trimmed), "wb") as out_wav:
                out_wav.setnchannels(channels)
                out_wav.setsampwidth(width)
                out_wav.setframerate(rate)
                source_wav.setpos(first)
                remaining = last - first
                while remaining:
                    take = min(remaining, 65536)
                    out_wav.writeframesraw(source_wav.readframes(take))
                    remaining -= take
            os.replace(trimmed, staging)
        if staging.stat().st_size > MAX_SNAPSHOT_BYTES:
            raise ValueError("ERROR: Selected analysis audio exceeds 200 MiB. Choose a shorter section range.")
        digest = hashlib.sha256()
        with staging.open("rb") as audio:
            for chunk in iter(lambda: audio.read(1024 * 1024), b""):
                digest.update(chunk)
        info = {"snapshot_id": snapshot_id, "project_id": project_id,
                "recipe_revision": recipe_revision, "rendered_mix_sha256": recipe_revision,
                "section_ids": section_ids,
                "start_seconds": start_seconds if selected else 0,
                "end_seconds": end_seconds if selected else frames / rate,
                "sample_rate": rate, "channels": channels,
                "sha256": digest.hexdigest(), "bytes": staging.stat().st_size,
                "source": "song-harbor-offline-mix", "status": "unvalidated"}
        os.replace(staging, final)
        try:
            metadata_path.write_text(json.dumps(info, indent=2), encoding="utf-8")
        except Exception:
            final.unlink(missing_ok=True)
            raise
        return info
    finally:
        staging.unlink(missing_ok=True)
        (folder / (snapshot_id + ".trim")).unlink(missing_ok=True)
