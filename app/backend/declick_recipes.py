"""Non-destructive, revisioned de-click edit recipes scoped to one Song Harbor job."""
from __future__ import annotations
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any

RECIPE_FILE = "declick-repairs.json"
MAX_REPAIRS = 256


def _checked(item: dict[str, Any], filenames: set[str]) -> dict[str, Any]:
    filename = item.get("filename")
    if not isinstance(filename, str) or filename not in filenames:
        raise ValueError("Repair target is not an active project audio filename")
    time = item.get("time_seconds")
    half = item.get("half_window_ms")
    if not isinstance(time, (int, float)) or isinstance(time, bool) or not math.isfinite(time) or time < 0 or time > 900:
        raise ValueError("Repair time must be within the song")
    if not isinstance(half, (int, float)) or isinstance(half, bool) or not math.isfinite(half) or not .15 <= half <= 3:
        raise ValueError("De-click half-window must be 0.15–3ms")
    rid = item.get("id")
    if not isinstance(rid, str) or not rid or len(rid) > 64:
        raise ValueError("Repair ID is missing")
    # Require exact immutable original-asset identity before accepting.
    key = item.get("source_key")
    if not isinstance(key, str) or len(key)>220 or not key:
        raise ValueError("Repair source identity is missing")
    return {"id": rid, "filename": filename, "source_key": key,
            "time_seconds": float(time), "half_window_ms": float(half)}


def read(folder: Path) -> list[dict[str, Any]]:
    path = folder / RECIPE_FILE
    if not path.exists():
        return []
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("version") != 1 or not isinstance(record.get("repairs"), list):
        raise ValueError("Unsupported de-click recipe version")
    return record["repairs"]


def append(folder: Path, candidate: dict[str, Any], filenames: set[str]) -> list[dict[str, Any]]:
    item = _checked(candidate, filenames)
    existing = read(folder)
    if len(existing) >= MAX_REPAIRS:
        raise ValueError("Project de-click repair limit reached")
    if any(row.get("id") == item["id"] for row in existing):
        raise ValueError("Repair ID already exists")
    # Preserve historical recipe list; atomically replace only the manifest.
    result = [*existing, item]
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / (RECIPE_FILE + "." + uuid.uuid4().hex + ".tmp")
    try:
        tmp.write_text(json.dumps({"version": 1, "repairs": result}, indent=2), encoding="utf-8")
        os.replace(tmp, folder / RECIPE_FILE)
    finally:
        tmp.unlink(missing_ok=True)
    return result


def remove(folder: Path, ident: str) -> list[dict[str, Any]]:
    previous = read(folder)
    remaining = [row for row in previous if row.get("id") != ident]
    if len(previous) == len(remaining):
        raise ValueError("Repair not found")
    tmp = folder / (RECIPE_FILE + "." + uuid.uuid4().hex + ".tmp")
    try:
        tmp.write_text(json.dumps({"version": 1, "repairs": remaining}, indent=2), encoding="utf-8")
        os.replace(tmp, folder / RECIPE_FILE)
    finally:
        tmp.unlink(missing_ok=True)
    return remaining
