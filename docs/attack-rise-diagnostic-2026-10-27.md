# Acoustic forensics: isolated attack-rise diagnostic (2026-10-27)

## Scope and evidence
Implemented in `app/frontend/src/AttackRiseDiagnostic.ts`; surfaced as `attack_rise` in the existing `AudioCleanupAnalyzer` findings. This is an independent envelope method motivated by the KillrBee exploration, not reused repository code or a reproduction of a trained detector. It does not identify AI generators, watermarking, provenance, or mixing defects.

RMS is computed separately across channel power (no stereo cancellation) in approximately 2 ms frames with three-frame smoothing. The scanner looks for isolated local maxima with at least 10 ms of quiet pre-onset, measures the first 10%-90% RMS threshold crossing in the preceding 150 ms, and reports candidate rises of 35-140 ms. Per-track results are limited to six, and findings share normal analyzer limits. No external model, GPU, network call, PCM mutation, or new UI surface is required.

## Interpretation
A gradual isolated attack is **not inherently a defect**. It can come from a softened percussion attack, bowed strings, cymbals, synth envelopes, compression or creative fades. The finding requires manual source/stem comparison. No automatic correction is connected. The old `transient` finding instead concerns abrupt sample discontinuities.

## Verification
Seven synthetic unit tests for the detector were executed locally under Node 22 and passed. They cover slow attack, sharp attack, silence, sustained tone, deliberately distorted bass, antiphase stereo, and PCM immutability. Two integration assertions were added to the existing analyzer tests for the timestamped finding and sharp attack control. End-to-end frontend build, Windows listening QA, WAV export parity, and real-music false-positive testing are not yet verified here.

## Acceptance limitations and next steps
1. Verify frontend CI and existing analyzer tests against main, then listen to a selected positive in the existing UI.
2. Add labeled real percussion and separation-artifact examples plus negative controls for cymbals, bowed/soft-pad attacks, intentionally gated industrial music, spatial reverbs, and mastered compression. Count false positives by source category; this slice must not be treated as a calibrated defect detector.
3. Compare isolated-stem against final-mix attack shape before offering any **opt-in**, reversible transient repair. The existing UI must preserve stale scan findings across mix edits.
4. Keep separate bench reports for lofcz fakeprints and lcrosvila robustness; never optimize a provenance or watermark detector score as a sound-quality target.
