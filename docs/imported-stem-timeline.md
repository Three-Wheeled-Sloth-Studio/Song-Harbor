# Imported stem timeline QA

Validated on 2026-10-23 against `Call of the Electric Siren` (`586a03b40c9c`) and the existing CelloPOC audio.

## Root cause and recovery

The import route converted every added file into a song-length WAV with silence appended at the end. The browser then decoded each import as another full-length stereo buffer. The six 341.36-second stems already use about 750 MiB of the 768 MiB audition budget, so either cello import could make synchronized playback preparation fail.

The two cello rows were separate imports, not an internal duplication of one request:

- `CelloPOC` used the previously padded full-song file.
- `cello-prechorus1` used the short cleaned passage and was padded from 0:00 by the old importer.

Both were removed through the guarded imported-track endpoint. Their working and uploaded project copies remain recoverable under `data/jobs/586a03b40c9c/trash/`; the six separated stems, 13 sections, and production automation remain in the project.

## Implemented behavior

- Imported audio is normalized to 48 kHz stereo 24-bit PCM but is no longer padded.
- Each imported track stores `start_seconds`, `duration_seconds`, `imported`, and a SHA-256 content fingerprint.
- The import UI accepts song start, a saved section boundary, or a custom timestamp.
- Imported rows expose reposition and remove actions. Removal requires confirmation and archives the project copies. Original separated stems cannot be repositioned or removed through these endpoints.
- Shared-clock playback schedules short buffers at their timeline offsets and skips clips that have already ended when seeking.
- Waveforms, offline browser export, FFmpeg mix export, DAW exchange metadata, source diagnostics, and section analysis account for clip offsets.
- A matching content fingerprint at the same timestamp is rejected with HTTP 409. The same audio at a different timestamp remains an intentional, valid import.

## CelloPOC validation

The cleaned CelloPOC passage was imported at `71.719` seconds:

- stored clip duration: `10.683` seconds (not `341.36` seconds)
- waveform placement: `71.719` seconds
- reposition round trip: `71.719` -> `137.906` -> `71.719`
- byte-range streaming: HTTP 206
- same audio/same position duplicate: HTTP 409
- seven-track FFmpeg mix duration: `341.36` seconds

The QA import and generated test mix were removed afterward. The live project finished with six manifest files, six source-track identities, zero imported tracks, and all six stem files present.

Frontend type-check/Vite build passes. Fifteen focused backend lifecycle, routing, mix-validation, and stem-import tests pass. The broader suite still reports unrelated Windows SQLite cleanup-handle errors and an existing lyric escape assertion. A browser click/listen smoke test was not available from the automation surface and should be performed once in the visible Song Harbor window.
