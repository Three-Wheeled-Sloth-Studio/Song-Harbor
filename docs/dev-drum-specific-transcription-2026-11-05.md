# DEV first slice: drum-specific MIDI extraction and editable groove

Date: 2026-11-05
Branch: dev only; keep main unchanged.
Status: **PAUSED for the next Infra Choir production release.** Windows DEV build reported clean; Muldjord sounds fuller but is not production-ready. Critical unresolved defect: deep, boomy, messy crashes in the source become higher, crisp, thin and mechanical after transcription/render, losing their ominous character. Do not merge into `main`. Resume using `refs/handoffs/dev-muldjord-drum-tone-pause-2026-11-05.md`.

## User-reported problems
- Old Extract used monophonic harmonic/pitched-note estimation even for Drums.
- Generated SFZ drum replacements sounded overly like MIDI, lacking energy, especially kick relative to snare.
- Prior volume lift helped overall output gain but not kit balance/realistic performance.

## First slice implemented
- `app/backend/drum_transcription.py`: bounded CPU transient detector (12kHz mono, 512-sample FFT, 128-sample hop, 20s chunks with edge overlap), provisional low/mid/high spectral classification into MIDI lanes 36 (kick), 38 (snare), 42 (closed hat). Maintains extracted, non-quantized onset timing and bounded attack-derived velocities. This is **not a model trained to separate overlapping drum hits**; many events will need correction, and toms/cymbals are not yet classified.
- `POST /api/projects/{id}/drum-midi/analyze`: validates selected stem and extraction span; creates new saved arrangement with MIDI channel 10 and an explicit **custom, provisional** mapping. Does not alter source stem.
- Drums `Extract` in Stem Tools calls this path, directly opens the saved arrangement in MIDI Piano Roll. Other stems retain existing pitched extraction.
- `Kick-forward accents` button in the piano roll applies a reversible, previewable note velocity modification on the current drum map: labeled kick +18, labeled snare -8, hat accents +5/-5. Undo works; saving and re-rendering required before audio changes. MIDI velocities are not dB and do not remap SFZ note pitches.
- `test_drum_transcription.py` validates silence, separated synthetic attacks, finite inputs; included in CI along with `test_midi_candidate_level.py`.

## Known limitations and QA gates
1. Classification is coarse; preserve actual times, no forced quantization. Verify low kick and snare onset recall in a real short drum excerpt. Overlapping kick+snare may be represented as just one hit. Tune or replace model based on measured confusion, not automatic assumptions.
2. **Big Rusty 01-full SFZ note pitch mapping is not verified.** The provisional 36/38/42 lane numbers must be auditioned, edited, and relabeled using actual kit note assignments before believing the render. Editing a label does not remap a pitch; move MIDI notes to the verified pitch. Do not silently treat GM as SFZ.
3. Full kit fills, toms, crash, ride, ghost hits, round robin, expressive CC and frequency-band/per-lane gain remain open. Some sample-engine features depend on the SFZ itself.
4. The button is an explicit deterministic gesture, not an LLM. Current natural-language `proposal-direction` selects presets; it is **not a generative drum arranger**. Next tranche should add provider-neutral drum note proposal schema, per-lane mix adjustments, section-aware intensity and reviewable diff.
5. New MIDI candidate auto-leveler only changes headroom, not perceived loudness or realism. Do not use repeated normalized render to hide sample/mapping defects.
6. QA: On Drums, choose a 5-15 second region with discrete kick/snare/hat. Extract, inspect grid (Drums checked; custom lanes shown), audition the kit notes/verify mapping, apply Kick-forward accents and undo, save revision, render, A/B with original. Check same groove at chorus and re-open saved arrangement. Ensure no source mutation and mono/stereo alignment.
7. No production promotion until timing, kit mappings and real audio render pass QA. Treat this as a first practical candidate, not a finished commercial drum transcription model.

## Follow-up sequence
A. Expose verified actual SFZ kit pitches and drum articulations through an inspectable keymap/audition UI (instead of assuming GM).
B. Add reliable multi-label transient model and onset confidence/edits for kick, snare, hat, toms, ride and crash; compare to manual labeled events.
C. Create editable groove transforms (kick-forward, hats, ghost notes, fills, humanization) with bounded, reversible, section-aware operations and note-diff preview.
D. Expose the above through an explicit natural-language plan adapter. Render audition and A/B acceptance remain mandatory.

Backend test suite may show unrelated existing failures in `test_polyphonic_midi.py` (undefined test variable) and `test_section_production.py` (brace parsing); npm Git dependency install has intermittently failed. Check the latest CI revision and do not misrepresent it as passing.

## 2026-11-05 follow-up: realism is a non-negotiable production requirement

User feedback: the new drum render is closer to usable, but still too MIDI-like and thin. Long-term support for acoustic overlap, natural performance/sample variation, sample diversity, expressive percussion transcription, and production processing is explicitly in scope, not optional polish.

### Sequenced acceptance criteria

1. **Acoustic resonance and note tails:** Separate MIDI note gates from one-shot sample decay. Preserve cymbal/tom/room tails across other hits and fast same-key retriggers where sampler voice behavior supports this. Verify no unexpected voice stealing. Explicit choke only for supported mappings. Test fast kicks, hats, cymbals over snares, tom fills.
2. **Verified kit mappings:** Read each SFZ program and verify actual playable pitches, velocity layers, alternate articulations, round-robin/randomization, hi-hat control and chokes. SFZ pitch 36 is not automatically a kick. Give users a kit note audition and correct mappings before comparing renders.
3. **Sample/performance variation:** Verify sampler opcodes for multi-sampling, velocity layers and round robin. Humanize with groove-informed accents and timing only when requested; keep exact timing as default, and all proposed edits revisioned, scoped, audible, reversible.
4. **Richer transcription:** Current speculative kick/snare/closed-hat spectral classifier is insufficient. Introduce overlapping/multi-label detection of kick, snare, hat articulations, tom, ride, crash and fills, with confidence/provenance and a manually corrected ground-truth comparison.
5. **Acoustic-to-industrial processing:** Build kit-group workflow including close microphones, overhead/room, bleed, stereo panorama, phase-safe multi-mic layering, transient shaping, EQ, saturation, distortion, parallel compression and room reverb. Preserve current source-mask/preview/export parity and end with one combined stereo drum stem.
6. **Natural language:** Add provider-neutral bounded note/lane/section production proposals with before/after diff and human approval. Current direction matching only selects presets and is not an expressive drum arranger.

### Muldjord SFZ library and large archive compatibility

The previously enforced upload limit was 768 MiB zipped and 1.5 GiB unpacked. DEV now accepts ZIP up to 4 GiB and declared unpacked payload up to 8 GiB with a 512 MiB free-space reserve, keeping path traversal, duplicate paths, file counts, file-type whitelists, and exact references validated. A browser-side preflight rejects ZIP files above 4 GiB before upload.

The SFZ Instruments Muldjord port is listed around 347 MB, whereas the original DrumGizmo kit is a different multi-microphone distribution. A larger downloaded file might not be the expected SFZ release. The FreePats stereo Muldjord FLAC SFZ is listed as 157 MiB but its official download uses 7z rather than the currently supported ZIP. Do not pretend a 7z archive is a ZIP or that the full DrumGizmo source is one compatible SFZ program.

Big Rusty remains the QA baseline. Compare the same MIDI score and measured render level against one compatible Muldjord SFZ program. If the kit consists of microphone-specific SFZ definitions, rendering one may sound thin because it is only one microphone, not a full kit mix; plan grouped simultaneous program rendering.

QA required: Windows upload of large ZIP, safe rejection of malformed archives, instrument listing, verified SFZ note mapping, real audio tails and velocity behavior, disk space, side effects and restoration.

Sources: https://sfzinstruments.github.io/drums/muldjord_kit/ ; https://github.com/sfzinstruments/DrumGizmo.MuldjordKit ; https://freepats.zenvoid.org/Percussion/acoustic-drum-kit.html

## 2026-11-05: Muldjord SFZ text-fragment import fix and release attribution

User attempted the approximately 338 MB `DrumGizmo.MuldjordKit-master.zip` SFZ conversion and received: `SFZ pack contains no complete instrument programs: Ambience left: SFZ references a missing or external include: ../Data/keymap.txt`.

Verified directly against `sfzinstruments/DrumGizmo.MuldjordKit` master: `Stereo/DrumGizmo MuldjordKit.sfz` and `Multi/Ambience left.sfz` explicitly include `../Data/keymap.txt`, `macro.txt`, `control/*.txt`, and many `Data/stereo/*.txt` or `Data/multi/*.txt` fragments. `Data/macro.txt` uses `#define $sample_dir ../Samples`, `#define $ext flac`, `default_path=$sample_dir/`, and inline multiple `#define`s. Region fragments build exact paths such as `$instr/1-$instr-$mic.$ext`, and the stereo program has multiple `#include` directives on one line. These are legitimate SFZ 2.0 include conventions, not a missing or external sample.

DEV `app/backend/sfz_pack.py` now retains bounded `.txt` SFZ include fragments (data-only, never executed), scans include/define directives anywhere within a line, follows nested pack-contained references, expands macros for sample path validation in order, and limits include recursion/visits and total referenced samples per program. It preserves current ZIP path, sample, size, and unresolved dependency safeguards. Coverage added to `app/backend/tests/test_sfz_pack.py` for Muldjord-style include/macros, missing samples, and traversal denial.

CI: new SFZ tests passed in workflow `42103474987`; the overall backend workflow still fails in the pre-existing `test_section_production` parser test. Live Windows import and sfizz sound output have not yet been verified; next step is retry importing the same ~338 MB SFZ ZIP, identify the `Stereo/DrumGizmo MuldjordKit` program, map pitches, and audition. The full multi microphone programs are not a default stereo mixed kit.

**Attribution:** User confirms all releases using Muldjord sample material will include the license-required attribution. Preserve creator/license/source/version alongside imported sample pack metadata and in release preparation. Do not automatically alter the existing Infra Choir standard credit block without user approval; add an appropriate separate samples credit when applicable.

Source: https://github.com/sfzinstruments/DrumGizmo.MuldjordKit

## 2026-11-05 Muldjord audio QA and expanded lane exploration

User confirmed Muldjord imports cleanly, rendered candidate loudness is appropriate, and the kit is fuller and generally sounds better than Big Rusty. Still somewhat artificial and thin, with under-represented deep-register hits and overly crisp isolated attacks. Existing extracted score screenshot showed 565 MIDI notes, mostly estimated Kick/Snare, with Closed hat as the only other named lane. This is a transcription limitation, not evidence that the Muldjord samples lack those kit pieces.

Implemented on DEV:
- The new conservative spectral drum classifier separates five attack bands, uses local onset novelty, and proposes kick (36), snare (38), closed hat (42), low tom (41), and crash (49) hypotheses, with occasional simultaneous kick/snare or bright/snare event estimates if both attack components are strong. No forced quantization or edited source PCM. All classifications remain exploratory; no measured recall or precision on real song yet.
- MIDI piano roll displays only mapped drum lanes plus any unmapped notes (rather than 54 empty semitone rows), and up/down note nudges move among those visible lanes. Melodic piano roll retains its full chromatic view.
- When selected SFZ instrument is `DrumGizmo MuldjordKit`, a `Muldjord map` button loads verified publisher note assignments from Data/keymap.txt. Includes two kicks, snare/rimstick, closed/open hats, four toms, two crashes, china, rides/tips/bells. Does not create, transpose or reclassify notes and requires Save for persistence. It does not include choke-control notes as playable drums.
- Earlier extracted score stays unchanged; users must explicitly Extract again to create a new versioned arrangement and compare it with their previously saved production score. The newly provided map is an editable label mapping, not a drum-hit classifier or sample import.

Important unresolved design: Accurate overlapping drum transcription and actual frequency-band separation require source evaluation and better multi-label detection, likely trained model or reference-driven template matching. Preserve sample one-shot tails and apply naturally recorded room/overhead layers. The Muldjord source includes loop_mode=one_shot and sample round-robin sequences, but actual sfizz interpretation and acoustic tail carryover require Windows listen tests. Renderer may still impose voice/group settings. Do not claim this is solved by MIDI label additions.

QA after DEV update: (1) open old saved score to ensure it is unchanged; (2) Extract a new short passage, inspect five estimated lanes and ensure notes remain editable; (3) select the stereo DrumGizmo MuldjordKit program and click Muldjord map, verify names including 35/36, 37/38, 41/45/47/48, 42/46, 49/57, 51/59 and 52; (4) save then render and compare. Check same-pitch retriggers and audible cymbal tails; (5) classify a manually identified kick/snare/cymbal passage for objective errors before changing thresholds.

Release attribution remains required when Muldjord sampled material is used.
