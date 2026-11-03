# Dev slice 1: durable MIDI arrangement assets (2026-11-03)
Branch: dev. No changes to main.
Status: implementation committed, local Windows runtime and CI results not yet verified.

## Delivered
- `app/backend/midi_arrangements.py`: independent, JSON-persisted schema v1. Stable UUID note IDs, 48-kHz sample-aligned start/end, polyphonic overlaps, velocity and MIDI channel, source track/region/method provenance, monotonically increasing revision and atomic file replacement. The file is not a rendered instrument candidate and does not mutate stems.
- `app/backend/server.py`: list / get arrangements, create one from a saved Stem to MIDI transcription, and PATCH with optimistic revision-checked atomic add/update/remove transactions. A stale revision fails rather than silently overwriting concurrent changes. All write paths enforce local-origin and completed project existence; no arbitrary filesystem paths accepted.
- `app/frontend/src/BassMidiTool.tsx`: **Save arrangement** saves current notes in the existing tool, without forcing instrument rendering or export; shows saved asset identifier. Existing audio A/B and .mid export remain distinct.
- `app/backend/tests/test_midi_arrangements.py` and CI backend regression list: persistence, schema rejection, note identity, polyphony, revision conflicts, non-quantized time and patch semantics.

## Known limits, deliberately deferred
- The current note-list UI cannot yet reopen and edit a saved arrangement or draw the piano roll. The backend GET/PATCH endpoints are the next UI integration point. Do not present the Save arrangement button as an implemented piano-roll editor.
- Each Save arrangement click creates a distinct arrangement versioned asset, not an update to an existing saved ID. This is safe but should be refined with explicit Save / Save As / version management before heavier editing.
- No MIDI importer/exporter for the new asset schema, automation lanes, tempo map, model transcription improvements, beat quantization, drum mapping, SFZ sampler or Deshimmer integration yet.
- API patch accepts proposed edits but does NOT invoke an LLM or authorize automatic acceptance. Future LLM agents must generate a reviewable patch against an explicit base revision, show a diff, and require user acceptance before commit. Commands never execute shell code.
- Mixed sources, source hash, multi-part score, articulation and CC expression are planned schema-v2 or optional compatible additions. Preserve schema-v1 readers.

## Test / QA
- Run: `python -m unittest discover -s app/backend/tests -p 'test_midi_arrangements.py' -v`.
- Run existing `test_bass_midi.py`, `test_instrument_library.py`, plus backend compileall and `cd app/frontend && npm run build`.
- On Windows, transcribe a short stem passage, edit notes, Save arrangement, GET the saved record, reload app and confirm it persists. Verify the original stem/hash remains unchanged and export is unaffected.
- Attempt stale PATCH and invalid/malicious IDs; assert the saved asset is not corrupted. Verify all notes remain at the intended audio-clock positions.
- Before beginning a full piano roll: make saved arrangement re-openable, implement undo/redo and stable drag-note commands. Then add the resizable timeline and velocity lane, with no auto playback.

## Next slice
1. List/reopen/select an existing saved arrangement from the MIDI tool, explicitly showing unsaved changes.
2. Implement piano roll as a resizable component using existing Song Harbor timeline/transport; note drawing/dragging/length, velocity lane, grid with snapping OFF by default, keyboard undo/redo.
3. Reuse server PATCH operations for individual note edits and batches; expose reviewable diff and operation plan for future LLM edits, without automatic execution.
4. Preserve instrument render as a separate action that consumes a selected arrangement revision.
