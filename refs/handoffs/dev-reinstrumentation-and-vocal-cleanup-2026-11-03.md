# CURRENT DEV HANDOFF: Song Harbor reinstrumentation + vocal restoration
Date: 2026-11-03
Scope: Three next implementation workstreams (piano roll, SFZ, Deshimmer)
Branch: **dev ONLY**. Do not work on main unless user explicitly approves a promotion.
Starting point: dev HEAD at least 8c5746a (polyphonic SF2 render), plus later source updates on dev if any. Always fetch current dev before editing.
User acceptance so far: dev application reloaded clean once, but not otherwise tested. User auditioned Mean Saw Bass and said it sounds pretty good. Do not infer that polyphonic rendering, piano roll or export have passed Windows QA.
Release: previous track mix is locked. Keep main and locked release assets unchanged.

## Mission and priority order
The next track has a relatively sparse arrangement. The aim is to reinstrument **all instrumental parts, not vocals**, with high-quality editable MIDI and sampled instruments, while aggressively investigating restoration of the **original vocal identity and phrasing**. Three near-term engineering workstreams:
1. **Piano roll / arrangement as editable production asset** (P0, fix correctness and usability first).
2. **SFZ sampler/render support** (P1; high-value expressive instruments and Growlybass / Bigcat cello).
3. **Deshimmer bridge** (P1 in parallel where possible; initial focus on isolated vocal stem, non-destructive).
Keep shared playback, candidate and transport infrastructure rather than multiplying tool windows.

## Existing source: distinguish implemented code from verified behavior
- `app/backend/midi_arrangements.py`: persistent schema-v1 MIDI arrangements, stable UUID note IDs, 48 kHz sample positions, source provenance, revision-checked atomic add/update/remove patches, polyphonic note overlaps. Source and candidate WAVs are not changed by an arrangement save.
- `app/frontend/src/MidiPianoRoll.tsx`: embedded first-pass SVG piano roll in existing Stem Tools > MIDI. Saved arrangement list, open, note creation/move/resize, velocity numeric field, undo/redo, optional grid snap (off initially), explicit Save and Render arrangement. No full velocity lane, multi-select, beat/tempo-map, robust keyboard editing, note grouping or score-wide zoom yet. Test drag/canvas coordinate math and accessibility on Windows.
- `app/frontend/src/BassMidiTool.tsx`: generic stem selection and legacy note list for transcription, plus piano roll; candidate A/B, Original dial, instrument selection and add/remove stem. Current monophonic transcription is heuristic (not reliable polyphony), distinct from polyphonic *render*.
- `app/backend/polyphonic_midi.py`: renders polyphonic note events to deterministic Standard MIDI Type 0 at fixed 120 BPM; validates same-pitch same-channel overlaps and excludes drum channel 10. `server.py` route `POST /api/projects/{id}/midi-arrangements/{asset_id}/render` verifies saved revision, resolves SF2 instrument and renders to an existing candidate via FluidSynth. No SFZ yet.
- `app/backend/instrument_library.py`: instrument pack registry, reviewed GeneralUser GS optional starter, manual SF2 import, FluidSynth support/configuration, SF2 instrument program/bank list. UI now offers **Configure FluidSynth** directly when missing; it opens the existing Settings > Components path.
- Existing audio cleanup Review/Original/Current/Fix and reversible recipe concepts. **No integrated Deshimmer adapter** yet; upstream checkout on user's Windows machine `D:\Apps\deshimmer`. Do not call it integrated.
- Tests committed include `test_midi_arrangements.py`, `test_polyphonic_midi.py` and older `test_bass_midi.py`. Frontend build, Windows drag/audio/render and persistence QA remain unverified in this thread.
- Design principles: compact icon-first context tools, wide useful timeline, resize rather than cramped controls, no surprise autoplay, explicit and reversible acceptance, no source overwrites, easy to do/easy to undo, same audition/export output, scripts/automation respected, no redundant permanent panels.
- LLM editability is a deliberate future requirement: MIDI is the canonical production asset. AI suggestions must generate *reviewable, explicit patch operations* against a base revision; never silently mutate an arrangement, and never discard original user edits.

## Workstream A - piano roll correctness + production editing
A0 **QA/regression gate before new features**:
- Load/saving/refreshing saved arrangement and candidate, source/stem switching, dirty state, note IDs and revision conflicts.
- Verify first-pass pointer drag and resize with horizontal scrolling, window resizing, edges, note hitboxes and keyboard focus. Test 20-second and 5+ minute score sizes; ensure layout does not widen the entire page.
- Verify the instrument dropdown is usable even without an active transcription candidate, that Render arrangement uses selected pack, and that a changed instrument rerenders rather than reuses stale audition. Check sparse overlapping notes and SF2 playback vs offline WAV. Fix bugs instead of covering with extra UI.
- Run backend unit tests, TypeScript/Vite build and Windows portable smoke. Record actual results, not assumed pass.

A1 **Make score the single source of truth**:
- Merge legacy note list and piano roll onto the versioned `midi_arrangements` asset. Explicit New/Save/Save As/Revert; reopening/revision conflict prompts; unsaved badge; avoid creating a new arrangement ID each Save.
- Render from **persisted selected arrangement revision** only; dirty score requires explicit Save or creates temporary clearly named preview that cannot overwrite saved record.
- Keep instrument selection / preview volume / Original stem gain separate from note content and preserve note IDs on re-render.
- Add usable undo/redo per edit gesture; stable selection, keyboard deletion/nudge/transposition, multi-select, copy/paste, zoom, a compact scrollable velocity lane, loop audition across the same timeline, and precise grid options (snap OFF by default).
- Introduce coherent song-time/beat mapping: store sample-accurate position as authority, add tempo map/PPQ metadata non-destructively, allow relative beat grid and swing/quantization with adjustable strength and undo. Avoid forcing original human timing into 120-BPM assumptions.
- Future editing contract: `{base_revision, operations:[{op:'add'|'update'|'remove',...}]}` with proposed diff, optional reason/confidence, preview-before-commit. Do not add an LLM dependency now.

A2 **QA**:
- UI exercises create/drag/resize/duplicate/multi-select/velocity/undo/redo/save/reopen and 1-3 overlapping notes across chords/section boundaries. Snap off and on. No change to original WAV hash.
- No stuck playhead, audio drift, hidden accept/discard or changed track automation. Exported accepted candidate and audition align to sample/section timing.
- Add isolated frontend tests for note hit geometry and editing reducer; backend schema/patch round-trip tests.

## Workstream B - SFZ instrument support
B0 Discovery:
- Choose a compatible and maintained Windows-capable SFZ sampler (e.g. **sfizz** CLI/library only if independently verified; do not assume SF2/FluidSynth loads SFZ). Verify CLI/API, compiled Windows binaries, local offline WAV render, sample-rate, sample triggers, release tail, license of engine and instrument, dependency/installer footprint, and reproducible pinned version. Prefer isolated process adapter rather than building a universal VST/CLAP host.
- Initial actual sample pack targets: Karoryfer x Bigcat Cello, Karoryfer Growlybass, a suitable VSCO 2 Community SFZ bank. Confirm licenses from publishers before any download or redistribution; manual local import preferred. No samples shipped in repo.
B1 Engine + pack registry:
- Add `engine:'sfz'` manifest support with local file picker, bounded extraction/import, path traversal/symlink reject, manifest file/sample hashes, instrument/articulation display, and path-safe data-only assets. User must explicitly install/browse. Avoid executing scripts from pack content.
- Renderer adapter with version probe and Settings > Components configuration at the point of failed render. If sampler does not expose a reliable standalone command, create a bounded helper using its supported library API, not an invented CLI.
- Use the same arrangement MIDI note data and same candidate preview/accept/undo workflow as SF2. Correct sound at sample clock, support velocity layers, release samples/round robin and CC keyswitch if the bank uses them. Permit different instruments for different score parts eventually; first slice one score-part/one SFZ instrument.
- Persist pack ID+hash, instrument ID, sampler version, MIDI arrangement ID/revision with the accepted candidate. Existing accepted audio must still play if the pack is later removed; rerender must warn clearly.
B2 QA:
- Real Windows audition of SFZ cello and Growlybass against GeneralUser GS equivalents, release/noise tails, missed notes, clicks, 48-kHz stereo output and render time. Verify same time alignment in player and 24-bit master export. Missing pack path must surface an actionable Configure/Locate control in the instrument area.
- License and network review, malformed pack, oversize pack, duplicate pack, missing samples, cancellation, nonfinite/clipped output, source integrity tests.

## Workstream C - Deshimmer vocal restoration bridge
C0 Existing integration plan: `docs/deshimmer-song-harbor-integration-plan-2026-11-03.md`; detailed upstream audit: `docs/deshimmer-evaluation-handoff-2026-11-03.md`. Do not blindly use the full-mix approved settings on vocals: they included intentional EQ/stereo/punch color changes, and the online 95% AI detection score is not a sound-quality metric.
C1 P0 isolated bridge:
- Probe configured `D:\Apps\deshimmer` Python environment and verify exact upstream version/API; worker imports `deshimmer.api.process_audio`, not Gradio. Server-owned input only; safe path validation, bounded async job with status/cancel/timeout, single-job concurrency and deterministic exact parameters, source hash/range identity. Start with isolated vocal stem whole-region then selected short range.
- Put Deshimmer action into existing Sound Cleanup review, not new full panel. Missing tool: contextual Configure Deshimmer opening existing component settings. Do NOT auto-play after adjustments. Preview candidate with Original/Current/Fix and **Removed by repair / Full difference**, matched perceived volume and aligned transport.
- Separate restorative components (shimmer/denoise/resonance) from optional creative enhancements/tonal balance. Presets/recipes versioned and inspectable; golden output fixture with verified upstream commit.
C2 P1 acceptance and vocal quality:
- Immutable accepted vocal repair candidate/recipe, original stem untouched. User-controlled Accept/Discard/Undo and reliable save/reopen. Reuse shared mix pipeline and preserve all section scripting; explicit processing order relative to stem effects.
- Compare wet consonants, breaths, formants, vibrato, backing vocal bleed, deliberate rasp, cymbal-like shimmer, hiss. Difference audition should make incidental musical loss evident.
- Ensure live audition and WAV export are sample/time/level consistent including transitions and tails. Avoid global auto-normalization or mastering.
C3 P2 after first verified success:
- Region repair with preceding/following context, exact trimming and crossfade, per-stem selective use and region boundaries. Optimize is an explicit **optional experiment**, never an automatic detector-score target or provenance removal.
C4 QA:
- Missing dependency, corrupt input, stale hash, cancel, timeout, deterministic repeat, input sample rate/channels, latency/tail/crossfade, preserve stereo, original waveform unchanged and real-world vocal listening. Run artifact suites separately from valid hearing tests.

## Recommended execution / parallelism
0. Baseline QA and quick correctness fixes first; no UI expansion until current dev slice builds and render works.
1. Deliver **A1** usable arrangement editor in main existing Stem Tools while starting **C1** Deshimmer Python handshake (independent work).
2. Deliver **B0/B1** SFZ renderer after sample engine/version is verified, then render saved score revisions through both SF2 and SFZ.
3. Deliver **C2** vocal accept/export parity and **B2** instrument bank real-music audition; fix any discovered synchronization or failure/UX issues.
4. Later: drum-focused extraction, articulation lanes/CC, polyphonic transcription, LLM patch review and optional local optimizer only after base workflows are validated.
Stage each meaningful slice with a repo commit on `dev` and update this handoff with actual test results. No main promotion without explicit user approval.

## Continuation 2026-11-03: incremental dev-only commits

Source inspection and GitHub commits completed; **not** a local Windows or CI test pass.
No changes to main or locked release assets. Latest handoff source SHA before update:
`f328b607b9011dc2aa08407636bcd119f5009677`.

### A: MIDI editor
- `1de2d42`: corrected drag snap to quantize absolute positions and adjusted pointer geometry for scaled SVG.
- `0fcd413`: keyboard single-note nudge (arrows), Ctrl+D duplicate, delete, explicit Revert, focus editor after note selection.
- `354851e`: piano roll optionally loads the persisted arrangement created by Save arrangement.
- `19d1acc`: legacy candidate editor yields to saved arrangement path after Save; use saved revision for subsequent render, not legacy note state.
- `e0ba6b6`: switching selected stem clears source-specific arrangement selection.
- `594a3df`, `4a23b34`: track dirty arrangement state, guard browser unload, and confirm before a user changes stems.
- Still incomplete: multi-select, clipboard, velocity lane, real tempo map, Save As, zoom/loop, revision collision recovery, keyboard accessibility QA. Automatic source changes from parent state/job transitions still need dedicated QA for unsaved work; do not describe the editor as finished.
- Test status: code committed; TypeScript/Vite build, interaction testing, backend suite, Windows audio and persistence **not executed** in this continuation.

### B: SFZ discovery and isolated adapter
- `130020e`, `07b073f`: `app/backend/sfz_render_adapter.py` supports configured offline `sfizz_render` with MIDI+SFZ file paths, 48 kHz stereo WAV validation, no overwrite, bounded timeout, failure cleanup. Not yet connected to pack registry, render endpoint, settings, preview or acceptance.
- `a7b15c0`: mocked unit tests added; not executed.
- Independently confirmed documented CLI: `sfizz_render --sfz FILE --midi FILE --wav FILE --samplerate 48000` (https://www.sfz.tools/sfizz/development/build/ and https://man.archlinux.org/man/sfizz_render.1.en). The original sfztools/sfizz repository was archived June 2026; treat as pinned dependency, do not assume ongoing upstream support.
- Pending: explicit pack import/path/sample validation, version pin and binary probe, safe isolated candidate storage, API wiring, local install QA, license review, real sample render.

### C: Deshimmer preflight only
- `dfd09f5`: `app/backend/deshimmer_adapter.py` probes a configured Python executable for callable `deshimmer.api.process_audio` via bounded subprocess, no Gradio import or audio processing.
- `f328b60`: mocked handshake tests added; not executed.
- It does not verify a specific Deshimmer upstream commit or function arguments, and does not yet include processing, Sound Cleanup UI, jobs, previews, acceptance or export parity.
- Next: confirm actual installed API signature/return payload and version, then implement server-owned audio worker with bounded temp jobs and validated output, before any browser action.

### Validation gate
This session had GitHub repository access but no working container network checkout; a direct `git ls-remote` failed DNS resolution. No build/tests/audio verification can be claimed. Run backend unit tests and frontend build on the configured dev machine before accepting. One practical spot check is to save an extracted arrangement, confirm the legacy editor disappears, edit/Save/reopen and render from the new piano roll while checking original audio is unchanged.

---

## Continuation: multi-note editing slice (2026-11-03)
Branch remains **dev only**. No main promotion or production audio changes.

- `90c56e6`: added Shift-click multi-note selection, group dragging, group nudging, copy/paste, group duplicate/delete using existing atomic arrangement patches. Clipboard is in-memory, not browser-global.
- `62fe3d7`: Select All, Clear, Ctrl+A/Escape and batch velocity edits.
- `0c62e28`: backend regression added for atomic 3-note patch, stable note IDs, persistence and rejected invalid batch.
- `6820f47`: invalidates MIDI candidate audition when the score becomes dirty, to prevent accidental playback of stale renders.
- Existing arrangement Save remains explicit and revision-guarded, with rendering disabled for dirty scores; note edits do not overwrite original stems.
- QA **not passed**: React/TypeScript build, Windows pointer gestures, group drag constraints, copy/paste, undo/redo, save/reopen, audio preview, exported WAV, and SFZ/Deshimmer sample processing still require execution. The GitHub connector supports repository edits, but this session's shell cannot resolve github.com to clone the dev tree.
- Design caveats: multi-selection is Shift-click rather than rectangle/lasso; clipboard paste places a phrase after its original end (or clips to score end), not yet a clicked playhead. Velocity is a numeric batch field, not a lane. No quantization or tempo-map conversion was introduced. Keep these limitations visible rather than imply complete piano roll.
- SFZ command syntax verified against official sfizz build docs and `sfizz_render` manual: `--sfz`, `--midi`, `--wav`, `--samplerate`. Windows binary/package and sample-bank audio QA remain pending.

### Next concrete QA gate
1. `cd app/frontend && npm run build` and `python -m unittest app.backend.tests.test_midi_arrangements app.backend.tests.test_sfz_render_adapter app.backend.tests.test_deshimmer_adapter` (adjust Python working directory/import paths if needed).
2. Use dev GUI on an arrangement with overlapping notes. Shift-select several notes; move/transpose; group velocity; copy/paste; Undo/Redo; Save; refresh; reopen; Render; compare output.
3. Verify a dirty score clears an existing rendered preview and source stems remain bit-identical.
4. Only then add velocity lane/zoom, SFZ candidate flow and bounded Deshimmer worker with real fixture validation.

---
## Continuation: piano-roll zoom and velocity editing (2026-11-03)
Branch: **dev only**. Prior user confirmed clean update loop for the previous slice, not this newly committed code.

- `e3661d7`: horizontal zoom presets (24, 65, 130, 260 pixels per second); preserves approximate viewport center when switching zoom, does not change note sample timestamps.
- `99c79ad`: aligned SVG velocity lane under piano-roll note grid. Dragging a velocity bar edits its note, or all currently selected notes if the dragged bar belongs to the group. Undo state captured once per drag, edited value clamped to MIDI 1-127. The existing numeric velocity edit remains.
- Pure source inspection confirmed old fixed PX_PER_SECOND references removed and the piano grid lines end before the lane. **Not a TypeScript build or interaction pass**.
- Open QA: zoom center preservation while scrolling at several window sizes; note hit targets at Overview; velocity lane accessibility and dense-overlap bar usability; undo/redo of a drag gesture; save/reopen/revision conflict; no preview autoplay or source mutation.
- Backend SFZ and Deshimmer work remains adapter/preflight only, not integrated audio processing.

---
## Immediate next-thread task
1. Read this file, `docs/dev-full-reinstrumentation-vocal-restoration-2026-11-03.md`, `docs/dev-polyphonic-render-slice-2026-11-03.md`, and `docs/deshimmer-song-harbor-integration-plan-2026-11-03.md`.
2. Fetch `dev`, compare current source with claims, run/build existing backend and frontend tests if an execution environment supports it.
3. Begin A0/A1, particularly authoritative note edits and piano-roll usability, while documenting an independently implementable C1 Deshimmer adapter path.
4. Preserve all accepted audio and previous production mix; work only on `dev`. Report committed SHA and actual/remaining QA.

## Explicit technical caution
The existing `refs/handoffs/currentHandoff.md` contains old guidance to work on `main` and older artifact priorities; those are historical for this new-track dev project. **This dev handoff supersedes that branch/prioritization guidance for the next thread.**
