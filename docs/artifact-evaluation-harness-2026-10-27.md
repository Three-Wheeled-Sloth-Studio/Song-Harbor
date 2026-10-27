# Audible artifact benchmark harness (2026-10-27)

## Scope
**This harness evaluates audible-acoustic observations, not generator fingerprints.** It exercises the isolated attack-rise and reverb-tail envelope diagnostics. Benchmark labels refer to physical envelope fixtures and intent, never an "AI"/"human" class. No audio modification or repair is executed.

## Code
- `app/frontend/tests/artifact-evaluation.mjs` provides timestamp-based one-to-one event matching and aggregate metrics.
- `app/frontend/tests/artifact-fixtures.mjs` defines deterministic 24 kHz, two-channel synthetic signals with annotated positive events and negative controls.
- `app/frontend/tests/run-artifact-benchmark.mjs` runs the production `inspectAttackRise` algorithm against the fixtures and prints versioned JSON.
- `app/frontend/tests/run-reverb-tail-benchmark.mjs` separately scores cutoff/stall observations and preserves the intentional-gate false positive.
- `app/frontend/tests/reverb-tail.test.mjs` covers localization, confounds, silence, steady/short/invalid input and PCM immutability.
- `app/frontend/tests/artifact-evaluation.test.mjs` verifies matching logic, duplicate suppression in scores, localization bounds, negative-case false-positive accounting, undefined metric handling, deterministic fixture construction and report shape.
- `.github/workflows/frontend-build.yml` executes the benchmark and retains `artifact-benchmark.json` as a workflow artifact for 30 days. It separately runs existing audio cleanup and attack-rise tests.

## Run
From repository root with Node 22+:

```sh
node --experimental-strip-types --test app/frontend/tests/artifact-evaluation.test.mjs
node --experimental-strip-types app/frontend/tests/run-artifact-benchmark.mjs > artifact-benchmark.json
node --experimental-strip-types app/frontend/tests/run-reverb-tail-benchmark.mjs > reverb-tail-benchmark.json
npm run build --prefix app/frontend
```

Do not commit generated benchmark JSON unless explicitly curating a baseline. The JSON is a reproducible CI output, not evidence of field validation.

## Report interpretation
- True positive: one observation matched one annotated event within 50 ms (default). Multiple observations for one event are counted as extra false positives.
- False positive: observation with no matching annotated event, including in explicitly negative-control recordings.
- False negative: annotated event with no matching observation.
- Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 = 2TP/(2TP+FP+FN). Undefined ratios are null, not 100%.
- Negative-case false-positive rate = fraction of negative **cases** with one or more unmatched observations. This is distinct from event-level precision and should be segmented by control category.
- Localization errors are absolute seconds for matched events. The report stores per-case values so percentile statistics can be computed later.

## Dataset v1 boundaries
Positive controls: synthetic isolated ~85 ms attacks in aligned and antiphase stereo. Negative controls: sharp onset, intentional industrial distortion, silence, steady tone, deliberate soft-pad attack, bright cymbal-like burst, and spatial/reverberant tail. The soft-pad negative may trigger the current method; that is a useful exposed limitation rather than a test to suppress.

Synthetic data does not establish audibility, artifact cause, source attribution, real-world precision, or acceptable repair. Do **not** declare a release-quality detector on these results. Current onsets are represented with approximate timing and do not have third-party listener annotations.

## Next evaluation slices
1. Add curated original/acoustic and generated/remixed/separated examples with source provenance, licenses, test annotations and clear rights to store/use.
2. Compare each source against intermediate stages and exported output, while preserving original/current/fix and the existing single compact UI.
3. Evaluate by instrument/source family (percussion vs soft synth vs vocals), effect types (distortion, reverb), sections and codecs; measure recall, precision, localization error distribution and per-category false-positive rate.
4. Add new acoustic methods (reverb-tail discontinuities, phase changes, harmonic/noise anomalies) with their own annotated fixtures.
5. Keep lofcz ONNX/CQT fakeprints and lcrosvila-style generator robustness under a **separate research protocol**, with model metadata and provenance retained; never optimize generator identification scores as an audio quality metric.

## Verification
Local Windows build and synthetic tests passed for implementation SHA `871003dfccec153623aa70e3eac847632f872b5e`; exact results are in `docs/artifact-validation-results-2026-10-27.md`. GitHub CI, Windows audio QA and listening remain separately reported rather than inferred.
