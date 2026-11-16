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


def _authored_direction(value: object) -> dict:
    """Read explicit parenthetical performance cues only; lyrics are not
    sentiment-classified, paraphrased, or edited."""
    if not isinstance(value, str):
        return {"tone": "unspecified", "cues": []}
    annotations = []
    for line in value.splitlines():
        line = line.strip()
        if line.startswith("(") and line.endswith(")") and len(line) < 220:
            annotations.append(line[1:-1].strip())
    evidence = " ".join(annotations).casefold()
    intimate = ("intimate", "whisper", "restrained", "hushed", "smoky", "quiet", "distant")
    expansive = ("full power", "choir swell", "anthemic", "soaring", "defiant", "explosive")
    if any(word in evidence for word in intimate):
        tone = "intimate"
    elif any(word in evidence for word in expansive):
        tone = "expansive"
    else:
        tone = "unspecified"
    return {"tone": tone, "cues": annotations[:5]}


def generate(project: dict, metrics: list[dict], *, spatial: int = 65,
             dynamics: int = 60, direction: str = "enhance",
             stereo_sources: list[dict] | None = None,
             section_stems: list[dict] | None = None,
             reviewed_context: dict | None = None) -> dict:
    """Return a validated import-ready text proposal; never mutate project."""
    if type(spatial) is not int or not 0 <= spatial <= 100:
        raise ValueError("Spatial ambition must be 0-100")
    if type(dynamics) is not int or not 0 <= dynamics <= 100:
        raise ValueError("Dynamic ambition must be 0-100")
    if direction not in ("enhance", "ominous", "movement", "contrast"):
        raise ValueError("Unknown production direction")
    reviewed_context = reviewed_context or {}
    if not isinstance(reviewed_context, dict):
        raise ValueError("Invalid reviewed production context")
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
        if row.get("rmsDbfs") is not None:
            energy = row["rmsDbfs"]
            if not isinstance(energy, (int, float)) or isinstance(energy, bool) or not math.isfinite(energy) or not -240 <= energy <= 24:
                raise ValueError("Invalid source RMS")
            profile["rmsDbfs"] = float(energy)
        profile["channels"] = channels
        source_profiles.append(profile)
    # Aligned dry-source observations are section-scoped evidence, unlike the
    # whole-source fingerprint. Silence and incomplete coverage are explicit.
    section_stems = section_stems or []
    if not isinstance(section_stems, list) or len(section_stems) > 8192:
        raise ValueError("Too many section stem observations")
    section_filenames = {x["id"] for x in sections}
    scoped: dict[tuple[str, str], dict] = {}
    for row in section_stems:
        if not isinstance(row, dict) or row.get("sectionId") not in section_filenames:
            raise ValueError("Unknown section stem observation")
        filename = row.get("filename")
        if not isinstance(filename, str) or len(filename) > 260:
            raise ValueError("Invalid section stem filename")
        if filename not in files:
            # A split-channel child or ephemeral audition track is not a
            # separate canonical source. Skip it rather than aborting the
            # whole proposal or inventing a parent-to-child relationship.
            continue
        key = (row["sectionId"], filename)
        measurement = {"sectionId": row["sectionId"], "filename": filename}
        for field, lo, hi in (
            ("rmsDbfs", -240, 24), ("balanceDb", -200, 200),
            ("widthDb", -240, 240), ("correlation", -1.001, 1.001),
            ("coverage", 0, 1.001),
        ):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError("Invalid section stem " + field)
            measurement[field] = float(value)
        previous = scoped.get(key)
        # Split channels can report multiple physical source lanes under one
        # working filename. Keep the strongest covered lane as conservative
        # presence evidence; split-child positioning stays protected.
        if previous is None or measurement["rmsDbfs"] > previous["rmsDbfs"]:
            scoped[key] = measurement
    lookup = section_production.source_map(files, project.get("source_tracks", []))
    by_filename = {row["filename"]: row for row in source_profiles}
    stem_states = {row.get("filename"): row for row in project.get("stems", [])}
    any_solo = any(row.get("solo", False) for row in stem_states.values())
    children = project.get("channel_children", {})
    protected_aliases = {"vocals", "bass", "drums"}
    # Multiple independently recorded stems are the preferred source of
    # new stereo differentiation. Width alone cannot widen a mono source.
    priority = ["other", "guitar", "piano", "synth", "strings", "ambience", "pads"]
    candidates = sorted(
        (alias for alias in parents if alias.casefold() not in protected_aliases),
        key=lambda name: (priority.index(name.casefold()) if name.casefold() in priority else len(priority),
                          name.casefold()),
    )
    eligible = []
    for alias in candidates:
        filename = lookup.get(alias)
        profile = by_filename.get(filename)
        if not profile or profile.get("rmsDbfs", 0) < -55:
            continue
        state = stem_states.get(filename, {})
        if (state.get("mute", False) or (any_solo and not state.get("solo", False))
                or float(state.get("gain", 1)) <= .001):
            continue
        # Explicitly protect existing channel split and dedicated hard pans.
        split = bool(children.get(filename, {}).get("export"))
        mono = profile["channels"] == 1 or (
            profile["widthDb"] < -35 and profile["correlation"] > .995
        )
        already_wide = profile["widthDb"] > -12
        existing_asymmetry = abs(profile["balanceDb"]) >= 1.7 or abs(profile["hardPan"]) > .1
        eligible.append({"alias": alias, "mono": mono, "split": split,
                         "wide": already_wide, "asymmetric": existing_asymmetry,
                         "profile": profile})
    clone = copy.deepcopy(project)
    original = project.get("section_production", {})
    all_authored = [directive for directives in original.values() for directive in directives]
    generated: dict[tuple[str, str], object] = {}
    added = []
    notes = []
    for index, section in enumerate(sections):
        metric = by_id[section["id"]]
        existing = list(original.get(section["id"], []))
        lower = section["kind"].lower()
        is_peak = lower in ("chorus", "pre-chorus")
        is_break = lower in ("bridge", "instrumental", "outro")
        is_intro = lower == "intro"
        is_verse = lower in ("verse", "verse 1", "verse 2", "verse 3")
        length = float(section["end_seconds"]) - float(section["start_seconds"])
        ramp = round(max(.05, min(length * (.42 if is_peak else .48), 15)), 2)
        quiet = metric["rmsDbfs"] < -30
        authored_direction = _authored_direction(
            project.get("section_lyrics", {}).get(section["id"], "")
        )
        confirmed = reviewed_context.get(section["id"])
        if confirmed is not None:
            if not isinstance(confirmed, dict) or confirmed.get("tone") not in (
                "intimate", "restrained", "ominous", "rising", "expansive",
                "driving", "suspended", "neutral"):
                raise ValueError("Invalid reviewed direction")
            # A human-confirmed interpretation can refine the broad stage cue,
            # but it never changes authored text or source measurements.
            tone = confirmed["tone"]
        else:
            tone = authored_direction["tone"]
        intimate = tone in ("intimate", "restrained", "suspended")
        expansive = tone in ("expansive", "rising", "driving")
        step: list[str] = []
        notes_local = []

        def set_effect(alias: str, kind: str, value: str):
            # Protect all authored effect dimensions, including values appearing
            # later in the song, from accidental proposed overrides.
            if _owned(all_authored, alias, kind):
                return False
            key = (alias.casefold(), kind)
            if generated.get(key) == value:
                return False
            parsed = f"{alias}.{kind}:{value}@{ramp:g}s:smooth"
            step.append(parsed)
            generated[key] = value
            return True

        # Choose only stems that contribute within this section. The earlier
        # full-song estimate remains the fallback for old planner clients.
        if section_stems:
            local_eligible = []
            for row in eligible:
                filename = lookup.get(row["alias"])
                evidence = scoped.get((section["id"], filename))
                if not evidence or evidence["coverage"] < .2 or evidence["rmsDbfs"] < -45:
                    continue
                local_eligible.append({**row, "section_evidence": evidence})
        else:
            local_eligible = eligible
        if spatial >= 20 and local_eligible:
            # Prefer separately recorded stem files, with complementary restrained
            # lateral placement; preserve existing panning or split routing.
            lateral = [row for row in local_eligible if not row["split"] and not row["asymmetric"]]
            pair = lateral[:2]
            for i, row in enumerate(pair):
                alias = row["alias"]
                # Deliberate spatial story: alternating/expanding verse positions,
                # bring separated tracks closer to center for chorus impact.
                if is_peak or intimate:
                    bias = min(24, round(spatial * .24))
                elif is_intro or is_break or expansive:
                    bias = min(48, round(spatial * .48))
                else:
                    bias = min(42, round(spatial * .40))
                if direction == "movement":
                    bias = min(55, bias + 8)
                if (direction == "ominous" or tone == "ominous") and is_break:
                    bias = min(55, bias + 5)
                side = ("left" if (index + i) % 2 == 0 else "right")
                if bias >= 12 and set_effect(alias, "pan", f"{side}.{bias}"):
                    notes_local.append(f"Position {alias} {side}; use available stem separation for stereo contrast")
            # Nonidentical backing stems can have individual reflection spaces.
            # Reflections generate decorrelated spatial information even where
            # a dry source is effectively mono; width alone does not.
            for i, row in enumerate(local_eligible[:3]):
                alias = row["alias"]
                reflections = min(35, round(6 + spatial * (.27 if is_break or is_intro or expansive else .18)))
                if direction in ("ominous", "movement") or tone == "ominous":
                    reflections = min(38, reflections + 4)
                if row["mono"] or metric["widthDb"] < -14:
                    if set_effect(alias, "space", str(reflections)):
                        notes_local.append(f"{alias}: spatial reflections, not fake mono widening")
                elif not row["split"] and not row["wide"] and not row["asymmetric"]:
                    width = min(145, round(105 + spatial * (.25 if is_peak or is_break else .15)))
                    set_effect(alias, "width", str(width))
                if (is_intro or is_break or is_peak or expansive or tone == "ominous") and i == 0:
                    wet = min(55, round(16 + spatial * (.30 if is_break else .22)))
                    if direction == "ominous" or tone == "ominous":
                        wet = min(60, wet + 7)
                    set_effect(alias, "reverb", str(wet))
            if len(local_eligible) < 2:
                notes_local.append("Only one eligible backing stem: reflections and positioning cannot create a second instrument")
        elif not local_eligible:
            notes_local.append("No active measured backing stems in this section; no invented spatial effect")

        # Create contrast by dynamically making room around the lead, not
        # forcing every section to one target loudness. Never touch lead/bass.
        vocal_filename = lookup.get(known.get("vocals", ""))
        vocal_section = scoped.get((section["id"], vocal_filename))
        lead_active = not section_stems or (
            vocal_section is not None and vocal_section["coverage"] >= .2
            and vocal_section["rmsDbfs"] >= -43
        )
        if dynamics >= 40 and known.get("vocals") and lead_active and local_eligible:
            backing = local_eligible[0]["alias"]
            if is_verse or is_break or intimate:
                duck = round(min(4.0, 1.1 + dynamics * .027 + (.4 if intimate else 0)), 1)
                if set_effect(backing, "duck", f"{duck:g}"):
                    notes_local.append(f"Voice-keyed backing duck {duck:g} dB, protecting lead clarity")
            elif is_peak:
                set_effect(backing, "duck", "1")
        # Role-aware production: lead, drums and bass contribute to the arc
        # without treating every source as a generic backing instrument.
        # All choices require the stem to be present in this section; keep
        # the lead and bass centered and respect existing authored controls.
        def active_role(name: str) -> tuple[str, dict] | None:
            alias = known.get(name)
            if alias is None:
                return None
            filename = lookup.get(alias)
            if filename is None:
                return None
            state = stem_states.get(filename, {})
            if state.get("mute", False) or (any_solo and not state.get("solo", False)):
                return None
            evidence = scoped.get((section["id"], filename))
            if section_stems:
                if (evidence is None or evidence["coverage"] < .2
                        or evidence["rmsDbfs"] < -45):
                    return None
            else:
                profile = by_filename.get(filename)
                if profile is None or profile.get("rmsDbfs", 0) < -55:
                    return None
            return alias, evidence or {}

        lead_role = active_role("vocals")
        drum_role = active_role("drums")
        bass_role = active_role("bass")
        if lead_role and spatial >= 35:
            alias, _ = lead_role
            # Reverb is a depth change, not a gain hike. Keep words forward
            # in verses and let the chorus/bridge open up without panning lead.
            wet = (17 + round(spatial * .25) if expansive or is_peak else
                   14 + round(spatial * .18) if intimate else
                   19 + round(spatial * .20))
            if tone == "ominous":
                wet += 7
            wet = min(55, wet)
            if set_effect(alias, "reverb", str(wet)):
                notes_local.append("Lead reverb depth follows section direction; preserve centered vocal")
        if drum_role and dynamics >= 35:
            alias, evidence = drum_role
            # Focus on transient character. No panning of the combined drum
            # bus: its kick and low hits must remain an anchored foundation.
            if (is_peak or expansive or tone == "driving") and metric["peakDbfs"] < -1.5:
                threshold = -15 if dynamics >= 70 else -18
                comp = f"{threshold},2"
                if set_effect(alias, "comp", comp):
                    notes_local.append("Measured active drums: moderate compression for impact, not forced loudness")
            elif is_break or tone == "ominous":
                send = min(28, 9 + round(spatial * .16))
                if spatial >= 35 and set_effect(alias, "space", str(send)):
                    notes_local.append("Drum reflections add threatening depth without hard-panning low hits")
        if bass_role and direction in ("ominous", "contrast") and dynamics >= 45:
            alias, _ = bass_role
            # Bass stays centered. Only a low-level ambient reflection during
            # sustained suspense, never a width/pan or high gain operation.
            if is_intro or is_break or tone in ("ominous", "suspended"):
                send = min(15, 5 + round(spatial * .10))
                if set_effect(alias, "space", str(send)):
                    notes_local.append("Subtle bass reflections; preserve low-frequency center")
        if confirmed:
            notes_local.append(
                "Human-reviewed direction: " + tone +
                " (" + confirmed.get("origin", "author") + ")"
            )
        if authored_direction["cues"]:
            notes_local.append(
                "Authored performance direction: " +
                authored_direction["tone"] +
                " (" + "; ".join(authored_direction["cues"])[:150] + ")"
            )
        if metric["peakDbfs"] > -1:
            notes_local.append("High mix peak; audition and check headroom, not automatically mastered")
        if quiet:
            notes_local.append("Quiet section deliberately preserved")
        # An existing wet return can remain broad through a dramatic section
        # without increasing the dry master level.
        if step:
            aliases = section_production.source_aliases(
                files, project.get("source_tracks", []), children
            )
            parsed = section_production.parse_block("{" + " ".join(step) + "}", aliases)
            clone.setdefault("section_production", {})[section["id"]] = existing + parsed
            added.append({
                "section_id": section["id"],
                "label": section["kind"] + (" " + str(section["number"]) if section.get("number") else ""),
                "directives": step, "measurements": metric,
            })
        for note in notes_local:
            notes.append({"section_id": section["id"], "note": note})
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
        "analysis_kind": "reviewed-context-v3", "stereo_sources": source_profiles,
        "reviewed_sections": sum(key in {x["id"] for x in sections} for key in reviewed_context),
        "section_stem_count": len(scoped),
        "disclaimer": "Stereo mix metrics do not establish independent stem/channel identity. Compare and audition before import.",
    }
