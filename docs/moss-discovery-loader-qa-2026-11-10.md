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

## 2026-11-10: in-app installer and workbench loader correction
User QA screenshot: WSL Ubuntu discovered, zero registered checkpoints, Load disabled. Requirement explicitly clarified: installation AND loading must be initiated from the Song Harbor function, not manual command-line configuration. This is a product bug, not a missing instruction.

### Implemented on dev
- In Settings > Models, new **Install MOSS** area with explicit **Install MOSS runtime** and **Download model** actions. Downloads only happen after selecting the action and checking approval. WSL is reused, not reinstalled. This area is separate from the optional Ubuntu distro installer.
- Setup runs a repo-owned Python worker inside existing WSL using wsl.exe argument vectors, not a user-authored shell command. Source and generated files stay under the shared model directory, including uv-managed Python 3.12, isolated SGLang runtime, cache, staging, logs and model weights. Configure the model root on D: first.
- SGLang installation pins the official OpenMOSS moss-audio branch at commit `c28a945853c7fee357f55d976b8abce51874bd94`. Installs SGLang from that source plus pinned recommended CuDNN and huggingface_hub. Does not start inference.
- Checkpoint download choices are allowlisted to `OpenMOSS-Team/MOSS-Audio-4B-Instruct` and `OpenMOSS-Team/MOSS-Music-8B-Instruct`. Hugging Face info is checked for Apache-2.0 license, pinned snapshot SHA and weight-file sizes before an explicit download. Downloads go to a revision-specific staging folder, check shard presence, record local SHA-256 inventory and atomically publish. A matching interrupted staging directory can resume. Local SHA-256 is an integrity baseline, not independently verified upstream authenticity.
- A completed checkpoint is automatically registered for model selection after manifest inspection. No manual folder pasting should be necessary for this install path.
- The Song Harbor production tool palette includes **MOSS music understanding**. Its popover exposes current model status, model selection, direct Load/Unload, and **Set up models**, which opens the model installer in Settings. This keeps tool use close to the authoring workflow and Settings responsible for infrequent installation.
- The underlying MOSS listening/SMU analysis workflow is **not implemented**, and model readiness does not mean audio inference is working.

### Safety gates and limitations
- The existing WSL Ubuntu distro on D: must not be replaced, relocated, or reinstalled. No model is installed or launched automatically on app launch.
- The 8B model has no validated 12 GB VRAM profile; don't claim it fits. Prefer explicit 4B initial runtime testing after approving model code. Load can still fail due GPU/runtime compatibility, with error states and logs.
- The pinned SGLang installer is source implemented, not yet run on the user's WSL installation. Actual pip/uv resolution, 4B load, WSL stop and Windows application navigation require validation.
- The separate **Install WSL** action is for users with no Linux distribution; it should not be used on this workstation.
- Installer setup state is in-memory during a backend session; verified completed files and manifest persist. Unexpected restarts may leave a partial download staging folder which can be resumed only if the repository and revision marker match.
- Do not modify song projects, audio files, source stems, scripting, or approved candidates.

### QA next
1. Relaunch dev; verify new MOSS production tool icon opens its own model control and its Set up models action opens Settings > Models.
2. Select existing Ubuntu and inspect. Confirm active model root is on D:, rather than system drive.
3. With explicit approval, click Install MOSS runtime; verify stage/status/log, pinned commit, isolated Python and path on D:. No automatic model download occurs.
4. Explicitly choose MOSS-Audio-4B-Instruct and Download model; verify disk preflight, staged transfer, manifest, registration and dropdown selection.
5. Explicitly approve checkpoint code and load from the production tool. Confirm starting, ready/error, no unintended inference, unload process cleanup.
6. Simulate insufficient disk space, disconnected network and interrupted transfer; verify clear errors, unchanged files and safe resumability.
7. Do not promote until actual Windows runtime results, smoke tests and unaffected active song verified. CI backend's two unrelated test failures are tracked separately.

## 2026-11-10 Ubuntu ensurepip bootstrap failure and repair
User reported explicit Install MOSS runtime failed immediately: `/usr/bin/python3 -m venv` returned `ensurepip is not available`, suggesting `python3.12-venv`. This occurs before SGLang, model checkpoint download or GPU inference. No project/audio changes.

- Root cause: our bootstrap incorrectly required the system Python `venv` and `pip`, even though the selected Ubuntu distro may not include Debian's optional `python3-venv` package.
- Repair: remove system `venv`/`pip` dependency from `ensure_uv`. Use a pinned standalone Astral uv 0.13.7 Linux binary downloaded into the selected shared model directory (`tools/uv-0.13.7`), verify the release archive against the published `.sha256`, extract only the standalone executable and verify its version. If uv is already available at our validated path, reuse it. Does not use shell-piped installer scripts, apt, sudo, or system Python modifications.
- The failed `bootstrap/` folder is left untouched and ignored by the new bootstrap path. No manual cleanup should be needed for retry. The user must explicitly click Install MOSS runtime again after updating dev. No downloads are performed on application launch.
- Installer now surfaces the last `ERROR:` from its log in the main error indicator, rather than only the generic 'See job log' message. The expandable log remains available.
- Tests added for synthetic standalone uv tar checksum success, checksum failure, and precise error reporting, without network access or executing downloaded model code.
- This repair solves the immediate ensurepip failure path. Full real WSL runtime package resolution, WSL NTFS (drvfs) executable/symlink behavior, and model loading are still awaiting Windows QA. An error in a subsequent stage should be reported with exact log text; don't treat successful uv bootstrap as proof of SGLang compatibility.

## 2026-11-11: Installer progress and load approval UX
User QA: WSL installed; runtime and two checkpoint entries visible. No activity animation for long runtime/checkpoint jobs; approval checkbox unexpectedly cleared after each install; model Load disabled by an unassociated custom-code checkbox below controls. Also requirement: production tool must handle selection/loading at point of use.

Changes on dev:
- Installation approval remains checked through sequential explicit actions, but each action still requires clicking Install/Download. Never automatically download or load based on checkbox state.
- While backend job state is running, Settings shows a compact animated activity spinner, explicit runtime-install vs model-download label, and ongoing status. The existing expandable log continues to provide real output. No fabricated progress percent.
- Settings Load no longer depends on a detached approval checkbox; pressing Load presents a contextual confirmation for the chosen model, with explicit custom-code approval and Confirm/Cancel beside the action. User agreement remains per-load, never persisted.
- Same contextual Load confirmation in production tool. On opening the tool, installed checkpoints and WSL runtime are discovered; 4B is the preferred initial selection if available, but explicit user choices are preserved. Settings now also queries the installed runtime's Python path as soon as WSL is selected, without requiring Inspect.
- No audio listening or Shared Musical Understanding analysis has been enabled yet; Ready must not be described as a completed musical recommendation. No changes to active project, rendering or scripting.

QA: verify the busy indicator remains visible during long installs/downloads, including after reopening Settings; ensure approval remains checked after a completed operation, and that no new operation auto-starts. Verify contextual confirmation appears immediately when Load is clicked in the production tool; cancel performs no load. After confirm, Starting should show a spinner and transition only on actual runtime state. No inference tests without separate authorization.

## 2026-11-11: Loading failed (exit 1), wrong log path and repeated code approval
User QA: model production-tool load failed with exit 1; user could not find claimed .song-harbor/logs/moss-runtime.log in the repo or application root. Existing WSL loader actually writes to the shared model directory at `D:\\Apps\\SongHarborDev\\models\\.song-harbor\\logs\\moss-wsl.log` (when model root has default value). Never display a relative misleading filename.

Changes on dev:
- Native and WSL runtimes each report the actual absolute log path. Read-only diagnostics endpoint returns a bounded log tail, and production tool and Settings show Failure details inline so users need not hunt for files. The reported process failure remains blocking, and Failed status remains visible until a new load attempt or successful unload; no false Ready state.
- One-time consent for installed models: the checkpoint's local installer manifest, repository/revision and inventory fingerprint act as a stored approval key. Explicit approval for this version may be reused on subsequent loads. A different manifest revision/inventory invalidates consent. Manual/unverified registrations and WSL-only checkpoints do not receive persistent trust and still require approval per load. This is not a license to auto-load or infer; every Load remains a deliberate user action.
- On the production tool, trusted loads no longer prompt for the checkbox; untrusted models show a contextual first-load code consent. Settings mirrors the behavior.

Validation required: Windows relaunch, verify failure log path is absolute and details show process output, identify actual reason for exit code 1 before changing inference parameters. Confirm remembered approval on subsequent loads of the same installed model and re-prompt on manifest change. No model load attempted from this environment.
