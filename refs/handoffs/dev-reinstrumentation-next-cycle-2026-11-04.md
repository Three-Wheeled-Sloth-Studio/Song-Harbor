# DEV implementation plan: stereo, drum kits, LLM arrangement rebuild
Date: 2026-11-04
Branch: dev only. Do not promote to main or modify release assets.
Source: dev-reinstrumentation-and-vocal-cleanup-2026-11-03.md (latest checkpoint 2026-11-04 16:20 ET).

## Baseline and QA gate
Current combined-stem acceptance is implemented but not functionally verified on Windows. Before new work, execute the checkpoint's five-section Growlybass composite acceptance, stereo L/R child controls, removal/mask restoration, section text roundtrip, audition/export parity, and targeted backend/frontend tests. Fix defects first. A clean launcher build is not functional QA.

## Slice 1: independently controllable stereo audio (P0)
- Keep canonical 48-kHz stereo render and immutable original, with separately addressable left/right derived tracks attached to the SAME accepted stem. Never confuse MIDI channel (0-15), drum voice/part, and PCM audio channel (L/R).
- Verify stereo is preserved through SFZ/SF2 rendering, section composite, imported track manifest, channel split, mixer, script parser, audition, and exported mix. Detect mono render explicitly; do not fabricate stereo separation from identical channels.
- Expose concise child channel controls under the single user-named stem, including solo/mute/pan/gain and effect directives consistent with existing Stem-left/Stem-right scripting. Preserve source masks on parent stem, not independently duplicated masks.
- For piano roll, defer per-note L/R until score parts/lanes exist; define optional note/part pan as rendering metadata, not MIDI channel identity. Ensure original stem and exported result remain unchanged when candidate is discarded.
- Tests: impulse hard-left/hard-right, asymmetric stereo fixture, stereo composite gap, export parity, section boundaries, remove/re-add, legacy scripts.

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
- Natural-language example: 'Rebuild Bass with Growlybass Dirty as default; angry choruses; shifty bridges; maintain and enhance industrial elements.' Resolve exact installed preset ID by catalogue; ask/flag when unavailable. 'Angry'/'shifty' become inspectable, user-editable intent tags, not magic unreviewable DSP.
- Proposed plan schema: {base_revision, target_stem, sections:[{section_id, intent, instrument:{pack_id,instrument_id}, operations:[{op, note_id?, values?}], rationale, confidence}], constraints:{preserve_vocals:true,preserve_timing:true,maintain_industrial:true}}. Validate JSON schema, section bounds, note ranges, preset existence, revision conflict, operation caps, and total duration before applying.
- Score should support section-level instrument assignment and deterministic rendering with a single combined stereo stem. Instrument swaps and note edits are separately reviewable. Add preview diff (before/after note map, kit piece map, preset changes), A/B and explicit Accept/Discard/Undo. One accepted stem per part across selected sections; linked source-volume masks only where replaced.
- Build LLM provider-neutral request/response contract and mock adapter first; local Ollama can be one optional provider. No hard-coded model dependency, hidden network calls, or silent edits. Keep prompt, structured plan, source revision, renderer/preset provenance and accept decision as a reproducible recipe.
- Musical heuristics to expose as editable parameters: chorus increased density/velocity/octave doubling/distortion-capable instrument, bridge syncopation/variation, industrial accents/percussive textures; avoid automatic loudness creep, harmonic clashes or overwriting manual edits.
- End-to-end fixture: five stems, section map including chorus/bridge, default Growlybass Dirty with chorus/bridge overrides, sparse arrangement, version conflict, unavailable preset, partial reject, repeatable render, exported stereo parity.

## Delivery order
0. Windows regression gate and bug fixes.
1. Stereo correctness and controls with tests.
2. Drum keymap/kit manifest + one working imported kit and percussion MIDI render.
3. Section-level preset assignments and one-stem multi-section render.
4. LLM plan schema, validator, mock adapter and review UI.
5. Optional local model integration and multi-stem orchestrator.
6. Deshimmer vocal bridge remains separately planned, not silently dropped.

## Acceptance principles
Dev only; reversible, non-destructive; user alias only in track name; no surprise autoplay; no silent partial batch acceptance; explicit review of model edits; no LLM modifications to vocals; script uses .volume not .original for emitted source muting; old .original imports still parse; do not claim Windows QA until user runs it.
