---
type: Handoff
title: Current Song Harbor Handoff
description: Discovery-phase project context and immediate next slice.
status: draft
tags: [handoff]
---
# Current Handoff

## Accepted Baseline

Song Harbor is the working title of a TWS Studios standalone local-first music production product. Baseline hardware RTX 4070 12 GB VRAM, 96 GB RAM. Requirements include stem and section control, exchangeable models, plugin/LoRA/LoKr support, remix/cover, native reconstruction from imported music, and future optional training/cloud. Infra Choir is a consumer, not a brand tie-in. See `refs/planning/decisions.yaml`.

## What Landed

Initial product vision, requirements, architecture direction, decision register, roadmap and open questions established under Agent Academy-compatible paths.

## Current Evidence Or Gap

No application code or measured product integration exists yet. Proposed MAG schema, specific model capabilities, hardware tiers and technology stack are not accepted/validated. The full Agent Academy harness, generated index and validation scripts have not yet been copied into Song Harbor.

## Next Slice

Copy Agent Academy harness and bootstrap initialized required files, regenerate its indexes, validate; then run bounded technical spikes against current local generation tools and reference hardware.

## Required Reads For Next Slice

- `refs/planning/decisions.yaml`: accepted requirements and proposal/decision separation.
- `refs/product/requirements.md`: concrete user scenarios for technical spikes.
- `refs/planning/openQuestions.yaml`: uncertainties to measure.
- Agent Academy `refs/README.md` and `refs/templatePolicy.yaml`: exact harness bootstrap/validation requirements.

## Relevant Files

`refs/project.yaml`, `refs/product/vision.md`, `refs/product/requirements.md`, `refs/architecture/overview.md`, `refs/planning/roadmap.yaml`, `refs/planning/todos.yaml`.

## Do Not Reopen

Local-first, standalone application, Infra Choir separation, and the working repository name unless directed by product owner.

## Validation

Documentation-only initialization; no application tests executed. Full Agent Academy initialized-mode validation pending harness installation.
