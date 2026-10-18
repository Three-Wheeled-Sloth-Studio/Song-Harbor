"""Durable, non-destructive Song Harbor song projects and DAW exchange.

All project data stays under the user-selected runtime data root, never in Git.
Existing stem jobs can be reconstructed from their on-disk source/stems after restart.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

ORDER = ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")
PROJECT_VERSION = 1


def stem_name(filename: str) -> str:
    for name in ORDER:
        if "(" + name + ")" in filename:
            return name
    raise ValueError("Unrecognized stem filename: " + filename)


def files_for_project(folder: Path) -> list[str]:
    stems = folder / "stems"
    found: dict[str, str] = {}
    for p in stems.glob("*.wav"):
        try:
            name = stem_name(p.name)
        except ValueError:
            continue
        if name in found:
            raise ValueError("Multiple files found for stem " + name)
        found[name] = p.name
    return [found[k] for k in ORDER] if set(found) == set(ORDER) else []


def project_path(data_root: Path, ident: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", ident):
        raise ValueError("Invalid project identifier")
    return data_root / "jobs" / ident / "song-harbor.json"


def default_settings(files: list[str]) -> list[dict[str, Any]]:
    return [{"filename": f, "gain": 1.0, "mute": False, "solo": False} for f in files]


def read_project(data_root: Path, ident: str) -> dict[str, Any] | None:
    folder = data_root / "jobs" / ident
    if not folder.is_dir():
        return None
    path = project_path(data_root, ident)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") == PROJECT_VERSION and data.get("id") == ident:
                return data
        except (ValueError, OSError, AttributeError):
            return None
    # Legacy jobs have no project manifest. Reconstruct only when all 6 stems exist.
    files = files_for_project(folder)
    if len(files) != 6:
        return None
    inputs = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in
              (".wav", ".flac", ".mp3", ".m4a", ".aiff", ".aif", ".ogg")]
    if len(inputs) != 1:
        return None
    return {
        "version": PROJECT_VERSION, "id": ident, "filename": inputs[0].name,
        "title": inputs[0].stem, "created_at": folder.stat().st_mtime,
        "source_filename": inputs[0].name, "model": "htdemucs_6s.yaml",
        "files": files, "stems": default_settings(files),
        "source_duration_seconds": None, "recovered": True,
    }


def write_project(data_root: Path, project: dict[str, Any]) -> dict[str, Any]:
    path = project_path(data_root, project["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(project, indent=2, ensure_ascii=False)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex[:8] + ".tmp")
    try:
        temp.write_text(encoded, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return project


def list_projects(data_root: Path) -> list[dict[str, Any]]:
    folder = data_root / "jobs"
    if not folder.is_dir():
        return []
    result = []
    for item in folder.iterdir():
        if item.is_dir() and re.fullmatch(r"[a-f0-9]{12}", item.name):
            project = read_project(data_root, item.name)
            if project and set(project.get("files", [])) == set(files_for_project(item)):
                result.append({
                    "id": project["id"], "title": project.get("title", project["filename"]),
                    "filename": project["filename"], "created_at": project.get("created_at"),
                    "recovered": project.get("recovered", False),
                })
    result.sort(key=lambda p: p.get("created_at") or 0, reverse=True)
    return result


def validated_stems(project: dict[str, Any], folder: Path) -> list[Path]:
    files = files_for_project(folder)
    if len(files) != 6 or set(files) != set(project["files"]):
        raise ValueError("Six matching source stems are required for DAW export")
    return [folder / "stems" / f for f in files]


def export_waveform(data_root: Path, project: dict[str, Any]) -> Path:
    """Portable Waveform import folder, NOT a fabricated .tracktionedit project."""
    folder = data_root / "jobs" / project["id"]
    originals = validated_stems(project, folder)
    export_parent = folder / "exports"
    export_parent.mkdir(parents=True, exist_ok=True)
    target = export_parent / "Waveform"
    # Unique exports preserve earlier bundles and any external edits.
    if target.exists():
        target = export_parent / ("Waveform-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4])
    staging = Path(tempfile.mkdtemp(prefix=".waveform-", dir=export_parent))
    try:
        tracks = []
        for index, p in enumerate(originals, start=1):
            name = stem_name(p.name)
            destination = f"{index:02d} - {name}.wav"
            shutil.copy2(p, staging / destination)
            tracks.append({"name": name, "file": destination, "start_seconds": 0.0,
                           "gain": next((s["gain"] for s in project["stems"]
                                         if s["filename"] == p.name), 1.0)})
        manifest = {"format": "song-harbor-waveform-exchange", "version": 1,
                    "song": project.get("title"), "source_project_id": project["id"],
                    "source_duration_seconds": project.get("source_duration_seconds"),
                    "sample_rate_hz": 48000, "track_count": 6, "tracks": tracks}
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (staging / "IMPORT-IN-WAVEFORM.txt").write_text(
            "Song Harbor -> Waveform Free\n\n"
            "1. Open Waveform Free and create/open a project and its Edit.\n"
            "2. Import all six WAV files as SIX SEPARATE TRACKS, not end-to-end clips.\n"
            "   Select files in Waveform's browser, then Ctrl-drag and choose separate tracks.\n"
            "3. Ensure every clip starts at timeline 0:00; disable tempo sync/stretch and looping.\n"
            "4. Check song duration and alignment before editing.\n"
            "5. Keep this export folder intact as Waveform may refer to its audio files.\n\n"
            "The six stems are copied unaltered from Song Harbor.\n"
            "This is a portable audio exchange, not a native .tracktionedit file.\n"
            "Mixer gains are in manifest.json as reference; apply levels in Waveform as desired.\n",
            encoding="utf-8",
        )
        staging.rename(target)
        return target
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
