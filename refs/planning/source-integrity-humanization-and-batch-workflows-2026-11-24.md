# Source integrity, humanization and batch workflows

Status: implementation underway, 2026-11-24. Internal production workflow takes priority over external adoption or narrow feature scope.

## First implementation slice: Deshimmer batch

- Sound cleanup now offers **Optimize all stems** alongside single-stem optimization.
- Runs sequentially to honor the existing server's one-active-Deshimmer-job contract.
- Shows completed/total progress, current stem and each stem's stage or error.
- Keeps successful candidates for individual A/B review and explicit acceptance. Never silently replaces audio.
- Stop batch cancels the active candidate and marks unstarted work cancelled. Completed candidates remain reviewable.
- One stem failure does not abort the remaining queue.

QA on the actual Windows workstation is required: run 2-3 stems including a split stem, confirm progress through analyze/optimize/render, stop, recover from a failed stem, review candidates, accept and undo. Verify project state after reopening. Large-stem processing performance is not yet measured.

**User QA update (2026-11-24):** Optimize all stems works and gives a clear working animation. Pin for the next cleanup UX pass: a coarse overall progress indicator (ideally a filling ring around the existing animation), plus **Accept All**. Accept All must review the set of ready candidates, explicitly confirm replacements, skip failures/stale originals, show individual outcomes, and preserve undo/version history. This is not authorization to auto-accept generated candidates.

## Next implementation slices

1. **Analyze all**: inventory analysis functions that operate on selected stems/sections, and expose clear whole-project commands with consolidated progress and findings. Preserve per-item drilldown. Do not mislabel an existing whole-mix analyzer as stem-by-stem analysis.
2. **Batch review**: reusable queue/status component, persistent batch run history, retry failures, review-next, optional selective accept-all after an explicit confirmation and safety checks.
3. **Source integrity report**: read-only metadata/container inventory, spectral anomaly detection, periodic/tonal candidates, transient condition, stereo phase/coherence and noise/residual observations. Findings must identify heuristic confidence and distinguish observed anomaly from proven watermark.
4. **Musical humanization**: reversible, source-aware microtiming, velocity/expression, dynamics and stereo motion, preferentially operating on editable MIDI or section automation. Respect author intent, tempo map, protected passages and channel-split constraints. Do not randomly perturb a final master as a default.
5. **Controlled comparison**: original generated source, Song Harbor production output and conventional reference; level-matched blind audition, spectral/transient/stereo measurements, objective metadata checks. Detector scores are exploratory, not proof of provenance removal.

## Incremental source scanning (2026-11-24)

- **Scan all stems** is now available in the existing Sound cleanup panel alongside Analyze mix.
- Reuses each already-decoded raw source lane (including split lanes) and existing read-only acoustic heuristics. Analysis runs sequentially, reports completed/total, supports stop between stems, and groups timestamped observations under each source.
- Source timeline offsets are retained. No new rendering, candidate processing, sample modification, metadata stripping, or watermark-removal action is performed.
- Validation: frontend build and focused audio/signal/stem tests passed locally. Added `stem-integrity-scan.test.mjs` to CI. Windows UI performance, cancellation latency on long sources, and listening relevance remain unverified.
- Next: progress within long-stem scans, batch retry/report persistence, metadata/container inspection and stronger source-integrity measurements. Maintain strict distinction between source QC, model-origin research and audible repair.

## Source measurement pass (2026-11-24)

- Per-stem scan now reports source peak and RMS (dBFS), DC offset (% full-scale), and when stereo is active, L/R correlation and side-to-mid energy (dB).
- Measurements use bounded deterministic sampling, are read-only, and carry no claim of confirmed watermark, artificial generation, or quality defect.
- Controlled tests cover aligned versus inverted stereo, expected RMS/DC values, silence, invalid samples, and non-mutation. Full Windows UI listening and performance checks are still required.
- Next targeted investigation: temporal persistence of narrowband features and spectral stationarity with meaningful industrial/electronic negative controls. Metadata/container inspection remains an independent track.

## External references

- https://github.com/geeknik/ai-audio-fingerprint-remover (archived MIT, deprecated)
- https://github.com/geeknik/mmm (archived CC0 successor)

Use MMM only in a separate local test environment as a diagnostic comparator. Its re-encoding and spectral perturbation are incompatible with transparent archival/master-quality processing as defaults. Do not promise removal of hidden watermarks or AI-origin classification signatures.
