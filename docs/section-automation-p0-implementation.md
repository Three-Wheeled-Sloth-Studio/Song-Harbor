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


## 2026-10-21 processed WAV export implementation (main)
The previous guard preventing export when pan curves exist has been replaced with `SharedClockAudition.renderWav24()`. It constructs an `OfflineAudioContext` from the *same decoded buffers*, per-stem level settings, active original-versus-split-child routing, child hard-L/R positioning, shared per-stem stereo bus pan automation and output sample rate as the live audition. Export is a browser-side 24-bit stereo PCM WAV; monitor volume is excluded. No backend FFmpeg mix endpoint changes were required; that endpoint remains a separate legacy route and does not represent the processed export.

A clipping render fails with a clear error rather than silently applying a mismatched limiter or normalizer. The offline path does not yet include reverb, width, creative processing or a tail extension. This is an implementation and build gate, not proof of audio parity without listening tests.

### Export parity smoke
1. In the 4:00 split-channel test track, preserve the saved vocal pan directives; run the usual `scripts/launch-song-harbor.bat` checkout of `main`.
2. Play 0:30-1:12 and verify vocal center-to-right movement. Export mix WAV from Tools, open the downloaded WAV in another player/DAW, and listen to the same times at matched loudness.
3. Compare split-L/R vocal center image to preview and check 2:05 Bridge reset and 3:48 Outro reset.
4. Ensure the mix export does not contain doubled parent + child stems and that playback was not timing-modified by rendering.
5. Reduce stem gains if the export detects peaks over full scale. Such a warning is deliberate, not a request to bypass headroom protection.
6. Change a section's pan, re-export and verify the new render differs accordingly. Monitor slider changes must not affect export amplitude.
7. Repeat a seek/pause/replay in the shared-clock player after export; confirm no drift.


## Spatial processing slice: initial section reverb send (2026-10-21)
- Added a deterministic 1.7-second diffuse stereo impulse shared by Web Audio audition and OfflineAudioContext rendering. Per-stem wet sends are mixed in parallel with dry stereo routing; split L/R channels remain reconstructed once, before the effect send.
- New supported token: `Vocals.reverb:30@2s:smooth` (0-100 wet-send percentage, 0.05-30s transition, default 1s smooth). Independent of `Vocals.pan` in the same brace line.
- `all.reset` and `Track.reset` reset both pan and reverb send to their initial neutral/default state. A missing reverb directive inherits the previous send target.
- Added structured **Section reverb** controls to the existing Tools sidebar with section, stem, wet send, ramp and interpolation curve.
- Production script import, song persistence and live preview are wired to `section_reverb_automation`. The same reverb and automation are included in offline WAV exports.
- This is ONE basic room response, NOT configurable acoustic room presets yet. Stereo width, tempo delay, final-tail extension and ending fades are later slices.

### Focused first spatial smoke test (The Logo and the Maw, split stems)
1. Use the already aligned four-minute vocal-pan sheet, with all six original stems split into left/right children.
2. In Tools > Sections, place `{Vocals.pan:center@2s:smooth Vocals.reverb:10@2s:smooth}` beneath Verse 1, and `{Vocals.pan:right.30@2s:smooth Vocals.reverb:30@2s:smooth}` beneath the first Chorus. Avoid 60% pan for musical judgments; that setting was for conspicuous pan QA only.
3. Keep Verse 2 without a block to test inheritance. In the Bridge use `{Vocals.reverb:45@4s:smooth}` (or an `all.reset` if testing reset behavior).
4. Apply the script, play across 0:34-1:12 and 2:05-2:28. Listen for a larger room on the Chorus and Bridge, with no clicks or sudden tail cutoff between sections.
5. Export a 24-bit WAV and compare with playback at matched loudness and same time. Check that dry vocal identity, separation and left/right timing remain intact.
6. Use the structured Section reverb editor to change the first Chorus from 30% to 20%, save, reload, and confirm the changed brace directive is still present in the Sections script.
7. Verify the exported file is not clipping. If a peak warning occurs, lower relevant stem gains in the mixer and retry.
8. Check that the original six stems and existing split child WAVs remain unchanged.

Limitations: Offline bounce currently ends at the original song duration (including truncating any remaining reverb decay); real-time playback also stops there. Extending the ending and preserving external reverb tails is subsequent work. No production-grade mastering or loudness matching has been implemented. Windows auditory QA and this commit's frontend/backend CI results are not yet verified.


## Clipping recovery workflow (2026-10-21, main)

The browser WAV bounce now analyzes the untrimmed summed mix before PCM encoding. When the full mix exceeds 0 dBFS, export **does not** create/download a file; instead the Tools > Export mix section automatically scrolls its actionable **Mix needs output headroom** panel into view. It displays measured untrimmed mix peak in dBFS, the recommended **additional** reduction to reach a -1 dBFS sample-peak ceiling, and an **Apply safe output trim and re-render** action.

The action applies an output-only master trim (after the stereo buses and reverb return, before the monitoring output), keeps existing individual stem gains, mute/solo and section pan/reverb automation untouched, makes that exact trim audible in shared-clock playback, then reruns the offline 24-bit PCM export. Output trim is also available through an always-visible -60 to 0 dB slider; it does NOT replace the independent monitor-volume slider. WAV export includes trim but deliberately excludes monitor volume. No limiter, compressor, makeup gain, normalization of tracks or source-file modification is implied. If the required correction exceeds -60 dB, the UI refuses auto-correction and suggests inspecting tracks/effects.

On successful rendering the app shows **Mix ready to download** and a clearly labeled **Download WAV** link. The generated file stays in browser memory until the user clicks Download WAV; the browser chooses its destination. Song Harbor cannot honestly report the actual browser download directory or open it until a future local-backend managed export is implemented. The output trim is currently SESSION-LOCAL and is not yet saved in the project manifest.

### Acceptance on split-stem 4:00 current song
1. Start Song Harbor using the ordinary launcher on **main**, open the current four-minute song with split L/R for all six stems, keep your existing pan/reverb script.
2. Click **Export mix WAV** without first changing stem gains. If the mix exceeds full scale, the headroom panel must appear beside Export, automatically scroll into view, show a numeric peak and suggested correction; no download link should appear yet.
3. Click **Apply safe output trim and re-render**. Stem sliders and section directives should remain unchanged, master trim should change, and the renderer should complete with a **Download WAV** link (unless another genuine error is reported).
4. Click **Download WAV**. Check the browser's configured destination or Ctrl+J, and compare the exported WAV against Song Harbor playback at matched loudness.
5. Play a Verse-to-Chorus vocal-pan transition before/after; ensure master trim changes overall level only and split-stem synchronization is intact.
6. Adjust the independent monitor volume: the rendered WAV should not change. Adjust master output trim: the subsequent WAV must change.
7. Test clicking Export again with sufficient headroom: the user should not see a clipping warning.

**QA gate:** These fixes are committed on main, but no local Windows build, actual browser download or listening smoke test was executed from this tool environment. A separate future slice should persist master trim and offer versioned backend-saved exports with a truthful destination/Open folder control.


## 2026-10-21 ending treatments: end-anchored dry fade and reverb post-roll

**Implemented on `main` (Windows listening QA not yet completed).** The Tools sidebar now has an **Ending treatments** panel. Presets **Clean fade**, **Atmospheric tail**, and **Clear treatment** only populate editable fields; pressing **Save ending** persists the parameters in the *last* song section and updates the section script. Equivalent canonical block:

```text
[Outro 3:48.183-4:00]
{Master.fade:6s:smooth Master.tail:3s}
```

- `Master.fade:6s:smooth`: the **dry** stereo mix holds until 3:54, then fades to zero at 4:00. Supported smooth or linear curves; 0-30 seconds in the sidebar, 0.05-30 seconds in active notation. Fades cannot exceed the last section duration.
- `Master.tail:3s`: adds up to 10 seconds of wet-only post-roll. A 4:00 original should render as a 4:03 WAV. The current reverb is a deterministic 1.7s impulse, so extra silence after its natural decay is expected; a tail only becomes audible when one or more reverb sends are active at the end.
- Important processing order: active split-L/R channels -> per-stem pan/reverb send -> **dry bus (faded)** plus **reverb return (unfaded)** -> shared master monitoring/trim. Live Web Audio and offline WAV use the same timing, fade and reverb impulse logic. Individual stem gains and section production are unchanged.
- `Master.fade` and `Master.tail` belong to the final section only; earlier placement and overlong fade produce explicit validation errors. A saved ending is carried in project `section_ending`; removing ending directives in a replace-mode section script resets it.
- A/B preview version history and generated musical extension are **not yet implemented**. Likewise the next width choreography is documented separately and is not yet an executable width directive.

### Windows test - The Logo and the Maw

1. Launch with the normal batch file on `main`; open the 4:00 split-channel project with existing section instructions intact.
2. In the existing **Ending treatments** panel, choose **Clean fade** (default 6s dry fade, 0s tail), then **Save ending**. Listen from 3:50 through the end. The dry mix should smoothly reach silence at 4:00; export should render ~4:00.
3. Choose **Atmospheric tail** (4s fade, 3s tail), then **Save ending**. Ensure Outro has a nonzero reverb send (e.g. `Vocals.reverb:35@2s:smooth` in its production block). Listen from 3:52 through 4:03; the performance should end by 4:00 while the reverb decay remains audible into the tail. Export WAV length should be ~4:03.
4. Open Tools > Sections and confirm the final Outro now contains `Master.fade:4s:smooth Master.tail:3s`. Save/reload the song and confirm the panel restores the chosen values and preserves all lyrics/pan/reverb notes.
5. Test seeking, replay, and pause/resume near 3:54 and 4:00; the waveform should not desync from the shared-clock player. Direct seek *into* a post-roll currently cannot reconstruct earlier reverb history and may sound different from continuous playback; this is a known limit.
6. Check that the previous headroom-fix flow still works for any clipping WAV; no stale download link should appear on failure.
7. Choose **Clear treatment**, Save, and verify the original 4:00 length returns and prior recordings were never overwritten.

Suggested initial preference for this track: **Atmospheric tail** with a moderate ending reverb send, but choose by listening rather than defaulting it into user content.

## 2026-10-21 P0 export fade correction + P1 A/B audition

### Fade diagnosis and fix

**Observed:** User confirmed rendered WAV carries noticeable section pan and spatial treatments but reported that the ending fade did not carry through clearly.

**Root cause identified in routing:** Prior graphs put the dry stereo buses through the ending fade, while the source continued driving the reverb convolver at full strength through the original audio endpoint. The *already wet* reverb output remained unfaded intentionally, but the continued unattenuated input could mask the musical fade in the resulting WAV.

**Implementation:** A dedicated `reverbDrive` GainNode was inserted between all per-stem reverb sends and the convolver, in **both** the live AudioContext and offline rendering graph. Both `dryMaster.gain` and `reverbDrive.gain` now receive the SAME end-anchored fade curve. The reverb *output* still bypasses the dry fade and decays naturally during the optional post-roll. Thus no new full-level vocal/instrument material is injected into reverb once the fade reaches zero. The fixed path is:

```
active original OR split L/R stem -> width -> spatial reflections -> pan bus
  -> dryMaster (end-anchored fade) -----------------------> master
  -> reverb send -> reverbDrive (same fade) -> convolver --> master
master -> saved output trim and independent preview-only monitor gain
```

This corrects **excitation** without cutting off **existing wet tails**. A true silent dry fade still requires active and nonzero `Master.fade` in the saved section script. Compare full final 4:00 musical endpoint and post-roll separately.

### P1 audition-only A/B comparison and effect bypass

Added an **A/B comparison & bypass** section to the existing Tools sidebar, deliberately without revisiting sidebar redesign yet.

- **A · Processed**: original saved section pan, width, early reflections, reverb, and ending are heard.
- **B · Original**: bypasses all five production effects in live audition, retaining source routing (including split L/R), individual stem levels/mutes/solos, and output master trim.
- Individual bypass checkboxes: pan, width, spatial reflections, reverb, ending. They can be toggled while auditioning. A/B changes are **session-only** and do not mutate project instructions or change the processed WAV.
- This is an **equal stem gain / output trim** comparison, NOT yet integrated-loudness-matched A/B. Loudness matching and historical mix snapshots remain future work.

### Windows acceptance test — current 4:00 song

1. Run the normal launcher on `main`. Confirm frontend builds, and open the saved song. All previous section lyrics, spatial settings and ending instructions must survive.
2. Inspect final `[Outro]` instructions; if necessary set `Master.fade:4s:smooth Master.tail:3s` in the ending tool. Check that Outro has active reverb sends so the return is audible.
3. Play continuously from 3:48 through ~4:03 and listen for performance/dry fade toward 4:00 plus **decaying**, not freshly sustained, reverb in post-roll.
4. Export the processed WAV, use the existing automatic master headroom correction if prompted, save by clicking **Download WAV**, and listen with a waveform editor around 3:56–4:03. Dry instrumental/vocal attack peaks should decline and cease near the original 4:00 boundary. The final 3s is ambience only, not continued full-volume music.
5. Toggle B · Original, then A · Processed in the same passage. Confirm the return of pan/width/reflections and ending fade. B will have an **unfaded original ending** by design, so do not confuse that with export.
6. Try bypassing **ending alone** while retaining reverb. It should stop the fade in live preview. Independently bypass **reverb** to hear the dry fade reach zero without a tail.
7. Export again while B is active: the WAV **must still contain the processed fade**, confirming A/B is purely an audition tool.
8. Verify no split-L/R drift, click or doubled stem, and that pausing or seeking behaves as before.

### Technical gates and future UI debt

- The current tools remain temporarily text-heavy. Future design-system refactor: **compact icon-first palette**, short hover/tooltip labels and status indicators, with editing forms hosted in pop-out modal/inspector overlays. Preserve full-width timeline/waveform usage; do **not** replace this with large blank margins.
- A/B loudness matching should measure an appropriate analysis interval or use independent reference gain, **not silently alter stem balance or export gain**.
- Pending: full Windows TypeScript build and auditory/quantitative fade test. Source code inspection verifies shared drive envelope routing; it is not by itself proof of audio output parity.
