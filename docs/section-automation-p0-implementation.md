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


## Two-line section production grammar (2026-10-21)
Canonical notation for this MVP is the bracketed section header followed by an optional single brace line. Example:

```text
[Verse 1 0:15-0:45]
{Other.pan:left.60@2s:smooth}
[Chorus 0:45-1:15]
{Other.pan:right.60@2s:smooth}
[Verse 2 1:15-1:45]
[Bridge 1:45-2:15]
{all.reset@2s:smooth}
```

Rules: a missing directive inherits its previous target; transitions are relative to song-time boundaries and default to 1s smooth; `Other.pan:reset`, `Other.reset` and `all.reset` restore automation overrides to the centered stem pan default without touching mixer levels or master monitor volume. `all.reset` only resets the currently supported pan automation, not future EQ/reverb until implemented. Track aliases are case-insensitive and must resolve to one of the six source stems. Unrecognized/unsupported effect directives (including width/reverb at present) are rejected, not silently ignored. Generation-engine prompts keep the clean bracketed header, not the brace line.

The existing structured pan editor is still available; the Section script editor is the text round-trip view. Pan targets imported through the Section script are immediately transferred to the existing shared-clock audition engine. Exports remain blocked when automation is active, because offline parity is not implemented. The compiled automation does not change source audio.

### Smoke test - after installing/building this feature branch
1. Open a section-aligned project, ideally with the Other stem not split.
2. Open Tools > Sections, edit three existing timed sections without changing their timestamps, and place a line `{Other.pan:left.60@2s:smooth}` immediately after Verse 1 and `{Other.pan:right.60@2s:smooth}` after the following Chorus. Leave the next Verse without braces. Apply.
3. Play the boundary from at least 5 seconds beforehand. Check a smooth left-to-right movement over 2 seconds. The next Verse should remain right.
4. After a later existing section, add `{all.reset@2s:smooth}`. Apply and listen for the controlled return toward center.
5. Seek into both ramps; pause/resume; loop across the Chorus. Listen especially for any restored stem drift around the previously problematic halfway passage.
6. Close and reopen the project. Open Sections and confirm text survived the round-trip with brace instructions intact.
7. Move one section boundary using the timeline and confirm its pan target moves with the section.
8. Confirm unsupported `{Vocals.width:120}` fails validation with a useful error and leaves saved instructions intact.
9. Confirm mix export warns that section automation is preview-only rather than delivering a mismatched WAV.

Limitations: this is a pan-only initial smoke test. Width/reverb are deliberately not active. Automated tests are committed but have not run in this environment. Review the results before enabling processing export or merging.


## 2026-10-21: split L/R stems and launcher branch correction
The supported launcher is `scripts/launch-song-harbor.bat`, which calls `start-song-harbor.ps1` then `update-checkout.ps1`. The updater fetches `origin/<currently checked-out branch>` and fast-forwards only. The expected normal installation is checked out on **main**. P0 was merged and further split-routing work committed directly to main; do not require switching to a feature branch for QA.

Every original stem, whether played as a stereo source or as active L/R children, routes through one stereo group pan control after its individual channel routing. Parent and split children remain mutually exclusive. The canonical `Vocals.pan` instruction pans this reconstructed vocal bus as one group, with neutral pan leaving existing split L/R positions intact. The structured pan editor now permits editing split parent stems.

Dedicated 4:00 production-script fixture for this track: `docs/qa-vocal-pan-the-logo-and-the-maw.md`. The 60% pan extremes are deliberately exaggerated test settings, not recommended mastering positions.

Remaining gate: real Windows headphones listening QA, including perceptual stereo quality, stem alignment, seek/resume/loop, and export blocked while automation is active.
