# Artifact validation results (2026-10-27)

## Reproducibility

- Starting branch/SHA: clean `main` at `b1e2563f4d57b720b85091eaa51707b42d573536`.
- Validated implementation SHA: `871003dfccec153623aa70e3eac847632f872b5e`.
- Host: Microsoft Windows 11 Home 10.0.26200 build 26200; PowerShell 7.6.7; Node 22.15.0; npm 10.9.2; Python 3.12.9.
- No song media, project database, source WAV or exported WAV was modified.

Commands run from repository root:

```powershell
pwsh -File scripts/verify-artifact-suite.ps1
pwsh -File scripts/verify-artifact-suite.ps1 -SkipInstall
node --experimental-strip-types app/frontend/tests/run-artifact-benchmark.mjs
node --experimental-strip-types app/frontend/tests/run-reverb-tail-benchmark.mjs
```

The initial prescribed run installed 115 packages with zero reported vulnerabilities. The post-change `-SkipInstall` run completed in 6.214 seconds and peaked at approximately 408.6 MiB working set across the wrapper and descendant processes, sampled every 100 ms. This is a coarse process-tree measurement, not a platform-independent memory benchmark.

## Build and tests

- TypeScript `tsc --noEmit`: PASS.
- Vite production bundle: PASS; 162 modules, JS 561.13 kB / 175.55 kB gzip. The existing >500 kB chunk warning remains informational.
- Acoustic, evaluator and planned-fixture tests: PASS, 45/45.
- Windows live playback/listening: NOT RUN.
- Offline exported-WAV parity and Accept/Discard: NOT RUN; no repair exists in this slice.
- Real-music evaluation: NOT RUN; no rights-cleared annotated corpus is present.

## Synthetic benchmark results

| Method | Cases | TP | FP | FN | Precision | Recall | Negative-case FP rate | Localization MAE / p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Attack rise RMS v1 | 9 | 2 | 1 | 0 | 0.667 | 1.000 | 1/7 (14.29%) | 2 / 2 ms |
| Reverb-tail envelope v1 | 4 | 2 | 1 | 0 | 0.667 | 1.000 | 1/2 (50.00%) | 15 / 30 ms |

Attack-rise's false positive is the intentional soft-pad envelope. Reverb-tail's false positive is the intentional gated reverb, whose PCM is byte-identical to the annotated hard cutoff. Neither should be hidden or relabeled: the first shows that a numeric rise can be intentional, while the second proves intent is not inferable from the waveform alone.

Repeated attack-rise JSON was byte-identical with SHA-256 `2674AC7CD768827919CA1EEF1541A85CA81F8A62BE73F20FB66DE093AA9F82BD`. Repeated reverb-tail JSON was byte-identical with SHA-256 `6EF6CBDB07DDC3850CB2CA10F17CF77B447CD4CEE84B5D6CBA50EE8F848BD9A4`. Reports are retained under `$env:TEMP/song-harbor-artifact-qa/` and are not committed as field-validation evidence.

## CI and decisions

For the starting SHA, GitHub exposed no check runs, so Frontend build and Single-server launch smoke were NOT VERIFIED. For implementation SHA `871003dfccec153623aa70e3eac847632f872b5e`, all required checks passed:

- [Frontend build](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/runs/40575198555): PASS, including typecheck/bundle, acoustic tests, both benchmark artifacts and Chromium smoke against Vite and the real FastAPI server.
- [Single-server launch smoke](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/runs/40575198464): PASS on Windows.
- [Windows launcher syntax](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/runs/40575198390): PASS.

The Frontend build emitted informational runner/action migration annotations; they did not fail a step.

The reverb-tail method was integrated into the existing Sound cleanup & forensics finding pipeline only. It creates review evidence and no automatic or suggested audio processing. Fingerprint/provenance research remains separate and no external model weights or datasets were downloaded.

## Rights-cleared real-audio continuation

The user subsequently supplied local job `586a03b40c9c` as rights-cleared. `scripts/run-real-audio-diagnostics.mjs` now provides a read-only FFmpeg adapter to run the production analyzer on supplied files. It does not render the project, edit PCM or accept repairs.

The 341.360-second source, six equal-duration Demucs stems and the imported 10.683-second cello were scanned. The source produced a reverb-stall candidate at 30.570 seconds and multiple attack/dynamics/spectral review candidates. Bass and drums each hit the six-result reverb-tail cap on ordinary stem decays, showing that unannotated real music has substantial confounds and that raw finding counts cannot be treated as defect prevalence.

The clearest stage-relative result was the imported cello. Separation cleanup reduced attack-rise observations from 4 to 1 and pumping observations from 2 to 1, but introduced a cutoff-like observation at local 2.080 seconds (project time 73.799 seconds). The boundary did not have a click-sized sample jump. A separate audition-only preview blended 400 ms of the preserved raw crop at -24 dB; it removed the cutoff observation without changing integrated loudness or true peak, but necessarily reintroduced a small amount of raw material. It was not imported or accepted. Full evidence and the remaining listener requirement are in `docs/artifact-real-corpus-manifest-2026-10-27.md`.
