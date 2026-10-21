"""Song Harbor production block notation, deliberately separate from section tags.

MVP executes PAN only. Other effects are rejected explicitly, not silently
accepted or misrepresented as applied audio processing.
"""
from __future__ import annotations
import re
from typing import Any

TOKEN = re.compile(
    r"(?i)^(?:(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.pan:(?P<value>center|left(?:\.\d{1,3})?|right(?:\.\d{1,3})?|reset)"
    r"|(?P<reset>all\.reset|[A-Za-z][A-Za-z0-9_-]*\.reset))"
    r"(?:@(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
ALIASES = ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")


def parse_block(text: str) -> list[dict[str, Any]]:
    if len(text) > 4096 or not text.startswith("{") or not text.endswith("}"):
        raise ValueError("Production instructions must occupy one {...} line")
    tokens = text[1:-1].strip().split()
    if len(tokens) > 64:
        raise ValueError("Maximum 64 production directives per section")
    directives = []
    touched = set()
    for token in tokens:
        match = TOKEN.fullmatch(token)
        if not match:
            raise ValueError(f"Unsupported production directive: {token}. Pan and reset only for this release")
        name = match.group("track")
        reset = match.group("reset")
        if name:
            canonical = next((a for a in ALIASES if a.lower() == name.lower()), None)
            if not canonical:
                raise ValueError(f"Unknown stem alias: {name}")
            value = match.group("value").lower()
            if value in ("center", "reset"):
                pan = 0.0
            else:
                direction, _, amount = value.partition(".")
                n = int(amount) if amount else 100
                if n > 100:
                    raise ValueError("Pan percentage cannot exceed 100")
                pan = n / 100 * (-1 if direction == "left" else 1)
            key = canonical.lower()
            directive = {"kind": "pan", "track": canonical, "pan": pan}
        else:
            canonical = "all" if reset.lower() == "all.reset" else next(
                (a for a in ALIASES if a.lower() == reset[:-6].lower()), None)
            if not canonical:
                raise ValueError(f"Unknown reset scope: {reset}")
            key = canonical.lower() if canonical == "all" else canonical.lower()
            directive = {"kind": "reset", "track": canonical}
        if key in touched or ("all" in touched):
            raise ValueError("Duplicate or conflicting production directives within a section")
        if canonical == "all" and touched:
            raise ValueError("all.reset cannot be combined with other section directives")
        touched.add(key)
        duration = float(match.group("seconds") or 1)
        if duration < 0.05 or duration > 30:
            raise ValueError("Transition must be between 0.05 and 30 seconds")
        directive["transition_seconds"] = duration
        directive["curve"] = (match.group("curve") or "smooth").lower()
        directives.append(directive)
    return directives


def render_block(directives: list[dict[str, Any]]) -> str:
    rendered = []
    for d in directives:
        suffix = f"@{d['transition_seconds']:g}s:{d['curve']}"
        if d["kind"] == "reset":
            head = "all.reset" if d["track"] == "all" else d["track"] + ".reset"
        else:
            value = float(d["pan"])
            if value == 0:
                pos = "center"
            else:
                pos = ("left" if value < 0 else "right") + f".{round(abs(value)*100)}"
            head = f"{d['track']}.pan:{pos}"
        rendered.append(head + suffix)
    return "{" + " ".join(rendered) + "}"


def materialize_pan(sections: list[dict[str, Any]],
                    blocks: dict[str, list[dict[str, Any]]],
                    files: list[str]) -> list[dict[str, Any]]:
    """Compile inheritance and resets into explicit per-section pan targets.

    This representation is compatible with the existing shared-clock preview.
    Missing directives hold the previous target. A reset restores track default
    (currently center), but does not alter manual mixer settings.
    """
    stems = {}
    for filename in files:
        for alias in ALIASES:
            if "(" + alias + ")" in filename:
                stems[alias] = filename
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for d in blocks.get(section["id"], []):
            targets = stems.keys() if d["kind"] == "reset" and d["track"] == "all" else [d["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Production track {alias} does not exist in this song")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "pan": d["pan"] if d["kind"] == "pan" else 0.0,
                    "transition_seconds": d["transition_seconds"],
                    "curve": d["curve"],
                })
    return output
