---
type: Test Protocol
title: Cross-Platform Stem Separation Benchmark
description: Track hardware environments, install capability, performance and quality across three or more systems.
status: draft
tags: [benchmark, hardware, audio, separation]
---
# Cross-Platform Stem Separation Benchmark

## Source of truth

- Machine inventory: [machineProfiles.yaml](../operations/machineProfiles.yaml)
- Engine candidates and licensing: [stemSeparationDiscovery.md](../planning/stemSeparationDiscovery.md)
- Each test run: a unique ID and an evidence record. Do not mistake environment readiness for a successful separation.

## Platform targets

| Platform ID | Current information | Status |
| --- | --- | --- |
| laptop-predator | GTX 1660 Ti 6 GB, NVIDIA driver 572.47, Windows PowerShell 7.6.7, Python 3.11/3.10/Anaconda, FFmpeg 4.2.3 | Python/Torch/ONNX/CUDA setup complete; separator environment probe passed, no audio inference yet |
| primary-desktop | RTX 4070 12 GB, 96 GB RAM reported previously | Direct baseline pending |
| platform-03 | Third device to be supplied | Pending |

## Recommended test ladder per platform

0. Inventory: OS, CPU, physical RAM, GPU, VRAM, driver, Python, FFmpeg, free disk, PyTorch GPU capability, idle VRAM and competing loads.
1. Environment: isolated virtual environment, package and dependency install versions, CUDA availability and model retrieval, no modifications to existing music/Comfy installs.
2. Smoke test: 20-30 s source, 2 stems. Record model ID/checkpoint/hash and output.
3. Four-stem test: exact same fixture, record alignment, runtime, artifacts and peak VRAM.
4. Full-song test: same source (authorized/owned), cold and warm runs; log input duration and elapsed time.
5. Quality: blind listening where possible, bass/transient quality, vocal bleed, phase/stereo; compare re-summed stems with source, document differences.
6. Degradation: try GPU and available CPU fallback; OOM handling and recommended chunk sizes; try reduced RAM/VRAM profiles.
7. Batch and export: multiple songs, WAV/FLAC, preserved sample count/rate, no source modification, cancellation/retry.

## Run record fields

- run_id, timestamp, machine_id, OS and GPU/driver, tool and version/commit
- Python, torch, CUDA-runtime build, CUDA available, optional FFmpeg path/version
- checkpoint name, source URL, explicit weight license status, model hash, separation mode and settings
- input filename or anonymous fixture ID, input SHA256, duration, sample rate/channels
- baseline VRAM; peak allocated/used VRAM; peak host RAM; elapsed seconds; real-time factor (elapsed / source duration)
- output stems, sample count and alignment, output format, reconstruction delta where measured
- perceived quality, bleed/artifacts, error traceback, success/failure and recommended fallback

## Comparison guardrails

Use identical authorized source fixtures and matching input sample rate and channel layout where supported. Do not compare absolute run times without noting shared GPU loads, power mode, thermal throttling, disk/cache state, and cold/warm status. Always distinguish observed results, expectations and unknowns. A passed smoke test does not imply commercially redistributable checkpoints.

## Current initial observation

Predator baseline at 2026-10-17 08:44:53: GTX 1660 Ti with 6144 MiB total VRAM and 830 MiB in use; NVIDIA-SMI 572.47, supported CUDA driver interface 12.8. PowerShell 7.6.7, Python launcher default 3.11, and FFmpeg 4.2.3 with GPL/version3 build options. System RAM observed 15.843 GiB. Isolated Python 3.11.2 virtual environment created on G:; torch 2.6.0+cu126 ran a 1024 x 1024 CUDA matrix multiplication on GTX 1660 Ti. audio-separator 0.47.0 installed; dependency resolver initially changed torch to CPU 2.14.1 and caused a torchaudio conflict. CUDA torch/vision/audio versions were restored with --no-deps. onnxruntime-gpu 1.24.4 installed; reported providers include TensorRT, CUDA and CPU. audio-separator --env_info successfully detected FFmpeg, Torch CUDA and ONNX CUDA. No model downloaded, no separation attempted, no latency or fidelity claims. Default model path displayed as /tmp/audio-separator-models/ and requires explicit G: configuration. Final pip check not provided.

## 2026-10-17 pause checkpoint

- **Predator:** environment passes CUDA compute and separator initialization, but no inference. On resumption, verify final `pip check`, check model storage CLI option, set `G:\Apps\SongHarbor\models`, clear checkpoint licensing, then perform 20-30-second first 2-stem smoke test.
- **Primary desktop:** user moving to reference RTX 4070 12 GB / 96 GB workstation. Start independently with `py -0p`, `nvidia-smi`, `ffmpeg -version`, physical RAM and free preferred-drive space. Do not carry Predator's Python paths or venv assumptions to another machine. Build isolated environment after inventory.
- **Third platform:** to be identified. Use same fixture/quality rubric when available.

## First completed audio smoke test (primary desktop, 2026-10-17)

- Run ID: `desktop-20261017-vr-2stem-001`.
- Source: locally produced `Raise the Neon Black`; 30 seconds starting at 0:30, stereo 48 kHz original 16-bit WAV, exported to 24-bit PCM test WAV (bit-depth conversion does not create fidelity).
- Engine: audio-separator 0.47.0, `1_HP-UVR.pth` VR vocals/instrumental checkpoint, torch 2.6.0+cu126; model integrity hash reported as `b5f988cd3e891dca7253bf5f0f3427c7`.
- Output: user confirms quick listening test sounds well separated; no objective artifact, reconstruction, timing, or stem-file count measurements yet.
- `Measure-Command` elapsed: **21.9218053 s** for 30 s input, ratio **0.7307x source duration**, approximately **1.37x real time** (includes startup/model loading).
- Unknown: captured GPU utilization/peak VRAM, whether logs confirm inference GPU placement, output sample count and exact stem alignment, repeatability, licensing of checkpoint weights. Do not treat a passing smoke test as proof of full production readiness.
- Next functional test: 4-stem vocals/drums/bass/other, then instrument-specific model capabilities; separating overlapping individual singers is a distinct source-separation/speaker task with variable feasibility.

## Four-stem smoke test (primary desktop, 2026-10-17)

- Run ID: `desktop-20261017-demucs-4stem-001`.
- Test input: same 30-second `source-30s.wav` sample as the two-stem run, originating from `Raise the Neon Black`.
- Engine: audio-separator 0.47.0, requested `htdemucs.yaml` (Demucs four-stem configuration), output format WAV.
- Elapsed reported by PowerShell `Measure-Command`: **10.1791727 seconds** (0.3393 × source duration; ≈ 2.95 × realtime processing speed).
- User listening result: **“Smoke test: pass.”** Full console logs, exact output file names/count, model checkpoint hash, actual GPU utilization, peak VRAM, alignment and artifact measurements have not yet been supplied independently; treat as user-confirmed smoke test, not comprehensive validation.
- Comparison to first 2-stem VR run (21.9218053 s): ≈ **2.15 ×** faster in observed wall time. Models differ and cold/warm model cache effects may be significant, so repeat controlled runs before inferring architectural speed advantage.
- Follow-up: inspect four output stems and filenames; measure sample rate, channel count, sample counts, stem alignment and quality; record checkpoint provenance/licensing; repeat both tests with matching cold/warm conditions.

## Four-stem output inspection (primary desktop)

User ran ffprobe on four `htdemucs` WAV outputs. Bass, Drums, Other and Vocals each report 48,000 Hz, 2 channels, and exactly 30.000000 s duration. This establishes format/duration parity; sample-level alignment and mix reconstruction accuracy are not yet measured.

## Four-stem reconstruction check (primary desktop)

- Python `soundfile` and `numpy` loaded original 30 s WAV and all four outputs. Each output shape was **(1,440,000, 2)**, matching 48 kHz stereo x 30 s.
- Original RMS: **0.15053791521019433**; sample-domain residual `original - sum(stems)` RMS: **0.004297088053176496**, or about **2.85%** of original RMS.
- Pearson sample correlation between original and summed stems: **0.9996214151357643**.
- These measurements support close waveform reconstruction, not perceptually transparent stems or exact null; no listening evaluation of residual and no stem artifact scoring yet.

## Reconstruction residual listening (primary desktop, 2026-10-17)

User auditioned `reconstruction-residual.wav` generated by subtracting the sum of four Demucs stems from the original 30-second source. Reported **“nothing useful or significant,” primarily hiss and distortion**, without meaningful recognizable vocal/instrument material. This is a favorable qualitative confirmation of the measured ≈2.85% residual RMS and 0.999621 waveform correlation, but not a blind listening test or proof of lossless reconstruction. Keep separate from evaluation of bleed and musical artifacts in individual stems.

## Six-stem exploratory run (primary desktop, 2026-10-17)

- User reported PowerShell elapsed **9.046711 seconds** for the 30-second excerpt, requesting `htdemucs_6s.yaml` (Vocals, Drums, Bass, Guitar, Piano, Other). Approximately 3.32× real-time.
- Prior results: VR 2 stems 21.9218053 s, Demucs 4 stems 10.1791727 s. Initial model downloads, cache and other runtime conditions may affect comparisons.
- Six outputs and isolation quality still await verification; guitar/piano listening assessment pending.

## Six-stem listening evaluation (primary desktop, 2026-10-17)

User reports six-stem isolation is **mostly good**. Guitar stem picks up some instruments that belong in Other, but the user considers this acceptable. **Vocals and percussion are separating cleanly**, which are the most important isolated edit targets for their existing tracks. Prioritize vocal and drum isolation utility, repeatability and artifacts for M0; do not require perfect guitar/other classification before usable release. This is a user listening impression, not a quantitative interference score.

## Current default model decision (2026-10-17)

User selected **`htdemucs_6s.yaml` as the current baseline** for continued Song Harbor tests. Use it for full-song, performance, quality, and hardware comparisons by default. The four-stem and VR two-stem models remain reference alternatives, not the present default. For current production needs, clean vocal and percussion stems are the primary qualitative acceptance criteria; modest guitar-versus-Other bleed is tolerated. This is a testing baseline, not a final release or licensing decision.
