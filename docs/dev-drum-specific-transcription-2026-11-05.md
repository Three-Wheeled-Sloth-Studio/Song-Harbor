# DEV first slice: drum-specific MIDI extraction and editable groove

Date: 2026-11-05
Branch: dev only; keep main unchanged.
Status: Implemented POC; requires local Windows auditory QA.

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
