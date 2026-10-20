# Integrated Production Timeline v1 — implementation checkpoint

**Status (2026-10-20):** code committed on default branch. No confirmed Windows/Predator acceptance run or full TypeScript/backend test pass. Do not present as a finished DAW or sample-accurate transport.

## Delivered in this incremental slice
- The existing `StemMixer` now groups draggable/resizable timed sections, shared-viewport waveform previews and region-loop audition in a compact *Production timeline* panel. 1×/2×/4×/8×/16× timeline zoom, horizontal viewport scroll and click-to-seek work off the same numeric time range. Section drag deltas are scaled to viewport duration; narrow presentation remains non-destructive.
- WAV stem waveform overviews continue to be server-generated/cached; split-channel waveforms use protected `GET /api/projects/{id}/channels/waveform/{parent_file}/{left|right}` and share the parent time origin. Derived child rows align horizontally with parent and section lanes.
- New `track_routing.py` validates channel-split manifests and derived files within a specific song export. The split operation registers the latest selected derived pair in `song-harbor.json`, **active** by default. It stores export-folder *names*, not absolute paths, to survive runtime workspace relocation.
- New endpoints `GET/PUT /api/projects/{id}/channels`, safe per-channel streaming `GET /api/projects/{id}/channels/stream/{stem}/{side}`; UI can toggle between a stereo original and its two derived mono children. Routing persists across reopen. Existing projects without children remain six-stem projects.
- The Web Audio output graph pans decoded mono left children hard left and right children hard right; it never creates the original parent audio player when children are active. Mute/solo/gain remain **parent-level** controls at this stage. Same chosen sources are used for stereo WAV mix export via FFmpeg (direct left/right routing with all other stems). Dedicated regression tests assert exclusive routing, persistence, missing source safety, and optional real FFmpeg L/R PCM roundtrip.
- Region-loop start and stop are marked at current playhead position and enabled on demand; loop repeats in the existing transport.

## Limitations to address next
- **Not sample accurate:** this is a Web Audio processing/output graph fed by independent HTML media elements, still subject to timing drift and 120ms follower correction. AudioContext alone does *not* turn it into one sample-locked transport. AudioWorklet/decoded-buffer shared clock or a native backend/audio engine needs a dedicated design and validation, especially before tight phase/null A/B and mastering exports.
- Region looping is seek-based, not gapless, not saved across sessions, and not yet a drag-to-select region gesture. Zoom is an overview SVG viewport: it enlarges the same 2048-bin peak cache rather than requesting higher-resolution peaks at larger zoom. Later generate a multiresolution waveform pyramid.
- L/R child controls are not independently adjustable yet; parent gain/mute/solo apply to the pair. Introduce child pan/gain and more general buses only with preview/export parity. No per-stem EQ or effect automation built.
- The section lane and waveforms are within one panel sharing viewport/time mapping, but section tagging remains in a distinct HTML row; not yet a single composited draggable clip-editing canvas.
- Channel routing only registers newly split exports, not all historical exports; older saved export folders require re-splitting to attach through current UI. Original media and older export folders are not modified.
- UI/TS build, Windows FFmpeg behavior, streaming and sound level parity unverified. Regression tests were added but not executed by the available GitHub connector (no CI check reported).
- Music production DSL is a separate nonexecuting proposal compiler; still no automated audio effects.

## Windows verification checklist (before claiming acceptance)
1. Relaunch on existing song, verify no TS build error and six displayed waveforms.
2. At 1× and 8× zoom, seek and drag a section boundary, save/reopen, verify timestamp precision and alignment.
3. Split Vocals L/R, confirm two child waveform rows and L/R active status; play and verify stereo output.
4. Toggle original, then L/R. Confirm parent **does not play together with children**, and overall gain is approximately matched.
5. Export full mix in original and L/R modes and compare stereo samples/fold-down and overall levels; verify both normal and mono source edge cases.
6. Reopen the song, confirm L/R mode persisted; restore original and export again.
7. Mark in/out and enable looping; inspect audible click/gap behavior and report.
8. Launch on Omen with already-synced folder to check portability and path safety, without simultaneous SQLite use.
9. Run `python -m unittest discover -s app/backend/tests` in Song Harbor runtime Python environment plus frontend `npm run build`.

## Suggested next step
Use a purpose-built shared-clock audio engine or verified native DAW bridge for stable sample-aligned playback and DSP preview/export parity; then per-child independent controls and section-driven width/room automation with level-matched A/B. Retain canonical project manifests and source lineage.
