# Dev program: Full reinstrumentation and aggressive vocal restoration
Date: 2026-11-03
Branch: dev only. main is release-stable at 957cef0.
Status: Planning baseline, no implementation claimed.

## Goals and boundaries
1. Rebuild all instrumental parts of next track with editable MIDI and high-quality sample/synth instruments. Do not reinstrument vocals.
2. Test aggressive vocal artifact cleanup while preserving identity, phrasing, timing, breaths, dynamics and intentional rasp/distortion.
3. Preserve originals and authored section automation. Every experiment has A/B, explicit acceptance, undo and live/export parity.
4. Do not apply aggressive edits to the previous locked release mix, and do not change main until proven.
5. Work from actual stems and mix; no assumption that "Other" is a single instrument or that polyphonic guitar/drums are recoverable perfectly.

## Baseline already in repo (verified source/docs, not newly QA'd)
- Generic stem selection to MIDI and region choices; current heuristic extraction predominantly mono/limited polyphony. Editable note list, synthetic voices, GeneralUser GS 2.0.3 SF2 starter, SF2 registry, FluidSynth integration and settings path.
- Sampled instrument libraries via SF2 supported. SFZ, VST3/CLAP not yet supported. No full piano-roll UI or robust drum/polyphonic transcriber.
- Non-destructive generated stems and adjustable Original level, replacement masks, script gain and sync export; Windows end-to-end QA not uniformly completed.
- Sound Cleanup correction comparison and finding/repair scaffolding exists. Deshimmer bridge remains unimplemented; integration plan: docs/deshimmer-song-harbor-integration-plan-2026-11-03.md.

## Workstream A: instrumental transcription and instrument rendering
A0 Inventory and baseline (first)
- Freeze original input/stem hashes and section markers, sample rate, tempos if known; define one reference passage per family: bass, drums, chordal guitar/piano, mixed orchestral/Other. Make release-independent test project in dev.
- Validate existing SF2 import and FluidSynth sample output, candidate acceptance/reopen and export parity on Windows before layering capabilities.
- Create track roles and articulation-map metadata; allow many new instruments per original stem, and one MIDI part to map to several instruments.

A1 MIDI asset model + editor (highest reusable leverage)
- Persist editable MIDI note events with stable IDs, start/end sample or tick mapping to master clock, pitch, velocity, channel, source-region/provenance, confidence and transcription model version; preserve PPQ/tempo map on import/export.
- Large resizable piano roll aligned to existing waveform/section timeline; drag/create/resize/multi-select/copy/paste/delete, pitch, velocity lane, keyboard shortcuts, snapping toggle and adjustable grid, zoom/scroll, playhead follow, preview, reversible undo/redo.
- Display extracted note confidence and source spectrogram/waveform overlay. Never quantize by default; provide non-destructive quantize/humanize with adjustable strength and independent timing/velocity.
- Add multi-region audition and versioned candidate notes to prevent losing work when instrument render changes.

A2 Transcription strategies
- Bass/lead: improve onset+pitch tracking; notes and bends/legato; detect octave errors and harmonics. Annotate confidence; support manual correction.
- Chordal piano/guitar: benchmark at least two plausible polyphonic transcription models against manually labelled excerpts. Detect and expose ambiguous chords; avoid promising perfect separation. Decode in CPU/GPU bounded jobs and document VRAM.
- Drums: transient-to-class lanes (kick/snare/toms/hats/cymbals/taiko), separate overlapping hits, editable drum grid, MIDI note maps, ghost notes, velocity and swing. Preserve original time feel.
- Other: first sub-separate if sources are distinguishable; if not, use manual arrangement and ACE accompaniment rather than pretending single-stem MIDI is accurate.
- Always maintain source audio + editable candidate together; allow selective replacement of only credible notes/regions.

A3 Instrument sampler and packs
- First QA existing GeneralUser GS SF2 and FluidSynth as fallback. Build isolated SFZ rendering adapter rather than mistaking SFZ for SF2. Explicit discovery/version check, path validation, offline deterministic render, cancellation and timeout.
- Initial bank shortlist: VSCO 2 Community (strings/brass/winds); Karoryfer x Bigcat Cello (bowed/staccato/pizz); SFZ Instruments drum kits (review each license/size); GeneralUser GS (broad compatibility). Explore curated Pianobook/Decent Sampler later, not universal plugin hosting yet.
- Support articulation/switch keys, sustain/CC1/CC11/CC64, velocity layers/round robins when supported, per-note expression/automation mapping, drum naming and preview in context.
- License gate: personal compositional use vs distribution/bundling. No automatic resale/redistribution or downloading unchecked assets; local import first and optional reviewed download.
- Project portability: store asset provenance, content hash and renderer version; accepted WAV must play even if sample pack becomes unavailable; warn on rerender.

A4 Full arrangement and acceptance
- Introduce grouped instrumental layers per source: candidate render, offset, instrument and original-source dial, region mask and section script still work.
- Per-instrument gain/pan/EQ/rack routed through current mixer; do not duplicate the automation engine.
- Preserve phrase dynamics rather than replacing everything at once. Keep build-up, ornaments, rests, timing and space against original vocals; review in instrument-family passes.
- Export every accepted layer with exact timeline and consistent latency/sample count. Store reversible edits and compare with original at matched loudness.

## Workstream B: vocal restoration
B0 Ground truth
- Save vocal stem, original full mix, stem-separation version and hashes; identify lyric/sibilant/breath/harshness passages, lead vs backing bleed, sustained notes, and intentional distortion. Distinguish separation contamination from original-generation artifacts.
- Baseline metrics: aligned RMS/LUFS, true peak, time-frequency residual, transient loss, stereo/phase, formant/pitch movement, consonant preservation; metrics are aids, not automatic quality labels.

B1 Deshimmer integration
- Implement scoped isolated Python process per existing integration plan: capability handshake, complete params, version/input hashes, async job/status/cancel, bounded resources and output validation. First pass on whole vocal stem then short passages; never autoplay.
- Clearly separate restoration (shimmer/denoise/deresonance) from tonal/color enhancement. Default to controlled settings, not blindly optimize the approved full-mix recipe for a vocal stem.
- Candidate modes Original / Current / Fix / Removed by repair / Total difference, level matched and aligned; no source mutation. Verify 24-bit accepted WAV matches audition and export.

B2 Iterative restoration experiment matrix
- Baselines: raw vocal, separation model variants if needed, mild Deshimmer, stronger Deshimmer, targeted sibilance/de-essing, resonance suppression, transient/formant preservation. Change one class at a time.
- Work in localized slices; protect sibilants, consonant starts, natural breath, vibrato and intended rasp, while focusing on metallic warble, watery high-frequency shimmer, cyclic resonance and bleed.
- Test lead/backing separation (e.g., alternative separation model) only when evidence shows bleed; preserve original timing and phase. Don't blend unaligned remixed sources.
- Save recipe + diff + metrics and score with listening notes. Reject aggressive cleanup that improves synthetic detection proxies but destroys musical content.
- If artifacts are unrecoverable, permit local re-synthesis/reperformance as separate, explicitly labelled experiment; no covert replacing vocal identity.

B3 Final vocal gate
- In-context level-matched A/B with rebuilt instruments, solo vocal listening, word-by-word intelligibility, phrase transitions, fades/tails; automation and export parity. Author must explicitly approve.

## Sequencing and milestones
S0 (foundation): test/dev data fixture, release branch guard, actual Windows QA of existing SF2/FluidSynth, split out vocal reference passages.
S1 (parallel): piano roll V1 + persistent MIDI assets; Deshimmer bridge whole-stem prototype.
S2: polyphonic and drum extraction tests; SFZ sampler and 2-3 high-quality packs; localized vocal candidate flow.
S3: expressions/articulations, instrument group management and complete first instrumental replacement; detailed vocal A/B and preservation.
S4: full-song re-instrumented + cleaned mix; save/reopen/export parity, performance regression, documentation, promote selectively to main only after release QA.

## QA gates / definition of done
- Test coverage: parser/backend model validation, MIDI round-trip and source timing, drum note mapping, sampler mock + real render, candidate replacement masks, versioned note edits, cancellation, stale jobs, cleanup reversibility, audio alignment.
- No unresolved clipping, unintended gain/tonal changes, source mutation, audio drift, missing notes from note editor, lost edits after reopen or unexpected preview autoplay.
- Original and new stems remain independently accessible; accepted WAV remains loadable with original sample pack uninstalled.
- Local CI unit tests plus `pwsh -File scripts/verify-artifact-suite.ps1`, `cd app/frontend && npm run build`, portable Windows startup and direct music audition.
- User approves instrument articulation / phrase feeling and vocal sound, not just a numeric metric.

## Out of scope for this development program
- New universal VST host, commercial instrument marketplace, cloud rendering, auto-humanizing everything, AI watermark removal, or optimizing AI-origin classifier scores.
- Automatic blanket conversion of every stem without human correction, or full song acceptance solely by automated metrics.

## Research sources (verify pack license and engine compatibility at download)
- https://versilian-studios.com/vsco-community/
- https://shop.karoryfer.com/pages/free-karoryfer-x-bigcat-cello
- https://sfzinstruments.github.io/drums/
- https://www.pianobook.co.uk/terms-conditions/
- https://github.com/mrbumpy409/GeneralUser-GS
- docs/instrument-pack-library.md
- docs/bass-midi-reinstrumentation-2026-10-29.md
- docs/deshimmer-song-harbor-integration-plan-2026-11-03.md
