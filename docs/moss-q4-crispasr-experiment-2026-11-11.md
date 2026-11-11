# Experimental MOSS-Audio Q4 hook
2026-11-11 | Song Harbor dev | Prototype boundary, not an approved inference backend

## Source and intent
The Q4 candidate is the **full MOSS-Audio-4B-Instruct** quantized GGUF published at
https://huggingface.co/cstr/MOSS-Audio-4B-Instruct-GGUF. Its model card describes the
full audio encoder, DeepStack and Qwen3 language components, with CrispASR as the
dedicated C++ runtime (https://github.com/CrispStrobe/CrispASR). This is **not**
a text-only GGUF. The license notices and version of both runtime and model
must be checked before distribution.

The goal of this slice is a discoverable local experiment from the *existing*
MOSS function in the Song Harbor production tool palette. There is **no**
automatic download, model conversion, CLI installation or inference at startup.

## Implemented
- MOSS palette tool includes a compact **Q4 GGUF / CrispASR** Experimental
  section with Open/Hide; the existing OpenMOSS/SGLang model control is unchanged.
- Bounded path discovery in configured shared model directories and tools folders.
  Supports both `crispasr.exe` and `crispasr-cli.exe` executable names.
- Explicit local executable and model selection with native Windows Browse pickers. Verifies file presence, GGUF
  header and Q4 MOSS-Audio name before saving configuration. This **does not**
  authenticate or prove the model's architecture; only model-source review and
  actual inference will do that.
- Direct links in the tool to the runtime releases and model publisher. User
  obtains these separately for now; no hidden multi-GB downloads.
- Explicit user-provided local WAV *test copy*, separate from the active project, selected through Browse or a pasted path.
  Verifies WAV header, file size <=200MB, nonempty question <=400 chars and
  per-run approval. Runs a fixed argument-vector `crispasr --backend moss-audio
  -m <absolute-gguf> -f <absolute-wav> --prompt <question>`, **never**
  `-m auto` or `--auto-download`.
- Experiment is a one-shot subprocess, **not** a resident SGLang model.
  Working state, cancel, 10-minute cap, background timeout monitor and
  append-only log in `<Song Harbor runtime>/logs/moss-q4-experiment.log`.
  Backend cleanup on normal shutdown. No project media or scripts are mutated.
- Output is labeled unverified regardless of exit code. No attempt to translate
  free-form text into Shared Musical Understanding assertions or ACE directions
  at this stage.
- API guarded against current Song Harbor audio jobs and another loaded MOSS
  service. Q4 source and runtime remain optional.

## QA gates
1. Relaunch dev; open **MOSS music understanding > Q4 GGUF / CrispASR**.
   Discover should be read-only and should *not* launch/download anything.
2. Obtain a pinned, reviewed CrispASR release and the full MOSS-Audio Q4_K GGUF
   using the linked publisher references; place on D:, then use **Use local files**.
   This slice does not yet provide an in-app binary installer/downloader.
3. Use a **separate** short test WAV, not the active song project; click Test Q4
   listening with explicit approval. Confirm command output in the application
   logs. Successful exit is not sufficient to approve production use.
4. Compare audio description with audible source and test at least one instrument
   change and temporal transition. Assess latency and peak GPU VRAM.
5. Cancel a running test and verify process termination / VRAM recovery. Verify
   normal Song Harbor shutdown cleans up the experiment. Forced app crashes
   are not yet covered by orphan identity recovery, unlike SGLang.
6. Validate model authenticity/provenance through content hash before building
   an automatic installer. Avoid assuming advertised Q4 sizes are consistent.
7. Do not merge to main until Windows testing and audio inference quality pass.

## Limitations
- Not a turnkey in-app CrispASR installer yet; paths require an existing
  binary and full-audio GGUF. This is an experimental hook for evaluation.
- No validated output quality, speed or memory profile on the RTX 4070 12 GB.
- The test runner is Windows-native and one-shot. It does not preload a model
  or expose a resident server, and will release its resources when it exits.
- The source-derived architecture and publisher examples do not constitute
  independent validation of the community model.
