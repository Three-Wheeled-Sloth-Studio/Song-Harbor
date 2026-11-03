# Dev slice 2: Saved MIDI piano roll
Date: 2026-11-03
Branch: dev only; no main changes.
Status: implementation committed; Windows runtime, frontend build and listening QA remain unverified.

## Implementation
- `app/frontend/src/MidiPianoRoll.tsx`: compact piano roll inside existing Stem Tools > MIDI, not another persistent tool window. Lists saved arrangements for selected source stem, opens exact saved asset/revision, scrollable pitch/time grid, click-to-add note, pointer drag move and right-edge resize, note selection, velocity input, undo/redo, optional 125/250/500ms snap OFF by default, keyboard delete and Ctrl+Z/Ctrl+Y when grid focused.
- `app/frontend/src/BassMidiTool.tsx`: embeds piano roll above temporary transcription candidate; Use in MIDI tool reopens candidate corresponding to the asset provenance and loads the saved notes for the existing instrument renderer. It verifies source track and exact source region and does not render or autoplay.
- `app/backend/server.py`: records parent transcription candidate ID when saving arrangement, allowing reopening on the user's local project. Previous assets without linkage remain editable but cannot be sent through the legacy renderer automatically.
- Notes are persisted with server PATCH against base revision. Changed note IDs generate update operations, new IDs generate add, deleted IDs generate remove. Any concurrent/stale update is rejected rather than overwritten. Unsaved edits are not silently discarded when choosing another arrangement. Undo history local to the editing session (not persistent).

## Important limitations / follow-up
1. Current Stem MIDI instrument rendering still uses the old monophonic `bass_midi.validate_notes` path and MIDI pitch restriction 28-76. Piano roll allows overlapping notes in the persistent data model, but **those cannot yet render through the old monophonic engine**. A clear note in the UI states this. Next priority is an arrangement-native polyphonic MIDI exporter/renderer.
2. After using an arrangement in the existing note-list tool, further changes in that old editor do not automatically update the saved asset; current UI explains that saving again makes a new asset. Next: unify editing around one authoritative arrangement model, with Save/Save As.
3. Only currently displayed MIDI notes (28-76) can be moved in the visual grid. Larger score pitch range and drum named lanes come with polyphonic/drum model.
4. No auto quantization, no automatic playback, no sample pack downloads, no sound/engine change on open/save, and no modification to source stems.
5. This is a lightweight first editor, not complete DAW piano-roll ergonomics: velocity lane visualization, multi-select, zoom, note keyboard nudges, articulation/CC, beat/tempo map, persisted undo and LLM review/diff UI remain next slices.
6. Pointer behavior and keyboard shortcuts need local browser accessibility/drag QA, including small note hit-targets, drag at edges, zoom/scroll, resizable popover and no accidental grid notes.

## QA
- Run backend `test_midi_arrangements.py` plus existing bass MIDI / instrument tests.
- Run `cd app/frontend && npm run build`; ensure TS / React pointer handlers compile.
- Manually: extract 10-20s sparse mono stem; Save arrangement; Refresh/Open; add/drag/resize note; undo/redo; toggle snap; change velocity; Save; close/reopen app; verify exact samples and revision; load into MIDI tool and render; verify no autoplay, no changes to source WAV.
- Negative cases: stale revision conflict (must not overwrite); unsaved reload confirmation; source stem switch; no original candidate; overlapping notes (save okay, legacy render rejected visibly); full 600s duration and narrow tool window.
- Do not promote to main until sample-accurate preview/export parity and Windows build are verified.

## Roadmap adjustment
Given the sparse next track, prioritize **single-part arrangement quality** and easy note editing over universal polyphonic transcription. A versioned, structured note diff is deliberately usable for future LLM edit proposals, but no LLM may mutate a score automatically.
