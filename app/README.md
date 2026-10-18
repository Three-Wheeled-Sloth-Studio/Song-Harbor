# Song Harbor M0: six-stem entry UI

This is a **local vertical slice**, not a bundled standalone installer yet. The frontend consumes components from [TWS-UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), which implements the canonical [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles). Product-specific deep blue-green theme overrides are semantic; shared controls are imported.

## Automated Windows bootstrap (recommended for Laptop Omen)

The reusable installer is [`scripts/bootstrap-windows.ps1`](../scripts/bootstrap-windows.ps1). It performs GPU, free-space, Python 3.11 x64, FFmpeg, Git, and npm checks, creates an isolated Python virtual environment, moves transient caches to the chosen work drive, pins CUDA PyTorch and compatible ONNX Runtime versions, installs the six-stem separator and UI, and verifies dependencies plus CUDA arithmetic.

**Laptop Omen uses C: as its only work drive.** The double-click launchers therefore default to `C:\Apps\SongHarbor` for Python, models, and runtime data. Generated data is stored outside the source checkout when the repo is cloned to a separate folder; this C: placement is an explicit hardware-driven exception to the preferred separate-drive policy.

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

One job at a time. Basic local-only progress state rather than fabricated percent; model downloads may delay startup. No multitrack editor, instrument playback, packaging, model selector, job persistence across app restarts, or deep licensing approval in this slice. No claims of tested production readiness before validation.

The source code sits in `app/`; generated assets, caches, model weights and imported music must remain local and untracked. The TWS design repo remains canonical rather than copying design-system source into Song Harbor.

## Laptop Omen user acceptance checkpoint (2026-10-17)

User reports **“Launcher works. Splitter works.”** for the C:-based bootstrap/launcher and M0 separation UI on Laptop Omen. This establishes user-reported functional end-to-end acceptance for the limited milestone of opening the app and separating audio, without claiming validation of every export/open-folder, error/cancel, performance, or packaging path. The core M0 entry UI + functional splitter is **accepted for the requested milestone scope**. Further tests and standalone packaging remain separate work.

## Known regression: output appears to stop at 4:00 (2026-10-17)

User reports a separation cutoff around 4:00 on Laptop Omen; root cause **not yet confirmed**. `htdemucs_6s.yaml` itself has no documented four-minute ceiling. Earlier M0 completion logic accepted any six WAV files regardless of duration. The backend now uses `ffprobe` to measure source and each stem and **reject** any mismatch greater than 0.25 seconds (instead of falsely declaring completion). Source duration, output durations, and error details are returned with the job. Added `app/backend/tests/test_duration_validation.py` for matched outputs, 4:00 truncated output, and slight container/codec duration variance. **No claim that duration validation repairs a truncation mechanism**: rerun a >4:00 source, inspect original/imported file and stem durations and backend logs, then identify/fix the cause. The prior user-reported M0 smoke acceptance covers a shorter track, not unrestricted-length separation.
