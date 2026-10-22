# 2026-10-21 dynamics stability and cleanup inspection QA

## Delivered

1. **A/B dynamics:** `StemMixer.tsx` has `dynamics` in the per-effect A/B key list. **B · Original** bypasses compressor and ducking in addition to the existing pan, width, spatial sends, reverb, EQ and ending treatment. Bypass applies only to live audition; `renderWav24` remains processed.
2. **No source restart during stem fader changes:** `SharedClockAudition.setLevels` updates gains by short target ramp, tracks *changed effective gains*, and rebuilds only duck envelopes whose vocal key gain changed. It reschedules only the duck GainNode; it never calls `seek` or `setAutomation` from the levels path. Monitoring volume changes alone do not trigger the sidechain scan.
3. **Non-destructive rendered-mix QC:** `AudioCleanupAnalyzer.ts` scans final float audio after OfflineAudioContext rendering, before WAV packing. It records near-ceiling peaks after master output trim and sharp sample discontinuity candidates. The Tools **Sound cleanup review** panel appears after successful WAV render, with click-to-seek timestamps. No automatic repair and no media/project changes.

## Fullscreen, floating inspector and correction-trial QA (2026-10-22)

- **Fullscreen / closing:** Launch via `.bat` using selected Chrome or Edge default. Confirm a dedicated borderless fullscreen app window, not a tab in your normal browsing profile. Its far-right × requests confirmation and shuts down *only* that local Song Harbor instance; do not stop other browsers or parallel Song Harbor instances. Verify exit is blocked with an active import/separation job and rejected for incorrect instance token/foreign Origin. Test Firefox kiosk path separately if available. Unsupported browser defaults fall back to normal window.
- **Icon rail:** Waveform must occupy recovered horizontal space (no old 255px Tools sidebar). Icons have accessible labels and focus states. Selecting exactly one icon opens draggable floating context; drag across main waveform and confirm waveform playback remains interactive beneath outside the tool's area. Esc or × dismisses tool. Test pan, reverb, width, space, EQ, A/B, endings, zoom, loop, channel split, DAW handoff, Sections and Cleanup.
- **Sections editor safety:** Type unapplied text, switch to EQ, return to Sections; draft must remain intact until explicit Apply. Browser relaunch still requires Apply: draft persistence is memory-only.
- **Correction trial:** On known 03:35 clipping peak click Try correction A/B and loop. A Saved should sound like current saved processing. B Proposed lowers monitor/output trim by suggested ~1.2dB, changes output in realtime while loop runs; accepting trim applies session-only setting and does not rewrite source media. Confirm WAV export is unavailable until accept/discard. Repeat for 02:43 repeated loudness dips: choose proposed duck=0 on an applicable target, or compression ratio 1:1. A Saved/B Proposed should audibly contrast if effect is present. Adjust effect while loop continues; no transport restart. Clicking Accept must persist the correct section block directive and retain all other directives, original lyrics and section timestamps. Closing window, switching tools, or Discard must fully revert the preview (including A/B bypass state) without saving.
- **Safety/limits:** If a section has conflicting broad `Other.reset` or no saved section for the event, Accept should show a validation error, never silently overwrite the block. Verify a temporary preview never reaches processed WAV export. Accepted compression/ducking affects subsequent inherited sections per normal script semantics. Master trim remains session-only. Corrections apply at *section scope*, not phrase scope.
- **Performance:** Fullscreen app and tool window should not change audio fidelity or shared-clock stem alignment. Try with 6 parents and 12 L/R children. Floating panels must not force permanent right-side whitespace. Check CPU usage when adjusting live correction sliders; duck envelope rescans may still cost CPU.
- **CI:** `test_runtime_quit.py` checks guarded quit; frontend typecheck/browser smoke and Windows PowerShell syntax checks must pass. Local Windows app-shell and listening QA remains essential.

## Expanded analyzer and workflow QA (2026-10-22)

Implemented post-checkpoint: `AudioCleanupAnalyzer.ts` now returns categorized listening candidates for sample-level clipping/headroom, repeated flattened peaks, discontinuities, broad-band sibilance-like bursts, presence-band harshness, upper-band fizz, quiet high-frequency residue, stereo anti-phase risk, and repeated RMS dips. These are conservative deterministic *signals*, not ML artifact labels; don't claim identifiable separation artifacts or a functioning de-esser.

`CleanupReview.tsx` opens the review in a compact Tools panel immediately **below Sections**, with category filter, count/severity, click-to-seek timestamps, automatic **Loop ± context** audition, guidance, temporary Mark reviewed/Show reviewed, and approximate raw-stem activity hints. A finding should never silently alter the song or be saved as a repair. Full scan and processing may take appreciable CPU/memory on long tracks; cap displayed findings and watch for UI responsiveness.

**QA checklist:**

- Analyze a track with a known peak at 03:35. The Levels result should still appear, offer an appropriate output trim suggestion, and seek/loop around the event.
- Filter Vocal / high frequency, Stereo / mono, Dynamics, and Levels separately, verifying the list changes, count remains global, and Mark reviewed only hides that candidate until Show reviewed is turned on.
- Loop a finding while playback is paused. It should seek near the candidate, configure a short region and **start playing**; the existing transport should loop and remain aligned.
- Change master output trim or a stem/effect parameter; previously displayed findings should be invalidated (because they describe an earlier processed mix). Re-run manually. Edits during a scan should not publish stale results.
- Check a bright cymbal or industrial-distortion passage; a sibilance-like or fizz warning is a **possible false positive**. Never call it confirmed vocal sibilance without checking Vocals in isolation. Show active raw-stem hints as context, not causal attribution.
- Audition stereo-risk points in mono in a DAW (Song Harbor does not yet supply a dedicated mono button). A strongly negative correlation should trigger a candidate; a stereo-aligned sine must not.
- Check intended reverb/hiss, ambience and noise in quiet passages. Do not automatically gate or erase atmosphere.
- Run 4-minute and longer projects to watch main-thread spectral calculation cost; FFT twiddle tables are precomputed. If the UI is materially unresponsive, move scan to worker or perform chunked yielding without changing analysis outcomes.
- Run `node --experimental-strip-types --test app/frontend/tests/audio-cleanup.test.mjs`, the regular frontend build, and real-browser smoke. Test actual Windows audio render/export parity after update.

**Not implemented:** Source-separation artifact classifier, reliable source attribution, actual dynamic de-esser, intelligent repairs, automatic EQ changes, automatic gain reduction, true-peak metering, and saved per-song review decisions. Do not imply these work. Dynamic compression bypass remains a separate audition-only feature.

## Windows QA after update

- Open a saved song with `Other.comp:-18,2` and `Guitar.duck:3`. Audition the same section in **A · Processed** and **B · Original**. B should clearly omit dynamics while preserving the same manual stem levels and active split L/R routing. Individual `Bypass dynamics` checkbox should affect compression and ducking together.
- With A processed and music playing, move non-vocal stem level, then change Vocals level; the playhead must not restart or jump. Repeat while dragging *monitor volume*; this must not rebuild the duck envelope. Listen for possible transitions/glitches when changing vocal level.
- Toggle solo and mute on Vocals and verify ducking reacts to actual vocal activity. Verify all six stems remain synchronized after repeated fader changes.
- Render WAV and verify section compression/ducking remain present even with B audition mode selected; check preview/export sonic parity and ending fade/tail.
- After successful render open **Sound cleanup review** in Tools. Test a quiet/silent song (zero findings), a synthetic clipped peak near 0 dBFS (warning candidate), and a deliberately abrupt sample jump (review candidate). Click timestamps to seek. Listen before treating percussion samples as clicks. When output exceeds headroom, fix master trim and re-render before inspecting.
- Inspect long-song rendering performance: the first-pass analysis loops across all stereo samples once, in addition to WAV encoding; watch for unacceptable pauses or UI freezes on 4-15 minute mixes. If too costly, merge the analyzer with PCM packing or move to a worker. Do not pretend this is measured.

## Limitations and next priorities

- This detector is **only** peak headroom and single-sample discontinuity. It does not identify vocal sibilance, artifacts, clipping distortion beyond sample headroom, source stems, broadband noise, or causes of compressor pumping.
- Candidate cutoff >=0.7 sample-to-sample delta may flag legitimate very sharp drums or distortion and miss small click artifacts. No automatic audio changes or magic cleanup claims.
- Large duck envelopes are regenerated in the main thread when actual vocal gain changes. Consider caching normalized RMS and applying gain scaling to avoid rescanning buffers during live vocal fader movement. For continuous live automation, consider scheduling only a future envelope segment rather than the full song; listen for time spikes.
- Section `setAutomation`, `setEnding` and A/B switches still restart sources when editing static arrangement or switching modes; the fader path specifically no longer does.
- Next: real-world audible QA, analyzer optimization, gain-reduction/activity meters, then targeted de-essing and artifact classification.
- Update in-app Help (`HelpDialog.tsx`) and `docs/user-guide.md` for any capability change.
