# Acoustic forensics: reverb-tail envelope diagnostic (2026-10-27)

## Scope

`app/frontend/src/ReverbTailDiagnostic.ts` measures rendered envelope behavior. It reports either a decaying envelope that ends abruptly or a decay that settles into an unusually flat level. It does not identify a generator, infer artistic intent, or modify audio.

The method computes across-channel RMS in 10 ms frames. A cutoff requires a decaying 200 ms lead-in followed by at least 100 ms near silence. A stall requires a decaying lead-in followed by at least 800 ms of low-variance level. Work is linear in PCM length with a small fixed per-frame lookahead; no model, GPU, network request, or additional UI is used.

## Interpretation boundary

The synthetic hard cutoff and intentional gated-reverb controls contain identical PCM. The method correctly returns identical observations for them. Therefore a returned cutoff is acoustic evidence only; source/effect-return comparison and listening are required to decide whether it is unwanted. The existing review pipeline labels this ambiguity and proposes no repair.

Held instruments, freeze effects, noise beds, compressors, gates and sound design can confound either observation. The method has not been calibrated on real music.

## Synthetic verification

At implementation commit `871003dfccec153623aa70e3eac847632f872b5e`:

- Natural exponential decay: no observation.
- Hard cutoff at 1.150 s: cutoff at 1.150 s.
- Stall beginning at 0.800 s: stall at 0.770 s (30 ms absolute error).
- Intentional gate: one false positive, identical to the hard-cut observation.
- Silence, steady tone, short buffer, invalid metadata and NaN PCM: no observation.
- Mono/stereo-safe RMS and PCM immutability are covered by the fixture and unit tests.

The four-case benchmark has TP 2, FP 1, FN 0, precision 0.667, recall 1.0 and negative-case false-positive rate 1/2 (50%). Localization MAE is 15 ms and p95 is 30 ms over only two matched events. These small synthetic counts do not establish field accuracy or audibility.

## Acceptance still required

Use rights-cleared natural rooms, halls, designed gates/freezes, held instruments and actual render cutoff/stall examples. Annotate acoustic presence separately from objectionability, responsible stage and repair eligibility. Any later fix must remain preview-only until explicitly accepted and export parity is confirmed.
