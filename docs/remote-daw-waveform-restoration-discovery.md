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
