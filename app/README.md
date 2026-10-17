# Song Harbor M0: six-stem entry UI

This is a **local vertical slice**, not a bundled standalone installer yet. The frontend consumes components from [TWS-UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), which implements the canonical [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles). Product-specific deep blue-green theme overrides are semantic; shared controls are imported.

## Current machine setup (Windows)

Prerequisites: Node.js + npm, FFmpeg on PATH, existing working `D:\Apps\SongHarbor\.venv` with CUDA PyTorch and `audio-separator[gpu]` already validated. Check out Song-Harbor so the repository root is `D:\Apps\SongHarbor`, or supply a root path to run.ps1 that contains the .venv and models. **Do not overwrite an existing project directory without inspecting it first.**

From a checkout of this repo:

```powershell
& "D:\Apps\SongHarbor\.venv\Scripts\python.exe" -m pip install -r app\backend\requirements.txt
npm install --prefix app\frontend
.\app\run.ps1
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
