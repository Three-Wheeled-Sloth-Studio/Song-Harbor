# Post-release direction: music understanding, model management, accompaniment
Date: 2026-11-10
Status: Approved product direction, explicitly PAUSED until current Infra Choir release is complete
Branch: dev. This document commits design/roadmap only, no model installation or runtime changes.

## Decisions locked today
1. Finish current track "Parade for the Drowned King" and its YouTube release before resuming development. Do not start heavy model downloads, benchmark jobs or UI refactors during release prep.
2. Defer YuE2 accompaniment/arrangement integration exploration to the NEXT TRACK. Preserve the distinction between ACE targeted conditioned Lego generation and YuE2 symbolic scoring/whole-render exploration. YuE2 prompt formats remain separate: global guidance + plain section tags/ABC vs ACE section-level instructions.
3. Proceed after release with MOSS music understanding as leading research direction. Explore `OpenMOSS-Team/MOSS-Music-8B-Instruct` against a smaller alternative `MOSS-Audio-4B-Instruct`. Verify model provenance, current license, repository identifiers, checkpoint formats, supported runtimes, quantization, audio limits, and memory/speed on RTX 4070 12 GB / 96 GB RAM before making feature claims.
4. Add an in-app installer/configurator in Settings, not a standalone installer or intrusive startup dialog. User can select a GENERAL shared model root (e.g. non-system drive), inspect installed/discovered models, install selected compatible models, manage load/unload, and choose an inference/runtime profile. Model installs should use that configured root and isolate caches/offload paths from C: unless explicitly chosen.
5. Implement a persistent, versioned Shared Musical Understanding record (SMU) as a first-class source-backed project asset, reused by accompaniment, production suggestions, and mixing diagnostics. No fictional confidence or fabricated instrument/key detection.
6. Model proposals are reviewable; no autonomous edits or unsupervised acceptance. Preserve user section sheet, existing stems, creative intent, aliases and approved render.

## In-app model management contract
- Settings > Models: compact model root selector, browse/paste path, optional locate existing models, validated disk capacity, and per-model actions Install, Load, Unload, Remove. The shared model root is separate from working song files and application binaries. Existing ACE/other model roots stay independently configurable.
- Respect existing external model installations; never silently duplicate or relocate. Prefer discover + link/registration. Do not assume that setting `SONG_HARBOR_MODELS` is sufficient for all model adapters; model root is a registry and runtime-specific paths are resolved explicitly.
- Install manifest: source repository, revision/commit, license status, checksum, exact file inventory, runtime backend, quantization/profile, local directory, installed bytes, download state, last verification, user approval.
- Install into staging directory within the chosen root; verify hash and metadata; publish atomically. Support recoverable interruption, retry, partial-download cleanup, disk-space preflight, and never overwrite unrelated directories.
- One heavy model worker at a time on 12 GB GPU; reserve VRAM for ACE when necessary or explicitly unload MOSS before ACE generation. Allow CPU/offload and lower-resource profiles only after actual benchmark.
- Load: explicit readiness state and health check, warm-up/cold-start status, cancellation/timeout, progress and model/error detail, not a fake green status. Unload frees resources. No loading models just by opening Song Harbor.
- State UX under canonical TWS-Design-Principles: icon-first status, a compact model picker in existing Settings, optional setup on first action, no permanent explanatory paragraphs.
- Security: no arbitrary code from model repos unless a reviewed/pinned runtime requires it; validate requested downloads, files and path traversal; no remote code trust by default. Record commercial-use rights and runtime compatibility before enabling install option.

## Shared Musical Understanding asset (SMU)
Use project+source revision and evidence:
- Audio source references and SHA-256, exact mix/stem hashes, processing/render recipe revision, analysis model ID/version and settings.
- Structure and time: stable section IDs, ranges, tempo/meter/key/chords where evidenced, confidence and measurement method.
- Instrument/source roles: observed or user-corrected candidates, accompaniment gaps, vocal prominence, rhythm/texture/dynamics, motifs and transitions.
- Measured section metrics: loudness (RMS and when validated LUFS), width/balance, crest factor, spectral brightness/low energy; preserve baseline and timestamp.
- Intent: user-authored scene/emotional arc and constraints, marked separately from model inference.
- User corrections, provenance and accepted choices persist independently of re-analysis.
- Invalidation: changed audio source -> invalidate dependent sonic metrics; changed section timing -> remap/flag observations; changed mixer processing -> invalidate mix measurements but not necessarily source-stem instrumentation; prompt/text change alone -> do not rescan audio.
- Local storage, no mandatory cloud or telemetry. Show uncertainty; never turn a possible chord/instrument into fact.

## Next implementation slices (AFTER release)
1. Verify current Deshimmer acceptance, source versioning, script-preservation, and playback/export parity. Do not regress clean UX or reintroduce mystery stems. User QA reports track recovery and cleanup pass on 2026-11-10.
2. Add shared model root configuration + per-model manifest/status and safe installer UI in Settings; test locate-existing and no-install use cases.
3. Create MOSS runtime adapter as an isolated, optional worker. Benchmark on hardware with realistic full mix and ~20s selected sections; record VRAM, RAM, peak allocation, load time, latency and accuracy against listening annotations. Implement graceful refusal/fallback.
4. Define SMU schema and evidence ingestion from existing section analysis, lyric sheets, tempo/key utilities, current stem inventory and user-authored intent. Deterministic baseline works even if MOSS unavailable.
5. MOSS -> schema-validated observation and accompaniment proposal (role, target sections, sound constraints, explicit evidence, confidence, ACE task family/prompt) -> reuse existing ACE Lego candidate A/B and acceptance. No second generator UI.
6. MOSS -> mix/production proposals constrained to supported Song Harbor section grammar, with before/after diff, reversible preview and explicit accept. Suggestions cannot alter media or execute arbitrary scripts.
7. Next track: investigate YuE2 providers, score/ABC editing, generating isolated musical parts vs complete rerenders, adapter costs, A/B and score-to-MIDI/SFZ alternatives. Do not promise native stem isolation without measured evidence.

## QA / Definition of done
- Fresh install with no configured model folder, preexisting folder, unavailable network, insufficient drive space, interrupted download, invalid hash, missing runtime; all leave working Song Harbor unaffected.
- No heavyweight auto-start, cache dump on C:, or unapproved checkpoint install.
- SMU reproducible and source-cited, with reliable invalidation and author correction persistence.
- Music model judged against objective source notes and actual user listening, not just plausible prose.
- Accompaniment generated from edited proposal, previewed at a known timeline position, never changes approved stems before Accept.
- Production suggestions have valid grammar, audible A/B, safe headroom, undo and playback/export parity.
- No additions that obstruct waveform, no explanatory filler.

## Related
- docs/audio-aware-production-and-deshimmer-2026-11-10.md
- docs/ace-accompaniment-integration-contract.md
- refs/product/vision.md
- refs/planning/decisions.yaml
- TWS-Design-Principles/apps/App-Design-Principles.md
- TWS-Design-Principles/apps/Studio-UI-Style-Guide.md

## Current state at thread handoff (2026-11-10)
- User reports Song Harbor dev relaunch clean and Deshimmer split-channel acceptance appears to pass QA. Previous attempts had failed on active L/R splits without updating any stem. After correction, user is **redoing cleanup work now**. Do NOT assume the new cleanup work is complete, frozen or exported. Do not touch this project, its stem files, its WAV exports or its Deshimmer runtime while active.
- Latest split-acceptance and blocking-error fixes are documented in docs/audio-aware-production-and-deshimmer-2026-11-10.md. Earlier legacy Clean_* stems were recovered by a coding agent. The new acceptance keeps original track IDs/aliases and regenerates split L/R audio, with rollback and explicit red ERROR / Stem not updated messaging.
- Infra Choir "Parade for the Drowned King" release work is primary today; base track artwork has already been generated. Music project and channel are separate from Song Harbor product identity.
- MOSS installer and SMU work is **approved but not implemented**. Roadmap IDs SH-RM-280, 285, 290; YuE2 follow-up SH-RM-295 reserved for next track.
- Priority when explicitly resumed: first inspect live dev implementation and user settings/model-path conventions; then implement a small safe model-folder/configuration slice without touching the active audio project. Do not begin multi-gigabyte model downloads until user opts in and destination/space are verified.
