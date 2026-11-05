# DEV handoff: persistent drum maps and catalogue-first instrument resolution
Date: 2026-11-04
Branch: dev ONLY. Production main stays at 2345c61.
Previous handoff: refs/handoffs/dev-drum-ui-checkpoint-2026-11-04.md

## QA evidence
User reports DEV auto-update/relaunch clean before this slice. No end-to-end Windows drum render or playing/export QA. These new commits have not yet been built on the user's Windows machine. No local backend tests executed in this connector-only development environment; direct container git network unavailable.

## Implemented
- `midi_arrangements.py`: optional `percussion:{mode:'drums',keymap:{schema_version:1,mapping_kind:'gm'|'custom',lanes:[...]}}` in existing schema-v1 asset. Validates all note channels are MIDI channel 10 (zero-based 9) and all pitches are mapped. Legacy arrangements without this optional field still load. Note edits and map metadata changes share one revision-checked atomic patch. Metadata-only changes supported. Clearing drum metadata is supported.
- `server.py`: MIDI PATCH accepts `update_percussion` and optional `percussion`; whole/section render requests validate supplied mapping against persisted canonical mapping. No source WAV mutations. `POST /api/instruments/match-direction` exposes catalog matching with current installed instrument library, same-origin checked, no LLM/network invocation.
- `MidiPianoRoll.tsx`: editor Save checks note edits *and* kit metadata edits, restores saved GM or custom kit map on reopen, and cannot render unsaved map. Custom SFZ maps are retained with arrangement revision, not merely window state. Frontend sends mapping in existing render request.
- `instrument_direction_match.py`: deterministic catalogue-first family and variant matching. Evidence trace includes chosen pack ID, actual installed instrument ID/name and section assignment; ambiguous/missing family not silently selected; retains full user request for downstream musical direction. Supports sample Growlybass Dirty default, Angry chorus, Shifty bridge, Industrial as unmatched creative term.
- Regression tests appended to `test_midi_arrangements.py`; new `test_instrument_direction_match.py` includes exact Growlybass scenario, no pack match, conflicts and bounds. Tests committed, not executed.

## Important limitations
- This is preparation for LLM planner, NOT an LLM workflow yet. Match endpoint does not write or render.
- Current matcher is deliberately small and phrase/proximity based. It is not a general semantic parser; manually review ambiguous scopes. Multi-family instructions currently return ambiguity rather than orchestrate five stems.
- Custom map names are labels at actual MIDI pitches, NOT sample remapping; SFZ kits must be audited for playable keys. No choke/round-robin implementation.
- UI drum grid currently displays pitches 28-81; expand/custom scroll for exotic kits.
- Backend and frontend tests, Windows release/build and audio parity remain unverified for this slice.

## QA gates
1. Windows DEV update/build. If TS build fails fix before proceeding.
2. In drum piano roll, switch to drum mode, change kit map, Save, close/reopen/relaunch: exact map, notes and revision should persist; Save with only map change must increment revision.
3. Verify custom mapped notes can render; saved map mismatch must reject, unsaved map must block rendering; old melodic scores must remain unchanged. Test dirty and undo/redo behavior.
4. Run `python -m unittest discover -s app/backend/tests -p 'test_midi_arrangements.py' -v`, `test_drum_keymaps.py`, `test_polyphonic_midi.py`, `test_instrument_direction_match.py`, and broader suite; frontend `cd app/frontend && npm run build`.
5. Exercise `POST /api/instruments/match-direction` with installed Growlybass pack and instruction: 'Growlybass Dirty default; Angry for choruses; Shifty for bridges; maintain industrial elements'. Check exact actual instrument IDs and no hallucinated selection.
6. Regression: multi-section composite acceptance, single imported track, L/R scripting, source-volume masks, Remove restoration, audition/export parity.

## Next work
- Add a compact reviewable instrument-resolution UI and reusable provider-neutral LLM proposal schema.
- Add per-section preset assignment + candidate render, so the catalog matched variants actually change between Verse/Chorus/Bridge in one accepted stem.
- Finish genuine SFZ kit mapping discovery and drum sample QA, rather than claiming that kit mapping alone makes arbitrary drum packs play correctly.
- Do not promote dev to main without explicit request.
