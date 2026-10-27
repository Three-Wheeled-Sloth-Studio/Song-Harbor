# Frontend build verification gate (2026-10-27)

## Why this exists
Two consecutive source-checkout launches failed at TypeScript compilation, first in `CorrectionWorkbench.tsx` (unclosed JSX conditional), then in `SharedClockAudition.ts` (TypedArray backing-buffer type mismatch). The launcher correctly aborts on failure; the release process failed by treating direct-to-main edits as complete before build results had been verified.

## Gate for every frontend change
1. Before declaring a direct-to-main implementation done, run `npm install --prefix app/frontend` (when dependencies are not already present) and `npm run build --prefix app/frontend`. The latter includes `tsc --noEmit` and the Vite bundle.
2. Run `node --experimental-strip-types --test app/frontend/tests/audio-cleanup.test.mjs app/frontend/tests/attack-rise.test.mjs` for acoustic diagnostic changes. Run applicable feature tests for other changes.
3. Inspect the **Frontend build** GitHub Actions run for the resulting commit on `main`, not an older successful commit. The workflow now runs both cleanup and attack-rise tests. Confirm **Single-server launch smoke** on Windows for modifications affecting the app startup or audio runtime.
4. For GitHub-only edits without a working local checkout, **never** claim build verified solely because the commit API succeeded. Mark the commit as *pending CI validation* and check the workflow result. A failure requires correction before sign-off.
5. Windows audition, live audio playback and rendered WAV export parity are separate hands-on acceptance checks; CI compilation does not prove audio quality.

## Operational constraint
Direct commits to `main` are an explicit project choice. A GitHub Actions workflow triggers *after* push; it cannot prevent an unbuildable commit from landing on an unprotected `main`. A true mandatory pre-merge gate requires branch protection/rulesets and PR-based integration, or validated local pre-push checks in the writer environment. Do not label the existing post-push CI as a hard push-blocking gate.

## What to report per implementation
- Commit SHA and paths changed.
- Local typecheck/build result (PASS / FAIL / NOT RUN).
- GitHub CI run status for that exact SHA (PASS / FAIL / PENDING / NOT AVAILABLE).
- Relevant unit/regression test result.
- Windows UI/listening/export status, kept separate.

## Relevant workflows
- `.github/workflows/frontend-build.yml`: Ubuntu Node 22 typecheck + bundle, acoustic tests, Chromium UI smoke.
- `.github/workflows/single-server-smoke.yml`: Windows Node 22 build + real FastAPI UI/API smoke.

If CI is pending, do not ask the tester to rely on an unverified update as a known-good build.
