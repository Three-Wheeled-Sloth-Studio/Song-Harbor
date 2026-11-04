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
## TIMEOUT RECOVERY: SFZ integration in progress (2026-11-03, evening)

**Purpose of this checkpoint:** The previous assistant message delivery timed out while development was underway. These changes were already committed before the interruption. This section records the actual stopping point and prevents duplicate work or overstated QA.

**Working branch: `dev` ONLY. Do not modify or promote `main`.** The user reported the *prior* update loop was clean, not that the new SFZ implementation passed a build or an audio audition. Locked tracks, mixes, and source stems must remain immutable.

### Committed in this interrupted slice, sequentially
- `2bf5bd5`: new `app/backend/sfz_pack.py`, initial bounded importer for user-provided self-contained SFZ ZIP archives.
- `fc05ee1`: streaming hashing instead of loading complete sample files for the pack fingerprint.
- `aec09a3`: SFZ engine/pack/instrument enumeration and individual SFZ path resolution in `instrument_library.py`.
- `f39bdca`: `server.py` adds `POST /api/instruments/sfz`; branches the existing saved-revision `POST /api/projects/{ident}/midi-arrangements/{asset_id}/render` to sfizz for SFZ instruments, retains SF2 branch, aligns to 48-kHz stereo PCM candidate, records instrument hash, and retains the current candidate A/B/add-stem workflow. This is a source implementation **not verified by end-to-end execution**.
- `cddeae4`: importer checks relative sample references for missing/external files.
- `a2ab811`: `BassMidiTool.tsx` adds local SFZ ZIP import picker, SFZ instrument selection, and saved-arrangement render path; error/help text notes `SONG_HARBOR_SFIZZ_RENDER`.
- `877954f`: new `app/backend/tests/test_sfz_pack.py`, unit tests for simple local package, registry resolution, traversal, unresolved samples, unsafe include, duplicate names.
- `ddbefaf`: tightened SFZ sample-opcode parsing to stop at a subsequent attribute on one line and rejected `default_path` in the intentionally narrow v1 importer.

### Source inspection at recovery
The `dev` GitHub reads confirmed:
- `server.py` contains the SFZ import route and calls `sfz_render_adapter.render_sfz` in the saved-arrangement renderer.
- `BassMidiTool.tsx` contains the SFZ ZIP import control and renders saved arrangements with SF2 or SFZ instruments.
- `instrument_library.py` lists and resolves SFZ manifest entries.
- `sfz_pack.py` contains archive/path checks and a content fingerprint.
- The prior `app/backend/sfz_render_adapter.py` remains as the sandboxed subprocess wrapper; it expects an installed offline `sfizz_render` executable.
- **No verification has been recorded for Python syntax, imports, unit tests, TypeScript/Vite build, Windows startup, actual ZIP import, actual sfizz execution, audio quality, or audition/export parity.** No commit-status checks reported on earlier development commits. Do not call these completed QA.

### Known gaps, likely fixes, and cautions before QA
1. **Run the new tests first** from `app/backend` (e.g., `python -m unittest discover -s tests -p 'test_sfz*.py' -v`). Then run `cd app/frontend && npm run build`, backend regression suite, and the Windows dev launcher. The tests were committed but not executed remotely.
2. Inspect `sfz_pack.py` sample parsing/metadata carefully with real sfizz-compatible packs. Current importer **deliberately rejects** external includes, preprocessing, `default_path`, and non-relative sample links, so many full instrument packs may fail with a clear error. Archive extraction is bounded by ZIP metadata but requires further adversarial tests for actual expanded-byte limits, symlinks, spoofed ZIP entries, duplicate directories, and malformed encoding. The importer has *not* been proven safe for arbitrary untrusted archives.
3. **Critical usability gap:** the previous attempt to locate the Settings > Components React source ended with an unsuccessful lookup of `app/frontend/src/App.tsx` (404). A configured-path action for sfizz in Settings has **not** been implemented. The current UI only shows the environment variable `SONG_HARBOR_SFIZZ_RENDER`; do not mark contextual setup complete.
4. `sfizz_render` binary/version handshake and compatibility with published executable flag syntax need Windows validation. No engine install/download or sample assets were added. Original sfizz upstream archival status should be considered before selecting a pinned runtime.
5. The API currently creates output through existing candidate logic; verify exact output frame count, tail handling, sample alignment, non-finite/clipped output, candidate provenance (full pack hash, not merely SFZ-definition hash), preview/accept/reopen/export parity, and graceful missing-executable errors before shipping.
6. Investigate the **saved-arrangement render vs legacy candidate render** distinction: SFZ is only connected to the saved-arrangement route. Avoid accidentally rendering a stale or unsaved note list. Verify no accidental autoplay.
7. Code in `server.py` relies on the existing ffmpeg dependency for output alignment; make sure an actual install and missing-dependency path are tested.
8. SFZ importer current format is narrow: uploaded **ZIP** with `.sfz` and relative sample files. A raw `.sfz` file alone is not a supported import. Karoryfer cello/Growlybass and VSCO 2 remain **unverified** for import, render, license and sound. No samples or licenses were redistributed.
9. Deshimmer was **not changed** in the interrupted slice. Only the previously committed Python capability handshake exists; no processing/preview/accept UI yet.
10. The preceding MIDI piano roll editor (group editing, zoom, velocity lane) was not changed in this interrupted SFZ slice. User's "update is clean" is not proof of a comprehensive MIDI QA pass.

### Resume from this exact point
1. Pull and inspect current `dev` (latest code commit before this handoff was `ddbefafe219cffcecfb900d9d6467c0928022fe7`; check for newer dev commits). Validate Python syntax/tests + frontend build before expanding functionality.
2. Find actual Settings > Components source files (do not assume `App.tsx`) and add a contextual, verified sfizz executable selector/path, consistent with FluidSynth.
3. Fix any SFZ ZIP parser/import issues found by fixtures, then run import plus first actual 48-kHz MIDI-to-WAV on Windows with a small legal/sample-based instrument. Do not assume full Karoryfer/VSCO compatibility.
4. Exercise the saved MIDI arrangement > selected SFZ > candidate A/B > reversible Add stem > reload > export path, comparing timing, original source hash and sound.
5. Keep SFZ and Deshimmer progress separate. Only after SFZ gate, continue Deshimmer worker with a pinned external API and non-destructive preview.
6. Continue recording every actual test outcome and incremental `dev` commit. Never report a feature as tested just because it compiles or the app reloads.

---

## 2026-11-04: resumed SFZ setup and import hardening

Branch: **dev ONLY**; main and release audio untouched. The user's last "Proceed" followed a timeout recovery, not a successful SFZ render test.

### Commits (in order)
- `80f2816` `sfz_render_adapter.py`: machine-local sfizz executable configuration, fixed-basename validation, bounded `--help` probe, atomic save in existing settings JSON, native Windows picker, configured/PATH discovery, and render using configured binary.
- `bf5151f` `server.py`: GET/PUT `/api/settings/sfizz`, POST `/api/settings/sfizz/browse`, exposed `sfizz_ready` in instrument catalog, configured renderer passed to SFZ render path.
- `84fccfe` `AppSettings.tsx`: contextual Components UI for Browse, Detect, Verify & save, ready/not configured status.
- `15d6a69`, `2570f86`, `eb551ae`: prop wiring from `main.tsx` through `StemMixer.tsx` into `BassMidiTool.tsx`; missing sfizz in instrument area now links directly to Settings.
- `9e577fd` `sfz_pack.py`: bounded actual decompressed-byte streaming per ZIP entry; reject unexpected entry sizes; importer retains rollback behavior.
- `671c83f` `test_sfz_render_adapter.py`: mocked settings validation, preserving other machine config keys, missing or mismatched executable.
- `b445571` `test_sfz_pack.py`: ZIP unpacked size limits, default_path rejection, failed import cleanup.
- `292b14b` `server.py`: candidate metadata includes `instrument_engine`, `instrument_sha256`, full `pack_sha256` from manifest.

### What was actually checked
- GitHub `dev` source inspection after wiring confirmed the expected frontend props/settings controls and backend routes were present.
- Public upstream sfizz-render source confirms `--help`, `--sfz`, `--midi`, `--wav`, `--samplerate`, and 16-bit stereo WAV output; source https://github.com/sfztools/sfizz-render/blob/master/main.cpp and CLI manual https://man.archlinux.org/man/sfizz_render.1.en.
- This environment has no working DNS access to `github.com` from the command-line container, therefore it **cannot clone/build/run the exact remote tree**. The GitHub app used for code commits does not itself execute tests.
- **No local Windows, frontend build, backend unit test, actual SFZ ZIP import, sampler probe, candidate audition, save/reopen, or export parity has passed during this session.** These are implementation commits awaiting testing.

### Required next QA and limitations
1. From dev checkout: `cd app/backend && python -m unittest discover -s tests -p 'test_sfz*.py' -v`, then full backend suite. Frontend `cd app/frontend && npm run build`. Fix test/build failures before any more features.
2. In Settings > Components, browse to installed `sfizz_render.exe`, verify and save, close/reopen Settings, ensure persisted path and `sfizz_ready` updates. Then in Stem Tools > MIDI select SFZ instrument and render a **saved** arrangement revision. The selection remains an explicit user action; no autoplay.
3. Import a tiny known-good self-contained SFZ ZIP first. Larger Karoryfer/VSCO packs may use unsupported `#include` or `default_path` opcodes, so current importer intentionally rejects them. Their licensing, sound, and compatibility are unverified.
4. Test same MIDI with SF2 vs SFZ, held notes and release tails, clipping, candidate A/B, Add stem/undo/reopen, section automation, 48-kHz timing and 24-bit export parity. Confirm original stem hash unchanged.
5. Validate ffmpeg dependency, sfizz error reporting, malformed archives and race conditions. Full pack fingerprint is recorded but user-mutation verification against the original manifest and sampler-version pinning remain pending.
6. Deshimmer remains an isolated Python API **handshake only**, not a vocal cleanup processor or integrated candidate. Do not claim processing has been implemented.
7. The historical handoff above contains earlier statements that SFZ was not connected. Those refer to previous checkpoints. As of this section, source is connected but **not tested**.

---
## 2026-11-04: curated SFZ instrument starter library (user confirmed sfizz configured)

User reported `sfizz_render.exe` loaded and configured on Windows, requested recommended starter packs placed in the in-app loader. No Windows instrument ZIP was supplied or auditioned during this session. Continue **dev only**, preserve main and all locked mixes.

### Curated editorial catalog and UI
- `a1877c1`: added `app/backend/curated_sfz.py`, editorial CC0/official release-asset catalog. No downloads, third-party binaries, audio samples, or licenses bundled.
- `c6069c2`: added `GET /api/instruments/curated-sfz`, data-only source of recommendations.
- `82f3795`: `BassMidiTool.tsx` loads the catalog, adds collapsible "Curated SFZ" within existing MIDI instrument import controls, publisher Get ZIP/Source links and manual local Import ZIP action using the current safe import route. Imported pack becomes selected. The button is **not** a verified one-click network installer.
- `0ef65f3`: compact, scrollable editorial entries in existing Stem Tools, no new permanent pane.
- `cdf38ec`: expanded initial recommendations with unusual Infra Choir-friendly String Cyborgs, War Tuba and Caveman Cosmonaut.
- `be7f2a1`: removed VSCO 2 CE from actionable curated list: its published ~2.3GB archive exceeds the current 768MB ZIP upload cap. Reconsider later with explicit large-pack streaming/storage design, not a disabled/false installer.
- `5eedb1f`: metadata-only regression tests `test_curated_sfz.py` require CC0, HTTPS versioned official ZIP assets, distinct IDs, no pack exceeding upload limit.
- Catalog currently features 7 CC0 Karoryfer downloads: Bigcat Cello v1.001 (~133MB ZIP), Growlybass v1.002 (~167MB), Bear Sax v1.004 (~132MB), Big Rusty Drums v1.100 (~620MB), String Cyborgs v1.001 (~64MB), War Tuba v1.002 (~109MB), Caveman Cosmonaut v1.001 (~98MB). Each official versioned GitHub release URL and size were queried from GitHub release metadata (2026-11-04). Sizes in UI are rounded download sizes, not total unpacked disk usage. License is marked CC0 based on Karoryfer's official free-samples page and repository LICENSE, no third-party sample redistribution.

### SFZ ZIP compatibility improvements
- `81b1f07`: importer accepts harmless metadata/UI companions (.txt/.pdf/.png/.xml/etc.) by **skipping**, not executing or importing them, and supports bounded relative `default_path` for sample references.
- `276a4fe`: also skips extensionless README/LICENSE/COPYING/AUTHORS/CHANGELOG/NOTICE.
- `b43f46e`: permits `../Samples/` relative paths in SFZ definitions **only when the fully resolved sample stays inside the imported pack root**, for common sibling Programs/Samples layouts. The ZIP filenames themselves still forbid traversal.
- `dcd66de`: skips optional Kontakt `.nki`/`.nkm`/`.nk*` companions. It does **not** load Kontakt presets; SFZ definitions only.
- `bb0178d`, `e696dff`: updated ZIP importer regression fixtures for `default_path`, sibling Samples layout, metadata skipping, failed import cleanup and external path rejection.
- Our intentionally bounded importer still **rejects** SFZ `#include` and macro `#define`, external absolute sample references, archives over 768 MB or metadata declaring over 1.5GB uncompressed, and unexpected executable file types. Real library compatibility remains unknown until a specific release ZIP is imported and a MIDI render is auditioned.
- Check `app/backend/sfz_pack.py` for security and edge-case parsing before shipping beyond local development, notably sample filename quoting, multiple `default_path` headers and extremely large decompression cases.

### Provenance and QA
- Source: https://shop.karoryfer.com/pages/free-samples; individual GitHub releases under `sfzinstruments/`; license evidence e.g. https://github.com/sfzinstruments/karoryfer.growlybass.
- VSCO 2 CE remains a later candidate: https://versilian-studios.com/vsco-community/ (larger than allowed).
- The private GitHub repository was updated via GitHub connector. The command-line container still cannot resolve `github.com`, so **no exact checked-out dev frontend build, backend unittest, ZIP import, sfizz subprocess audition, or export parity test was executed**. Static source inspection confirms catalog integration; commits passing API calls do not prove runtime compatibility.
- Priority: on user Windows dev build, run `npm run build` in `app/frontend`, `python -m unittest discover -s tests -p 'test_*sfz*.py' -v` from `app/backend`, and try real Bigcat Cello and Growlybass releases with short saved MIDI phrases. Record pack importer success/errors, polyphony, release tails, audio quality and candidate accept/export alignment. Revisit archive parser pragmatically based on real failures.
- If a curated ZIP does not import, inspect its published structure and unsupported opcode; do not mark it installed or silently bypass security checks. Avoid auto-download until producer-approved fixed release and SHA-256 are verified (GitHub asset metadata currently did not include a digest).

---
## Immediate next-thread task
1. Read this file, `docs/dev-full-reinstrumentation-vocal-restoration-2026-11-03.md`, `docs/dev-polyphonic-render-slice-2026-11-03.md`, and `docs/deshimmer-song-harbor-integration-plan-2026-11-03.md`.
2. Fetch `dev`, compare current source with claims, run/build existing backend and frontend tests if an execution environment supports it.
3. Begin A0/A1, particularly authoritative note edits and piano-roll usability, while documenting an independently implementable C1 Deshimmer adapter path.
4. Preserve all accepted audio and previous production mix; work only on `dev`. Report committed SHA and actual/remaining QA.

## Explicit technical caution
The existing `refs/handoffs/currentHandoff.md` contains old guidance to work on `main` and older artifact priorities; those are historical for this new-track dev project. **This dev handoff supersedes that branch/prioritization guidance for the next thread.**
