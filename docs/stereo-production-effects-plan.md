# Stereo production and effects: near-dual-mono sources

Status: design direction (2026-10-20), not implemented. User confirmed *Voices Below the Deck* stems have very high L/R similarity, with some small differences. First two tracks will be finished manually in external DAWs. Song Harbor is product-first, with human A/B decisions and local-first processing.

## Critical finding: six-stem mixer vs derived track exports
`ChannelSplitter` generates distinct L/R mono WAVs in `exports/Channels-*/`. The player in `StemMixer.tsx` still constructs exactly six HTMLAudioElement players from original separation outputs; channel split outputs are not in its track graph or export mix. This is a real model/UX gap, not a missing refresh. **Do not merely append the channels to the six existing tracks**; playing stereo parent plus L/R children simultaneously doubles audio, risks clipping and invalidates listening experiments.

## Target track/clip model
- Source media: immutable stereo stem from separation; derived artifacts retain lineage/source hash and time alignment.
- Parent stereo stem plus optional children L/R (or later separated voices/instruments), stable track IDs, independent gain/pan/effects/mute/solo, group bus and routing.
- **Exclusive default routing:** when split children are active, parent is inactive in playback AND export. `Restore stereo` reactivates parent, children remain as reversible artifacts.
- Derived mono children default to hard-left/hard-right, unity gain, preserving reconstructed stereo without inadvertent +3/+6 dB change. Need explicit pan law tests and numerical null/reconstruction tests including source sample format/resampling.
- Persist active routing and child settings across open/restart; reflect in the integrated waveform timeline and asset/version history. Generic track graph supports later L/R, vocal subgroup, percussive layers or instrument stems without enforcing six audio elements.
- Mix-only/master monitoring level never modifies exports. All DSP previews and offline export use the same deterministic graph and latency compensation.
- Consider safe on-demand streaming of derived exports using exact project+manifest-owned path, not user-supplied arbitrary files. Do not mix stale exports from another song.

## Stereo strategy for highly correlated L/R audio
1. Analyze L/R correlation, side-to-mid energy ratio, mono fold-down/phase stability, dynamic frequency balance and stereo perception by section. Flag high correlation as an opportunity rather than a defect.
2. Keep centered anchors: main lead vocals, kick/snare impact and bass fundamental. Preserve center/low end mono compatibility. Human/organic sounds generally bias left, mechanical/synthetic textures bias right, ambient/orchestral layers spread wider, as a **customizable album profile**, not global product branding.
3. **Prefer spatial arrangement of independently separated stems or effects returns** over decorrelating the full stereo master. Use semantically tagged tracks and buses.
4. Add perceptual width via controlled stereo reverb, early reflections, tempo-synced L/R delays and asymmetric short texture sends. Can offset one side's ambience without moving the dry center. Use mid/side EQ only when measurable side energy exists; avoid blind `widen 150%` on nearly dual-mono inputs.
5. Section-aware pan automation: modest curves, timed responses, human-vs-machine handoffs, slow movement and punctuation on transitions. Derive from saved section labels and analyzer suggestions, not unpredictable pan jitter. Parameter curves with sample-time alignment and bounded smoothing.
6. Optional transient/percussion accents and new organic/mechanical layers for richer width later; channel extraction alone does not produce new independent source information.
7. Guardrails: evaluate mono fold-down, correlation/negative-phase events, true peak, low-frequency anchoring, vocal focus and excess head-motion; loudness-matched blind/reversible A/B. Strong recommendation can be `leave as-is`.

## Effects work allocation

| Domain | External DAW now | Song Harbor near term |
|---|---|---|
| Editing and cleanup | Audacity precise waveform repair | analyzer and bounded problem regions, deterministic gain fades later |
| Pan/automation | MorningDAW and Waveform native automation | pan curves linked to section/track semantics with matched A/B |
| EQ dynamics | DAW VST3 & built-ins | basic EQ/dynamic controls, offline/preview parity |
| Width/depth | DAW stereo delays/reverbs and sends | controlled stereo cross-delays/early reflections/return buses, constrained preset engine |
| Creative layers | DAW aligned impacts/percussion/audio | versioned supplemental tracks later |
| Third-party automation | Manual in DAW; export WAVs and parameter recipes | No unverified native session creation, plugin state injection, automation scripting or UI keystroke macros |

MorningDAW documentation: https://edu.morningdewmedia.com/pages/morningdaw/manual/ (automatable pan/sends/plugins, CLAP/VST3, sidechain). Waveform manual: https://tracktion.github.io/waveform_manual/latest/automation/ (pan/volume/plugin automation). Audacity 4 manual: https://www.audacityteam.org/manual/effects/realtime-effects/ (whole-track realtime effects). Specific automatic scripting capabilities **not validated**, treat native session export as feasibility spikes.

## Procedural engine architecture
- Canonical multi-track audio graph + routing + automation curves (seconds/samples; section IDs as metadata), independent of DAW vendor.
- Separate deterministic measurement layer (correlation, mid/side ratios, loudness, tempo, transients, sections) from recommendation layer.
- Suggest **one scoped candidate at a time**, with evidence, expected audible effect, constraints and confidence.
- Real-time loudness-matched A/B/bypass, human **Better / Worse / Reroll** and optional contextual notes. All candidates reversible, preview/export parity mandatory.
- Learn personal preference patterns locally and transparently; LLM only enriches explanations/creative variants, never authoritative DSP or unattended changes.
- Derived media, source and processing graph remain immutable/versioned; edits create new versioned parameters/renders.

## Suggested engineering slices
P0: integrate channel split outputs into song graph + active parent/child routing, visual rows, persistence and export, sample reconstruction tests; replace six-HTMLAudioElement assumption before promising reliable synchronized A/B.
P1: one synchronized audio clock/DSP engine and section-loop audition; per-track pan including center-preserving equal-power behavior; offline export parity.
P2: analyzer v1 (correlation, mid/side energy, mono and balance) + procedural static stereo layout suggestions by context; A/B decisions.
P3: stereo ambience sends, frequency-dependent width, automation curves that respect song sections and narrative tags.
P4: EQ/compression/saturation buses, more sophisticated orchestral masking and industrial percussion treatments.
P5: optional vocal subdivision, supplemental audio tracks and DAW handoff improvements.

Acceptance tests: active L/R child render approximately reconstructs parent at default routing; no parent/child doubling; saving/reopening maintains routing; stereo suggestions change measured and perceived spatial field while preserving centered anchors and mono compatibility; every accepted processing choice is reversible and auditable.
