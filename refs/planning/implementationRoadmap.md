---
type: Implementation Roadmap
title: Song Harbor Phased Implementation Roadmap
description: Dependency-driven delivery plan, experiments, exit gates, milestones and provisional MVP boundary.
status: draft
tags: [roadmap, discovery, implementation, music-production]
---
# Song Harbor Implementation Roadmap

Last updated: 2026-10-17. **Generation-first sequencing is accepted (SH-DEC-009).** Exact implementation stack, acceptance thresholds and schedule remain proposed/unvalidated. `refs/planning/roadmap.yaml` is the structured roadmap; this document explains stage rationale, discovery and gates. Product constraints are authoritative in `refs/product/requirements.md` and accepted decisions in `refs/planning/decisions.yaml`.

## Delivery strategy

Build vertical slices that produce testable musical outputs, not a collection of disconnected model demos. Test difficult integration and preservation constraints early; maintain a desktop shell from the start. Default development target: Windows on RTX 4070 12 GB VRAM, 96 GB RAM, with user-selectable lower/higher capability profiles planned. Never interpret proposed performance or model support as proven.

**Priority-zero deliverable (SH-RM-005):** Local stem separator before the generation workbench. This is a self-contained utility, not full imported-track reconstruction. See [Stem Separation Discovery](stemSeparationDiscovery.md).

Use six delivery milestones:
- **M0 First Stems (stage 0.5):** 2/4-stem local separation, preview, batch and aligned export on reference hardware.
- **M1 First Sound (stages 0-3):** at least one viable local generation engine, interchangeable adapter architecture, auditable jobs, preview, export, saved/reopened native project; a second engine is targeted subject to feasibility.
- **M2 First Arrangement (stages 4-5):** sections, independently addressable generated/imported tracks, synchronized audition, basic mixer and track export.
- **M3 First Surgery (stage 6):** bounded region/stem revisions, alternate takes, preservation locks and safe transitions.
- **M4 First Release (stage 9):** a standalone offline **generation-first** Windows application; does not require full mixed-track reconstruction, cover, or remix workflows.
- **M5 Reconstruction and Remix (stages 7-8):** import existing tracks, reconstruct editable musical structure, create guided covers/remixes on the established project and generation pipeline.
- **M6 Open Studio (stage 10):** advanced model/adapters training, remote providers and extensions.

**Accepted sequencing:** A functional native generation and revision workflow precedes full import-and-remix product development. Early import/separation analysis may be used for feasibility research but must not block the generation-first release.

**Implementation order:** 0 -> 0.5 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 9 -> 7 -> 8 -> 10. Stage IDs retain their historical identifiers for stable references; numbering is not implementation order after this decision.

The stage IDs below match the structured roadmap. Phases can overlap after interface contracts stabilize.

## Stage 0: Harness, baseline and evidence strategy (SH-RM-000)

**Build:** Finish full Agent Academy `refs/` harness, deterministic indexes and initialized validation. Define experiment manifests (inputs, model version, adapter weights, prompts, hardware, timings, peak VRAM/RAM, outputs, quality notes) and a reproducible fixture pack. Decide non-copyrighted or fully authorized benchmark assets. Establish smoke-test and hardware telemetry scripts.

**Discovery:** Source licenses and distribution restrictions for model code, weights, transcription/separation checkpoints and VST hosting. Distinguish community anecdotes from documented capability and measured capability. Inspect YuE2 Studio, ACE-Step and local music workflows for reusable interfaces.

**Exit gate:** initialized Agent Academy validation passes; test assets are legally usable; experiment protocol and reproducibility criteria recorded; key unknowns owned.

**Avoid:** implementation-stack commitments based only on attractive demos; storing licensed or private music in git.

## Stage 0.5: Stem Separation Workbench (SH-RM-005)

**Build:** standalone-compatible local 2-stem and 4-stem separation; batch queue, model selection, progress, solo/mute preview, aligned lossless WAV/FLAC export, source preservation and output provenance. Use a replaceable local inference worker that can later plug into Song Harbor.

**Discovery:** First test python-audio-separator, including model-weight rights, Windows CUDA, 12 GB VRAM, CPU fallback and 30-second/full-track fixtures. Compare Demucs and MSST if warranted. See `refs/planning/stemSeparationDiscovery.md`.

**Exit gate (M0):** local offline inference once weights are installed, 2/4-stem output, aligned lossless exports, batch and audition, repeatable measurements, and reviewed checkpoint rights before any distribution.

**Scope boundary:** Separation is not native independent stem generation or reconstruction of song instructions. Defer full reconstruction/remix to M5 and continue generation-first afterward.

## Stage 1: Technical feasibility bakeoff (SH-RM-010)

**Experiment A - Full song:** generate at least three seeds per engine from a common style+lyrics+score case; record adherence, duration and resource usage.
**Experiment B - Section surgery:** try replacing 8-16 bars while retaining neighboring material; measure timing drift, audible joins and unintended changes.
**Experiment C - Stems:** independently generate or condition drums, horns, and vocals; compare with separator-derived tracks, record bleed, edit control and alignment.
**Experiment D - Cross-model handoff:** pass common score/MIDI/ABC or audio conditioning between engines; document which fields survive and which are approximate.
**Experiment E - Adaptation:** inventory LoRA/LoKr compatibility, weighted combinations, loading cost and model-specific constraints.
**Experiment F - Reverse ingestion (optional, bounded):** sample tempo/key/sections, transcription and separation only to expose likely format/schema requirements. Defer systematic reconstruction benchmarks until native generation and selective revision work.

**Exit gate:** signed-off capability registry with observed/support classifications; at least one viable 12 GB offline end-to-end generation path; explicit go/no-go/fallback choices for surgery and true stem generation. Failed experiments are acceptable evidence; do not conceal missing capability.

**Fallbacks:** import or separate stems when genuine stem generation fails; use score-guided symbolic production where audio generation cannot follow timing; postpone unsupported operations rather than fabricate feature support.

## Stage 2: Desktop shell and model workbench (SH-RM-020)

**Build:** minimal standalone Windows desktop shell, model discovery/registry, standardized job contract and progress/cancel, one-worker-at-a-time GPU scheduling, disk cache, generation input pane, waveform preview, model comparison, output export, job logs. Initially connect two engines only where supported by benchmarks.

**Discovery:** test process isolation, Python model worker packaging, worker crashes, cold/warm load time, model download locations, CPU offload/quantization, and UI responsiveness. Choose desktop and audio stack after small proof-of-concept; Tauri/React/Rust remain proposals.

**Exit gate (M1 part): can choose compatible engines, generate, audition, export, interrupt/restart jobs and run disconnected once dependencies are installed. Record performance rather than setting speculative latency promises.

## Stage 3: Native project representation (SH-RM-030)

**Build:** versioned model-neutral project schema (MAG working title), unique song/section/track/clip IDs, tempo and meter maps, musical and sample clocks, score/lyrics and media references, approved-region locks, immutable render assets, provenance, undo/redo and migration tests. Persist and reopen all work from M1.

**Discovery:** short schema spike using complex polyrhythmic material, variable tempo, multiple vocal parts and ambiguous source separation. Compare structured JSON+SQLite vs alternative stores. Decide authoritative score vs analysis inference and soft vs hard constraints.

**Exit gate (M1 complete):** project round-trip maintains exact audio references, track IDs, timings and history; version change and crash recovery tests pass. No engine-native format becomes authoritative.

## Stage 4: Composition and arrangement workbench (SH-RM-040)

**Build:** arrangement timeline, section add/split/reorder, per-section track direction, scoped text/score instructions, voice and instrument identities, bar/beat selection, transition and fade controls. Implement deterministic fades and edits independently of AI.

**Discovery:** controlled tests of engine-specific prompt compilation: YuE2 plain lyrics tags plus song-level styling/score control versus ACE section direction where supported. Explore score generation using ABC/MIDI and editing ergonomics.

**Exit gate:** author a multi-section piece with different male/female vocal assignments, boom-bap drums and go-go horns; demonstrate preserved IDs and repeatable transition instructions.

## Stage 5: Stem production, separation and mixer (SH-RM-050)

**Build:** stem-directed native generated tracks, imported reference tracks, symbolic tracks, region-level mute/solo/level/pan, synchronized playback, stem rendering/export, routing and basic effects. Keep separated-stem origin metadata in the schema, but defer complete mixed-track reconstruction tooling until M5. Capability labels must disclose which stems are inferred versus generated independently.

**Discovery:** latency/drift for long stems, loudness/phase behavior, onset alignment, resampling, plugin-host feasibility, native stem generation fidelity and compatible local synthesis/rendering methods. Separation quality can receive a bounded research check. Limit heavyweight DAW authoring.

**Exit gate (M2 complete):** at least one song with four independently addressable tracks; independently replace or mute any one; synchronized playback and exports with documented artifacts/tolerances.

## Stage 6: Second Take - selective regeneration (SH-RM-060)

**Build:** selected region and stem target, preserve locks, contextual generation, multiple candidates, A/B audition, apply/revert, boundaries/crossfades, optional reference audio, provenance and model routing. A deterministic edit remains possible if AI candidates fail.

**Discovery:** neighboring-context size, source contamination, phrase seams, beat/frame drift, vocal identity consistency, candidate selection and quality rubric. Compare native repaint, score-conditioned replacement and segmented renders.

**Exit gate:** replace one verse vocal without modifying protected stems/regions; timeline alignment stays within an agreed measured tolerance and the result can be undone. If no reliable isolated generation, expose safe fallback explicitly rather than claiming it.

## Stage 7: Import and reconstruction (SH-RM-070)

**Build:** ingest audio and stems, detect tempo/key/sections, optional lyric transcription, chord/melody/ABC/MIDI inference, style and instrument descriptors, separation and reconstruction into editable Song Harbor tracks. Surface uncertainty and keep original assets.

**Discovery:** precision/recall of detected boundaries, BPM half/double errors, chord ambiguities, speech/music transcription, symbolic transcription quality, tool licenses and inference speed on 12 GB. Evaluate multi-pass analysis without VRAM contention.

**Exit gate (M5 part):** reconstruct a useful draft from a mixed song and perform one non-destructive revision. Inferences remain labeled; no promise of perfect source-project recovery.

## Stage 8: Covers and remixes (SH-RM-080)

**Build:** preserve/change matrix for lyrics, melody, harmony, rhythm, voice, instrumentation and production style; guided cover/remix workflows; copyright/permissions metadata and user-facing provenance; before/after comparisons.

**Discovery:** test which control combinations preserve requested musical content per engine, duration/structure constraints, vocal conditioning, and cover/remix licensing obligations. Verify supported workflows on owned/licensed material.

**Exit gate (M5 complete):** controlled transformation of authorized source material with explicit differences and preserved elements; clear limitations when model cannot honor a hard requirement.

## Stage 9: Standalone generation-first MVP hardening (SH-RM-090)

**Sequencing:** Implement this stage immediately after Second Take (stage 6), before full reconstruction/remix (stages 7-8).

**Build:** reliable installer/update strategy, external model-weight manager, offline first-run and dependency checks, security boundaries, license notices, project migration, backup/recovery, accessibility, audio device behavior, export profiles, help and troubleshooting. Prefer Windows first.

**Discovery:** test clean installs on non-developer machines, hardware below/above reference, driver mismatch, antivirus interference, disk/VRAM pressure, corrupted projects, and model-download interruptions.

**Exit gate (M4 complete):** fresh user installs without development tooling, works offline after setup, generates/arranges/selectively revises/mixes/exports native projects within documented model limitations, and recovers reliably from failed jobs. Full song reconstruction and guided covers/remixes are not requirements for this release. The scope of M4 is proposed and may be adjusted after feasibility results.

## Stage 10: Open Studio and advanced extensions (SH-RM-100)

**Build later:** LoRA/LoKr training UI with dataset governance, third-party model and effects SDKs, optional cloud/provider job execution, remote workers, advanced mastering and collaboration if validated by users. Core adapter/compute interfaces should anticipate these without MVP implementation.

**Discovery:** GPU/training cost, licensing and weight redistribution, provider privacy/cost models, compatibility tests, extension sandboxing, plugin review and maintenance costs.

**Exit gate (M6):** each optional subsystem is bounded and replaceable, without undermining offline core features.

## Cross-cutting discovery and engineering gates

1. **Performance:** peak GPU/RAM, execution time, cold/warm starts and playback responsiveness tracked per workflow on reference hardware; step-down/up matrix published after measurement.
2. **Preservation:** protected tracks/regions checked by deterministic asset hashes and render diff where possible; audible quality judged separately.
3. **Reproducibility:** model versions, seeds, conditioning, inputs and adapter manifest stored; probabilistic output is not guaranteed bit-for-bit repeatable.
4. **Licensing and safety:** model weight and code distribution, third-party plugin licenses, user input/cover rights, and source provenance reviewed before packaging; M5 remix/covers require separate rights review.
5. **Testing:** fast automated contract tests, fixture-based audio comparison, UI smoke tests and periodic human listening evaluations.
6. **Fallbacks:** if a model cannot perform a promised action precisely, degrade to manual/symbolic editing or declare unsupported rather than regenerate unrelated content.

## Explicit scope boundaries and decisions pending

- No cloud service, accounts or model training required in the initial release.
- No commitment yet to Tauri, SQLite, Rust, React, an audio engine, project file extension or named module brands.
- Generation-first MVP scope is accepted; define measurable release acceptance thresholds, release licensing, minimum supported hardware and model distribution rules after technical spikes.
- Native-stem generation and exact section surgery are aspirational user capabilities requiring measured validation; imported and separated stems are practical fallbacks, not equivalent capabilities.
- Keep Song Harbor independent of Infra Choir's identity. Use authorized music from that workflow as optional test fixtures, not branding.

## Next actionable slice

Complete the Agent Academy validation path, then deliver M0 local stem separation with benchmarked engines. After M0, proceed with the generation model-adapter experiment. The experiment should produce a machine-readable capability report and audio examples, making architecture choices evidence-based.
