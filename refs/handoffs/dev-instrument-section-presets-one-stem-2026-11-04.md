# DEV checkpoint: one instrument stem with section-specific presets
Date: 2026-11-04
Branch: dev only. Main is pinned to 2345c61.

## Requirement
User explicitly permits one stem per instrument, but NOT one stem for each instrument multiplied by every section. Example: Growlybass Dirty default, Angry chorus, Shifty bridge -> one accepted Bass stem spanning the selected sections, with source masks for only replaced regions.

## This slice
- `app/backend/section_instrument_selection.py`: pure, bounded validation of up to eight section-specific pack/instrument IDs against the installed SF2/SFZ catalogue; default preset fills unoverridden sections; rejects duplicates, unknown sections, absent or synthetic instruments. No LLM guess or automatic changes.
- `app/backend/server.py`: `render-sections` request accepts `section_instruments` overrides and resolves the correct installed preset for each section before rendering independently reviewable candidate audio. The existing `bass-midi/compose-sections` consolidates those previews into ONE stereo candidate with multiple reversible source masks. Added section-to-instrument and candidate SHA provenance to consolidated candidate metadata.
- `app/frontend/src/MidiPianoRoll.tsx`: per-selected-section instrument dropdowns with the existing default selected instrument as fallback; the render request includes only chosen overrides. Multi-section section selection and one-stem combined acceptance remain intact.
- `app/backend/tests/test_section_instrument_selection.py`: cases for Dirty/Angry/Shifty, duplicate/unselected overrides, uninstalled defaults, nonexistent or synthetic presets, maximum selections and nonmutation.

## Important behavior
- This is one instrument/part per saved MIDI arrangement; repeat workflow for Bass, Drums, Guitar, Piano, Other. The generated combined candidate is one stem per instrument with selectable section sound changes, not one stem per section.
- The existing UI renders section previews and then requires the user to review and explicitly click Add combined stem. It does NOT silently accept stems or rewrite the source.
- Instrument matches from catalog-first endpoint are not automatically connected to the new selectors yet. That is the next orchestration slice.
- The per-section preset selections are currently transient UI state; the combined render candidate records verified selected IDs, but persistent, editable section assignments inside saved arrangement assets are future work.

## QA status
Previous user DEV auto-update was clean, no other QA. New slice has NOT been compiled or Windows functional tested. Regression test code committed but not executed in this connector session.
QA: run frontend build, backend tests, section rendering on installed Growlybass family, inspect preview differences, accept one combined stem, confirm L/R channel split and per-section masks, export, remove and restore. Ensure no duplicate source masks or accidental single-section acceptance. Main remains untouched.

## Next
1. Integrate catalog-first match preview into reviewable assignment UI. Match actual installed variants before interpreting musical direction. No automatic LLM editing.
2. Persist editable section preset overrides as versioned arrangement metadata; validate against installed catalogue at render.
3. Provider-neutral LLM plan validator and preview diff for Bass/Drums/Guitar/Piano/Other.
4. Address verified drum SFZ note/sample mapping and broader stereo QA.
