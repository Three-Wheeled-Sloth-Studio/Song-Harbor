# Audio-aware production assistants and Deshimmer cleanup

2026-11-10 | Song Harbor dev branch | implementation and research handoff

## Priority 0: Deshimmer cleanup MVP

### Implemented in source (not yet QA accepted)
- `app/backend/deshimmer_stem_jobs.py`: validates server-owned stem filenames, uses the configured isolated Python runtime, runs Deshimmer Analyze -> Optimize (conservative aggressiveness 0.35, 4 trials per stage) -> full-stem processing with mastering disabled. Single concurrent operation, bounded source identity by SHA-256, stores candidate and settings independently from original.
- `app/backend/server.py`: start, status, cancel, candidate-WAV routes. No arbitrary user-provided paths.
- `app/frontend/src/DeshimmerCleanup.tsx`: stem selection, optimize/start, polling, original/cleaned A/B using existing SharedClockAudition candidate layer, accept via existing track add and replace mask (original gain 0), discard.
- `WorkbenchTools.tsx` + CSS: full-window dark busy shield with animated spinner, disabled close/drag and explicit Cancel cleanup button. The cleanup palette button is disabled while locked.
- User action required before first use: configure `SONG_HARBOR_DESHIMMER_PYTHON` to a separately installed Deshimmer `.venv/Scripts/python.exe`. Backend probe requires `deshimmer.api.process_audio`. On target machine inspect `D:\Apps\deshimmer\.venv\Scripts\python.exe` as a *possible* location; do not presume it exists.

### Known MVP gaps (must not claim production-ready)
- No installed Windows processor tested. Frontend build/backend tests/local A/B and WAV parity unverified.
- Current A/B route is candidate layer substitution via preview mixer; candidate does not run through all original-stem effects before insertion. A/B vs accepted render may therefore differ when existing automation or effects affect the original stem. Product acceptance must explicitly QA this limitation, ideally move cleaned audio into effectiveBuffer for the original stem in both audition and export instead.
- On Accept, new track uses a replacement mask, leaving prior per-stem scripted effects attached to the original alias. A robust solution needs to transfer/rebind effects or treat the accepted repair as a version of the source stem without changing its script identity.
- Candidate status is in-memory; reloading or restarting the backend loses active status history. Candidate audio and recipe remain under cleanup_candidates. Implement manifest-backed recovery and orphan cleanup.
- No Apply/Re-optimize controls, no stored trial alternatives, no diff audition, no per-section processing, no LUFS matching or quality/preservation score. Deshimmer's Optimize is CPU-intensive. Cancel and error QA needed.
- Input/output comparison validates WAV rate, frame count, channels, PCM24, numerical finiteness and peak in child worker. Test performance/memory with long stems, voices, crash-heavy drums and silence.
- UI busy overlay is required during Analyze, Optimize, Render, Accept and candidate load. Verify no conflicting normal cleanup actions are accessible beneath shield.
- Candidate currently generates as whole-stem. Protect important transient content (crashes, growls) using original-vs-cleaned and isolated diff audition before accepting.

### Release gates
1. `python -m unittest discover -s app/backend/tests -p 'test_deshimmer*.py' -v`
2. `npm run build --prefix app/frontend`, frontend unit tests, launcher reload.
3. Real installed Deshimmer version handshake, conservative optimizer, time/cancellation budget.
4. Comparison preview vs final mix parity with source stem's own pan, width, gain, EQ, reverb, ducking and section automation.
5. Undo/remove accepted repair, restart/reopen and 24-bit export parity; no mutation of original stem.
6. Lock overlay fully blocks interactions, visibly animates during stages, safely cancels.

## Priority 1: Audio-aware accompaniment assistant

### Model choice
Explore `OpenMOSS-Team/MOSS-Music-8B-Instruct` first for music-specific audio interpretation; Apache 2.0 checkpoint. The model is ~9.1B total parameters and may exceed 12 GB RTX 4070 memory in an unquantized direct load. Benchmark supported quantized/CPU-offload inference before claiming local fit. Do not silently run multiple GPU-heavy models while ACE is loaded.
Alternative `nvidia/music-flamingo-2601-hf` for research comparison, but check current model card usage rights: an older model card states non-commercial research only. Avoid shipping commercial-facing software dependent on restrictive weights.
Simple fallback: deterministic MIDI/key/BPM/spectral analysis plus a local text LLM to draft prompts, clearly labeled non-listening mode.

### Workflow
1. Select whole song or 1-3 existing sections, provide production goal in free text (example: '2:10-2:34: add an unsettling cello counterpoint, preserve vocals').
2. Render an immutable *reference* from the current saved mix (or stem subset) and capture audio SHA, selected section timestamps, existing stem inventory, lyrics, section intent, key/BPM if available, and measured metrics.
3. Audio-understanding model returns observations with `evidence` anchored to specific ranges, `uncertainty`, and suggested instrument/roles. Ground claims in model results or measured DSP; never invent detected chords or instruments.
4. Constrain next LLM stage to a validated JSON plan: `engine` (ACE Lego/Add/Complete vs YuE2), `mode`, `target_sections`, `role`, `prompt`, `negative_constraints`, `why`, `expected_fit`. Provide ACE section-level directives; YuE2 receives global style plus plain section headers and score/ABC where supported, never ACE-style section annotations in YuE2.
5. Show editable proposal before running. Reuse existing ACE candidate submission, native Lego, source conditioning, candidate A/B/accept and volume controls. Do not build a second generator UI.
6. Score output for clipping, timestamp alignment, unrelated vocals, overlap, musical interference and section boundaries. Never automatically accept. Use provider-generated stems independently.

### MVP deliverable
'Analyze reference' -> one or more grounded suggested accompaniment plans -> edit -> 'Generate with ACE' -> existing A/B/accept. Prefer ACE over YuE2 first, because ACE Lego integration and candidates are already built. YuE2 planner can follow once prompt schema distinctions and local service endpoints are validated.

## Priority 2: Audio-aware mix/production assistant

### Proposed operation modes
- **Explain**: listen to a selected range, overlay actual Song Harbor section metrics + stems, describe likely issues, cite evidence and uncertainty; no mutations.
- **Suggest**: produce reviewable section script changes from a supported grammar only: stem.pan/width/reverb/space/eq/gain/volume/comp/duck etc. Show before/after and intended goal, make no unsupported claims like auto.gain.
- **Preview**: create an in-memory alternate automation plan, render/level-match audition against original on shared clock, show difference metrics and any headroom violations.
- **Apply**: only after explicit acceptance, update the saved section script. Provide undo with an immutable prior revision.

### Architecture
Music listening model + deterministic DSP measurements + rule/LLM planner + strict schema validator + existing section automation compiler + reversible preview. Use recorded user intent (victory-to-dread narrative, foreground vocals) as a constraint, not an inferred truth. Never let model output directly execute arbitrary directives or alter PCM.

### Practical first experiment
For Parade for the Drowned King, compare first chorus (55.876-81.653) with final chorus (154.421-182.469), then bridge 2 (130.635-154.421). Ask for 2-3 alternative arrangements. Evaluate preservation of vocals, coherence, emotional contrast, stereo/mono and headroom; report false suggestions.

## Expected order
1. Stabilize Deshimmer worker and lock/accept parity, test on Windows.
2. Add structured audio observation and prompt proposal as a sidecar to existing ACE UI.
3. Add mix suggestion/preview validation using existing section script compiler.
4. Later: quantized MOSS benchmark, optimizer profiles, diff audition, section-level repair and YuE2 guided accompaniment.

## References
- `docs/deshimmer-song-harbor-integration-plan-2026-11-03.md`
- `docs/ace-accompaniment-integration-contract.md`
- `docs/section-intelligence-sprint.md`
- Upstream Deshimmer Python API https://github.com/TheApeMachine/deshimmer/blob/main/docs/api.md
- MOSS-Music https://github.com/OpenMOSS/MOSS-Music


## 2026-11-10 Deshimmer UX correction
- Reported QA: App reload clean, busy overlay looks good; launching Deshimmer from Song Harbor failed when Deshimmer UI was closed due to short cold-import probe; A/B buttons gave no obvious playback; excess explanatory copy breached the studio UI rules.
- Reviewed canonical `Three-Wheeled-Sloth-Studio/TWS-Design-Principles/apps/App-Design-Principles.md` and `apps/Studio-UI-Style-Guide.md`: clarity of state/action, icon-first affordance, minimum necessary text, contextual dependency recovery and compact controls.
- Fix: `deshimmer_adapter.resolve_python` resolves installed Python without import; the worker imports Deshimmer itself, independently of its UI. Explicit full probe retained with 90s timeout for diagnostics only.
- Fix: cleanup candidate shows a play/pause icon with an Original/Cleaned segmented toggle. Play loads preview and starts synchronized Song Harbor playback; switching version changes the preview without restarting transport. Accept/Discard remain adjacent. Removed persistent instructional paragraphs, redundant per-toggle notices and duplicated busy text.
- Source changes are committed on dev; no machine-local frontend build or actual audio A/B was executed in the connector environment. Validate fresh launch with external Deshimmer UI closed, switching during playback, pause/resume, Accept/Discard and output parity.
- Model limitation to address separately: cleaned preview is still a candidate layer at the master bus rather than full post-stem effects insertion. Do not treat audition as mathematically identical to final accepted render until parity is verified.
