"""Validated, non-destructive Song Harbor timeline section metadata.

Sections are canonical typed records in seconds, not engine-specific prompt strings.
Import/export adapters may translate to YuE2/ACE tags without interpreting stage directions.
"""
from __future__ import annotations

import math
import re
import uuid
from typing import Any

ALLOWED = ("Intro", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Instrumental",
           "Guitar Solo", "Outro", "End")
# Keep external display tags intentionally narrower than ACE stage directions.
TAG_RE = re.compile(
    r"^\[(Intro|Verse|Pre-Chorus|Chorus|Bridge|Instrumental|Guitar Solo|Outro|End)"
    r"(?:\s+(\d+))?(?:\s+(\d{1,3}:\d{2}(?:\.\d{1,3})?-\d{1,3}:\d{2}(?:\.\d{1,3})?))?\]$"
)

def seconds_to_stamp(value: float) -> str:
    minutes, seconds = divmod(value, 60)
    return f"{int(minutes)}:{seconds:06.3f}".rstrip("0").rstrip(".")

def stamp_to_seconds(value: str) -> float:
    mm, ss = value.split(":")
    secs = float(ss)
    if secs >= 60:
        raise ValueError("Seconds component must be below 60")
    return int(mm) * 60 + secs

def validate_sections(raw: list[dict[str, Any]], duration: float | None = None) -> list[dict[str, Any]]:
    if len(raw) > 256:
        raise ValueError("Maximum 256 sections per song")
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        ident = item.get("id") or uuid.uuid4().hex
        if not isinstance(ident, str) or not re.fullmatch(r"[0-9a-f]{32}", ident) or ident in seen:
            raise ValueError("Section IDs must be unique UUID-like hex values")
        seen.add(ident)
        kind = item.get("kind")
        number = item.get("number")
        if kind not in ALLOWED:
            raise ValueError("Unsupported section kind")
        if number is not None and (type(number) is not int or number < 1 or number > 99):
            raise ValueError("Section number must be between 1 and 99")
        if kind == "End" and number is not None:
            raise ValueError("End section cannot be numbered")
        try:
            start, end = float(item["start_seconds"]), float(item["end_seconds"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Section requires numeric start and end") from exc
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise ValueError("Section must have finite positive duration and nonnegative start")
        if duration is not None and end > duration + 0.005:
            raise ValueError("Section exceeds the source duration")
        clean.append({"id": ident, "kind": kind, "number": number,
                      "start_seconds": round(start, 3), "end_seconds": round(end, 3)})
    clean.sort(key=lambda s: (s["start_seconds"], s["end_seconds"]))
    for previous, current in zip(clean, clean[1:]):
        if current["start_seconds"] < previous["end_seconds"] - 0.001:
            raise ValueError("Sections may not overlap; use adjacent boundaries")
    return clean

def display_tag(section: dict[str, Any]) -> str:
    label = section["kind"]
    if section.get("number") is not None:
        label += " " + str(section["number"])
    return f"[{label} {seconds_to_stamp(section['start_seconds'])}-{seconds_to_stamp(section['end_seconds'])}]"

def parse_tag(tag: str) -> dict[str, Any]:
    match = TAG_RE.fullmatch(tag.strip())
    if not match:
        raise ValueError("Use [Chorus 1:15-1:45] or a supported plain section tag")
    kind, number, times = match.groups()
    if times is None:
        raise ValueError("A timed section tag is required to annotate audio")
    start, end = times.split("-")
    return validate_sections([{"kind": kind, "number": int(number) if number else None,
                               "start_seconds": stamp_to_seconds(start),
                               "end_seconds": stamp_to_seconds(end)}])[0]
