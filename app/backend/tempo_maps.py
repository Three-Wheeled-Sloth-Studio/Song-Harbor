"""Provider-neutral, revisioned tempo-map composition assets.

A tempo map is *not* a master tempo estimate. Values are anchored at fixed
sample positions; candidate estimates remain distinct from author-accepted
anchors. This module does not warp audio, rewrite MIDI, or call a model.
"""
from __future__ import annotations

import copy
import json
import math
import os
import re
import uuid
from pathlib import Path

SCHEMA_VERSION = 1
SAMPLE_RATE = 48000
MAX_DURATION_S = 3600
MAX_ANCHORS = 2048
MAX_OBSERVATIONS = 4096
ID_RE = re.compile(r"^[0-9a-f]{32}$")


def _id(value: object, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {field}")
    return value


def _int(value: object, field: str, lo: int, hi: int) -> int:
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(f"{field} must be integer in [{lo}, {hi}]")
    return value


def _bpm(value: object) -> float:
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError("BPM must be finite")
    if not 20 <= value <= 320:
        raise ValueError("BPM must be between 20 and 320")
    return round(float(value), 4)


def _anchor(row: dict, duration: int) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Tempo anchor must be an object")
    result = {
        "id": _id(row.get("id"), "tempo anchor ID"),
        "sample": _int(row.get("sample"), "tempo anchor sample", 0, duration - 1),
        "bpm": _bpm(row.get("bpm")),
        "transition": row.get("transition", "step"),
        "origin": row.get("origin", "author"),
    }
    if result["transition"] not in ("step", "linear"):
        raise ValueError("Tempo transition must be step or linear")
    if result["origin"] not in ("author", "accepted-candidate"):
        raise ValueError("Unknown tempo anchor origin")
    meter = row.get("meter", [4, 4])
    if not isinstance(meter, list) or len(meter) != 2:
        raise ValueError("Meter must be [numerator, denominator]")
    _int(meter[0], "meter numerator", 1, 32)
    if type(meter[1]) is not int or meter[1] not in (1, 2, 4, 8, 16, 32):
        raise ValueError("Invalid meter denominator")
    result["meter"] = meter[:]
    section_id = row.get("section_id")
    if section_id is not None:
        result["section_id"] = _id(section_id, "section ID")
    return result


def _observation(row: dict, duration: int) -> dict:
    if not isinstance(row, dict):
        raise ValueError("Tempo observation must be an object")
    start = _int(row.get("start_sample"), "observation start", 0, duration - 1)
    end = _int(row.get("end_sample"), "observation end", 1, duration)
    if end <= start:
        raise ValueError("Observation must have positive duration")
    method = row.get("method")
    if not isinstance(method, str) or not 1 <= len(method) <= 160:
        raise ValueError("Observation method required")
    result = {
        "id": _id(row.get("id"), "observation ID"),
        "start_sample": start, "end_sample": end,
        "method": method,
        "bpm": _bpm(row["bpm"]) if row.get("bpm") is not None else None,
        "status": row.get("status", "unverified"),
        "alternatives": [],
    }
    if result["status"] not in ("unverified", "plausible", "confirmed", "rejected"):
        raise ValueError("Invalid observation status")
    alternatives = row.get("alternatives", [])
    if not isinstance(alternatives, list) or len(alternatives) > 8:
        raise ValueError("Too many alternative tempos")
    result["alternatives"] = [_bpm(x) for x in alternatives]
    for name in ("source_sha256", "source_revision", "provider", "evidence"):
        value = row.get(name)
        if value is not None:
            if not isinstance(value, str) or len(value) > 500:
                raise ValueError(f"Invalid {name}")
            result[name] = value
    if row.get("confidence") is not None:
        value = row["confidence"]
        if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("Invalid observation confidence")
        result["confidence"] = float(value)
    else:
        result["confidence"] = None
    return result


def validate(asset: dict) -> dict:
    if not isinstance(asset, dict) or asset.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported tempo-map schema")
    _id(asset.get("asset_id"), "asset ID")
    _int(asset.get("revision"), "revision", 0, 1000000)
    if asset.get("sample_rate") != SAMPLE_RATE:
        raise ValueError("Tempo-map sample rate must be 48000")
    duration = _int(asset.get("duration_samples"), "duration_samples", 1, SAMPLE_RATE * MAX_DURATION_S)
    anchors, observations = asset.get("anchors"), asset.get("observations")
    if not isinstance(anchors, list) or len(anchors) > MAX_ANCHORS:
        raise ValueError("Invalid tempo-map anchors")
    if not isinstance(observations, list) or len(observations) > MAX_OBSERVATIONS:
        raise ValueError("Invalid tempo observations")
    clean = copy.deepcopy(asset)
    clean["anchors"] = sorted((_anchor(x, duration) for x in anchors), key=lambda x: x["sample"])
    clean["observations"] = [_observation(x, duration) for x in observations]
    if len({a["sample"] for a in clean["anchors"]}) != len(clean["anchors"]):
        raise ValueError("Two accepted tempo anchors cannot occupy one sample")
    if len({a["id"] for a in clean["anchors"]}) != len(clean["anchors"]):
        raise ValueError("Duplicate tempo anchor IDs")
    if len({o["id"] for o in clean["observations"]}) != len(clean["observations"]):
        raise ValueError("Duplicate tempo observation IDs")
    return clean


def create(duration_samples: int) -> dict:
    asset = {"schema_version": SCHEMA_VERSION, "asset_id": uuid.uuid4().hex,
             "revision": 0, "sample_rate": SAMPLE_RATE,
             "duration_samples": duration_samples, "anchors": [], "observations": []}
    return validate(asset)


def revise(asset: dict, base_revision: int, *, anchors: list | None = None,
           observations: list | None = None) -> dict:
    """Explicit human save. No automatic promotion of candidate observations."""
    current = validate(asset)
    if base_revision != current["revision"]:
        raise ValueError("Stale tempo map revision; reload before saving")
    if anchors is None and observations is None:
        raise ValueError("No tempo-map changes supplied")
    if anchors is not None:
        current["anchors"] = anchors
    if observations is not None:
        current["observations"] = observations
    current["revision"] += 1
    return validate(current)


def bpm_at(asset: dict, sample: int) -> float | None:
    """Read-only sample-position query; linear ramps interpolate *toward* next anchor."""
    current = validate(asset)
    _int(sample, "sample", 0, current["duration_samples"] - 1)
    anchors = current["anchors"]
    if not anchors or sample < anchors[0]["sample"]:
        return None
    for i in range(len(anchors) - 1):
        left, right = anchors[i], anchors[i + 1]
        if left["sample"] <= sample < right["sample"]:
            if left["transition"] == "linear":
                t = (sample - left["sample"]) / (right["sample"] - left["sample"])
                return left["bpm"] + t * (right["bpm"] - left["bpm"])
            return left["bpm"]
    return anchors[-1]["bpm"]


def _path(job_root: Path) -> Path:
    return job_root / "generated" / "tempo-map.json"


def read(job_root: Path) -> dict | None:
    target = _path(job_root)
    if not target.is_file():
        return None
    return validate(json.loads(target.read_text(encoding="utf-8")))


def save(job_root: Path, asset: dict, *, expected_revision: int | None) -> dict:
    """Compare-and-swap must be serialized by caller for simultaneous API writes."""
    clean = validate(asset)
    existing = read(job_root)
    if existing is None:
        if expected_revision is not None or clean["revision"] != 0:
            raise ValueError("Stale tempo map: asset has not been initialized")
    elif existing["revision"] != expected_revision or existing["asset_id"] != clean["asset_id"]:
        raise ValueError("Stale tempo map: project asset changed")
    target = _path(job_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(clean, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return clean
