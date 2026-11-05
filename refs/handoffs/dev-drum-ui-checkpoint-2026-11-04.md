# DEV checkpoint: drum piano roll and kit mapping UI
Date: 2026-11-04
Branch: dev ONLY. Main production frozen at 2345c61. Latest dev source commit at time of handoff: a2ab35a.

## User QA baseline
User reported auto-update clean before these edits, no other QA performed. That clean launch applies to previous dev version, NOT this drum UI. Do not claim frontend compile, live audio, SFZ compatibility, or acceptance passed.

## Implemented
- app/frontend/src/MidiPianoRoll.tsx has explicit Drum kit mode that converts the existing editable arrangement notes between melodic MIDI channel 1 (zero-based 0) and percussion MIDI channel 10 (zero-based 9). Change is undoable and must be saved before rendering. Drum notes show named keymap rows, and clicking empty drum lane produces short percussion notes.
- Kit mapping selector: General MIDI SoundFont (only for SF2; full canonical GM labels matching backend) or explicit custom kit mapping entered as MIDI pitch = name lines for SFZ. Missing pitches and empty/invalid/duplicate kit lanes block render. Arbitrary SFZ kits are NOT silently assumed GM.
- Existing piano-roll Render passes percussion and drum_keymap into app/frontend/src/BassMidiTool.tsx useArrangement, to whole-arrangement and section render APIs. No new separate drum window or automatic source mutations.
- Backend from prior slice accepts and validates mappings in server.py / drum_keymaps.py and writes immutable candidates. Existing accept flow attempts L/R split.
- No user-installed drum pack data was changed or downloaded. Curated Karoryfer Big Rusty Drums remains optional, not yet Windows tested.

## Open engineering/QA risks
1. Run frontend `cd app/frontend && npm run build`; this connector-based environment did NOT execute it. Fix any TypeScript/JSX problems before calling the UI build-clean.
2. Run backend unit tests (`test_drum_keymaps.py`, `test_polyphonic_midi.py`, `test_midi_section_composite.py`) and broader suite.
3. Open saved arrangement and switch Drum kit on; check note conversion/edit/undo/save/reopen, pitch lane labels, short drum note addition, selected sections, GM rendering through GeneralUser GS SF2, one accepted composite stem, channel split scripts, source masks and remove.
4. Import a compatible verified SFZ percussion kit, inspect actual playable note map and manually populate custom mappings; verify sample audio, note-off/release and exported WAV. Custom map currently labels/validates keys, not a sample remapper, round robin or choke engine.
5. GM/custom selected mapping is UI session state, not yet persisted as a revisioned arrangement attribute; reopening percussion notes detects drum mode but defaults kit selector to GM. Persist verified custom kit mapping with score as next iteration, before relying on saved arrangement reproducibility.
6. Potential piano-roll limit: drum display currently pitches 28-81 for useful GM range; custom SFZ notes outside this range require viewport/range controls.
7. Need exact editor QA to check textarea layout, scroll handling, and note editing performance.

## Next development
- Persist custom kit manifest/pitch mapping with saved arrangement, expose installed-kit presets and their actual playable notes.
- Build deterministic catalog-first instrument family/variant match service for LLM plans; match growlybass_dirty default, growlybass_angry chorus, growlybass_shifty bridge, industrial as direction.
- Maintain source integrity, user-named parent stem and L/R child scripting; dev only until explicit promotion.
