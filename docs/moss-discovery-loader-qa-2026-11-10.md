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
