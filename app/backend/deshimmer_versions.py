"""Non-destructive, identity-preserving Deshimmer stem version adoption.

A cleanup is a new version of an existing source key, never a new track.
The original media and its production-script identity remain recoverable.
"""
from __future__ import annotations
import copy
import hashlib
import os
import shutil
import uuid
import channel_split
from pathlib import Path

def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()

def _current(project: dict, filename: str) -> dict:
    track = next((row for row in project.get("source_tracks", [])
                  if row.get("working_filename") == filename), None)
    if not track:
        raise ValueError("Source stem identity is missing")
    if any(mask.get("source_filename") == filename for mask in project.get("replacement_masks", [])):
        raise ValueError("Remove existing replacement layers for this stem before accepting a cleaned version")
    return track

def adopt(root: Path, project: dict, filename: str, candidate: Path,
          expected_hash: str, candidate_id: str, save,
          ffmpeg: str | None = None, ffprobe: str | None = None) -> dict:
    """Atomically publish a repaired working WAV and manifest, rolling back on failure.

    save(project) persists the complete project and is dependency-injected for tests.
    Original working audio is backed up before the first byte is replaced.
    """
    _current(project, filename)
    target = root / "jobs" / project["id"] / "stems" / filename
    if not target.is_file() or not candidate.is_file():
        raise ValueError("Stem or cleaned candidate does not exist")
    if digest(target) != expected_hash:
        raise ValueError("Stem changed during cleanup; regenerate the candidate")
    version_id = uuid.uuid4().hex
    folder = root / "jobs" / project["id"] / "stem_versions" / version_id
    folder.mkdir(parents=True, exist_ok=False)
    previous = folder / "previous.wav"
    staging = target.parent / ("." + version_id + ".new.wav")
    shutil.copy2(target, previous)
    shutil.copy2(candidate, staging)
    new_hash = digest(staging)
    updated = copy.deepcopy(project)
    updated.setdefault("stem_cleanup_versions", []).append({
        "id": version_id, "filename": filename,
        "track_id": _current(updated, filename)["track_id"],
        "source_hash": expected_hash, "candidate_hash": new_hash,
        "candidate_id": candidate_id,
        "backup": "stem_versions/" + version_id + "/previous.wav",
        "prior_channel_children": copy.deepcopy(project.get("channel_children", {}).get(filename)),
    })
    replaced = False
    new_export: Path | None = None
    try:
        os.replace(staging, target)
        replaced = True
        if project.get("channel_children", {}).get(filename, {}).get("active"):
            if not ffmpeg or not ffprobe:
                raise ValueError("L/R split tools unavailable; cleaned stem not accepted")
            # Generate a new immutable derived export BEFORE publishing its routing.
            new_export = channel_split.split_stems(root, updated, [filename], ffmpeg, ffprobe)
            updated.setdefault("channel_children", {})[filename] = {
                "export": new_export.name, "active": True
            }
        save(updated)
        return updated
    except Exception:
        if replaced:
            shutil.copy2(previous, staging)
            os.replace(staging, target)
        if new_export is not None:
            shutil.rmtree(new_export, ignore_errors=True)
        raise
    finally:
        staging.unlink(missing_ok=True)

def undo(root: Path, project: dict, filename: str, save) -> dict:
    """Undo only the latest stem cleanup version when current bytes match it."""
    records = project.get("stem_cleanup_versions", [])
    matches = [row for row in records if row.get("filename") == filename]
    if not matches:
        raise ValueError("No accepted cleanup for this stem")
    record = matches[-1]
    target = root / "jobs" / project["id"] / "stems" / filename
    backup = root / "jobs" / project["id"] / record["backup"]
    if not backup.is_file() or not target.is_file():
        raise ValueError("Stored cleanup version is incomplete")
    if digest(target) != record["candidate_hash"]:
        raise ValueError("Current stem no longer matches accepted cleanup; cannot safely undo")
    if digest(backup) != record["source_hash"]:
        raise ValueError("Backup hash mismatch; refusing undo")
    updated = copy.deepcopy(project)
    updated["stem_cleanup_versions"] = [row for row in records if row["id"] != record["id"]]
    # Restore exactly the routing that belonged to the prior audio version.
    if "prior_channel_children" in record:
        if record["prior_channel_children"] is None:
            updated.get("channel_children", {}).pop(filename, None)
        else:
            updated.setdefault("channel_children", {})[filename] = copy.deepcopy(record["prior_channel_children"])
    staging = target.parent / ("." + uuid.uuid4().hex + ".undo.wav")
    accepted = target.parent / ("." + uuid.uuid4().hex + ".accepted.wav")
    shutil.copy2(target, accepted)
    shutil.copy2(backup, staging)
    replaced = False
    try:
        os.replace(staging, target)
        replaced = True
        save(updated)
        return updated
    except Exception:
        if replaced:
            os.replace(accepted, target)
        raise
    finally:
        staging.unlink(missing_ok=True)
        accepted.unlink(missing_ok=True)
