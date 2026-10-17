---
type: Technical Discovery
title: Stem Separation Engine Discovery
description: Candidate engines, licensing gates, benchmark plan and first deliverable scope.
status: draft
tags: [discovery, audio, separation, licensing]
---
# Stem Separation Engine Discovery

Date: 2026-10-17. Candidate findings derive from upstream repository README and package metadata; this is **not** a completed model license audit or a measured hardware benchmark.

## Decision and placement

Per SH-DEC-010, build the **Stem Separation Workbench** as priority-zero functional deliverable before the generation workbench. The overall initial Song Harbor production release is still generation-first: mixed-track reconstruction and guided covers/remixes are later. Stem separation is a self-contained production utility, **not** equivalent to full reconstruction.

## Initial functional scope (proposed)

- Import WAV/FLAC/MP3 and common codecs supported by bundled/installed decoder.
- 2-stem vocals/instrumental and 4-stem vocals/drums/bass/other presets.
- Model chooser with source, license, hardware estimates and 2/4-stem output capabilities.
- GPU execution with CPU fallback if engine supports it; bounded chunks and resource controls targeted at 12 GB VRAM / 96 GB system RAM.
- Batch job queue, progress, cancellation, retry and explicit errors.
- Lossless aligned stem export (WAV and/or FLAC); original file unchanged; manifests include model and weight hashes, parameters, output paths and processing timings.
- A/B input/reference listening plus individual stem mute/solo and simple mix; no full DAW.
- Local/offline processing once model weights installed. Clearly separate model download from inference.
- Never represent inferred separated stems as native generated stems. No automated sample or arrangement inference required for this deliverable.
- Optional candidate follow-up: specialty drums, guitar, piano, de-reverb, bleed suppression, models ensembles and export profiles.

## Repositories surveyed

| Candidate | Upstream | Code license | Position | Critical caveats |
| --- | --- | --- | --- | --- |
| python-audio-separator | https://github.com/nomadkaraoke/python-audio-separator | MIT per upstream README | **Preferred integration wrapper to prototype first** | Has CLI and Python API supporting Demucs, MDX-Net, VR, MDXC; individual pretrained model rights need per-weight review; dependency, Windows CUDA and load time need testing |
| Demucs | https://github.com/facebookresearch/demucs | MIT per upstream README | Reference benchmark and optional adapter | Official repo archived; 4/6-stem variants; individual pretrained checkpoint/data rights must be reviewed |
| Ultimate Vocal Remover | https://github.com/Anjok07/ultimatevocalremovergui | MIT per upstream README | Model ecosystem / comparison | GUI is not desired embedded shell; checkpoint rights/credit and maintenance vary |
| MSST | https://github.com/ZFTurbo/Music-Source-Separation-Training | MIT per pyproject | Advanced experimentation/training & optional model backend | Large architecture/dependency surface; model-specific metadata/license checks and GPU measurements needed |
| Spleeter | https://github.com/deezer/spleeter | MIT code per README | Simpler 2/4/5-source benchmark | TensorFlow dependency path, artifacts, weight terms and Windows packaging to test |
| Open-Unmix | https://github.com/sigsep/open-unmix-pytorch | MIT code per README | Reference comparison | Default umxl pretrained weight license is CC BY-NC-SA 4.0; NOT safe to assume commercial redistribution or use |

## Licensing gate

For each **specific** shipping checkpoint inspect and record: source URL, maintainer, explicit license evidence, redistribution terms, commercial-use permission, attribution requirements, dataset-origin caveats, dependencies (including FFmpeg packaging), provenance and file hash. A code license is not proof of model-weight rights. Treat unknown weights as **not yet cleared for commercial bundling**. User-provided recordings likewise retain their original copyrights; the application should not implicitly license input media. Favor user-downloadable models with clear metadata, but note that downloading separately does not eliminate license obligations.

## Benchmark bakeoff

On RTX 4070 12 GB / 96 GB:
1. **S-01 baseline**: select two explicitly licensable models, one 2-stem and one 4-stem, and a small source fixture whose isolated reference stems are available with rights.
2. **S-02 sound**: blind-listen for vocal bleed, drum transients, bass preservation, cymbal swish, reverb, stereo positioning and source mix reconstruction.
3. **S-03 resources**: repeat cold/warm separation with representative 30-second and full-song fixtures; measure wall-clock, peak GPU memory, RAM, output size and recoverability on out-of-memory.
4. **S-04 integrity**: sample count and time alignment match source, no unwanted fades, source unchanged, sum stems vs reference tolerance reported; export WAV/FLAC without unexpected resampling.
5. **S-05 functionality**: exercise CLI/library backend, progress/cancel/failure, batch, model cache location and offline run after download.
6. **S-06 packaging**: Windows isolated subprocess, CUDA/PyTorch dependencies, model installation and clean-machine smoke tests.
7. **S-07 comparison**: include Demucs and MSST/RoFormer candidates if legal and resource viable; avoid benchmark expansion before first utility works.

Record engine/code SHA, checkpoint SHA, license decision, input SHA, parameters, output paths, samples/quality notes, VRAM and RAM measurements.

## Recommended implementation

- **First spike**: local CLI worker using python-audio-separator, with one verified-license 2-stem checkpoint. Add a known 4-stem option, plus Demucs comparison.
- **UI**: extremely lightweight local utility with file import, model/preset dropdown, progress, separated-audio audition, and batch WAV/FLAC export. Use the shared Song Harbor worker/job contract (planned) so it can be reused in the production application.
- **Scope limit**: no lyrics, score extraction, remix or full project reconstruction until generation workflow is operational.
- **Gate**: separations run offline on reference system; alignment and export validation pass; at least one viable 4-stem mode; no bundled weights without legal review.

## Sources

- https://github.com/nomadkaraoke/python-audio-separator
- https://github.com/facebookresearch/demucs
- https://github.com/Anjok07/ultimatevocalremovergui
- https://github.com/ZFTurbo/Music-Source-Separation-Training
- https://github.com/deezer/spleeter
- https://github.com/sigsep/open-unmix-pytorch
