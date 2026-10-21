---
type: Product Discovery
title: Waveform, Remote DAW Control, and Audio Restoration
status: research-and-design
date: 2026-10-20
---
# Integrated waveforms, remote DAW bridges, stereo room and unobtrusive audio repair

## User direction, 2026-10-20
- Elevate real waveform display into the first player/integrated-timeline milestone, not a late analyzer extension.
- Deprioritize Audacity as strategic integration surface; retain optional surgery/cleanup handoff.
- Discover and verify genuinely remote-controllable DAWs before concluding that Song Harbor must recreate all DAW capabilities.
- Explore detection and conservative repair of audible synthetic-generation artifacts (e.g. unstable vocal harmonics, metallic warble, harsh/noisy upper frequencies, transient smear, clicks, separation bleed, stereo anomalies) as a quiet cleanup/quality function, not prominently marketed as 'AI detector evasion'.
- Vocal width is a storytelling and room cue: solo human narration relatively narrow; normal leads and small backing voices intermediate; massed choir/choral refrain very wide using genuinely independent voice layers, spatial sends and early reflections. Keep center intelligibility and mono compatibility. Room size/width/depth and wet/dry ambience can vary across sections.
- Creative human/organic bias left, impersonal/mechanical bias right, orchestral/environmental elements wide, rhythm and bass anchors centered. Avoid rigid panning rules and large correlated-source Haas tricks.

## Remote DAW candidate evidence (research only; none implemented)
1. **Ardour — serious OSC + Lua candidate**. OSC receives transport, track/strip, panning, plugin and editor commands; Lua editor actions and session scripts have direct session APIs and can generate automation. https://manual.ardour.org/using-control-surfaces/controlling-ardour-with-osc/ and https://manual.ardour.org/lua-scripting/ . Windows officially supported, open-source GPL; prebuilt full version generally requires small payment, demo periodically mutes after 10min. Commercial embedding or shipping Ardour binaries/plugins requires GPL and dependency-license review. https://ardour.org/faq.html
2. **REAPER — most mature scripting candidate**. ReaScript Lua/Python/EEL2, extensions, OSC/MIDI control and extensive project/edit API. https://www.reaper.fm/sdk/reascript/reascripthelp . 60-day fully functional evaluation; qualifying discounted license currently $60; not a perpetual free dependency. https://www.reaper.fm/purchase.php
3. **Waveform Free — OSC/MIDI configurable control surfaces**. Scripted surface modes documented, but do not assume arbitrary session creation/effects/automation via external API. https://tracktion.github.io/waveform_manual/latest/reference-settings/ . Continue existing adapter.
4. **MorningDAW — MIDI Learn**. Maps controller messages to device parameters, transport, faders; capable of automation but not a verified full session API or external control protocol. https://edu.morningdewmedia.com/pages/morningdaw/manual/ . Continue optional manual handoff, test virtual MIDI loopback commands if needed.
5. **Audacity — repair, not strategy**. Maintain handoff but stop expanding feature-specific integration unless a clear repair necessity appears.

### Bridge feasibility spikes before choosing strategy
For Ardour and REAPER on Windows: (A) discover/launch installed DAW, (B) create six aligned audio tracks from known WAV files, (C) set track pan and gain, (D) insert EQ/delay plugin with parameters, (E) write several time-varying pan/width/send automation points, (F) render song or region to aligned lossless WAV, (G) recover after crash/reopen, (H) inspect license/reproducibility and user-control security. Record what is OSC-only, what requires an internal Lua script, what is permitted in free/demo versions, and time/effort. Do not infer full bridge from 'has OSC'. Prefer structured local IPC and explicit user opt-in for external DAW process actions; avoid blind keyboard macros.

A capable DAW bridge **does not eliminate Song Harbor's own** versioned track graph, waveforms, routing, non-destructive effects recipes, A/B feedback, analysis, or media portability. Own the project intent; render in a backend that meets the capability contract.

## First integrated timeline milestone
P0 waveform pyramid/cache for each source and derived track (min/max peaks at progressively coarser resolutions); shared horizontal time coordinate; zoom/scroll; precise cursor seek; section drag/stretch + optional snap; loop selection; expandable parent/child channels without double playback; persist/reload active routing; test PCM reconstruction at defaults and preview/export parity. At current code baseline `StemMixer.tsx` has six HTMLAudioElement instances with periodic drift correction, **not** a synchronized DAW-class transport. Waveform cache should be computed server-side rather than loading all full-resolution samples into JS memory. Timeline should support future clip lanes, FX automation curves, analysis overlays and A/B takes without redesign.

## Spatial storytelling presets (initial proposals, not mandated numeric settings)
- **Narrator/solo intimate:** mostly center or modest human-left tilt; narrow direct sound, restrained short room, preserve consonant intelligibility.
- **Human duet/small ensemble:** spread independent parts moderately, not simply L/R copies; subtle left/right answer-back if lyric calls for it.
- **Mass choir/choral refrain:** wide decorrelated voice layers/independent harmonies, stereo room reflections/reverb return, center presence preserved; mono check essential. Avoid 'stereoizer 200%' on a single narrow vocal track.
- **Machine/impersonal voices:** right-biased direct layers or right-weighted effect returns, potentially automated from narrative transitions.
- **Orchestral/environmental bed:** broad spatial returns and independent ensemble placement; avoid separating unrelated instruments from the Other stem by pretending L/R channels are distinct parts.
- **Transitions:** section-driven width, ambience size, reflection timing and pan envelopes with gradual motion and bounded extrema; no restless whole-mix panning.
Allow track/section tagging: narrator, lead, duet, backing, choir, organic, mechanical, orchestral, ambient; additional 'room intent' attributes (intimate, medium room, cavernous/communal, exterior etc.). Suggestions remain opt-in and A/B judged.

## Audio artifacts and provenance
**Objective: better audio, not fool detectors.** Detect and prioritize audible defects in source and separated stems: click/pop, peak clipping, warbling vocal/formant pitch, high-frequency fizz/metallic resonance, smeared transients, excessive constant noise, phase/mono anomalies, unexpected silence, pumping, stem-separation bleed. Measure region-local confidence, provide listening loop and spectrogram support, suggest narrow reversible repairs: declick, local spectral attenuation/notches, de-ess, dynamic EQ, transient reshaping, denoise, interpolation/crossfade, spectral restoration or replacement of limited contaminated region when reliable. Evaluate whether repair introduces musical loss or further synthetic artifacts. Prefer raw source when separation damage causes the issue.

**AI-origin classifier optimization is not a fidelity metric**, cannot promise change in detector scores, and should not be positioned as a feature. Distinguish statistical origin guessing from embedded provenance. For example, Suno publicly documents C2PA credentials on newer downloads; provenance can survive normal handling and is not simply an audible artifact. https://suno.com/suno-credentials . Preserve available origin/provenance metadata through derivative workflow where supported, and preserve internal edit history, without claiming a repaired file was fully human performed or deliberately trying to strip watermarks. C2PA mastering/mixing actions: https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html .

### Quality-control rollout
P0 objective click/clipping/anomaly detectors plus waveform/spectrogram overlays, no invisible repair.
P1 conservative local repair candidates, level-matched region A/B with Better/Worse/Reroll and keep-original.
P2 vocal modulation instability and difficult spectral defect analysis as research (high false-positive risk for deliberate vibrato/industrial distortion); optional neural restoration with model/license benchmarking.
P3 user-profile adaptive cleanup ranking and album consistency analysis.
Capture noisy/noisy-control fixtures, dry and processed stem fixtures, authentic deliberate distortion. Report preservation, false positives, compute time and perceived benefit per detector.

## Proposed execution sequence
1. Integrated waveform timeline and dynamic parent/child track graph / routing with export parity.
2. DAW bridge spikes (Ardour and REAPER) in parallel with shared audio transport/DSP decision. Continue Waveform/MorningDAW as external manual production options.
3. Spatial stereo foundation: pan, choir width, spatial send buses and section-linked automation with human A/B.
4. Basic unobtrusive quality inspection and repair candidates, analysis overlays.
5. Guided effects, learning/reroll, deeper arrangement and stem regeneration later.

No new application code is implied by this research note; commit is a design/reference update.

## 2026-10-20 incremental implementation and decisions

A **first playable-workspace waveform overview** is now implemented: `app/backend/waveform_peaks.py` obtains bounded 2048-bin min/max waveform previews using FFmpeg decoding and caches them under `jobs/<id>/waveforms`, keyed to source size/mtime. `GET /api/jobs/{ident}/waveform/{filename}` exposes previews only for validated original stem filenames. `app/frontend/src/StemWaveforms.tsx` displays six aligned waveform rows with a shared playback cursor and click-to-seek, mounted within `StemMixer.tsx`. Regression tests cover shape/cache invalidation in `test_waveform_peaks.py`. **Not yet**: integrated section overlay, independent L/R child rows, zoom/scroll/detail pyramid, true DAW shared-clock transport, waveform editing, beat snapping or render parity; no Windows build/CI verification yet.

A compact exploratory section-spatial grammar is also committed in `app/backend/production_cues.py`, with tests. Example:
```
[Chorus 1:15-1:45 Vocal1:Expansive-Left Drums:Narrow-Right Bass:Moderate]
[Verse 2 1:45-2:10 Vocal1:Narrow-Left Machines:Moderate-Right]
```
Its parser only returns typed **proposals** for an arranger/processor; it has no audio side effects, is not connected to the UI and uses track aliases pending a real stable-ID resolver. In particular, `Expansive-Left` means independent perceptual *width* and leftward *bias*, not hard pan. The bracket grammar is Song Harbor's proposed production language, not YuE2/ACE's native section instruction format; adapters must translate canonical sections and effect cues separately. Timeline editing must round-trip these objects without requiring users to type strings.

**Ardour demo clarification:** Official Ardour free/demo binaries periodically silence playback after 10 minutes running. A legitimate locally compiled Ardour from GPL source does not inherit this demo-binary restriction. However, official MSVC Windows build steps are explicitly unsupported and may require fixes: https://ardour.org/building_msvc.html . Official unrestricted binaries are available for a small payment at https://community.ardour.org/download ; compare cost to engineering time before embarking on a build. Source build/licensing considerations still apply to redistribution. OSC can manipulate strips and transport; don't assume arbitrary Lua calls with arguments through OSC. Ardour scripting docs: https://manual.ardour.org/lua-scripting/ . REAPER trial can remain unstarted while waveform and grammar foundations are built.

## Provenance and watermark distinction (primary-source check, 2026-10-20)
Suno's current Content Credentials announcement specifies C2PA metadata attached to newly downloaded songs: https://about.suno.com/suno-credentials . Its Terms of Service explicitly restrict removing, altering, obscuring or circumventing watermarks/fingerprints/metadata **for the purpose of concealing or misrepresenting provenance, service tier or status**: https://about.suno.com/terms . User's valid production concern is that *one generated instrumental inside a heavily edited composition must not falsely imply the entire arrangement was unmodified AI output*. Product solution: model **per-source/track provenance and edit lineage** (human performance, generated instrumental, synthesized vocal, repair or processing) and export an accurate derivation record/credits when supported. Never claim a mastering filter can guarantee origin-detector outcome. 
Unobtrusive "Audio Quality" inspection and repair should target *audible* problems and preserve provenance information where applicable; no generic watermark-stripping or origin-concealment operation is implemented/planned. Evaluation can still measure false positive/false negative rates of classification tools when assessing quality/reliability, separate from changing output to defeat their thresholds.

## Ardour procurement comparison
Official Windows demo's audio periodically goes silent after 10 min runtime; full paid binaries have no demo silence, and normal GPL source builds do not inherit it. Official [MSVC build recipe](https://ardour.org/building_msvc.html) is unsupported and may need manual repairs. Current purchase options allow low-cost one-time payment for current major version (https://community.ardour.org/download?architecture=x86_64&paymentSelection=options&platform=win&type=compiled) or $1/month subscription and access to nightlies. Given developer hours, try inexpensive official unrestricted binary rather than spending a day troubleshooting Windows dependencies unless build/test/distribution is itself the objective. **Do not start REAPER's 60-day trial yet** per user's preference.


## 2026-10-21 revised production roadmap after verified WAV spatial/fade QA

User confirmed processed audio and WAV export both sound good after spatial effects and fade corrections. The browser GET /favicon.ico 404 is cosmetic and can be fixed by shipping an icon/link.

**New workflow requirement:** Add an in-app **Check for updates / Install & Relaunch** action. Reuse the existing safe `scripts/update-checkout.ps1` fast-forward logic rather than introducing a second updater. Must preserve dirty files and refuse conflicting/diverged changes; check `/api/runtime/status` for active processing jobs; never kill unknown listeners; coordinate backend stop, fetch, frontend build and reopen with an independent launcher/helper so the running service does not terminate its own only restart mechanism. Show version, available commits, changelog/result and rollback guidance; only offer actual restart after update/install validation. Do not run background auto-update while jobs are active. Manual current behavior remains valid until implemented.

**Audio priority** (favor dynamic script automation, which avoids many manual DAW clip edits):
1. Parametric EQ, with frequency/Q/gain/type, named validated presets and smooth per-section interpolation. Dynamic EQ and de-ess use related detector infrastructure.
2. Compressor and safe sidechain ducking keyed to source stems or vocal activity; strong dynamic/phrase-aware value. Meter gain reduction. Avoid overcompressing already mastered AI material.
3. Detection-first audio cleanup: sample peak/true peak, clicks, clipping, sibilance, high-frequency fizz, stationary noise, unstable resonances, stereo phase/mono compatibility, transient smear, separated-stem bleed. Flag exact time intervals and confidence, provide loop audition and original/repair A/B.
4. Bounded, reversible region-local treatment: short fades/crossfades, declick, de-ess, dynamic EQ, surgical filter adjustments, limited noise attenuation; do not automatically overwrite originals. Time-range scoped production directives are essential because sections alone are often too coarse.
5. Tempo-synced stereo delay and rhythmic spatial modulation, separate from fixed 13/19ms early-reflection widening. Later: spectral restoration or generative regeneration only after the conservative QA workflow is proven.
6. Mix diagnostics: mono collapse, correlation, loudness-matched A/B and frequency-buildup warnings, with optional gain-reduction and spectra overlays.

**Script design:** prefer an extensible, typed graph of track-level, section-level and *time-range/phrase-level* targets with preset references plus explicit numeric parameters and transition shapes. Keep effect order unambiguous and identical in live playback versus offline WAV; add parameter persistence and A/B tests before broad feature rollout. Example EQ notation in exploratory discussions is NOT executable yet; do not paste unimplemented directives into the active section sheet.

**Deferred design-system UI debt:** right-hand Tools area has become verbose. Convert to **compact icon-first tool access, informative status states, and pop-out modal/inspector for long settings**. Preserve full timeline/ waveform width and avoid empty margins. Base shared patterns in TWS-UI rather than repeating a bespoke approach.

**Milestone boundary:** basic cleanup is ~2-3 implementation slices away if EQ/dynamic processing and diagnostics are tackled next, not a claim about elapsed time. Advanced harmonic/voice warble restoration remains separate research, with evidence-based quality evaluation.

## 2026-10-21 implementation: update/relaunch + first parametric EQ

**Committed to `main`; Windows build and user listening acceptance outstanding.** This is the first focused slice after the user accepted the script-first effects roadmap.

- **In-app updates:** header ↻ control calls GET `/api/runtime/update` on demand. It uses read-only branch checks plus `git fetch` (which updates remote refs but not the working tree), reports revision/current vs remote, divergence and busy state. Explicit **Install & relaunch** confirmation sends a per-instance token to POST `/api/runtime/update/relaunch`. When the app is not busy and the Git history can fast-forward, a **separate** PowerShell terminal starts `scripts/relaunch-song-harbor.ps1`, waits for the current backend PID to exit, invokes existing non-destructive `update-checkout.ps1`, and relaunches `start-song-harbor.ps1 -NoUpdate`. Conflicting local changes are never reset or stashed. The old browser may remain open but a new browser window is opened. Save unapplied text edits before restarting.
- **Favicon:** lightweight SVG icon in `app/frontend/public/favicon.svg`, linked from `index.html` and explicitly served at `/favicon.svg`.
- **Three-band peaking EQ:** `{Vocals.eq1:320,1.2,-2@2s:smooth}` controls band 1 at 320 Hz, Q 1.2, -2 dB gain. Bands `eq1`, `eq2`, `eq3` can all be set in one section alongside pan/width/space/reverb/ending directives. Supported frequency 30-16000 Hz, Q .3-12, gain -12..+12 dB, transition .05-30 sec. Omitted sections inherit; reset restores all 3 bands' gain to 0. Source files unchanged. Three cascaded Web Audio peaking filters run **after split-child reconstruction and before stereo width** in BOTH live/offline graphs. Bypass EQ from the A/B panel without changing WAV output. The structured **Parametric EQ** tool saves via PUT `/api/projects/{ident}/section-eq` and round-trips into canonical production blocks. The current EQ does **not** offer dynamic threshold-following behavior, shelves, high/low-pass, spectral repair, or plugin hosting.
- **Strategic acknowledgement:** A full effects rack and third-party/plugin hosting **are eventual product capabilities**, but not near-term priorities. Favor section-/phrase-aware processing difficult to automate manually in conventional DAWs. Future plugin compatibility will need format/platform/licensing/security choices (e.g. VST3 on Windows), sandboxing/crash containment and deterministic offline rendering; do not describe it as already supported.

### Windows QA gates

1. Start from `main`; the normal launcher still performs its own safe update/build and should display Song Harbor with no frontend errors.
2. Click the **↻ Check updates** header action. Current branch/revisions should appear; if already up-to-date, don't offer an unnecessary restart. Diverged Git or busy processing should block restart.
3. If an update is actually available, save all in-app edits, choose **Install & relaunch**, accept the explicit confirmation, observe the separate update console and newly opened Song Harbor. Verify dirty checkout files are untouched, songs/projects and audio continue to open.
4. Open a song's **Parametric EQ** control. Choose Vocals, Verse 1, band 1, 320 Hz, Q1.2, -2 dB, transition 2 seconds, save. Inspect the section script for `Vocals.eq1:320,1.2,-2@2s:smooth`; check it survives closing/reopening and project reload.
5. Audition with EQ bypassed vs active at matched monitoring/output volume. Then export WAV, inspect that its EQ matches processed audition while keeping split L/R alignment and pan.
6. Set a second band in the same section; verify neither instruction replaces the other. In a later section, set band 1 +2 dB and verify smooth transition/inheritance. Use a reset and verify EQ returns to neutral, without erasing other automation.
7. Re-import the existing 13-section full spatial sheet (if testing import). It has no EQ directives and must remain unchanged in sound and structure; no accidental EQ must be imposed.
8. Since the backend/routing edits were made remotely without a Windows runtime, successful source commits **are not evidence of a passing local TypeScript build or actual audio QA**.

Next DSP slice: compression and vocal-dependent ducking, then quality diagnostics/region repair; UI compact icon-first inspector design remains deferred.
