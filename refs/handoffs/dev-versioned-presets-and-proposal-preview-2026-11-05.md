# DEV checkpoint: persistent section presets and read-only MIDI proposals
Date: 2026-11-05
Branch: dev only. Production main pinned at 2345c61.
User QA: clean build of preceding dev slice. Changes in this checkpoint have not been Windows-built or audio-QA tested.

## Delivered
- `app/backend/section_instrument_selection.py`: canonical `instrument_sections` recipe containing exact version, default installed pack/instrument IDs, selected section IDs and overrides. Validates 1-8 sections, duplicate/foreign overrides, and installed presets at render time.
- `app/backend/midi_arrangements.py`: optional section recipe in saved score schema v1, backward compatible. Note edits, percussion metadata and preset recipe share an atomic revision-guarded PATCH. Metadata-only save and removal work.
- `app/backend/server.py`: PATCH validates saved recipe against actual song section timestamps and arrangement bounds. Saved recipe must exactly match selected section scope, default and overrides when rendering. Whole-arrangement render refuses to discard saved section-specific presets. Render continues producing independent candidate clips for review, followed by ONE combined instrument stem and reversible masks.
- `app/frontend/src/MidiPianoRoll.tsx`: save/reopen selected sections, default instrument and overrides, restore dropdown state; mark pending metadata as unsaved and block rendering until saved. Use main instrument selector as single source of truth. Existing Match library preview still requires explicit Apply.
- `app/backend/midi_proposal_preview.py`: provider-neutral proposal contract (schema_version, base_revision, source_track_id, target_stem, sections/intents, MIDI operations, optional preset recipe). Pure in-memory note and recipe diff; ensures actual installed preset IDs, selected section scope, safe targets (Bass/Drums/Guitar/Piano/Other, not Vocals), MIDI note bounds and proposed note edits strictly within selected sections. Does NOT save, accept, render, or invoke an LLM.
- `POST /api/projects/{ident}/midi-arrangements/{asset_id}/proposal-preview`: same-origin read-only validation endpoint.
- Regression tests added in `test_midi_arrangements.py`, `test_section_instrument_selection.py`, `test_midi_proposal_preview.py`.

## QA evidence and gates
Previous user build clean only. New backend tests NOT executed here. New frontend build not run in this connector environment.
Run `cd app/frontend && npm run build`; run `python -m unittest discover -s app/backend/tests -p 'test_midi_arrangements.py' -v`, `test_section_instrument_selection.py`, `test_midi_proposal_preview.py`; then broader suite.
- Open a saved MIDI score, select sections, assign default Dirty and chorus Angry/bridge Shifty, Save, close, reopen. Verify exact dropdown values and selected sections restored, revision incremented, unchanged notes.
- Confirm metadata-only update and stale revision rejection. Check main instrument selector change updates unsaved status.
- Render selected sections and accept one composite Bass stem. Verify appropriate preset sound in each section, section-level source masks, L/R split, remove restores original audio, export parity.
- Whole-arrangement Render must explain that section-specific preset recipe requires selected-section rendering. No silent fallback to default.
- Proposal-preview endpoint must reject vocals, wrong source, stale revision, section outside arrangement, absent presets, operations outside selected sections. Response must show proposed diff with zero mutations.

## Known next work
- Add proposal preview/diff UI (currently endpoint only), mock provider adapter, then explicit Accept/Discard application that rechecks score revision. Do not automatically apply LLM MIDI edits.
- Catalogue resolver still heuristic for unusual phrasing; trace and review required.
- Full drum SFZ sample mapping and dynamics remain unverified. Source-vocal cleanup remains separate.
- No promotion of dev to main without explicit user instruction.
