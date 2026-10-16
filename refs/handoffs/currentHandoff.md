---
type: Handoff
title: Current Song Harbor Handoff
description: Discovery-phase baseline and next bounded implementation slice.
status: draft
tags: [handoff]
---
# Current Handoff

## Accepted Baseline

Song Harbor is the TWS Studios working title. A standalone local-first product must support stem/section-level music editing and generation, swappable models, plugins/LoRA/LoKr, remix/cover, imported-track reconstruction, and future optional training/cloud execution. Reference system RTX 4070 12 GB VRAM / 96 GB RAM. Infra Choir is a consumer, not co-brand. Accepted facts are in `refs/planning/decisions.yaml`.

## What Landed

Product vision, requirements, architecture direction, decisions, open questions, structured roadmap and detailed implementation roadmap with discovery spikes, experiment goals, stage gates, fallback paths and proposed release milestones. Agent Academy foundation files were partially copied previously.

## Current Evidence Or Gap

No music app runtime, technical feasibility measurements or confirmed production stack. Full Agent Academy harness and generated indexes are still not verified as initialized. Stage sequence and M1-M5 boundary are **proposals**, not newly accepted product decisions. Work remains to prove source isolation, independent stem output and reliable 12 GB execution.

## Next Slice

1. Finish the Agent Academy harness and validation, creating a stable agent re-entry workflow.
2. Define a reproducible benchmark fixture pack and experiment manifest for two local model backends.
3. Run controlled tests of full generation, localized edits, independent stems, score-conditioned handoff and import analysis on reference hardware.
4. Record observed capabilities, model licenses and measurable go/no-go results; only then finalize adapter and project schema contracts.

## Required Reads For Next Slice

- `refs/planning/implementationRoadmap.md`: Stage 0/1 experiment definition and exit criteria.
- `refs/product/requirements.md`: required track, section and local capability outcomes.
- `refs/planning/decisions.yaml`: accepted boundaries versus proposals.
- `refs/planning/openQuestions.yaml`: unresolved technical and release decisions.
- `refs/README.md` and `refs/templatePolicy.yaml`: harness bootstrap and validation requirements.

## Relevant Files

`refs/planning/roadmap.yaml`, `refs/planning/todos.yaml`, `refs/architecture/overview.md`, `refs/project.yaml`.

## Do Not Reopen

Song Harbor working title/repo, TWS Studios ownership, Infra Choir brand independence, local-first/standalone and future-not-MVP cloud/training policy.

## Validation

Documentation-only updates were pushed. No executable product tests or initialized Agent Academy generator/index validation was run. Do not declare full harness compliance before those checks pass.
