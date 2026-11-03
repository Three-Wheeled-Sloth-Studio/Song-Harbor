# Deshimmer evaluation and Song Harbor integration handoff
Date: 2026-11-03
Status: Research + user listening QA only. No Song Harbor code changes or validated bridge.
Local external checkout: `D:\Apps\deshimmer`
External repo: https://github.com/TheApeMachine/deshimmer (MIT)
Related repos: https://github.com/geeknik/ai-audio-fingerprint-remover (MIT, deprecated 2025-12-09); successor https://github.com/geeknik/mmm (CC0 repository, experimental).

## Executive summary
- User launched Deshimmer locally via `uv sync` and `uv run deshimmer-ui` (local Gradio UI at http://localhost:7860).
- Listening result: cleaned audio sounded substantially clearer; removed/diff signal contained considerable content, perceived mainly as shimmer. User did not notice obvious loss of musical effects in the initial preview.
- QA concern: full WAV render sounded perceptibly different from the Full Song Mode browser preview, with vocals more prominent relative to softened/diffused, less punchy percussion. This might be musically useful but is not an acceptable silent change for a repair process.
- Online AI detector continued flagging approximately 100%, subsequently 95% AI; this is NOT evidence for or against audible repair quality, and should not be optimized as an objective. Detector identity, calibration, files and exact tests were not supplied.
- Decision: favor a pinned, isolated Python Deshimmer adapter returning non-destructive repair candidates into Song Harbor's existing Sound Cleanup / Try Fix / Accept / Discard flow; keep restoration separate from creative enhancements. Do not build universal plugin hosting first.
- Analysis only, no code change committed to Song Harbor in this task except this document/handoff pointer.

## Core upstream architecture confirmed
Relevant source:
- `src/deshimmer/api.py`: `process_audio(x, sr, params, master_params, include_residuals)` accepts mono/stereo NumPy, returns processed audio plus measurements/residuals. `slice_with_context()` allows region processing with preceding/following temporal context.
- `src/deshimmer/ui/handlers.py`: `run_once()` and `render_full_to_files()` both call `process_audio()` with UI parameter state. Short preview trims context and optionally performs loop crossfade; Full Song Mode processes entire input for browser playback; full export rerenders the entire input and writes 24-bit PCM output/difference WAVs and parameters JSON with `soundfile`.
- `src/deshimmer/ui/audio.py`: Gradio playback returns float32 arrays; input conversion clips to [-1,1]. Browser output and file playback may differ even with same DSP; need objective aligned PCM comparison before attributing to DSP.
- `src/deshimmer/ui/app.py`: `a_out` has `autoplay=True`; knobs are bound to rerun `run_once` on change/release, explaining unwanted frequent preview playback. A small upstream UI change to `autoplay=False` would stop spontaneous playback, though computation would still rerun.
- `src/deshimmer/core/pipeline.py`: `Params.enhance=True` by default activates L/R micro-delay alignment and spectral balancing. Tonal self-consistency repair is also active by default (0.5).
- `src/deshimmer/autotune/analyzer.py`: 'Set from audio' is NOT report-only; it updates many DSP knobs. `Optimize` runs multi-stage Optuna/NSGA-II searches and replaces settings. `Render Full` does not invoke Optimize. Save a preset/JSON before Optimize or further auto analysis.
- `src/deshimmer/ui/presets.py`: built-in defaults and user preset management.
- `src/deshimmer/autotune/scoring.py`, `docs/autotune_optimizer.md`: six proxy objectives: artifact reduction; musical preservation; leakage of musical transients/harmonics into diff; stereo integrity; loudness/spectral balance; tonal coherence. These are not independent perceptual listening scores.

## User's Set from audio diagnostic report (verbatim measurements)
- Shimmer band: 3300-14100 Hz; prominence 7.5 dB.
- Estimated noise floor: -179.8 dBFS (not credible as a practical measured ambient/noise floor; derived from very small spectral values).
- Stationary whines: none.
- Tonal balance band energies: Sub_Bass -32.3 dB, Low_Mid -46.0 dB, Mid -53.6 dB, Presence -61.1 dB, Air -72.2 dB. These are mean STFT band energies, NOT conventional per-stem loudness/EQ targets.
- Dynamics: crest factor 16.7 dB, dynamic spread 35.5 dB; analyzer labels healthy.
- Stereo: overall L/R correlation 0.64; sub side/mid ratio 0.45. The ratio exceeds analyzer's 0.22 threshold for enabling mono bass, but such low-frequency stereo may be an intentional feature of this mix.
- Tonal family consistency: user 1 family / 0.94 cents p95 disagreement; quiet 0 families; loud 2 / 6.05 cents; trans 0; tail 5 / 5.42 cents. Do not overinterpret low sample counts or self-referenced estimates.
- Analyzer reported automatic high-frequency swish/decorrelation, tonal EQ, mono bass and bass-tightening decisions. Analyzer source confirms these knobs are set from heuristic thresholds, not a proof of audible defects.

## Exact user-supplied effective processing settings (post manual adjustments)
The complete JSON was supplied in the chat on 2026-11-03 and is the source of truth; salient values transcribed here:
```json
{
  "start_hz":3300,"end_hz":14100,"edge_hz":540,
  "n_fft":2048,"hop":512,"flat_start":0.2,"flat_end":0.2,
  "freq_med_bins":9,"thr_db":8,"slope":0.6,
  "density_lo":0.02,"density_hi":0.15,
  "flux_thr_db":6,"flux_range_db":8,
  "noise_resynth":0.2,"mix":1.0,"enhance":true,
  "tonal_repair":0.5,"tonal_max_shift_cents":25,
  "denoise":0.2,"dn_start_hz":120,"dn_end_hz":16000,
  "dn_floor_db":-18,"dn_attack_ms":39,"dn_release_ms":120,
  "deres":0.3,"deq_start_hz":180,"deq_end_hz":12000,
  "deq_thr_db":6,"deq_max_att_db":8,"deq_persist_ms":600,
  "expander":false,"hpss":false,
  "magnitude_inpaint":true,"deq_inpaint":true,
  "total_att_cap_db":12,"nuclear_mode":false,
  "ms_process":false,"phase_blur":0.1,
  "swish_repair":0.35,"swish_start_hz":2800,"swish_end_hz":14600,
  "hf_decorrelate":0.2,"hf_dec_start_hz":4500,"hf_dec_end_hz":16000,
  "hf_resynth":false,"temporal_masking":true,
  "tonal_balance":0.5,"tb_air_db":2,
  "transient_punch":0.2,"bass_mono":false,"bass_mono_hz":120,
  "bass_tighten":0.1,"stereo_width":1,
  "stereo_safe_mono":false,"harmonic_enhance":0,
  "delta_listen":false
}
```
Mastering settings: `master_params.enabled=false`; values for target LUFS (-14), true-peak ceiling (-1 dBTP), DC remove, HP, limiter and normalization are present in the config but are INACTIVE when disabled. Other settings omitted above retain the user JSON values; obtain the actual exported `params-*.json` for full exact reproduction rather than rebuilding from this summary.

**Important**: User initially described turning off Mono bass and some enhancements. Actual JSON proves `bass_mono=false` and mastering off, but `bass_tighten=0.1`, `tonal_balance=0.5`, `transient_punch=0.2`, `phase_blur=0.1`, `swish_repair=0.35`, and `hf_decorrelate=0.2` remain active. `enhance=true` also activates L/R alignment and spectral balancing outside these UI knobs. Do not assume this was a shimmer-only render.

## Likely causal explanations, not yet proven
- Broad 3.3-14.1 kHz suppression may reduce percussion attacks and cymbal texture, compared with default 5.1-7.2 kHz.
- `bass_tighten`, `tonal_balance`, `transient_punch`, `phase_blur`, `swish_repair`, `hf_decorrelate` and `enhance` can change perceived balance/transients/stereo. The enabled tonal balance may add 2 dB air-band compensation, not simply subtract shimmer.
- Full Song Mode preview and WAV export call the same processing API, so a consistent material PCM difference is unexpected; investigate settings snapshot/timing, deterministic rendering, Gradio normalization, level matching, player behavior, any clipping, and output format before attributing to audio stages.
- No user WAVs, exact diff files, audio measurements, listening blind tests or local commit hashes were provided in this thread. All perceptions are user listening notes; no quantitative ABX claims.

## Immediate next tests (do these before Song Harbor integration)
1. Retain the successful exports and original source; export/save `params.json` and a named custom preset BEFORE clicking Optimize.
2. A/B original source, browser Full Song Mode, exported 24-bit WAV at matched levels. Prefer loading both preview audio and WAV into a shared aligned player if practical. Check for Gradio player normalization and compare actual sample outputs if accessible.
3. Make a 'focused restoration' candidate: keep shimmer (first test use detected 3300-14100 band), denoise 0.2 and deres 0.3; disable `tonal_balance`, `transient_punch`, `bass_tighten`, `phase_blur`, `swish_repair`, `hf_decorrelate`, and bass mono. Mastering remains off. Save as distinct preset and render.
4. A/B default narrower shimmer band 5100-7200 Hz with identical other parameters, to isolate frequency-range impact.
5. API-only A/B `enhance=True` vs `False`, `tonal_repair=0.5` vs `0.0`, avoiding confounding simultaneous changes. `enhance` is not clearly exposed as a normal UI control.
6. Only then run Optimize (e.g. aggressiveness 0.25, 15 trials/stage, 3s refine, 4 representative regions including a user-selected percussion-heavy passage), inspect every changed knob, and listen to the same aligned regions. Optimize is exploratory, not required before WAV render.
7. Inspect difference audio carefully: desirable percussion/vocal consonants/strings in the diff are evidence of collateral change. Compare the standard total diff to repair-only diff, which excludes engineering enhancements and mastering.
8. Record source/export hashes, sampling rate/channels, parameters, peak/LUFS/stereo/attack metrics and subjective findings. No automatic acceptance on numeric classifier results.

## Song Harbor integration recommendation and boundaries
- Build P0 isolated/pinned Deshimmer Python process adapter (local Windows checkout first), explicit executable/version discovery, async cancellation, bounded CPU/memory, process failure handling, file/region I/O. NOT a VST3 plugin; avoid general plugin host at this stage.
- P1 connect localized Song Harbor Sound Cleanup findings to non-destructive candidate generation (start on stems or short regions), handling exact time-origin, sample-rate, context padding, source revision and crossfades.
- P2 integrate existing Original / Current / Fix with a separate 'Removed by repair' and 'Total processing difference' audition option. Ensure controls remain visible and never auto-play after every knob change.
- P3 version immutable accepted repair asset/recipe; support undo, source hash validation and identical live versus export PCM. Do not rewrite underlying source stem.
- P4 evaluate safe multi-objective Optimize only after manual baseline is validated. Do not optimize opaque AI detector scores or remove provenance.
- Separate RESTORATION (shimmer, noise, resonances) from ENHANCEMENT (tonal EQ, stereo width/correlation, mono bass, punch, phase, mastering) in Song Harbor UI and acceptance data.
- Prior analysis estimated P0 proof ~2-3 dev days, candidate generator ~3-5, UI diff audition ~2-4, accept/export parity ~3-5, optimizer ~3-6 (13-23 dev days planning estimate, unvalidated).
- Existing single Sound Cleanup entry point and current QA harness remain canonical: `docs/artifact-fingerprint-cleanup-roadmap-2026-10-26.md`, `docs/artifact-validation-results-2026-10-27.md`, `refs/handoffs/artifact-validation-agent-2026-10-27.md`. Do not proliferate competing panels.

## Separate research: fingerprint-removal repos
- `geeknik/ai-audio-fingerprint-remover` explicitly deprecated Dec 9, 2025 in favor of `geeknik/mmm`.
- Their heuristics (frequency/periodicity/statistical anomaly labels) are not independently validated watermark proof; changed hashes prove changed audio only.
- MMM documents lossy WAV re-encoding (16-bit in README), potential poor fit for Song Harbor 24-bit workflow. Do not put either in the audio cleanup pipeline or claim that a percentage change on a third-party AI detector measures cleaned music.
- Metadata/provenance inventory and a separately labeled research bench are optional future ideas; preserve attribution and disclosures.

## Explicit handoff caveats
Research/inspection used upstream GitHub repository code, not local execution. User ran Deshimmer and auditioned outputs on their own Windows machine. No Deshimmer CLI benchmark, audio/null comparison, reproducibility confirmation, installation/bridge code, or Song Harbor build/test performed by assistant. The next thread should ask for existing exported WAV and parameter artifacts only if needed for targeted audio QA; do not make the user repeat findings already documented.
