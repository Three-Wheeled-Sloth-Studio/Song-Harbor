# Bass-to-MIDI / bowed-string prototype (Blackwater Firmware)

**Status:** first-pass implementation committed directly to `main`; Windows/local listening QA pending. This is not a validated cello instrument or a full polyphonic transcriber.

## User goal
Extract Blackwater Firmware's existing Bass stem into editable MIDI notes, optionally modify the melody, and audition a bass-cello style arrangement without losing the original Bass. Follow **easy to do, easy to undo**.

## Entry and workflow
1. Update normal `main` launcher and open Blackwater Firmware.
2. From the right Tools rail, open **♮ Bass to MIDI / cello**.
3. Choose **Custom range**, preferably a clear 10–20s bass passage; start at the playhead if convenient. Existing section ranges can also be selected, but max region length is 45 seconds.
4. **Extract bass notes (CPU)** reads only the original separated Bass working WAV. It uses a bounded 12-kHz mono FFmpeg decode and a local harmonic pitch estimate (no ML model, no GPU). Notes are restricted to MIDI 28–76 and monophonic.
5. Edit note pitches, start/end seconds, remove/add notes or transpose an octave. **Revert edits** returns to the first extracted result.
6. **Render bowed-string candidate** creates a new isolated PCM WAV and General MIDI file. It uses an original additive bow-like tone, **not** a sampled acoustic cello. **Solo candidate** or **A/B with song** uses the existing candidate-preview player.
7. **Export .mid** saves the corrected note sequence for use with a proper cello sample library/DAW. **Accept as NEW track** imports the non-destructive bowed candidate as `BassCello` at the excerpt's original start timestamp. Original Bass stays intact; mute it to compare replacement.
8. To undo accepted audio, remove the imported bowed-bass track using existing track actions. To undo note edits before acceptance, use **Revert edits**. No original WAV or source stem is overwritten.

## Important limitations
- The built-in bowed tone tests timing/phrasing only. An actual cello sound will require a user-provided properly licensed SoundFont/sample library/VST or another rendering engine. Do not advertise this as acoustic cello.
- No piano-roll visualization yet; compact editable note list is the first pass.
- Pitches, onsets, durations, velocity (fixed estimated 85), rests and octave selection may be wrong, especially with bass distortion, bleed, double stops or very low fundamentals.
- Only monophonic melody is supported. Notes cannot overlap, and maximum is 320 notes/45 seconds.
- MIDI output is standard type-0, tempo 120 BPM, cello program 43 (one-based), times expressed relative to selected excerpt start. No automatic beat quantization, tempo detection or expression curves. Import it into a DAW aligned to the excerpt's song position.
- Candidate metadata/exports are stored under `jobs/<id>/generated/bass-midi/<candidate-id>` and are separate from original stems. For the current first pass, existing candidates are on disk but not re-listed in the UI after relaunch.
- Existing original Bass routing and mix effects are not overwritten. The extracted source is the original Bass working WAV, not any live mixer processing or split-channel effects.

## Safety
- Bounded CPU-only operation and FFmpeg decode timeout. No ACE/LLM process involved. No downloads or network.
- The backend validates note range, non-overlap, audio duration and candidate ID. Imported playback uses the existing clip import/undo semantics.
- The dedicated NumPy dependency is declared in backend requirements; existing audio-separator environments generally already include NumPy.

## QA handoff
- `python -m unittest discover -s app/backend/tests -p 'test_bass_midi.py' -v`
- `python -m py_compile app/backend/bass_midi.py app/backend/server.py`
- `cd app/frontend && npm run build`
- On Windows verify FFT note accuracy versus actual Bass, regional start alignment, silence gaps, note boundaries, render length, shared-clock audition, MIDI file import into DAW, re-import to Song Harbor, mute source, remove imported candidate, and original stem checksum unchanged.
- Inspect 100% CPU, memory and GPU behavior; no GPU usage is expected.
- Review sound quality separately. Move to high-quality cello SF2/VST preview **after** timing/pitch and reversible workflow pass acceptance.


## Product direction confirmed after Blackwater Firmware listening QA

The user reports that the experimental bass-to-bowed-cello treatment **sounds really good and moves the mix in the intended direction**. Treat this as subjective musical acceptance of the experiment, **not** an accuracy benchmark or approval of the temporary synth as a production cello.

**Do not proliferate instrument-pair tools.** The current **Bass to MIDI / cello** entry is a temporary proof-of-concept. Its replacement must be two reusable operations:

1. **Stem → MIDI** from any eligible stem. Transcription strategy depends on the audio (monophonic pitched, polyphonic, percussion, vocals), with explicit confidence/limitations, editable timing/pitch, and non-destructive export.
2. **MIDI → Reinstrument** from generated or imported MIDI. Select and audition an instrument source (synth/SoundFont/sampler/plugin), edit notes independently, render to a new candidate audio track, compare A/B, and accept/remove without overwriting the original.

**Stem-label interaction is the canonical entry point.** Labels in the mixer/timeline should be clickable/focusable controls opening stem-specific tools, including transcription, separation, cleanup, effects and routing. Avoid growing a permanent right-hand sidebar entry for every source/instrument combination. Preserve access through ordinary keyboard navigation and keep timeline width available.

The MIDI intermediate representation should persist independently of the source stem, with a provenance link to the original source/region and editable revisions. The original stem and candidate must coexist; undo should require no regeneration. Follow the product's established **easy to do, easy to undo** principle.

**Next implementation slices (not implemented here):** reusable stem selector/track contextual actions, decoupled MIDI extraction artifact, general MIDI editing, instrument registry/render backend, source vs candidate audition, and removal of the experiment-specific tool label after general workflow is available.

Remain on **main** for normal Song Harbor development. Reserve `dev` for explicitly designated high-risk implementation experiments only.

## 2026-10-29 follow-on: Generic Stem → MIDI entry point (main)

- **Interactive mixer stem labels:** click or keyboard-activate a stem's icon/name to reveal scoped tools: **Stem → MIDI**, Rename and Sound cleanup. Mute/Solo remain separate controls; the wider waveform stays intact.
- **Generic source:** the MIDI tool receives a stable `track_id` from the selected label and offers an explicit source-stem selector. Backend uses selected working WAV and handles local offsets of imported clips, not just a hard-coded Bass stem.
- **Separate MIDI step:** edit notes, then **Save / Export MIDI** without rendering a replacement instrument. Editing the MIDI invalidates any previous instrument preview; rerender before accepting.
- **Reinstrument step:** currently offers the one experimental bowed-string synth. Additional renderers and generic MIDI file import remain future work.
- **Safety:** the source stem remains immutable; the new track is optional and removable; MIDI candidate files stay within the song's generated folder. Existing bass-to-cello experiment is preserved, not migrated.
- **QA outstanding:** local Windows frontend build, UI interaction and focus, selection persistence, audio/MIDI comparison, imported clip alignment, user listening, and integration regressions.

This is the first architecture slice, **not** a claim of robust transcription for drum/polyphonic/vocal/mixed stems. Avoid adding instrument-pair buttons as permanent sidebar tools.

## Compact stem-tools UX revision (2026-10-29)

- **Stem tools** is a compact resizable floating hub, not a permanent Bass-to-Cello feature. Interactive mixer stem labels open the hub; the tool rail remains a secondary entry point.
- Function selector: **Mix** and **MIDI**. Only the selected function's controls are displayed. Mix immediately exposes the existing live base gain %, Mute, Solo and Reset controls. Changes follow the existing song-save behavior. MIDI's extraction, note editor, renderer and audition controls are hidden until MIDI is selected. Notes remain collapsed until requested.
- Region presets under MIDI: **Whole song**, **From section → To section** (inclusive endpoints), or **Custom** position/length, with Start-at-playhead. Region validation considers the selected stem's playable clip, not just total song length.
- Long transcriptions: backend decodes and analyzes bounded 30-second chunks; maximum aggregate region length is **600 seconds** and 4000 estimated note events. The original <=45s path remains unchanged. Long renders remain separate; do not assume acoustic-cello timbre or accurate polyphony. Transcription is CPU-only and synchronous during this prototype.
- **Global stem effects future contract**: expand Mix into a compact base-effects rack supporting Gain, Pan, Width, Reverb, Early reflections, EQ, Compression, Ducking and De-essing where applicable. This is the *base layer* that section scripts override/inherit, not a competing automation system. Do not display inert controls for unimplemented effects. Keep per-effect reset, A/B and script override visibility. Allow the same effect logic to be reused by per-section scripting without duplicated DSP implementations.
- QA: normal launcher / main; check accessibility/keyboard focus, popover width after large resizes, selection change, direct MIDI/preview, inclusive section ranges, full-song runtime and CPU load, state invalidation, combined candidate placement, source untouched, and no disruption to prior Blackwater Firmware test.
