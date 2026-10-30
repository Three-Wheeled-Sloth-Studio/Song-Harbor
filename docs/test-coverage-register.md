# Song Harbor test coverage register (2026-10-30)

The goal is low-noise CI with **no silent loss of regression coverage**.

## Required on ordinary source edits

- Backend: `.github/workflows/projects-tests.yml` runs 42 Python unittest modules, each in an isolated process with GitHub log groups. This includes mocked ACE integration contracts, track routing, clip-duration validation, script roundtrip and effects, library, waveform, and generated stem import.
- Frontend: `.github/workflows/frontend-build.yml` runs 14 Node test files in one grouped command; this includes cleanup/analyzer diagnostics, waveform tools, split/replace masks, and audio effects, followed by Chromium rendering checks.
- Windows: `.github/workflows/single-server-smoke.yml` validates the real Windows build, runtime server, and asset serving. The launcher-syntax workflow tests PowerShell parsing and safe update behavior.

## Environment-dependent test

- `app/backend/tests/test_channel_roundtrip.py`: real FFmpeg + FFprobe stereo reconstruction fidelity test. Keep the fixture and assertion; skip unless both tools are available. Run independently on a properly configured audio-tool environment when testing audio export or channel-splitting changes. **Do not delete it or silently call it a redundant mock test.**

## Non-test fixture and benchmark helpers

- `app/frontend/tests/artifact-evaluation.mjs`, `artifact-fixtures.mjs`, `planned-artifact-fixtures.mjs`: support modules imported by the Node tests; not standalone `*.test.mjs` scripts.
- `app/frontend/tests/run-artifact-benchmark.mjs` and `run-reverb-tail-benchmark.mjs`: synthetic benchmark generators, run separately with artifacts retained.

## Duplication policy

One test should represent each behavior, not each implementation location. Shared helpers and overlapping assertions can be consolidated after inspecting expected coverage and failure modes. Do not remove tests based solely on similar filenames. The Chromium browser test and Windows smoke intentionally overlap in startup path, but check different operating systems and are both retained.

## CI hygiene

- Each workflow cancels earlier runs for the same branch and workflow.
- Backend and frontend unit suites are grouped for simpler logs, without dropping individual tests.
- No real ACE model or download is required on CI; ACE unit tests must continue to use mocks.
- A new test file must be added to a required suite or documented here as intentionally optional.
