---
type: Product Vision
title: Song Harbor Product Vision
description: Working product promise, positioning, and non-goals.
status: draft
tags: [product, vision]
---
# Song Harbor Product Vision

Song Harbor is a **local-first, standalone music production environment** that makes AI generators interchangeable instruments within a user-controlled creative process. It is not primarily a one-shot text-to-song generator and is not branded to any particular fictional or actual performer.

## Core promise

Keep the parts you like; revise, regenerate, rearrange, or replace the parts you do not. A person can direct a full song, one section, one track or stem, or a short phrase without unnecessarily losing approved work.

## Product principles

- Local generation is fundamental. The reference baseline is NVIDIA RTX 4070 12 GB VRAM and 96 GB system RAM; the base tier must be usable on this machine.
- Design step-up and step-down capabilities for smaller or larger hardware. Specific minimums and benchmarks are not yet confirmed.
- Own a model-neutral, non-destructive project representation with explicit song, section, track, timing, media, score, and provenance data.
- Support structured editing and natural-language direction, with transparent differences between exact operations and approximate generative guidance.
- Treat separately generated tracks, separated stems, imported audio, and symbolic/MIDI tracks as different kinds of editable assets.
- Allow model, effect, plugin, LoRA and LoKr substitution according to actual compatibility and licensing.
- Work offline for core workflows. Optional cloud execution is future-facing, user-configured, and not required for MVP.
- Support ingesting recordings/stems and reconstructing editable project structure with confidence and uncertainty represented.
- Preserve versions, approved regions, render recipes, and generation provenance.

## Product family and branding

TWS Studios is the publisher. Song Harbor is a **working title**, locked for the repository, not a claim of trademark clearance. Potential module names, not approved brands: **Second Take** (revision/remix), **Track Yard** (stem and arrangement), **Pocket Producer** (creative assistant), **Patch Bay** (routing/model management). Module and workspace naming is intentionally open. Infra Choir is an independent consumer/test workload and must not be embedded as a product identity or cross-promotion.

## Users and outcomes

Start with independent creators on consumer GPUs. A successful workflow imports or generates a song, inspects sections/stems, changes a bounded region while preserving surrounding work, auditions alternatives, mixes, and exports a complete song without depending on hosted services.

## Non-goals for initial release

- Reimplementing a complete professional DAW from scratch.
- Requiring cloud subscriptions or cloud identity for core creation.
- Guaranteeing perfect source separation or recovering unknowable original composition instructions from mixed audio.
- Supporting every model architecture or adapter combination from day one.
- Shipping training, collaboration, or remote compute in MVP.
