# Artifact / fingerprint cleanup — implementation exploration
Date: 2026-10-26
Status: research and architecture recommendation; **no new detector, model download, audio processing, or release candidate changes**.

## Decision in one sentence

Build **source-aware, localizable, reversible artifact repair** into existing Song Harbor Sound Cleanup, while keeping AI origin/fingerprint classification as a separately labeled offline research bench. Never use detector-score suppression or provenance removal as a mastering objective.

## Current checked implementation

The repository already has:
- `app/frontend/src/AudioCleanupAnalyzer.ts`: inspectRenderedAudio runs on a fully rendered in-app float mix. Detectors cover sample peak/headroom (not true peak), abrupt jumps, flat-tops, repeated level dips, stereo anti-correlation, and sustained 2.5–4.9 kHz harshness, sibilant/high-fizz and noise-like energy. Results have approximate positions, not proof of source or cause. Up to 48 returned.
- `app/frontend/src/SignalAudit.ts`: sampled 4096-FFT scan, max 600 distributed analysis windows, looking for persistent narrowband lines from 4–11.5 kHz. It explicitly **cannot identify watermarks or generator fingerprints**. A repeated synth resonance can score.
- `app/frontend/src/ForensicsReview.tsx`: separate experimental inspector with grouping/filtering, seek and loop; **reuses the same findings** as Sound Cleanup, not an independent pretrained classifier.
- `app/frontend/src/CleanupReview.tsx`: regional loop and seek; existing try-correction A/B presently offered for headroom and pumping only. Other categories have listening suggestions, not repair actions.
- `app/frontend/src/SharedClockAudition.ts`: current live/offline mix graph and on-demand analysis; source stems available in the project, which makes future attribution and A/B possible.
- `docs/ai-audio-forensics-discovery.md` and `docs/remote-daw-waveform-restoration-discovery.md`: existing exploration and cautions.

Gaps: no aligned original->export/stage diff, no per-stem culpability score, no spectrogram time-frequency region overlay, no click or spectral repair candidate generator, no objective true-peak/integrated LUFS pipeline in this analyzer, no robust user-reviewed repair ledger, and no production-general AI fingerprint detection model. Do not overstate finished capabilities.

## Why generator fingerprint scores are not a cleanup target

1. **Provenance**: embedded credentials or watermark schemes are separate from audible signal defects. Retain records and disclosure; do not attempt to strip provenance or misrepresent generation.
2. **Generator spectral residuals**: architecture-specific periodic components may identify particular old Suno/Udio engines, but a score dropping after EQ, resampling, denoise, limiting or codec changes does not prove better sound.
3. **Audible defects**: clicks, warped harmonics, smeared attacks, harsh upper mids, pumping, mono cancellation, poor transitions, clipping, vocal formant/sibilance flaws and separation bleed. These can be identified, isolated, A/B tested and often repaired.
4. **Artistic texture**: industrial distortion, metallic cymbals, sustained synth harmonics and intense compression are *often intentional*. Require a context-sensitive listening judgment.

## Candidate technologies — validated scope and caution

| Candidate | Utility | Integration assessment |
|---|---|---|
| Existing TypeScript Analyzer + SignalAudit | Starting point for audible issue detection, timecode/loop and mix playback | **P0 — extend rather than replace**; no model/GPU |
| **KillrBee/ai-music-detector** | Heuristic multi-domain ideas: spectral/temporal/spatial/vocal analysis, breath/formant and timbral consistency | **Method reference only**; heuristically weighted “AI probability” trained/tuned on a small calibration sample. README says MIT, but confirm repository current license before copying any implementation; build independent tests rather than importing wholesale |
| **lofcz/ai-music-detector** | MIT ONNX/CQT/Suno-Udio-specific “fakeprint” spectral classification | **Optional P2 forensic sandbox**, trained for specific generators. No reliable claim for ACE 1.5/YuE2 or mastered hybrids; not a repair quality metric |
| **lcrosvila/ai-music-detection** | Transform robustness, validation methods; Essentia/CLAP embedding source classifiers | **Research only**, too heavy for realtime/local repair and rights of code/weights need validation |
| **Spotify pedalboard** | CPU offline effect renderer and third-party VST3 hosting on Windows | **P1 repair engine candidate**; good backend for reversible de-esser/EQ/gate etc after latency/automation/plugin licensing tests, not itself an AI-restoration solution |
| **DeepFilterNet** | Full-band 48-kHz learned noise suppression focused on speech | **P2 optional isolated vocal stem experiment**, not a default full-mix music enhancer; watch lost breath, consonants and reverb. Assess local Windows packaging/runtime/licensing |
| **iZotope RX** | Mature de-click, de-clip, spectral denoise/repair tools | **External specialist benchmark / manual DAW handoff**, proprietary and not assumed callable from Song Harbor |
| **facebookresearch/denoiser** | Neural speech denoise reference | **Deprioritize**: archived, CC-BY-NC; unsuitable to bundle as production dependency without rights review |

References:
- https://github.com/KillrBee/ai-music-detector
- https://github.com/lofcz/ai-music-detector
- https://github.com/lcrosvila/ai-music-detection
- https://spotify.github.io/pedalboard/
- https://github.com/Rikorose/DeepFilterNet
- https://www.izotope.com/pages/rx-for-content
- https://github.com/facebookresearch/denoiser

## Prioritized implementation sequence

### P0 — establish actual regression and position (suggested 2–4 dev days)

- Introduce `AudioAnalysisTarget` identifying stage and asset identity: source mix, extracted stem, accepted/generated stem, effects-rendered mix and final exported WAV. Include PCM revision hash, sample rate, channels, and timeline origin.
- Align time and sample rate; account for known intentional gain, fades/tails, resampling and stem offsets. Use *stage-to-stage deltas* rather than absolute “AI” likelihood.
- Compute per-section/window: sample and oversampled/true peak, integrated and short-window LUFS, spectral centroid/rolloff, multi-band energy deviations, transient-envelope attack preservation, stereo correlation, mid/side ratio, mono loss, large sudden silence and output tail truncation.
- Report source -> output differences with precise times and one of: `new since source`, `inherited from source`, `changed`, `ambiguous`. Make confidence source-dependent; no unsupported numerical probabilities.
- Surface actionable “go to timestamp”, 2–5-second loop, choose reference, and **Mark intentional / Reviewed / Needs repair** actions; persist decisions with source revision so old decisions invalidate on edit.

### P1A — attribution and visibly reversible repair POC (3–6 dev days)

- For each candidate issue, check stem-local signal evidence within ±1–3s. Rank *suspect stems* by transient/time-frequency coincidence, energy and source-vs-mix comparison. Never claim certainty when separation bleed or effects cause ambiguity.
- Waveform + compact spectrogram strip for a selected region. Render only the selected region, not a full high-resolution 5-minute track in browser memory.
- Implement **one conservative deterministic de-click** candidate for isolated impulses (short interpolation with edge-aware crossfade, or offline linear prediction), plus preview gain-match. On drum transients require stricter thresholds and user approval.
- Add **stereo/mono integrity** diagnostics for the user's changing L/R reverb and bass movements; report whether a proposed repair reduces intended spatial storytelling.
- A/B buttons Original, Corrected, Solo suspect stem, bypass, and Accept/Revert; accept as an immutable edit recipe/child asset referencing the source revision, not destructive rewrite.

### P1B — musical-specific remediation (4–8 dev days)

- Extend effect schema with explicit per-stem/per-section *de-ess*, narrow dynamic EQ and bounded notch with time/frequency envelope. Avoid blind static peak deletion.
- Treat low-energy hiss and bleed in isolated stems differently from full-mix texture. Verify no newly introduced gated tails/phase artifacts.
- Add targetable transient recovery/guard and late-tail crossfade only on confirmed areas.
- Report audibility after correction: level-matched A/B, changed-band energy, clip/mono changes and a subjective Better/Same/Worse decision; never autocommit.

### P2 — optional specialized experiments (2–4 dev days per narrow POC; independent of release)

- Bench lofcz ONNX in a sidecar on a controlled corpus with human electronic mixes and generated Suno, YuE2, ACE, stems and deliberately distorted masters. Verify accuracy, false positives, latency and codec sensitivity against intended original model domain; do not ship general “human score”.
- Try DeepFilterNet on *isolated vocal* samples only. Compare dry reference and denoised candidate; listen for smeared sibilants, lost air, and metallic artifacts before adopting.
- Consider a neural music restoration model only after a reproducible defect-specific fixture shows it beats conventional repair on our music. Do not put PyTorch/VST dependencies into the default Song Harbor install prematurely.
- Fold useful forensics into Sound Cleanup; retain optional “Advanced forensic evidence” disclosure instead of two duplicative tool windows.

## QA fixtures and measurements

Build four fixture families:
1. Clean human/vocals, intentionally distorted industrial synth and normal cymbal resonance **negative controls**.
2. Known click/flat-top, hard cutoff reverb, narrow HF spur, phase-inverted wide stereo, over-deessed vocals, gated tails **synthetic positive controls**.
3. Anonymized Infra Choir generated mixes and separated stems (Suno -> YuE -> Song Harbor), with previously noted ~02:43 loudness dips, ~03:35 near-overloaded peaks; verify on the actual revision instead of claiming those timestamps apply to every track.
4. Edited-before/after control pairs, identical song content, matched loudness; preserve original data and disclose generation provenance.

Per detector report FPR on controls, precision@5 actionable findings, time localization error (target <200ms for clicks), false suppression of intentional percussion, scan latency, memory on 5-minute 48-kHz stereo / 16-stem session, audible Better/Same/Worse rate, export parity and undo. Quantitative targets need calibration from this corpus.

## Performance and cache discipline

CPU-first detection, bounded 5–15s windows, incremental STFT, chunked renders, reuse waveform peak caches where useful. 12 GB VRAM RTX 4070 reserved for ACE/other generators; don't keep forensic models resident. Optional heavy models run separately with explicit resource status. Cache analysis by `project revision + render stage + detector version + sample format`; archive only findings and downsampled preview statistics, not redundant full-length PCM unless accepted candidate needs provenance. Candidate retention must be reference-safe.

## Release gate vs feature work

The currently finishing Infra Choir track should **not** be blocked on fingerprint classifiers or speculative generative restoration. Run current Sound Cleanup and listen to flagged regions; preserve intentional elements. If there is a clear click/clip or audible distortion, attempt safe narrow correction or external RX/DAW handoff. Do not start model installation or bulk processing mid-mastering.

The first implementation PR/commit sequence after release: P0 stage-diff schema and measurements -> local waveform/spectrogram QA -> one de-click A/B repair -> optional model bench. A separate panel that outputs another origin score is explicitly **not** first priority.
