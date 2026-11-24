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

## Next implementation slices

1. **Analyze all**: inventory analysis functions that operate on selected stems/sections, and expose clear whole-project commands with consolidated progress and findings. Preserve per-item drilldown. Do not mislabel an existing whole-mix analyzer as stem-by-stem analysis.
2. **Batch review**: reusable queue/status component, persistent batch run history, retry failures, review-next, optional selective accept-all after an explicit confirmation and safety checks.
3. **Source integrity report**: read-only metadata/container inventory, spectral anomaly detection, periodic/tonal candidates, transient condition, stereo phase/coherence and noise/residual observations. Findings must identify heuristic confidence and distinguish observed anomaly from proven watermark.
4. **Musical humanization**: reversible, source-aware microtiming, velocity/expression, dynamics and stereo motion, preferentially operating on editable MIDI or section automation. Respect author intent, tempo map, protected passages and channel-split constraints. Do not randomly perturb a final master as a default.
5. **Controlled comparison**: original generated source, Song Harbor production output and conventional reference; level-matched blind audition, spectral/transient/stereo measurements, objective metadata checks. Detector scores are exploratory, not proof of provenance removal.

## External references

- https://github.com/geeknik/ai-audio-fingerprint-remover (archived MIT, deprecated)
- https://github.com/geeknik/mmm (archived CC0 successor)

Use MMM only in a separate local test environment as a diagnostic comparator. Its re-encoding and spectral perturbation are incompatible with transparent archival/master-quality processing as defaults. Do not promise removal of hidden watermarks or AI-origin classification signatures.
