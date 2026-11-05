# DEV handoff: library-aware instrument direction preview
Date: 2026-11-04
Branch: dev ONLY. Production main pinned at 2345c61.
Previous checkpoint: refs/handoffs/dev-instrument-section-presets-one-stem-2026-11-04.md

## User QA
User confirmed clean DEV build before this slice. This confirms previous DEV launch/build, not functional behavior of this newer matcher UI. No Windows audio render, full tests, or new UI build has yet been verified for these commits.

## Implemented
- app/frontend/src/MidiPianoRoll.tsx now includes an Instrument direction text area, Match library action, review of actual installed matched family/preset IDs and their default/section scope, and an explicit Apply verified presets button. It submits to POST /api/instruments/match-direction, available from the previous slice.
- The preview makes no changes. Apply updates only the existing instrument-default selection and section-specific preset dropdowns. It does not edit MIDI notes, generate audio, or overwrite sources.
- Section scope matches the existing timeline section kinds. With no explicit selection, preview targets the visible sections intersecting the arrangement. More than 8 sections must be narrowed first. A missing default variant, ambiguous catalogue match, unavailable preset, or nonmatching scoped section blocks Apply and shows a reason.
- Confirmed user granularity: one accepted stem per instrument with different presets per selected section; existing multi-section render and combine into a single candidate/stem is retained.
- app/backend/instrument_direction_match.py enhanced to assign section qualifiers within per-variant phrases instead of letting Dirty inherit Angry's chorus or Shifty's bridge, and supports prefix qualifiers such as 'chorus Angry, bridge Shifty'. test_instrument_direction_match.py extended for both variants of phrasing.

## QA requirements
1. Windows update/build first. The newest UI change has NOT been build-tested in this connector session.
2. Open saved Bass MIDI arrangement, import/choose installed Growlybass, enter: 'Growlybass Dirty as default, Angry for choruses, Shifty for bridges, maintain industrial elements.' Click Match library; expected preview one installed family, Dirty default, Angry chorus, Shifty bridge.
3. Confirm preview does NOT change default/section dropdowns until Apply. Confirm Apply chooses default and section overrides. Review the section dropdown values before rendering; verify unselected sections not touched.
4. Render selected sections, A/B, Add combined stem. Expect one user-named Bass stem with per-section preset audio and corresponding source-volume masks; inspect L/R child scripting and remove/restore.
5. Negative tests: family not installed, mixed pack names, two variants targeted at one section, no matching chorus/bridge, >8 selected sections, malformed instruction, unavailable preset after preview. All must fail closed.
6. Run backend tests (especially test_instrument_direction_match.py, test_section_instrument_selection.py, test_midi_arrangements.py, test_midi_section_composite.py); run frontend npm run build and check controls fit in piano-roll popout.

## Limitations and next steps
- This is deterministic library matching, not LLM generation. Unmatched words such as 'industrial' remain in request, but are not yet decomposed into edits.
- Matcher's phrase heuristics are bounded and imperfect; unusual syntax may be ambiguous. No silent auto-accept or whole-song audio transfer.
- Section preset choices remain temporary UI selections for rendering, not saved arrangement metadata. Persist these before LLM plans or reproducibility claims.
- Build provider-neutral validated LLM plan schema and read-only proposal diff; implement actual note edits only with revision guards and explicit user acceptance.
- Keep main untouched.
