# P0 section automation implementation slice

Status: preliminary implementation branch, not yet user-facing or export-ready.

## Implemented
- `SectionAutomation.ts`: section target -> song-time curve compilation, default 1-second linear transition, optional smoothstep transition, bounds/overlap validation, interpolation, and AudioParam scheduling from an arbitrary seek offset.
- `SharedClockAudition.ts`: allocate a panner on all sources (including centered sources); add source-keyed pan curves; reschedule on shared-clock play, seek and loop restart.
- The parent/child audio routing continues to be selected upstream. No new duplicated audio source is introduced.

## Explicitly not yet implemented
- Section UI controls or saved automation metadata; no actual curve is supplied to the engine yet.
- Gain automation, wet effects, reverb/width and custom envelope editing.
- Matching offline export; existing WAV mix export does not apply new pan curves.
- Automated/browser audio tests and Windows hearing QA.

## Next changes, in order
1. Define persisted per-source section target records keyed by stable section ID and source key, rather than stem filename alone.
2. Build a compact parameter editor in the existing tools sidebar; avoid narrowing the timeline or leaving unusable margins.
3. Recompile and apply curves when section markers change, and map split child source keys independently.
4. Implement deterministic offline render parity before exposing an enabled production export.
5. Add tests for 0/1-second and shortened transitions, smoothness, seek into the middle of a ramp, pause/resume, loops, rapid pan edits, center/mono preservation and split L/R phase alignment.
6. Then add width, reverb sends and gain envelopes.

## Acceptance gate
Do not merge as a completed production feature until a live track can set, audition, persist and export a section pan automation curve, with the offline audio matching the synchronized preview. Playback regression tests must include the user's previously problematic halfway-through section.
