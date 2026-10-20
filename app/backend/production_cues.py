"""Prototype parser for readable, bounded section-scoped spatial production cues.

This compiles human-friendly notation into typed *proposals*; it executes no DSP.
The grammar is intentionally independent of YuE2 / ACE prompting.
"""
from __future__ import annotations

import re
from typing import Any

WIDTHS = {"Narrow", "Moderate", "Wide", "Expansive"}
BIASES = {"Left", "Right", "Center"}
TYPES = ("Guitar Solo", "Pre-Chorus", "Instrumental", "Chorus", "Bridge",
         "Verse", "Intro", "Outro", "End")
CLOCK = r"(?:\d{1,3}:\d{2}(?:\.\d{1,3})?)"
TIME = re.compile(rf"^({CLOCK})-({CLOCK})(?:\s+|$)")
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

def stamp(value: str) -> float:
    minute, seconds = value.split(":")
    sec = float(seconds)
    if sec >= 60:
        raise ValueError("Invalid seconds in timecode")
    return int(minute) * 60 + sec

def parse_cue(line: str) -> dict[str, Any]:
    if len(line) > 4096 or not line.startswith("[") or not line.endswith("]"):
        raise ValueError("Cues must be bracketed and at most 4096 characters")
    text = line[1:-1].strip()
    kind = next((name for name in TYPES if text.startswith(name) and
                 (len(text) == len(name) or text[len(name)].isspace())), None)
    if kind is None:
        raise ValueError("Unrecognized section")
    text = text[len(kind):].strip()
    section_number: int | None = None
    # Optional section index, e.g. Verse 2 1:15-1:45.
    numbered = re.match(r"^(\d{1,2})\s+(?=\d{1,3}:)", text)
    if numbered:
        section_number = int(numbered.group(1))
        if section_number < 1:
            raise ValueError("Section number must be positive")
        text = text[numbered.end():]
    span = TIME.match(text)
    if not span:
        raise ValueError("Section cue requires a start-end time range")
    start, end = map(stamp, span.groups())
    if start >= end:
        raise ValueError("Section end must be after start")
    text = text[span.end():].strip()
    edits = []
    encountered = set()
    for token in text.split():
        if len(edits) >= 64:
            raise ValueError("Too many processing directives")
        if token.count(":") != 1:
            raise ValueError("Expected Track:Width[-Bias]")
        target, parameter = token.split(":")
        if not NAME.fullmatch(target) or target in encountered:
            raise ValueError("Track references must be unique simple names")
        encountered.add(target)
        choices = parameter.split("-")
        if len(choices) not in (1, 2) or choices[0] not in WIDTHS:
            raise ValueError("Expected Narrow, Moderate, Wide or Expansive")
        bias = choices[1] if len(choices) == 2 else "Center"
        if bias not in BIASES:
            raise ValueError("Expected Left, Center or Right bias")
        edits.append({"track_alias": target, "width": choices[0].lower(),
                      "bias": bias.lower()})
    return {"section": {"kind": kind, "number": section_number,
                        "start_seconds": start, "end_seconds": end},
            "spatial": edits, "status": "proposal"}

def compile_cues(lines: list[str], known_tracks: set[str] | None = None) -> list[dict[str, Any]]:
    if len(lines) > 256:
        raise ValueError("Too many cues")
    parsed = [parse_cue(line) for line in lines if line.strip()]
    if known_tracks is not None:
        unknown = {item["track_alias"] for cue in parsed for item in cue["spatial"]} - known_tracks
        if unknown:
            raise ValueError("Unknown track alias: " + ", ".join(sorted(unknown)))
    return parsed
