# Song Harbor M0: six-stem entry UI

This is a **local vertical slice**, not a bundled standalone installer yet. The frontend consumes components from [TWS-UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), which implements the canonical [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles). Product-specific deep blue-green theme overrides are semantic; shared controls are imported.

## Shared-tool setup and recovery (FFmpeg / FFprobe)

Song Harbor now treats absent FFmpeg as a **passive feature setup state**, not a failed application launch. On launch, it checks the saved path in `<runtime-root>/config/settings.json`, then PATH and common installation folders. If it still cannot find both executable tools, Song Harbor shows only a **small upper-right gear icon with an unresolved-component count**. The main workspace stays unchanged. When the user clicks **Separate stems** or **Export mix** and the required tool is missing, or voluntarily clicks the gear, a **compact TWS Dialog** presents: **Browse…** to locate an existing install, **Search computer** (a bounded opt-in search of common app locations across available drives), or **Download and install here** to place a publisher-supplied Windows essentials build into a user-selected folder. The installer downloads the archive and associated publisher SHA-256 checksum from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), verifies the digest, extracts only `ffmpeg.exe` and `ffprobe.exe`, verifies that both run, and writes the resolved binary folder to application configuration. Source media remains untouched; no system-wide PATH changes, admin operations, or installs into shared system folders are needed. The user can revisit the setting by clicking the header gear. The selected recording and pending action are preserved; successful setup resumes separation or retries mix export. Dismissing setup leaves the rest of the app usable.

New backend endpoints: `/api/dependencies/ffmpeg`, `/browse`, `/search`, `/locate`, `/install` plus installation status polling. Both separation and mix export use the same configured tools. First use should be validated on Predator without ffprobe on PATH; source and six stem durations should still match. An empty/invalid chosen directory and download/checksum/network errors remain recoverable in the same setup panel. Windows-native folder picker requires an interactive desktop session. Automatic installation is only supported on Windows at this stage.

This is an initial implementation of the canonical [TWS dependency-recovery design principle](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles/blob/main/apps/App-Design-Principles.md). Other external system prerequisites (Git, Node, NVIDIA drivers) are still handled by bootstrap diagnostics, rather than this FFmpeg-specific graphical flow. **Code committed, not yet smoke-tested on Predator.**

## Portable Windows launch (all supported machines)

The recommended entry point is **`scripts/launch-song-harbor.bat`**. It invokes `scripts/start-song-harbor.ps1` and locates the isolated runtime, without assuming C:, D:, or G:. Runtime resolution order: explicit first BAT argument (`-Root` in PowerShell), `SONG_HARBOR_HOME`, an existing `.venv` in/next to the source checkout (including a sibling `SongHarbor` runtime directory), then a new sibling `SongHarbor` directory. It prints the resolved source and runtime directories on launch.

If the runtime is missing, it calls `scripts/bootstrap-windows.ps1` to set it up; if only Node/UI dependencies are missing, it installs only those. `scripts/bootstrap-windows.bat` performs install-only without launching the UI. Existing working CUDA environments are not reinstalled for routine launches. A Windows NVIDIA driver compatible with CUDA 12.6, Git, FFmpeg, Node/npm, PowerShell 7 and a 64-bit Python 3.11 interpreter (or `uv`/Python launcher support) are required; the launcher diagnoses missing system prerequisites rather than silently installing drivers or system apps.

Examples:

```bat
scripts\launch-song-harbor.bat
scripts\launch-song-harbor.bat G:\Apps\SongHarbor
```

**Predator:** `G:\Apps\Song-Harbor` source checkout can discover the existing `G:\Apps\SongHarbor\.venv`. **Skynet:** a checkout under `D:\Apps\SongHarbor\source` detects `D:\Apps\SongHarbor\.venv`. **Omen:** separate checkout and `C:\Apps\SongHarbor\.venv` are supported. Explicit arguments or `SONG_HARBOR_HOME` override autodetection for atypical layouts.

The portable launch change is committed but **requires a user smoke test on Predator**; previous Omen success predates this change.

## Automated Windows bootstrap (recommended for Laptop Omen)

The reusable installer is [`scripts/bootstrap-windows.ps1`](../scripts/bootstrap-windows.ps1). It performs GPU, free-space, Python 3.11 x64, FFmpeg, Git, and npm checks, creates an isolated Python virtual environment, moves transient caches to the chosen work drive, pins CUDA PyTorch and compatible ONNX Runtime versions, installs the six-stem separator and UI, and verifies dependencies plus CUDA arithmetic.

**Laptop Omen uses C: as its only work drive.** The installed runtime on Omen uses `C:\Apps\SongHarbor` for Python, models, and runtime data; launchers no longer hard-code this path. Generated data is stored outside the source checkout when the repo is cloned to a separate folder; this C: placement is an explicit hardware-driven exception to the preferred separate-drive policy.

From the cloned repository, double-click `scripts/bootstrap-windows.bat` to install dependencies, then `scripts/launch-song-harbor.bat` to start the UI. The first launcher keeps the console open and prints any failure. Both accept an optional custom root path as their first argument.

Or invoke PowerShell 7 directly from a repository checkout:

```powershell
Set-Location <Song-Harbor-repo-checkout>
.\\scripts\\bootstrap-windows.ps1 -Root "E:\\Apps\\SongHarbor"
.\\app\\run.ps1 -Root "E:\\Apps\\SongHarbor"
```

If you use another machine, replace `C:\\Apps\\SongHarbor` with an appropriate path. The bootstrap requires working Git, FFmpeg, NVIDIA driver compatible with CUDA 12.6, Node.js/npm for the UI, and Python 3.11 x64. If `uv` is present, `uv python install 3.11` can provide Python 3.11 before bootstrap. No existing unrelated Python or music-generation environment is modified.

Use `-SkipUI` to install only the separator backend, or `-SkipModel` to skip downloading the six-stem checkpoint. The script will **fail clearly** if prerequisites or CUDA tests are unavailable; it will not automatically replace drivers or install system software. It must still be tested on Omen and should not be presented as a validated installer until then.

## Current machine setup (Windows)

Prerequisites: Node.js + npm, FFmpeg on PATH, existing working `D:\Apps\SongHarbor\.venv` with CUDA PyTorch and `audio-separator[gpu]` already validated. Because `D:\Apps\SongHarbor` already holds the validated `.venv` and downloaded models, clone the source into a **subdirectory**. Point `run.ps1 -Root` at the parent data/runtime folder, not the source checkout. **Do not overwrite the existing environment or downloaded models.**

From PowerShell on the desktop:

```powershell
git clone https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor.git D:\Apps\SongHarbor\source
Set-Location D:\Apps\SongHarbor\source
& "D:\Apps\SongHarbor\.venv\Scripts\python.exe" -m pip install -r app\backend\requirements.txt
npm install --prefix app\frontend
.\app\run.ps1 -Root D:\Apps\SongHarbor
```

Opens local interface at http://127.0.0.1:5173. Backend listens only on 127.0.0.1:8765 and executes audio-separator.exe from the active virtual environment; no remote upload. Source files are copied into `data/jobs/<id>` and left untouched at their original location. Download stems individually or open the local output folder.

## M0 acceptance

- [x] UI starts locally via batch launcher; user reports launcher works (Laptop Omen).
- [x] User reports splitter works from entry UI on Laptop Omen; end-to-end workflow smoke passed.
- [x] Six-stem model fixed to `htdemucs_6s.yaml` for M0.
- [x] End-to-end separation user smoke passed; individual error/cancel paths not yet exercised.
- [x] Splitter output successful as reported by user; individual download/open-folder actions not independently verified.
- [ ] Independently validate source preservation and runtime security beyond code review.
- [ ] Record exact Omen input fixture, stem durations, and per-stem listening confirmation (user reports successful splitter without specifics).
- [ ] `npm run build --prefix app/frontend` passes.

## Scope boundaries

One job at a time. Basic local-only progress state rather than fabricated percent; model downloads may delay startup. M1 adds an in-app mixer for the six separated stems. Still no clip editing, packaging, model selector, job persistence across restarts, or deep licensing approval. No claims of tested production readiness before validation.

The source code sits in `app/`; generated assets, caches, model weights and imported music must remain local and untracked. The TWS design repo remains canonical rather than copying design-system source into Song Harbor.

## Laptop Omen user acceptance checkpoint (2026-10-17)

User reports **“Launcher works. Splitter works.”** for the C:-based bootstrap/launcher and M0 separation UI on Laptop Omen. This establishes user-reported functional end-to-end acceptance for the limited milestone of opening the app and separating audio, without claiming validation of every export/open-folder, error/cancel, performance, or packaging path. The core M0 entry UI + functional splitter is **accepted for the requested milestone scope**. Further tests and standalone packaging remain separate work.

## Known regression: output appears to stop at 4:00 (2026-10-17)

User reports a separation cutoff around 4:00 on Laptop Omen; root cause **not yet confirmed**. `htdemucs_6s.yaml` itself has no documented four-minute ceiling. Earlier M0 completion logic accepted any six WAV files regardless of duration. The backend now uses `ffprobe` to measure source and each stem and **reject** any mismatch greater than 0.25 seconds (instead of falsely declaring completion). Source duration, output durations, and error details are returned with the job. Added `app/backend/tests/test_duration_validation.py` for matched outputs, 4:00 truncated output, and slight container/codec duration variance. **No claim that duration validation repairs a truncation mechanism**: rerun a >4:00 source, inspect original/imported file and stem durations and backend logs, then identify/fix the cause. The prior user-reported M0 smoke acceptance covers a shorter track, not unrestricted-length separation.


### 2026-10-17 cutoff diagnostic update
User ran ffprobe on Laptop Omen's most recent job, `Salt in the Circuit`: imported `Salt in the Circuit.wav` was **exactly 240.000000 s** and each of the six Demucs 6s outputs was **exactly 240.000000 s**. This rules out *post-import separation-only* truncation in this job, but does not determine whether the user selected a naturally 4:00 file or whether upload/import changed a longer original. The 0.25 s stem-to-imported-source guard is insufficient to detect pre-separation truncation. Next: compare external selected original file with imported job file (ffprobe duration, byte count, SHA256), and if original is longer, audit browser upload and import handling.


### Follow-up: suspected Audacity timeline artifact (2026-10-17)
User withdrew the four-minute cutoff report after realizing a 4:00 song was previously imported into Audacity and the next song likely shared that timeline. The inspected Song Harbor job had source and all six stems at exactly 240 seconds. **No Song Harbor truncation has been demonstrated.** Reclassify this as a probable Audacity session/timeline issue rather than a confirmed application regression. Keep the new source-to-stem duration validation as useful defensive QA; it does not compare against the user's external original.


## M1: In-app stem mixer (implemented; awaiting local QA)

The separation results now include a compact mixer with **Play/Pause**, a seekable timeline, separate **Mute / Solo / Gain (0-100%)** per stem, **Reset mix**, and **Export mix WAV**. Individual stems remain downloadable. After exporting, use the in-app download link or Open folder. The backend uses FFmpeg's six aligned WAV inputs, applies each stem's effective gain and a peak limiter, writes 24-bit stereo PCM WAV to the job output folder, validates duration against the original source, and leaves source stems unchanged. The export is not an unaltered null reconstruction due to limiting and mixing. Gain/solo/mute API input is validated to prevent arbitrary file access. A separate inline stream endpoint supports media playback via range requests.

**Preview caveat:** browser media elements are independently decoded and corrected for observable drift; this is a low-memory audition surface, **not guaranteed sample-accurate synchronized DAW playback**. The backend renders the export with FFmpeg using sample-aligned input stem files. Assess any flamming/phasing in the preview separately from the exported WAV. We should migrate transport to a shared Web Audio clock if audible drift is unacceptable.

**Test plan on Laptop Omen** (run a completed separation after pulling latest source):

1. Playback starts and stops; seek to middle/end and verify the timeline is correct.
2. Solo vocals; solo drums; mute both; move volume sliders and check responsiveness.
3. Reset mix; export WAV; download and audition it independently; compare duration with original using ffprobe.
4. Re-export with vocals muted and verify the resulting mix audibly omits vocals. The exported source stems must remain unchanged.
5. Run backend tests from the installed environment: `& C:\\Apps\\SongHarbor\\.venv\\Scripts\\python.exe -m unittest discover -s app\\backend\\tests -v`.
6. Validate the frontend: `npm run build --prefix app/frontend`.

No user acceptance or end-to-end QA is claimed yet. M0 remains accepted; M1 is **implemented, unverified on the workstation**.


## Dependency UI correction (2026-10-18)

The initial implementation showed a large persistent setup panel on page load, even if the user was not trying to use FFmpeg. This is explicitly **rejected**. Correct design: passive status icon/count in the thin header, no workspace takeover; modal recovery only on affected action or user-clicked component settings; replay interrupted task after configuration. Implementation uses shared `@tws-ui/core/react` Dialog, preserves file selection, and keeps core engine status separate from FFmpeg readiness. Canonical standards updated in TWS Design Principles sections 19–20 and Studio UI Style Guide. UI requires a local smoke test on Laptop Predator after pulling latest source.

## M2: Persistent song workbench + Waveform Free-first handoff

Song Harbor now saves a `song-harbor.json` manifest in the machine-local `<runtime>/data/jobs/<id>/` folder on completion. It includes the song name, source name, six source stems, and mix controls (gain, mute, solo). The mixer exposes **Save song**, and **Open saved song** restores an earlier session without running the model again, including stem mixing state. Existing older six-stem jobs with all original files can be discovered and recovered after restart, with their initial mixer state set to defaults until explicitly saved.

The next step into a full DAW is **Export to Waveform** on a completed song. This copies the six **unaltered**, aligned 48 kHz WAV stems into a self-contained `exports/Waveform` folder (or a unique suffixed sibling for later exports), includes a `manifest.json` with track order and original mix gains for reference, and writes `IMPORT-IN-WAVEFORM.txt` with documented import steps. Press **Open export folder** and then in Waveform Free: create/open an Edit, select all six WAVs, **Ctrl-drag** to import on separate tracks, and check every track begins at timeline 0:00. Do not import clips consecutively or allow tempo stretch. Export intentionally is **not** a generated `.tracktionedit`: we have not yet validated a native project format against the installed current Waveform version. We do not attempt to install or force-launch any DAW.

**Waveform Free is first priority because the project currently has no funding**. REAPER is the next target when practical, initially via the same generic aligned six-stem exchange, then potentially a native `.RPP` project validated against REAPER. A DAW plugin and embedded full DAW are explicitly deferred. No paid integration is required for core Song Harbor use.

Automated checks: GitHub Actions [Song projects and Waveform exchange](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/workflows/projects-tests.yml) validates Python syntax, recovery, save/reload, a non-destructive six-stem export, and re-export into a distinct location. The frontend build workflow type-checks and bundles the UI. These checks do not prove the actual audio imports into Waveform or guarantee sample accuracy in browser preview; both require local acceptance testing.

### Predator smoke test

1. Pull main and relaunch; separate a song, adjust vocal gain and solo/mute, and click **Save song**.
2. Close/relaunch Song Harbor; expand **Open saved song**, select the track, and confirm six stem controls retain their settings and playback works.
3. Click **Export to Waveform** and **Open export folder**; verify six sequentially named WAVs, manifest, and import instructions. Original stem files must remain unchanged.
4. Import all six WAVs as separate tracks starting at 0:00 in Waveform Free and verify full song alignment and audio.
5. Re-export; confirm the first Waveform folder still exists and is not overwritten.

M2 is committed and the code-level CI checks passed; **Waveform application import and Predator end-to-end smoke checks remain unverified**.

## Library-first foundation and DAW adapter recovery (2026-10-18)

The application now **opens to a compact Library** instead of the former separation landing screen. The source/separation/mixer remains available by selecting Import song or opening an existing song. The Library indexes existing six-stem jobs in an on-drive SQLite database at `<runtime>/data/library/library.sqlite` without relocating recordings. Virtual nested collections can hold the same song in multiple groups; the catalog stores stable identity apart from physical files. Renaming a song updates Library metadata and the portable song manifest **without renaming WAV/MP3 audio files**. A shared TWS-UI `EditableTitle`, `Menu`, `IconButton` and status/dialog primitives are used; native right-click handling and broader context-action abstractions are reserved for the shared UI follow-up.

**DAW export is now generic**. The mixer exposes **Export to DAW**, leading to a focused target dialog. Waveform Free is the only active adapter today; REAPER follows. Portable aligned WAV export works even if Waveform is not installed. The dialog supports Detect installed Waveform, browse for its executable, save the resolved location, and launch it. When missing, it opens the **official Tracktion Waveform Free download page**, allows choosing the downloaded installer, and can launch a Windows-signed Tracktion installer on explicit command; after the publisher's account/install flow, press Detect to resume. The app never assumes it can bypass account or licensing steps or directly fetch an unverified installer. This recovery is distinct from FFmpeg setup.

The mixer now has **playback-only master volume**; it changes monitoring loudness, never rendered mix gain or the availability of an already-exported WAV.

### Local acceptance checklist

1. Pull main, restart the backend/launcher, confirm the Library is the default home.
2. Confirm existing six-stem songs show without file relocation. Open one into Song Workspace and return to Library.
3. Create a virtual collection, place a song in it, and check the underlying source/stem paths stay unchanged.
4. Rename the Library display name (e.g., Salt in the Circuit → Circuit of Salt) and confirm that the original imported WAV/MP3 filename has **not** changed. Confirm the display title survives restart.
5. In the mixer, change **monitoring volume**, then export a mix and verify the output loudness is controlled by channel mix settings, not the monitoring slider.
6. Click **Export to DAW**. Choose Waveform; prepare stems. If Waveform is absent, the dialog must explain the absence and offer Detect/Browse/official publisher download/installer assistance—never raw Not Found. Imported stems should start simultaneously at 0:00.
7. If selecting a downloaded Waveform installer, run it only after explicit confirmation; Windows signature verification will reject missing/untrusted signatures.

This is **P0 / early P1**, not the full library/version history experience. Named branching versions, multi-export history management, trash/restore, relationship-aware deletion, complete right-click/touch context menus, verified native Waveform projects and REAPER adapter are still planned. See [Library-first architecture](../docs/library-first-architecture.md).

Automated checks validate Python syntax, SQLite adoption/rename/virtual grouping, non-destructive exports and TypeScript/Vite builds. **A local Windows + Waveform first-use smoke test remains necessary before acceptance.**

## Predator QA corrections — 2026-10-18

Recent tester notes: initial launch failed, second launch briefly showed HTTP 404 until refresh; Library looked good but identical source files were shown twice, opened songs still displayed import controls, icons/text were too verbose, and help led directly to GitHub.

Implemented in this QA pass:

- Developer checkout launcher (`scripts/start-song-harbor.ps1`) now attempts `git fetch` + `merge --ff-only` before startup. Skips silently modifying dirty checkouts or detached HEAD; offline/remote failures warn and launch the existing code. `-NoUpdate` disables this for local experiments. **This is source-checkout convenience, NOT a production auto-updater.**
- `app/run.ps1` now starts backend and frontend, polls actual API/UI readiness and opens the default browser only after both report ready. A frontend crash or readiness timeout gives a directed console error instead of preemptively opening a dead page. Library load also has bounded UI retries with in-app retry control. Further production work should include migration progress, asset discovery in a worker, and cold-start/upgrade recovery tests.
- SQLite Library now records a SHA-256 fingerprint for each *source file*, caching each digest in `sources.sha256`. Jobs with identical source **bytes** group into one visible song with an expandable set of takes; filenames alone do not trigger a merge. No source files move and the original per-job manifests stay intact. The first Library scan may perform hash I/O on existing media. Progressive/indexed scanning will be needed before shipping publicly with large libraries.
- Library context menu offers **Remove from Library**, plus an Undo action and a Removed view with Restore; this sets a logical deletion flag and preserves all physical source/stem files. Whole grouped song removal is supported; per-version/per-artifact cleanup remains a separate upcoming feature.
- Opening an existing song now hides the import/separation form and shows its song workbench. Ingesting a new song starts from the Library's import action.
- Primary controls use icon-first TWS IconButton with accessible labels and tooltips: playback, save, reset, export mix, DAW handoff, and stem identity icons. Targeted setup dialogs retain explanatory copy where necessary. The Library's context Help now opens an in-app guidance dialog first; technical docs are a further click.
- The shared TWS Design Principles explicitly cover startup readiness, duplicate media identity, recoverable Library removal, contextual in-app help, user-adjustable text/density (planned) and developer vs production updates.

**QA to run on Predator:** Relaunch by double-clicking the repo batch file without manually pulling; confirm it fast-forwards a clean checkout, respects the default browser and shows no 404. Confirm one top-level Library song for the two truly byte-identical source files, with both takes expandable and independently openable. Remove from Library; Undo; remove again; Restore from Removed. Confirm source files, six stems and prior exports remain on disk. Open a saved song and verify import form absent, monitoring/master volume and icons operable, and contextual help in-app. Test with intentionally dirty Git checkout to ensure update is skipped, and with no network to ensure launch proceeds.

**Unverified on Windows**: actual Vite readiness process startup, installer detection, duplicate reconciliation on existing production-size recordings and native media playback. CI success covers frontend compile and backend unit tests, not end-to-end Windows behavior. Exact-source hashing is intentionally conservative: alternate compressed encodes or remastered exports are not auto-merged.

## Duplicate + 404 regression investigation (2026-10-18)

QA from Predator: two *Raise the Neon Black* Library rows persisted despite sourcing the identical file, and both Remove and Combine returned HTTP **404 Not Found**. This is consistent with a **stale running Python backend**: Vite hot-reloads new frontend code while `server.py` is not hot-reloaded; `run.ps1` previously accepted any healthy listener on `127.0.0.1:8765`, including a prior Song Harbor instance lacking the new routes. We have not inspected Predator's runtime processes directly, so treat this as a high-confidence hypothesis rather than proof.

Mitigations:
- The backend health endpoint now advertises `instance_token` and `api_features`. `run.ps1` generates a fresh token, passes it to the new Python process, and **refuses to accept any previous backend's health response**. On collision, user receives explicit instructions to close earlier Song Harbor launchers. This prevents opening current UI against old APIs.
- Vite runs with `--strictPort`, avoiding silent fallback to 5174 when an old server already owns 5173.
- The Library checks required backend API capabilities before listing, and translates stale-route 404s into an actionable restart message rather than dumping `Not Found`.
- Added integration tests using FastAPI TestClient (not just direct SQLite functions) for identical-source SHA-256 grouping, POST Remove, POST Restore, and POST Combine of two intentionally different files. Linux backend CI passed.
- Replaced platform-dependent small emoji channel indicators with **32px scalable instrument SVGs**, enlarged mixer transport/action icons, and retuned fixed track columns so controls receive remaining space. Visual hierarchy references Tracktion Waveform's more confident icon/text balance, while keeping Song Harbor's own design language.

On Predator: fully exit all Song Harbor launchers before restarting; the launcher should auto-fast-forward main. Check that two identical-byte source copies appear under one song with two expandable takes. If still separate, hover source filename to see 12-digit hash prefix and inspect the underlying files; differences in audio metadata or encoder output can make nominally same recordings byte-distinct. Remove and Restore should succeed; if not, the in-app diagnostic should identify the route mismatch.

**Production follow-up:** consolidate backend/frontend into one supervised desktop runtime, use real service readiness and version handshake, and add migration/indexer progress. Preventing split-version development servers is a necessary intermediate step, not a final production deployment architecture.

## Launcher recovery: dirty Git checkout and occupied ports (2026-10-18)

Predator QA exposed two failures: launcher printed `Skipping auto-update (working tree changes or detached HEAD)`, and backend crashed with Windows socket error `[Errno 10048]` when an older Song Harbor process still owned `127.0.0.1:8765`.

**Source auto-update:** `scripts/start-song-harbor.ps1` now invokes `scripts/update-checkout.ps1`. The updater fetches the current branch and attempts a **fast-forward even with unrelated dirty/untracked local files**. Git's normal safety checks prevent clobbering tracked or untracked files when they conflict with the incoming changes. It never forces, resets, cleans or stashes your files. If offline or diverged/conflicting, a warning describes why and it launches the existing checkout. PowerShell switch `-NoUpdate` disables auto-update. The Windows CI workflow performs a real bare-origin/checkout Git integration test confirming that an unrelated dirty file survives a successful fast-forward and that a conflicting upstream update is refused without altering local content.

**Occupied localhost ports:** `scripts/prepare-local-ports.ps1` runs before creating a new backend. It examines listeners on **8765 (backend)** and **5173 (Vite)**, verifies process type and full Song Harbor checkout command line, and reclaims those ports **only if the owners belong to this exact checkout**. It refuses to terminate unrelated apps. If the existing backend supports the runtime status endpoint and has active separation/render/export jobs, it refuses to interrupt the work. Older versions without runtime job status require one explicit restart confirmation rather than risking lost processing. Closing an older browser tab alone may not stop a backend; the launcher handles verified stale processes. The new backend exposes `/api/runtime/status` for subsequent safe restarts.

**How to test:** For this one update, manually `git pull` if the old launcher still skips updates. Then close previous launchers and double-click the BAT; confirm that it prints update information and either frees verified stale ports or asks once before retiring an old backend that cannot report active jobs. Repeat with a dirty but unrelated tracked file and confirm it is preserved and incoming unrelated commits are applied. No administrative privileges or generic process killing are used.

## Single-process launch architecture (2026-10-18)

After an Omen test showed Vite reporting ready while repeated `/api/health` calls failed with `ECONNREFUSED 127.0.0.1:8765`, the normal Windows launcher was simplified. **A single Python/FastAPI process now serves both the compiled React UI and all API endpoints, using a fresh OS-assigned localhost port for each launch.** There is no Vite dev server, Vite API proxy, separate fixed API port, or restart/port-killing routine in the normal launch path. Existing other applications or old Song Harbor processes are left alone.

On every source-checkout launch, `app/run.ps1` runs `npm run build` and verifies `app/frontend/dist/index.html` exists before starting the backend. The backend mounts Vite's compiled `dist/assets`, serves `index.html` at `/` and serves SPA fallback routes, while preserving `/api/*` for real API requests. The launcher dynamically selects a free ephemeral loopback TCP port, supplies it through `SONG_HARBOR_PORT`, verifies the backend instance token and both the API and HTML page on the **same port**, and only then opens the Windows default browser (a separate window when supported). No backend or frontend process is killed during preflight. Closing the launcher should stop its single child backend; no unrelated process is touched.

`scripts/start-song-harbor.ps1` retains runtime discovery, dependency bootstrap and safe Git fast-forward updater. An unavailable CUDA GPU no longer triggers endless prerequisite reinstalls before the Library can open; GPU capability remains relevant when actually separating audio.

**Testing:** Windows PowerShell parser checks passed; GitHub Actions `Single-server launch smoke` runs a fresh Windows frontend build, launches the same FastAPI app on a dynamic port, and verifies that both UI and API respond from it. This CI is not a substitute for local acceptance on Omen/Predator.

**For the next launch**, manually `git pull` once if the old updater is not trustworthy, then double-click `scripts/launch-song-harbor.bat`. Expected: `Building Song Harbor interface...`, then `UI/API (single server): http://127.0.0.1:<dynamic-port>/` and a new browser window at that URL. Do **not** expect port 5173 or port 8765; old tabs pointing at those ports are obsolete. Closing earlier launchers is optional because each new instance has its own port, though each consumes resources.

## Audacity DAW adapter / Omen discovery test (2026-10-18)

**Audacity** is now a second DAW target, alongside Waveform Free, with the same generic **Export to DAW** workflow. The selected target is persisted as `selected_daw` under the runtime root's `config/settings.json`; paths for both installations are stored independently under `daws.audacity.executable` and `daws.waveform.executable`. Discovery checks configured paths first, then Windows uninstall registrations (including InstallLocation/DisplayIcon) and App Paths, standard per-machine/per-user folders, and PATH. It does **not** start any discovered executable during scanning. Users can use Detect or Browse if automatic discovery fails. The UI displays the selected DAW's readiness and resets the prepared-folder state when the target changes.

**Prepare stems** for Audacity copies the original six aligned WAVs, untouched, into `<runtime>/data/jobs/<id>/exports/Audacity*` and includes `manifest.json` and `IMPORT-IN-AUDACITY.txt`; Waveform continues using its original output directory. All exports are versioned by unique folder names and never overwrite the previous export. After preparing, **Launch** is primary; the chosen DAW launches from its validated configured path, but importing the WAVs remains a manual step. Audacity import instructions use File → Import → Audio with all six WAV files chosen together so the six tracks start at 0:00.

**First acceptance bench: Laptop Omen**, where Audacity is reportedly already installed. Close the prior Song Harbor window, update source, relaunch, open a completed song → DAW handoff → select Audacity. Expected: Ready without install and a persisted Audacity.exe location. Prepare, Files, Launch, then import all six stems into Audacity. Test switching back to Waveform and confirm that it retains its own stored path. If Audacity is not detected, use Detect once, then Browse and report its executable path so discovery can be improved for that installation layout. No purchase or Audacity reinstallation should be needed.

Automated backend adapter tests cover existing-install discovery, independent saved paths, saved target selection, reject mismatched executables, API routes and non-destructive Audacity WAV exports. Frontend CI also typechecks the target-specific interface. **Real Omen installation detection and launch remain to be verified.**
