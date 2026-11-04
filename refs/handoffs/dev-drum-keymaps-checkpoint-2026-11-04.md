# DEV checkpoint: drum keymaps and percussion rendering
Date: 2026-11-04
Branch: dev. Production main remains pinned to 2345c61.

## Implemented this slice
- `app/backend/polyphonic_midi.py`: explicit `percussion=True` renders channel-10 MIDI notes without injecting melodic program changes; default melodic path retains its channel-10 safety check.
- `app/backend/drum_keymaps.py`: data-only GM percussion lane labels and bounded custom mapping validation; validates every score pitch is defined by the selected keymap. Choke groups are metadata only, not functional sampler choke.
- `app/backend/server.py`: opt-in `percussion` and `drum_keymap` in saved-arrangement whole and selected-section render requests. Renders are still immutable candidates in existing A/B and acceptance flow. Candidate record includes mode and map. `GET /api/instruments/drum-keymap/gm` serves defaults for frontend editing.
- Tests: `test_drum_keymaps.py` and extended `test_polyphonic_midi.py`.

## Important boundary
This is backend plumbing only. No frontend drum-mode toggle, drum-lane editor, per-kit SFZ keymap wizard, installed kit verification, choke synthesis, sample round-robin, or real Windows playback QA yet. A saved percussion score must presently contain notes on MIDI channel 10 (zero-based 9). Neither transcription nor bulk channel migration has been added. SFZ packs are not assumed to follow GM pitches. Do not auto-assign a GM map to imported SFZ kits.

## Immediate next slice
1. Add explicit UI kit-mode toggle and kit map picker (GM default only for known GM drum kits; custom required for arbitrary SFZ). Provide labels in piano-roll drum mode and a safe way to map note pitches and MIDI channel 10.
2. For imported SFZ kits, inspect actual playable key ranges and samples, then allow custom pitch/label mapping without rewriting samples. Inventory Karoryfer Big Rusty Drums; verify real kit behavior on Windows before labeling compatible.
3. Ensure the accepted rendered drum stem goes through the existing L/R split path and per-channel scripting, and validate remove/mask restoration.
4. Run `python -m unittest discover -s app/backend/tests -p 'test_*midi*.py' -v` and `python -m unittest discover -s app/backend/tests -p 'test_drum_keymaps.py' -v`, then broader tests and frontend build. These have NOT been run from this connector-only session.
5. Add deterministic library-first name/variant matcher for LLM planning (Growlybass family first, Dirty/Angry/Shifty actual installed variants, unmatched industrial as creative direction). Preserve reviewable proposals; no silent model edits.

## Constraints
No main changes, no source overwrite, no automatic download, no unverified claims of correct audio, no implicit LLM audio uploads. Explicitly review and accept generated sections.
