# DEV implementation plan: stereo, drum kits, LLM arrangement rebuild
Date: 2026-11-04
Branch: dev only. Do not promote to main or modify release assets.
Source: dev-reinstrumentation-and-vocal-cleanup-2026-11-03.md (latest checkpoint 2026-11-04 16:20 ET).

## Baseline and QA gate
Current combined-stem acceptance is implemented but not functionally verified on Windows. Before new work, execute the checkpoint's five-section Growlybass composite acceptance, stereo L/R child controls, removal/mask restoration, section text roundtrip, audition/export parity, and targeted backend/frontend tests. Fix defects first. A clean launcher build is not functional QA.

## Slice 1: minimum viable L/R split on imported rendered stems (P0)
- MVP is **reuse the existing imported-stem channel split** for every accepted reinstrumentation, including multi-section composites. Generate separately addressable Stem-left and Stem-right children exactly as other imported stems already do; permit the existing per-channel scripting (e.g. GrowlybassDirty-left.pan:left.6 and GrowlybassDirty-right.reverb:18) and preserve one user-named parent stem.
- This is NOT a new stereo architecture, nor per-note piano-roll panning, nor independent instrument generation by channel. Do not confuse MIDI channels with audio channels.
- Preserve original/rendered files, composite timing, source replacement masks and removal reversibility. Do not duplicate region masks per split child.
- Smoke QA: render -> Add combined stem once -> see one parent with both split channels -> apply distinct L/R scripts -> audition/export; remove -> masks clear. Check for errors and source integrity. Defer broader stereo refactoring and extensive spatial feature work.

## Slice 2: drum kits and editable percussion score (P1)
- Introduce arrangement part.kind='drums', explicit percussion keymap and note labels, e.g. kick/snare/closed hat/open hat/toms/cymbals. Use standard GM percussion note conventions as import defaults, not a hard-coded universal map.
- Existing polyphonic_midi.py rejects MIDI channel 9 (GM channel 10); replace blanket rejection with an explicit percussion mode while keeping melodic safeguards. For SF2 use the bank's percussion mapping; for SFZ use explicit instrument sample map/kit manifest, and don't assume all SFZ kits respond to GM.
- Support multiple simultaneous hits, velocity layers, choke groups (open/closed hats), note duration/release, sample tails, optional round robin, and independently editable kit-piece lanes. Render entire kit to one stem first, with optional per-piece stereo or separate outputs later.
- Drum transcription: start with reviewable transient-to-hit proposals with uncertainty and manual correction. Do not claim accurate full-kit transcription from an existing mixed drum stem.
- Pack discovery: inventory installed GeneralUser GS percussion and user-imported SFZ kits first; assess licenses, sample provenance, offline Windows sfizz compatibility, mapping, memory footprint and musical fit (industrial/nu-metal/boom-bap). No unverified bundled samples.
- Tests: percussion MIDI roundtrip, overlapping hits, choke behavior, non-GM mapping, silence/latency/tails, channel split and audition/export.

## Slice 3: LLM arrangement deconstruct/rebuild (P1)
- Scope: Bass, Drums, Guitar, Piano, Other. Keep Vocals excluded by default. Model receives bounded section map, note/event summaries, stem analyses, available installed packs/presets and current arrangement revision. Never send raw audio implicitly.
- Two-stage workflow: (1) analyze/transcribe source into versioned editable arrangements with confidence and uncertain notes, then (2) LLM proposes explicit section-scoped edits to those assets. Do not treat model guesses as ground-truth transcriptions. Preserve source audio and source note snapshots.
- **Catalog-first semantic resolution is mandatory**. Before interpreting any supplied musical adjective or qualifier as creative direction, inspect the *installed* pack/instrument/preset catalogue (including names, aliases and variants) and resolve the strongest exact or normalized match. Resolve pack/family first, then the matching variant *within that family*, then assign unresolved phrases to musical direction. Use IDs from the actual catalogue rather than inventing names.
- Example library contains Karoryfer Growlybass variants `growlybass_angry`, `growlybass_clean`, `growlybass_dirty`, `growlybass_excessive`, `growlybass_shifty`, `growlybass_strange`, `growlybass_vicious`. Request 'Growlybass Dirty default, Angry in choruses, Shifty in bridges, maintain and enhance industrial elements' must resolve `growlybass_dirty` as default, override chorus with `growlybass_angry`, bridge with `growlybass_shifty`, and retain 'industrial' as a musical direction **unless the installed catalogue contains a relevant matching instrument or variant and the requested syntax indicates one**. 'Angry' and 'Shifty' must NOT be turned into generic note-density/velocity heuristics when they resolve to actual selected instrument variants.
- Resolution order: (1) identify stem target and named pack/instrument family, (2) exact ID/name/alias match, (3) normalized and scoped family-variant match, (4) explain unresolved or ambiguous matches and request selection when necessary, (5) only then interpret remaining text as musical intent, style and constraints. A detected catalogue term is not automatically an instrument selection if context clearly uses it as an adjective: retain explicit evidence and allow user override. Never silently substitute a different library preset.
- Supply the model with a compact, grounded catalogue snapshot and a tool/schema for verified IDs; ideally perform deterministic backend matching before the model, and validate all selected IDs again on return. Log resolution evidence in the review diff: phrase -> type (pack/variant/direction) -> ID/reason/confidence. Do not depend on the LLM's implicit knowledge of user's installed samples.
- Proposed plan schema: {base_revision, target_stem, sections:[{section_id, intent, instrument:{pack_id,instrument_id}, operations:[{op, note_id?, values?}], rationale, confidence}], constraints:{preserve_vocals:true,preserve_timing:true,maintain_industrial:true}}. Validate JSON schema, section bounds, note ranges, preset existence, revision conflict, operation caps, and total duration before applying.
- Score should support section-level instrument assignment and deterministic rendering with a single combined stereo stem. Instrument swaps and note edits are separately reviewable. Add preview diff (before/after note map, kit piece map, preset changes), A/B and explicit Accept/Discard/Undo. One accepted stem per part across selected sections; linked source-volume masks only where replaced.
- Build LLM provider-neutral request/response contract and mock adapter first; local Ollama can be one optional provider. No hard-coded model dependency, hidden network calls, or silent edits. Keep prompt, structured plan, source revision, renderer/preset provenance and accept decision as a reproducible recipe.
- Musical heuristics, applied ONLY to unresolved musical-direction terms after catalogue matching: chorus increased density/velocity/octave doubling, bridge syncopation/variation, industrial accents/percussive textures; avoid automatic loudness creep, harmonic clashes or overwriting manual edits.
- End-to-end fixture: five stems, section map including chorus/bridge, catalog-matched growlybass_dirty default, growlybass_angry choruses, growlybass_shifty bridges, 'industrial' retained as direction, verified resolution trace, sparse arrangement, version conflict, unavailable preset, partial reject, repeatable render, exported stereo parity.

## Delivery order
0. Windows regression gate and bug fixes.
1. MVP existing imported-stem L/R split and per-channel scripting smoke QA.
2. Drum keymap/kit manifest + one working imported kit and percussion MIDI render.
3. Section-level library-variant assignments and one-stem multi-section render, with catalog-first language resolution.
4. LLM plan schema, validator, mock adapter and review UI.
5. Optional local model integration and multi-stem orchestrator.
6. Deshimmer vocal bridge remains separately planned, not silently dropped.

## Acceptance principles
Dev only; reversible, non-destructive; user alias only in track name; no surprise autoplay; no silent partial batch acceptance; explicit review of model edits; no LLM modifications to vocals; script uses .volume not .original for emitted source muting; old .original imports still parse; do not claim Windows QA until user runs it.
