# CURRENT HANDOFF — 2026-10-26 — Return to actual AI-artifact / fingerprint discovery

> **2026-10-27 Windows validation continuation:** Local Windows TypeScript/Vite build and 45/45 artifact tests passed at implementation SHA `871003dfccec153623aa70e3eac847632f872b5e`; exact-SHA Frontend build, Windows single-server launch smoke and launcher syntax CI also passed. Added a bounded, non-destructive reverb-tail envelope diagnostic for abrupt cutoff/stall evidence in the existing Sound cleanup & forensics pipeline, plus a separate benchmark. Its intentional-gate control is byte-identical to the hard cutoff and is honestly counted as a false positive (1/2 negative cases); the method cannot infer intent and offers no repair. Attack-rise retains the intentional soft-pad false positive (1/7 negative cases). See `docs/artifact-validation-results-2026-10-27.md`, `docs/reverb-tail-diagnostic-2026-10-27.md` and the empty real-corpus manifest. Real listening/export QA and a rights-cleared annotated corpus remain pending.

> **2026-10-27 testing-agent preparation:** An executable Windows test command, synthetic planned-method fixtures, optimized event matching and a full agent brief are now available. Start with `refs/handoffs/artifact-validation-agent-2026-10-27.md` and `pwsh -File scripts/verify-artifact-suite.ps1`. This is harness preparation, **not** completed Windows/real-music or fingerprint-model validation. Continue honoring the October 26 acoustic/fingerprint distinction.\n\n
## Read this first (next thread)
**User decision:** After several Song Harbor Sound Cleanup implementation slices, the user asked whether those were actually the specialized techniques from the three pinned GitHub discovery projects. The answer was **mostly no**. We built valuable conventional DSP/QA infrastructure but drifted away from the original AI-generated audio artifact and fingerprint research. **Next thread must correct that direction rather than continue building generic mastering controls.**

**Work directly on `main` in `Three-Wheeled-Sloth-Studio/Song-Harbor`.** User prefers in-repo commits and chat answers, not downloadable deliverables. Keep UI sparse, compact, icon-driven and do not reintroduce duplicate panels. Existing **Sound cleanup & forensics** tool is the single entry point, with **Original / Current / Fix**, **Accept / Discard** in a compact sticky toolbar.

### What actually exists in main (code committed; Windows run/QA not uniformly verified)
- `AudioCleanupAnalyzer.ts`: on-demand offline mix QC including level/peak, suspicious transient and flat-top, loudness dips, stereo cancellation, sibilance/presence/fizz/noise categories. **Heuristics, not general AI artifact detectors**.
- `SignalAudit.ts`: narrow tonal signal scan. **Not a validated generator fingerprint extractor or watermark detector**.
- `AudioStageComparison.ts`: aligned dry-stem versus processed-mix RMS and L/R balance flags; intentional automation can trigger them.
- `StemArtifactAttribution.ts` / `RegionSpectrogram.ts`: bounded per-stem frequency-band energy hints and compact region spectral tiles; not causal or precision time-frequency artifact classification.
- `LocalizedDeclick.ts`, `DeclickWorkbench.tsx`, `declick_recipes.py` and local API endpoints: non-destructive small impulse replacement, preview, accept/undo persisted recipes, source-file SHA-256 validation and accepted-only export design. Requires on-device audition/export parity QA.
- `CorrectionWorkbench.tsx`, `CleanupReview.tsx`: compact comparison and findings review. Targeted de-ess, compressor/ducking, trim, and `spectral` section EQ cut. **Spectral cut is ordinary section-scoped peaking EQ, not spectrogram pixel reconstruction or fingerprint cleaning.** It can inherit across later sections.
- Single entry via `WorkbenchTools.tsx` / `StemMixer.tsx`: **Sound cleanup & forensics**. Prior separate Audio Forensics popover was removed as redundant.
- Prior release mix should remain unmodified unless a specific fix is heard, manually approved, and verified in the exported WAV.

### Pinned discoveries (specific, not interchangeable)
1. **https://github.com/KillrBee/ai-music-detector** — seven analysis domains: spectral, spatial, production, temporal, structural, vocal, optional watermark. Explore transient/attack and phase anomalies, sustained harmonic-to-noise and unusual upper-band structure, reverb-tail inconsistency, timing/phrase repetition, vocal breath/formant/phoneme coherence. **High-priority for interpretable, locatable audible-artifact diagnostics**. Its global AI score is heuristic / not calibrated; no top-level LICENSE was found in earlier inspection: confirm permissions before copying code. Implement independent feature algorithms and test fixtures first.
2. **https://github.com/lofcz/ai-music-detector** — MIT ONNX spectral fakeprint / vocoder architecture residual spectrum and CQT route, scoped by its author to specific Suno/Udio generations. **Run as optional, offline research experiment**, not source quality metric. Validate supported model/preprocessing (16 kHz / 1–8 kHz noted in discovery) and test false positives on ACE 1.5, YuE2, remixed mastered hybrids, industrial synths and real acoustic music. No watermark stripping.
3. **https://github.com/lcrosvila/ai-music-detection** — Essentia/CLAP features, hierarchical classifiers, and robustness tests under sample-rate changes, filtering, noise and codecs. **Use mainly as evaluation methodology**, not a live default dependency; repo/license/dataset availability to verify before reuse.

Additional canonical source: `docs/ai-audio-forensics-discovery.md`. The roadmap `docs/artifact-fingerprint-cleanup-roadmap-2026-10-26.md` records many commits chronologically but starts with **historical, now-stale** statements. This prominent handoff reflects the current decision.

### Explicit reset of priorities for the next thread
- **P0: audit and reproduce the source techniques** from all three pinned repositories before writing more code. Inspect actual source algorithms, model assumptions, license/weights, maintenance, hardware needs, inputs/outputs. Produce a capability matrix: detectable acoustic phenomenon, window size, source vs mix, temporal localization, observable evidence, likely false positives, CPU/GPU, and whether a reversible *audible* repair is available.
- **P1: implement KillrBee-inspired interpretable detectors**, separately calibrated on controlled fixture audio: attack/transient smearing, phase/width incoherence, sustained harmonic/noise anomalies, nonphysical/stalled reverb decays, then vocal formant/breath/phoneme and phrase-temporal irregularities. Labels should describe evidence and location—not a global AI percentage. Negative controls MUST include intentionally distorted electronic/industrial music, cymbals and wide/spatial reverbs.
- **Parallel limited P1/P2: isolated lofcz spectral fakeprint bench**. Download/adapt only if license and runtime allow; strictly a research report. Preserve fingerprint/provenance information; **do not minimize detection score or remove provenance**. A changing AI score does not mean an audible improvement.
- **P2: use lcrosvila-style robustness evaluation** to test over Suno -> YuE2 remix -> stem separation -> ACE accompaniment -> Song Harbor mix/export, plus acoustically recorded and deliberately synthetic controls. Report precision/false positives, codec/sampling stability, and category-specific localization.
- **Only after detectors are validated**, map *audible, localized* defect categories to opt-in Original / Current / Fix candidates (repair should remain reversible with export parity). Do not expand basic EQ, compression, or UI without a concrete artifact diagnostic requirement.
- **UI requirements:** Single compact existing tool, keep Accept/Discard reachable, preserve previous scan findings after mix edits with a stale marker, no verbose disclaimers or duplicated forensic windows.
- **Engineering:** Local-first, CPU bounded where possible, 12 GB RTX 4070 available for optional experiments, avoid a permanently resident model. Maintain explicit tests; **do not claim Windows build/audio QA unless actually run**.

### Immediate next-thread kickoff
Suggested user prompt: **"Continue Song Harbor from `refs/handoffs/currentHandoff.md`, section CURRENT HANDOFF — 2026-10-26. Audit the three pinned AI-music detector repos, build the artifact-method capability matrix, and implement the first specific KillrBee-inspired diagnostic with tests. Work on main."**

### Notable other deferred work
Release-bound current track needs independent listening/export sign-off. Candidate cleanup/retention (reference-safe), foreground app focus on update/relaunch, pinned global header, vocal profile exploration (Applio/RVC, DiffSinger/OpenUtau), and enhanced ACE isolation QA remain separate backlogs; do not mix them into this artifact-detection workstream.

---

## 2026-10-23: Premium cross-device cloud sync plan — documented, not implemented

User wants eventual cross-device Song Harbor cloud synchronization, ideally a
paid premium feature, without sacrificing local-first production. Created full
architecture, UX, pricing-cost controls and milestone plan in
`docs/premium-cloud-sync-plan.md`; roadmap entries SH-RM-260, SH-RM-265,
SH-RM-270. No app/service code was changed in this planning pass.

**LOE:** approximately 3–5 weeks for manifest/revision metadata foundation
and offline metadata proof; ~8–13 weeks total to a usable two-device
media-sync MVP; ~12–21 weeks total to a production-ready premium
commercial service, for one experienced full-stack engineer with managed
cloud infrastructure; ranges subject to real asset sizes, security and
sync conflict QA. A one-way backup prototype is smaller but not equivalent
to multi-device sync.

**Design choices:** sync semantic portable versioned manifests and
immutable hash-addressed source/stem/assets, never live
`library.sqlite` or device absolute paths; durable local outbox and
offline editing; compare-and-swap song revision commits; concurrent edits
preserved as named conflict versions; verified, resumable transfer;
per-device availability; full local editing stays functional after
downgrade or cloud outage. Cloud account, quota and billing entitlement
authorize the optional remote service, not base music playback/editing.
Evaluate R2/B2 object storage plus managed identity and Stripe when
prototype usage data is available; no vendor is selected.

**Important existing state:** projects currently write atomic v1 JSON
under user-selected data directory; SQLite Library v1 indexes absolute
paths and source SHA-256. Existing Settings suggest Google Drive folder
mirroring but correctly warn against two Song Harbor sessions writing the
same database concurrently. This shortcut is NOT a safe premium sync
design. First useful slice is portable dependency-complete snapshot/
restore on two PCs, not a hosted service or client-side cloud secrets.

---

## 2026-10-23: Whole-song production blocks now accept LF and CRLF directive separators

- User requested production scripting readable one directive per line, in
  addition to legacy space-delimited syntax. Implemented in
  `app/backend/section_import.py`: a single `{ ... }` block per section
  may span multiple physical lines, mix spaces/LF/CRLF and contain blank
  lines. Tokens still feed the same `section_production.parse_block`
  validation/typed effects; project mutation remains atomic on rejection.
  Unterminated/nested/duplicate braces and misplaced closing braces now
  produce line-aware validation messages. Lyrics still live OUTSIDE braces.
- `section_production.render_block` formats multi-directive blocks into
  canonical one-directive-per-line text after applying/reopening, without
  changing effect semantics, section times or lyrics; a single directive
  continues to render compact on one line.
- `StemMixer.acceptCorrection` now reads/replaces an entire brace span
  rather than assuming braces/directives reside on one text line, so
  accepted cleanup actions retain all other multiline directions.
- Editor helper guidance and `docs/user-guide.md` updated. Test suite
  `app/backend/tests/test_multiline_section_production.py` added and
  wired into backend CI. Backend suite passed at `e25c38d1`; frontend
  build passed for help text at `d34553f5`. Later correction-path frontend
  build is separately pending; local Windows UI QA not yet claimed.
- Test on Windows: paste a long timed sheet with CRLF and one directive
  per line, Apply, reopen, verify one-brace-block formatting and original
  lyrics, effects inherited correctly, Go to line on malformed directive
  and correction A/B -> Accept without losing production instructions.

---

## 2026-10-23: First menacing Spatial Evolution Macro + natural-end transport reset

**Implemented on main; backend automated tests green, Windows listening QA pending.**

- `Other.evolve:menacing@20s:smooth` is now executable in exactly one normal
  `{...}` production line below a timed section. Parser validates alias,
  bounded duration .05–30s, only `menacing` v1, no duplicate macro.
  Saved `section_production` contains versioned `evolve` intent, not a
  destructive rewrite of the authored lyrics/production script.
- `section_production.expand_evolution` deterministically resolves that
  intent at import into existing typed materializations. Preset v1 targets
  parent pan +.18 right, width 125%, space 18%, reverb 16%, EQ1 380Hz/Q.9
  +1.1dB, EQ2 3200Hz/Q.8 -1.7dB. Where child channels are attached,
  left reverb 11%/EQ2 3500Hz -.8dB, right reverb 23%/EQ2 2600Hz -2.1dB.
  Explicit manual same-section parameter/band overrides generated target.
  Falls back to parent-only if no L/R split. No vocals/other stems changed.
- Resolved effects go through normal automation arrays for playback and
  WAV export. No new DSP processor/model/GPU service required; this is a
  *fixed deterministic preset*, not adaptive safe-space DSP. No per-macro
  bypass, curve inspection UI, true-peak/correlation guard or independently
  variable reflection predelay yet. Follow-on only after listening proves
  usefulness; see `docs/spatial-evolution-macros.md`.
- Regression `app/backend/tests/test_spatial_evolution.py` integrated
  in projects workflow, tests parse/serialize/import, parent and L/R
  target materialization, conflict priority and rejection.
- User QA bug: on natural song completion `StemMixer.tsx` now calls
  `engine.stop()` rather than `stop()`+display duration; updates
  transport generation, playing state and position to 0. Manual Pause
  still retains position; next Play begins at 0.
- **Windows manual QA:** enable split Other, apply macro in one section,
  audition (with level matched A/B and mono check), verify child asymmetry,
  script persistence across reopen and export parity. Test unsplit parent
  fallback, explicit override `Other.reverb:10`, next-section inheritance,
  click seek/play near ending, ordinary Pause stays at pause location and
  natural completion resets both engine/visual playhead to zero. Avoid
  replacing the ongoing other-machine production sheet merely for QA.

CI at implementation time: backend new macro suite passing in
`Song projects and Waveform exchange`; frontend build passed after
transport end reset. *Do not claim local Windows audio testing done.*

---

## 2026-10-23: Deferred JS bundle cleanup + Spatial Evolution Macros review

- Vite warning `Some chunks are larger than 500 kB after minification` is informational, not updater failure. Deferred P2 task `docs/frontend-bundle-cleanup.md`, roadmap SH-RM-245: capture real assets and minified sizes, lazy-load session boundary and useful optional inspectors without splitting playback clock ownership, regression-test update/open song/transport/export; estimate 1-3h, avoid threshold-only suppression.
- Reviewed `docs/spatial-evolution-macros.md` against current parent/child audio graph; appended nonbinding engineering review and staged LOE. Roadmap SH-RM-250 is **proposal-reviewed-not-approved**. Recommendation: 0.5-1 day audition of an explicit manually scripted `Other` progression first; then a deterministic, versioned `menacing` intent -> inspectable envelopes compiler (~2-4 days), with further adaptive safeguards/new asymmetric reflection parameters (~3-7 days) only if justified.
- Current `space` is fixed symmetric 13/19ms cross-channel reflection send, and `width` cannot expand exactly mono input. The proposed `Other.auto.space:menacing` token is NOT recognized syntax. Exact namespace, precedence, active split-state fallback and long (>section) macro time anchoring are unresolved design choices. Preserve center/lead, consistent offline/live sound, manual override/undo, mono safety, and immutable track identities. No implementation of macros in this pass.

---

## 2026-10-23: Independent split L/R production scripting implemented (Windows audio QA pending)

User approved independently targeting `Drums-left` and `Drums-right` without replacing immutable track identity or losing the shared parent bus. Implemented on main:

- `section_production.source_map(files,tracks,channel_children)` adds virtual channel aliases mapped to `<working_filename>:left/right` when a split export is attached; collisions reject. `section_import` resolves these aliases and compiles channel-specific gain/pan/eq/reverb source keys. `all.*` production broadcasts only to true **parent** stem aliases.
- Section script examples (one production block LINE after the heading): `{Drums.reverb:10@2s:smooth Drums-right.reverb:18@2s:smooth Drums-left.gain:-0.75@2s:smooth Drums-right.eq1:1000,1,-2@2s:smooth}`. Parent send supplies the default for both channels; explicit right send **overrides** right's value, not adds. Parent EQ/width/pan/etc remain on parent bus. Child effect stages precede parent effects, and parent/child gains multiply.
- `SharedClockAudition.ts` has new per-child gains/pan/EQ/sends for live audition AND `renderMixBuffer` 24-bit export. When split, parent reverb signal is routed through per-child sends, each falling back to parent automation; the original shared post-parent-bus send is disabled for split sources to avoid double reverberation. This changes the reverb send's tap location for split streams (pre-parent FX); requires listening parity QA, especially when parent EQ/compression is active.
- Child pan defaults remain hard-left/hard-right unless the script explicitly overrides. When switching back to unsplit stereo, child curves are dormant. Existing source WAVs and physical L/R routing remain unchanged.
- Child width, spatial reflection, compression, ducking and de-essing are currently rejected; don't claim support. Parent versions of these effects still work.
- Rename of a parent alias migrates `-left/-right` script directions. New regression suite `test_child_channel_scripting.py`, wired into backend CI, covers distinct source targets, no accidental broadcast, unsupported directives and rename/identity preservation.
- Full syntax and expected behavior documented in `docs/user-guide.md`.

**Windows acceptance, still pending:** split an actual Drums source; enable L/R. Apply one-line sample; check each channel independently by muting/soloing via listening, compare per-child reverb 0/18 vs parent baseline 10, pan and EQ. Verify inheritance across sections, A/B processing bypass, rendered WAV audible parity, reopen, rename Drums to Percussion while preserving script, switch Stereo and back. Check memory performance at 16+ tracks. Do not declare production-grade until listening verifies both playback and offline bounce.

---

## 2026-10-23: Click-to-error section text import QA fix

User QA: a rejected section script with an unsupported section header should offer a clickable navigation target instead of merely showing an error. Updated `app/frontend/src/SectionsTool.tsx` to parse existing backend `Line N:` validation errors and render accessible `Go to line N ↗` beside the message. Clicking focuses the textarea, selects the offending line and scrolls it into view; user draft is preserved. Added compact styling in `song-harbor.css`. Does not auto-correct or discard edits. Applies to both unsupported bracket section tags and line-specific production syntax failures. For errors without a line number, plain error text remains; future richer diagnostics can add structured spans.

Local QA: paste multiple sections with an invalid header in the middle (e.g. `[Interlude]` when unsupported), click Apply, click `Go to line N`, verify selected text/scroll and editing; repeat with an invalid `{...}` production directive. Correct and re-Apply. On failure the original saved sections must remain unchanged. Frontend CI check independently.

---

## 2026-10-23: USER QA PASS — YouTube lyric SRT import

User reported: **"Lyric upload to youtube passed QA - nearly perfect alignment, clean import."**

- Mark Song Harbor generated timed-lyrics SRT -> YouTube upload/import as **user-accepted for the tested song**. Formatting/import is clean; observed lyric alignment was nearly perfect, not claimed sample-accurate or universally guaranteed.
- This closes the previously deferred user-side YouTube lyric-export QA gate in older sections below. Those older "pending tomorrow" statements are historical and superseded by this note.
- Do NOT declare all of v0.2.1 released solely from this acceptance; independent CI, other release criteria and remaining Windows QA still apply.
- Future enhancement only if useful: optional per-line/per-word manual adjustment, not required to accept the existing SRT workflow.

---

## 2026-10-23: Temporary Audio Forensics sidebar tool for discovery QA

- Right palette contains new `forensics` tool icon `⌁` in
  `WorkbenchTools.tsx`; view `ForensicsReview.tsx` styled through
  `song-harbor.css`.
- Reuses existing `SharedClockAudition.analyzeMix()` CPU/offline rendered-mix
  scan and Sound Cleanup state. Categories: spectral texture, attacks and
  dynamics, stereo compatibility, peaks. Supports seek and timed looping.
  No new AI detector, model download, GPU dependency, external service or
  audio mutation. Scan is on demand, not triggered by opening the panel.
- This experimental inspection view is intentionally not a new analysis
  pipeline. Source-vs-output artifact regression and separately validated
  fingerprint model are pending. Do not advertise watermark verification,
  detector evasion or a universal human-sounding score.
- User wants the tool icon available for testing, with integration into the
  main analyzer only after evidence of value. Windows QA is pending; check
  frontend CI and launcher smoke after commits before acceptance.

---
## 2026-10-23 DISCOVERY: Audio forensics, AI fingerprints, human-sounding production

User requested inspection of KillrBee/ai-music-detector, lofcz/ai-music-detector, and lcrosvila/ai-music-detection for Song Harbor sound-quality cleanup and avoiding introduced artifacts. Reviewed actual repo READMEs and implementation. Full findings: `docs/ai-audio-forensics-discovery.md`; roadmap SH-RM-235.

Key: KillrBee offers interpretable signal-domain QC ideas but lightly calibrated heuristic AI scores and no visible LICENSE. lofcz has MIT-licensed spectral fakeprint extraction and pretrained ONNX, reports high in-distribution classification performance, but no proven applicability to ACE/YuE or quality. lcrosvila researches CLAP+Essentia classifiers and demonstrates classification fragility under audio transforms; no visible LICENSE. Additional primary paper/code: Deezer ISMIR 2025 Fourier explanation.

Product direction: analyze *generated input vs edited output* and localize actual clipping, HF harshness, transient damage, phase/mono problems, tail continuity, unexpected rolloff and dynamics. Prefer source/stem/time-region diagnostics plus non-destructive level-matched repair audition. AI detector outputs are not quality targets; fingerprints can be inaudible, and watermark checks are incomplete. Do NOT auto-notch all generative spectral signatures or build watermark suppression. Optional isolated offline benchmark with documented model versions, controls and false positives. No application code changed by this discovery; not an accepted feature sprint.

---

## 2026-10-23: Accepted clip alignment design (discovery checkpoint)

**User decision, binding for Second Take and imported short stems:** A section boundary is a visual alignment suggestion, NEVER a required snap point. Align-to-section supplies an initial offset only. Imported/generated short audio is represented as a draggable, non-destructive clip with its original waveform and duration intact, virtual silence outside its bounds, song-relative start time, independent fades, and precise unsnapped fine movement. The original WAV, immutable track_id, and script alias must not change when a clip is moved. Section scripting remains anchored to absolute song time.

**Implementation status:** design approved and documented, NOT implemented. Today's `POST /tracks/add` still physically pads a working WAV to full song duration starting at 0:00. This remains a temporary compatibility behavior, not the intended clip model. Do not claim the clip can already be dragged or aligned to a section.

**Timing:** Defer standalone clip editor build and acceptance tests until the initial ACE-Step context-conditioned accompaniment generation experiment produces a real short stem. At that point implement and test the offset/clip transport across audition, WAV export, reload, and DAW exchange. No enforced snapping even with a visible snap preview.

**Next step:** User requested a brief discovery detour after updating documentation. Ask what discovery topic to pursue; do not assume it is ACE, Ardour or a new product.

---

## 2026-10-22 LATE: Persistent stem identity, rename and in-project add implemented (Windows QA pending)

Following user approval to separate immutable track identity from names, second P1 lifecycle slice committed to main.

- `section_production.source_map(files,source_tracks)` resolves mutable script aliases to immutable working WAV filenames; all saved section materializers use it. `section_import` validates imported scripts against project metadata, not filenames. Direct effect routes likewise resolve actual aliases.
- `track_lifecycle.py`: metadata backfill for old six-stem projects generates persistent IDs without renaming original WAVs; validated atomic rename checks collisions, reserved names, previously loaded alias (stale window), updates production/spatial track fields and rematerializes all audio automations while preserving lyrics/source keys. Filesystem transaction is one atomic manifest replacement. `GET /api/projects/{id}/tracks` backfills and persists metadata, `PUT /api/projects/{id}/tracks/rename` performs rename.
- Mixer has pencil rename action with two simple name/alias prompts. Rejects rename while Whole Song Section Text is open; applies pending fader changes before rename, then refreshes project/engine to prevent stale UI metadata. Existing song script is reloaded with new alias.
- `POST /api/projects/{id}/tracks/add` takes one supplied local audio file, display name and unique alias, preserves source in originals, uses FFmpeg to align/pad to existing duration, rejects longer sources instead of silently truncating, creates new working WAV and immutable ID, appends neutral mixer track, and atomically saves the project. Failed conversion removes staging files. UI provides + Add stem.
- DAW exchange now labels exported tracks by current alias and records permanent track ID rather than reintroducing an old embedded filename alias.
- `test_track_lifecycle.py` verifies renamed production effects and preserved WAV references, duplicate/reserved alias rejection and stable legacy ID generation. GitHub backend projects CI success as of `65e5085e`; latest frontend CI passed `4f2512c7`; newer add-stem UI/API commits require their own finished build and real Windows test.

**Risk and QA notes**: No actual 7/16/33-track Windows listening/export/close-reopen test yet. The upload route converts synchronously via FFmpeg inside request; it is a limited MVP and may feel unresponsive with large sources. Browser 768 MiB decoded-audio limit still applies. The UI prompts are provisional until compact inspector controls. Do not claim batch append or generated accompaniment; Second Take remains future. Full acceptance checklist is in `docs/multitrack-import-qa.md`. YouTube SRT QA remains user-deferred.

---
## 2026-10-22 NIGHT: P1 arbitrary-stem effects hardening first slice

The product increment roadmap was approved earlier today. User now requested implementation of the next slice. Code committed to main:
- Direct individual section effects routes in `app/backend/server.py` (pan, reverb, width, space, EQ) no longer infer aliases only from the six default Demucs names. They derive aliases from the actual project file list, allowing existing custom named imported stems to participate in section editing.
- `app/backend/section_production.py::materialize_reverb` now expands explicit and broadcast reverb/reset to imported custom stem aliases instead of hardcoding the six default labels.
- New `test_16_custom_tracks_reverb_and_broadcast` uses 16 synthetic `Synth_NN` stems and tests `all.reverb`, a custom override, independent gain/pan, reset, and script round trip. Backend project CI passed after fixing test fixture newline escaping, SHA `fa101be7`.
- Updated `docs/multitrack-import-qa.md` with this slice's exact boundaries.

This is **backend architecture hardening, not the full accepted 16+ stems QA**. No real 16-track import/export audio test has been performed; do not claim high-track memory viability. Add new stem to an existing song, atomic custom stem rename propagating every section directive, script draft safety, and frontend dynamic display/selection remain open. These should be the next P1 implementation increments; never rename source filenames or track_id to implement a display-name change. User's YouTube SRT QA was deferred until tomorrow and remains open. Ardour POC and Second Take additive cello generation remain subsequent roadmap work.

---

## 2026-10-22 PI REVIEW - ACTIVE DECISIONS / START HERE

**User-approved priorities and QA state**
- Track *The Logo and the Maw*: user reports rich, balanced audio and intentional environmental rightward swing in the second pre-chorus. Fade-out accepted. Preserve accepted artistic panning; do not chase numeric zero in every section.
- Section header: compact scan icon and 5-pixel bottom color strip accepted. Hover text with intensity, RMS, peak, L/R balance and width accepted.
- YouTube timed lyrics (.srt): implemented (saved section timing, editable preview/download) but **user Windows QA postponed until tomorrow**. Do not mark v0.2.1 released or formally accepted before that gate and current CI.
- Documentation catch-up approved; roadmap reconciled in `refs/planning/roadmap.yaml` and detailed PI gates below. Historical notes further down are snapshots and can contain obsolete "not implemented" descriptions. Latest dated active record takes precedence.

**P1 flexible stems and track lifecycle (approved)**
- Existing multitrack importer supports 2-64 parent tracks and channel-pair manifest reimport; neither 16/33-track Windows audio QA nor adding a new track to an EXISTING song is proved.
- Full acceptance: import 16+, add new named stem to saved song, control by human-readable alias, rename alias and automatically migrate all active script directives/drafts/reference mappings; preserve immutable track_id/source. Save/reopen/export after rename, catch collisions and rollback failures.
- Existing code still has hardcoded `ALIASES` assumptions in `section_production.materialize_reverb` and several individual section UI setter routes in `server.py`. Shared-clock decoded audio guard is 768 MiB. Do not claim arbitrary stem effects and high-count playback validated until these are fixed and tested.
- Exact QA matrix: `docs/multitrack-import-qa.md`. Next implementation priorities: add-to-existing-song API, stable alias rename transaction, replace hardcoded effect targets, large-track memory/streaming strategy.

**P1 mix versions / level-matched A/B (approved)**
- Save named non-destructive mix candidates, allow accept/reject/revert and actual matched-loudness comparison; current bypass/test modes are not the same thing. Avoid applying auto.gain:0 to the accepted track just to fill roadmap.

**P1 Ardour optional round trip (approved, narrow scope)**
- Ardour is installed on the user's Windows machine; no Ardour target has yet been added to `app/backend/daw.py`.
- One proof only: Song Harbor -> aligned stems/sections -> Ardour scripted pan/gain via documented Lua/OSC where feasible -> Ardour processed stem export -> import back into Song Harbor as a NEW reversible track version.
- Stop instead of building generic Ardour project exporter/plugin host if public interfaces are unreliable. See `docs/ardour-roundtrip-spike.md`.

**P2 Second Take additive generation (approved)**
- Primary request: "Add some cello to this section, harmonically and rhythmically fitting existing instrumentation." Require an independent new stem, retained original stems, alignment/transition checks, 2-3 candidate A/B where possible, immutable model/provenance. Test ACE-Step/YuE2 capabilities rather than assume they can output isolated conditioned stems. Evaluate symbolic/MIDI instrument alternative if needed.
- See `docs/second-take-additive-generation.md`.

**P2 surgical phrase editing**
- Under consideration only; defer until ordinary short sections fail a real workflow. Do not schedule region-editing engine as approved near-term work.

**Delivery order**
1. Tomorrow: Windows SRT preview/download QA + current checks; release baseline v0.2.1 only if verified.
2. 16+ track import/export/control and add/rename propagation, with tests.
3. Small Ardour automation/render/reimport probe in parallel only if bounded.
4. Named versions + matched-loudness candidate A/B, then additive Second Take cello prototype.
5. Conventional plugin racks, long-tail surgical editing, and auto.gain remain deferred.

---

## 2026-10-22 — Section intelligence and accepted automation roadmap

User approved hue-by-intensity section-header rendering with neutral empty opposing edge for stereo bias, generalized all.effect and auto.effect namespaces, auto.pan:center, auto.gain:0 compensation for an explicit Drums.gain:+0.75 boost, longer independent effect-return tails, per-section stem gain and level-matched A/B.

Implemented: frontend SectionInsights.ts computes post-mix per-section RMS, sample peak, L/R balance and side/mid width from offline mix; SharedClockAudition.analyzeMix(section ranges) exposes sectionInsights; StemMixer feeds SectionEditor. Sections receive subtle cool-to-warm hue based on song-relative intensity and neutral edge on opposite side of louder channel (left-heavy => neutral right edge). Hover reports exact metrics. Re-analysis using Sound cleanup > Analyze mix required after changes. Stale stats cleared on effect/stem/section or bypass modifications. Regression tests in app/frontend/tests/section-insights.test.mjs. No DSP changes.

Scoped but NOT implemented yet: all.effect / auto.effect DSL, stem.gain section directives, wet return tail enhancement, loudness-matched A/B. Grammar rules and safety priorities documented in docs/section-intelligence-sprint.md; current production importer intentionally rejects new tags. Follow existing parser, preview and render architecture. Browser QA section hues and alignment remains. CI status must be verified separately.

---
## 2026-10-22: pre-release acoustic signal screening (non-destructive)

User asked whether Suno source C2PA metadata naturally disappears when Song Harbor exports WAV; confirmed from the actual `encodeWav24` implementation in `SharedClockAudition.ts`: output RIFF has **only the 44-byte PCM WAV header with fmt and data chunks**, no source metadata forwarding, so original C2PA provenance chunk is not copied. Distinguish **source-file provenance/soft-binding fingerprint metadata** from **actual acoustic watermark**; no claim that re-rendering erases fingerprints computed from content or provider-specific embedded audio watermark.

User approved **audio signal screening without any automatic action**. Implemented directly on `main`:
- New `app/frontend/src/SignalAudit.ts` independent deterministic scanner, streaming bounded 4096-sample Hann-windowed FFT analysis across song (at most 600 windows); searches for persistent high-frequency (>4kHz to 11.5kHz, where supported) narrowband lines >22dB above nearby band with >62% sampled active-window persistence and at least 12 windows/10 seconds, returns up to 3 *possible* anomalies (timestamp, duration, Hz, spectral contrast, prevalence). Limited by design: ignores low bands, short bursts, spread spectrum and provider-specific embedded signals. A normal synth or resonant instrument can trigger; a negative result does not prove watermark absent.
- `AudioCleanupAnalyzer.ts` merges those with existing non-destructive `AudioFinding` results as `signal_audit`, severity Review, safe text with explicit no-identification language; output mixes and audio remain unchanged.
- `CleanupReview.tsx` adds **Signal audit** category, warnings about false positives and no automatic filtering/removal. Ordinary loop-to-review/timestamp workflow reused.
- `app/frontend/tests/audio-cleanup.test.mjs` adds synthesized persistent 6kHz reference, silence/low-note/short-clip negatives, source-buffer immutability. Frontend CI synthetic DSP tests **passed at `99aabfbd`**, as did TS bundle and initial Chromium UI mount; full backend-served browser smoke still in progress at last check.
- `docs/user-guide.md` updated on clean RIFF export, feature behavior, uncertainty and privacy. No source metadata byte manipulation API, no fingerprint verification, no cloud upload.
- GitHub Actions initially failed in Node test runner because import extension was omitted; fixed by explicit `./SignalAudit.ts` import (tsconfig already has `allowImportingTsExtensions=true`). Avoid reversing fix.

QA: After pulling latest, run Sound cleanup > Analyze mix > filter Signal audit; expect maybe 0 results on Salt in the Circuit because no obvious stable narrowband tone earlier. Test intentionally sustained synthetic tone separately. No "watermark detected" or automatic correction should appear. Consider future metadata-reporting separate from audio detector if useful, but do not implement auto-removal.

---

---
type: Handoff
title: Current Song Harbor Handoff
description: Current audited handoff, QA status, and next-thread starting point.
status: active
tags: [handoff]
---
# Current Handoff

## 2026-10-22 QA follow-up: persisted listening volume, scrollable floating tools, whole-song text and section A/B

User tested full-window workspace, floating windows, Section Edit, and analyzer; reports: (1) monitor playback volume resets loudly each app restart, (2) mousewheel does not scroll tool popovers, (3) analyzer A/B good, (4) Section Edit effect controls should have their own real-time non-destructive A/B before Apply, and (5) discoverable **full raw section script covering the entire song** is missing from present UI.

**Implemented on `main`:**

- `StemMixer.tsx`: monitoring slider reads/writes local browser storage key `song-harbor:monitor-volume`, clamped 0–100, safe first-launch/fallback **25%** (previous 75%). Shared across song sessions within the same dedicated Chromium browser profile. The monitor slider still affects audition only, not stem gain/project save or WAV mix.
- `WorkbenchTools.tsx` and `song-harbor.css`: ToolWindow content stops wheel event propagation to underlying workspace while preserving native scrolling; removes overscroll containment in tool content and cleanup list, retains flex child `min-height:0`, inner independent scrolling and visible scrollbars. Added Chromium smoke check to inject an actual CSS floating window and verify mousewheel changes `scrollTop` rather than the page.
- `StemMixer.tsx` now displays a prominent **Edit whole-song section text…** action inside Edit sections, launching a separate wide/resizable floating window **Whole-song section text** (not a primary effect tab). It mounts the existing `SectionsTool` backing `GET /api/projects/:id/sections/export` and `POST .../sections/import`, so the user can see/edit the full authoritative source: every section header, every curly-brace production block, and all lyrics across the song. Script drafts retained in memory while switching tools; Apply validates and persists. Full text editing is *not* live-previewed without validated Apply. The main Section Edit window keeps shared section dropdown + Pan/Reverb/Width/Reflections/EQ/De-ess tabs.
- `SectionPanTool.tsx`, `SectionReverbTool.tsx`, `SectionWidthTool.tsx`, `SectionSpaceTool.tsx`, `SectionEqTool.tsx`, and `SectionDeEssTool.tsx`: accept optional previewEnabled/onPreview and generate temporary proposed target arrays in frontend on slider/select changes when B Draft is enabled; they do **not** write to the API until their explicit Save/Apply action. Their existing saved targets still come from validated backend on successful Save.
- `StemMixer.tsx`: isolated `SectionPreview` union holds unsaved per-effect target curves. **A · Saved / B · Draft preview** in Edit sections above effect tabs; choosing B sets loop bounds for selected section, seeks to its beginning and plays if stopped. While B, existing shared-clock per-stem automation compiles from staged target arrays (pan, reverb, width, space, EQ, de-ess) using `engine.setAutomation(byFile,true)`; no saved song mutation. Choose A to hear saved curves, switch effect/section or close Edit sections to discard staged preview. Effect Save/Apply writes the backend and ends the draft. WAV export disabled during B preview. If analyzer correction is active, choosing B clears analyzer preview so two trial lanes don't silently compose. Scripts are not directly live-previewed: whole-song editor validation is needed.
- `SectionsTool.tsx` identifies **Whole-song script · all sections and lyrics**, supports de-ess in typed targets and updated syntax help. `HelpDialog.tsx` and `docs/user-guide.md` updated for discoverability and safe volume.
- `app/frontend/scripts/browser-smoke.mjs` now tests wheel scrolling in real Chromium against compiled CSS. Earliest compiled frontend at `446a1521` and later at `68fcea36` passed; newest smoke test and code changes need final CI confirmation. No direct Windows listener or persistence cross-relaunch QA yet.

**Windows QA**:
1. Set monitor volume to 12%, restart Song Harbor through the BAT, reopen same or different song: slider should remain 12%; no loud 75% initial blast. A brand-new Chromium browser profile should begin at 25%. These settings must not affect exported audio.
2. Open two floating tools; scroll inside each, verify content moves with wheel and main waveform/page position does not. Resize panels and check scrollbars at smaller heights. Mousewheel over *waveform* should still scroll the page, not zoom.
3. Open Edit sections -> Edit whole-song section text…; verify complete lyrics + every section's production block visible, not just chosen section. Change a safe directive, Apply, close/reopen, verify persisted; don't change lyrics unless intended. Whole-song raw text must be prominent and editable, not a read-only dump.
4. Select a section and Pan/EQ/De-ess etc.; choose B Draft, play and adjust slider: hear immediate change and loop stays aligned. Choose A: saved sound returns. Close tool without saving: project/export unchanged; reopen and compare. Save while B -> effect persists after relaunch; output WAV reflects accepted target. Switching section/effect cancels unsaved preview. While B, WAV export should be unavailable.
5. Confirm existing analyzer A/B still works unaffected and no accidental 3× audition settings enter saved mix.

**Limitations:** Section Edit preview covers current effect tabs, **not direct text parsing of unsaved entire-song script**; user must press Apply for script text. A/B is not loudness-matched blind testing. Monitor preference relies on browser profile's localStorage (and will reset if that profile is erased). Chromium smoke fixture tests scrolling mechanics, not actual Windows mouse hardware; require real QA.

---

## 2026-10-22: gain reduction / exaggerated A/B and per-section de-esser milestone

User accepted Song Harbor layout, full section Script access, double-click to Edit sections, multi-window z-order, and analyzer report (03:35 +0.2 dBFS peak, 02:43 loudness dips). User could not hear compression/ducking trial differences and approved next two priorities: **visible gain-reduction feedback and meaningful A/B**, then **targeted section-aware de-essing**. Continued directly on `main`.

**Implemented:**
- `SectionDynamics.ts`: per-stem neutral-by-default peaking Biquad de-esser between compressor and duck gain. A deterministic two-pole high-pass envelope detector monitors sibilance-band activity (attack ~12ms, release ~120ms) and schedules dynamic negative peaking-filter gain up to the section's max reduction. Two-pole detector rejects low vocal fundamentals better than one-pole. Frequency 3-11kHz, Q .4-8, threshold -70..-10 dBFS, maximum 0-12dB. Preview/offline renderer both schedule identical curve; original buffers untouched.
- `SharedClockAudition.ts`: builds deesser on each source bus in live AudioContext and offline 24-bit WAV render; mirrors section automation and L/R derived buffers; schedules cleanup/bypass and releases nodes. `dynamicsMeters` reports live WebAudio compressor.reduction, duck GainNode attenuation and de-esser Biquad gain (dB) per parent stem. A/B has independent compressor/duck/de-ess bypass keys and B Original removes all three in audition only.
- `section_production.py`: new `Vocals.deess:6500,2,-40,4@2s:smooth` parsed, validated, round-tripped, inherited and reset; `materialize_dynamics` persists `kind=deess` targets. Direct Script interface remains fully intact; old songs neutral without deess. `section_import.apply` and server's existing import/export route persist with no new ad-hoc file mutation.
- `StemMixer.tsx`: compiles `kind=deess` per-section frequency/Q/threshold/max reduction curves; live meters refreshed ~130ms only while visible. Correction trial adds de-esser for analyzer sibilance-like findings and chooses Vocals as suggested stem. **3× audition strength** previews exaggerated reduction only and never writes boosted values. Unboosted values go through validated script import on Accept. Full offline WAV always uses accepted production directives, not audition A/B bypass or unaccepted trial.
- `CorrectionWorkbench.tsx`: direct adjustable frequency, Q, threshold, max reduction, updated live meters (comp/duck/deess) and "Actual 1× / Exaggerated audition 3×" selector. Intended to reveal subtle processing without misrepresenting delivered sound. `CleanupReview.tsx` offers Try correction on sibilance-like findings.
- `SectionDeEssTool.tsx`: new **Edit sections → De-ess** tab, follows shared section selection; sliders and Apply safely rewrite one targeted de-esser script token via authoritative `GET sections/export` / `POST sections/import`. Script tab remains accessible for full text. Updates all frontend project production targets on success.
- Documentation updated in `docs/user-guide.md`, in-app `HelpDialog.tsx`, `docs/dynamics-cleanup-qa.md`.
- Regression tests: backend `test_section_deess.py` checks notation, range, normal reset, conflict and materialization (wired to Song projects CI). Frontend `section-deess.test.mjs` builds DSP module with esbuild and tests synthesized HF/low-frequency/silent/max reduction/split input behavior (wired to frontend CI).

**Important limits**: A/B is **not yet genuinely integrated-loudness-matched**; exaggerated trial is instead a deliberately marked 3× audition diagnostic. Browser compressor gain reduction is read from WebAudio, duck/deess attenuation read from scheduled AudioParams; these are live approximations, not integrated LUFS or true peak. The detector is not a trained vocal/sibilant classifier, and cymbals, hi-hats, guitar and synth noise may be flagged. No automatic de-essing or destructive edit. De-ess affects a whole named section and may inherit until changed; do not call it a phrase-isolated repair.

**Verification:** Backend projects CI passed at `d4efa673` (before latest frontend); the new Section de-ess test workflow was started. Frontend build passed at `2c75b3d8` after initial de-esser data wiring, with later UI/test work queued heavily. Do not claim newest changes or actual audio preview/export parity tested until latest CI and user Windows listening checks succeed. First Windows QA: check Edit sections → De-ess, Script roundtrip, sibilance trial actual 1× vs exaggerated 3×, live gain reduction, A/B deess bypass, 24-bit WAV processed rendering and preservation of other directives/lyrics. Compare sibilants and cymbals to avoid over-deessing intentional textures.

**Next after QA**: integrated LUFS and oversampled true-peak analysis, and gain-level-matched blind A/B comparisons; avoid adding a conventional broad effects rack ahead of section-oriented correction workflows.

---

## 2026-10-22: first-pass icon rail QA and unified Section Edit / multi-window follow-up

User supplied desktop screenshot; fullscreen shell, top-right Close X, working project `The Logo and the Maw`, and 12 L/R waveform rows display. First-pass UI approved; requested: icons 2–3x bigger and narrower reserved rail, corner-resizable tools, optional multiple tool windows simultaneously, rename DAW Handoff to **Download**, consolidate all per-section effects in one **Edit sections** tool, and double-clicking section block on timeline to open editor focused on that section.

**Implemented on main:**
- `WorkbenchTools.tsx`: rail now has eight categories (Edit sections, Sound cleanup, A/B, Ending, Zoom, Loop, Split channels, Download). Old Pan/Reverb/Width/Reflections/EQ rail icons removed. Multiple windows can remain open concurrently and click-to-front reorder; each keeps initial/restored drag position. Same non-modal draggable floating panes, now resizable by CSS lower-right corner.
- `StemMixer.tsx`: `openTools` list replaces single `selectedTool`. **Edit sections** window has shared section selector and tabs Script, Pan, Reverb, Width, Reflections, EQ. The selected effect subtool is the only one mounted; dynamics remain addressable through Script and analyzer correction A/B. `SectionEditor.onSectionDoubleClick` opens/raises `sectionEdit`, sets exact clicked section as shared selection and opens Pan tab. Tool close dismisses only that window (cleanup close also discards unaccepted correction); other windows stay open. Download icon opens existing aligned-track exporter.
- Per-effect tools `SectionPanTool`, `SectionReverbTool`, `SectionWidthTool`, `SectionSpaceTool`, `SectionEqTool` accept optional `initialSectionId`, react to shared selection, and hide redundant internal section selectors only when embedded in unified edit panel. Local data persistence unchanged.
- `song-harbor.css`: high-specificity workspace grid fixes previous broad ~300px reserved column; now 54px rail and 48px-wide icons with ~39px glyphs, responsive 46px rail. Floating tool defaults ~490×520 and supports native CSS resize:both (minimum 315×230) with independently scrollable content and corner handle. Multiple windows automatically stagger on initial opening; bring-to-front doesn't change original position.
- `DawHandoff.tsx`: renamed tool/modal **Download tracks**, changed primary action to **Export tracks**, folder button **Open folder**, and optional DAW launching is explicitly separate. This still exports files to a **local folder**; a browser ZIP download is not yet implemented. Do not pretend the DAW installation helper is already gone.
- `docs/user-guide.md` and handoff synchronized.
- CI passed on commit `8b405754`: Frontend build + browser smoke and single-server launch smoke success (covers the refactor and CSS). Later changes were simple label/docs and have also passed through `52209dd1`. Actual multi-window drag/resize and section effect QA on Windows still outstanding.

**Suggested QA**: Launch from BAT; verify 54px icon rail actually reclaims 200+px of waveform. Open Cleanup and Edit sections simultaneously; resize each from corner, drag, bring one forward, close it and verify other unaffected. In Edit sections choose Verse 2 -> EQ -> set a band; verify section selected from shared picker and saved effect persists. Double-click Bridge in waveform -> Edit sections opens/raises at Bridge (Pan tab) without a full script editor; try switching to Script and editing text, switch to another tool, return and confirm unsaved text retained. Download opens export controls, folder path, optional DAW launch separate. Test with 6 grouped stems and 12 children; no overflow or lost playback focus.

---

## 2026-10-22: fullscreen app window, icon tool rail, floating edit panes and correction A/B

User shallow-accepted analyzer: 03:35 peak +0.2 dBFS (Drums/Bass activity hint, suggest -1.2dB master trim) and 02:43 repeated level dips (Vocals/Drums activity hint). Asked for quick UI/UX cleanup and ideal loop-based correction workflow.

**Implemented directly to `main`:**

- The Windows `app/run.ps1` launcher opens isolated fullscreen Chromium app window for selected Chrome/Edge/Brave/Vivaldi default browsers, isolated Firefox kiosk profile for Firefox, and generic default browser fallback. Saves only its own browser process handle and closes that dedicated process when its backend exits. No general browser process enumeration or kill. Browser profile cache lives under local `cache/`. `app/backend/server.py` exposes token-guarded, local-origin-only `POST /api/runtime/quit`, rejects busy jobs. Far-right close X in `main.tsx` requests confirmation and gracefully shuts down current backend; if browser script close denied, shows closed page. Test `test_runtime_quit.py` wired to backend CI.
- `WorkbenchTools.tsx`: compact icon rail and non-modal draggable floating tool window with Esc and close X, over waveform, no permanent 255px Tools sidebar. Only selected tool panel visible: Sections, Sound cleanup, pan, reverb, width, space, A/B, EQ, ending, zoom, region loop, channel splitting and DAW handoff. Effect panels expand upon selection. Primary mix/export remains below the waveform across full width. `SectionsTool` preserves an unapplied draft **in memory only** while switching tools; saves still require Apply.
- `CorrectionWorkbench.tsx` + `CleanupReview.tsx` + `StemMixer.tsx`: `Try correction A/B` on peak or pumping findings. Loop around event, compare **A Saved** against temporary **B Proposed** while editing controls. For clipping candidate suggest sample-peak-trim (session-only). For repeated loudness dips, prefer neutralizing the latest active vocal duck or compressor target; user can choose track, compressor threshold/ratio or duck depth and transition. Draft dynamics override exists only in frontend, preview reschedules existing AudioParams rather than restarting sources for every fader change. On **Accept**, GET authoritative `sections/export`, change one section directive for the chosen alias, POST validated full `sections/import` which persists production text and derived targets atomically; rejects invalid reset conflicts. Discard or switching tools cancels temp override. Disable WAV export or reanalysis while unaccepted correction is being auditioned: preview must not leak into WAV. Actual source WAV files are never rewritten. Editor documentation/help updated.
- `SharedClockAudition.setAutomation(curves,liveTrial)` reschedules live trial parameter curves on existing sources, minimizing audio stalls during A/B. `setEnding` now exits early when unchanged to avoid unwanted seek from correction updates.
- `docs/user-guide.md` and in-app `HelpDialog.tsx` updated. QA needed in `docs/dynamics-cleanup-qa.md` and Windows local shell.

**Acceptance tests pending**: On Windows confirm fullscreen opens in *dedicated* browser app, far-right X closes only that app/backend and refuses an active job. Test app menu keyboard focus and dragging tool windows without stealing transport. Verify the main waveform is wider. Validate `Try correction A/B` on known 03:35 peak and 02:43 pumping event: B changes playback, A restores, Accept writes correct directive under original lyrics/timings, Discard leaves project unchanged, unaccepted draft cannot export, and output trim is session-only. Verify Windows `run.ps1` syntax workflow and backend quit tests. CI had heavy queued work; early frontend build `09d7ef68` and launch smoke passed, but recent changes to tool layout/correction must not be declared QA-proven until their own runs complete.

**Known limitations**: This is a floating panel *within Song Harbor's browser window*, not independent OS child window, so it remains in app bounds. Fullscreen is implemented only where launcher can safely invoke the default browser with an isolated profile. A/B correction supports only session trim and section compression/ducking today, not de-essing/EQ/other artifact repairs. Editing and persist mechanisms are non-destructive. Master output trim is not durable across relaunch. No loudness matching of A/B.

---

## 2026-10-22: expanded sound-cleanup detection and review UI

User reports A/B compression/ducking bypass works, and first on-demand scan found `03:35 Peak exceeds 0 dBFS`. Accepted priority: add missing detection categories THEN make sound cleanup practical in UI; maintain non-destructive local-first behavior.

**Code delivered on `main`:**
- `AudioCleanupAnalyzer.ts`: deterministic, bounded peak and sample discontinuity, flat-topped waveform, FFT spectral sibilance-like bursts (5–9.5 kHz), high presence emphasis (2.5–4.9 kHz), upper-band fizz, quiet high-frequency residue, stereo negative-correlation mono risk, repeated RMS level troughs. These are signal heuristics and may flag creative music; don't claim confirmed de-essing or AI artifact identification. Conservative type-specific cooldown/max findings, severities and suggested next action; optimized precomputed 2048-bin FFT twiddles; output-trim-aware peak suggestion aiming for -1 dBFS sample ceiling (not true peak).
- `SharedClockAudition.ts`: `analyzeMix()` and processed `renderWav24()` use same offline AudioContext render graph. Findings annotated with up to 2 prominent *raw stem activity* hints (not causal attribution), accounting for stem level and split-child buffers.
- `CleanupReview.tsx`: analyzer appears directly below Sections in existing narrow Tools column; per-category filters, count/severity, temporary reviewed toggle, click-to-seek, **Loop ± context** that sets an audition region and starts playback, suggestion copy and active source hints. No workspace width loss or automatic media modifications.
- `StemMixer.tsx` and `song-harbor.css`: a single slim **QC finding marker rail** sits between section timeline and stem waveform rows (not repeated for every L/R child). Markers seek to associated timestamps and follow timeline zoom/pan.
- `StemMixer.tsx`: published scan results cleared when stem balance, trim, effects, ending or channel routing changes, avoiding stale review on changed mix; analysis started during a mix change refuses stale completion. Prior successful WAV export also publishes findings.
- Documentation synced in in-app Help and `docs/user-guide.md`; QA plan `docs/dynamics-cleanup-qa.md`. Synthetic deterministic regression tests `app/frontend/tests/audio-cleanup.test.mjs` wired into `.github/workflows/frontend-build.yml`.

**Verification needs:** At checkpoint time GitHub Actions runners were queued heavily after commits; treat synthetic tests, actual Windows audio scan, runtime speed and UI loop behavior as **pending** until explicit evidence arrives. Do not claim de-essing, accurate artifact classification, stem attribution, or sound quality improvements. User's known 03:35 peak is the first useful validation target. User asked for "missing analysis", not yet automatic surgical repair; next stage could add precise de-esser and artifact cleanup actions after listening QA.

---

## 2026-10-22 laptop QA: explicit dynamics A/B, sound cleanup, zoom, build identity

User on a production laptop deferred multi-track import test. Screenshot confirmed Tools A/B offered one opaque `Bypass dynamics` toggle rather than separate compression/ducking, and sound cleanup was hidden until processed WAV export and poorly discoverable. Mouse-wheel waveform zoom hijacked normal page scrolling. The Git SHA badge `main@... ` was not usable as release identity. User requested **Version:Revision:Build** rather than hash; later true fullscreen desktop-mode app and far-right topbar close X.

**Implemented on main:**
- Frontend A/B exposes independent **Bypass compression** and **Bypass ducking** controls, plus previous individual effects. B Original bypasses both; A Processed restores both. SharedClockAudition schedule separately disables compressor and duck envelope only in audition, while offline rendered audio remains processed.
- Restored native mouse-wheel screen scrolling over waveform and timeline. Zoom remains available through Tools dropdown and slider. Removed non-passive wheel handler to avoid scroll capture.
- Sound cleanup analyzer is now an always discoverable Tools section with **Analyze mix** button, candidate timestamp list with click-to-seek. Uses same OfflineAudioContext render graph as WAV export but does not encode/download a WAV or change source audio. Successful WAV export still refreshes findings. Analysis detects near-ceiling peaks and extreme single-sample jumps only; can false-positive percussion and won't de-ess.
- Version badge is `Version:Revision:Build`, e.g. `0.1.0:1:412`. Package version read from `app/frontend/package.json`; revision development epoch is `1`; build is git `rev-list --count HEAD`; full short Git commit/branch only in tooltip. No network access needed; fallback build=local. `test_version_badge.py` in backend CI.
- In-app Help + docs/user-guide.md updated to reflect behavior and no wheel zoom.
- **Deferred shell request:** True fullscreen desktop-style startup and far-right close X must be implemented as a platform-aware shell strategy. Browser window.close() cannot reliably close the host or backend for self-opened tabs; avoid pretending it is implemented. Design a safe explicit local quit endpoint guarded by instance token, confirmation of unsaved work, and fullscreen-window startup with browser kiosk/app mode where appropriate, with a normal window opt-out. Avoid killing unrelated browser sessions or orphaning backend.
- QA: Confirm each bypass toggles independently with `Other.comp:-18,2` and `Guitar.duck:3`; run Analyze mix before export, seek results, then render WAV; verify native page scrolling when pointer is over waveform and Tools Zoom works; confirm version badge uses three fields and tooltip contains diagnostic commit. Performance caveat: analyzer offline-renders full mix even before WAV, so consider recording memory/cpu impact on long songs. Last frontend real Chromium build at `87daecc2` succeeded; newest commits await CI. No actual Windows listening QA.

---

## 2026-10-22 pre-test: L/R manifest restore and dozens of named tracks

User specifically blocked acceptance testing until native Song Harbor split export (`12 mono WAV + manifest.json`) and arbitrary named track support are addressed.

**Implemented on main:**
- New `stem_import.channel_groups` validates the real `song-harbor-stereo-channel-split` v1 manifest, checks exact uploaded files, safe flat filenames, complete unique L/R pairs, group count, and rejects malformed/incomplete manifests. Input is WAVs plus `manifest.json`; do not include README.txt. Support up to 64 paired parents / 128 mono children.
- `POST /api/jobs/import-tracks` now separates `manifest.json` from audio uploads. For a valid manifest it reconstructs each stereo working parent from its two mono channels using FFmpeg, copies immutable mono originals into a new per-job `Channels-Imported-<id>` folder and writes a remapped project-local channel manifest. Sets `channel_children[parent].active=true`; existing playback/route switching sees it just like an in-app stereo split.
- Standalone multi-track import supports 2-64 parents. Input media ceiling 1GiB per audio file and 16GiB per batch; source originals preserved. Custom names sanitized to unique aliases from original filenames, each with `track_id` stable across display-name changes. `stem_name`, `channel_split`, `SaveProject`, channel split API no longer require fixed six aliases/count.
- `section_production` derives allowed stem aliases from current project working WAVs; `section_import.apply` passes them to the script parser. Pan, width, space, reverb, EQ, compression, ducking, reset can address arbitrary aliases, not only initial six; supports up to 512 production tokens per section. Mixer displays original imported source names and the exact script alias in a compact extra label; classic six-stem mixer retains original icon layout.
- Import screen accepts up to 64 standalone files or 128 mono+manifest with title inference from manifest parent source names; user override remains.
- Tests: `test_stem_import.py` verifies exact 12-file manifest reimport to six parents with active L/R routing, malformed manifests, and 33 named source aliases in section pan/EQ scripts. Python backend CI passed at `1a57d74a` for parser fix; additional later changes in tests/docs/alias UI should be rechecked. Frontend build passed at `f69df049`, and post-named-stem builds need verification.
- Ran actual local FFmpeg filter smoke on synthetic float-mono Left/Right WAVs; produced a valid 48 kHz stereo working parent. This is command validation, not end-to-end audio QA on user's Windows song.
- Documentation: `docs/user-guide.md`, in-app `HelpDialog.tsx`, and `docs/multitrack-import-qa.md` updated.

**Limits and future contract:** Browser shared-clock preview still limits decoded AudioBuffers to 768MiB; long mixes containing dozens of tracks may need future chunked streaming even though project save/reopen/DAW handoff accept 64. Source track IDs are stable, script alias is human-readable. When implementing editor track rename, do not change immutable `track_id`/media keys; instead perform atomic validation/migration of every section block, all stored production/spatial references and derived targets to the renamed alias. Renaming UI and atomic alias migration are explicitly *future work*, not implemented now. Do not let a cosmetic edit silently orphan production references.

**Next user test:** Reimport exact 12 mono WAVs PLUS their manifest from a known six-stem split; confirm Library opens 6 parents, all in L/R active state, stereo toggle works, audio is aligned, and WAV export matches expectations. Then import 16+ named tracks and test per-name section script, subject to decoded-audio limit. Rollback checkpoint remains available.

---

## 2026-10-22: first-class multi-track import

Requested: Import screen must accept multiple existing stems/tracks into **one song**, suggest title from their common filename portion and offer manual override. Implemented directly on `main`:

- Import screen toggle `Single recording · separate stems` vs `Multiple tracks · already separated`; latter accepts 2-12 files, previews names/sizes, guesses title from filename common prefix and offers editable override.
- `POST /api/jobs/import-tracks`: accepts multipart `files` and `title` Form, streams files to `jobs/<id>/originals` (original bytes retained), converts each locally via FFmpeg to aligned 48k stereo 24-bit WAV under `stems`. Shorter stems padded silently to longest with no time stretching. Background job progress flows through existing polling; max 15 minutes, 1 GiB/file and 2 GiB/batch; invalid or duplicate names rejected. Demucs separator is NOT called.
- `stem_import.py`: infers canonical labels Vocals/Drums/Bass/Guitar/Piano/Other, including the `(Vocals)_htdemucs_6s` pattern. Unknown or repeated labels become independent TrackNN. `source_tracks` mapping persists original filenames and working aliases.
- `projects.py`, `server.py`, `library.py`: 2-12 imported stem projects can be saved, reopened, indexed in Library and exchanged via DAW export without the old exact-six constraint. Legacy separation still requires its six stems.
- Mixer shows original names for imported tracks. Existing waveform/timeline and A/B engine are reused.
- Added backend tests (`test_stem_import.py`, CI backend project workflow), guide/Help and `docs/multitrack-import-qa.md`.
- **Verification:** latest frontend build at `f54b0a6a` passed. Backend project CI at `d18155d7` passed including mocked track conversion. Windows smoke at `f54b0a6a` passed; Windows end-to-end real audio import and playback still require user QA.

Limits: original six canonical aliases are the section effect grammar; additional TrackNN files can be mixed/exported but not yet individually addressed by section scripts. No automatic offset alignment, stem role reassignment or time stretching. Do not call this a source synchronization tool.

**Next:** User should update/relaunch, try imported 2-6 existing stems including a manually overridden title, check Library reopen and listen for track sync; extend dynamic script grammar to custom aliases as future scoped work.

---

## 2026-10-21 late: post-checkpoint dynamics and cleanup milestone

User explicitly confirms a safely downloaded rollback checkpoint exists and prioritizes continued development rather than release freeze. Implemented and committed to `main`:

- A/B comparison now includes `dynamics` key; B Original bypasses compression and ducking during live audition. Processed WAV bounce ignores audition bypass.
- `SharedClockAudition.setLevels` no longer calls `setAutomation`/seek or restarts sources when stem levels change. Only changed sidechain-key gains rebuild and reschedule downstream duck GainNode; monitor-only volume changes do not recompute ducking. Stem gain uses a brief target ramp.
- First non-destructive audio cleanup inspector scans the float render prior to 24-bit WAV encoding for near-ceiling peaks and very large single-sample changes. Tools presents a clickable `Sound cleanup review` after successful render; this is **candidate detection**, not automatic repair, de-essing, or general artifact detection.
- Documentation updated: `docs/user-guide.md`, `app/frontend/src/HelpDialog.tsx`, QA checklist `docs/dynamics-cleanup-qa.md`.
- Frontend build passed at `cf20f1ec` for integrated analyzer UI, and older `02713968` passed; the most recent docs/UI jobs may still be pending. No user-machine listening QA done. Do not state full playback/export parity verified.

**Next:** Validate listening transport during repeated vocal gain drags, B-original dynamics bypass, user-facing candidate false positives and CPU cost, fade/tail export. Optimize detector caching/scheduling and continue with gain-reduction visibility/de-essing work if QA allows. User's upcoming track release can use their downloaded safe checkpoint independently of development.

---

## 2026-10-21: first external testers and in-app Help

User reports additional people are now testing Song Harbor. Added an always-available **i** Help icon immediately beside header Settings. Opens a TWS Dialog with offline searchable user guidance: quick start, Library, synchronized transport/mixer, non-destructive section script grammar, supported pan/width/space/reverb/EQ/compression/vocal ducking, fade/tail, WAV versus original stem DAW export, safe update/version, troubleshooting and feedback. Help content is maintained in `app/frontend/src/HelpDialog.tsx`; external user-facing guide in `docs/user-guide.md`. Tester QA checklist in `docs/help-qa-checklist.md`. `README.md` links guide and updates capabilities. Frontend TypeScript/build passed at `02713968` for final UI/CSS changes; actual Windows modal/accessibility acceptance pending.

**New documentation gate:** For any feature or renamed control, update in-app Help AND `docs/user-guide.md` in the same change. Keep user descriptions limited to implemented behavior. Avoid modal/sidebar UI that reduces timeline width. Continue receiving tester version badge and steps with each bug.

---

## 2026-10-21 follow-up: updater acceptance, version badge, scoped Outro correction

User reports soft update/relaunch apparently successful on Windows. This is preliminary user acceptance for the main happy path only; conflict protection and busy-job refusal remain separate checks. Added compact always-visible `main@<8-char-sha>` badge alongside the in-app update icon. `GET /api/runtime/version` uses local Git commands only, no network fetch, and falls back to `local` when unavailable. Badge refreshes on relaunch and after an explicit update check. No invented semver.

The submitted 13-section Salt in the Circuit sheet contained a specific Outro conflict: `Other.reset@2s:smooth` appears with `Other.pan`, `Other.width`, and `Other.space` in the same production block. This is correctly forbidden by the reset grammar. Replace ONLY `Other.reset@2s:smooth` with `Other.comp:-18,1@2s:smooth` to restore neutral compression without clearing explicitly set spatial effects. `Guitar.duck:0@1s:smooth` stays. Do not change lyrics, durations, master fade 4s, or tail 3s. Parser now returns a specific actionable reset-conflict diagnostic; regression test verifies correction, dynamics and ending. This does not silently rewrite existing saved user song content.


## Development checkpoint - 2026-10-21 dynamics on main

Section compressor and vocal-keyed ducking are wired through the shared playback/offline engine, with import/export persistence, validated production scripts, and neutral legacy defaults. See `docs/section-dynamics-implementation.md` for exact grammar, implementation and QA gaps. Backend CI passed at `830c4f53`; latest frontend/Windows checks remain pending. Do not mark update/relaunch, EQ persistence, fade/tail or listening parity as user-accepted.

## START HERE — 2026-10-21 handoff after in-app updates and section EQ

**Branch:** Work directly on `main` of `Three-Wheeled-Sloth-Studio/Song-Harbor`. Supported Windows launcher: `scripts/launch-song-harbor.bat`. Checkout observed at `C:\\Apps\\Song-Harbor`, with separate runtime `C:\\Apps\\SongHarbor`. Launcher safely fast-forwards updates when Git permits, builds frontend (`tsc --noEmit && vite build`), then starts one FastAPI server on an available loopback port; Vite is build-time only. Local projects and source WAVs are non-destructive. See `app/README.md` for setup. **Do not start another feature branch or resurrect superseded HTMLAudioElement multi-stream transport.**

### Latest user acceptance and open verification

- User confirmed the final *The Logo and the Maw* spatial treatment is **“very good and epic”**. The processed in-app audio and exported WAV were both reported to sound good after the fade-excitation fix. Audible section pan and widening carry through the export. The section EQ sounds **“subtle, but good”** in the latest feedback. Treat these as *user listening acceptance*, not proof of numerical null/parity or every individual code path.
- The earlier clipping error now offers one-click, non-destructive master output trim. Browser-generated 24-bit WAV requires an explicit **Download WAV** click; actual destination is controlled by browser settings. Master trim is **session-only**, not persisted.
- Sections text reload previously failed due to a backend `render_block` attempt to access `transition_seconds` on `Master.fade`/`Master.tail`; serializer ordering and editor cache refresh were repaired, and the 13-section full sheet has a regression fixture. User had to reenter a block before fix; no later explicit section-reload acceptance report. Do not assert that long-term persistence has been verified end-to-end.
- Latest new `↻` update-check/relaunch control has **not** been verified by user on Windows. No completed CI run for the latest group of commits has been confirmed here, and the assistant did not execute a full local build. Before expanding DSP, QA its header display, update status, independent PowerShell handoff, process shutdown/restart, project persistence, and Git conflict protection. Review `app/backend/app_update.py`, `scripts/relaunch-song-harbor.ps1`, `app/frontend/src/UpdateControl.tsx`.
- The prior harmless `GET /favicon.ico 404` led to `public/favicon.svg`, `index.html` reference and FastAPI `/favicon.svg` route. This avoids requests from the new page icon, but legacy explicit `/favicon.ico` probes can still 404 harmlessly.

### Current production stack — distinguish implemented from planned

- Local six-stem separation (Vocals/Drums/Bass/Guitar/Piano/Other), song Library/project persistence, waveform overview, section timeline, split L/R source routing with parent exclusivity, and stable shared-clock Web Audio `AudioBufferSourceNode` transport. Decode limit **768 MiB** and >150ms stem-duration mismatch check; no fallback to phase-unsafe independent media streams. User previously found split-channel drift and waveform-stall bugs; shared-clock approach is the accepted architecture.
- 13-section *The Logo and the Maw* test content: `docs/qa-full-spatial-the-logo-and-the-maw.txt` (four-minute source, Outro 3:48.183–4:00, optional 3s wet post-roll to ~4:03). Preserve existing lyrics, exact section labels/timings, and inherited effects; do not regenerate new lyrics or automatically replace sheet while testing other effects.
- Canonical production grammar: one `[Section time]` line, optional **single** `{...}` directive line and original lyrics beneath. Supported `Track.pan:left.40@2s:smooth`, `Track.width:135@2s:smooth` (0–150%), `Track.space:20@2s:smooth` (0–40 cross-channel early reflections), `Track.reverb:35@2s:smooth` (0–100 send), `Track.eq1:320,1.2,-2@2s:smooth` (three peaking EQ bands, 30–16000Hz, Q .3–12, ±12dB), resets, `Master.fade:4s:smooth`, `Master.tail:3s` on final section. Directives inherit across omitted sections; unknown directives are rejected, not silently ignored.
- Playback and offline rendering share stem gains, pan curves, EQ, M/S width, short spatial reflections, reverb and end fade. End fade now attenuates both **dry mix** and **reverb excitation** before convolution, while retaining decay of already-generated reverb into the post-roll. Offline renderer applies master trim; monitor volume is excluded. A/B bypass for pan, width, space, reverb, EQ and ending is **audition-only**, does not alter saved mix or WAV. It is not perceived-loudness matched.
- Structured editors: sections, pan, reverb, width, spatial reflections, ending treatments and now **Parametric EQ**; GET/PUT section target APIs, saved production blocks and text round-trip. EQ filters are three cascaded Web Audio peaking BiquadFilters after reconstruction of split L/R and before width; static scripted EQ by section is implemented, but dynamic threshold-following EQ, compression, sidechaining and advanced repair are **not**.
- In-app safe update/relaunch implemented: manual ↻ Git check (fetch does not overwrite tree), per-instance token + same-origin POST, refuse busy server/diverged branch, independent `pwsh` helper waits for old backend PID then uses existing `update-checkout.ps1` and reopens standard launcher. **First Windows end-to-end QA is pending**. Save unapplied browser edits before restart. Never silently kill active jobs, reset/stash conflicting files, or kill unrelated listeners.

### Accepted priorities for next thread (in order)

1. **Stabilization / QA first:** Run normal launcher on `main` and confirm frontend TypeScript build, backend import/tests and actual ↻ update/relaunch on Windows. Test safe update with latest available commit, dirty unrelated file, busy job refusal, and old-window/new-window behavior. Address errors before starting more DSP. Reverify EQ persistence plus audio preview/WAV parity and final 4s fade + 3s tail.
2. **Next DSP slice: section/phrase-aware compression + source-aware ducking**. Design a consistent live/offline graph; detector/threshold/ratio/attack/release/makeup, gain reduction metering; sidechain signal from vocals or selected stem to guitars/Other, with reversible intensity and independent range/section automation. Start conservatively: AI-generated music is often already compressed. Follow with **de-essing** using frequency-selective dynamics.
3. **First sound cleanup workbench:** detect and mark click/pop, clipping, harsh resonance, de-essing candidates, high-frequency fizz, mono/phase issues and separated-stem bleed; offer precise region looping → conservative suggested gain/EQ/fade repair → A/B → accept/revert. Add **time-range/phrase-level directives** because sections alone are too coarse for isolated defects. Preserve original stems and provenance.
4. **Next script features:** dynamic EQ, rhythmic/tempo-synchronized stereo delay, loudness-matched A/B, true/sample-peak/stereo-correlation/mono QA, versioned mixer renders with honest open-folder links and persisted master trim.
5. **Deferred UI pass:** right Tools sidebar has become text-heavy. User explicitly wants **compact, icon-first tools, informative state, and details in pop-out modals/inspectors**, retaining as much waveform/timeline width as possible. Follow shared TWS Design Principles; no blank outer margins or narrowed editor.
6. **Longer-term, still accepted:** full effects rack **and third-party plugin hosting**, native model generation/ACE-Step/YuE2 adapters, Second Take targeted revision/remix, local model workbench, standalone packaging, optional cloud handoff. Plugin format, licensing, sandbox/security, realtime/offline render determinism are open architecture choices. These are not replaced by the script-first priority.

**User product principle:** develop unique section-/stem-/phrase-scriptable operations that otherwise require extensive manual clip cutting and per-region effects in a DAW; retain non-destructive source, preview/export parity, local-first, compact efficient UI and future conventional effects/plugin extensibility. Band usage (*Infra Choir*) is a testing use case, not Song Harbor product branding.

### Immediate source map / instructions

- `app/frontend/src/SharedClockAudition.ts`, `SectionAutomation.ts`, `SectionEq.ts`, `StereoWidth.ts`, `SpatialReflection.ts` — DSP and shared-clock audition/offline bounce.
- `app/frontend/src/StemMixer.tsx`, `SectionsTool.tsx`, `SectionEqTool.tsx`, `UpdateControl.tsx` — orchestration/controls.
- `app/backend/section_production.py`, `section_import.py`, `server.py`, `app_update.py` — grammar, project persistence, API, update/restart.
- `scripts/update-checkout.ps1`, `start-song-harbor.ps1`, `relaunch-song-harbor.ps1`, `app/run.ps1` — Windows boot/update.
- `docs/remote-daw-waveform-restoration-discovery.md` — effect/cleanup priority detail; `docs/section-automation-p0-implementation.md` — historical slice/test notes; `docs/spatial-choreography-target-the-logo-and-the-maw.md` — artistic spatial targets; `docs/qa-full-spatial-the-logo-and-the-maw.txt` — full original test section sheet.

**Next-thread opening request:** “Continue Song Harbor on `main` from `refs/handoffs/currentHandoff.md`, START HERE section. Verify new in-app update/relaunch and EQ build/persistence, then implement conservative section-aware compression and vocal-keyed ducking with shared audition/WAV processing, tests and non-destructive structured scripting. Preserve existing spatial/ending work and compact-UI debt.”

---

## 2026-10-21 stereo channels drifting mid-song: replaced multi-stream transport
User verified previous cursor fix improved alignment, but left/right channels and stems audibly slipped apart halfway through playback. Fundamental architecture defect: independent media elements each have their own buffering/decoder clock, and prior per-stem playbackRate/drift-seek correction is unsafe for phase-coherent music.

**Committed new `app/frontend/src/SharedClockAudition.ts` and integration in `StemMixer.tsx`:** one Web Audio AudioContext, predecoded AudioBuffers for each selected stem or split mono channel, with each AudioBufferSourceNode scheduled at the same AudioContext timestamp and sample offset for play, seek and resume. Pause records the single clock's position. Playback cursor polls engine clock every 33ms, not median or first stream. Stem gain/mute/solo and master monitor gains through GainNodes; split mono left/right through StereoPannerNodes. Existing export path/source protection unchanged; split-to-stereo parent exclusivity remains. UI displays synchronized audio preparation progress and disables Play until **all** tracks decode successfully. Engine refuses mismatched durations (>150ms), uses explicit **768 MiB decoded audio budget** and no automatic fall back to desynchronized HTMLMediaElement playback; longer songs require later shared-clock chunked scheduler/AudioWorklet. Engine and nodes disposed on song or routing change; old multi-stream polling/timing code removed.

**This remains UNVERIFIED on Windows**; no npm build/real hearing test/CI check. QA must listen through the problem middle-song passage (especially split L/R), seek/pause/resume/loop, confirm no drift, and test mixer updates and track mode transitions. A 4-minute six-stereo-track song may require ~500MiB decoded RAM, so preload is intentional and can take some time. Bigger tracks beyond cap display explicit error; do not promise arbitrary song length. QA details: `docs/production-timeline-script-ux.md`.

## 2026-10-21 frozen playhead regression (blocks section alignment)
User QA: waveform cursor freezes even though audible stems continue playing. Root cause inspected in `StemMixer.tsx`: transport clock was always `players[0].currentTime`, so first stem underrun froze position and could force wrong drift corrections. Fixed to sample all media at 160ms cadence, select actively advancing ready/nonseeking streams and prefer audible ones, use median actual media time as displayed clock and correction target. Stalled first track never freezes playhead as long as any other audible stream advances. Poll cache clears on pause, resume, seek, loop and route rebuild; all-ended state still stops transport. Still six independent HTMLMediaElements: sample-accurate long-term engine remains necessary. Windows/CI tests unverified; acceptance checklist in `docs/production-timeline-script-ux.md`. QA should inspect song 2+ mins while tracking cursor, muted/soloed/split behavior and pause/resume/seek/loop transitions. If the cursor still freezes, inspect all streams' `currentTime`, `readyState`, `paused`, `seeking` in browser DevTools and consider Web Audio shared clock engine.

## 2026-10-21 QOL regression repair: Space, audio stutter, wasted margins
User QA: Space pressed with waveform/button focus activated last button instead of playback; prolonged stem playback often stuttered; the new tools sidebar existed *inside* the globally 1440px-capped page leaving large outer screen gutters and an unnecessarily skinny waveform. Changes committed to main:
- `StemMixer.tsx`: global keydown listener now capture-phase; Space calls play/pause even with focused controls/buttons/waveform (but not while typing or operating range/select/accessibility sliders); Left/Right jump 5s. Fixed pending playback async race via generation counter. On resume no unnecessary per-stem seek; audio preload auto.
- Transport correction reduced from >90ms hard seek every 120ms to gentle ±2.5% follower playback-rate correction when >120ms drift, with extremely limited hard resync for >1.5s drift once per 4s and only when ready, checking every 160ms. **This is a mitigation, not a sample-accurate shared-clock engine**; Windows audible QA still needed.
- `main.tsx`: mark active sessions `workspace--song-session`; `song-harbor.css`: remove global 1440px page cap in session and size timeline flexibly with bounded inspector and responsive gutters. Also remove 1450px width cap on song library inventory. Sidebar must consume unused viewport before compressing the main work area.
- Elevated cross-app doctrine to canonical `Three-Wheeled-Sloth-Studio/TWS-Design-Principles` in `apps/App-Design-Principles.md` (hard no-letterboxed-editor invariant and QA rejection gate) plus `apps/Studio-UI-Style-Guide.md` (screen utilization and 1366/1920px width checks). Future design agents should retrieve these canonical documents before doing desktop layout.
- QA plan: `docs/production-timeline-script-ux.md`. No verified Windows test/CI/build result; user should test full-window resizing, Space from toolbar and waveform focus, 2–3 minutes unbroken playback, repeated seeks/pause/loops. If stutters persist, prioritize an actual shared-clock/decoded-chunk audio engine rather than further patching multiple HTMLAudioElements.

## 2026-10-21 production timeline UX / section script
User requested keyboard Space play/pause and left/right 5-sec jumps, compact transport above section headers/waves, right-click rewind to start, tool sidebar for zoom/split/export/section script, header doubleclick opens corresponding text, and LOE for lyrics-aware alignment. Implemented in `StemMixer.tsx`: keyboard handler excludes editable/form/section-slider controls; play/pause, back5, forward5, stop+zero; rightclick back=>zero. Main workspace layout: transport -> section bar -> aligned waves -> stem mixer. Tools aside includes `SectionsTool.tsx`, zoom+pan, region loop, existing ChannelSplitter with open-folder, rendered mix download, DAW handoff. CSS responsive. `SectionEditor.tsx` now section rail with icon-only manual controls left; section doubleclick invokes script focus, persisted boundary callback invalidates text view; old import UI removed. `SectionsTool.tsx` loads on demand from saved GET /sections/export, applies via existing import endpoint, and preserves unsaved drafts when timeline saves change (stale prompt). Server `section_import.py` / `server.py` now round-trip *lyrics* inside each section as section_lyrics, preserving stable IDs on like-for-like script edits and maintaining lyrics when time boundaries move. Test `test_section_import.py` added lyrics retime roundtrip. Design + Windows acceptance checklist `docs/production-timeline-script-ux.md`. This is source-of-truth structured script UI, **not yet** insert/merge sections or intelligent lyric timestamping. Rough discovery: local stable-ts or WhisperX forced align known lyrics to separated vocal stem, 3–6 dev-days prototype and 1–2 weeks useful constrained implementation, with chorus/rap/singing caveats. Existing main branch changes are **unverified on Windows and not CI checked**.

## 2026-10-20 QA: legacy song duration and compact section toolbar
User could see/play song but untimed section Apply yielded `Song duration is required to place untimed sections`. Root cause: recovered legacy `song-harbor.json` and recovered backend job lacked source duration even though HTML media element playback knows duration. Committed `resolved_song_duration` in `app/backend/server.py`: reuse valid known duration or FFprobe existing original/stem WAV, persist value to project/job, and use for section import and section save. Added `test_duration_recovery.py`. Also fixed accidentally literal double-escaped newlines in old untimed section test fixtures. Compact progressive-disclosure UX now in `SectionEditor.tsx`: brief icon-forward Import, saved-tag edit, file open, collapsed manual section creation, collapsed detailed section list and contextual `?` listing supported types; removed verbose paragraphs and shortened status messages. Expand vocabulary and reusable contextual help later. Docs: `docs/timeline-navigation-section-import.md`. **No Windows/CI test execution verified**. After relaunch, test import untimed tags in existing recovered song and confirm sections render across waveform; note that actual FFprobe must be configured and working.

## Section import succeeds but markers invisible (2026-10-20 QA fix)
User reported Apply no longer errors, but imported sections do not appear on waveform graph. Root cause/design gap: `SectionEditor` owned sections independently while `StemWaveforms` had no section data and only rendered wave peaks. Fixed `StemMixer.tsx` to hold shared `timelineSections`, with `SectionEditor.onSectionsChange` feeding waveforms. Successful imports reset timeline to 1× and leftmost position for visibility. `StemWaveforms.tsx` now paints vertical section-start guides across parent AND L/R child rows; `SectionEditor` shows saved count and number in current viewport. Also made `SectionEditor` resist delayed `initialSections` prop updates overwriting successfully imported/edited local state (localRevision guard). CSS guides are noninteractive and audio is untouched. Commits through `8f0b9f950e6266f1bcfa285551a74ebbfa0aa497`. **Windows/TypeScript build unverified**. Smoke check: paste [Intro]/[Verse]/[Chorus]/[Outro], Apply, verify four blocks in section lane plus four vertical boundaries in stem waves, zoom/pan and drag shared boundaries; close/reopen confirms saved positions.

## Untimed section scaffolding and shared-boundary resizing (2026-10-20)
User QA: section file import exists but making users invent time ranges is tedious. Committed `section_import.py` enhancements: support bare `[Intro]`, `[Verse 1]`, `[Chorus]`, `[Outro]` (including typed spatial suggestions like `[Chorus Vocal1:Expansive-Left]`) without timecodes. For Replace, evenly distribute N audible sections across full actual track duration; for Append, distribute over remaining time after final existing section. Final untimed `[End]` is a terminator (not an artificial long section). Ordinary lyric lines between bracket tags are skipped; unrecognized bracket tags error. Mixed timed and untimed imports deliberately rejected rather than guessing. Existing explicitly timed import path preserved. `SectionEditor.tsx` now foregrounds untimed paste and returns a clear message: equal spacing is an estimate and user should visually align markers. Import response includes `auto_distributed` flag. Draggable/shared boundary now adjusts ending previous section AND starting next section in tandem (including keyboard nudge), allowing painless contiguous alignment without gaps. Source files unaffected; old sections retained on validation failure. New tests `test_section_import.py` cover equal spacing, final End, lyric lines, JSON, append and invalid mixed formats. Fixed timed-vs-untimed regex escaping in a follow-up commit. Documentation: `docs/timeline-navigation-section-import.md`. **No verified CI or Windows build/runtime QA; test on Predator with normal launcher.**

## Timeline navigation and section import QOL (2026-10-20)
User QA: waveform graph good, zoom dropdown works, adjacent slider and mouse wheel did not; no way to import/edit timed section files; width may be revisited when effects panel exists. Root cause: old slider was horizontal viewport pan, disabled at 1×, mislabeled contextually. Updated `StemMixer.tsx`: slider now actually zooms (1,2,4,8,16×), separate Pan slider appears at zoom >1, native non-passive mouse-wheel zoom anchored to waveform position; Shift+wheel pans; normal interactive controls and text editor scrolling remain unaltered, and waveform buttons accept wheel zoom. `SectionEditor.tsx` now supports paste/edit, file picker .txt/.json, edit saved tags, Replace/Append import. Added `app/backend/section_import.py` and atomic `POST /api/projects/{id}/sections/import`, `GET /api/projects/{id}/sections/export`. Accepts bracketed timed sections (including `[Chorus 0:45-1:15 Vocal1:Expansive-Left]`) and section JSON, rejects untimed headings or invalid overlapping ranges without saving anything; spatial cues retained as nonexecuting per-section proposals, also preserved when dragging a tagged section. Tests `test_section_import.py`; acceptance checklist `docs/timeline-navigation-section-import.md`. No new effects panel/full-width reshuffle (existing song workspace already occupies full grid). **Code committed but no verified Windows build/QA or test execution.**

## Integrated Timeline v1 code slice (2026-10-20, unverified on Windows)

Implemented in current main branch: `track_routing.py` persisted non-destructive channel children in per-song `song-harbor.json`; channel splitting now registers child media. Validated GET/PUT channel routing endpoints, protected derived mono streaming and cached child waveforms; a parent stereo track OR its two mono children are activated, never both. Rendered mix via FFmpeg selects same active sources, routing mono files to correct L/R sides, while retaining original parent stem gain/mute/solo. `StemMixer.tsx` uses an AudioContext media-element graph with hard L/R panning when split tracks active, shows selected source mode toggle, original and child waveforms, region-loop in/out controls, and shared timeline zoom 1× to 16×. Consolidated section marker lane and waveform rows in a compact production timeline panel using common viewStart/viewEnd; section drag timing respects zoom. `ChannelSplitter.tsx` now refreshes routing immediately after export. Source files and old exports preserved.

Regression source committed: `test_track_routing.py` (exclusive routing, persistence and no source mutation) plus optional real-FFmpeg `test_channel_roundtrip.py` (left/right fidelity); also existing waveform/section tests. **No verified CI or Windows build/test run**; ask user to relaunch and share failure output before saying accepted. `docs/integrated-production-timeline-v1.md` includes acceptance steps and known limitations.

**Critical caveat:** despite the AudioContext output routing, playback still has independent HTMLMediaElements and 120ms drift correction. It is not sample-accurate or gapless looping and not appropriate for precision null tests/A-B mastering. Also L/R channels share parent gain/mute/solo; independent per-child controls and pan/EQ/FX automation not yet implemented. Zoom enlarges 2048 cached bins rather than requesting true high-resolution new peaks. Old channel exports predating this slice need re-split to be registered. The next responsible engineering slice is shared-clock playback/offline parity, multi-resolution peaks and independent child effects rather than treating this first iteration as complete DAW functionality.

## October 20 waveform implementation and spatial DSL spike
Following the user's request to use today for work not requiring REAPER, added `waveform_peaks.py` (2048-bin cached min/max FFmpeg waveform overview and source signature invalidation), `GET /api/jobs/{ident}/waveform/{filename}`, and `StemWaveforms.tsx` integrated into `StemMixer` as aligned clickable waveforms and shared playback cursor. Backend tests: `test_waveform_peaks.py`. Also added **nonexecuting prototype** `production_cues.py` and `test_production_cues.py` compiling e.g. `[Chorus 1:15-1:45 Vocal1:Expansive-Left Drums:Narrow-Right Bass:Moderate]` to typed proposals; width and bias independent. None of these perform DSP or add L/R channel playback. **Windows build and automated tests not yet verified**. Do not represent overview as full zoomable waveform editor. Follow-up roadmap and research details: `docs/remote-daw-waveform-restoration-discovery.md`. Primary-source Suno terms restrict watermark/provenance alteration for concealment; implement track-level mixed-origin lineage rather than watermark evasion. Ardour demo periodically mutes after 10 minutes; non-demo sources/full binaries don't have that limitation; MSVC build unsupported. REAPER trial should wait until user wants to start it.

## DAW remote control, waveform and artifact repair discovery (2026-10-20)
User reprioritized immediate waveform display with integrated six-stem timeline, wants investigate full remote scripting before building DAW, deprioritize Audacity, explore low-profile audible AI artifact detection/repair, and spatial storytelling: narrow individual narrator, moderately wide other leads, very wide massed choir; room changes dynamically by section. Research and plan at `docs/remote-daw-waveform-restoration-discovery.md`. Candidate bridge spikes: Ardour OSC/Lua (GPL/license and paid prebuilt limitations) and REAPER ReaScript (60-day evaluation/paid afterwards); Waveform OSC/scripted control surfaces, MorningDAW MIDI Learn have less-proven general edit API. **Only docs committed, no implemented waveform or remote control.** Restore audible fidelity through reversible region-local cleanup, not AI-detector-evasion or provenance removal. Next code milestone waveform cache/zoom + shared-clock timeline + parent/child routing and loops; parallel bridge spike before reinventing DAW.

## Stereo production planning (2026-10-20)

User confirmed the current L/R channels have extremely high correlation; goal is **intelligent, dynamically changing stereo differentiation**, not merely channel extraction. User observed that channel-split exports are not reflected in the six-stem player. Root cause verified: current mixer hardcodes six original audio players, derived L/R files are export-only. Recorded engineering plan at `docs/stereo-production-effects-plan.md`: introduce persistent parent/child track routing, enable L/R children in playback/export **instead of** the parent (avoid double-summing), unify timeline/DSP clock, stereo analyzer, human/machine asymmetric semantic placement, section-driven pan/ambience automation, A/B preference capture. MorningDAW and Waveform are useful for manual pan and plugin automation, Audacity for cleanup; no verified general remote DAW control. This is **planning/documentation only**, not a completed player integration. Next code task: child-track routing + view + persistence + export and channel-reconstruction tests.

## MorningDAW and stereo-channel split utilities (2026-10-20)

User requested (1) MorningDAW support and (2) a utility to extract L/R tracks from existing stereo stems. Implemented MorningDAW as third optional DAW target with common Windows detection, explicit selection, vendor download and *manual* six-WAV import exchange (no unverified .mdproject automation). Implemented `channel_split.py`, POST `/api/projects/{ident}/channels/split`, and compact collapsed `ChannelSplitter.tsx` in the stem mixer. Selected two-channel stem files produce unique exports containing separate aligned left/right 32-bit float mono WAVs, manifest and README. Originals untouched; failed jobs clear staging. Regression tests in `test_channel_split.py`, updated `test_daw.py`. See `docs/morningdaw-channel-split.md`. **CI/local Windows build unverified**: ensure TypeScript build and backend tests before claiming acceptance. The utility does not perform further instrument separation or stereo widening. MorningDAW import remains manual.

## Working files Settings and compact component setup (2026-10-20)

User requested machine-specific selection of Song Harbor working-file directory, intending to use Google Drive local sync between Predator/Omen/Skynet; and removal of oversized one-component setup UI. Added `app/backend/workspace_settings.py` + guarded settings API, `app/run.ps1` respects configured location after relaunch, header gear opens compact `AppSettings.tsx` (Working files + collapsed Components), FFmpeg locate/install sections now collapsed, contextual FFmpeg recovery preserved. Tests in `app/backend/tests/test_workspace_settings.py`; guide `docs/working-files-settings.md`.

**Safety / honest limits:** Changing location **does not move existing files** or reconcile old and new libraries; stored per machine under runtime `config/settings.json`. Current SQLite WAL library lives inside the selected data folder and tracks absolute paths. Google Drive sync of a live SQLite DB is not safe for concurrent multi-machine use; sequential single-computer use only with sync completed, backup recommended. Different machine path layouts may require index rebuild/relink; ideal future design is local SQLite plus portable synced song manifests/media. Do not claim automatic seamless sync. Code committed to main, CI and Windows smoke verification still pending. No local user testing requested.

## Timeline-first section UX follow-up (2026-10-19)
User wants YouTube-style editing: visually align section blocks with the audio and stems; drag blocks to move, drag edges to stretch. Commit `76e728ab` upgrades `SectionEditor.tsx` from static blocks to pointer-draggable/resizable section blocks with playback cursor, adjacent-section constraints, and arrow-key nudging. See `docs/adaptive-production-workbench.md`. **This is an aligned annotation lane, not yet integrated multi-stem waveform visualization or snapping.** Next prioritize waveform rendering + timeline zoom/beat snapping, then synchronized per-stem pan/EQ, loudness-matched A/B and better/worse/reroll. No Predator/Omen QA performed and CI outcome not yet verified.

## Latest incremental implementation — manual song section markers (2026-10-19)

After acceptance of the Adaptive Production Workbench direction, the user additionally requested early YuE2/ACE-inspired timed section labeling; procedural core with optional LLM enrichment; and approved the pan/EQ/A-B next slice. Added `app/backend/sections.py` canonical validated time sections (kind, optional number, start/end, stable ID), `PUT /api/projects/{ident}/sections` to persist without rewriting media, `app/frontend/src/SectionEditor.tsx` mounted in StemMixer with Mark in / Mark out at playback cursor, time labels and timeline markers, and backend regression tests. References: `docs/adaptive-production-workbench.md`. **Status: source changes committed, automated CI and on-machine Windows QA not yet verified; do not claim marker editor accepted.** Known limitation: markers only, no signal processing or section-aware procedural effect engine. Next: build low-latency DSP/monitoring architecture and persistence for per-stem pan/EQ and level-matched A/B, Better/Worse/Reroll experiments; ensure preview/export parity; feed section context into procedural suggestions. First album tracks remain external-editor manual production; user currently on Predator and not testing.


## Planning update — Adaptive Production Workbench (2026-10-19)

User is currently on **Predator**, not doing live QA. Audacity Omen smoke remains pending; do not request Omen testing as a prerequisite to planning. User intends to finish the first one or two *Voices Below the Deck* tracks manually in Waveform/Audacity while using observations to drive **product-first Song Harbor development**. Approved direction documented at [docs/adaptive-production-workbench.md](../../docs/adaptive-production-workbench.md): non-destructive production graph, analysis with scoped evidence/expected value, fast matched-loudness A/B, Better/Worse/Reroll, locally inspectable preference learning, optional male/female voice and instrument subdivision. Album profile: organic/human bias left, mechanical/impersonal bias right, orchestra/environment wider and central anchors preserved, with deliberate motion. Added industrial sound design is later, not first-track release-blocking. No production implementation or on-machine tests were performed for this planning update. Avoid naming this slice M3 without reconciling existing roadmap's M3 First Surgery.


## NEXT THREAD — Song Harbor Audacity Handoff QA (2026-10-19)

**Start here. This section supersedes older historical "pending" statements below.**

**Product direction:** Song Harbor is a local-first standalone music workbench. Current accepted vertical slice: Library/song projects, six-stem separation and mixer, non-destructive export, and optional DAW handoff. **Audacity and Waveform Free remain supporting external editors, while priority gradually shifts toward building useful stem editing tools directly into Song Harbor.** Maintain common TWS-UI design standards (dense, icon-first, clear hover/help and recovery actions), original source/stem immutability, and zero-cost-first operation.

**Machines / current QA:** Omen laptop is the immediate test bench. User confirmed the new **single-server launcher works**, Waveform installer worked, and **Audacity4 automatic discovery now works** after executable-name and shortcut handling fixes. FFmpeg was already discovered on Omen, so the amber warning and guided FFmpeg-not-found workflow remains **untested** there. Predator and Skynet remain secondary test environments; don't assume Omen's paths/drives match other machines.

**Most recent code, ready for Omen test:** Audacity's DAW dialog **Prepare stems → Launch** now calls `POST /api/projects/{ident}/daw/launch` with the explicit prepared folder/target. The backend checks that the requested bundle belongs to the selected completed song and contains the expected manifest. For Audacity it calls `app/backend/audacity_handoff.py`, validates six numbered source-preserving WAV copies and zero-offset manifest entries, writes `Song Harbor - Import six stems.lof`, launches the discovered `Audacity4.exe` (or other verified Audacity executable) with that LOF as **one argument**, and starts a daemon attempt to foreground only windows owned by that actual Audacity executable, including an already-running instance. For Waveform, Launch still opens Waveform and **manual track import remains required**. No scripting pipe, keystroke automation, synthesized .aup3 projects, source file edits, or certainty about successful import.

**Implementation detail correction:** The final LOF contains `window` then six lines `file "01 - Vocals.wav" offset 0` through `file "06 - Other.wav" offset 0`, using **relative ASCII filenames** in the export folder (not the older absolute paths stated in the historical section below), to avoid Unicode Windows folder encoding problems. The export folder also holds `manifest.json`, instructions and the six untouched WAV copies.

**Verification completed:** Latest Linux backend CI, run [39161294330](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/runs/39161294330), **passed** including LOF order/content, missing/path-escape rejection, process argument and focus-request mocks, and API folder/target isolation. Latest Windows single-server smoke, run [39161294241](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/actions/runs/39161294241), **passed** including frontend compilation and Windows setup checks. CI validates the request/implementation, **not that Audacity4 accepts LOF** or that Windows permits foreground activation on Omen.

**Priority 0 next-thread Omen smoke:**
1. Pull latest clean checkout if needed and use `scripts/launch-song-harbor.bat`. Open any completed six-stem song; select Audacity (should already say Ready).
2. With Audacity **closed**, click **Prepare stems → Launch**; inspect whether Audacity opens **one project with exactly six synchronized tracks at 0:00**, and whether Audacity receives foreground focus. Note any unsupported-file dialog, empty project, duplicate windows, failed focus, or other behavior.
3. Repeat with **Audacity already open**; ensure it handles a fresh six-track import without destroying an existing session, and foreground focus selects the correct application.
4. If LOF isn't supported in Omen's Audacity4, **do not claim success** and don't add unsafe generic UI keystroke automation. Evaluate a verified Audacity4-supported import protocol; fall back cleanly to **Files** and six-wave manual import, with accurate UI message until a real automated method is proven.
5. If focus fails, capture whether Audacity opened/new vs reused process and whether window is visible; Windows `SetForegroundWindow` restrictions make focus best-effort. Address with supported OS behavior rather than stealing arbitrary application focus.

**Other tracked follow-ups:** make prepared-export state durable across dialog reopen (currently state lives inside the dialog); check Audacity import reliability and usability; consider target-aware Auto Import on Launch when supported; revisit source dedup and Library Remove regression on Predator if reappearing; FFmpeg dependency recovery needs no-FFmpeg smoke; future named versions/subcollections and in-product surgical waveform/stem editing. No new external DAW engine is an immediate priority.

**Key files:** `app/backend/audacity_handoff.py`, `app/backend/daw.py`, `app/backend/projects.py`, `app/backend/server.py`, `app/frontend/src/DawHandoff.tsx`, `app/backend/tests/test_audacity_handoff.py`, `app/backend/tests/test_daw.py`, `app/README.md`, `scripts/start-song-harbor.ps1`, `app/run.ps1`. GitHub repo: https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor.

---

## Accepted Baseline

Song Harbor is the TWS Studios working title. A standalone local-first product must support stem/section-level music editing and generation, swappable models, plugins/LoRA/LoKr, remix/cover, imported-track reconstruction, and future optional training/cloud execution. Reference system RTX 4070 12 GB VRAM / 96 GB RAM. Infra Choir is a consumer, not co-brand. Accepted facts are in `refs/planning/decisions.yaml`. **SH-DEC-009 accepts generation-first comprehensive release sequencing, while SH-DEC-010 makes a self-contained stem separator the first functional deliverable.** Full mixed-song reconstruction and guided remix follow, rather than gate, the initial standalone generation-first release.

## What Landed

Product vision, requirements, architecture direction, decisions, open questions, structured roadmap and detailed implementation roadmap with discovery spikes, experiment goals, stage gates, fallback paths and proposed release milestones. Agent Academy foundation files were partially copied previously. The roadmap now explicitly orders standalone generation-first release before reconstruction/remix.

## Current Evidence Or Gap

Laptop Predator setup (2026-10-17) reached **environment validated, inference not yet attempted**. GTX 1660 Ti 6 GB, RAM 15.843 GiB, Windows build 10.0.26100, driver 572.47; Python 3.11.2 isolated in `G:\Apps\SongHarbor\.venv`; torch/torchaudio 2.6.0+cu126, torchvision 0.21.0+cu126, onnxruntime-gpu 1.24.4, audio-separator 0.47.0. Torch CUDA matrix multiplication succeeded and `audio-separator --env_info` detected Torch CUDA, ONNX CUDA provider, and FFmpeg 4.2.3. Pip initially upgraded torch to CPU-only 2.14.1; compatible CUDA packages restored with --no-deps. Missing ONNX Runtime was corrected by installing onnxruntime-gpu. Default model directory is /tmp/audio-separator-models/ and needs explicit G: override. Final pip check was not supplied. No model download or stem separation performed.

The user is moving to the **primary desktop**. Its previously reported RTX 4070 12 GB and 96 GB RAM are pending direct verification. Three-machine benchmark process is captured in `refs/testing/stemSeparationBenchmark.md`. No product runtime exists; full Agent Academy initialized-mode validation still pending.

## Active Test Model

User selected **Demucs six-stem `htdemucs_6s.yaml` as the current benchmark baseline** after a successful 30-second desktop run (9.046711 s) and listening check. Vocals/percussion clean; some guitar-versus-Other bleed acceptable. Prioritize full-song test and sustained performance with this model. Four-stem Demucs and two-stem VR remain comparators. Not a final shipping decision; verify weights licensing and full track resources.

## M0 UI Implementation Checkpoint (2026-10-17)

Reviewed canonical `TWS-Design-Principles/apps/App-Design-Principles.md`, `apps/Studio-UI-Style-Guide.md`, `apps/Fullscreen-Workspace-Interaction-Standards.md` and shared `TWS-UI` API. Implemented initial local vertical slice under `app/`: FastAPI service using the validated virtualenv's `audio-separator.exe`, fixed six-stem Demucs, one-job queue, status/error/logs, cancellation, download and open-output-folder, plus React entry screen importing shared `@tws-ui/core/react` controls. `app/run.ps1` launches local service and dev UI. `.gitignore` excludes models, audio, venv, runtime data and build artifacts. Follow `app/README.md` for installation and acceptance. **Not yet smoke-tested end-to-end** on user's Windows workstation; do not check off the milestone until UI works on the actual machine. No packaged standalone binary yet. User's working `D:\Apps\SongHarbor` already contains models and venv: clone source to a subdirectory or integrate git carefully rather than overwriting existing local assets.

## Multi-machine Bootstrap (2026-10-17)

The previous primary development machine is confirmed as **PC Skynet** (RTX 4070 / 96 GB), and the third laptop is named **Laptop Omen** (hardware inventory pending). A reusable Windows setup script has been added at `scripts/bootstrap-windows.ps1`. It pins torch, torchvision, torchaudio to CUDA 12.6-compatible 2.6.0 builds and ONNX Runtime GPU to 1.24.4, uses an isolated user-chosen work drive, checks GPU/FFmpeg/Python/npm, installs `audio-separator[gpu]==0.47.0`, downloads `htdemucs_6s.yaml`, and installs/builds the M0 UI. Script committed but **not yet exercised on Laptop Omen**; run it and diagnose any machine-specific issues. Avoid assuming its drive mapping, driver, Python, or memory match either prior machine.

## Laptop Omen Launchers (2026-10-17)

Added `scripts/bootstrap-windows.bat` and `scripts/launch-song-harbor.bat`, default work root `C:\\Apps\\SongHarbor`, since Omen has no other work drive. Both launch PowerShell 7 via `pwsh.exe` using repository-relative .ps1 paths; bootstrap launcher preserves errors in the console, and either accepts a root override as argument. C: placement is a deliberate machine constraint, not a change to preferred storage topology for other machines. Neither launcher has been tested on Omen yet.

## Laptop Omen M0 Acceptance (2026-10-17)

User confirmed **“Launcher works. Splitter works.”** on Laptop Omen using the C:-based bootstrap and GUI. The limited milestone of a working entry UI plus end-to-end six-stem separation is **user accepted**. Do not imply installer packaging or exhaustive QA is complete. Remaining deferred checks include specific output validation, error/cancel behavior, exact Omen system inventory, performance and an independent frontend build/test run.

## Open Regression: possible 4:00 truncation (2026-10-17)

User reports the splitter appears to cut off at exactly four minutes on longer content. This is **open and unverified**. Reviewed upstream Demucs/audio-separator: no inherent four-minute input ceiling; chunking is optional and default off. Prior backend only required six files, so could report a false success when truncated. Added source/stem `ffprobe` duration guard (0.25 s tolerance), exposing measured lengths and an actionable error, plus duration-regression tests. A guard is **not the underlying fix**. Diagnose on Laptop Omen by probing imported source and all six produced stems and checking latest job logs. Do not claim full-length (>4 minute) separation as accepted until reproduced and corrected.

## M1 In-app Stem Mixer (2026-10-17)

User prioritizes removing Audacity from ordinary stem audition and recombination. Implemented `app/frontend/src/StemMixer.tsx` and mixer styling; wired into completed six-stem jobs. Playback, seek, per-stem gain/mute/solo/reset, exported WAV download and local file-folder integration. Server has inline stem streaming and an FFmpeg six-input mixdown endpoint using validated existing stem filenames, proper gain/solo/mute, 24-bit WAV with limiter, atomic output replacement, source-duration validation, and concurrency guard. Added `app/backend/tests/test_mix_validation.py`. **Not yet user-tested or build-verified on Laptop Omen**; current M1 checkpoint is code complete pending smoke test. Preview synchronization uses individual browser MediaElements with drift correction, which is not sample-accurate; mixdown renders synchronized input stems using FFmpeg.

## Portable Launcher Fix (2026-10-18)

Regression discovered on **Laptop Predator**, where checkout is `G:\\Apps\\Song-Harbor` and validated virtual environment is `G:\\Apps\\SongHarbor\\.venv`. Old `scripts/launch-song-harbor.bat` hard-coded Omen's `C:\\Apps\\SongHarbor` and failed. Added `scripts/start-song-harbor.ps1` with explicit override/environment/sibling venv discovery and conditional bootstrap; changed BATs to use it instead of hard-coded drive. Missing UI-only dependencies are installed without reinstalling CUDA PyTorch. `scripts/bootstrap-windows.bat` now does install-only. Docs updated. **Not yet verified in runtime on Predator**; user's next step is git pull and relaunch to confirm correct resolved root and UI operation.

## FFmpeg Guided Recovery (2026-10-18)

Predator reported a completed UI upload failing with `ffprobe is required... install FFmpeg on PATH`. User requires applications to offer discovery, native folder selection, explicitly selected install destinations, installation assistance, validation and persistence of machine-specific tool locations rather than generic dependency errors. Added `app/backend/dependencies.py` with saved-path/PATH/common-folder resolution, opt-in bounded machine app-folder search, Windows native folder picker, SHA-256 verified official Gyan essentials ZIP download to an explicitly chosen empty location, verified FFmpeg/FFprobe pair, machine-local config file, and async install status. Added FastAPI setup endpoints, a recovery UI, change-path action, configured FFmpeg use in separation and export, and removed mandatory FFmpeg PATH check from bootstrap. Added dependency tests and excluded local config/managed binaries in .gitignore. Added the behavior as cross-project Principle 19 in TWS-Design-Principles. **Not smoke-tested on Predator**; test with no ffprobe on PATH and ensure setup works before marking accepted. The currently implemented setup is FFmpeg-specific; other system prerequisites are still bootstrap-validated.

## Contextual Dependency Recovery UX (2026-10-18)

The user's product-taste correction: the first FFmpeg setup implementation incorrectly occupied large persistent workspace area at launch, even when the user was not using the feature. Updated the canonical `TWS-Design-Principles/apps/App-Design-Principles.md` with sections 19–20 and `apps/Studio-UI-Style-Guide.md`: quiet upper-right header dependency count, never a startup takeover for feature-scoped tools, compact just-in-time modal only when an affected action is requested, preserve pending input and action, then resume upon recovery. Song Harbor now uses a shared TWS Dialog, removes persistent FFmpeg setup/status panels, keeps Separate enabled until invoked, and retries separation or mix export after successful configuration. Server health distinguishes `separator_ready` from combined readiness. **Committed; UI behavior pending local verification on Laptop Predator.**

## Next Slice

1. **Primary desktop first:** inventory Python installations, GPU/driver, FFmpeg, physical RAM and available storage. Ask for output, then select an isolated environment location. Do not copy Predator paths.
2. Verify CUDA Torch in the desktop environment; avoid letting audio-separator pip dependencies silently replace the selected CUDA build. Check `pip check`.
3. Install audio-separator and onnxruntime-gpu as needed; verify `--env_info`, configure a known model directory, then select a legally reviewable model for a short audio smoke test.
4. Later resume Predator at model-dir CLI inspection and a 2-stem short test. Compare same fixture across environments and keep provenance/performance separate.

## Required Reads For Next Slice

- `refs/planning/implementationRoadmap.md`: M0 separator gate and subsequent generation sequence.
- `refs/planning/stemSeparationDiscovery.md`: candidates, licensing and benchmark criteria.
- `refs/product/requirements.md`: required track, section and local capability outcomes.
- `refs/planning/decisions.yaml`: accepted boundaries versus proposals.
- `refs/planning/openQuestions.yaml`: unresolved technical and release decisions.
- `refs/README.md` and `refs/templatePolicy.yaml`: harness bootstrap and validation requirements.

## Relevant Files

`refs/planning/roadmap.yaml`, `refs/planning/todos.yaml`, `refs/architecture/overview.md`, `refs/project.yaml`.

## Do Not Reopen

Song Harbor working title/repo, TWS Studios ownership, Infra Choir brand independence, local-first/standalone, future-not-MVP cloud/training policy, and generation-first release sequence (SH-DEC-009), with separator first (SH-DEC-010).

## Validation

Documentation-only updates were pushed. No executable product tests or initialized Agent Academy generator/index validation was run. Do not declare full harness compliance before those checks pass.


### 2026-10-17 cutoff diagnostic update
User ran ffprobe on Laptop Omen's most recent job, `Salt in the Circuit`: imported `Salt in the Circuit.wav` was **exactly 240.000000 s** and each of the six Demucs 6s outputs was **exactly 240.000000 s**. This rules out *post-import separation-only* truncation in this job, but does not determine whether the user selected a naturally 4:00 file or whether upload/import changed a longer original. The 0.25 s stem-to-imported-source guard is insufficient to detect pre-separation truncation. Next: compare external selected original file with imported job file (ffprobe duration, byte count, SHA256), and if original is longer, audit browser upload and import handling.


### Follow-up: suspected Audacity timeline artifact (2026-10-17)
User withdrew the four-minute cutoff report after realizing a 4:00 song was previously imported into Audacity and the next song likely shared that timeline. The inspected Song Harbor job had source and all six stems at exactly 240 seconds. **No Song Harbor truncation has been demonstrated.** Reclassify this as a probable Audacity session/timeline issue rather than a confirmed application regression. Keep the new source-to-stem duration validation as useful defensive QA; it does not compare against the user's external original.

## Predator launcher / TSX regression fix (2026-10-18)

User requested the launcher open the local UI in a **new browser window** rather than reusing a tab and reported Vite Babel parser error in `FfmpegSetup.tsx` line 122 caused by literal `\\n` characters inserted during a JSX edit. Fixed literal characters and an additional mismatched opening `<Panel>`/closing `</Dialog>` tag in `FfmpegSetup.tsx`. Modified `app/run.ps1` to start Edge or Chrome using `--new-window` (fallback to default browser URL opener if no supported executable found). Added GitHub Actions frontend type-check/build workflow. GitHub Actions run **39116679928** for corrected commit `7a3ad824` completed **successfully**, including `npm run build --prefix app/frontend`. Browser-new-window behavior still requires local Windows verification on Predator.

## Windows default-browser correction (2026-10-18)

User reported that the new-window launch forced Edge even though Chrome was Windows' default and prior browser. This was an assistant-introduced product regression caused by the prior `msedge.exe`-first executable scan. `app/run.ps1` now reads the user's Windows HTTP UserChoice association and resolves that ProgId's open command; uses a new-window switch for the *selected* supported browser (Chrome/Edge/Firefox/Brave/Vivaldi). When it cannot safely identify a supported executable, it opens via the default URL handler, prioritizing user's browser preference over forced new-window behavior. No alternate browser is selected. Commit `4515ad48` pending Windows smoke verification on Predator.

## DAW strategy / next feature recommendation (2026-10-18)

User confirms guided FFmpeg install works and resumes the original separation. Added compact installer progress: download percent from Content-Length if supplied, indeterminate track during checksum/extraction; committed, pending frontend CI and Predator smoke test. The user asks whether to develop a complete DAW or integrate an existing DAW. Recommendation: **do not build a new DAW or VST hosting engine** for Song Harbor. Keep six-stem audition, mute/solo/level adjustment, remix export in our app; use **external DAW handoff** for waveform editing, clip rearrangement, time-stretching, automation, effects, and mastering. Explore REAPER (native .RPP session generation if validated, paid discounted license; strong scripting) as primary deep-integration candidate; Waveform Free as zero-cost choice, Cakewalk Sonar free tier as Windows alternative; Ardour source available but official Windows binary generally paid/unrestricted. Next product increment: durable **Song Workbench** with reopenable sessions, audio/stem paths + hashes, non-destructive mix-state manifest; then **Export to DAW** action with portable 6-stem aligned WAV bundle, optional REAPER .RPP project after tested schema, allow selecting installed executable, no forced install or premium DAW lock-in. Explicitly not a VST plugin first: complex plugin formats, hosts, distribution and latency contracts are needless for handoff. User has not requested actual implementation of next milestone yet.

## M2 persistent songs / Waveform Free-first DAW handoff (2026-10-18)

User explicitly prioritized **Waveform Free** ahead of REAPER due to **zero current funding**. This is the target order for DAW integration. Implemented `app/backend/projects.py` and server routes to persist six-stem Song Harbor manifests, reopen completed/recovered jobs after backend restarts, save song name and per-stem mixer state, list recent projects, and copy six full-length unaltered WAVs to a portable Waveform exchange folder containing a track-order manifest and import guide. No fabricated Waveform native session file; import six files as separate tracks at t=0 via Ctrl-drag in Waveform. UI has compact Open saved song picker and Save song / Export to Waveform / Open export folder controls, preserving main workspace. Automated GitHub Actions Python syntax+project test workflow and frontend build both passed, but **local import into Waveform Free, mixer-setting restoration, and end-to-end Windows operation remain unverified**. REAPER `.RPP` handoff follows when practical; a full embedded DAW and DAW plugins are deferred.


## Library-first product correction & generic DAW setup (2026-10-18)

User confirmed **music Library as default landing, SQLite catalog, song as parent of sources/versions/artifacts, rename separate from filenames, virtual nested collections unrelated to disk paths, dense icon-first UI, contextual right-click help, and reuse of shared TWS-UI**. Canonical principles updated in `TWS-Design-Principles/apps/App-Design-Principles.md` sections 21–22 and Studio UI Style Guide. Created `docs/library-first-architecture.md` covering approved schema, collection and history model, metadata-only renaming, dedup and safe trash/migration strategy.

Implemented initial SQLite `app/backend/library.py`, transactionally creating an indexed catalog on the runtime drive, idempotently adopting existing complete six-stem jobs without touching original sources, and endpoints for listing, renaming and virtual collection membership. Song Harbor now launches to compact LibraryHome, using TWS-UI controls, and opens the existing Song Workspace for import/separation/mixing. Mixer adds monitoring-only master volume, separated from export/mix gain.

Previous **Export to Waveform → Not Found** was a dead-end UX. Replaced the mixer action with generic **Export to DAW** dialog, first Waveform Free target. Implemented `app/backend/daw.py` discovery, persisted selected executable, local native picker, target metadata and official vendor download URL, and selected vendor installer execution after Windows Authenticode verification. No automatic direct download due publisher account/installer distribution. Portable six-stem exchange does not require an installed DAW; launching Waveform does, with guided recovery. **REAPER adapter later** due zero project funding.

GitHub Actions frontend typecheck/build and Python backend suite have been green for committed changes. Local Predator Windows smoke test remains outstanding, especially native installer detection/signature and Waveform handoff. Named version branching, multiple-artifact management, soft deletion/trash and native .tracktionedit format are not yet implemented; document as later P2/P4. Avoid claiming the finished product exists merely because the Library scaffold is visible.

## Launch/Library/UX QA correction (2026-10-18)

Tester: startup error then 404 until refresh; wants double-click launcher to fast-forward pull automatically; Library must deduplicate identical sources into variant takes and allow reversible removal; opened song must not show import form; icons for stems and actions; Help must be in-app before public release; scalable fonts later. Added safe fast-forward developer auto-update (skips dirty/offline/detached; `-NoUpdate`), backend+Vite readiness gate before browser launch, quiet Library startup retry, SHA-256 source-based grouping with cached hashes (no file moves), soft remove/Undo/Removed Restore, expandable takes, session-only Song Workspace, monitoring/stem/control icons and contextual in-app Help. Tests for duplicate grouping, file preservation, removal and restore passed in GitHub Actions, as did frontend build. Cross-project Principles expanded sections 23–24.

Design limitation: exact byte-level hashes, so source files with different encoding but same music are not merged; no auto-merging based on title. Current Remove hides whole grouped song, not an individual edit/mix—separate artifact lifecycle remains upcoming. Waveform remains first DAW target; REAPER later. Attracktive from Tracktion is a free VST3 instrument sound player with 100 included sounds, optional expansions—sensible as external Waveform plugin later but not Song Harbor VST hosting. $10 Waveform Welcome Bundle contents not independently verified; skip purchase with zero project budget. User has not yet locally verified corrected launcher/readiness or new Library actions on Predator.

## Predator Library QA follow-up (2026-10-18)

Screenshot: Two identical-titled **Raise the Neon Black** rows; original source filename also same; no automatic grouping shown. Tester reports **Remove from Library** gave generic "Could not change Library status", collection context submenu too long, desire browser desktop right-click, unutilized space in mixer stem rows, undersized icons. Launch smooth, song import panel removed, contextual in-app Help accepted.

Corrections committed:
- Backend explicit `song_links` table allows **Combine as takes** even if two files differ in byte SHA-256 (which may be true for same named audio after metadata/export changes); no original media is touched. Automatic hash grouping remains strict. Library source filename hover includes a short SHA-256 prefix for diagnosis, not noisy inline copy.
- Revised Library remove/restore to update underlying SQLite IDs transactionally rather than finding and mutating groups through the list presentation. Endpoints now preserve all media and return HTTP details in UI if a failure recurs. Backend test expanded for non-identical file versions manually combined and recovered, and checks the original stored files.
- Collection menu is now a single **Add to collection…** command opening a compact searchable picker; supports growing collections without an enormous context menu.
- Desktop right-click on a song row opens item actions (Open, Add to collection, Combine as takes, Remove/Restore, Help), with Shift+F10/context-key alternative and existing ellipsis menu as mouse/touch fallback. This is browser-based, not an OS-native extension; upstream reusable TWS-UI component is still desirable.
- Stem channel CSS uses a small fixed icon cell and gives remaining width to the actual controls/sliders; action/transport icons enlarged. Song Library typography fixed to dense sans-serif and pencil button, including compatibility with already-installed TWS-UI library; shared `TWS-UI` EditableTitle updated to a pencil glyph too.
- Frontend and backend automated build/tests passed after changes. Real Predator acceptance test pending.

Caveat: do not claim exact duplicates exist merely based on filename. Exact SHA-256 is authoritative for byte-identical copies; manual grouping is a safe way to link genuinely related but nonidentical encodes. Current take grouping is metadata only; independent version editing, take deletion and full artifact lifecycle are future work.

## Launcher fixes after Predator port collision (2026-10-18)

User reports portable launcher never auto-pulled due detected dirty checkout and failed with backend `Errno 10048` at 127.0.0.1:8765 (old Song Harbor service still bound).

Fixed in source:
- New `scripts/update-checkout.ps1` attempts safe fetch + fast-forward on the current branch **even when local edits exist**, letting Git refuse only actual file conflicts. Never reset/clean/stash/force. Handles detached HEAD, offline or diverged branches gracefully. `start-song-harbor.ps1` invokes it; `-NoUpdate` bypasses.
- New `scripts/prepare-local-ports.ps1` checks owners of 8765 and 5173 before creating child processes; only confirmed Song Harbor processes whose commands contain the same repo path may be stopped. An existing runtime with active jobs is protected; older runtime without job-state endpoint requires explicit restart confirmation. Unknown apps are never terminated.
- `app/run.ps1` invokes safe port preflight before backend launch. Backend now exposes `GET /api/runtime/status` with active job status.
- Expanded Windows CI to parse new PowerShell scripts and test real Git fast-forward behavior with unrelated dirty and conflicting tracked files. Windows CI run 39134418037 passed both syntax and updater integration tests.

**Pending Predator smoke:** one-time manual git pull to obtain the updater, relaunch, accept prompt if an older verified Song Harbor backend cannot report job activity, confirm healthy API/UI and subsequent double-click updates. If Git still refuses due overlapping tracked changes, console should explain protected local checkout; inspect `git status --short` and resolve manually. This is developer checkout behavior, not public auto-update mechanism.

## Omen FFmpeg UX regression: disabled separation action (2026-10-18)

On Laptop Omen, tester selected Raise the Neon Black.wav in Library → Import while FFmpeg was missing. The **Separate stems** control was disabled (gray), so clicking it could not trigger the already-implemented guided FFmpeg setup. Root cause: frontend computed `canStart = file && health.separator_ready && ...`, contradicting the recoverable dependency flow.

Changed in `app/frontend/src/main.tsx`: separation action remains enabled when a file and backend health are present, even if `health.ffmpeg` or the separator capability is missing. The click checks FFmpeg first and opens the existing compact locate/search/install dialog while setting `pendingSeparation`. Successful FFmpeg configuration automatically resumes the requested separation if the separator engine is ready. A missing core separator engine now produces specific recovery guidance rather than blindly invoking the backend. The action is a 52px icon-first, accessible SVG separation control with tooltip; missing FFmpeg gets a subtle amber outline and small exclamation badge, without putting a large dependency banner in the workspace. During active upload/separation, the control is disabled normally.

**Local Omen acceptance:** update checkout and relaunch, select an audio file with FFmpeg not configured, see amber icon rather than gray disabled button, hover to see 'FFmpeg required', click to open installer, finish setup and confirm separation begins automatically without reselecting the recording. Confirm a machine already configured for FFmpeg sees an ordinary icon and no extra setup dialog. Frontend CI build was passing for the first icon change; final follow-up CI run needs confirmation and Windows local smoke remains pending.

## Single-process launch correction (2026-10-18)

User reported backend disappeared even after the launcher printed Vite ready, followed by repeated Vite proxy `ECONNREFUSED 127.0.0.1:8765`. User explicitly wanted a **safe launcher**, not more finicky two-server start/stop logic, and approved a build step.

Replaced normal launcher runtime: `app/run.ps1` always builds Vite frontend to `dist`, then starts **one** Python/FastAPI server on a dynamically assigned free localhost port; it polls both `GET /` (real compiled index) and `GET /api/health` from this same new instance before opening the user's Windows default browser. No `npm run dev`, no proxy, no fixed port, no `prepare-local-ports.ps1` in normal runtime. Other old instances remain untouched and cannot collide with the new port. Backend `server.py` serves compiled assets and SPA fallback and reads `SONG_HARBOR_PORT` at startup; local origin acceptance updated. The obsolete dual-process helper remains in repo but is not invoked. Source checkout launcher still optionally fast-forwards Git and uses the configurable runtime root.

Added Windows CI `single-server-smoke.yml` to build frontend and check one backend serves both UI and API. Verification pending CI completion and Omen local smoke. Key consequence: changing frontend code now requires relaunching/building (no hot reload). The portable single server model is closer to eventual standalone packaging.

## Audacity second DAW adapter (2026-10-18)

User approved dual Audacity/Waveform handoff, with gradual absorption of common stem editing tools into Song Harbor. Omen is the first discovery test: Audacity is already installed and must be found without reinstalling. Implemented adapter registry and `Audacity.exe` verification in `app/backend/daw.py`; tries previously stored executable, Windows registered uninstall locations and App Paths, common installation paths and PATH, and persists actual resolved location. Selection via `POST /api/daws/select`, discovery/browse/locate/launch under `/api/daws/{target_id}/*`. Existing Waveform routes remain for compatibility. UI makes select target, readiness state, Prepare, Files, Launch target-specific and clears prepared folder on switching target. `projects.export_daw` writes six original aligned WAVs into distinct Waveform/Audacity exchange directories with target-specific instructions, retaining `export_waveform` compatibility wrapper. Existing source/stem media never overwritten. Backend tests for discovery, settings, HTTP endpoints and Audacity exports passed in CI; frontend builds pending final run. User must verify actual Audacity detection and launch on Omen. Deferred: auto-import into Audacity, editing plug-in, native .aup3 generation, and remote installer automation.

## Omen Audacity not detected — discovery improvements (2026-10-18)

User reported existing Audacity installation on Omen (single local drive) not detected by DAW adapter. Expanded `app/backend/daw.py` to discover Audacity in custom Apps folders on every mounted drive, resolve matching Start Menu shortcut targets (only when fast checks miss), and added separately initiated bounded async **Search this PC** (max 14,000 directories/35s, skip junction/symlink and system/development caches). New `POST /api/daws/{target_id}/search` and `GET /api/daws/search/{search_id}` endpoints; DAW handoff polls status and persists verified executable location. `Browse` still fallback. Backend tests for custom and nested paths passed in CI; frontend build passed; not tested on Omen. If user reports failure again, ask for actual Audacity.exe install path rather than assuming standard Program Files or silently installing a duplicate.

## Audacity prepared-stem auto-import and foreground focus (2026-10-18)

User validated Audacity4 auto-discovery on Omen; now requested Launch to **import the six prepared stems into Audacity** and bring Audacity to foreground rather than leaving browser focused.

Changes:
- New `app/backend/audacity_handoff.py`: validates the prepared Audacity manifest has exactly six expected ordered WAVs, 0.0 start offsets, and paths under the prepared bundle. Generates `Song Harbor - Import six stems.lof` in that bundle, using Audacity's documented List-of-Files format: a new window plus six `file "<absolute path>" offset 0` lines. Does not touch original WAVs or enable Audacity scripting pipe.
- Launch invokes installed, validated Audacity executable with the LOF as a *single argument*, not six WAV arguments (which would open separate project windows in previous Audacity versions). Spawns a short-lived daemon thread to locate a visible Audacity window by its **owning process executable path** (not just title) and attempt Windows `ShowWindow(SW_RESTORE)` + `SetForegroundWindow`. Handles forwarding to an existing instance of Audacity, with best-effort focus under Windows foreground restrictions. No global keyboard automation.
- New `POST /api/projects/{ident}/daw/launch` validates that the export folder is a child of the expected project's `exports` directory and manifest ID/DAW target match. Waveform launch continues to start the editor without automatic track import. Frontend `DawHandoff` sends selected target and prepared folder to the new endpoint, preserving Prepare → Launch sequence.
- CI tests validate exact six-line LOF content and ordering, rejection of missing/traversal stems, no modifications to original audio, invoked executable argument, requested focus thread, and API rejects wrong project/DAW folder. Backend CI passed (run 39161094796). Frontend CI build passed (run 39161020389); Omen end-to-end not yet done.

**Important uncertainty:** Audacity's official LOF importer is documented for the 3.x application; documentation available for Audacity 4 does not establish that 4 supports LOF. The launch response carefully states *import requested* rather than claiming six tracks were verified imported. Omen is first real acceptance: relaunch Song Harbor, prepare Audacity stems, click Launch with Audacity4 installed (first when not running, then already open). Confirm one project containing exactly six aligned tracks, Audacity window focused. If Audacity4 rejects .lof or shows empty project, treat as unsupported importer rather than silently pretending success: next step evaluate Audacity4-compatible automation or user-consented UI import, not enabling insecure mod-script-pipe by default.
