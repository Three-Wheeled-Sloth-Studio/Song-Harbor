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
        ("rmsDbfs", -240, 24), ("peakDbfs", -240, 24),
        ("widthDb", -240, 240), ("balanceDb", -200, 200),
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
             dynamics: int = 60, direction: str = "enhance",
             stereo_sources: list[dict] | None = None) -> dict:
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
    stereo_sources = stereo_sources or []
    if len(stereo_sources) > 200:
        raise ValueError("Too many stereo sources")
    source_profiles = []
    for row in stereo_sources:
        if not isinstance(row, dict) or not isinstance(row.get("filename"), str) or len(row["filename"]) > 260:
            raise ValueError("Invalid stereo source identity")
        profile = {"filename": row["filename"]}
        for name, minimum, maximum in (
            ("balanceDb", -200, 200), ("widthDb", -240, 240),
            ("correlation", -1.001, 1.001), ("hardPan", -1, 1),
        ):
            value = row.get(name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError("Invalid source stereo " + name)
            profile[name] = float(value)
        channels = row.get("channels", 2)
        if type(channels) is not int or channels not in (1, 2):
            raise ValueError("Invalid source channel count")
        profile["channels"] = channels
        source_profiles.append(profile)
    spatial_filename = section_production.source_map(files, project.get("source_tracks", [])).get(spatial_alias or "")
    target_profiles = [row for row in source_profiles if row["filename"] == spatial_filename]
    stem_state = next((item for item in project.get("stems", [])
                       if item.get("filename") == spatial_filename), None)
    any_solo = any(item.get("solo") for item in project.get("stems", []))
    spatial_audible = not stem_state or (
        not stem_state.get("mute", False)
        and float(stem_state.get("gain", 1)) > .001
        and (not any_solo or stem_state.get("solo", False))
    )
    has_split = bool(project.get("channel_children", {}).get(spatial_filename or "", {}).get("export"))
    source_unmeasured = not target_profiles
    source_near_mono = bool(target_profiles) and all(
        row["channels"] == 1 or (row["widthDb"] < -35 and row["correlation"] > .995)
        for row in target_profiles
    )
    source_already_spatial = has_split or any(
        abs(row["balanceDb"]) >= 1.5 or row["widthDb"] > -12 or abs(row["hardPan"]) > .1
        for row in target_profiles
    )
    clone = copy.deepcopy(project)
    authored = [directive
                for directives in project.get("section_production", {}).values()
                for directive in directives]
    # Effects inherit across sections. A missing directive in a later section
    # does not make an earlier authored effect available for replacement.
    def available(kind: str) -> bool:
        return spatial_alias is not None and not _owned(authored, spatial_alias, kind)
    added = []
    notes = []
    generated_pan = False
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
        authored_pan = spatial_alias is not None and _owned(existing, spatial_alias, "pan")
        if spatial_alias and spatial_audible and available("width") and not _owned(existing, spatial_alias, "width"):
            if not wide and not polarized and not source_already_spatial and not source_near_mono and not source_unmeasured and spatial >= 35:
                target = min(145, 100 + round(spatial * (.38 if is_peak or is_break else .17)))
                if direction == "movement" or (direction == "contrast" and is_peak):
                    target = min(145, target + 10)
                if target > 108:
                    step.append(f"{spatial_alias}.width:{target}@{ramp:g}s:smooth")
            elif wide or polarized or source_already_spatial:
                notes.append({"section_id": section["id"], "note": "Existing stereo/channel separation protected; no additional widening"})
            elif source_near_mono:
                notes.append({"section_id": section["id"], "note": "Near-mono source; width control cannot create independent stereo detail"})
            elif source_unmeasured:
                notes.append({"section_id": section["id"], "note": "No source stereo measurement; skipping unsupported width change"})
        if (spatial_alias and spatial_audible and not authored_pan and not source_already_spatial
                and not polarized and not wide and not source_unmeasured and direction == "movement"
                and spatial >= 65 and available("pan") and not _owned(existing, spatial_alias, "pan")
                and lower in ("verse", "bridge", "pre-chorus")):
            side = "left" if index % 2 == 0 else "right"
            bias = min(35, round(spatial * .32))
            if bias >= 20:
                step.append(f"{spatial_alias}.pan:{side}.{bias}@{ramp:g}s:smooth")
                generated_pan = True
        if spatial_alias and spatial_audible and available("reverb") and not _owned(existing, spatial_alias, "reverb") and spatial >= 45:
            wet = min(45, round(12 + spatial * (.24 if is_break else .14)))
            if direction == "ominous":
                wet = min(50, wet + 8)
            if is_break or lower == "intro":
                step.append(f"{spatial_alias}.reverb:{wet}@{ramp:g}s:smooth")
        # Only modest level reductions for objectively hot sections.
        # No attempt to force low-energy intros to match a chorus.
        if spatial_alias and spatial_audible and available("gain") and not _owned(existing, spatial_alias, "gain"):
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
    def lyrics_clean(value: object) -> str:
        return "\n".join(line.rstrip() for line in str(value or "").splitlines()).strip()
    original_lyrics = {key: lyrics_clean(value) for key, value in project.get("section_lyrics", {}).items()}
    result_lyrics = {key: lyrics_clean(value) for key, value in validated.get("section_lyrics", {}).items()}
    if result_lyrics != original_lyrics:
        raise ValueError("Proposal did not preserve authored lyrics")
    if [(x["id"], x["start_seconds"], x["end_seconds"]) for x in validated["sections"]] != [
            (x["id"], x["start_seconds"], x["end_seconds"]) for x in sections]:
        raise ValueError("Proposal changed section identity or timing")
    return {
        "profile": PROFILE, "content": content, "suggestions": added,
        "notes": notes, "source": "current-saved-section-text-plus-client-measured-mix",
        "analysis_kind": "bounded-deterministic-v1", "stereo_sources": source_profiles,
        "disclaimer": "Stereo mix metrics do not establish independent stem/channel identity. Compare and audition before import.",
    }
