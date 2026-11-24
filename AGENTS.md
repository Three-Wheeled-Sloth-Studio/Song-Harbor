# Song Harbor agent instructions

## Source of truth

- Follow the installed `tws-development-standards` skill for shared TWS development, UX, batch processing, local-first integration and QA practices. If the skill is unavailable, inspect the repository's design references and ask about consequential policy conflicts.
- This file records Song Harbor-specific rules. Read `README.md`, `refs/handoffs/currentHandoff.md`, `refs/architecture/overview.md`, and relevant feature documentation before changing an affected subsystem. Handoffs contain historical entries and may include obsolete branch directions; the active branch policy below takes precedence.

## Branches and delivery

- **Develop on `dev` only. Do not create feature branches.** Inspect the remote `dev` head and local changes before editing. Preserve unrelated user work.
- **Do not modify or promote `main` without explicit user QA approval.** Do not push around permission restrictions or protected workflows.
- Keep implementation, tests, and documentation synchronized. Deliver results in chat or the repository, not downloads unless requested.

## Architecture and runtime

- This is a local-first, non-destructive, single-server music production workbench. The app owns project and arrangement state; external models are replaceable adapters.
- `app/backend/`: Python FastAPI services, audio/model adapters and project persistence. `app/frontend/src/`: React/TypeScript UI and shared-clock Web Audio workflow. `app/frontend/tests/` and `app/backend/tests/`: focused regression tests.
- Reuse the existing source-track identity, stem version, candidate preview, section scripting, accept/undo and 24-bit WAV export contracts. Keep original media immutable; do not silently replace sources or generate extra tracks when accepting a version.
- Use shared components from TWS-UI and the canonical TWS Design Principles. Keep the Tools UI compact, icon-first and contextual. Errors must say **ERROR:** and indicate whether the stem/project was updated.
- Discover installation paths and optional models; do not hard-code drives or require manual CLI work for routine user operations. Avoid reinstalling working CUDA/model environments.
- Preserve split L/R stem semantics, section/lyric author intent, protected automation and stereo/mix quality. Musical humanization is desirable when controlled, reversible and auditionable.

## Launch and checks

- Windows normal launcher: `scripts/launch-song-harbor.bat`; development launcher: `scripts/launch-song-harbor-dev.bat`. Bootstrap: `scripts/bootstrap-windows.bat`. Launchers should discover source and runtime locations.
- Frontend build: `npm install --prefix app/frontend` followed by `npm run build --prefix app/frontend`.
- Relevant frontend regressions: see `.github/workflows/frontend-build.yml` and `app/frontend/tests/`. Backend suite: see `.github/workflows/projects-tests.yml` and `app/backend/tests/`. Windows script syntax: `.github/workflows/launcher-syntax.yml`.
- Verify with scoped tests first, then applicable full checks. Never report Windows launch, GPU processing, listening quality or mix/export parity as tested unless actually verified on the relevant system.
- Audio diagnostic findings are hypotheses, not proof of a watermark, AI origin or an audible defect. Require controlled comparisons and listening before automatic correction.

## Workflow-friction checkpoint

- For any per-stem, per-section, or per-asset operation, assess an **All** action with total/current progress, safe cancellation, per-item errors and retry.
- Keep candidates reviewable with Original/Current/Fix comparisons and explicit Accept/Discard. An all-items run must not automatically accept quality-changing modifications.
- Preserve the active project, selected item, and tool state when installing, refreshing, accepting or recovering from an error.
- Record QA limitations and next steps in `refs/` or feature docs before handing off.
