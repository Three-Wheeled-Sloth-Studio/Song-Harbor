---
type: Architecture Overview
title: Song Harbor Architecture Direction
description: Proposed boundaries and data ownership, subject to technical spikes.
status: draft
tags: [architecture, local-first]
---
# Architecture Direction

**Architecture principle:** The application owns composition and project state. Models operate on bounded jobs and return assets or suggestions, never authoritative replacements for the project itself.

## Layers (proposed)

1. Desktop UI: timeline, section editor, track/stem mixer, prompt/score editor, asset manager, model settings.
2. Composition/project engine: a versioned model-neutral **Music Arrangement Graph (MAG)** working concept. Song metadata, tempo map, musical clock (bar/beat/ticks/sample positions), section regions, track assignments, notes/score, lyrics, instructions, effects routing, assets, confidence and provenance.
3. Task orchestrator: dependency-aware jobs, capability-aware model selection, caching, GPU lifecycle, memory budgets, cancellation, results and validation.
4. Model and analysis adapters: generation, repaint, cover, separation, transcription, style/chord/BPM inference, mastering.
5. Native audio processing: playback, alignment, fades, mixing, plugins, rendering, stem export.
6. Compute providers: local GPU/CPU now; optional remote/cloud workers later via common job contract.

## Distinctions to preserve

- **True native generated stem:** generated for a dedicated track context.
- **Separated stem:** estimated isolation from a mix, with possible bleed/artifacts.
- **Symbolic track:** MIDI/ABC/note sequences; distinct from rendered audio.
- **Imported recording:** retains original media and rights/provenance metadata.
- **Hard constraint:** deterministic edit or verifiable requirement.
- **Soft instruction:** generative guidance, not guaranteed by the engine.
- **Inferred fact:** analysis output with confidence, not an original score claim.

## Candidate implementation stack, not decided

Tauri 2 desktop shell, React/TypeScript frontend, Rust orchestration, native Rust/C++ audio components, SQLite project index, versioned JSON manifests, FLAC/WAV assets, external managed model workers and optional MCP/local API. Evaluate YuE2 Studio and ACE-Step as adapters or reusable components; investigate licenses, APIs, adapter/LoRA support and runtime behavior before commitment.

## Runtime constraints

One large generator loaded at a time on base hardware if required, disk caching, quantization/offloading where supported, responsive UI and playback, clean worker lifecycle, job persistence, controlled network permissions. Core workflow remains local. Avoid bundling huge model weights in the installer unless justified.

## Integration contracts to define

Model capability manifest; job submit/progress/cancel/result; asset and waveform provenance; model+adapter compatibility; memory estimate and hardware policy; score/audio context and duration alignment; non-destructive clip replacement; audio effect plugin hosting; and optional remote execution provider.

## Architecture decisions still open

See `refs/planning/openQuestions.yaml`. MAG is a working design label, not an approved file format or audio codec.
