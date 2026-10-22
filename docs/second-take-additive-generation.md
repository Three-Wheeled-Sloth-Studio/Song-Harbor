# Second Take: additive accompaniment first

Status: P2 approved product direction, 2026-10-22. Not implemented.
Initial user request: "I think some cello could be added to this section -
generate something that aligns well with existing instrumentation."

## Core job to be done

While a song is playing, select an existing section and request an additional
instrumental layer. Song Harbor should generate candidate *separate new
stems* that fit the musical context without rerendering vocals, drums or any
accepted track. The user auditions candidates in context and accepts only
the new layer they like. This is NOT simply remixing the entire mixed song.

## MVP scenario

1. Select a section (e.g. Bridge 2:05-2:28) or accepted time range.
2. Enter "Add an expressive cello counterline that supports the vocal, with
   restraint at the start and a stronger rising phrase approaching the
   next section." Choose instrument, role (pad, doubling, counterline,
   rhythmic accents), optional intensity and optional negative guidance.
3. Analyze needed musical constraints from existing audio: global/section
   BPM, meter, harmonic center/key/chord sequence, downbeats, phrase
   boundaries, vocal activity and dynamics, with uncertainty attached.
   Retain exact section start/end, audio sample rate and source provenance.
4. Provide existing stereo section mix or suitable instrumental context
   to a capability-checked model adapter. Evaluate ACE-Step / YuE2 for
   actual *separate conditioned stem* output. Do NOT assume prompt-to-song,
   remix or melody generation produces a clean independent accompaniment.
5. Request 2-3 candidates if resources allow, with deterministic
   selection and recorded model/prompt/seed parameters where supported.
   Use intro/outro context handles for attack, decay and transition.
6. Normalize and align candidates to the source timeline. Validate that
   duration, tempo grid, onset structure, harmonic conflict, output
   isolation and transitions are fit for purpose. Do not falsely state
   a model can guarantee harmonic match.
7. Load each candidate as a named, separately controllable new track
   (e.g. Cello_Counterline) through the approved add-track flow; audition
   A/B with level matching and solo/mute. Regeneration never touches
   accepted stems. Selecting a candidate is reversible.
8. Accept creates a new non-destructive track version with metadata.
   Reject keeps the original mix. The user may then edit/pan/gain/script
   the new stem by alias; renaming propagates through scripted guidance.

## Prerequisites before a coding sprint

- 16+ stem import/add and stable rename semantics are validated.
- Mix versioning and quick, loudness-matched candidate A/B are functional
  enough for a meaningful test.
- Bench an actual 15-30-second instrumental-only cello result conditioned on
  the existing arrangement. Measure time drift, onset alignment, harmonic
  fit, leakage from source music and timbral quality.
- If ACE-Step / YuE2 cannot supply isolated conditioned accompaniment,
  investigate a MIDI/symbolic line -> local cello virtual instrument ->
  rendered stem route. This is an alternate *test path*, not guaranteed.
- Constrain VRAM according to the base 12 GB machine; avoid loading many
  large models concurrently. No cloud dependency for MVP.

## Follow-ons, not in first increment

- Replace a defective region, change an instrument performance while
  maintaining neighboring stems, lyrical or vocal retakes and non-destructive
  comping.
- Automatic phrase edits are **not** a prerequisite; ordinary inserted
  sections may solve enough cases. Revisit surgical edits only when a clear
  user task cannot be expressed with sections or section subdivisions.

## Acceptance test

"Add cello to the bridge" produces at least one context-aligned independent
cello track, not a full-song stereo remix. It plays in sync, fades naturally
at section boundaries, supports named automation, survives reopen and export,
and can be accepted/reverted without altering any existing stem.
