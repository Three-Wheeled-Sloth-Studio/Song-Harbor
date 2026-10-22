"""Generate readable, approximate YouTube caption timing from saved Song Harbor sections.

The output is standard UTF-8 SubRip (.srt), not a claim of aligned
word-level transcription. Source text and timing are never modified.
"""
from __future__ import annotations
import re
from typing import Any

_STAGE = re.compile(r"^\s*\([^\n]*\)\s*$")
_MAX_CAPTION_CHARS = 80
_SHORT_LINE_CHARS = 29


def _chunks(lines: list[str]) -> list[list[str]]:
    """Usually two lyric lines. Three brief lines or one long line."""
    result: list[list[str]] = []
    index = 0
    while index < len(lines):
        first = lines[index]
        if len(first) >= _MAX_CAPTION_CHARS:
            count = 1
        elif index + 2 < len(lines) and len(lines) - index != 4 and all(
            len(x) <= _SHORT_LINE_CHARS for x in lines[index:index + 3]
        ):
            count = 3
        elif index + 1 < len(lines) and (
            len(first) + len(lines[index + 1]) <= _MAX_CAPTION_CHARS
        ):
            count = 2
        else:
            count = 1
        result.append(lines[index:index + count])
        index += count
    return result


def _stamp(seconds: float) -> str:
    ms = max(0, round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def render_srt(project: dict[str, Any]) -> dict[str, Any]:
    sections = sorted(project.get("sections", []), key=lambda s: s["start_seconds"])
    lyrics = project.get("section_lyrics", {})
    cues: list[tuple[float,float,list[str]]] = []
    ignored_directions = 0
    warnings: list[str] = []
    for section in sections:
        start = float(section["start_seconds"])
        end = float(section["end_seconds"])
        if end <= start:
            continue
        raw = lyrics.get(section["id"], "")
        lines = []
        for line in raw.splitlines():
            clean = line.strip()
            if not clean:
                continue
            if _STAGE.fullmatch(clean):
                ignored_directions += 1
                continue
            lines.append(clean)
        if not lines:
            continue
        groups = _chunks(lines)
        # Evenly distribute *source lines* over their section. A 3-line cue
        # spans three equal lyric slots, a 1-line cue one slot.
        slot = (end - start) / len(lines)
        consumed = 0
        for group in groups:
            cue_start = start + consumed * slot
            consumed += len(group)
            cue_end = min(end, start + consumed * slot)
            if cue_end - cue_start < 0.35:
                warnings.append(f"Brief caption in {section['kind']}")
            cues.append((cue_start, cue_end, group))
    if not cues:
        raise ValueError("No saved lyric lines with timed sections to export")
    result = []
    for number,(start,end,lines) in enumerate(cues, 1):
        result.append(f"{number}\n{_stamp(start)} --> {_stamp(end)}\n"
                      + "\n".join(lines))
    return {"content": "\n\n".join(result) + "\n",
            "cue_count":len(cues),
            "excluded_directions":ignored_directions,
            "warnings":sorted(set(warnings)),
            "timing":"Estimated evenly by lyric line inside each saved section; review against vocal playback."}
