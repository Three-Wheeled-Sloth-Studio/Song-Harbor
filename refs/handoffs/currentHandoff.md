---
type: Handoff
title: Current Song Harbor Handoff
description: Discovery-phase baseline and next bounded implementation slice.
status: draft
tags: [handoff]
---
# Current Handoff

## Accepted Baseline

Song Harbor is the TWS Studios working title. A standalone local-first product must support stem/section-level music editing and generation, swappable models, plugins/LoRA/LoKr, remix/cover, imported-track reconstruction, and future optional training/cloud execution. Reference system RTX 4070 12 GB VRAM / 96 GB RAM. Infra Choir is a consumer, not co-brand. Accepted facts are in `refs/planning/decisions.yaml`. **SH-DEC-009 accepts generation-first comprehensive release sequencing, while SH-DEC-010 makes a self-contained stem separator the first functional deliverable.** Full mixed-song reconstruction and guided remix follow, rather than gate, the initial standalone generation-first release.

## What Landed

Product vision, requirements, architecture direction, decisions, open questions, structured roadmap and detailed implementation roadmap with discovery spikes, experiment goals, stage gates, fallback paths and proposed release milestones. Agent Academy foundation files were partially copied previously. The roadmap now explicitly orders standalone generation-first release before reconstruction/remix.

## Current Evidence Or Gap

Laptop Predator setup (2026-10-17) reached **environment validated, inference not yet attempted**. GTX 1660 Ti 6 GB, RAM 15.843 GiB, Windows build 10.0.26100, driver 572.47; Python 3.11.2 isolated in `G:\Apps\SongHarbor\.venv`; torch/torchaudio 2.6.0+cu126, torchvision 0.21.0+cu126, onnxruntime-gpu 1.24.4, audio-separator 0.47.0. Torch CUDA matrix multiplication succeeded and `audio-separator --env_info` detected Torch CUDA, ONNX CUDA provider, and FFmpeg 4.2.3. Pip initially upgraded torch to CPU-only 2.14.1; compatible CUDA packages restored with --no-deps. Missing ONNX Runtime was corrected by installing onnxruntime-gpu. Default model directory is /tmp/audio-separator-models/ and needs explicit G: override. Final pip check was not supplied. No model download or stem separation performed.

The user is moving to the **primary desktop**. Its previously reported RTX 4070 12 GB and 96 GB RAM are pending direct verification. Three-machine benchmark process is captured in `refs/testing/stemSeparationBenchmark.md`. No product runtime exists; full Agent Academy initialized-mode validation still pending.

## Active Test Model

User selected **Demucs six-stem `htdemucs_6s.yaml` as the current benchmark baseline** after a successful 30-second desktop run (9.046711 s) and listening check. Vocals/percussion clean; some guitar-versus-Other bleed acceptable. Prioritize full-song test and sustained performance with this model. Four-stem Demucs and two-stem VR remain comparators. Not a final shipping decision; verify weights licensing and full track resources.

## M0 UI Implementation Checkpoint (2026-10-17)

Reviewed canonical `TWS-Design-Principles/apps/App-Design-Principles.md`, `apps/Studio-UI-Style-Guide.md`, `apps/Fullscreen-Workspace-Interaction-Standards.md` and shared `TWS-UI` API. Implemented initial local vertical slice under `app/`: FastAPI service using the validated virtualenv's `audio-separator.exe`, fixed six-stem Demucs, one-job queue, status/error/logs, cancellation, download and open-output-folder, plus React entry screen importing shared `@tws-ui/core/react` controls. `app/run.ps1` launches local service and dev UI. `.gitignore` excludes models, audio, venv, runtime data and build artifacts. Follow `app/README.md` for installation and acceptance. **Not yet smoke-tested end-to-end** on user's Windows workstation; do not check off the milestone until UI works on the actual machine. No packaged standalone binary yet. User's working `D:\Apps\SongHarbor` already contains models and venv: clone source to a subdirectory or integrate git carefully rather than overwriting existing local assets.

## Multi-machine Bootstrap (2026-10-17)

The previous primary development machine is confirmed as **PC Skynet** (RTX 4070 / 96 GB), and the third laptop is named **Laptop Omen** (hardware inventory pending). A reusable Windows setup script has been added at `scripts/bootstrap-windows.ps1`. It pins torch, torchvision, torchaudio to CUDA 12.6-compatible 2.6.0 builds and ONNX Runtime GPU to 1.24.4, uses an isolated user-chosen work drive, checks GPU/FFmpeg/Python/npm, installs `audio-separator[gpu]==0.47.0`, downloads `htdemucs_6s.yaml`, and installs/builds the M0 UI. Script committed but **not yet exercised on Laptop Omen**; run it and diagnose any machine-specific issues. Avoid assuming its drive mapping, driver, Python, or memory match either prior machine.

## Laptop Omen Launchers (2026-10-17)

Added `scripts/bootstrap-windows.bat` and `scripts/launch-song-harbor.bat`, default work root `C:\\Apps\\SongHarbor`, since Omen has no other work drive. Both launch PowerShell 7 via `pwsh.exe` using repository-relative .ps1 paths; bootstrap launcher preserves errors in the console, and either accepts a root override as argument. C: placement is a deliberate machine constraint, not a change to preferred storage topology for other machines. Neither launcher has been tested on Omen yet.

## Next Slice

1. **Primary desktop first:** inventory Python installations, GPU/driver, FFmpeg, physical RAM and available storage. Ask for output, then select an isolated environment location. Do not copy Predator paths.
2. Verify CUDA Torch in the desktop environment; avoid letting audio-separator pip dependencies silently replace the selected CUDA build. Check `pip check`.
3. Install audio-separator and onnxruntime-gpu as needed; verify `--env_info`, configure a known model directory, then select a legally reviewable model for a short audio smoke test.
4. Later resume Predator at model-dir CLI inspection and a 2-stem short test. Compare same fixture across environments and keep provenance/performance separate.

## Required Reads For Next Slice

- `refs/planning/implementationRoadmap.md`: M0 separator gate and subsequent generation sequence.
- `refs/planning/stemSeparationDiscovery.md`: candidates, licensing and benchmark criteria.
- `refs/product/requirements.md`: required track, section and local capability outcomes.
- `refs/planning/decisions.yaml`: accepted boundaries versus proposals.
- `refs/planning/openQuestions.yaml`: unresolved technical and release decisions.
- `refs/README.md` and `refs/templatePolicy.yaml`: harness bootstrap and validation requirements.

## Relevant Files

`refs/planning/roadmap.yaml`, `refs/planning/todos.yaml`, `refs/architecture/overview.md`, `refs/project.yaml`.

## Do Not Reopen

Song Harbor working title/repo, TWS Studios ownership, Infra Choir brand independence, local-first/standalone, future-not-MVP cloud/training policy, and generation-first release sequence (SH-DEC-009), with separator first (SH-DEC-010).

## Validation

Documentation-only updates were pushed. No executable product tests or initialized Agent Academy generator/index validation was run. Do not declare full harness compliance before those checks pass.
