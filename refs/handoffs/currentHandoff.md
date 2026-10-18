---
type: Handoff
title: Current Song Harbor Handoff
description: Discovery-phase baseline and next bounded implementation slice.
status: draft
tags: [handoff]
---
# Current Handoff

## Accepted Baseline

Song Harbor is the TWS Studios working title. A standalone local-first product must support stem/section-level music editing and generation, swappable models, plugins/LoRA/LoKr, remix/cover, imported-track reconstruction, and future optional training/cloud execution. Reference system RTX 4070 12 GB VRAM / 96 GB RAM. Infra Choir is a consumer, not co-brand. Accepted facts are in `refs/planning/decisions.yaml`. **SH-DEC-009 accepts generation-first comprehensive release sequencing, while SH-DEC-010 makes a self-contained stem separator the first functional deliverable.** Full mixed-song reconstruction and guided remix follow, rather than gate, the initial standalone generation-first release.

## What Landed

Product vision, requirements, architecture direction, decisions, open questions, structured roadmap and detailed implementation roadmap with discovery spikes, experiment goals, stage gates, fallback paths and proposed release milestones. Agent Academy foundation files were partially copied previously. The roadmap now explicitly orders standalone generation-first release before reconstruction/remix.

## Current Evidence Or Gap

Laptop Predator setup (2026-10-17) reached **environment validated, inference not yet attempted**. GTX 1660 Ti 6 GB, RAM 15.843 GiB, Windows build 10.0.26100, driver 572.47; Python 3.11.2 isolated in `G:\Apps\SongHarbor\.venv`; torch/torchaudio 2.6.0+cu126, torchvision 0.21.0+cu126, onnxruntime-gpu 1.24.4, audio-separator 0.47.0. Torch CUDA matrix multiplication succeeded and `audio-separator --env_info` detected Torch CUDA, ONNX CUDA provider, and FFmpeg 4.2.3. Pip initially upgraded torch to CPU-only 2.14.1; compatible CUDA packages restored with --no-deps. Missing ONNX Runtime was corrected by installing onnxruntime-gpu. Default model directory is /tmp/audio-separator-models/ and needs explicit G: override. Final pip check was not supplied. No model download or stem separation performed.

The user is moving to the **primary desktop**. Its previously reported RTX 4070 12 GB and 96 GB RAM are pending direct verification. Three-machine benchmark process is captured in `refs/testing/stemSeparationBenchmark.md`. No product runtime exists; full Agent Academy initialized-mode validation still pending.

## Active Test Model

User selected **Demucs six-stem `htdemucs_6s.yaml` as the current benchmark baseline** after a successful 30-second desktop run (9.046711 s) and listening check. Vocals/percussion clean; some guitar-versus-Other bleed acceptable. Prioritize full-song test and sustained performance with this model. Four-stem Demucs and two-stem VR remain comparators. Not a final shipping decision; verify weights licensing and full track resources.

## M0 UI Implementation Checkpoint (2026-10-17)

Reviewed canonical `TWS-Design-Principles/apps/App-Design-Principles.md`, `apps/Studio-UI-Style-Guide.md`, `apps/Fullscreen-Workspace-Interaction-Standards.md` and shared `TWS-UI` API. Implemented initial local vertical slice under `app/`: FastAPI service using the validated virtualenv's `audio-separator.exe`, fixed six-stem Demucs, one-job queue, status/error/logs, cancellation, download and open-output-folder, plus React entry screen importing shared `@tws-ui/core/react` controls. `app/run.ps1` launches local service and dev UI. `.gitignore` excludes models, audio, venv, runtime data and build artifacts. Follow `app/README.md` for installation and acceptance. **Not yet smoke-tested end-to-end** on user's Windows workstation; do not check off the milestone until UI works on the actual machine. No packaged standalone binary yet. User's working `D:\Apps\SongHarbor` already contains models and venv: clone source to a subdirectory or integrate git carefully rather than overwriting existing local assets.

## Multi-machine Bootstrap (2026-10-17)

The previous primary development machine is confirmed as **PC Skynet** (RTX 4070 / 96 GB), and the third laptop is named **Laptop Omen** (hardware inventory pending). A reusable Windows setup script has been added at `scripts/bootstrap-windows.ps1`. It pins torch, torchvision, torchaudio to CUDA 12.6-compatible 2.6.0 builds and ONNX Runtime GPU to 1.24.4, uses an isolated user-chosen work drive, checks GPU/FFmpeg/Python/npm, installs `audio-separator[gpu]==0.47.0`, downloads `htdemucs_6s.yaml`, and installs/builds the M0 UI. Script committed but **not yet exercised on Laptop Omen**; run it and diagnose any machine-specific issues. Avoid assuming its drive mapping, driver, Python, or memory match either prior machine.

## Laptop Omen Launchers (2026-10-17)

Added `scripts/bootstrap-windows.bat` and `scripts/launch-song-harbor.bat`, default work root `C:\\Apps\\SongHarbor`, since Omen has no other work drive. Both launch PowerShell 7 via `pwsh.exe` using repository-relative .ps1 paths; bootstrap launcher preserves errors in the console, and either accepts a root override as argument. C: placement is a deliberate machine constraint, not a change to preferred storage topology for other machines. Neither launcher has been tested on Omen yet.

## Laptop Omen M0 Acceptance (2026-10-17)

User confirmed **“Launcher works. Splitter works.”** on Laptop Omen using the C:-based bootstrap and GUI. The limited milestone of a working entry UI plus end-to-end six-stem separation is **user accepted**. Do not imply installer packaging or exhaustive QA is complete. Remaining deferred checks include specific output validation, error/cancel behavior, exact Omen system inventory, performance and an independent frontend build/test run.

## Open Regression: possible 4:00 truncation (2026-10-17)

User reports the splitter appears to cut off at exactly four minutes on longer content. This is **open and unverified**. Reviewed upstream Demucs/audio-separator: no inherent four-minute input ceiling; chunking is optional and default off. Prior backend only required six files, so could report a false success when truncated. Added source/stem `ffprobe` duration guard (0.25 s tolerance), exposing measured lengths and an actionable error, plus duration-regression tests. A guard is **not the underlying fix**. Diagnose on Laptop Omen by probing imported source and all six produced stems and checking latest job logs. Do not claim full-length (>4 minute) separation as accepted until reproduced and corrected.

## M1 In-app Stem Mixer (2026-10-17)

User prioritizes removing Audacity from ordinary stem audition and recombination. Implemented `app/frontend/src/StemMixer.tsx` and mixer styling; wired into completed six-stem jobs. Playback, seek, per-stem gain/mute/solo/reset, exported WAV download and local file-folder integration. Server has inline stem streaming and an FFmpeg six-input mixdown endpoint using validated existing stem filenames, proper gain/solo/mute, 24-bit WAV with limiter, atomic output replacement, source-duration validation, and concurrency guard. Added `app/backend/tests/test_mix_validation.py`. **Not yet user-tested or build-verified on Laptop Omen**; current M1 checkpoint is code complete pending smoke test. Preview synchronization uses individual browser MediaElements with drift correction, which is not sample-accurate; mixdown renders synchronized input stems using FFmpeg.

## Portable Launcher Fix (2026-10-18)

Regression discovered on **Laptop Predator**, where checkout is `G:\\Apps\\Song-Harbor` and validated virtual environment is `G:\\Apps\\SongHarbor\\.venv`. Old `scripts/launch-song-harbor.bat` hard-coded Omen's `C:\\Apps\\SongHarbor` and failed. Added `scripts/start-song-harbor.ps1` with explicit override/environment/sibling venv discovery and conditional bootstrap; changed BATs to use it instead of hard-coded drive. Missing UI-only dependencies are installed without reinstalling CUDA PyTorch. `scripts/bootstrap-windows.bat` now does install-only. Docs updated. **Not yet verified in runtime on Predator**; user's next step is git pull and relaunch to confirm correct resolved root and UI operation.

## FFmpeg Guided Recovery (2026-10-18)

Predator reported a completed UI upload failing with `ffprobe is required... install FFmpeg on PATH`. User requires applications to offer discovery, native folder selection, explicitly selected install destinations, installation assistance, validation and persistence of machine-specific tool locations rather than generic dependency errors. Added `app/backend/dependencies.py` with saved-path/PATH/common-folder resolution, opt-in bounded machine app-folder search, Windows native folder picker, SHA-256 verified official Gyan essentials ZIP download to an explicitly chosen empty location, verified FFmpeg/FFprobe pair, machine-local config file, and async install status. Added FastAPI setup endpoints, a recovery UI, change-path action, configured FFmpeg use in separation and export, and removed mandatory FFmpeg PATH check from bootstrap. Added dependency tests and excluded local config/managed binaries in .gitignore. Added the behavior as cross-project Principle 19 in TWS-Design-Principles. **Not smoke-tested on Predator**; test with no ffprobe on PATH and ensure setup works before marking accepted. The currently implemented setup is FFmpeg-specific; other system prerequisites are still bootstrap-validated.

## Contextual Dependency Recovery UX (2026-10-18)

The user's product-taste correction: the first FFmpeg setup implementation incorrectly occupied large persistent workspace area at launch, even when the user was not using the feature. Updated the canonical `TWS-Design-Principles/apps/App-Design-Principles.md` with sections 19–20 and `apps/Studio-UI-Style-Guide.md`: quiet upper-right header dependency count, never a startup takeover for feature-scoped tools, compact just-in-time modal only when an affected action is requested, preserve pending input and action, then resume upon recovery. Song Harbor now uses a shared TWS Dialog, removes persistent FFmpeg setup/status panels, keeps Separate enabled until invoked, and retries separation or mix export after successful configuration. Server health distinguishes `separator_ready` from combined readiness. **Committed; UI behavior pending local verification on Laptop Predator.**

## Next Slice

1. **Primary desktop first:** inventory Python installations, GPU/driver, FFmpeg, physical RAM and available storage. Ask for output, then select an isolated environment location. Do not copy Predator paths.
2. Verify CUDA Torch in the desktop environment; avoid letting audio-separator pip dependencies silently replace the selected CUDA build. Check `pip check`.
3. Install audio-separator and onnxruntime-gpu as needed; verify `--env_info`, configure a known model directory, then select a legally reviewable model for a short audio smoke test.
4. Later resume Predator at model-dir CLI inspection and a 2-stem short test. Compare same fixture across environments and keep provenance/performance separate.

## Required Reads For Next Slice

- `refs/planning/implementationRoadmap.md`: M0 separator gate and subsequent generation sequence.
- `refs/planning/stemSeparationDiscovery.md`: candidates, licensing and benchmark criteria.
- `refs/product/requirements.md`: required track, section and local capability outcomes.
- `refs/planning/decisions.yaml`: accepted boundaries versus proposals.
- `refs/planning/openQuestions.yaml`: unresolved technical and release decisions.
- `refs/README.md` and `refs/templatePolicy.yaml`: harness bootstrap and validation requirements.

## Relevant Files

`refs/planning/roadmap.yaml`, `refs/planning/todos.yaml`, `refs/architecture/overview.md`, `refs/project.yaml`.

## Do Not Reopen

Song Harbor working title/repo, TWS Studios ownership, Infra Choir brand independence, local-first/standalone, future-not-MVP cloud/training policy, and generation-first release sequence (SH-DEC-009), with separator first (SH-DEC-010).

## Validation

Documentation-only updates were pushed. No executable product tests or initialized Agent Academy generator/index validation was run. Do not declare full harness compliance before those checks pass.


### 2026-10-17 cutoff diagnostic update
User ran ffprobe on Laptop Omen's most recent job, `Salt in the Circuit`: imported `Salt in the Circuit.wav` was **exactly 240.000000 s** and each of the six Demucs 6s outputs was **exactly 240.000000 s**. This rules out *post-import separation-only* truncation in this job, but does not determine whether the user selected a naturally 4:00 file or whether upload/import changed a longer original. The 0.25 s stem-to-imported-source guard is insufficient to detect pre-separation truncation. Next: compare external selected original file with imported job file (ffprobe duration, byte count, SHA256), and if original is longer, audit browser upload and import handling.


### Follow-up: suspected Audacity timeline artifact (2026-10-17)
User withdrew the four-minute cutoff report after realizing a 4:00 song was previously imported into Audacity and the next song likely shared that timeline. The inspected Song Harbor job had source and all six stems at exactly 240 seconds. **No Song Harbor truncation has been demonstrated.** Reclassify this as a probable Audacity session/timeline issue rather than a confirmed application regression. Keep the new source-to-stem duration validation as useful defensive QA; it does not compare against the user's external original.

## Predator launcher / TSX regression fix (2026-10-18)

User requested the launcher open the local UI in a **new browser window** rather than reusing a tab and reported Vite Babel parser error in `FfmpegSetup.tsx` line 122 caused by literal `\\n` characters inserted during a JSX edit. Fixed literal characters and an additional mismatched opening `<Panel>`/closing `</Dialog>` tag in `FfmpegSetup.tsx`. Modified `app/run.ps1` to start Edge or Chrome using `--new-window` (fallback to default browser URL opener if no supported executable found). Added GitHub Actions frontend type-check/build workflow. GitHub Actions run **39116679928** for corrected commit `7a3ad824` completed **successfully**, including `npm run build --prefix app/frontend`. Browser-new-window behavior still requires local Windows verification on Predator.

## Windows default-browser correction (2026-10-18)

User reported that the new-window launch forced Edge even though Chrome was Windows' default and prior browser. This was an assistant-introduced product regression caused by the prior `msedge.exe`-first executable scan. `app/run.ps1` now reads the user's Windows HTTP UserChoice association and resolves that ProgId's open command; uses a new-window switch for the *selected* supported browser (Chrome/Edge/Firefox/Brave/Vivaldi). When it cannot safely identify a supported executable, it opens via the default URL handler, prioritizing user's browser preference over forced new-window behavior. No alternate browser is selected. Commit `4515ad48` pending Windows smoke verification on Predator.

## DAW strategy / next feature recommendation (2026-10-18)

User confirms guided FFmpeg install works and resumes the original separation. Added compact installer progress: download percent from Content-Length if supplied, indeterminate track during checksum/extraction; committed, pending frontend CI and Predator smoke test. The user asks whether to develop a complete DAW or integrate an existing DAW. Recommendation: **do not build a new DAW or VST hosting engine** for Song Harbor. Keep six-stem audition, mute/solo/level adjustment, remix export in our app; use **external DAW handoff** for waveform editing, clip rearrangement, time-stretching, automation, effects, and mastering. Explore REAPER (native .RPP session generation if validated, paid discounted license; strong scripting) as primary deep-integration candidate; Waveform Free as zero-cost choice, Cakewalk Sonar free tier as Windows alternative; Ardour source available but official Windows binary generally paid/unrestricted. Next product increment: durable **Song Workbench** with reopenable sessions, audio/stem paths + hashes, non-destructive mix-state manifest; then **Export to DAW** action with portable 6-stem aligned WAV bundle, optional REAPER .RPP project after tested schema, allow selecting installed executable, no forced install or premium DAW lock-in. Explicitly not a VST plugin first: complex plugin formats, hosts, distribution and latency contracts are needless for handoff. User has not requested actual implementation of next milestone yet.

## M2 persistent songs / Waveform Free-first DAW handoff (2026-10-18)

User explicitly prioritized **Waveform Free** ahead of REAPER due to **zero current funding**. This is the target order for DAW integration. Implemented `app/backend/projects.py` and server routes to persist six-stem Song Harbor manifests, reopen completed/recovered jobs after backend restarts, save song name and per-stem mixer state, list recent projects, and copy six full-length unaltered WAVs to a portable Waveform exchange folder containing a track-order manifest and import guide. No fabricated Waveform native session file; import six files as separate tracks at t=0 via Ctrl-drag in Waveform. UI has compact Open saved song picker and Save song / Export to Waveform / Open export folder controls, preserving main workspace. Automated GitHub Actions Python syntax+project test workflow and frontend build both passed, but **local import into Waveform Free, mixer-setting restoration, and end-to-end Windows operation remain unverified**. REAPER `.RPP` handoff follows when practical; a full embedded DAW and DAW plugins are deferred.


## Library-first product correction & generic DAW setup (2026-10-18)

User confirmed **music Library as default landing, SQLite catalog, song as parent of sources/versions/artifacts, rename separate from filenames, virtual nested collections unrelated to disk paths, dense icon-first UI, contextual right-click help, and reuse of shared TWS-UI**. Canonical principles updated in `TWS-Design-Principles/apps/App-Design-Principles.md` sections 21–22 and Studio UI Style Guide. Created `docs/library-first-architecture.md` covering approved schema, collection and history model, metadata-only renaming, dedup and safe trash/migration strategy.

Implemented initial SQLite `app/backend/library.py`, transactionally creating an indexed catalog on the runtime drive, idempotently adopting existing complete six-stem jobs without touching original sources, and endpoints for listing, renaming and virtual collection membership. Song Harbor now launches to compact LibraryHome, using TWS-UI controls, and opens the existing Song Workspace for import/separation/mixing. Mixer adds monitoring-only master volume, separated from export/mix gain.

Previous **Export to Waveform → Not Found** was a dead-end UX. Replaced the mixer action with generic **Export to DAW** dialog, first Waveform Free target. Implemented `app/backend/daw.py` discovery, persisted selected executable, local native picker, target metadata and official vendor download URL, and selected vendor installer execution after Windows Authenticode verification. No automatic direct download due publisher account/installer distribution. Portable six-stem exchange does not require an installed DAW; launching Waveform does, with guided recovery. **REAPER adapter later** due zero project funding.

GitHub Actions frontend typecheck/build and Python backend suite have been green for committed changes. Local Predator Windows smoke test remains outstanding, especially native installer detection/signature and Waveform handoff. Named version branching, multiple-artifact management, soft deletion/trash and native .tracktionedit format are not yet implemented; document as later P2/P4. Avoid claiming the finished product exists merely because the Library scaffold is visible.

## Launch/Library/UX QA correction (2026-10-18)

Tester: startup error then 404 until refresh; wants double-click launcher to fast-forward pull automatically; Library must deduplicate identical sources into variant takes and allow reversible removal; opened song must not show import form; icons for stems and actions; Help must be in-app before public release; scalable fonts later. Added safe fast-forward developer auto-update (skips dirty/offline/detached; `-NoUpdate`), backend+Vite readiness gate before browser launch, quiet Library startup retry, SHA-256 source-based grouping with cached hashes (no file moves), soft remove/Undo/Removed Restore, expandable takes, session-only Song Workspace, monitoring/stem/control icons and contextual in-app Help. Tests for duplicate grouping, file preservation, removal and restore passed in GitHub Actions, as did frontend build. Cross-project Principles expanded sections 23–24.

Design limitation: exact byte-level hashes, so source files with different encoding but same music are not merged; no auto-merging based on title. Current Remove hides whole grouped song, not an individual edit/mix—separate artifact lifecycle remains upcoming. Waveform remains first DAW target; REAPER later. Attracktive from Tracktion is a free VST3 instrument sound player with 100 included sounds, optional expansions—sensible as external Waveform plugin later but not Song Harbor VST hosting. $10 Waveform Welcome Bundle contents not independently verified; skip purchase with zero project budget. User has not yet locally verified corrected launcher/readiness or new Library actions on Predator.

## Predator Library QA follow-up (2026-10-18)

Screenshot: Two identical-titled **Raise the Neon Black** rows; original source filename also same; no automatic grouping shown. Tester reports **Remove from Library** gave generic "Could not change Library status", collection context submenu too long, desire browser desktop right-click, unutilized space in mixer stem rows, undersized icons. Launch smooth, song import panel removed, contextual in-app Help accepted.

Corrections committed:
- Backend explicit `song_links` table allows **Combine as takes** even if two files differ in byte SHA-256 (which may be true for same named audio after metadata/export changes); no original media is touched. Automatic hash grouping remains strict. Library source filename hover includes a short SHA-256 prefix for diagnosis, not noisy inline copy.
- Revised Library remove/restore to update underlying SQLite IDs transactionally rather than finding and mutating groups through the list presentation. Endpoints now preserve all media and return HTTP details in UI if a failure recurs. Backend test expanded for non-identical file versions manually combined and recovered, and checks the original stored files.
- Collection menu is now a single **Add to collection…** command opening a compact searchable picker; supports growing collections without an enormous context menu.
- Desktop right-click on a song row opens item actions (Open, Add to collection, Combine as takes, Remove/Restore, Help), with Shift+F10/context-key alternative and existing ellipsis menu as mouse/touch fallback. This is browser-based, not an OS-native extension; upstream reusable TWS-UI component is still desirable.
- Stem channel CSS uses a small fixed icon cell and gives remaining width to the actual controls/sliders; action/transport icons enlarged. Song Library typography fixed to dense sans-serif and pencil button, including compatibility with already-installed TWS-UI library; shared `TWS-UI` EditableTitle updated to a pencil glyph too.
- Frontend and backend automated build/tests passed after changes. Real Predator acceptance test pending.

Caveat: do not claim exact duplicates exist merely based on filename. Exact SHA-256 is authoritative for byte-identical copies; manual grouping is a safe way to link genuinely related but nonidentical encodes. Current take grouping is metadata only; independent version editing, take deletion and full artifact lifecycle are future work.

## Launcher fixes after Predator port collision (2026-10-18)

User reports portable launcher never auto-pulled due detected dirty checkout and failed with backend `Errno 10048` at 127.0.0.1:8765 (old Song Harbor service still bound).

Fixed in source:
- New `scripts/update-checkout.ps1` attempts safe fetch + fast-forward on the current branch **even when local edits exist**, letting Git refuse only actual file conflicts. Never reset/clean/stash/force. Handles detached HEAD, offline or diverged branches gracefully. `start-song-harbor.ps1` invokes it; `-NoUpdate` bypasses.
- New `scripts/prepare-local-ports.ps1` checks owners of 8765 and 5173 before creating child processes; only confirmed Song Harbor processes whose commands contain the same repo path may be stopped. An existing runtime with active jobs is protected; older runtime without job-state endpoint requires explicit restart confirmation. Unknown apps are never terminated.
- `app/run.ps1` invokes safe port preflight before backend launch. Backend now exposes `GET /api/runtime/status` with active job status.
- Expanded Windows CI to parse new PowerShell scripts and test real Git fast-forward behavior with unrelated dirty and conflicting tracked files. Windows CI run 39134418037 passed both syntax and updater integration tests.

**Pending Predator smoke:** one-time manual git pull to obtain the updater, relaunch, accept prompt if an older verified Song Harbor backend cannot report job activity, confirm healthy API/UI and subsequent double-click updates. If Git still refuses due overlapping tracked changes, console should explain protected local checkout; inspect `git status --short` and resolve manually. This is developer checkout behavior, not public auto-update mechanism.

## Omen FFmpeg UX regression: disabled separation action (2026-10-18)

On Laptop Omen, tester selected Raise the Neon Black.wav in Library → Import while FFmpeg was missing. The **Separate stems** control was disabled (gray), so clicking it could not trigger the already-implemented guided FFmpeg setup. Root cause: frontend computed `canStart = file && health.separator_ready && ...`, contradicting the recoverable dependency flow.

Changed in `app/frontend/src/main.tsx`: separation action remains enabled when a file and backend health are present, even if `health.ffmpeg` or the separator capability is missing. The click checks FFmpeg first and opens the existing compact locate/search/install dialog while setting `pendingSeparation`. Successful FFmpeg configuration automatically resumes the requested separation if the separator engine is ready. A missing core separator engine now produces specific recovery guidance rather than blindly invoking the backend. The action is a 52px icon-first, accessible SVG separation control with tooltip; missing FFmpeg gets a subtle amber outline and small exclamation badge, without putting a large dependency banner in the workspace. During active upload/separation, the control is disabled normally.

**Local Omen acceptance:** update checkout and relaunch, select an audio file with FFmpeg not configured, see amber icon rather than gray disabled button, hover to see 'FFmpeg required', click to open installer, finish setup and confirm separation begins automatically without reselecting the recording. Confirm a machine already configured for FFmpeg sees an ordinary icon and no extra setup dialog. Frontend CI build was passing for the first icon change; final follow-up CI run needs confirmation and Windows local smoke remains pending.
