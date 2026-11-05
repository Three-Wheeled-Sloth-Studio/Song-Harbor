# DEV checkpoint: offline mock proposal review and guarded acceptance
Date: 2026-11-05
Branch: dev only. Production main pinned at 2345c61.
User QA: most recent pre-slice DEV build clean. The changes in this checkpoint are not yet Windows-built or audio-tested.

## Implemented
- app/backend/midi_proposal_mock.py: deterministic, offline provider-neutral mock. Given an existing saved MIDI arrangement, selected song sections, part, and velocity delta (-20 to +20, nonzero), proposes a bounded list of velocity-only edits for notes wholly inside selected sections. No model, download, external connection, source or song mutations.
- app/backend/server.py: POST /api/projects/{ident}/midi-arrangements/{asset_id}/proposal-mock generates the proposal and review preview (read-only); POST /api/projects/{ident}/midi-arrangements/{asset_id}/proposal-accept revalidates the complete plan while holding the project lock, verifies current MIDI revision, section boundaries and installed instruments, then atomically saves the next revision of the editable MIDI arrangement. Does not render WAV, accept stems, or change original audio.
- app/frontend/src/MidiPianoRoll.tsx: offline mock proposal review controls within existing piano roll, with part selection (Bass/Drums/Guitar/Piano/Other), velocity delta, preview, note-level before/after velocity display (first 30 rows and complete count), explicit Accept MIDI edits confirmation and Discard. Accept reloads returned saved score; preview does not alter current notes. Any note edit, change of section selection, or reopen clears the preview.
- app/backend/tests/test_midi_proposal_mock.py: deterministic output, nonmutation, section scope, clipping and zero/invalid velocity limits. Existing test_midi_proposal_preview.py covers stale revisions, absent presets, outside-section edits, and forbidden vocal target.

## Confirmed behavior and granularity
- One combined output stem per instrument; variants can change by section. This slice is score-edit preview/accept only, not audio acceptance.
- Explicit human review required before note modifications. No LLM invoked. Never auto-edit Vocals.
- Existing saved section preset recipe remains separate from mock velocity changes. Save/preview/read-write work on the same revisioned score model.
- No modifications to main.

## QA gates
1. Windows DEV auto-update / frontend build. This checkpoint has not been built in the connector environment.
2. Open saved MIDI arrangement; select one or more complete timeline sections containing notes; use Offline mock proposal with +5 velocity. Preview shows before/after. Check no change in notes or audio until Accept.
3. Discard leaves score unchanged. Accept asks confirmation and increments revision, reloads score with changed notes and leaves original stem untouched. Render remains separate and explicit.
4. Edit a note or change selected sections while preview is displayed: proposal must clear. If score changed elsewhere after preview, Accept must reject due to stale revision.
5. Try note at boundary between sections, no selected sections, no eligible notes, invalid delta, Vocals selection unavailable, exceeding 8 sections; fail closed.
6. Run tests: test_midi_proposal_mock.py, test_midi_proposal_preview.py, test_midi_arrangements.py, test_section_instrument_selection.py, broader backend suite and frontend npm run build.

## Limitations / next
- This slice is a **mock** provider, not actual LLM planning. UI shows changes to velocity only; generic proposal endpoint can validate add, remove, update and preset recipe changes, but wider visual diffs still need polish.
- Proposal accept writes the new MIDI asset revision, not audio, and makes no transport or stem changes.
- Next slice: provider-neutral LLM adapter and structured proposal review for note additions/removals, score regions and instrument changes, behind explicit review. Local Ollama optional, no hidden network.
- Prior QA backlog remains: SFZ drum playback correctness, composite audio export parity, L/R routed splits, source mask restoration.
