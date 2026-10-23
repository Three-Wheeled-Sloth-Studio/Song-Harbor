"""Section import/export adapters; all imports are validated before persistence.

Readable Song Harbor section tags are independent of generation-engine prompts.
Spatial annotations are stored as nonexecuting proposals keyed to section IDs.
"""
from __future__ import annotations
import json
import math
import re
from typing import Any
import sections
import production_cues
import section_production

def parse_untimed(line: str) -> dict[str, Any]:
    """A plain section header may include a verse number and spatial proposals."""
    if len(line) > 4096 or not line.startswith("[") or not line.endswith("]"):
        raise ValueError("Expected a bracketed section header")
    text = line[1:-1].strip()
    kind = next((name for name in production_cues.TYPES if
                 text.startswith(name) and
                 (len(text) == len(name) or text[len(name)].isspace())), None)
    if kind is None:
        raise ValueError("Unknown section type")
    remainder = text[len(kind):].strip()
    number = None
    tokens = remainder.split()
    if tokens and tokens[0].isdigit():
        number = int(tokens.pop(0))
        if number < 1 or number > 99 or kind == "End":
            raise ValueError("Invalid section number")
    # Reuse the same spatial grammar as timed tags without inventing a time.
    directives = []
    used = set()
    for token in tokens:
        if token.count(":") != 1:
            raise ValueError("Expected Track:Width[-Bias] or a numbered section")
        track, width_bias = token.split(":")
        pieces = width_bias.split("-")
        if (not production_cues.NAME.fullmatch(track) or track in used
                or len(pieces) not in (1, 2)
                or pieces[0] not in production_cues.WIDTHS
                or (len(pieces) == 2 and pieces[1] not in production_cues.BIASES)):
            raise ValueError("Invalid or duplicate spatial directive")
        used.add(track)
        directives.append({"track_alias": track, "width": pieces[0].lower(),
                           "bias": (pieces[1] if len(pieces) == 2 else "Center").lower()})
        if len(directives) > 64:
            raise ValueError("Too many spatial directives")
    return {"kind": kind, "number": number, "spatial": directives}


def parse(content: str, aliases:tuple[str,...]=section_production.ALIASES) -> list[dict[str, Any]]:
    stripped = content.strip()
    if not stripped:
        raise ValueError("No sections supplied")
    if stripped.startswith("{") or stripped.startswith("[{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON") from exc
        entries = data.get("sections") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise ValueError("Expected a sections array")
        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Each section must be an object")
            result.append({key: entry[key] for key in
                           ("id", "kind", "number", "start_seconds", "end_seconds", "spatial", "lyrics", "production")
                           if key in entry})
        return result

    result = []
    for index, line in enumerate(content.splitlines(), 1):
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        if stripped_line.startswith("{") and stripped_line.endswith("}") and result:
            if "production" in result[-1]:
                raise ValueError(f"Line {index}: Only one production block per section")
            try:
                result[-1]["production"] = section_production.parse_block(stripped_line,aliases)
            except ValueError as exc:
                raise ValueError(f"Line {index}: {exc}") from exc
            continue
        if stripped_line.startswith("{") and not result:
            raise ValueError(f"Line {index}: Production block needs a preceding section")
        if not stripped_line.startswith("["):
            if result:
                result[-1].setdefault("lyrics", []).append(line.rstrip())
            continue
        try:
            if re.search(r"\d{1,3}:\d{2}(?:\.\d{1,3})?-", stripped_line):
                cue = production_cues.parse_cue(stripped_line)
                result.append({**cue["section"], "spatial": cue["spatial"]})
            else:
                result.append(parse_untimed(stripped_line))
        except ValueError as exc:
            raise ValueError(f"Line {index}: {exc}") from exc
    for item in result:
        if "lyrics" in item:
            item["lyrics"] = "\n".join(item["lyrics"]).strip()
    if not result:
        raise ValueError("No recognized section headers found")
    return result


def assign_initial_times(imported: list[dict[str, Any]], mode: str,
                         previous: list[dict[str, Any]],
                         duration: float | None) -> tuple[list[dict[str, Any]], bool, bool]:
    """Auto-distribute untimed sections across the available song interval."""
    timed = [("start_seconds" in s or "end_seconds" in s) for s in imported]
    if any(timed) and not all(timed):
        raise ValueError("Use either all timed or all untimed sections in one import")
    if all(timed):
        return imported, False, False
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("Song duration is required to place untimed sections")
    # [End] is a terminator, not an audible section with a long arbitrary duration.
    had_end = imported[-1]["kind"] == "End"
    if had_end:
        imported = imported[:-1]
    if not imported:
        raise ValueError("A song must contain at least one audible section")
    if any(s["kind"] == "End" for s in imported):
        raise ValueError("[End] is only supported as the final untimed terminator")
    start = max((float(x["end_seconds"]) for x in previous), default=0.0) if mode == "append" else 0.0
    available = float(duration) - start
    if available < len(imported) * 0.1:
        raise ValueError("Not enough unassigned song time to distribute these sections")
    result = []
    for index, section in enumerate(imported):
        first = round(start + available * index / len(imported), 3)
        last = (round(float(duration), 3) if index == len(imported) - 1
                else round(start + available * (index + 1) / len(imported), 3))
        result.append({**section, "start_seconds": first, "end_seconds": last})
    return result, True, had_end


def validate_spatial(raw:Any)->list[dict[str,str]]:
    if not isinstance(raw,list) or len(raw)>64:
        raise ValueError("Spatial directives must be a list with at most 64 entries")
    clean=[]
    used=set()
    for item in raw:
        if not isinstance(item,dict):raise ValueError("Invalid spatial directive")
        alias=item.get("track_alias")
        width=item.get("width")
        bias=item.get("bias","center")
        if not isinstance(alias,str) or not production_cues.NAME.fullmatch(alias) or alias in used:
            raise ValueError("Invalid or duplicate track alias")
        if width not in {x.lower() for x in production_cues.WIDTHS}:
            raise ValueError("Invalid width")
        if bias not in {x.lower() for x in production_cues.BIASES}:
            raise ValueError("Invalid bias")
        used.add(alias)
        clean.append({"track_alias":alias,"width":width,"bias":bias})
    return clean

def apply(project: dict[str, Any], content: str, mode: str,
          duration: float | None) -> dict[str, Any]:
    if mode not in ("replace", "append"):
        raise ValueError("Mode must be replace or append")
    files=project.get("files",[])
    tracks=project.get("source_tracks",[])
    children=project.get("channel_children",{})
    parents=section_production.source_aliases(files,tracks) or section_production.ALIASES
    aliases=section_production.source_aliases(files,tracks,children) or parents
    imported = parse(content,aliases)
    old = project.get("sections", [])
    imported, distributed, end_terminator = assign_initial_times(imported, mode, old, duration)
    # Editing the timed text of the existing arrangement should preserve stable
    # section IDs when section order and identities are unchanged.
    if mode == "replace" and len(imported) == len(old):
        for current, prior in zip(imported, old):
            if (not current.get("id") and current["kind"] == prior.get("kind")
                    and current.get("number") == prior.get("number")):
                current["id"] = prior["id"]
    combined = (old if mode == "append" else []) + imported
    validated = sections.validate_sections(combined, duration=duration)
    old_proposals = project.get("section_spatial_proposals", {})
    old_lyrics = project.get("section_lyrics", {})
    old_production = project.get("section_production", {})
    proposals = {x["id"]: old_proposals[x["id"]] for x in validated
                 if x["id"] in old_proposals and any(y.get("id") == x["id"] for y in old)}
    lyrics = {x["id"]: old_lyrics[x["id"]] for x in validated
              if x["id"] in old_lyrics and any(y.get("id") == x["id"] for y in old)}
    production = {x["id"]: old_production[x["id"]] for x in validated
                  if mode == "append" and x["id"] in old_production
                  and any(y.get("id") == x["id"] for y in old)}
    for item in imported:
        if "spatial" not in item and "lyrics" not in item and "production" not in item:
            continue
        spatial = validate_spatial(item["spatial"]) if "spatial" in item else None
        match = next((s for s in validated if
                      s["kind"] == item.get("kind") and s["number"] == item.get("number")
                      and s["start_seconds"] == round(float(item["start_seconds"]), 3)
                      and s["end_seconds"] == round(float(item["end_seconds"]), 3)), None)
        if match is None:
            raise ValueError("Unable to match imported spatial annotation")
        if spatial is not None:
            proposals[match["id"]] = spatial
        if "production" in item:
            if not isinstance(item["production"], list):
                raise ValueError("Production directives must be a list")
            # Normalize even JSON imports through the same constrained grammar.
            parsed = section_production.parse_block(section_production.render_block(item["production"]),aliases)
            if parsed:
                production[match["id"]] = parsed
        if "lyrics" in item:
            if not isinstance(item["lyrics"], str) or len(item["lyrics"]) > 20000:
                raise ValueError("Lyrics text must be at most 20000 characters per section")
            lyrics[match["id"]] = item["lyrics"]
    # Child processing is presently supported for individual gain, pan,
    # reverb sends and EQ. Never silently claim child width/spatial/dynamics.
    child_aliases={alias.casefold() for alias in aliases if alias not in parents}
    for directives in production.values():
        for directive in directives:
            if directive.get("track","").casefold() in child_aliases and directive["kind"] not in ("gain","pan","reverb","eq","reset"):
                raise ValueError("Child split channels currently support gain, pan, EQ and reverb only")
    auto_pan_targets = section_production.materialize_auto_pan(validated, production, files, tracks, children)
    # Keep authored macro intents in section_production for roundtrip.
    # Resolve deterministic effect targets only while materializing automation.
    effective = section_production.expand_evolution(
        section_production.expand_broadcast(production, parents), parents, aliases)
    pan_targets = section_production.materialize_pan(validated, effective, files, tracks, children)
    reverb_targets = section_production.materialize_reverb(validated, effective, files, tracks, children)
    width_targets = section_production.materialize_width(validated, effective, files, tracks, children)
    space_targets = section_production.materialize_space(validated, effective, files, tracks, children)
    eq_targets = section_production.materialize_eq(validated, effective, files, tracks, children)
    dynamics_targets = section_production.materialize_dynamics(validated, effective, files, tracks, children)
    gain_targets = section_production.materialize_gain(validated, effective, files, tracks, children)
    ending = section_production.materialize_ending(validated, production)
    return {"sections": validated, "section_spatial_proposals": proposals,
            "section_production": production, "section_pan_automation": pan_targets,
            "section_reverb_automation": reverb_targets, "section_width_automation": width_targets,
            "section_space_automation": space_targets, "section_eq_automation": eq_targets,
            "section_dynamics_automation": dynamics_targets, "section_gain_automation": gain_targets,
            "section_auto_pan": auto_pan_targets,
            "section_ending": ending,
            "section_lyrics": lyrics,
            "imported_count": len(imported), "auto_distributed": distributed,
            "end_terminator_ignored": end_terminator}


def render_tags(project:dict[str,Any])->str:
    cues=project.get("section_spatial_proposals",{})
    lines=[]
    for entry in project.get("sections",[]):
        head=sections.display_tag(entry)[:-1]
        edits=cues.get(entry["id"],[])
        for item in edits:
            head+=" "+item["track_alias"]+":"+item["width"].capitalize()
            if item["bias"]!="center":head+="-"+item["bias"].capitalize()
        lines.append(head+"]")
        directives = project.get("section_production", {}).get(entry["id"], [])
        if directives:
            lines.append(section_production.render_block(directives))
        lyric = project.get("section_lyrics", {}).get(entry["id"], "")
        if lyric:
            lines.append(lyric)
            lines.append("")
    return "\n".join(lines)
