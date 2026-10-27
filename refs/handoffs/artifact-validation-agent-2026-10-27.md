# Song Harbor artifact and fingerprint validation agent handoff
Date: 2026-10-27
Branch: main
Authority: user explicitly requested main; preserve working user media, don't reset/clean local checkout.

## Immediate objective
Run and harden the artifact QA harness on a real Windows installation, reproduce failures, calibrate the first acoustic diagnostic, and prepare additional specialized diagnostics. **Do not equate generator fingerprints with audible artifacts or repair efficacy.** Any audio modification requires explicit preview/accept.

Read first:
- refs/handoffs/currentHandoff.md (2026-10-26 priority reset)
- docs/ai-audio-forensics-discovery.md
- docs/artifact-evaluation-harness-2026-10-27.md
- docs/attack-rise-diagnostic-2026-10-27.md
- docs/frontend-build-release-gate.md

## Stage 0: environment, reproducibility, compilation
1. Confirm branch `main`, clean/dirty working tree and exact starting SHA; NEVER discard edits, overwrite audio, or force-reset.
2. Run from repo root (PowerShell 7): `pwsh -File scripts/verify-artifact-suite.ps1`.
   - This invokes `npm ci --prefix app/frontend`, `npm run build --prefix app/frontend`, acoustic tests and an artifact benchmark. It writes `$env:TEMP/song-harbor-artifact-qa/artifact-benchmark.json`.
   - Alternative for staged environments: `pwsh -File scripts/verify-artifact-suite.ps1 -SkipInstall`.
   - Report TypeScript/Vite failure separately from test/benchmark failure. A successful GitHub commit does NOT certify a passing build.
3. Inspect GitHub Actions **Frontend build** and **Single-server launch smoke** for the specific commit. If access to Actions statuses is unavailable, say NOT VERIFIED, never PASS.
4. If a test fails, capture exact input, expected, observed, log, test name and SHA. Fix smallest cause, rerun entire test group and build.
5. No claimed live audio QA unless using real Windows playback and offline exported WAV.

## Stage 1: synthetic acoustic QA
Files:
- `app/frontend/src/AttackRiseDiagnostic.ts`
- `app/frontend/src/AudioCleanupAnalyzer.ts`
- `app/frontend/tests/artifact-evaluation.mjs`
- `app/frontend/tests/artifact-fixtures.mjs`
- `app/frontend/tests/planned-artifact-fixtures.mjs`
- `app/frontend/tests/run-artifact-benchmark.mjs`
- `app/frontend/tests/*.test.mjs`

The matchEvents evaluator has maximum-cardinality one-to-one pairing rather than nearest-first greedy matching, which can lose matches when truth windows overlap. Verify TP/FP/FN, timestamps, duplicate-hit penalties, and localization tolerances. Assert deterministic repeated JSON on the same environment. Keep floating-point precision and sample-rate drift visible.

Attack-rise currently detects 35-140 ms isolated 10%-90% RMS ramps from ~2ms frames. **A soft synthesizer pad can correctly satisfy its numeric condition and still be an intentional sound**, so its negative control is not to be silently relabeled. Report this as an observed false-positive rate, not necessarily a failed test.

The planned-method fixtures include:
- Reverb: natural decay, hard cutoff, flat/stalled tail, intentional gate.
- Spatial: aligned stereo, antiphase, intentional wide stereo.
- Spectral: natural harmonic tone, upper-band line, deliberate industrial saturation.
- Vocal: simple breath-like/noise fragment (NOT a validated human phoneme/formant control).
These fixtures are currently **data and contract tests only**. Do not claim the named specialized algorithms are present.

## Stage 2: real audio evaluation matrix
Curate recordings only when ownership/licensing allows. Preserve source names, model versions, generation dates, chain stage, sample rates, source hashes and annotation metadata separately from audio. Do not commit copyrighted/private WAV files to the public repository.

Per control family, include at minimum:
- Sources: acoustic recordings; intentionally processed industrial/electronic; Suno, YuE2, ACE outputs (model versions recorded); source + remix + separated stems + accompaniment + mastered Song Harbor export.
- Transient: dry/percussive onset, slowed onset after processing, intentionally soft pad, cymbal, saturated kick, hard-gated layer.
- Reverb: natural room/long hall, designed freeze/shimmer, gated tail, actual unintended cutoff/stall after render.
- Stereo: in-phase, deliberate Haas widening, antiphase, intentional moving pan, collapsed mix after processing.
- Spectral: pitched synth resonance, industrial harmonics, cymbal noise, vocal sibilants, resampling/codec artifacts.
- Vocal: breaths, formant changes, harmonies and lead/backing bleed; require real annotations before measuring any phoneme coherence.
- Codec: original WAV, lossless resampling 44.1/48/24 kHz, MP3/AAC where rights/tools allow; include stage-relative timing offsets.

Separate labels:
1. acoustic event present (objective);
2. audible objectionability (blind/listener confirmed);
3. source or processing stage responsible (supported by A/B);
4. eligible reversible repair (only after verified).

For each category report precision, recall, localization MAE/p95, negative-case FP rate, and confidence interval when sample size supports it. Show raw counts and denominator; aggregate AI-origin percentage is prohibited.

## Stage 3: validate/revise detector priorities
Implement independent, CPU bounded acoustic detectors in this order **after test controls prove they can separate conditions**:
1. Reverb-tail discontinuity/stall: segment envelope, identify candidate transitions, distinguish silence and purposeful gate where feasible, return observable timestamp and evidence. The synthetic hard cutoff and intentional gate are intentionally identical audio, so no algorithm can infer intent without context.
2. Stereo phase/width instability vs intentional motion: per-window mid-side power, correlation, mono fold-down loss, original-current deltas.
3. Harmonic/noise residual inconsistencies: time-frequency analysis with tonal and distorted synthesizer controls; avoid blanket high-frequency suppression.
4. Vocal breath/formant/phrase diagnostics only after manually annotated source-level corpus exists.

For every method: isolated unit tests, positives, confound negatives, deterministic timestamps, bounded CPU/memory, mono and stereo, silence, short buffers, NaN/invalid input, no PCM mutation, no auto repair; then integrate into the existing single Sound cleanup & forensics entry point. Keep existing findings visible but marked stale after edits, and the Accept/Discard buttons reachable.

## Stage 4: **SEPARATE** fingerprint/provenance research
- `lofcz/ai-music-detector` MIT-licensed code/model research: independently verify exact license coverage of weight files, ONNX model hashes, accepted 16kHz preprocessing/residual-spectrum/CQT pipeline and supported Suno/Udio generations; do not assume claims generalize to ACE, YuE2, hybrids or mastered music.
- `lcrosvila/ai-music-detection`: use robustness evaluation ideas (resampling, filtering, codec/noise, source holdouts) as a protocol; verify repo, model, dataset licenses before copying or distributing assets.
- `KillrBee/ai-music-detector`: use concepts/algorithms as independent ideas; rights require verification before copying code. Its global AI-origin score must never be the audio-quality metric.
- Log generator/model, training coverage, actual corpus composition, per-class precision/recall, sample-rate and codec effects, false positives on industrial/synth controls, and version/hash. No provenance/watermark stripping or optimization to evade classifiers.
- No mandatory resident model or GPU for normal Song Harbor use; bench optional/offline, isolated process. Keep fingerprints out of audible repair suggestions.

## Release and handoff acceptance
A. TypeScript/Vite build green on exact SHA; Windows single-server launch succeeds.
B. Node synthetic tests pass and JSON report is retained; categorize detector false positives honestly.
C. Real music tests include blind A/B and stage/source-localization evidence before claiming an audible defect.
D. Audio export parity and non-destructive/undo confirmed for any later repair.
E. CI green or explicitly NOT VERIFIED; no unauthorized model weights or dataset distribution.
F. Document changes, failures and reproducible audio fixture derivation in repo; commit on main, no unsolicited UI expansion.

## Expected agent deliverables
- `docs/artifact-validation-results-<date>.md`: SHA, OS/Node/Python version, exact commands, CI status, tests passed/failed, processing wall time/peak memory, per-category metrics, reproducible failures and decisions.
- `docs/artifact-real-corpus-manifest-<date>.md`: non-sensitive metadata only; local media paths stay local.
- Method-specific algorithm+unit tests for any validated detector changes, separately from fingerprint bench reports.
- Update `refs/handoffs/currentHandoff.md` at end, preserving the 2026-10-26 historical decision.
