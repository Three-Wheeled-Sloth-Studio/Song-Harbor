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

Three-platform benchmark tracking is initialized in `refs/operations/machineProfiles.yaml` and `refs/testing/stemSeparationBenchmark.md`. Laptop Predator inventory observed GTX 1660 Ti 6 GB, NVIDIA driver 572.47 and Python 3.11, but GPU-enabled PyTorch and RAM remain unknown. Primary desktop and third platform are pending direct measurements.


No music app runtime, technical feasibility measurements or confirmed production stack. Full Agent Academy harness and generated indexes are still not verified as initialized. The generation-first sequencing is accepted, while detailed milestone acceptance thresholds and the implementation stack remain proposed. Work remains to prove source isolation, independent stem output and reliable 12 GB execution.

## Next Slice

**Priority zero: Stem Separation Workbench, ahead of generation.**

1. Finish the Agent Academy harness and validation, creating a stable agent re-entry workflow.
2. Prototype python-audio-separator with legally reviewed 2/4-stem models; measure 12 GB VRAM, audio quality and alignment.
3. Build standalone-compatible separation utility: batch, progress, preview, export, manifests. Then resume ACE-Step/YuE2 generation benchmark.
4. Record observed capabilities, model licenses and measurable go/no-go results; only then finalize adapter and project schema contracts.

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
