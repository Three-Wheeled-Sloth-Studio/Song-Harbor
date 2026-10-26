# Discovery: AI music fingerprints versus actionable sound quality
Date: 2026-10-23
Status: Research only. No production code, detector model, or repair rule adopted.

## Purpose
Compare three external AI music detection projects for *source-to-output quality
regression*, audible artifact localization, and more natural musical production.
Keep legitimate provenance and disclosure intact. An AI classifier output is
neither an audio-quality score nor proof that any identified feature is audible.

## Projects inspected

1. https://github.com/KillrBee/ai-music-detector
   - Python/FastAPI seven analysis domains: spectral, spatial, production,
     temporal, structural, vocal, optional watermark. Frequency rolloff,
     HF harmonic-to-noise patterns, flux, transient attacks, phase/low-bass
     width, loudness range, reverb-tail consistency, breath/formant checks.
   - Strong *idea source for interpretable artifact diagnostics*.
   - The overall AI score uses handcrafted heuristic weights and thresholds.
     README says some tiers were tuned on a 22-track sample (10 human,
     12 generated); spectral code itself documents large human overlap.
     Do not present that score as a calibrated AI probability or a standard.
   - Watermark implementation uses optional AudioSeal detector and is off by
     default. AudioSeal only recognizes compatible marks; a negative result
     DOES NOT prove absence of other watermark systems or provenance.
     No removal or suppression workflow proposed.
   - No top-level LICENSE found in inspected default branch; do not copy code
     without confirming rights/permissions.

2. https://github.com/lofcz/ai-music-detector
   - MIT-licensed. Spectral fakeprint method derives a residual average
     spectrum and identifies vocoder upsampling architecture patterns;
     includes ONNX models, Python, C# and CQT/CNN alternate path.
   - README scope Suno <=5 and Udio <=1.5; claimed 99.88% accuracy on
     17,866 held-out examples (5,741 real, 12,125 AI). Training-specific
     metric, not validated on ACE-Step 1.5, YuE2 or postprocessed hybrids.
   - Model config specifies 16 kHz / 1-8 kHz analysis, and 10+ second
     preferred duration; ensure correct resampling and preprocessing if
     evaluating. C# extractor has different default parameters: inspect
     model metadata rather than assuming arbitrary defaults match weights.
   - Not a perceptual quality measure. Highly characteristic generator
     patterns can be inaudible; global spectrum obscures time-local faults.
   - Follow paper: Afchar et al., A Fourier Explanation of AI-music
     Artifacts (ISMIR 2025), https://arxiv.org/abs/2506.19108 .

3. https://github.com/lcrosvila/ai-music-detection
   - Official research implementation for Cros Vila et al., The AI Music
     Arms Race: On the Detection of AI-Generated Music (TISMIR 2025).
     Embedding-based SVM/RF/kNN hierarchical AI/source classifiers,
     Essentia features, CLAP, tests across sample rates, filtering/noise.
   - Research involved 30,000 tracks (20k AI, 10k commercial) and exposes
     problems with detector robustness under audio manipulations.
   - Valuable for robust evaluation protocol and confound controls; too
     heavy and task-mismatched for an always-running Song Harbor scan.
   - No top-level LICENSE found in default branch; do not copy code or
     trained artifacts without verifying permissions. Dataset access is
     not turnkey; README has TODO for prepared download.

## Important interpretation rules

- Distinguish (a) embedded provenance/watermarks, (b) generator architecture
  signatures, (c) audible degradations, and (d) normal artistic choices.
- Never represent missing AudioSeal detection as proof there is no watermark.
  Do not design provenance-stripping or detector-score minimization.
- A score delta after editing is not sound quality improvement; codecs,
  EQ, limiting, resampling, and musical genre can shift classifier outputs.
- Preserve legitimate generator disclosures and source/provenance records.
- Do not auto-clean all spectral peaks: harmonics may be desired synth/guitar
  content, and targeted notches can damage arrangement, clarity or timbre.
- Keep analysis off the real-time audio thread; scan full offline exports,
  individual stems, and source-master pairs as available.
- Raw analytic confidence and listening confidence must be separate.

## Highest-value Song Harbor features (incremental)

P1: *Stage-by-stage audio QA*: run existing QC on generated source,
  YuE2 remix, separated/recombined mix, processed export. Measure
  source->output: peak/true peak, LUFS/LRA, clipped flat-top samples,
  tail truncation, spectral-band gain, unusual tonal spur/bandwidth changes,
  phase/mono loss, transient attack alteration and section timing drift.
  Include channel/stem references, time ranges and difference estimates.
  If introduced in export, flag the exact processing stage. No blanket
  AI probability displayed.
P1: *Localize and audition*: flag timestamps or time-frequency regions,
  solo/mute candidate cleanup with loudness-matched original vs repaired,
  accept/revert via existing non-destructive production instructions.
  Useful repairs: conservative isolated de-click, clipped-onset guard,
  transient recovery, sibilance tuning, phase/mono compatibility, reverb
  tail continuity, targeted EQ. Warn where source attribution is uncertain.
P2: *Optional offline forensic model bench*: test lofcz ONNX on a
  representative controlled corpus (Suno, YuE2, ACE, hybrids, acoustically
  recorded human, manually processed synth/electronic music). Record
  model/version, resampler/codec, false positives, and sensitivity to
  source/edit chain. Show experimental model evidence only if useful.
P2: *Musical realism suggestions* on separated stems: phrase/breath
  consistency in lead vocals, automation over-stability, abrupt timbre
  discontinuities, articulations and timing that sound mechanically
  repetitive. Human performance is not simply random jitter; never
  add random timing/noise as a default 'humanize' operation.

## Suggested experiment (before any code adaptation)

- Capture original generated full mix and current Song Harbor output
  plus exported separated source stems for The Logo and the Maw.
- Reuse existing Song Harbor post-effects scan. Add one offline diff
  report for isolated objective faults: transient damage, audible
  aliasing/harsh bands, output reverb cutoff, phase/mono collapse.
- Blind, level-match and compare targeted small repairs with the
  untouched approved final mix. Reject cleanup that reduces musical impact.
- Separately benchmark the MIT ONNX detector as a *research instrument*,
  never as a release gate. Compare results on controlled generated and
  human recordings before claiming generalization.
- No long-term inference models or large data caches in the MVP.

## Go/no-go
**Go:** interpretability of signal-level QA, source-output regressions,
localizable defects, user-auditioned reversible repairs.
**Conditional:** independent MIT forensic benchmark (no score optimization).
**No-go:** universal 'human score', watermark suppression, indiscriminate
filtering of spectral signatures, opaque self-validating auto fixes.

References:
- https://github.com/KillrBee/ai-music-detector
- https://github.com/lofcz/ai-music-detector
- https://github.com/lcrosvila/ai-music-detection
- https://arxiv.org/abs/2506.19108
- https://doi.org/10.5334/tismir.254
- Additional primary research implementation: https://github.com/deezer/ismir25-ai-music-detector

## Experimental in-app tool (2026-10-23)

A separate **⌁ Audio forensics (experimental)** icon is now available in the
right-hand tool palette. It opens a compact inspector, sharing the already
implemented on-demand `SharedClockAudition.analyzeMix()` scan. Results are
organized into spectral texture (sibilance/harshness/fizz/noise/persistent
signal), transient/dynamics, stereo/mono, and peak integrity. Each finding
supports seek and audible region looping. Scanning processes the actual
rendered current mix and does not create/edit WAV files.

**Resource footprint:** No new model runtime, GPU, web service or Python
dependency. It invokes the same offline render and CPU FFT analysis that
Sound Cleanup already provides; opening the panel alone does not run the scan.
The full offline render may temporarily require substantial memory on longer
songs, so this first experiment still inherits the normal mixer limits.

**Boundary:** This is an *experimental diagnostic view*, not yet an
independent fingerprint model, source/output comparison, or cleaner. It
intentionally shares findings with Sound Cleanup until signal relevance,
performance and presentation have been assessed. Fold proven measures into
the general analyzer and retire the separate panel once mature. No
fingerprint avoidance optimization or watermark-removal feature.


## 2026-10-26 development course correction

The subsequent cleanup implementation (`AudioCleanupAnalyzer`, `SignalAudit`, per-stem evidence, de-click, EQ/de-ess and three-way audition) **has not implemented the distinctive research algorithms summarized in this discovery**. This difference was explicitly raised by the user and acknowledged. The next research/development pass should directly inspect KillrBee, lofcz, and lcrosvila, capture exact model and licensing constraints, design controlled validation, and implement audibly actionable feature detectors first. See `refs/handoffs/currentHandoff.md` and the last section of `docs/artifact-fingerprint-cleanup-roadmap-2026-10-26.md`. Keep fingerprints and generator provenance separate from audible quality and optional repair.
