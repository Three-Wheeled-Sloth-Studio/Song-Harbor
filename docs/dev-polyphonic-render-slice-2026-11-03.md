# Dev: arrangement-native polyphonic SF2 render
Date: 2026-11-03
Branch: dev only. Main remains release-stable.
Status: implementation committed; CI/Windows integration listening and export parity not yet verified.

## Outcome
- `app/backend/polyphonic_midi.py`: creates deterministic Type 0 Standard MIDI from the **saved MIDI arrangement revision** with exact 48-kHz sample timeline mapping, pitch/velocity/channel, bank/program messages, and note-off before note-on ordering on equal ticks. Different pitches can overlap. Conflicting overlapping notes with the same pitch/channel are rejected rather than risk unpredictable note-offs. Melodic channel 10 is reserved.
- `app/backend/server.py`: `POST /api/projects/{id}/midi-arrangements/{asset_id}/render` with `revision`, `pack_id`, `instrument_id`. Checks selected saved revision, validates instrument, only supports SF2+FluidSynth in this slice, creates a **new** removable candidate in existing `generated/bass-midi` cache, and reuses current preview/accept endpoints. Original stem, saved arrangement and prior candidates remain unchanged.
- `app/frontend/src/MidiPianoRoll.tsx`: open/save edited arrangement, select **Render arrangement**. Must be saved first; revision conflict fails rather than silently render stale note state.
- `app/frontend/src/BassMidiTool.tsx`: SF2 instrument selectors available without a temporary transcription candidate. Render arrangement creates candidate available for current Solo/A-B/Original retained mix/add-stem flow; subsequent re-render chooses selected SF2 instrument and reads original saved revision. Legacy monophonic extraction remains unchanged. Old monophonic note-list editing is hidden on polyphonic candidates to prevent mistakenly saving into the wrong data model.
- `app/backend/tests/test_polyphonic_midi.py`: note overlap, stable ordering, same-pitch conflicts, bank/program, off-on collisions, channel restrictions and deterministic output. Test added to backend CI.

## Why it is separated from the legacy bass renderer
Existing `bass_midi.validate_notes` assumes a single note at a time, and its legacy `midi_bytes` and synthetic previews share that assumption. Changing those globally would risk breaking the working bass sound and earlier projects. The new MIDI route reads canonical versioned arrangement notes directly, preserving source timing and stable IDs.

## Limitations
- SF2/FluidSynth only in this slice. No SFZ renderer, no multisampler articulation or CC/expression lane, no drum-specific note maps yet.
- Same-pitch overlaps on one channel must be shifted, shortened or assigned distinct channels; otherwise the encoder rejects them with a specific message.
- Some instruments have long sample-release tails; output is trimmed/padded by the existing FluidSynth renderer to arrangement duration.
- Current embedded piano roll does not yet show a vertical velocity lane or multi-select, and doesn't surface an instrument-specific drum grid.
- Accepted candidate remains ordinary removable stem with existing Original dial. The candidate records `arrangement_id` and revision; future re-render should continue to demand the revision.
- Current tool renders/accepts a fresh candidate without changing source stems. Production main is untouched.

## QA gates
1. `python -m unittest discover -s app/backend/tests -p 'test_polyphonic_midi.py' -v`
2. `python -m unittest discover -s app/backend/tests -p 'test_midi_arrangements.py' -v`
3. `python -m unittest discover -s app/backend/tests -p 'test_bass_midi.py' -v`
4. `cd app/frontend && npm run build`
5. On Windows dev, load a saved arrangement with bass chord or overlapping interval, select installed GeneralUser GS and Mean Saw Bass, click Render arrangement. Confirm preview and A/B, Original slider, add stem, save/reopen, export alignment and source hash. Verify opening saved arrangement works when no transcription candidate is loaded.
6. Edit a saved arrangement and confirm render refuses dirty state; Save then Render. Modify stored asset from another client and verify stale revision rejection.
7. Compare chord sample onset and ending against source section grid; check no unwanted click at new candidate boundaries or clipping. Confirm no preview autoplay when opening the roll or changing instrument.
8. Run existing artifact suite and launcher checks before a main-branch promotion.

## Follow-on
Move MIDI instrument rendering under the canonical arrangement editor fully (rather than sharing candidate view UI), add piano roll velocity lane and true melodic multichannel/drum-lane maps, then add SFZ sampler and expression CC for realistic sampled instruments. LLM edits remain reviewable version-checked patches, never automatic file rewrites.
