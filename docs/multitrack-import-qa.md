# Multi-track song import acceptance (2026-10-22)

## Manifest-aware reimport and arbitrary named stems update

**Required for the next user QA:** On Import > Multiple tracks, select all 12 mono channel WAVs **and** the exact `manifest.json` emitted by Song Harbor’s `Split stereo channels` export. The application groups the manifest-defined six Left/Right pairs into six stereo working parents and restores active L/R child routing, instead of interpreting them as 12 unrelated instruments. Verify `GET /api/projects/<id>/channels` returns six active entries; toggle one source to Stereo and back to L/R, play and WAV-export in both modes, then reopen from Library and recheck routing. Incorrect or missing paired channels must fail with clear errors; never guess a pair and never silently discard a channel. The parent/child files stay local and the originals remain intact.

**Scalability and script aliases:** Import accepts 2–64 standalone files or 2–128 mono files plus a supported manifest (up to 64 parent stems). Test 16 and 33 uniquely named tracks in the project and use the displayed sanitized alias, e.g. `Synth_32.pan:right.60@2s:smooth`, and EQ in a section sheet. Test multiple arbitrary aliases in the same section, round-trip export/re-import, and DAW handoff. Preserve `track_id` and working filename independent of display name. A later rename UI must atomically migrate stored production directives/references, not merely repaint the label. Current shared-clock browser audition is capped at 768 MiB decoded audio; record memory-limit errors for long projects rather than pretending full dozens-of-tracks playback is validated.



## New user-facing flow

Import song > **Multiple tracks · already separated**.
Select 2-64 audio files. Song Harbor guesses a title from common filename prefix, provides editable song title before import, preserves original uploads, creates aligned 48-kHz stereo WAV working tracks, pads shorter tracks with silence, and opens the standard mixer/timeline/Library project after the background conversion finishes.

One recording > **Single recording · separate stems** is unchanged.

## Core validation

1. Select e.g. `Salt in the Circuit - Vocals.wav`, `Salt in the Circuit - Drums.wav`, `Salt in the Circuit - Bass.wav`. Confirm title suggestion is `Salt in the Circuit`.
2. Override title with `Salt - Test Mix`; import. Confirm title appears in song header and Library, and persists after relaunch.
3. Check standard stem aliases are inferred even from `MySong_(Vocals)_htdemucs_6s.wav`, and labels show source track names. Additional unrecognized or repeated roles should become independent sanitized script-safe names (or TrackNN fallback) rather than overwrite an existing track.
4. Select 2 tracks, then 6, then 16-33; ensure the first and last persist, save their mixer levels, export WAV, reopen Library, and create DAW exchange. All tracks must remain separate and synchronized.
5. Use tracks of different duration. Confirm all start at 0:00 and the shorter files are silent at the end, without stretching or artificial BPM alignment. Song Harbor does **not** auto-align arbitrary off-time performances.
6. Confirm original files under `jobs/<id>/originals` are byte-for-byte unchanged. Working WAVs are created under `jobs/<id>/stems`. No Demucs invocation for this path. Conversion requires local FFmpeg/FFprobe.
7. Test bad input cases: 1 file, more than 64, unsupported extension, two identical filenames, empty file, over-size files (>1 GiB each, >16 GiB per batch), missing FFmpeg, corrupt media, duration >15 minutes, and conversion failure. The job should show a useful error and must not appear as a finished Library song.
8. Confirm the import remains local (no remote upload). Large albums may take time to convert; processing progress should be visible without freezing UI.

## Current limits

- Per-track start offsets, manual stem role assignment, true multichannel import, sample-rate-preserving audio, and time alignment/sync of unsynchronized takes are **not** implemented.
- Section production grammar now accepts arbitrary project aliases for imported names, based on the stable working file mapping. Full rename/migration UI remains unimplemented.
- Testing on an actual Windows installation with real converted audio is outstanding. CI validates route/model helper behavior and the current frontend build, not audio listening QA.

## Code

- `app/backend/stem_import.py`: filename inference and alias assignment.
- `app/backend/server.py`: multipart local import endpoint and background conversion.
- `app/backend/projects.py`, `library.py`: durable variable-track projects and Library/DAW adoption.
- `app/frontend/src/main.tsx`, `StemMixer.tsx`: import option, suggested editable title, preserved original track labels.
- `app/backend/tests/test_stem_import.py`: route, metadata and project persistence tests.

Keep `docs/user-guide.md` and `app/frontend/src/HelpDialog.tsx` aligned as this evolves.
