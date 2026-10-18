# Song Harbor M0: six-stem entry UI

This is a **local vertical slice**, not a bundled standalone installer yet. The frontend consumes components from [TWS-UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), which implements the canonical [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles). Product-specific deep blue-green theme overrides are semantic; shared controls are imported.

## Shared-tool setup and recovery (FFmpeg / FFprobe)

Song Harbor now treats absent FFmpeg as an **in-app setup state**, not a failed separation job. On launch, it checks the saved path in `<runtime-root>/config/settings.json`, then PATH and common installation folders. If it still cannot find both executable tools, the UI presents: **Browse…** to locate an existing install, **Search computer** (a bounded opt-in search of common app locations across available drives), or **Download and install here** to place a publisher-supplied Windows essentials build into a user-selected folder. The installer downloads the archive and associated publisher SHA-256 checksum from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), verifies the digest, extracts only `ffmpeg.exe` and `ffprobe.exe`, verifies that both run, and writes the resolved binary folder to application configuration. Source media remains untouched; no system-wide PATH changes, admin operations, or installs into shared system folders are needed. The user can revisit the setting with **Change**.

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
