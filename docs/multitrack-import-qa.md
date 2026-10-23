# Multi-track song import acceptance (2026-10-22)

## Manifest-aware reimport and arbitrary named stems update

**Required for the next user QA:** On Import > Multiple tracks, select all 12 mono channel WAVs **and** the exact `manifest.json` emitted by Song Harbor’s `Split stereo channels` export. The application groups the manifest-defined six Left/Right pairs into six stereo working parents and restores active L/R child routing, instead of interpreting them as 12 unrelated instruments. Verify `GET /api/projects/<id>/channels` returns six active entries; toggle one source to Stereo and back to L/R, play and WAV-export in both modes, then reopen from Library and recheck routing. Incorrect or missing paired channels must fail with clear errors; never guess a pair and never silently discard a channel. The parent/child files stay local and the originals remain intact.

**Scalability and script aliases:** Import accepts 2–64 standalone files or 2–128 mono files plus a supported manifest (up to 64 parent stems). Test 16 and 33 uniquely named tracks in the project and use the displayed sanitized alias, e.g. `Synth_32.pan:right.60@2s:smooth`, and EQ in a section sheet. Test multiple arbitrary aliases in the same section, round-trip export/re-import, and DAW handoff. Preserve `track_id` and working filename independent of display name. The new rename UI must atomically migrate stored production directives/references, not merely repaint the label; Windows QA is pending. Current shared-clock browser audition is capped at 768 MiB decoded audio; record memory-limit errors for long projects rather than pretending full dozens-of-tracks playback is validated.



## Second implementation slice: persistent identity, rename and add-track (2026-10-22)

**Code implemented, real Windows audio acceptance still pending.**

- Every project exposes durable `track_id` via `GET /api/projects/{id}/tracks`.
  Legacy six-stem projects receive metadata backfill with stable IDs;
  source WAV files are not renamed or overwritten.
- Source aliases and display names live separately from immutable
  `working_filename`. All section script materializers now resolve the
  project mapping rather than assuming alias is embedded in the filename.
- Mixer offers a pencil action on each stem. Renaming verifies the previously
  loaded alias to reject stale edits, rejects reserved/colliding/invalid aliases,
  rewrites structured production directives and spatial proposals, and
  revalidates/rematerializes saved pan, gain, EQ, reverb, width, space, dynamics,
  auto-pan and ending before one atomic manifest replacement. Lyrics remain
  unchanged. The renamed identity follows DAW exchange exports.
- Mixer offers **+ Add stem** for audio already prepared externally. Its
  `POST /api/projects/{id}/tracks/add` path saves the untouched uploaded
  source under originals, converts to a stereo 48 kHz working WAV, pads shorter
  inputs to the existing song duration without extending it, assigns a new
  permanent ID and editable alias, and adds neutral mixer settings. Longer
  sources are rejected rather than silently truncated. Conversion failures
  remove staging files and leave the original project manifest unchanged.
- The mixer saves currently staged faders before a successful add/rename and
  reloads the project and audio engine to include the resulting changes.
  Whole Song Section Text must be closed first; apply or discard its draft.
- Regressions: `test_track_lifecycle.py` verifies all-effects rename,
  alias validation, preserved source filenames/IDs and legacy identity
  backfill. Backend CI and frontend typecheck are necessary but do not prove
  the audio conversion path on the user's Windows host.

### Local acceptance script

Full 13-section fixture for the *Logo and the Maw* add/rename trial: `docs/qa-the-logo-and-the-maw-stem-lifecycle.txt`. It adds bridge-local `Cello_Accent.pan`, `Cello_Accent.gain`, and `Cello_Accent.reverb` to the accepted audio treatment. **Only apply this on a test copy with a stem imported under alias `Cello_Accent`**; the source song has no such stem until the user adds one. The renaming action should update every corresponding token to `CounterCello` automatically.

1. Open an existing six-stem project. Rename `Guitar` to
   `Guitar_Lead` (display name `Lead Guitar`). Verify every scripted
   `Guitar.<effect>` becomes `Guitar_Lead.<effect>` and exports still play.
2. Add a short prepared cello WAV. Name it `Cello Accent` with alias
   `Cello_Accent`. Confirm it appears as a separate seventh mixer track,
   with correct alignment and silence padding.
3. Add `{Cello_Accent.pan:right.25@2s:smooth Cello_Accent.gain:+1}`
   to one section while preserving the rest of the whole-song text.
4. Rename `Cello_Accent` to `CounterCello`. Confirm script changes
   automatically, sound remains identical, source filename and permanent
   track ID remain unchanged.
5. Try duplicate `Vocals`, invalid `1Cello` and reserved `auto`.
   All must fail without changing any existing directions or files.
6. Save, close, reopen Library and export mix plus DAW exchange. Both
   should contain the added stem with the updated readable name. Run
   loudness/headroom verification after any substantive gain changes.
7. Repeat with sixteen prepared stems and then a 33-stem short synthetic
   fixture. The 768 MiB browser decode limit is still active: memory
   failures must be explicit, not silent omission.

**Out of scope for this slice:** additive generative creation of a cello,
batch append, 33+ practical-duration browser streaming, automated Ardour
round-trip, or a polished non-modal rename dialog. Current UI uses simple
name/alias prompts until the compact track inspector is designed.

## First implementation slice: six-role effects removal (2026-10-22)

Completed in code:
- Direct section pan/reverb/width/space/EQ handlers now resolve the project's actual sanitized alias list instead of hardcoded `Vocals, Drums, Bass, Guitar, Piano, Other`.
- Reverb materialization, including `all.reverb` and `all.reset`, now also uses actual project track aliases.
- Added a 16-track synthetic script regression with `Synth_01`-`Synth_16`, `all.reverb`, a track override, gain and pan, plus round-trip/reload. CI and real Windows audio acceptance are separate gates.

Still explicitly NOT implemented in this slice: adding a track to an existing
project; editable alias rename with transactional script/automation migration;
track groups; scalable chunked decoding. Those remain the primary next
work items. No claim that a 16-track audio export was auditioned.

## Accepted 16+ stem PI acceptance contract (October 22)

The acceptance target now includes both **initial multitrack import** and
**adding another track to an already saved song**. These are separate flows.
The former is implemented with limits; the latter and transactional renaming
are requirements, not features claimed working today.

### Core user story: add, address, rename

1. Import sixteen uniquely named tracks; keep all sixteen through library
   reopen, scripted pan/gain/EQ/reverb, mute/solo, WAV export and DAW handoff.
   Repeat with at least 33 short tracks as a metadata/control stress fixture.
2. Open the sixteen-track project; add one more aligned cello stem without
   deleting or reimporting any other stem, its cues, its automation or its
   balance. Verify the new track begins at 0, silence-padded where needed,
   with original file hash preserved.
3. Assign distinct **display name** and script-safe **alias** (e.g.
   `Cello_Accent`). Track identity is an immutable `track_id`, separate
   from names, source filename and generated output filename. Save a directive:
   `Cello_Accent.pan:right.22@2s:smooth`.
4. Rename `Cello_Accent` to `CounterCello`. All authored section-script
   tokens, saved parsed directives, unresolved editable drafts where safely
   migratable, UI selectors, and queued/render manifests must refer to the
   new alias. No old alias should silently become a different track.
5. Verify rename persists after project reopen, and the original audio and
   `track_id` remain unchanged. A second distinct cello track must not be
   merged or overwritten. Check all effect kinds, not just pan, including
   EQ, gain, reverb, width, spatial effects, dynamics and reset.
6. Reject invalid aliases, reserved names (`all`, `auto`, `Master`),
   case-insensitive duplicates, in-use file collisions, ambiguous legacy
   directives, and concurrent/stale revisions. Rename must be atomic or
   fully rolled back with a useful error. Do not rewrite lyric prose or
   unrelated quoted words while migrating structured tokens.
7. Renaming while unsaved whole-song script edits exist must prompt to
   apply, discard or cancel, OR correctly migrate the dirty draft without
   loss. Never silently overwrite the draft.
8. Test `all.pan:center` on custom aliases and direct edits through every
   section-effect UI; inspect old six-role materializers and route handlers
   for custom-name assumptions before local acceptance.
9. Measure decoded-audio RAM at 16 tracks of practical song length. The
   current browser shared-clock 768 MiB limit is an intentional guard;
   streaming/segmented decoding or adaptive memory budget is the follow-on.
   Never falsely report a project as fully auditionable beyond that limit.

**Exit gate:** A user can say "add cello to this song", immediately mix the
new track, rename it, see the edited names in ALL script guidance, and export
and reopen without manual token repair.

## Approved future short-clip alignment (not in current import)

Current in-project Add stem aligns audio to song start and physically pads its
48-kHz working WAV. This is transitional and **not** the accepted long-term UX.

When testing the first ACE-Step accompaniment stem, introduce a clip instance
independent of the track, with an immutable imported source and original
duration, a mutable song-relative start offset, and virtual silence around
the actual waveform. Offer Align to selected section as **initial placement**
only; allow continuous free dragging without enforcing section snapping.
Show section boundary snap *suggestions* visually, with exact position and
fine adjustment controls. Retain stable track_id, script alias, and absolute
song-time directives when moving clips. Editing must be reversible; audition,
WAV export, reload and DAW exchange must honor the same offsets. No standalone
alignment acceptance QA until ACE accompaniment provides a useful short stem.

See `docs/second-take-additive-generation.md` for the approved UI behavior.

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
- Section production grammar now accepts arbitrary project aliases for imported names, based on the stable working file mapping. A provisional pencil-triggered rename/migration UI is implemented; local Windows acceptance remains outstanding.
- Testing on an actual Windows installation with real converted audio is outstanding. CI validates route/model helper behavior and the current frontend build, not audio listening QA.

## Code

- `app/backend/stem_import.py`: filename inference and alias assignment.
- `app/backend/server.py`: multipart local import endpoint and background conversion.
- `app/backend/projects.py`, `library.py`: durable variable-track projects and Library/DAW adoption.
- `app/frontend/src/main.tsx`, `StemMixer.tsx`: import option, suggested editable title, preserved original track labels.
- `app/backend/tests/test_stem_import.py`: route, metadata and project persistence tests.

Keep `docs/user-guide.md` and `app/frontend/src/HelpDialog.tsx` aligned as this evolves.
