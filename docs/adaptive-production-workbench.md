---
type: Product Design
title: Adaptive Production Workbench
description: Human-directed analysis, audition, learning and production workflow for separated music.
status: design-direction
tags: [production, analysis, ab-testing, local-first]
---
# Adaptive Production Workbench (2026-10-19)

## Status and scope
User-approved direction, **not implemented functionality**. Current six-stem separator, Library, basic mixer/export and optional external DAW handoffs remain the functional baseline. Product-first development; the first one or two tracks of *Voices Below the Deck* will be finished manually in Waveform and Audacity, with observations returned to inform the product. Do not block the publishing schedule on feature work. Predator is current machine; no local QA is requested.

Avoid confusing this proposed increment with the historical generation roadmap's M3 ("First Surgery"). Call it **Adaptive Production Workbench** until roadmap identifiers are reconciled.

## Governing principles
- Local-first, zero-cost-first, original source and separated stem immutability, durable song/version history and reproducible render artifacts.
- Human taste and checkpoints control every creative acceptance. Analysis suggests; it does not silently transform accepted audio.
- Instant or low-latency loudness-matched A/B is a first-class workflow, not a secondary toggle.
- User judgments are useful preferences, not universal acoustic truth. Opt-in local learning, explainability and feedback inspection/reset are required.
- Reuse shared TWS-UI dense, icon-first controls; contextual help and recovery. No workspace takeover.
- Maintain strict distinction between objectively measured defects, inferred hypotheses and aesthetic recommendations.

## Proposed user journey
1. Open a completed six-stem song and choose or create a named, non-destructive production version.
2. Analyze source mix and aligned stems: loudness/peaks, clipping, spectrum, masking, transients, stereo correlation and balance, quiet sections, separation artifact suspects, and optional timeline/section segmentation. Preserve raw measurements and confidence/provenance. No model-based inference should masquerade as a direct measurement.
3. Present ranked **opportunities**, each scoped to song/stem/region and explained: diagnosis, evidence, expected audible outcome, estimated benefit/confidence, potential tradeoff, suggested processing change, and undo.
4. Stage one candidate in a preview processing graph. A/B at loudness-matched level with fast, glitch-controlled switching, equal starting position and bypass, synchronized playback and no modification to originals. Preview/export processing parity is a release gate.
5. Ask user **Better / Worse / Reroll** (optionally neutral/skip, annotation). Better accepts a versioned change; Worse discards; Reroll creates a distinctly parameterized alternative but retains experiment lineage. Permit manual adjustment at every step.
6. Record experiment context and feedback locally, refine personal/profile-dependent ranking cautiously. User can see, export, undo or clear learning history. No cloud data transfer or model training by default.
7. Export named masters with complete parameter, tool, engine, and media provenance.

## Album-specific creative profile, not a global rule
*Voices Below the Deck* uses **human/organic sounds biased left**, **impersonal/mechanical sounds biased right**, with purposeful transitions across the field. Lead vocal/kick/snare/bass retain center support where needed; environmental/orchestral material is generally wider. Recommend balance and mono-compatibility checks rather than rigid hard-panning. Store optional semantic tags (human, mechanical, orchestral, ambient, synthetic, organic) to guide recommendations and automation. Profile should be transferable/customizable for other music, independent of Infra Choir branding in product UI.

## Candidate analysis families
- Technical: clipping, true/sample peaks, integrated/short-term loudness, crest/transient metrics, excessive silence, phase/stereo correlation, mono fold-down and source/stem duration/alignment.
- Mix hypotheses: mask-prone overlapping energy, vocal intelligibility risk, low-frequency competition, harshness bands, overcompression, uneven stereo field, separation artifacts.
- Context: regions, section changes, drum hits, vocal-active segments and possible moments for widening, delays or industrial accents.
- Confidence/calibration: ranked recommendations represent uncertain expected value, not guaranteed improvements; distinguish heuristics from verified detectors.

## Separation expansion
Existing six stems remain default: Vocals, Drums, Bass, Guitar, Piano, Other. Optional second-pass male/female voice isolation and additional instrument subdivision are desirable but **not immediate requirements**. Verify overlap, harmonies and duet leakage; voice labels may require user correction and must not be presented as ground truth. Additional orchestral subdivision is lower priority for this particular album. Always retain parent stems and alignment metadata.

## Effects and composition
Initial DSP: gain, pan, EQ, compression, saturation, limiter/bypass and true monitoring/export parity. Follow with stereo metering, effect buses, parallel drum treatment, reverb/delay, automation and spatial motion. Preserve clean orchestration, intelligible vocals and punchy drums with optionally blended industrial coloration. Later allow supplementary aligned sound-design tracks (subtle machine rhythms, metallic sounds, glitch/interference) and eventually melodic/MIDI parts. These later features must not delay near-term publishing.

## Architecture proposal (subject to implementation spike)
Persist separate immutable source/stem/analysis artifacts, a versioned **processing graph** with deterministic plugin IDs, parameter values, routing and automation, and an append-only experiment log. The log records song version, source/stem identity, chosen region, diagnosis and evidence, candidate parameters, rendered preview IDs, loudness normalization, A/B response, rerolls and selected outcome. Keep raw subjective feedback separate from inferred preference models. Cache previews by input hashes + engine/version + graph parameters; never write changes into source files. Ensure all references survive reopen and can be relinked or recovered.

## Suggested delivery gates
1. **Foundations / dogfood:** Persistent processing graph and versions; per-stem gain/pan/basic EQ; aligned playback/render; fast level-matched A/B, bypass, Better/Worse/Reroll and append-only experiment log. Verify original hashes unchanged, history round-trip, undo and preview/export parity.
2. **Analyzer v1:** Reliable measurements, evidence-linked prioritized opportunities, explainable conservative proposed parameters and no-change recommendations; user-controlled trial and rating.
3. **Mix craft:** Compression/saturation, per-stem buses and parallel drums, stereo/mono checks, effect presets and automation, vocal clarity workflow.
4. **Learning:** Locally rank recommendations based on repeated contextual feedback, with privacy controls, understandable preference memory, and comparison to no-learning baseline. Avoid inferring causal effects from compound changes.
5. **Advanced editing:** Optional voice subdivision, further instrument separation, aligned layers, transient/region surgery and creative machine sounds.

## Open validation questions
- DSP engine and low-latency preview architecture with deterministic offline export and delay compensation.
- What reliably counts as an A/B audible improvement: matched loudness, switch/crossfade latency, repeat loops, blind-option mode, normalization boundaries?
- Which measurable detectors yield genuinely useful, low-false-positive suggestions on AI-generated music?
- How should song-level, album-profile and user-level taste models be separated and reset?
- Which manual Waveform/Audacity processes in the first two album tracks provide the highest value for implementation?

## Section annotation contract (2026-10-19 implementation increment)
User can manually mark in/out points on the transport and label a non-overlapping audio range with a section type and optional number. Backend persists typed sections in the existing song manifest through `PUT /api/projects/{ident}/sections`. The display notation is inspired by timed YuE2-style sections, e.g. `[Chorus 1:15-1:45]` or `[Verse 2 0:10.25-0:35.5]`, but stored canonical timestamps are numeric seconds and section IDs. Parsing engine-specific staging is deliberately not part of the canonical annotation. Boundary validations reject overlap, non-finite ranges and out-of-duration sections. No editing of media.

**Important status:** Markers are metadata only today, not a waveform selection or procedural effect automation engine. Next increment is synchronized, near-instant loudness-matched A/B and per-stem pan/EQ with persistent processing graph, then section-scoped recommendation and automation. Map section kinds to engine-specific YuE2/ACE prompt formats through adapters, never reuse their divergent stage-direction syntax indiscriminately. The current browser six-element playback is not guaranteed sample-accurate; do not promise click-free A/B or preview/export DSP parity until an audio engine spike proves it.


## Timeline-first section editing update (2026-10-19)
User prefers a YouTube-like timeline: section blocks visible in sync with audio, draggable horizontally, and resizable from either edge rather than typing times. First implementation updates `SectionEditor.tsx` with horizontally positioned blocks, move/resize pointer handles, numeric timestamp display, playback cursor, and 0.1-second keyboard nudging. Boundaries are constrained against neighboring sections and song duration, and validated through the existing backend. Section text notation remains a derived representation, not the editing control.

**Still needed:** integrated, zoomable multi-stem waveform graph (today this is an aligned section lane, not waveform rendering), visual region creation by dragging empty timeline space, snapping to detected transients/beats/section changes, accurate zoom-scale drag math, undo history, and accessibility/Windows pointer QA. The current first-pass lane should not be described as a full waveform editor. Explore shared `TWS-UI` timeline component rather than indefinitely embedding bespoke controls.
