# Song Harbor dev handoff: Q4 listening to contextual musical production
Date: 2026-11-11 | Branch: dev | Production stays untouched

## Resume here
The user confirmed clean build after the Q4 output capture changes. CrispASR CUDA126 and MOSS-Audio Q4 GGUF are installed and recognized through the in-app installer; one actual external WAV review completed. A rerun is now under way on the user's test workstation. **Its result is pending**; do not claim quality has passed or rerun it automatically. Q4 is experimental and currently external-WAV-only.

**New QA issue**: "Approve selected download to shared model drive" checkbox resets (probably component-local state on tool remount; inspect actual lifecycle). Installed artifacts should not continue requiring an installation approval control. Resolve by making installation an action-local confirmation, with no persistent approval checkbox, and collapse installed/setup controls by default. Approve-and-run Q4 test was already changed to a contextual confirmation after Test, replacing an effectively invisible checkbox. Verify this in live UI.

Last Q4 output issue: prior review began mid-word and contained contradictory descriptions of genre, lyrics, voice, tempo, and instrumentation. Root cause of the **missing beginning** was slicing last 5,000 bytes of a combined console log. Source now captures separate `logs/moss-q4-<run-id>.txt` per test, exposing output from its beginning, an incomplete-output error if >2 MiB, source WAV, and run ID. Contradictory model content **is not yet explained**. CLI process exit != valid musical analysis.

### Primary code and contracts
- `app/frontend/src/MossModelTool.tsx`: palette MOSS wrapper including legacy SGLang and Q4 experiment.
- `app/frontend/src/MossQ4Experiment.tsx`: Q4 UI, setup, audio question, approval, test and raw output. Needs substantial condensation.
- `app/backend/moss_q4_experiment.py`: CrispASR one-shot subprocess and per-run output. Inspect actual parsing, process lifecycle and diagnosis.
- `app/backend/moss_q4_installer.py`: opt-in verified pinned downloads on configured D: model root; keep existing checksums/artifacts.
- `app/backend/moss_runtime.py`: older unquantized SGLang backend, GPU guard, explicit unload. Q4 uses its own runtime; don't conflate statuses.
- `docs/shared-musical-understanding-v0.md`: authoritative versioned sidecar SMU schema and invalidation/approval rules.
- `docs/ace-accompaniment-integration-contract.md`: ACE range, proposal, generation, A/B, insertion and provenance contract.
- `docs/audio-aware-production-and-deshimmer-2026-11-10.md`: first audio-aware workflow outline and ACE/YuE direction.
- `docs/moss-q4-crispasr-experiment-2026-11-11.md`: test/installation history and current Q4 limitations.
- Canonical UI principles: TWS-Design-Principles / `apps/App-Design-Principles.md` and `apps/Studio-UI-Style-Guide.md`. Read actual documents before UI changes. Favor compact, understandable icon-first controls and clear blocking errors. No full-width low-value messages or invisible checkboxes.

## Priority 1: Finish evaluating Q4 review
Wait for user to share the rerun's actual output / diagnostics. Confirm one run's WAV identity, duration, run ID, runtime version and complete beginning, rather than making assumptions about how the model responded.
1. Split/model-parse CrispASR human-answer text from startup logs, tracing/debug, progress, timestamps, alternative captions, and anything else in raw output. Do not assume multiple paragraphs = one song. Preserve untouched raw output for audit.
2. Compare descriptions against the known audio and supplied lyrics/section labels. Specifically check hallucinated quotes, vocal gender, instruments, BPM, key/chords, genre and transition times. Mark grounded, uncertain, contradicted. Do not imply confidence from flowery prose.
3. Record measured latency, peak VRAM if available, and cleanup after the one-shot process. No inferred benchmark numbers.
4. Test one controlled, short 15-30s region with known arrangement changes, plus another style/clip if quality remains plausible. Show concise, time-located observations; the freeform essay belongs in collapsible Raw.
5. Decide go/no-go for Q4-as-a-listening-component before enabling production suggestions. If Q4 fails, retain deterministic audio/MIDI analyzers and consider alternative models without throwing away SMU.

Acceptance: review begins at first character, is tied to correct source and region, logs isolated, obvious unsupported claims flagged, and observed differences versus ground truth documented.

## Priority 2: Fix approval reset and clean UI to standards
Current MOSS popup duplicates title; Q4 section contains blue external links, installed download actions, full source paths, extraneous explanation, separate install approval, manual Use local files, Discover, Browse controls, WAV controls and prompt all at once. When installed, these dominate the listening task.
Proposed UX:
- Palette title: `Musical understanding` with compact engine status (Q4 Experimental, Installed/Ready/Analyzing/Failed). Hide legacy SGLang loader behind an advanced engine chooser while preserving recovery access.
- Primary compact row: Source [Current mix | Selected range | External WAV], range/section, Analyze button. Advanced collapsible: Model & runtime, Install/manage, diagnostics, custom prompt, raw output.
- Once the Q4 runtime/model are installed, show `Ready`, not disabled installation controls or an approval checkbox. Installation requires contextual permission only when a user actually clicks an Install/Download action; no checkbox to retain/reset.
- Analysis confirmation belongs at the action, never at a distant line in the layout. Avoid reapproving trusted installed model code unless checkpoint changes; distinguish download consent, executable consent and actual analysis approval.
- Results: brief findings and evidence per section, optional raw model prose; actionable controls only for separately verified proposals.
- Fix narrow-width layout, long paths, scroll containment, labels, field spacing, status and cancellation; no silent truncation. No decorative/technical explanations cluttering normal flow.
- Keep direct access to `<runtime>/logs/` from an error, clear `ERROR:` with consequence and resolution.
- Test reopen/tool switch/model installed/analysis running/cancel/error and both narrow and large windows. No disappearing controls.

Acceptance: a user with Q4 already installed can choose scope and Analyze in one compact surface without encountering installer controls or an unrelated checkbox.

## Priority 3: Read *active project* audio, not only external WAV
Current Q4 `start` accepts an arbitrary absolute external WAV path. This is an experimental fallback, not the integrated workflow.
- Default `Current mix` includes selected stems, current gain/pan/width, all approved replacements and effects, and section-script automation exactly as playback/export intends. Use existing shared rendering/mix source; never grab a stale exported file or source WAV that omits in-app production changes.
- `Selected range` uses current project section IDs, From/To inclusive, with existing timeline's exact sample boundaries; allow manual selection when available. For long tracks, chunk/cap analysis by supported model context, not silent truncation.
- Keep `External WAV` for differential QA.
- Backend creates immutable temporary analysis snapshots under an app-managed cache (not a user export), with audio hash, render/recipe/project revision, sample rate/channels, time span, source-stem identities and applied effects. Snapshot generation must not modify active tracks, alter volume/script state, or interrupt playback. Reuse valid hash-matched snapshots, dispose stale temporary assets safely.
- Route Q4 through a server-owned snapshot reference rather than arbitrary browser path for project sources. Enforce project/run concurrency, cancellation and GPU release.
- Verify against a rendered mix by null/spectral/time-alignment comparison; QA with a split stem, automation change, muted source and an accepted reinstrumentation.

Acceptance: changing a section directive or stem balance affects the next Current mix analysis; unmodified project and original files remain byte-identical.

## Priority 4: Enrich with authored and measured musical context
Use the existing SMU v0 schema instead of creating a second incompatible data model.

Inputs (each tagged as source, version, scope and trust):
- **Section text & lyrics**: persisted section names, start/end, script directives and authored lyrics; differentiate descriptive text from executable automation. Align lyrical passages only where actual timing supports it. Never invent sung words from text alone.
- **MIDI scoring**: reuse existing scored MIDI/piano roll/ABC where available, with note, track, instrument, meter/key/tempo metadata and confidence. If absent for an eligible stem/section, queue existing stem-to-MIDI transcription as a *separate explicit bounded analysis stage*, creating editable candidate scoring rather than overwriting stems. Polyphony/percussion transcription can be unreliable; mark uncertainty and allow corrections.
- **Author intent**: project- and section-level desired mood, genre, focal instruments, vocals-to-protect, dramatic arc, constraints, negative directions, production target, what to preserve. User-authored intent is authoritative; derived guesses are not.
- **Measured DSP**: audio timing, spectral balance, dynamics, spatial metrics, transients, rhythmic events/tempo, candidate harmonic features (only when method valid). Use these to corroborate, not to rubber-stamp, Q4 prose.
- **Q4 observations**: time-specific, source-hash-tied candidates with evidence, model/version/profile, question and confidence/uncertainty. Compare against authored intent; highlight discrepancies with evidence.

Do not trigger full re-transcription on every analysis: per-stem hash/section changes and provenance determine reuse, invalidation, and which scoring is missing. Provide an opt-in action `Generate missing scoring`, meaningful status/progress and candidate review. Keep heavy tasks serialized and within the local RTX4070 budget.

Acceptance: resulting SMU sidecar clearly distinguishes heard, measured, scored and intended, and preserves user corrections through reruns.

## Priority 5: Turn analysis into reviewable production proposals
Use two distinct proposal types, not freeform instructions directly injected into the project.

A. **Production adjustment**:
- Structured recommendations for sections/stems (gain, pan/width, reverb, delay, balancing, cleanup or other *currently supported* section-script directives). Include intended outcome, evidence, estimated sonic tradeoffs, and exact target section IDs.
- Produce a syntactically validated **script diff/patch** using Song Harbor's current actual directive grammar. Do not resurrect obsolete `.original` directives or unsupported EQ instructions. Inspect actual parser and allowed effects before proposing.
- Preview proposal and temporary A/B where feasible; apply only selected changes on Accept, preserving original script as an undoable revision. No silent rewrites or automatic optimize.

B. **Accompaniment proposal**:
- Translate evidence + author intent + scored notes into a role/section-specific counterpoint, drum texture, orchestration or bridge proposal, including instrument role, rhythmic/harmonic boundaries and where to avoid masking vocals.
- Route to capability-verified **ACE** or **YuE** adapter (ACE for local add/repaint/Lego if verified; YuE for scoring/remix/structure depending on its current supported pipeline). Do not assume YuE2 is already integrated; it has previously been deferred pending the next track.
- Reuse existing ACE candidate lifecycle for generation, non-destructive preview, shared-clock A/B and explicit Accept/Insert. Generated section ranges must preserve inclusive From/To and context timing. Rejected and unaccepted audio never change the mix.
- An approved insertion gets a new stem/clip aligned to the exact target, stable alias, candidate provenance and section-specific muting/layering as appropriate, with reversible history.
- Ensure engine is unloaded/released when unused, avoid simultaneous heavy GPU jobs and protect active project/render.
- Clearly separate **Approve proposal** from **Generate audio** and **Accept generated audio**; these are different irreversible/expensive boundaries.

Acceptance: at least one validated section-script suggestion and one accompaniment plan can be reviewed and accepted without touching original assets or losing session history. Only claim generated accompaniment success after an actual model candidate is produced and auditioned.

## Suggested increments and gates
1. **Slice A**: review pending Q4 result, fix per-run output interpretation, eliminate installer consent reset and make installed-state UI compact. QA before expanding functionality.
2. **Slice B**: active mix snapshot + selected section support, no mutations, external WAV fallback.
3. **Slice C**: SMU v0 context aggregation (lyrics/sections + authored intent + existing MIDI + measured metrics), then opt-in missing-MIDI scoring.
4. **Slice D**: read-only structured findings and validated production-script diffs, explicit Accept/Undo.
5. **Slice E**: ACE/YuE capability-aware accompaniment plan, candidate generation + A/B + explicit insert.

## Non-negotiables
- Dev only until actual Windows build and end-to-end QA. Active song and production main unchanged.
- No silent network downloads, inference, GPU concurrency, section script edits, stem replacements or new inserts.
- Every change easy to undo; distinguish raw evidence, analysis suggestions, preview, candidate and acceptance.
- GPU/resource lifecycle with truthful busy, Cancel/Unload and errors. Never claim weights freed without checking actual worker termination.
- Keep implementation and handoff in repository; no downloadable document needed.
- Latest raw Q4 rerun result is *not yet available* in this handoff. Continue from it rather than inventing a quality verdict.


## 2026-11-11 dev Slice A implementation (Windows QA pending)

Source commits: `dbec7b5`, `d1e0f39`, `23d13e7`, `563b4ea`, `e5ff6ed`.

- Reviewed uploaded `moss-q4-experiment.log` / per-run Q4 text: both contain nine independently processed audio slices, full final concatenated prose, and startup/tracing logs. Source duration reported 237.6s. Detected internally inconsistent descriptions and invented-sounding lyrics; **Q4 musical quality has not passed**. No actual source WAV or synchronized lyrics were available in this review for independent listening.
- Backend `_review_output` separates post-`crispasr: transcribed ...` human text from the combined diagnostics, preserves the raw per-run output unchanged, records reported duration/slice count, labels model claims unvalidated/unaligned and flags repeated chord sequences and estimated tempo. It **does not** claim to reconstruct slice timestamps or align the captions. If the final delimiter is absent, final answer is intentionally empty with a warning rather than passing diagnostics as prose.
- UI now uses the structured review and keeps raw output behind details. Installed-state setup is hidden by default; an action-local confirmation replaces the download approval checkbox. The scope remains **external WAV only**, clearly labeled. No automatic inference, project asset edit, or network download was added.
- Added offline regression test `app/backend/tests/test_moss_q4_review.py` (not executed by connector). **TypeScript build, Python tests, and Windows live QA have not been run since these commits.** The user's prior clean build predates this change.
- Next QA: refresh `dev`, check `tsc --noEmit`/Vite build and Python test, then inspect installed Q4 panel. Confirm no checkbox or installer actions on default view, advanced installation confirm, source/run identity, concise review, expandable raw diagnostics, cancellation, and missing-delimiter behavior. Rerun only if user deliberately initiates another test. The first-pass result still cannot justify enabling production suggestions.
- Following accepted QA, proceed to Slice B active-project snapshot and SMU context pipeline.


## 2026-11-11 Slice A Windows QA and repeat-run result

User QA: updated dev build clean; Q4 displays Ready; old download approval checkbox gone. These checks pass. Advanced UI layout, cancel, failure, and installation confirmation still lack explicit interactive QA.

Latest complete run: `moss-q4-74682cdddf11450b9debd4097520b7a7.txt`, CrispASR v0.8.53, RTX 4070, 237.6 s, nine reported slices, 44.69 s CLI-reported transcription time (not a separately measured whole-process benchmark). Compared the model-answer portion after the final `crispasr: transcribed` marker with previous `moss-q4-c952750b95c341f3b5a3bfbd3ea5305f.txt`; **exact match**. Repeated C/F chord looping, incompatible BPM/genre/instrument/voice claims remain. Output capture and UI were improved, not model quality.

Gate: Q4 is a usable experimental CLI listener, **not approved as a grounded musical-analysis source or automatic script/accompaniment adviser**. Preserve raw/provenance; no forced re-run. Next slice may advance independent active-mix snapshots and SMU context, but Q4 observations remain unvalidated and must not trigger mutations. A separate short, ground-truth instrument-change clip is still needed to decide whether the Q4 backend has any reliable local listening utility.


## 2026-11-11 Slice B: active-project mix snapshot (committed, Windows QA pending)

Implementation on dev:
- `SharedClockAudition.renderWav24()` is reused **directly** from the live StemMixer. No pre-existing export file is read, no Download action runs, and no playback stop is requested. The mixer guards unsaved section previews, unloaded repairs, not-ready audio, and simultaneous mix exports.
- The Q4 palette now offers `Current mix`, `Selected section` (inclusive From/To), and `External WAV (QA)`. For mix/section, the user explicitly approves Q4, then Song Harbor offline-renders its current playback/export graph into a temporary Blob, computes SHA-256, and uploads it through `POST /api/settings/models/q4/snapshot`.
- Backend `moss_q4_snapshots.py` stores an immutable validated stereo 24-bit analysis WAV and JSON provenance under `<runtime>/cache/moss-q4-snapshots`; the complete mix checksum is checked against the client hash, the selected inclusive range is extracted at PCM sample boundaries without changing the underlying song, and the selected WAV gets its own SHA-256. Per-snapshot source includes project/job ID, rendered mix SHA-256 (currently reused as render recipe fingerprint), section IDs, bounds, rate, channels, bytes. No assertion of an authoritative saved project revision is made yet.
- `POST /api/settings/models/q4/snapshot/analyze` accepts a server-generated snapshot ID only; it resolves/verifies the cached WAV and passes the internal path to the existing explicitly approved one-shot Q4 runner. Existing local-origin, busy/GPU guards, cancel, watchdog and raw per-run logs remain intact. Pollable Q4 status carries the snapshot identity.
- Full offline WAV uploads are bounded to 600 MiB and actual analysis WAVs to 200 MiB; a whole mix beyond the latter must use a shorter section selection. Old immutable snapshots are retained for seven days, then removed on subsequent snapshot creation. No silent network/model download, auto-inference, project mutation, script edit, or insertion was added.
- Offline tests added in `app/backend/tests/test_moss_q4_snapshots.py` (selected sample frame count, unchanged source bytes, invalid snapshot IDs and hash corruption). Tests are committed but **not executed** in this environment.

**Important QA gates** (current code is not yet build- or live-verified):
1. Update/relaunch `dev`; run frontend TypeScript/Vite build and `python -m unittest app/backend/tests/test_moss_q4_snapshots.py app/backend/tests/test_moss_q4_review.py` from the repository with the appropriate backend Python available.
2. Choose MOSS > Q4 > `Current mix`, approve Analyze. Verify separate cached WAV and JSON, project ID and run ID, metadata SHA-256 and full audio duration; verify source files unchanged and music playback position unaffected.
3. Change a saved section directive, rerun a separate approved analysis, verify new mix SHA-256. Test split L/R stems, muted source, accepted reinstrumentation and reverb/tail parity against normal export. Also test source mix clipping/headroom failure.
4. Choose `Selected section`, From and To inclusive, verify sample-accurate WAV length, metadata section IDs and bounded model input; test single-section selection, reversed/empty selection and a late outro. Q4 may still generate multiple internal slices on long ranges.
5. Cancel Q4, reopen the palette, inspect retained snapshot/run identity; confirm old external-WAV QA still works, failures do not modify active project, and no cached audio is represented as verified musical analysis.
6. Compare rendered offline WAV with exported saved mix using null/spectral/time alignment when available. This comparison has **not** been performed. Rendering itself updates in-memory analysis metrics but does not intentionally modify audio stems, automation or playback transport.
7. Next follow-up: capture explicit source-stem IDs and authoritative saved project/recipe revisions in the metadata once the existing project revision contract is identified; current source hash provides real rendered-audio invalidation, not the full semantic dependency graph. Move to Slice C SMU aggregation only after Windows QA.

**Q4 trust gate remains unchanged:** repeated 237.6-second freeform responses were internally inconsistent. No automatic recommendations or accepts are authorized.


### Additional Slice B implementation notes
- Follow-up commit sequence through `a39c6e6` adds active working-stem provenance: track ID, working filename, displayed name, gain percentage, mute and solo values. The cache does not yet record a complete effect-by-effect recipe or canonical project revision. The actual rendered mix PCM and full-mix SHA-256 are authoritative for listening.
- Section scope now supports inclusive **From/To** selection instead of a single-section picker. The backend hashes the uploaded full mix, slices selected PCM in bounded chunks, hashes the resulting Q4 input WAV, and retains both scope and source identities. The full upload has a 600 MiB transfer guard while the final Q4 input has the existing 200 MiB bound.
- UI changes and backend tests remain unverified on the user's Windows machine after these commits. Do not assert build success based on earlier Slice A QA. Automated CLI test execution is not available through the repository connector.
- Remaining before declaring full Slice B acceptance: end-to-end validation of current mix vs export with effects, safe section playback continuity, full source identity/effect recipe revision, cache reuse across matching renders, and stale asset eviction under repeated sessions. The current seven-day cache cleanup runs when creating a new snapshot.


### 2026-11-11 live QA: single Verse 1 selected-range inference
User ran the new active-project selected-range path on **Verse 1** and received a full Q4 response. This is evidence that a selected section can reach the model and produce output, but independent snapshot checksums, exact sample count, mix/export parity, and nonmutation checks were not supplied and are not marked passed.

The answer consisted of two consecutive full-song-style passages, both describing slow introspective indie rock at **111 BPM**, female breathy lead, clean electric guitar arpeggios, bass/drums and synth pad. It proposed **A minor** with Am/F/G/C/D/Em chords and quoted lines including `I saw neon on the water / Like a bruise that would not fade` and `Saw the longshore saints keep working / For a half-dead promised wage`. None of these claims are independently verified here against source stems, authoritative lyrics or measured beat/chord estimates. The model incorrectly extrapolated verse-chorus/intro/bridge structure from a Verse 1-only clip. The repeated descriptions likely reflect the model's independent slice processing but the exact slice count and timing were not supplied for this run.

Priorities after this QA:
1. Preserve and display distinct Q4 audio slice text with bounded provenance where the CLI can provide it; never concatenate as one track-level claim or fabricate per-slice timestamps.
2. Reduce prompt scope for short clips to **only what is audible in this excerpt**, prohibit guesses about unseen intro, bridge and chorus, distinguish quoted/transcribed lyrics from provided authored lyrics.
3. Compare output with persisted section text/lyrics, current track identities, optional scored MIDI, and deterministic DSP; tag heard/derived/intended/unverified separately using SMU v0.
4. Continue Slice B parity/source checks before declaring active mix integration fully validated.


### 2026-11-11 human verification of Verse 1 observations
User ground-truth notes for the track:
- Female lead vocal: **confirmed accurate**, especially Verse 1.
- Atmosphere/arrangement: **confirmed** largely atmospheric, sparse and restrained; drums become aggressive at some points elsewhere.
- MOSS's 111 BPM: **not verified**. User states the piece has several tempo changes. Measure local tempo and build a section/time-positioned tempo map rather than asserting one song-wide BPM. Guard against half-time/double-time interpretations; record confidence and ambiguous pulse.
- A minor and specific chords: **plausible but unverified**; defer to MIDI/harmonic measurement, including confidence and polyphonic limitations.
- Clean electric guitar and synth: **questionable**. Very little on the recording is clean apart from vocals. Prefer source-neutral sound-texture observations until stem identity and instrumentation are verified; a processed texture resembling guitar is not proof of clean guitar.
- Quoted lyrics: **unverified** until compared with authored section lyrics.

Use these as human-authored validation annotations in the future SMU observation/correction layer. Preserve original model observations and record confirmations/uncertainty independently; do not rewrite MOSS text or mark all inferred details as confirmed. No new inference or automatic project modifications authorized by this feedback.


## 2026-11-11 approved Slice C direction: multi-tool composition intelligence

User explicitly approves the four next analysis workstreams:
1. **Tempo map**: strong approval. Build a time-positioned, section-aware musical pulse/tempo map supporting multiple real tempo changes, uncertain segments, meter changes where corroborated, and half-/double-time alternatives. Do not force one global BPM. Keep measured onset/pulse evidence, authored tempo information, existing MIDI timings and candidate revisions distinct. The editable map should be a reusable composition asset for arranging, scoring, accompaniment alignment, beat-aware edits and playback/render workflows, not just a diagnostic output.
2. **Section and lyrics context**: approved. Use canonical section IDs/boundaries, author's section text and lyrics, separate expressive intention from executable production directives, and preserve source/provenance.
3. **Stem-aware identification**: approved. Cross-check listening claims against actual existing stems and working aliases/routing. Model-observed sonic texture is not a verified instrument identity. Allow overlap, bleed, layered sounds and uncertainty.
4. **Harmonic analysis**: approved. Prefer existing scored MIDI as evidence, then supported signal analysis and candidate score extraction where useful; do not auto-overwrite a composition asset with machine guesses.

**Architectural principle, explicitly approved by user**: Song Harbor is a complete composition toolkit that combines multiple tools, sometimes with overlapping capabilities. Avoid a "one magical model/tool" strategy or architectural coupling to MOSS. Each provider/analyzer contributes separately versioned observations, measurements, authored data, scored data or candidate interpretations with capability, scope, evidence, uncertainty and dependency tracking through SMU v0 / the evolving composition graph. Contradictions are useful review signals; no forced consensus, auto-accept, or production mutation. Allow corroboration and human correction without erasing alternate evidence.

Suggested implementation sequence after Slice B QA:
- Define a provider-neutral, versioned tempo-map/beat-grid candidate schema and edit/accept/invalidate rules, aligned with canonical section timeline and sample positions.
- Reuse deterministic DSP and existing MIDI/transcription components for local tempo/beat/harmonic estimates; layer MOSS observations as optional independent hints, never the source of truth.
- Aggregate section lyrics/intention and working stems by source IDs and revisions; show corroboration/conflicts in compact review UI.
- Add editable candidate scoring and multi-provider reconciliation, with explicit approval before accepting map/score changes or generating accompaniment.
- Validate measured tempo changes, mixed meter/halftime cases, variable-tempo song, percussion-free passage, sparse atmospheric passage and a controlled known click/tempo-transition fixture.

Approval covers the design and priorities, not unattended Q4 inference or automatic mutation of the active song.


## 2026-11-11 Slice C1: provider-neutral editable tempo-map asset (dev committed; Windows QA pending)

Delivered in `app/backend/tempo_maps.py`:
- Persisted, versioned JSON tempo-map composition asset `<project job>/generated/tempo-map.json` with canonical **48 kHz sample positions**, stable anchor/observation IDs, duration bounds, multiple anchors, step and linear BPM transitions, per-anchor meter and optional canonical section reference.
- Distinguishes **accepted tempo anchors** from **unverified provider observations**; includes method, source hash/revision, provider, BPM candidate and half/double-time alternatives, uncertainty state and optional confidence. Empty maps answer `unknown`, never a fabricated default BPM. `bpm_at(sample)` provides read-only interpolation.
- Validation, revision guards, atomic write, concurrency-safe API transactions, and explicit human edits. No playback-speed adjustment, time-stretch, auto-quantize, MIDI rewrite, or Q4 inference.
- Backend endpoints: `GET/POST/PATCH /api/projects/{ident}/tempo-map`; POST initializes an empty map, PATCH saves revised anchors or observations with base revision and asset ID. All write endpoints enforce local origin, project existence and optimistic revision checks under server lock.
- `TempoMapTool.tsx` and `WorkbenchTools.tsx`: independent Tempo map palette item, compact editing of tempo anchors by time/BPM/meter/step-versus-ramp and optional existing section ID; explicit Save/Discard/Reload; read-only candidate inspector. Current map is explicitly labelled *composition timing asset*, not connected to audio clock, MIDI, or rendering yet.
- Offline regression coverage in `test_tempo_maps.py`: unmeasured starts unknown, real tempo changes and ramps, unverified candidates not auto-promoted, rejected duplicate anchors, stale revisions and round-trip persistence. Tests were committed but not run through the connector; **Windows build and app QA still required**.

Next increments, after C1 build acceptance:
1. Deterministic locally measured onset/pulse candidate analysis with **windowed tempo** and half/double-time ambiguity, capable of sparse and changing-tempo passages, explicit non-detection instead of forced guesses; add timed events and provenance to observation evidence.
2. Bring in existing MIDI note onset candidates only where note/beat inference is justified (drums vs melody, subdivisions, ties, expressive timing). Preserve user anchor corrections.
3. Align canonical authored section text and lyrics and actual stem identities with observations in SMU; cross-check MOSS separately.
4. Make explicitly accepted tempo maps available to piano roll, ACE/YuE accompaniment constraints and section-aware timing *without* automatically stretching playback or re-quantizing existing notes.
5. Prove parity and unchanged project assets under split stems, tempo-change fixture, meter changes, sparse/no-percussion material and rejected/stale edits.

**Limitations to retain visibly:** no automatic BPM estimator, provider adapter or playback timing integration is completed by C1. Human-entered 111 BPM must not be mistaken for the track's verified meter/tempo.


## 2026-11-12 Slice C2: deterministic windowed tempo measurement (dev, QA pending)

User confirmed the C1 Tempo map tool opens after previous TypeScript fix and requested adding automated measurement.

Implementation:
- `app/backend/tempo_measure.py`: local CPU-only spectral onset novelty over the actual 24-bit Song Harbor saved-mix render. Decodes stereo PCM in bounded chunks, computes positive log-spectral flux (2048 FFT / 512 hop), estimates onset periodicity via autocorrelation in overlapping **12-second windows, 6-second step**. Candidate search is 50-210 BPM, with musically relevant half/double-rate and near-ranked alternatives (bounded to 20-320). Each result carries its absolute project-clock sample range, method `spectral-onset-autocorr-v1`, explanation of non-detection (e.g. low-onset activity), and explicitly `unverified` state with null calibrated confidence. This is an onset pulse *heuristic*, not proof of a song's BPM; unpitched ambient/noisy passages may be uncertain or misleading.
- `POST /api/projects/{ident}/tempo-map/measure`: read-only tempo analysis from the existing **verified Q4 offline-mix snapshot** (Q4 inference is NOT invoked). Project/snapshot identity verified, onset windows constrained to the persisted tempo-map duration. No modifications to stems, project JSON, piano roll or accepted anchors.
- `TempoMapTool.tsx` now includes **Measure tempo** for current mix or a chosen existing section. It explicitly renders current saved mix and creates a SHA-256-verified audio snapshot using the same render path as Q4. Shows active phase/working spinner; displays overlap-window BPM estimates, alternatives, and non-detections. `Stage anchor` drafts one measured tempo as an author-reviewable **accepted-candidate** anchor; Save map is a separate action. `Save evidence` persists the candidate results as **unverified observations** without promoting anchors, preserves unrelated historical evidence and prevents dropping unsaved anchor edits. Discard erases unsaved measurement results.
- Backend synthetic fixture tests `test_tempo_measure.py`: silence must remain unknown, known 96->144 BPM click transition must yield local candidates (half/double ambiguous accepted), and selected-section sample offsets preserve absolute time. These tests were committed but not executed by connector.
- No dependency added beyond existing NumPy. No model loads, background analysis, automatic Q4 processing or quantization.
- **Windows QA required**: ensure frontend build and Python import clean; use `Tempo map > Create map > Measure tempo` on a short section; observe candidate windows, show alternate rates, Stage candidate, Save tempo map, reload. Check `Save evidence` separately, no automatic tempo changes, and sparse/quiet passage reports no reliable pulse rather than inventing BPM. Check server responsiveness and run synthetic tests. Compare a known tempo-change track, inspect loud/aggressive drum section vs restrained Verse 1.
- Known limitations: window-level estimates may smear short tempo transitions, prefer a steady rhythmic section; no bar/downbeat, beat-by-beat grid, meter measurement, MIDI-derived pulse, harmonic validation or full mix/DAW synchronization yet. Do not equate candidate periodicity with authoritative BPM.
