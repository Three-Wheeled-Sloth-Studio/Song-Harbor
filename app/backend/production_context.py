"""Human-reviewed musical context for production planning.

The sole authority for these labels is a user save. A MOSS/Q4 run can be
linked as supporting, unverified provenance, never as an automatic fact.
"""
from __future__ import annotations

import copy
import json
import os
import uuid
from pathlib import Path

VERSION = 1
TONES = {"intimate", "restrained", "ominous", "rising", "expansive",
         "driving", "suspended", "neutral"}
SOURCE_TYPES = {"author", "q4-reviewed"}


def empty() -> dict:
    return {"schema_version": VERSION, "revision": 0, "sections": {}}


def normalize(raw: dict, section_ids: set[str], *, allow_retired: bool = False) -> dict:
    if not isinstance(raw, dict) or raw.get("schema_version") != VERSION:
        raise ValueError("Invalid production context format")
    revision = raw.get("revision")
    if type(revision) is not int or not 0 <= revision < 1000000:
        raise ValueError("Invalid production context revision")
    entries = raw.get("sections")
    archived = raw.get("archived", {})
    if (not isinstance(entries, dict) or not isinstance(archived, dict)
            or len(entries) + len(archived) > 512):
        raise ValueError("Invalid production context sections")
    result = {"schema_version": VERSION, "revision": revision, "sections": {},
              "archived": {}}
    for section_id, item in [*entries.items(), *archived.items()]:
        if section_id in entries and section_id not in section_ids and not allow_retired:
            raise ValueError("Production context references an unknown section")
        if (not isinstance(section_id, str) or not 1 <= len(section_id) <= 200
                or not isinstance(item, dict)):
            raise ValueError("Invalid production context section identity")
        tone, origin = item.get("tone"), item.get("origin", "author")
        if tone not in TONES or origin not in SOURCE_TYPES:
            raise ValueError("Invalid reviewed musical direction")
        note = item.get("note", "")
        if not isinstance(note, str) or len(note) > 240:
            raise ValueError("Production note exceeds 240 characters")
        source_id = item.get("source_run_id")
        source_hash = item.get("source_sha256")
        if origin == "q4-reviewed":
            if (not isinstance(source_id, str) or len(source_id) != 32
                    or not isinstance(source_hash, str) or len(source_hash) != 64
                    or any(c not in "0123456789abcdef" for c in source_id + source_hash)):
                raise ValueError("Reviewed Q4 context must reference a complete run and audio hash")
        elif source_id is not None or source_hash is not None:
            raise ValueError("Only reviewed Q4 context can reference a model run")
        cleaned = {"tone": tone, "origin": origin, "note": note.strip()}
        if origin == "q4-reviewed":
            cleaned["source_run_id"] = source_id
            cleaned["source_sha256"] = source_hash
        target = "sections" if section_id in section_ids else "archived"
        result[target][section_id] = cleaned
    return result


def path(folder: Path) -> Path:
    return folder / "generated" / "production-context.json"


def read(folder: Path, section_ids: set[str]) -> dict:
    location = path(folder)
    if not location.is_file():
        return empty()
    return normalize(json.loads(location.read_text(encoding="utf-8")), section_ids,
                     allow_retired=True)


def save(folder: Path, raw: dict, section_ids: set[str], expected_revision: int) -> dict:
    existing = read(folder, section_ids)
    if existing["revision"] != expected_revision:
        raise ValueError("Stale production context; reload before saving")
    cleaned = normalize(copy.deepcopy(raw), section_ids)
    # Keep reviews of retired section IDs historical and unassociated with
    # new boundaries. UI edits only active IDs; it cannot discard archives.
    for section_id, item in existing.get("archived", {}).items():
        if section_id not in cleaned["sections"] and section_id not in cleaned["archived"]:
            cleaned["archived"][section_id] = item
    if cleaned["revision"] != expected_revision:
        raise ValueError("Incorrect base production-context revision")
    cleaned["revision"] += 1
    target = path(folder)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(cleaned, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return cleaned
