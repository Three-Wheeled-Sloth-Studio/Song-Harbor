# Guided specialist model installation (2026-11-23)

Branch: dev. Extends the isolated specialist separation experiment; no default separator or production release change.

## User workflow
- Stem Tools > Separate lists two recommended UVR-family MDX checkpoints whether installed or missing: `UVR-MDX-NET-Inst_HQ_3.onnx` for instrumental/vocal comparison, and `UVR_MDXNET_KARA_2.onnx` for lead/backing vocal experiments. The standard installed cache remains visible.
- An absent model is visibly amber, with purpose, upstream source link and a checkpoint licensing caveat. No hidden checkbox or confirmation popup.
- Install model reveals an explicit Approve install action. Only that action begins the download. The application shows busy status and then green success/red ERROR; it refreshes the selector when complete.
- The backend uses its already configured `audio-separator` runtime and owned model directory. Fixed allowlist blocks arbitrary model URLs or file paths. Files download to a temporary directory, the expected model file must exist and exceed 1 MiB, and the final file is moved into the cache only after successful exit.
- SHA-256, model ID, registry origin, timestamp and an explicit unverified-license notice are saved beside the installed checkpoint. No stem or script is modified on install.

## Constraints and known limits
- These weights are research candidates, not approved for bundling or commercial redistribution; the user should review checkpoint-specific rights. Source: https://github.com/nomadkaraoke/python-audio-separator and the maintained UVR model registry.
- No auto-download or install on merely entering Stem Tools. Installs have a 30-minute timeout and do not overwrite an existing model.
- Progress is phased/busy state; percentage is not shown because the pinned audio-separator download flow does not expose a stable byte counter.
- The experimental audition remains a non-destructive up-to-30-second candidate preview. Stereo integrity, phase alignment, A/B loudness, model-specific output categories, CUDA VRAM and Windows model runtime require actual user QA.
- Selection is currently limited to two known, curated filenames. Extend only after model provenance and licensing review.

## QA
- Python compile/test checks and automated CI build are required before QA on Windows.
- In Crown of Hollow Stars, select Vocals, open Separate, install one model explicitly, inspect status, run 20-30 second comparison. Verify that original stems and section script are unchanged. A second install should be refused as already installed.
