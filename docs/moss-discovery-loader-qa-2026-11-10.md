# MOSS local discovery and explicit loader QA
Date: 2026-11-10
Branch: dev
Status: implemented in source; Windows runtime QA not yet confirmed

## Available in Settings > Models
- Choose shared model directory and relaunch (separate from existing separator/ACE model paths).
- Scan up to 400 directories and three levels beneath the chosen shared directory. No network or auto downloads.
- Register an existing MOSS Music or MOSS Audio folder. Indexed safetensors shards must all exist; presence is not cryptographic verification.
- Paste a specific existing checkpoint directory to register outside the shared root without moving or copying it.
- Unlink only removes registry reference; never deletes checkpoint files.
- Specify an existing isolated SGLang Python executable and explicitly acknowledge custom checkpoint Python code before selecting Load.
- Load starts an offline-only localhost SGLang process on 127.0.0.1:18791; status stays Starting until /v1/models reports the expected model identity. Unload targets only the process started by Song Harbor; Windows child processes are terminated with taskkill /T. No auto-load at startup.
- Runtime logs: shared model root/.song-harbor/logs/moss-runtime.log. Shared cache: .song-harbor beneath same root.
- Only one managed MOSS process; no audio generation or inference initiated by Song Harbor during registration.

## Important limits
- Custom remote-code execution is required by upstream MOSS: do not approve unless code and runtime environment have been reviewed. The checkbox is per Settings opening and not persisted.
- The loader requires a preinstalled compatible SGLang Python environment. Installer and runtime bootstrap are not implemented.
- The registry checks checkpoint layout and completeness; it does not perform SHA-256 verification of checkpoint files or prove license, compatibility, memory fit, inference accuracy, or working audio processing.
- The 8B BF16 checkpoint is larger than the RTX 4070's 12 GB VRAM; no proven working 12 GB quantized or offload profile exists. Prefer no launch until a tested profile is documented.
- SGLang startup arguments and API readiness must be tested with the actual local runtime. The server may fail and will report a failed status with a log path. Avoid presenting readiness as evidence of actual audio comprehension.
- No shared GPU scheduler with ACE yet. Do not run ACE and MOSS simultaneously until resource policy is integrated.
- Runtime status is in-memory; unexpected parent-server crash may require manual cleanup. An app shutdown hook and/or orphan recovery should be added after Windows tests.
- No model removal, downloads, model installation, external process discovery or local inference in this slice.

## Suggested QA sequence
1. Confirm existing song opens, separator still resolves its own previous model directory, and Deshimmer still runs on split stems.
2. Set an empty dedicated model folder, save, relaunch, scan: zero results, no downloads.
3. Place an existing complete MOSS checkpoint under folder; scan, register, close/reopen Settings, verify registry persists, unlink, verify files untouched.
4. Locate an external checkpoint by pasting absolute folder path. Confirm no copying.
5. Try an incomplete safetensors index: must show Incomplete and refuse registration.
6. Try Load without trust approval and without Python runtime: blocked.
7. On a separately prepared compatible SGLang environment only, explicitly approve custom code and attempt Load. Observe Starting/Ready/Failed, actual loaded model identity, logs, peak VRAM/RAM, unload and process-tree cleanup.
8. Verify no changes to active project, approved stems, scripts, outputs or candidate assets.

## Tests
Source tests: app/backend/tests/test_model_registry.py
Run: python -m unittest discover -s app/backend/tests -p 'test_model_registry.py' -v
Build: npm run build --prefix app/frontend
These have NOT been run by the GitHub connector environment.

## 2026-11-10 loader hardening after main promotion
- Production main was fast-forwarded to clean-build dev commit 4cabca8. All further work here stays on dev.
- Runtime executable now persists in machine-local Settings and is validated as an existing Python executable; no automatic environment installation.
- Loader lightweight preflight checks the selected Python environment can locate the SGLang module. Missing runtime is a blocking error before model load.
- Local port is tested for occupancy before launching. A unique served model ID `songharbor-moss-<registry-id>` is provided to SGLang and must match /v1/models to become Ready.
- Startup deadline is 180 seconds; a timeout attempts to terminate the owned process tree and reports a blocking error. Windows worker process trees are terminated on Unload. A best-effort shutdown handler is registered for ordinary backend exits.
- New model launches are rejected while Song Harbor audio processing jobs are active. Other external GPU services (including ACE) are not yet governed by a shared scheduler: do not attempt concurrent heavy loads.
- Discovery recognizes both `MossMusicModel` and `MossAudioModel` config architecture strings. Model files are inspected, not deserialized or hashed.
- A clean frontend build was reported by the user on the pre-promotion head. These subsequent loader commits have NOT yet been built or runtime-tested on Windows. Treat this as a source implementation pending QA.

## Additional Windows QA
1. Settings > Models: save runtime Python path; reopen Settings and relaunch to ensure persistence. A missing path must show an explicit failure without changing configuration.
2. Scan directories and register both MOSS architecture families; verify registered model state survives restart.
3. Attempt Load without checkbox; confirm explicit error. Attempt Load with non-SGLang Python executable; confirm blocking preflight error and no child process.
4. Confirm an occupied port 18791 refuses launch even if /v1/models is unavailable.
5. With a compatible runtime and checkpoint, explicitly Load and inspect Starting -> Ready, model ID match, Unload -> Unloaded, no orphan child processes, and no network downloads.
6. Simulate failing SGLang startup; confirm Failed and error log path. Confirm timeout cleanup of child processes.
7. Build: `npm run build --prefix app/frontend`. Backend: `python -m unittest discover -s app/backend/tests -p 'test_*model*.py' -v`; also test shared model settings explicitly.

## Windows host / WSL2 integration note
Official SGLang deployment commonly targets Linux/WSL2, not native Windows. The managed Python loader is source implemented but not a validated native Windows execution path. A separate Connect WSL action now attaches to a server already running on localhost port 18791; it does not launch WSL, download weights, or kill the external service on Disconnect.

To make Connect WSL available:
1. Register a checkpoint folder visible to Song Harbor (existing Windows folder / WSL-mounted volume; no copying).
2. Start your **existing** compatible SGLang installation inside WSL2 with the model path translated to its Linux path and with flags `--host 127.0.0.1 --port 18791 --trust-remote-code --served-model-name songharbor-moss-<registered-id>`. The registered ID comes from the registry API; do not substitute the model display name.
3. In Settings > Models, click Connect WSL. A matching /v1/models response yields Connected. Disconnect removes only the Song Harbor connection and does not stop the Linux process. Shut it down inside WSL using its own terminal/supervisor.

WSL launcher installation, executable discovery, direct WSL process start/stop, quantized 12 GB profiles and GPU resource coordination with ACE are follow-up engineering work, not completed in this slice. No actual Windows/WSL MOSS run has been verified.

## 2026-11-10: D-drive WSL discovery and loader visibility update
User QA: dev relaunch clean, but Load was effectively hidden until a checkpoint was registered. Corrected to a visible Settings > Models > MOSS loader section with WSL distro selection, Inspect, a registered-model picker and explicit Load MOSS / Unload actions. Compact inline blockers now explain missing checkpoint, Python path, or custom-code approval.

### WSL installation
- Discover registered distros through `wsl.exe --list --quiet`, handling Windows UTF-16 output; never reinstall an existing distro.
- Explicit optional Ubuntu install from Settings requires a new dedicated non-system-drive location and an approval checkbox. Uses documented `wsl.exe --install --distribution Ubuntu --location <folder> --no-launch`, after checking CLI support for `--location`. Install is asynchronous, with status and log under the shared model root.
- Installing Ubuntu may require administrator rights, network transfer and/or restart. No install has been run on the test machine.
- This does not relocate an existing distro. In particular, the user's D: WSL installation must be discovered and reused without mutation.
- Installing compatible SGLang, CUDA dependencies, or model checkpoints is NOT implemented by the Ubuntu installer and requires a separate explicit install workflow once runtime compatibility is verified.

### Runtime and checkpoint discovery
- Inspect WSL distro for Python candidates and basic GPU-tool visibility; candidate locations can be edited.
- Register an existing checkpoint via a Windows-accessible path OR a Linux path inside the selected WSL distribution. Linux checkpoint metadata is inspected through bounded Python commands in the selected distro without importing model code or loading weights.
- Managed WSL launch uses the registered checkpoint, an existing WSL Python environment with importable SGLang, localhost model identity, and offline Hugging Face settings. Cache paths are located beneath the shared model root (set this to D: before launch).
- WSL worker shutdown attempts to terminate only the owned uniquely named SGLang server; refuses to report Unloaded if the server is still present. No actual WSL model launch or stop was tested.
- A visible Load control is not proof that the required model, compatible SGLang fork, quantization or VRAM profile is present. Full model install/verification remains a separate gate.

### QA for the next relaunch
1. Settings > Models should open with visible MOSS loader even with zero models. Detect WSL should list the existing D: Linux distribution without installing anything.
2. Inspect should show Python candidates and GPU visibility; missing optional nvidia-smi or virtualenv must not be displayed as a fatal crash.
3. Try Register WSL path to an existing MOSS checkpoint, if one exists; otherwise confirm explicit refusal without side effects.
4. Do not attempt full inference on the active workstation until the exact SGLang MOSS branch and 12 GB VRAM/offload profile are verified.
5. If testing optional Ubuntu installation, choose a new D: directory and verify no distro overwrite, download/start approval, status feedback and safe error on unsupported WSL CLI.
6. Tests: `test_model_registry.py`, `test_wsl_model_bridge.py`, `test_shared_model_settings.py`. Frontend CI and single-server smoke must be green before promotion.
