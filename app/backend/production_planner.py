"""Non-destructive, evidence-bounded section production suggestions.

This is a deterministic first provider, not an LLM or a loudness solver.
Existing section structure, lyrics, and authored effects take precedence.
"""
from __future__ import annotations

import copy
import math

import section_import
import section_production

PROFILE = {
    "id": "infra-choir-v1",
    "name": "Infra Choir",
    "lead": "Intelligible center-focused female lead",
    "character": "Gothic industrial, orchestral atmosphere and heavy rhythmic contrast",
    "rules": [
        "Retain existing arrangement and all lyrics",
        "Respect existing spatial placement and stereo differentiation",
        "Keep low end anchored; avoid automatic master leveling",
        "Use long ramps except deliberate short dramatic turns",
        "Do not overwrite authored section directives",
    ],
}


def _measurement(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Measurements must be objects")
    section_id = raw.get("sectionId")
    if not isinstance(section_id, str) or not section_id:
        raise ValueError("Measurement is missing a section ID")
    values = {}
    for field, minimum, maximum in (
        ("rmsDbfs", -160, 24), ("peakDbfs", -160, 24),
        ("widthDb", -100, 70), ("balanceDb", -100, 100),
        ("intensity", 0, 1),
    ):
        value = raw.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError("Invalid measured " + field)
        values[field] = float(value)
    return {"sectionId": section_id, **values}


def _owned(directives: list[dict], alias: str, kind: str) -> bool:
    return any(
        (str(item.get("track", "")).casefold() in (alias.casefold(), "all")
         and item.get("kind") in (kind, "reset", "evolve"))
        or (item.get("kind") == "reset" and str(item.get("track", "")).casefold() == "all")
        for item in directives
    )


def generate(project: dict, metrics: list[dict], *, spatial: int = 65,
             dynamics: int = 60, direction: str = "enhance") -> dict:
    """Return a validated import-ready text proposal; never mutate project."""
    if type(spatial) is not int or not 0 <= spatial <= 100:
        raise ValueError("Spatial ambition must be 0-100")
    if type(dynamics) is not int or not 0 <= dynamics <= 100:
        raise ValueError("Dynamic ambition must be 0-100")
    if direction not in ("enhance", "ominous", "movement", "contrast"):
        raise ValueError("Unknown production direction")
    sections = project.get("sections", [])
    if not sections:
        raise ValueError("Create and save song sections before planning production")
    if not isinstance(metrics, list):
        raise ValueError("Invalid measurement collection")
    by_id = {}
    for item in metrics:
        row = _measurement(item)
        if row["sectionId"] in by_id:
            raise ValueError("Duplicate section measurement")
        by_id[row["sectionId"]] = row
    if {x["id"] for x in sections} != set(by_id):
        raise ValueError("Scan the current mix to measure every saved section before planning")
    files = project.get("files", [])
    parents = section_production.source_aliases(files, project.get("source_tracks", []))
    known = {x.lower(): x for x in parents}
    # Only plan on known parent stems. Child L/R spatial settings are retained.
    spatial_alias = next((known[a] for a in ("other", "guitar", "piano") if a in known), None)
    vocal = known.get("vocals")
    clone = copy.deepcopy(project)
    added = []
    notes = []
    for index, section in enumerate(sections):
        metric = by_id[section["id"]]
        existing = list(clone.get("section_production", {}).get(section["id"], []))
        lower = section["kind"].lower()
        is_peak = lower in ("chorus", "pre-chorus")
        is_break = lower in ("bridge", "instrumental", "outro")
        length = section["end_seconds"] - section["start_seconds"]
        ramp = round(max(.05, min(length * (.38 if is_peak else .44), 14)), 2)
        # Use only clear mix-level evidence and modest bounded targets.
        # widthDb closer to zero denotes more natural side content already.
        wide = metric["widthDb"] > -10
        polarized = abs(metric["balanceDb"]) >= 2
        quiet = metric["rmsDbfs"] < -30
        step = []
        if spatial_alias and not _owned(existing, spatial_alias, "width"):
            if not wide and not polarized and spatial >= 35:
                target = min(145, 100 + round(spatial * (.38 if is_peak or is_break else .17)))
                if direction == "movement":
                    target = min(145, target + 10)
                if target > 108:
                    step.append(f"{spatial_alias}.width:{target}@{ramp:g}s:smooth")
            elif wide or polarized:
                notes.append({"section_id": section["id"], "note": "Existing stereo separation detected; no added width or pan"})
        if spatial_alias and not _owned(existing, spatial_alias, "reverb") and spatial >= 45:
            wet = min(45, round(12 + spatial * (.24 if is_break else .14)))
            if direction == "ominous":
                wet = min(50, wet + 8)
            if is_break or lower == "intro":
                step.append(f"{spatial_alias}.reverb:{wet}@{ramp:g}s:smooth")
        # Only modest level reductions for objectively hot sections.
        # No attempt to force low-energy intros to match a chorus.
        if spatial_alias and not _owned(existing, spatial_alias, "gain"):
            if metric["peakDbfs"] > -1 and dynamics >= 45:
                step.append(f"{spatial_alias}.gain:-1@{ramp:g}s:smooth")
                notes.append({"section_id": section["id"], "note": "Peak near ceiling; modest backing attenuation suggested, not a headroom guarantee"})
            elif quiet:
                notes.append({"section_id": section["id"], "note": "Quiet passage preserved; no automatic loudness lift"})
        # Do not alter vocal gain or pan: input stems can contain shared male/female vocals.
        if vocal and metric["peakDbfs"] > 0:
            notes.append({"section_id": section["id"], "note": "Mix peak exceeds digital full scale; review master headroom separately"})
        if step:
            mapping = section_production.source_aliases(files, project.get("source_tracks", []), project.get("channel_children", {}))
            parsed = section_production.parse_block("{"+ " ".join(step) +"}", mapping)
            clone.setdefault("section_production", {})[section["id"]] = existing + parsed
            added.append({"section_id": section["id"], "label": section["kind"] + (" " + str(section["number"]) if section.get("number") else ""),
                          "directives": step, "measurements": metric})
    content = section_import.render_tags(clone)
    # Run complete import validation without changing source project or manifest.
    # A proposal that loses a directive/lyric or cannot round-trip is not returned.
    duration = max(float(x["end_seconds"]) for x in sections)
    validated = section_import.apply(copy.deepcopy(project), content, "replace", duration)
    if validated.get("section_lyrics", {}) != project.get("section_lyrics", {}):
        raise ValueError("Proposal did not preserve authored lyrics")
    if [(x["id"], x["start_seconds"], x["end_seconds"]) for x in validated["sections"]] != [
            (x["id"], x["start_seconds"], x["end_seconds"]) for x in sections]:
        raise ValueError("Proposal changed section identity or timing")
    return {
        "profile": PROFILE, "content": content, "suggestions": added,
        "notes": notes, "source": "current-saved-section-text-plus-client-measured-mix",
        "analysis_kind": "bounded-deterministic-v1",
        "disclaimer": "Stereo mix metrics do not establish independent stem/channel identity. Compare and audition before import.",
    }
