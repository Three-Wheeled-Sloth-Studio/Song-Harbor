"""Song Harbor production block notation, deliberately separate from section tags.

MVP executes pan, mid/side width, reverb send and reset. Other effects are rejected explicitly, not silently
accepted or misrepresented as applied audio processing.
"""
from __future__ import annotations
import re
from typing import Any

TOKEN = re.compile(
    r"(?i)^(?:(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.(?P<parameter>pan|reverb|width|space):(?P<value>center|left(?:\.\d{1,3})?|right(?:\.\d{1,3})?|reset|\d{1,3})"
    r"|(?P<reset>all\.reset|[A-Za-z][A-Za-z0-9_-]*\.reset))"
    r"(?:@(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
ALIASES = ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")
FINISH = re.compile(r"(?i)^Master\.(fade|tail):(\d+(?:\.\d{1,3})?)s(?::(smooth|linear))?$")


def parse_block(text: str) -> list[dict[str, Any]]:
    if len(text) > 4096 or not text.startswith("{") or not text.endswith("}"):
        raise ValueError("Production instructions must occupy one {...} line")
    tokens = text[1:-1].strip().split()
    if len(tokens) > 64:
        raise ValueError("Maximum 64 production directives per section")
    directives = []
    touched = set()
    for token in tokens:
        finishing = FINISH.fullmatch(token)
        if finishing:
            action, duration, curve = finishing.groups()
            action = action.lower()
            seconds = float(duration)
            if action == "fade" and not (0.05 <= seconds <= 30):
                raise ValueError("Master fade duration must be 0.05-30 seconds")
            if action == "tail" and not (0 <= seconds <= 10):
                raise ValueError("Master tail must be between 0 and 10 seconds")
            key = "master." + action
            if key in touched:
                raise ValueError("Duplicate master ending directive")
            touched.add(key)
            directives.append({"kind": action, "track": "Master", "seconds": seconds,
                               "curve": (curve or "smooth").lower()})
            continue
        match = TOKEN.fullmatch(token)
        if not match:
            raise ValueError(f"Unsupported production directive: {token}. Pan, width, reverb send and reset only for this release")
        name = match.group("track")
        reset = match.group("reset")
        if name:
            canonical = next((a for a in ALIASES if a.lower() == name.lower()), None)
            if not canonical:
                raise ValueError(f"Unknown stem alias: {name}")
            value = match.group("value").lower()
            parameter = match.group("parameter").lower()
            if parameter == "space":
                if not value.isdigit() or int(value)>40:
                    raise ValueError("Spatial reflection send must be 0-40 percent")
                directive = {"kind":"space", "track":canonical, "amount":int(value)}
            elif parameter == "width":
                if not value.isdigit() or int(value) > 150:
                    raise ValueError("Width must be 0-150 percent (100 is original width)")
                directive = {"kind": "width", "track": canonical, "width": int(value)}
            elif parameter == "reverb":
                if not value.isdigit() or int(value)>100:
                    raise ValueError("Reverb send must be 0-100 percent")
                directive = {"kind": "reverb", "track": canonical, "wet": int(value)/100}
            elif parameter == "pan" and value in ("center", "reset"):
                pan = 0.0
            elif parameter == "pan":
                if not (value.startswith("left") or value.startswith("right")):
                    raise ValueError("Pan target must be center, left or right")
                direction, _, amount = value.partition(".")
                n = int(amount) if amount else 100
                if n > 100:
                    raise ValueError("Pan percentage cannot exceed 100")
                pan = n / 100 * (-1 if direction == "left" else 1)
            key = canonical.lower() + "." + parameter
            if parameter == "pan":
                directive = {"kind": "pan", "track": canonical, "pan": pan}
        else:
            canonical = "all" if reset.lower() == "all.reset" else next(
                (a for a in ALIASES if a.lower() == reset[:-6].lower()), None)
            if not canonical:
                raise ValueError(f"Unknown reset scope: {reset}")
            key = canonical.lower() if canonical == "all" else canonical.lower()
            directive = {"kind": "reset", "track": canonical}
        if key in touched or ("all" in touched) or canonical.lower() in touched:
            raise ValueError("Duplicate or conflicting production directives within a section")
        if canonical == "all" and any(not x.startswith("master.") for x in touched):
            raise ValueError("all.reset cannot be combined with stem directives")
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
        elif d["kind"] in ("fade", "tail"):
            head = f"Master.{d['kind']}:{float(d['seconds']):g}s"
            if d["kind"] == "fade":
                head += ":" + d["curve"]
            rendered.append(head)
            continue
        elif d["kind"] == "space":
            head = f"{d['track']}.space:{d['amount']}"
        elif d["kind"] == "width":
            head = f"{d['track']}.width:{d['width']}"
        elif d["kind"] == "reverb":
            head = f"{d['track']}.reverb:{round(float(d['wet'])*100)}"
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
            if d["kind"] in ("reverb", "width", "space", "fade", "tail"):
                continue
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


def materialize_reverb(sections: list[dict[str, Any]],
                       blocks: dict[str, list[dict[str, Any]]],
                       files: list[str]) -> list[dict[str, Any]]:
    stems = {}
    for filename in files:
        for alias in ALIASES:
            if "(" + alias + ")" in filename:
                stems[alias] = filename
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for directive in blocks.get(section["id"], []):
            if directive["kind"] in ("pan", "width", "space", "fade", "tail"):
                continue
            targets = list(stems) if directive["kind"] == "reset" and directive["track"] == "all" else [directive["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError("Reverb target not in project")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "wet": directive["wet"] if directive["kind"] == "reverb" else 0.0,
                    "transition_seconds": directive["transition_seconds"],
                    "curve": directive["curve"],
                })
    return output



def materialize_width(sections: list[dict[str, Any]],
                      blocks: dict[str, list[dict[str, Any]]],
                      files: list[str]) -> list[dict[str, Any]]:
    """Compile explicit width changes; omitted sections inherit previous value."""
    stems = {alias: filename for filename in files for alias in ALIASES
             if "(" + alias + ")" in filename}
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for directive in blocks.get(section["id"], []):
            kind = directive["kind"]
            if kind not in ("width", "reset"):
                continue
            targets = (list(stems) if kind == "reset" and directive["track"] == "all"
                       else [directive["track"]])
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Width target {alias} not in project")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "width": directive["width"] if kind == "width" else 100,
                    "transition_seconds": directive["transition_seconds"],
                    "curve": directive["curve"],
                })
    return output

def materialize_space(sections: list[dict[str, Any]],
                      blocks: dict[str, list[dict[str, Any]]],
                      files: list[str]) -> list[dict[str, Any]]:
    stems={alias:filename for filename in files for alias in ALIASES
           if "(" + alias + ")" in filename}
    output=[]
    for section in sorted(sections,key=lambda s:s["start_seconds"]):
        for d in blocks.get(section["id"], []):
            if d["kind"] not in ("space","reset"):
                continue
            targets=list(stems) if d["kind"]=="reset" and d["track"]=="all" else [d["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Spatial reflection target {alias} not in project")
                output.append({"section_id":section["id"], "source_key":stems[alias],
                               "amount":d["amount"] if d["kind"]=="space" else 0,
                               "transition_seconds":d["transition_seconds"], "curve":d["curve"]})
    return output


def materialize_ending(sections: list[dict[str, Any]],
                       blocks: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """End-anchored dry mix fade and wet-tail extension.

    An explicit ending is restricted to the final audible section. The full
    post-roll is a single project-level setting, not a per-stem effect.
    """
    ordered = sorted(sections, key=lambda s: s["start_seconds"])
    ending = {"fade_seconds": 0.0, "tail_seconds": 0.0, "curve": "smooth"}
    final_id = ordered[-1]["id"] if ordered else None
    for section in ordered:
        for directive in blocks.get(section["id"], []):
            if directive["kind"] not in ("fade", "tail"):
                continue
            if section["id"] != final_id:
                raise ValueError("Master.fade and Master.tail belong to the final section")
            if directive["kind"] == "fade":
                if directive["seconds"] > section["end_seconds"]-section["start_seconds"]:
                    raise ValueError("Fade cannot be longer than the final section")
                ending["fade_seconds"] = directive["seconds"]
                ending["curve"] = directive["curve"]
            else:
                ending["tail_seconds"] = directive["seconds"]
    return ending
