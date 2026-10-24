"""Engine-neutral validation of instrumental add/replace generation intents.

This module deliberately does not mutate project audio or claim that a native
ACE Base checkpoint has been verified. Use before constructing backing WAVs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

INSTRUMENTS = frozenset(("woodwinds", "brass", "fx", "synth", "strings",
                         "percussion", "keyboard", "guitar", "bass", "drums"))
EXCLUDED_VOCAL_TRACKS = frozenset(("vocals", "backing_vocals"))
OPERATIONS = frozenset(("add", "replace"))


@dataclass(frozen=True)
class InstrumentIntent:
    operation: Literal["add", "replace"]
    instrument: str
    target_track_id: str | None
    direction: str


def normalize_instrument(value: str) -> str:
    """Map musical family labels, never infer unsupported ACE track classes."""
    if not isinstance(value, str):
        raise ValueError("Instrument family must be a string")
    key = value.strip().lower()
    if key not in INSTRUMENTS:
        raise ValueError("Select a supported instrumental family (violin/cello use strings)")
    return key


def validate_intent(operation: str, instrument: str, direction: str,
                    target_track_id: str | None,
                    tracks: list[dict[str, Any]]) -> InstrumentIntent:
    if operation not in OPERATIONS:
        raise ValueError("Choose Add or Replace instrument")
    name = normalize_instrument(instrument)
    if not isinstance(direction, str) or not 1 <= len(direction.strip()) <= 2000:
        raise ValueError("Direction must be between 1 and 2000 characters")
    if operation == "add":
        if target_track_id is not None:
            raise ValueError("Add must not specify an existing replacement track")
        return InstrumentIntent("add", name, None, direction.strip())
    if not isinstance(target_track_id, str) or not target_track_id:
        raise ValueError("Replace requires an existing target track")
    candidates = [row for row in tracks if row.get("track_id") == target_track_id]
    if len(candidates) != 1:
        raise ValueError("Replacement target track is missing or ambiguous")
    row = candidates[0]
    if not row.get("working_filename"):
        raise ValueError("Replacement requires an accessible original instrument track")
    if row.get("removed"):
        raise ValueError("Cannot replace a removed track")
    return InstrumentIntent("replace", name, target_track_id, direction.strip())


def require_native_lego(model: dict[str, Any] | None) -> None:
    """Gate UI and jobs on an independently verified Base checkpoint."""
    if not isinstance(model, dict) or model.get("name") not in (
        "acestep-v15-base", "acestep-v15-xl-base"):
        raise ValueError("An installed ACE Base or XL-Base checkpoint is required for Lego")
    if model.get("verified_native_lego") is not True:
        raise ValueError("Native Lego is not yet verified for this local checkpoint")
    if not model.get("loaded"):
        raise ValueError("Load the verified Base checkpoint before Lego generation")
