"""Data-only percussion keymaps for editable drum arrangement lanes.

The General MIDI map is a convenient *default*, not a claim about arbitrary
SFZ sample sets. Non-GM kits require an explicit user-verified mapping.
No sample packs are downloaded or imported by this module.
"""
from __future__ import annotations
import re

GM_PERCUSSION = {
    35: "Acoustic Bass Drum", 36: "Bass Drum 1", 37: "Side Stick",
    38: "Acoustic Snare", 39: "Hand Clap", 40: "Electric Snare",
    41: "Low Floor Tom", 42: "Closed Hi-Hat", 43: "High Floor Tom",
    44: "Pedal Hi-Hat", 45: "Low Tom", 46: "Open Hi-Hat",
    47: "Low-Mid Tom", 48: "Hi-Mid Tom", 49: "Crash Cymbal 1",
    50: "High Tom", 51: "Ride Cymbal 1", 52: "Chinese Cymbal",
    53: "Ride Bell", 54: "Tambourine", 55: "Splash Cymbal",
    56: "Cowbell", 57: "Crash Cymbal 2", 58: "Vibraslap",
    59: "Ride Cymbal 2", 60: "Hi Bongo", 61: "Low Bongo",
    62: "Mute Hi Conga", 63: "Open Hi Conga", 64: "Low Conga",
    65: "High Timbale", 66: "Low Timbale", 67: "High Agogo",
    68: "Low Agogo", 69: "Cabasa", 70: "Maracas", 71: "Short Whistle",
    72: "Long Whistle", 73: "Short Guiro", 74: "Long Guiro",
    75: "Claves", 76: "Hi Wood Block", 77: "Low Wood Block",
    78: "Mute Cuica", 79: "Open Cuica", 80: "Mute Triangle",
    81: "Open Triangle",
}
MAX_LANES = 128
MAX_LABEL = 80
LABEL = re.compile(r"^[^\x00-\x1f\x7f]{1,80}$")


def default_keymap() -> dict:
    """Return serializable, editable GM pitch labels for a known GM drum kit."""
    return {"schema_version": 1, "mapping_kind": "gm", "lanes": [
        {"pitch": pitch, "name": name} for pitch, name in sorted(GM_PERCUSSION.items())
    ]}


def validate_keymap(mapping: dict) -> dict:
    """Reject duplicate, unsafe or misleading lane assignments.

    Choke groups are optional annotations for UI and future sample engines;
    this does not claim to synthesize choke or round-robin behavior.
    """
    if not isinstance(mapping, dict) or mapping.get("schema_version") != 1:
        raise ValueError("Unsupported drum keymap schema")
    kind = mapping.get("mapping_kind")
    if kind not in ("gm", "custom"):
        raise ValueError("Drum mapping must be gm or custom")
    lanes = mapping.get("lanes")
    if not isinstance(lanes, list) or not 1 <= len(lanes) <= MAX_LANES:
        raise ValueError("Drum keymap must contain 1 to 128 lanes")
    pitches = set()
    result = []
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("Invalid drum lane")
        pitch = lane.get("pitch")
        name = lane.get("name")
        choke = lane.get("choke_group", "")
        if type(pitch) is not int or not 0 <= pitch <= 127 or pitch in pitches:
            raise ValueError("Duplicate or invalid drum pitch")
        if not isinstance(name, str) or not LABEL.fullmatch(name.strip()):
            raise ValueError("Invalid drum lane name")
        if not isinstance(choke, str) or len(choke) > 32 or (
            choke and not re.fullmatch(r"[a-zA-Z0-9_-]+", choke)
        ):
            raise ValueError("Invalid drum choke group")
        if kind == "gm" and (pitch not in GM_PERCUSSION or name != GM_PERCUSSION[pitch]):
            raise ValueError("Use custom mapping for non-GM drum lanes")
        pitches.add(pitch)
        row = {"pitch": pitch, "name": name.strip()}
        if choke:
            row["choke_group"] = choke
        result.append(row)
    return {"schema_version": 1, "mapping_kind": kind,
            "lanes": sorted(result, key=lambda row: row["pitch"])}


def label_for_pitch(mapping: dict, pitch: int) -> str:
    validated = validate_keymap(mapping)
    if type(pitch) is not int or not 0 <= pitch <= 127:
        raise ValueError("Invalid drum pitch")
    return next((lane["name"] for lane in validated["lanes"]
                 if lane["pitch"] == pitch), f"Unmapped note {pitch}")


def verify_notes(asset: dict, mapping: dict) -> None:
    """Fail before rendering if a drum note is not represented in its kit."""
    import midi_arrangements
    notes = midi_arrangements.validate(asset)["notes"]
    pitches = {lane["pitch"] for lane in validate_keymap(mapping)["lanes"]}
    missing = sorted({note["pitch"] for note in notes} - pitches)
    if missing:
        raise ValueError("Drum kit has no mapped lanes for MIDI pitches: " +
                         ", ".join(map(str, missing)))
