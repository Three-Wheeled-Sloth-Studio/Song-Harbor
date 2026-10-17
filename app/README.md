# Song Harbor M0: six-stem entry UI

This is a **local vertical slice**, not a bundled standalone installer yet. The frontend consumes components from [TWS-UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), which implements the canonical [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles). Product-specific deep blue-green theme overrides are semantic; shared controls are imported.

## Automated Windows bootstrap (recommended for Laptop Omen)

The reusable installer is [`scripts/bootstrap-windows.ps1`](../scripts/bootstrap-windows.ps1). It performs GPU, free-space, Python 3.11 x64, FFmpeg, Git, and npm checks, creates an isolated Python virtual environment, moves transient caches to the chosen work drive, pins CUDA PyTorch and compatible ONNX Runtime versions, installs the six-stem separator and UI, and verifies dependencies plus CUDA arithmetic.

**Use a suitable work drive for Omen, rather than copying Skynet's D: or Predator's G: paths.** From PowerShell 7 after cloning the repository:

```powershell
Set-Location <Song-Harbor-repo-checkout>
.\\scripts\\bootstrap-windows.ps1 -Root "E:\\Apps\\SongHarbor"
.\\app\\run.ps1 -Root "E:\\Apps\\SongHarbor"
```

Replace `E:\\Apps\\SongHarbor` with a real chosen path on the machine. The bootstrap requires working Git, FFmpeg, NVIDIA driver compatible with CUDA 12.6, Node.js/npm for the UI, and Python 3.11 x64. If `uv` is present, `uv python install 3.11` can provide Python 3.11 before bootstrap. No existing unrelated Python or music-generation environment is modified.

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

- [ ] UI starts locally and imports shared TWS UI components.
- [ ] Select a supported audio file using native browser file selection.
- [ ] Six-stem model is fixed to `htdemucs_6s.yaml` for this milestone.
- [ ] Start a separation job; show truthful queued/running/complete/error status.
- [ ] Show six WAV outputs; download and open output folder.
- [ ] Confirm existing source remains unchanged; no shell invocation with untrusted file contents.
- [ ] Real 3:28 track tested end-to-end from the interface.
- [ ] `npm run build --prefix app/frontend` passes.

## Scope boundaries

One job at a time. Basic local-only progress state rather than fabricated percent; model downloads may delay startup. No multitrack editor, instrument playback, packaging, model selector, job persistence across app restarts, or deep licensing approval in this slice. No claims of tested production readiness before validation.

The source code sits in `app/`; generated assets, caches, model weights and imported music must remain local and untracked. The TWS design repo remains canonical rather than copying design-system source into Song Harbor.
