# Multi-track song import acceptance (2026-10-22)

## New user-facing flow

Import song > **Multiple tracks · already separated**.
Select 2-12 audio files. Song Harbor guesses a title from common filename prefix, provides editable song title before import, preserves original uploads, creates aligned 48-kHz stereo WAV working tracks, pads shorter tracks with silence, and opens the standard mixer/timeline/Library project after the background conversion finishes.

One recording > **Single recording · separate stems** is unchanged.

## Core validation

1. Select e.g. `Salt in the Circuit - Vocals.wav`, `Salt in the Circuit - Drums.wav`, `Salt in the Circuit - Bass.wav`. Confirm title suggestion is `Salt in the Circuit`.
2. Override title with `Salt - Test Mix`; import. Confirm title appears in song header and Library, and persists after relaunch.
3. Check standard stem aliases are inferred even from `MySong_(Vocals)_htdemucs_6s.wav`, and labels show source track names. Additional unrecognized or repeated roles should become independent TrackNN labels rather than overwrite an existing track.
4. Select 2 tracks, then 6, then 10-12; ensure the first and last persist, save their mixer levels, export WAV, reopen Library, and create DAW exchange. All tracks must remain separate and synchronized.
5. Use tracks of different duration. Confirm all start at 0:00 and the shorter files are silent at the end, without stretching or artificial BPM alignment. Song Harbor does **not** auto-align arbitrary off-time performances.
6. Confirm original files under `jobs/<id>/originals` are byte-for-byte unchanged. Working WAVs are created under `jobs/<id>/stems`. No Demucs invocation for this path. Conversion requires local FFmpeg/FFprobe.
7. Test bad input cases: 1 file, more than 12, unsupported extension, two identical filenames, empty file, over-size files (>1 GiB each, >2 GiB per batch), missing FFmpeg, corrupt media, duration >15 minutes, and conversion failure. The job should show a useful error and must not appear as a finished Library song.
8. Confirm the import remains local (no remote upload). Large albums may take time to convert; processing progress should be visible without freezing UI.

## Current limits

- Per-track start offsets, manual stem role assignment, true multichannel import, sample-rate-preserving audio, and time alignment/sync of unsynchronized takes are **not** implemented.
- Section production grammar still recognizes the original six canonical stem names. Additional TrackNN parts are available to mixer level/mute/solo/export but not addressable in section effects scripts yet.
- Testing on an actual Windows installation with real converted audio is outstanding. CI validates route/model helper behavior and the current frontend build, not audio listening QA.

## Code

- `app/backend/stem_import.py`: filename inference and alias assignment.
- `app/backend/server.py`: multipart local import endpoint and background conversion.
- `app/backend/projects.py`, `library.py`: durable variable-track projects and Library/DAW adoption.
- `app/frontend/src/main.tsx`, `StemMixer.tsx`: import option, suggested editable title, preserved original track labels.
- `app/backend/tests/test_stem_import.py`: route, metadata and project persistence tests.

Keep `docs/user-guide.md` and `app/frontend/src/HelpDialog.tsx` aligned as this evolves.
