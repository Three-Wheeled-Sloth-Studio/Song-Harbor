# DEV UX QA checkpoint: whole-song scope and proposal discoverability
Date: 2026-11-05
Branch: dev only. Main unchanged at 2345c61.

## User-reported QA
Screenshot: piano roll 243 notes, saved r0. Direction contained Growlybass Dirty default / Angry choruses / Shifty bridges. Matcher correctly identified installed variants and counted three choruses plus two bridges but disabled Apply because the full arrangement has more than eight timeline sections. Mock proposal button was disabled because it required explicit section selection and was labelled Preview proposal. Direction field presented an entire example sentence as a placeholder. Review text was low contrast and crowded.

## Changes
- Instrument direction remains empty on reopen, including clearing previous score context. Removed full example sentence from placeholder; simple neutral guidance only.
- Empty timeline selection explicitly means Whole saved arrangement; piano roll prints scope and explains how to restrict it. Match library uses all visible song sections for whole-song direction. No arbitrary eight-section block: bounded 64 sections per operation, with existing maximum 600 seconds for audio.
- Mock proposal uses whole-song section IDs when none are explicitly selected. Button is labelled Generate mock proposal and review panel explains that it is an offline mock. No hidden or automatic AI action.
- Increased server request and domain limits consistently for sections and overrides, proposal preview, mock editing (up to 2000 changes) and composed candidates. Import candidate acceptance now permits up to 64 source replacement regions. All selected fragments still combine into one stereo stem per instrument.
- MIDI render slicing skips sections that have no MIDI notes, preserving original source audio without silently muting. All-silent selection still fails closed.
- Added CSS readability and spacing to direction and mock review bands, and regression coverage for 12-section slicing/composition and sparse sections.

## QA instructions
1. Windows DEV update/build. New slice has not been compiled in connector session.
2. Open score with >8 sections and no manual section selection; look for Whole saved arrangement (# sections) in top row.
3. Leave instrument direction empty: it should stay blank. Enter a fresh direction, Match library, review bridge/chorus/default and apply across all sections. Save before Render. Confirm only one combined instrument stem after review; no unexpected single-section additions.
4. With no manual section selection, Generate mock proposal should be available for clean scores with valid timeline sections. Preview should show note changes; Discard changes nothing; Accept saves only MIDI revision after confirmation.
5. Selecting a few timeline sections restricts matching and mock proposal. Use whole arrangement to clear the selection. No hidden 8-section cap. Check edits remain within selected scope, stale revision rejected.
6. Verify empty sections are skipped without replacement masks, and a selection with no notes rejects. Test >8 combined sections, L/R split and removal/restoration.
7. Backend tests: test_midi_section_slices.py, test_midi_section_composite.py, test_section_instrument_selection.py, test_midi_proposal_mock.py, test_midi_proposal_preview.py, test_midi_arrangements.py. Frontend: npm run build.

## Caveats
- Whole song here means all timeline sections intersecting the saved MIDI score. If a section extends outside the score, UI shows a scope error rather than silently omitting part of a section. A saved score with no song sections cannot use section-specific matching or mock section-scoped proposals.
- The mock is an explicit offline demo and does NOT interpret the musical instruction; resolving installed instruments only chooses verified presets.
- Rendering is still explicit and compositional, never automatically adds original stems or changes audio without acceptance.
- No tests executed here; need user's Windows build and playback QA.
