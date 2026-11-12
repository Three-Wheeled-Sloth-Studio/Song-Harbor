# MOSS quantization feasibility on RTX 4070 12 GB
2026-11-11 | Investigation only | dev | No installs, model downloads or inference authorized or executed

## Decision
**Do not abandon local MOSS yet.** Two genuinely model-specific candidate routes exist. Neither is validated end to end on our workstation. Do not expose a selectable 'supported' 4-bit profile or remove the existing safety blocker until one passes actual loading, audio-input and resource-release tests.

- **Track A: OpenMOSS SGLang 4-bit BitsAndBytes (on-the-fly)**. Best route for reusing the current in-app model lifecycle and API, but may take substantial time to load BF16 source shards from /mnt/d and may peak higher during dynamic quantization.
- **Track B: CrispASR MOSS-Audio Q4_K GGUF**. Strong fallback and potentially preferable for a local desktop application. A complete multimodal (audio encoder + adapter/DeepStack + Qwen3 decoder) C++ implementation and a published Q4 checkpoint exist. Third-party conversion/runtime must be inspected and benchmarked; do **not** substitute text-only MOSS-Music GGUFs.

## Reproduced failure / constraints
- User's 2026-11-11 uploaded SGLang log: MOSS-Audio-4B loads 3 safetensors shards in 668.98s on WSL /mnt/d; reports 10.79 GB used / 0.00 available after weights, then `RuntimeError: Not enough memory` in KV-cache initialization (mem_fraction_static=0.696). 15-min wrapper timeout is secondary.
- OpenMOSS MOSS-Audio-4B is approximately 4.6B parameters with Qwen3-4B LLM and separate audio encoder. MOSS-Music's current released variants are 8B, around 9.1B total parameters; a 4B Music model is not currently documented as released.
- The 12 GB RTX 4070, 96 GB system RAM and D: WSL installation require small-model/quantized or explicitly validated offloaded operation. Other production GPU jobs must have priority.
- CUDA SM89 can satisfy SGLang's BitsAndBytesConfig minimum capability 70, but this is **not** an end-to-end model compatibility or throughput guarantee.

## Track A: specific evidence in pinned fork
Inspected commit `c28a945853c7fee357f55d976b8abce51874bd94` in `OpenMOSS/sglang`:
- `python/sglang/srt/models/moss_audio.py`: `MossAudioModel` declares `default_bitsandbytes_target_modules` (Q/K/V/O and gate/up/down) and `bitsandbytes_stacked_params_mapping`, and passes `quant_config` to its Qwen3 language backbone. The audio encoder is instantiated separately, so not every module is necessarily quantized.
- `python/sglang/srt/model_loader/loader.py`: `BitsAndBytesModelLoader` selects the model's default target modules, streams source safetensors, quantizes selected weights in `_unquantized_generator`, then calls the model's `load_weights`. Its 4-bit quantization runs on GPU and may introduce **peak** VRAM stress.
- `python/sglang/srt/layers/quantization/bitsandbytes.py`: 4-bit default enabled; CUDA capability >=70; `bitsandbytes>=0.46.1` required by the linear layer method.
- The fork's documented CLI/load path includes `--load-format bitsandbytes` and `--quantization bitsandbytes`. Exact combination and current environment dependencies need an offline preflight and a bounded, manually approved test. Do not silently add flags to production launch.
- Generic FP8/AWQ/GPTQ/torchao availability in SGLang does not establish MOSS-Audio interoperability. AWQ/GPTQ require compatible pre-quantized checkpoints and/or model-specific calibration. NVIDIA Blackwell-only FP4 is not a path for SM89.

**Risks**: quantizer weight naming/stacked mapping; non-quantized audio encoder/embedding and activation memory; temporary GPU allocations during conversion; slow /mnt/d shards; missing BitsAndBytes wheel; runtime audio input quality; model-specific SGLang fork divergence. Preserve full-precision checkpoint and don't use /mnt/d in-place edits. Distinguish syntax/preflight success, loaded-ready service, successful audio question, and useful answer.

## Track B: actual full-audio GGUF alternative
- Third-party Hugging Face: https://huggingface.co/cstr/MOSS-Audio-4B-Instruct-GGUF
- Source runtime: https://github.com/CrispStrobe/CrispASR
- The model card publishes a `moss-audio-4b-instruct-q4_k.gguf` and claims full encoder, 3 DeepStack taps, adapter and Qwen3 decoding. The source repo on main contains `src/moss_audio.cpp` and `models/convert-moss-audio-to-gguf.py` matching those architectural components.
- C++ runtime supports `--backend moss-audio --prompt <question> -f <audio.wav>`, generic ggml CUDA/Vulkan/CPU backends, and no SGLang Python dependency. Source references code paths for native GPU/CPU fallback. Thus it is not *automatically* text-only like some GGUF conversions.
- Some MOSS-Music-8B GGUF repositories explicitly contain only the LLM backbone and no audio projector, so cannot replace MOSS musical listening.
- Third-party model card's advertised file-size table and Hugging Face listing have inconsistent reported file sizes; verify the exact immutable artifact size/hash via the provider before use. No inference or GPU/quality benchmark on our machine has been done.
- License review: CrispASR GitHub metadata MIT; upstream MOSS-Audio weights Apache-2.0. The community quantization still requires supply-chain/source review, pinning, manifest verification and explicit opt-in download. Never install a random GGUF simply based on a filename.

## Prioritized validation plan (all in-app, explicitly approved)
0. First verify prior owned WSL worker is stopped and VRAM returned via `nvidia-smi` baseline; do not run simultaneous ACE, separators, or production jobs.
1. **Read-only preflight for BnB**: probe selected isolated WSL Python for `bitsandbytes>=0.46.1`, `torch.cuda.get_device_capability`, pinned fork classes, allowed load-format/quantization flags. No imported checkpoint weights or downloads. Verify free disk space, and read-only cost of source file.
2. **One bounded BnB proof**: when separately authorized, make one explicit 4-bit experimental launch with per-phase logs, VRAM samples, maximum allowed startup time, and owned-process cleanup. Respect the existing 12GB unquantized blocker; this is a distinct experimental profile only. Do not claim success until /v1/models matches ID and an audio-question API actually returns.
3. **CrispASR alternative proof** if A cannot pass: inspect pinned release and full-multimodal source, verify checksum and runtime license, make optional self-contained install under shared model directory, first CPU proof to check audio support then RTX4070 GPU test. No automatic upgrade or download.
4. **A/B task sample**: 15-30s excerpts from a non-active test copy, ask about instrumentation, rhythm, arrangement transitions, and expressive dynamics; include at least two different genres and at least one 'what happens at time' prompt. Compare actionable Structured Musical Understanding evidence and false claims with audible reference. Measure peak VRAM, load time, warm inference time and reclaimed VRAM.
5. **Go/no-go**: retain MOSS if either path has verified multimodal output, fits 12 GB without destabilizing production, and returns sufficiently actionable musical observations on short excerpts. Provisional experience target: 30s clip in roughly one minute warm processing (a design target, NOT a measured benchmark); slower may still be useful as optional offline analysis if quality is strong. If neither path meets criteria, pivot to modular MIR/audio-analysis tools feeding shared schema, not an abandoned architecture.

## Integration rules
- Use shared model registry with a per-model `backend` and `profile` (sglang-bnb-nf4 / crispasr-q4), manifest and provenance. Never share one loader's flags with another.
- No change to audio, approved stems, scripting or active projects. Treat analysis outputs as read-only candidates with source hash, audio span, model revision, quantization profile, inference engine, timestamps, confidence/limitations and invalidation rules.
- Maintain explicit user control of installing and loading. Child process groups must be terminated and VRAM reclamation observed. Disable unsupported profiles with useful errors, not hidden checkboxes.
- Reuse current MOSS tool and in-app model directory. Native Windows runtime for C++ is a potential escape from WSL DrvFS load overhead; benchmark before claiming a gain.

## Primary evidence
- https://github.com/OpenMOSS/MOSS-Audio
- https://github.com/OpenMOSS/MOSS-Music
- https://github.com/OpenMOSS/sglang/tree/c28a945853c7fee357f55d976b8abce51874bd94
- https://github.com/OpenMOSS/sglang/blob/c28a945853c7fee357f55d976b8abce51874bd94/python/sglang/srt/models/moss_audio.py
- https://github.com/OpenMOSS/sglang/blob/c28a945853c7fee357f55d976b8abce51874bd94/python/sglang/srt/model_loader/loader.py
- https://github.com/OpenMOSS/sglang/blob/c28a945853c7fee357f55d976b8abce51874bd94/python/sglang/srt/layers/quantization/bitsandbytes.py
- https://huggingface.co/cstr/MOSS-Audio-4B-Instruct-GGUF
- https://github.com/CrispStrobe/CrispASR/blob/main/src/moss_audio.cpp
- https://github.com/CrispStrobe/CrispASR/blob/main/models/convert-moss-audio-to-gguf.py
