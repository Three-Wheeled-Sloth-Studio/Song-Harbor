# Artifact / fingerprint cleanup — implementation exploration
Date: 2026-10-26
Status: research and architecture recommendation; **no new detector, model download, audio processing, or release candidate changes**.

## Decision in one sentence

Build **source-aware, localizable, reversible artifact repair** into existing Song Harbor Sound Cleanup, while keeping AI origin/fingerprint classification as a separately labeled offline research bench. Never use detector-score suppression or provenance removal as a mastering objective.

## Current checked implementation

The repository already has:
- `app/frontend/src/AudioCleanupAnalyzer.ts`: inspectRenderedAudio runs on a fully rendered in-app float mix. Detectors cover sample peak/headroom (not true peak), abrupt jumps, flat-tops, repeated level dips, stereo anti-correlation, and sustained 2.5–4.9 kHz harshness, sibilant/high-fizz and noise-like energy. Results have approximate positions, not proof of source or cause. Up to 48 returned.
- `app/frontend/src/SignalAudit.ts`: sampled 4096-FFT scan, max 600 distributed analysis windows, looking for persistent narrowband lines from 4–11.5 kHz. It explicitly **cannot identify watermarks or generator fingerprints**. A repeated synth resonance can score.
- `app/frontend/src/ForensicsReview.tsx`: separate experimental inspector with grouping/filtering, seek and loop; **reuses the same findings** as Sound Cleanup, not an independent pretrained classifier.
- `app/frontend/src/CleanupReview.tsx`: regional loop and seek; existing try-correction A/B presently offered for headroom and pumping only. Other categories have listening suggestions, not repair actions.
- `app/frontend/src/SharedClockAudition.ts`: current live/offline mix graph and on-demand analysis; source stems available in the project, which makes future attribution and A/B possible.
- `docs/ai-audio-forensics-discovery.md` and `docs/remote-daw-waveform-restoration-discovery.md`: existing exploration and cautions.

Gaps: no aligned original->export/stage diff, no per-stem culpability score, no spectrogram time-frequency region overlay, no click or spectral repair candidate generator, no objective true-peak/integrated LUFS pipeline in this analyzer, no robust user-reviewed repair ledger, and no production-general AI fingerprint detection model. Do not overstate finished capabilities.

## Why generator fingerprint scores are not a cleanup target

1. **Provenance**: embedded credentials or watermark schemes are separate from audible signal defects. Retain records and disclosure; do not attempt to strip provenance or misrepresent generation.
2. **Generator spectral residuals**: architecture-specific periodic components may identify particular old Suno/Udio engines, but a score dropping after EQ, resampling, denoise, limiting or codec changes does not prove better sound.
3. **Audible defects**: clicks, warped harmonics, smeared attacks, harsh upper mids, pumping, mono cancellation, poor transitions, clipping, vocal formant/sibilance flaws and separation bleed. These can be identified, isolated, A/B tested and often repaired.
4. **Artistic texture**: industrial distortion, metallic cymbals, sustained synth harmonics and intense compression are *often intentional*. Require a context-sensitive listening judgment.

## Candidate technologies — validated scope and caution

| Candidate | Utility | Integration assessment |
|---|---|---|
| Existing TypeScript Analyzer + SignalAudit | Starting point for audible issue detection, timecode/loop and mix playback | **P0 — extend rather than replace**; no model/GPU |
| **KillrBee/ai-music-detector** | Heuristic multi-domain ideas: spectral/temporal/spatial/vocal analysis, breath/formant and timbral consistency | **Method reference only**; heuristically weighted “AI probability” trained/tuned on a small calibration sample. README says MIT, but confirm repository current license before copying any implementation; build independent tests rather than importing wholesale |
| **lofcz/ai-music-detector** | MIT ONNX/CQT/Suno-Udio-specific “fakeprint” spectral classification | **Optional P2 forensic sandbox**, trained for specific generators. No reliable claim for ACE 1.5/YuE2 or mastered hybrids; not a repair quality metric |
| **lcrosvila/ai-music-detection** | Transform robustness, validation methods; Essentia/CLAP embedding source classifiers | **Research only**, too heavy for realtime/local repair and rights of code/weights need validation |
| **Spotify pedalboard** | CPU offline effect renderer and third-party VST3 hosting on Windows | **P1 repair engine candidate**; good backend for reversible de-esser/EQ/gate etc after latency/automation/plugin licensing tests, not itself an AI-restoration solution |
| **DeepFilterNet** | Full-band 48-kHz learned noise suppression focused on speech | **P2 optional isolated vocal stem experiment**, not a default full-mix music enhancer; watch lost breath, consonants and reverb. Assess local Windows packaging/runtime/licensing |
| **iZotope RX** | Mature de-click, de-clip, spectral denoise/repair tools | **External specialist benchmark / manual DAW handoff**, proprietary and not assumed callable from Song Harbor |
| **facebookresearch/denoiser** | Neural speech denoise reference | **Deprioritize**: archived, CC-BY-NC; unsuitable to bundle as production dependency without rights review |

References:
- https://github.com/KillrBee/ai-music-detector
- https://github.com/lofcz/ai-music-detector
- https://github.com/lcrosvila/ai-music-detection
- https://spotify.github.io/pedalboard/
- https://github.com/Rikorose/DeepFilterNet
- https://www.izotope.com/pages/rx-for-content
- https://github.com/facebookresearch/denoiser

## Prioritized implementation sequence

### P0 — establish actual regression and position (suggested 2–4 dev days)

- Introduce `AudioAnalysisTarget` identifying stage and asset identity: source mix, extracted stem, accepted/generated stem, effects-rendered mix and final exported WAV. Include PCM revision hash, sample rate, channels, and timeline origin.
- Align time and sample rate; account for known intentional gain, fades/tails, resampling and stem offsets. Use *stage-to-stage deltas* rather than absolute “AI” likelihood.
- Compute per-section/window: sample and oversampled/true peak, integrated and short-window LUFS, spectral centroid/rolloff, multi-band energy deviations, transient-envelope attack preservation, stereo correlation, mid/side ratio, mono loss, large sudden silence and output tail truncation.
- Report source -> output differences with precise times and one of: `new since source`, `inherited from source`, `changed`, `ambiguous`. Make confidence source-dependent; no unsupported numerical probabilities.
- Surface actionable “go to timestamp”, 2–5-second loop, choose reference, and **Mark intentional / Reviewed / Needs repair** actions; persist decisions with source revision so old decisions invalidate on edit.

### P1A — attribution and visibly reversible repair POC (3–6 dev days)

- For each candidate issue, check stem-local signal evidence within ±1–3s. Rank *suspect stems* by transient/time-frequency coincidence, energy and source-vs-mix comparison. Never claim certainty when separation bleed or effects cause ambiguity.
- Waveform + compact spectrogram strip for a selected region. Render only the selected region, not a full high-resolution 5-minute track in browser memory.
- Implement **one conservative deterministic de-click** candidate for isolated impulses (short interpolation with edge-aware crossfade, or offline linear prediction), plus preview gain-match. On drum transients require stricter thresholds and user approval.
- Add **stereo/mono integrity** diagnostics for the user's changing L/R reverb and bass movements; report whether a proposed repair reduces intended spatial storytelling.
- A/B buttons Original, Corrected, Solo suspect stem, bypass, and Accept/Revert; accept as an immutable edit recipe/child asset referencing the source revision, not destructive rewrite.

### P1B — musical-specific remediation (4–8 dev days)

- Extend effect schema with explicit per-stem/per-section *de-ess*, narrow dynamic EQ and bounded notch with time/frequency envelope. Avoid blind static peak deletion.
- Treat low-energy hiss and bleed in isolated stems differently from full-mix texture. Verify no newly introduced gated tails/phase artifacts.
- Add targetable transient recovery/guard and late-tail crossfade only on confirmed areas.
- Report audibility after correction: level-matched A/B, changed-band energy, clip/mono changes and a subjective Better/Same/Worse decision; never autocommit.

### P2 — optional specialized experiments (2–4 dev days per narrow POC; independent of release)

- Bench lofcz ONNX in a sidecar on a controlled corpus with human electronic mixes and generated Suno, YuE2, ACE, stems and deliberately distorted masters. Verify accuracy, false positives, latency and codec sensitivity against intended original model domain; do not ship general “human score”.
- Try DeepFilterNet on *isolated vocal* samples only. Compare dry reference and denoised candidate; listen for smeared sibilants, lost air, and metallic artifacts before adopting.
- Consider a neural music restoration model only after a reproducible defect-specific fixture shows it beats conventional repair on our music. Do not put PyTorch/VST dependencies into the default Song Harbor install prematurely.
- Fold useful forensics into Sound Cleanup; retain optional “Advanced forensic evidence” disclosure instead of two duplicative tool windows.

## QA fixtures and measurements

Build four fixture families:
1. Clean human/vocals, intentionally distorted industrial synth and normal cymbal resonance **negative controls**.
2. Known click/flat-top, hard cutoff reverb, narrow HF spur, phase-inverted wide stereo, over-deessed vocals, gated tails **synthetic positive controls**.
3. Anonymized Infra Choir generated mixes and separated stems (Suno -> YuE -> Song Harbor), with previously noted ~02:43 loudness dips, ~03:35 near-overloaded peaks; verify on the actual revision instead of claiming those timestamps apply to every track.
4. Edited-before/after control pairs, identical song content, matched loudness; preserve original data and disclose generation provenance.

Per detector report FPR on controls, precision@5 actionable findings, time localization error (target <200ms for clicks), false suppression of intentional percussion, scan latency, memory on 5-minute 48-kHz stereo / 16-stem session, audible Better/Same/Worse rate, export parity and undo. Quantitative targets need calibration from this corpus.

## Performance and cache discipline

CPU-first detection, bounded 5–15s windows, incremental STFT, chunked renders, reuse waveform peak caches where useful. 12 GB VRAM RTX 4070 reserved for ACE/other generators; don't keep forensic models resident. Optional heavy models run separately with explicit resource status. Cache analysis by `project revision + render stage + detector version + sample format`; archive only findings and downsampled preview statistics, not redundant full-length PCM unless accepted candidate needs provenance. Candidate retention must be reference-safe.

## Release gate vs feature work

The currently finishing Infra Choir track should **not** be blocked on fingerprint classifiers or speculative generative restoration. Run current Sound Cleanup and listen to flagged regions; preserve intentional elements. If there is a clear click/clip or audible distortion, attempt safe narrow correction or external RX/DAW handoff. Do not start model installation or bulk processing mid-mastering.

The first implementation PR/commit sequence after release: P0 stage-diff schema and measurements -> local waveform/spectrogram QA -> one de-click A/B repair -> optional model bench. A separate panel that outputs another origin score is explicitly **not** first priority.

## Implemented first P0 slice (2026-10-26) — pending runtime/build QA

Code committed directly to main:
- `app/frontend/src/AudioStageComparison.ts`: CPU-only, non-mutating, sample-aligned, one-second window comparison of a dry source-stem mix against the full effects-rendered mix. Current rules flag differences exceeding 9 dB RMS or 9 dB stereo right-left balance. Conditions skip near-silent regions; results are capped. This is **not an unbiased source/output null test** because dry reference intentionally omits per-section automation, effects and ending treatment.
- `app/frontend/src/SharedClockAudition.ts`: `analyzeMix()` now renders the current processed mix and a second aligned *dry* reference from the existing decoded stem buffers with level and source-position baselines. The new findings are merged into Sound Cleanup. Normal playback and `renderWav24()` are unchanged; no additional reference render occurs during export.
- `app/frontend/src/CleanupReview.tsx` and `StemMixer.tsx`: Sound Cleanup shows the number of large dry-to-processed changes and allows one-session `Mark intentional` triage. This action is deliberately ephemeral until a revision-keyed persisted review ledger is implemented.
- `app/frontend/tests/audio-stage-comparison.test.mjs`: synthetic test fixtures for null changes, localized gain reduction, L/R shift, silence/mismatch, and buffer immutability.

**Limits and quality gates:**
1. This initial analysis renders an additional full-length dry buffer on a user-initiated scan; benchmark 5-minute stereo and 16-stem projects before calling performance acceptable. Avoid duplicate full mix retention/caches.
2. It does **not** yet compute standards-compliant integrated LUFS, oversampled true-peak, source-region time-frequency attribution, spectral change features, audible masking, exported-WAV readback, or exact per-processing-stage causality. Proposed P0 has therefore **started, not completed**.
3. The current dry reference uses each decoded track's static mixer gain and source pan (not its animated per-section treatment); intentional deviations can dominate. Review flags mean 'compare here', not 'damage'. A truly isolated detector of newly introduced glitches requires narrower time-frequency and transient comparisons.
4. Review decisions are currently UI-only and reset after rescan. Persist with project revision and evidence identifiers before making them production decisions.
5. No TS build, Node tests, browser or audio QA were run from this GitHub-only coding session. On the production machine execute `npm run build` and `node --test tests/audio-stage-comparison.test.mjs tests/audio-cleanup.test.mjs` from `app/frontend`; inspect Sound Cleanup's new comparison group, verify that playback/export audio is bitwise unchanged, check performance and manual false positives.
6. Next implementation milestone: short-region spectrogram, source-vs-output time-frequency evidence, source-stem likelihood ranking, and deliberate one-click A/B on selected region. Then a conservative de-click candidate, reversible acceptance, and export parity.

Release safety: this work is observational and only executes on explicit Analyze. Continue current track mastering on the existing stable mix; do not auto-apply a correction from any stage-comparison finding.

## P1 preview and focused evidence slice (2026-10-26) — code committed, QA pending

User feedback: eliminate verbose Sound Cleanup copy, put an accessible **Original / Current / Fix** comparison at the top of a selected correction, and progress into local evidence.

Implemented:
- `CorrectionWorkbench.tsx`: compact three-way selector, Original (unprocessed aligned stems), Current (saved full mix), Fix (unsaved correction). Moving a correction slider selects Fix; acceptance still requires explicit user action.
- `SharedClockAudition.ts`: new playback-only `setReferenceOriginal()` path. It suppresses section gain, EQ, dynamics, authored pan/width/space and reverb/fade for a static aligned-stem reference. It modifies neither source buffers nor export path. Original is **not the original mastered source WAV**; it is the currently loaded stem reconstruction with static mixer levels and routing. Keep wording precise.
- `StemMixer.tsx`: correction selector now appears before scrollable scan findings. Conservative non-zero defaults enable audible comparisons for a new duck/compression trial, but actual musical benefit must be judged by listener.
- `CleanupReview.tsx`: condensed scan summary, shortened finding rows, detailed explanation under disclosure. Only headroom, pumping and sibilance expose Try Fix, consistent with the effects currently implemented. Avoid offering a faux repair for arbitrary spectral abnormalities.
- `RegionSpectrogram.ts`: small 24-column × 12-band, three-second Goertzel time-frequency tile. Appends bounded evidence to the first 20 findings based on the **already-rendered** mix, no extra model or file decode. Visual is a diagnostic approximation and not a precision, high-resolution spectrogram. `region-spectrogram.test.mjs` verifies timing, bounds and immutable PCM.
- `AudioCleanupAnalyzer.ts`: findings can carry optional spectral preview.
- Existing stage comparison and source-activity hints remain; no claim of rigorous per-stem causal attribution.

Remaining next steps:
1. **QA this three-way playback behavior** on an active, playing song including corrected-to-original-to-current without timeline jumps, reset when correction closes, and matching volume (static gains retained; intentional effects will alter actual perceived loudness). Ensure external A/B bypass and candidate audition do not collide.
2. Improve stem evidence using band-specific short-region signal measurements, rather than raw high-pass energy or static top-two RMS. Add confidence rubric and verification against actual solo.
3. Implement **real regional de-click** as a reversible edit candidate (non-mutating source, independent audition buffer/recipe, exact export replay), but do not expose a clickable fix before preview, persistence, undo and export parity exist.
4. Local loudness matching and more granular time-frequency source/output comparison. Persistent review decisions should be keyed to source/project revision; current intentional-review action is session only.
5. Merge proven diagnostics with the primary Sound Cleanup; retire duplicated verbose Audio Forensics prose.

QA command from `app/frontend`:
`npm run build`
`node --test tests/audio-stage-comparison.test.mjs tests/audio-cleanup.test.mjs tests/region-spectrogram.test.mjs`

**Runtime limitation:** GitHub file edits were not exercised on the user's Windows browser/audio device here. Build and audio QA required before release use.

## UX consolidation after desktop screenshot QA (2026-10-26)

The screenshot showing version 0.1.0:1:1097 captured the separate legacy **Audio forensics (experimental)** popover, not **Sound cleanup**. The former reused the same scan findings but did not expose new Original / Current / Fix correction actions or stage-comparison evidence. This was a confusing duplicate tool entry, not evidence that the frontend update failed.

Resolution committed on main:
- Collapsed the toolbar into **Sound cleanup & forensics**, with the existing `cleanup` tool identifier and consolidated correction/report view.
- Removed the old `forensics` window path from `StemMixer.tsx`; its historical `ForensicsReview.tsx` source remains unused pending a separate housekeeping pass.
- Fixed parameter adjustments in `CorrectionWorkbench.tsx` so edits always select **Fix** audibly, including after switching to Original.
- Current/Original/Fix comparison is shown **after clicking Try Fix on a supported finding**, not as a global toggle in the scan summary. Stage comparison and regional spectrum live in the same combined tool.
- No backend models or audio exports were changed in this UI fix. Desktop frontend build and listening QA are still required.

## Compact cleanup desktop QA corrections (2026-10-26)

Desktop screenshots identified overlarge correction forms and disappearing scan findings.

Changes on main:
- Removed the generic bottom disclaimer and the unclear dry-to-processed summary block. Kept the actual comparison *findings* and their details.
- Findings now retain the previous scan after an accepted mix change, with a concise `Previous scan · mix changed. Re-analyze to refresh.` indicator. A second scan explicitly replaces them. The previous analysis isn't silently represented as current.
- The correction toolbar now places **Original | Current | Fix** and **Accept | Discard** in the same sticky toolbar row. Live dynamics meters are collapsed, Strength/Effect/Track occupy a single compact grid row, and numeric parameters use accessible compact rotary-style controls (arrow keys plus horizontal drag). User must confirm real usability on Windows; the dials are range inputs visually styled as controls, not native VST knobs.
- `Strong presence-band emphasis` is **diagnostic-only**: no validated matching dynamic EQ/notch repair recipe exists for that finding yet, and the old generic ducking fallback would be misleading. No `Try Fix` until an actual frequency-targeted repair exists.
- Findings are snapshot observations; when the mix changes, only the stale label changes and the previous scan remains for review. Future persistence across app restarts will require revision-keyed storage.
- Source hints are approximate; they are not proven causality. Better stem-specific spectral attribution remains P1.

QA: test scrolling a small tool window and a full-width one; confirm Accept is reachable without scrolling, dials change values by dragging and arrow keys, switching comparisons doesn't seek, accepting leaves the list and its review state intact with a stale marker, rescan replaces the snapshot, and successful export remains non-destructive. No automated Windows build or browser QA has been executed.

## P1 spectral source-evidence and de-click foundation (2026-10-26)

Commits on main:
- `app/frontend/src/StemArtifactAttribution.ts`: bounded, zero-dependency Goertzel band-energy estimate (7 probe frequencies × max 4 windows × <=256 samples per stem) around each finding. Known spectral bands: 2.5–4.9 kHz harshness, 5–9.5 kHz sibilance, 7.5–11.5 kHz fizz, 6–11.5 kHz noise, 4–11.5 kHz signal audit. Other findings use generic low/mid-band screening. Evidence shares and uncertainty are indicative only: no phase-aware source mix reconstruction, account for source bleed, nor processing-stage causality.
- `SharedClockAudition.ts`: replaces broad unfiltered RMS source hints for rendered-audio findings with frequency-specific source evidence; source reference uses the track's real start offset and static mixer gain. Evidence collection is non-mutating and only executes during an explicit scan.
- `AudioCleanupAnalyzer.ts`: optional typed per-source evidence and uncertainty.
- `CleanupReview.tsx`: compact collapsed spectral evidence details, displays strongest source without asserting proof, expands to band and sampled energy shares. No additional verbose default paragraph.
- `app/frontend/tests/stem-artifact-attribution.test.mjs`: synthetic tests for harmonic source ranking, silence and unchanged input.
- `app/frontend/src/LocalizedDeclick.ts`: candidate-only, sub-3ms interpolation with smooth boundary blend and explicit replacement samples. It copies buffers and does not modify the source. `tests/localized-declick.test.mjs` verifies bounded replacement and baseline preservation.

**Important incomplete integration**: The de-click primitive is NOT yet hooked into Original/Current/Fix audition, project recipe persistence, or export. It is not presented as an actionable UI repair. Implement waveform-local verified click detection, select region, effect-chain audition including exact undo, non-destructive stored correction recipe, and export parity before enabling Accept. We are not auto-repairing drums or intended industrial transients.

Known design risk: fractional source-band energy is an *energy association* only. Correlated separated stems and compressor/duck dynamics can produce a false attribution. A score of 80% is not an 80% probability that the source caused the issue. Future display should use uncertainty weighting and source-isolation audition.

Local QA from `app/frontend`:
```powershell
npm run build
node --test tests/stem-artifact-attribution.test.mjs tests/localized-declick.test.mjs tests/audio-cleanup.test.mjs
```
No Windows TS build or browser listening QA was performed in the GitHub-only implementation environment. This remains a development milestone, not release mastering approval.

## P1 de-click trial, acceptance and export wiring (2026-10-26)

Implemented on main, pending desktop QA:

- `app/backend/declick_recipes.py`: project-scoped `data/jobs/<id>/declick-repairs.json` manifest, version 1, atomic writes, append and undo by unique recipe ID. The source WAV is not rewritten.
- `app/backend/server.py`: GET/POST/DELETE `/api/projects/{ident}/cleanup/declick`; local-origin validation for edits; target must be an active filename, a valid parent or L/R source key, within measured clip duration, and inside a 0.15–3 ms half-window. Old projects without source_tracks fall back to saved files.
- `app/frontend/src/SharedClockAudition.ts`: retains immutable decoded `rawBuffer` for each lane. Accepted repairs are replayed into separate buffers and used consistently by processed playback and offline WAV export. The Original audition selects raw source buffers. Unsaved Fix preview is built separately and is NEVER used by export. Playback switching restarts at the existing position when buffer identity needs to change. No normalization or content hallucination occurs.
- `app/frontend/src/DeclickWorkbench.tsx`: compact Original/Current/Fix + Accept/Discard, selected physical source lane and repair width. Opt-in `Try de-click` appears for transient warnings only; it does not automatically modify drum attacks. Accepted entries list individual Undo actions.
- `app/frontend/src/StemMixer.tsx`: loads saved edits when a project audio engine becomes ready, updates engine after Accept/Undo, keeps existing QC findings marked stale rather than discarding scan results, and blocks WAV export until the saved manifest has loaded. This prevents a background failure from silently exporting without accepted repairs.
- `app/frontend/src/LocalizedDeclick.ts`: replacement-only operation avoids expensive full-length temporary clones when applying recipes. Replays deterministically and preserves untouched sample positions.
- New backend tests `test_declick_recipes.py` cover persistence, validation, undo and source immutability. Existing `localized-declick.test.mjs` covers bounded interpolation and input immutability.

**Critical QA acceptance** (not yet verified on Windows):
1. Start a new project with no repair manifest: no backend errors; a normal WAV export remains possible.
2. Scan a transient; click Try de-click. Test Original vs Current vs Fix at identical timestamp and loop. Confirm a genuinely isolated click is audibly suppressed and an intentional drum transient is *not* approved blindly.
3. Select the correct stem/L/R source; change 0.5/1/2/3 ms. Preview should stay separate from saved current. Discard leaves original and export unchanged.
4. Accept and verify a project manifest appears; previous findings remain but show a stale indicator. Current now plays accepted repair; Original does not. Fix before acceptance and Current after acceptance should closely match at equal settings.
5. Export WAV, reimport/inspect the exact repair region (not only full song listening); confirm accepted repair appears, discarded preview never appears, surrounding audio unchanged, and original source WAV byte hash unchanged.
6. Relaunch/reopen: same edit recovered; export blocked on manifest-load failures. Undo -> current/export return to original at repaired sample region.
7. Split L/R sources, overlapping edits, back-to-back edits and clips with start offset must remain aligned. Test 16+ stem memory and update after seek/playback at candidate boundary.
8. Run `python -m unittest app.backend.tests.test_declick_recipes` from repository root and `npm run build` plus `node --test tests/localized-declick.test.mjs tests/stem-artifact-attribution.test.mjs` from `app/frontend`.

**Remaining risk:** the recipe currently identifies project filename and source lane, not a cryptographic version of that PCM file. Replacing a WAV in place while preserving its filename could reapply an old repair at the wrong position. Add source content identity and reject stale recipes before calling this production-complete. Audio audition/export parity also requires in-app Windows listening verification, as source-convolver graphs and per-stem processing can alter perceived repair effectiveness.

### Follow-up safeguards in the same slice

- Every accepted de-click manifest entry now has a SHA-256 of the **exact audio file feeding that lane** (parent source or derived left/right mono WAV). Manifest reload verifies fingerprints before returning repairs; if any file changed in place, restore the matching WAV or explicitly discard stale repairs. Export is blocked until the manifest was fetched and successfully applied to the audio engine. The old unversioned filename-only risk above is therefore addressed for current version-1 saved entries.
- Clip duration is verified on the actual repair source file on acceptance. Legacy projects without `source_tracks` fall back to `project.files`.
- The three-way comparison forces a buffer reschedule at the same transport timestamp when toggling Original/Current after accepted or preview edits; source PCM remains immutable.
- Memory optimization: the replay path constructs short sample replacement arrays instead of also cloning full buffers for every tiny repair. The accepted target still requires one decoded repaired AudioBuffer per active source lane.

**Note**: SHA validation is at project open and edit submission, not on every export byte read. After physically altering a source file outside Song Harbor while it remains open, restart/reopen so source identity can be checked before export. A future project file watcher could provide immediate invalidation.

This change is code-complete for desktop QA, **not empirically verified** for live audition/export identity. Unit tests exercise edit manifest logic and interpolation, but on-device playback, persisted reopen and WAV parity checks remain necessary.

## Next artifact cleanup capability: section-scoped spectral attenuation (2026-10-26)

Implemented on main:
- The existing Sound Cleanup findings `harshness`, `fizz`, `noise` and `signal_audit` now offer `Try Fix`; unlike the de-click recipe path, this is a **frequency-targeted section EQ cut**, *not* a generative or spectrogram-pixel reconstruction tool. It does not claim to remove AI provenance or fingerprints.
- The correction panel gains a `Spectral cut` effect with source, frequency, Q, attenuation (0–9 dB), and section transition. Suggested centers are 3.5 kHz for presence harshness, 10 kHz for fizz, 8.5 kHz for noise and 6 kHz for persistent tonal features; tune against actual listening evidence.
- The trial compiles through the existing three-band section EQ automation and its live playback graph. `Original` remains the unprocessed stems, `Current` the saved mix, and `Fix` the proposed EQ. Accept appends a normal `<alias>.eq<band>:freq,Q,-gain@transition:smooth` directive to the current section's production block; existing section import persists it and the offline WAV render uses the same processor. Discard leaves the section script unchanged.
- The proposed EQ uses an available band in preferred order 3, 2, 1; it refuses to silently overwrite an occupied band in that section. Source selection checks the destination band's availability, and blocked trials now surface their error even without an open workbench.
- `app/backend/tests/test_spectral_cleanup_directives.py` checks parser acceptance, independent frequency bands and duplicate-band rejection.

Important constraints:
- **Section-wide, not time-frequency localized.** The EQ cut ramps in over the first `transition` seconds of the target section and carries forward according to Song Harbor's inherited automation semantics. It may suppress desirable content later. In a production mix, inspect later sections and restore/reset the EQ when necessary. A truly isolated 200 ms fix requires region-scoped automation or audio replacement with exact rendering parity.
- `3× preview` exaggerates the audition only; Accept saves the actual 1× dial setting. For preview/export comparison use `1×`.
- These are sound-shaping options, not evidence that a classified anomaly is genuinely objectionable. Intentional industrial harmonics and synth noise should often be left alone. Never use a falling AI-detection score as evidence that audio sounds cleaner.
- Windows build and audio QA have not run in this GitHub-only session. Run `npm run build` and `python -m unittest app.backend.tests.test_spectral_cleanup_directives`, then listen across the entire target and following sections; compare Fix with resulting Current after acceptance and the exported WAV.
- Next material improvement: genuinely **region-scoped** attenuation with attack/release and transient protection, spectral delta measurement pre/post, persist/replay exact slice, targeted de-clip and de-noise candidates. Avoid adding a third duplicate cleanup panel.


## 2026-10-26 course correction: detection research is NOT yet implemented

**User challenge and agreed answer:** The prior Sound Cleanup progression delivered conventional DSP analysis, source attribution hints, a de-click recipe workflow, and section EQ/ducking/de-ess audition. These are valuable production infrastructure but **not faithful implementations of the three pinned AI-music detector projects**. No validated KillrBee multi-domain checkerboard/harmonic/reverb/vocal artifact suite, lofcz ONNX fakeprint extractor, or lcrosvila robustness/embedding bench has been integrated. Do not market section EQ as fingerprint cleaning.

**New next priority:** inspect and reproduce the actual upstream algorithms, their corpus limits, model contracts, available licenses, and failure modes. Build an explicit detector capability/QA matrix, then implement one *interpretable, temporally localizable* KillrBee-inspired artifact detector and test it on both positive fixtures and intentional industrial negative controls. Bench lofcz separately (research-only; not a quality score) and use lcrosvila methodology for robustness. The existing compact Sound Cleanup tool is the only UI destination and Original/Current/Fix is reserved for manually approved *audible* corrections.

**Boundaries:** Fingerprints/provenance, audible artifacts, and repairs remain three different categories. No attempts to strip watermarks or optimize to evade classifiers. Avoid grand "AI probability" or "human score" claims. No Windows runtime/audio QA claimed for many preceding commits; verify before shipping.

Canonical implementation handoff: `refs/handoffs/currentHandoff.md` (top section CURRENT HANDOFF — 2026-10-26).
