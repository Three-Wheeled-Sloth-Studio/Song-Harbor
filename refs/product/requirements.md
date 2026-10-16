---
type: Requirements
title: Song Harbor Product Requirements
status: draft
description: User-specified requirements and phased product acceptance expectations.
tags: [product, requirements]
---
# Song Harbor Requirements

Status legend: **Required** = requested product capability; **MVP target** = first implementation scope proposal; **Later** = architectural provision without initial implementation commitment; **Open** = feasibility or precise acceptance unresolved.

| ID | Requirement | Priority / phase | Notes |
| --- | --- | --- | --- |
| R-001 | Local AI music generation | Required, MVP target | Reference RTX 4070 12 GB VRAM, 96 GB RAM; benchmark before claiming performance |
| R-002 | Scale up/down across hardware tiers | Required architectural | Sequential loading, offload, caching, quality tiers; actual limits open |
| R-003 | Optional configured cloud model offload | Later | No cloud requirement for MVP |
| R-004 | Independent stem-level editing, generation, and output | Required | Model capability varies; do not mislabel separated stems as independently generated |
| R-005 | Section-level control, generation, and transitions | Required | Explicit section IDs, track assignments, delivery cues, transitions, crossfades |
| R-006 | Exchange models for different tasks | Required, MVP target | Capability registry and adapter contract |
| R-007 | Plugin, LoRA and LoKr support | Required | Engine-specific compatibility checks |
| R-008 | Adapter/model training | Later | Data rights and resource requirements reviewed before implementation |
| R-009 | Cover and remix creation | Required | Preserve user-selected aspects; respect rights and provenance |
| R-010 | Import track/stems and decompose to native instructions | Required | Confidence-bearing approximation; source retained |
| R-011 | Standalone desktop application | Required | Development workflows can live anywhere |
| R-012 | Non-destructive edits, versions, previews, undo | Required architectural | Exact vs probabilistic change semantics must be explicit |
| R-013 | Mixing, basic processing, and stem/project export | MVP target proposal | Rich DAW features may be integrations rather than bespoke |
| R-014 | Song/section/track/phrase level instruction model | Required architectural | Structured intent plus native media/score data |
| R-015 | Export assets and generated song with provenance | Required | Formats and licensing policy open |

## Representative acceptance scenarios

1. Create a song with drum 1 = boom-bap, horns 1 = go-go, vocal 1 = dramatic soprano female, vocal 2 = swing-flow baritone male; retain track identity across sections.
2. Direct Verse 1 to use vocal 2 with triplet-flow drill delivery and a short crossfade into the following section. Regenerate and audition without unintentionally overwriting other accepted sections.
3. Replace one instrumental stem or region; keep unaffected audio and timing stable within an agreed tolerance (tolerance not yet set).
4. Import a mixed song; produce synchronized sections, rough stem separation, inferred tempo/key, optional lyrics and symbolic scores, with confidence and source preservation.
5. Replace one model with another capable model for a bounded task without changing the native project format.
6. Complete the core workflow with network disabled on the reference workstation.

## Technical spikes before claiming feasibility

Test timing preservation, edit isolation, model interoperability, VRAM and RAM peaks, output quality, stem bleed, and recoverability. ACE-Step and YuE2 are evaluation candidates, not endorsed dependencies.
