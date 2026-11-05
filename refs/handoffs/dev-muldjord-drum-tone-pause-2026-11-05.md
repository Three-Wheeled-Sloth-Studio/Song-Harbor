# Song Harbor DEV handoff: Muldjord drum tone and transcription, paused for production release

Date: 2026-11-05
Status: **PAUSED by user for next Infra Choir release on existing production path. Do not resume experimental development or merge into main without explicit request.**
Branch at handoff: `dev` = `b2c782a69b5bdccace069db6503c5e63103c9e20`
Production branch: `main` = `2345c61d57407b62cf809fd4f2c68b972eb60f89`
Related design plan: `docs/dev-drum-specific-transcription-2026-11-05.md`

## Summary for next thread

User reports **DEV build clean and drum render sounding better**, but **not production-ready**. Muldjord Kit SFZ import and render work on Windows. Relative to Big Rusty, Muldjord sounds fuller, with appropriate candidate output volume. Extraction creates and opens an editable saved percussion MIDI score; example reviewed had 565 notes. The piano roll now includes compact mapped drum lanes and a Muldjord keymap shortcut. No promotion to main is authorized.

**Critical sonic regression: low, deep, booming, messy crashes in the ORIGINAL source become unnaturally crisp, higher-pitched, thin and mechanical when transcribed and re-rendered. The emotional result changes from ominous to mechanical. Preserve the source's threatening weight, decay, room, stereo texture and dissonant tails.** Do not declare success merely because MIDI hit onsets align, drum samples are louder, or the new kit sounds cleaner. The desired timbre may involve low toms, low-pitched impacts, distorted cymbals, overlapping kick/symbol textures, original room tails, or layered sound design, not a conventional high-pitched crash. A single MIDI note/preset cannot reliably encode these qualities.

### Implementation present on dev

- SFZ ZIP importer supports bounded archives up to 4 GiB compressed and 8 GiB declared expanded, with disk reserve, safe paths, text-based `#include` files, sample macros, and exact local sample reference validation. Muldjord SFZ imported successfully after the text-fragment fix. Do not conflate the ~338 MB SFZ conversion with ~2.48 GB DrumGizmo kit archive.
- `app/backend/drum_transcription.py`: CPU spectral-flux/onset estimation using five broad frequency bands, provisional lanes 36 kick / 38 snare / 42 closed hat / 41 low tom / 49 crash and limited simultaneous-hit hypotheses; creates editable, saved, channel-10 MIDI arrangement. This is still a heuristic, NOT comprehensive source separation.
- `app/backend/polyphonic_midi.py`: safe same-pitch percussion retriggers; melodic overlap checks preserved. Note-off on retrigger may still affect acoustic tails; verify the renderer's one-shot/voice-stealing semantics before assuming tails are intact.
- `app/backend/midi_candidate_level.py`: boost-only bounded gain for newly rendered SFZ/SF2 candidates; user confirms volume is now appropriate. Do not change loudness normalization based on this feedback.
- `app/frontend/src/MidiPianoRoll.tsx`: drum rows compacted to mapped lanes plus unmatched notes, kick-forward velocity accents remain undoable, and Muldjord keymap is available when the stereo instrument is selected. Published keymap: kick 35/36, snare 37/38, toms 41/45/47/48, hats 42/46, crash 49/57, china 52, rides 51/53/55/59; choke control notes distinct from hits.
- Reversible arrangements, A/B candidates and user approval are mandatory. Natural-language instrument direction currently selects presets, not full LLM drum composition. Do not represent it otherwise.

### User-verified QA

- Latest Windows DEV build clean. This is a **user report**, not a claim that all GitHub Actions suites pass.
- Muldjord SFZ import clean.
- Muldjord drum render generally fuller, more realistic and correctly leveled compared with Big Rusty; still thin/artifactual in portions and especially wrong in boomy crashes.
- Earlier QA: old extractor over-assigned snare/kick, little hi-hat variety; note grid had 565 events. Five-lane estimator/map UI were implemented after that screenshot. The user reports it sounds better; do NOT infer measured precision/recall or successful tom/cymbal classification from that qualitative report.
- Do not discard or overwrite the user-approved existing production arrangement or audio, and do not automatically accept new candidates.
- Muldjord sample licensing/attribution: user explicitly agreed to provide required attribution on any release using its samples. Keep sample credit **separate** from the existing locked Infra Choir standard credit wording.

## Top priority on resumption: retain ominous boomy crashes

1. **Select and preserve a ground-truth passage** from the source audio containing 2-4 representative deep messy crashes, plus a reference normal kick, snare and cymbal. Create a section-bounded QA fixture or timestamped comparison against the exact source. Capture source vs new stereo mix at matched perceived level, peak, duration and stereo field. Do not assume no sample replacement will be necessary.
2. **Classify the source sound before mapping to a GM pitch.** Determine whether each impact is acoustic cymbal, low tom, kick+crash, noise wash, low-frequency industrial impact, or a layered/processed combination. Analyze pre/post spectral centroid, low-band energy, decay duration, onset layering, envelope and stereo width. Separate transcription timing, instrument family, rendering, sample-program choice and processing as distinct stages.
3. **Introduce a non-destructive 'unclassified impact / texture' lane** or layered hit event rather than forcing all deep crashes into crisp `49 Crash` or `38 Snare`. Preserve source slices or spectral/texture layers where sample substitution is not timbrally equivalent. Prefer retained source texture/room tails underneath carefully chosen synthesized/transcribed hits. This is a candidate architectural feature, not yet implemented.
4. **Expand multi-label drum transcription** for simultaneous kick, snare, open/closed hats, low/mid/high toms, multiple cymbals, rides, crashes, ghost notes and fills with confidence and human-in-the-loop reassignment. Measure classifications on ground truth; don't raise the number of labels simply to make a fuller grid.
5. **Timbre and acoustic overlap:** verify SFZ one-shot semantics, voice stealing, note-offs, round robin, velocity layers and Muldjord microphone/room/overhead layers. Keep overlapping tails. Compare source-vs-render envelopes, and avoid trimming audio at the nominal MIDI note length. Some low ominous effects may require tuning, pitch-shifted samples, transient reshaping, filtered distortion, layered sub impacts and substantial room processing; make these opt-in, reversible, scoped effects.
6. **Build reviewable A/B production transforms:** section-level low-impact layering, saturation, distortion, EQ, parallel compression, room reverb and stereo effects, honoring existing Song Harbor automation. One combined stereo stem with reversible source volume mask and no source mutation. Show reviewable per-lane/per-section note and effect changes before acceptance.
7. **LLM directions only after controlled primitives exist**, e.g. `Preserve the deep ominous crash tails, make kick heavier, darken cymbal timbre, retain natural room decay, don't brighten the hits`. LLM produces reviewable edits, not direct destructive mutations.

Acceptance gate: the rendered crash must preserve the source's **low-register weight, overlapping messy/booming tail and ominous emotional impression** at level-matched playback, or the source texture remains layered in the mix. A technically cleaner result is not necessarily better.

## Pause/release boundary

- Experimental DEV drum replacement is **not ready for release** and must not be merged to production `main`.
- Next immediate focus is Infra Choir's **next scheduled track release using established Song Harbor production workflow** on `main`, with the existing accepted mix/assets. Preserve the locked YouTube credit block; only add Muldjord sample attribution if the released master actually contains Muldjord samples.
- No experimental re-extraction, library switching, or mastering changes should be silently applied to the imminent production track.
- Resume DEV from this handoff and the related drum plan after the release is handled.

## Validation/technical note

Last reported CI: targeted drum/transcription and SFZ tests passed; some GitHub backend suites still showed an unrelated section-production parser test failure. User confirms Windows DEV **build** clean; do not upgrade that to comprehensive CI or sound-signoff.

Key paths: `app/backend/drum_transcription.py`, `polyphonic_midi.py`, `sfz_pack.py`, `sfz_candidate_audio.py`, `midi_candidate_level.py`, `app/frontend/src/MidiPianoRoll.tsx`, `BassMidiTool.tsx`, `docs/dev-drum-specific-transcription-2026-11-05.md`.
