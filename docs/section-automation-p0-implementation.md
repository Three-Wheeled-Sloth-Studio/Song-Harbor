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


## 2026-10-21 next slice: interactive section pan audition
- Added `SectionPanTool.tsx` in the existing production tools sidebar, without changing timeline geometry.
- New validated `GET/PUT /api/projects/{ident}/section-pan` persists per-section/per-stem pan target, transition seconds (0.05-30), and curve (linear/smooth). Saved section IDs and original stem filenames are required.
- Moving a section preserves targets by stable ID. Removing/replacing sections prunes orphaned targets.
- Saved values compile into per-source pan envelopes and schedule on the shared-clock Web Audio path. Imported section changes recompile preview automation.
- Explicitly exclude actively split parent stems from new pan edits for this slice. Their existing hard L/R routing stays intact.
- Current WAV mix export is blocked while pan targets exist. This is deliberate: offline parity is not complete and there must be no silent mismatched export.
- No automatic instructions are inferred from lyric/tag text yet; that's the *following* slice. The editor deliberately operates on canonical saved section records.

### User smoke-test sequence (after build/deployment)
1. Open a track with saved sections and unsplit Vocals and Other stems.
2. Expand **Section pan (preview)** in the right Tools column; choose Verse 1 / Other / 60% left / 1s smooth and Save.
3. Choose Chorus / Other / 60% right / 2s smooth and Save.
4. Play from 5s before the chorus, then seek into the transition and replay. Listen for smooth movement, no reset clicks, and no stem drift.
5. Reload the song and confirm saved values return. Move a section boundary and confirm the pan transition follows its new start time.
6. Try **Export mix WAV** and confirm the explicit preview-only safeguard (rather than exporting an unprocessed file).
7. Split a stem: the editor should exclude that source, while the original L/R routing is preserved.

### QA still outstanding
- TypeScript/Vite build and real Windows listening test not executed from this environment (no network access to clone/install).
- No preview/export parity, stereo width, reverb, gain envelopes or notation-based effect instructions.
- Current sound engine restarts the shared source scheduler when editing pan while playing; validate that this is click-free, or defer live updates to next play.
