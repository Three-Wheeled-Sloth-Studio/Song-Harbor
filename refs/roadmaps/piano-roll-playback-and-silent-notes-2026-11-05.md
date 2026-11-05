# Piano-roll playback and silent-note diagnostics roadmap
Date: 2026-11-05
Status: Planned; no implementation promised in this rendering slice
Branch: dev

## Request
- Play button inside MIDI piano roll.
- Highlight the notes as their note-on events fire, with duration-aware active highlighting and a clear current-playhead line.
- Keep pitch labels frozen horizontally and section ruler frozen vertically, while retaining panning/zoom and low-height usability.
- Make MIDI velocity (1-127) understandable without explanatory paragraphs. Bars show MIDI strike values, not measured audio loudness.
- Diagnose notes visible in the piano roll that are missing or too quiet in the rendered SFZ/SF2 candidate (QA example: user circled a very low note around G#1 in Growlybass).

## Playback implementation proposal
- Reuse Song Harbor's existing transport clock and preview/audition infrastructure. Do not create a second unsynchronized audio engine.
- Read the saved or selected render candidate; bind timestamp to shared transport with seek, pause, rate, and section boundaries.
- Highlight notes during [start_sample, end_sample) based on the common 48-kHz clock, not on independent timers or DOM animations.
- Render active-note glow and cursor without regenerating a giant SVG for each audio frame; treat hundreds to thousands of notes efficiently.
- Provide play/pause, optional loop selection, follow-playhead toggle, and song/selected section scope from existing controls.
- Allow auditioning a note/instrument under pointer selection if playback backend supports single note render. Note visualization must distinguish MIDI note-on from actual audible sample output.
- Playback must preserve existing user editing, selection, and acceptance states. Audio automatically stops on closing or changing projects, following current transport behavior.

## Silent-note diagnosis
- Visible pitch and velocity are **intent**, not proof that an installed sampled instrument contains a playable key/velocity range.
- For SFZ, inspect imported SFZ region key ranges (key, lokey, hikey), velocity ranges, trigger behavior and articulation/CC requirements, including referenced includes/global/group inheritance. Avoid claiming the instrument is playable based on the note editor's generic 28-81 view.
- Correlate the exact MIDI note (pitch, channel, time, duration, velocity) with actual render candidate audio, taking into account mixed notes and stereo, section clipping, sample root notes, SFZ choke groups, envelopes and silent attack samples.
- Add an inexpensive note coverage/readiness indicator; make unavailable keys/velocity-layer gaps discoverable by tooltip/click, not by a wall of warnings.
- For actual rendered note isolation diagnosis, provide an optional temporary solo-note render (no destructive edits) and show measured rendered signal presence; do not infer an absent note solely from global RMS or mixed-bus level.
- QA with the observed low Growlybass note plus several audible notes using same pack; verify SFZ sample mapping rather than guessing from a screenshot.

## Acceptance checks
- Playhead and note highlight remain synchronized during play, seek, zoom, resize, pausing, and looping.
- Row label/section header remain visible during independent horizontal/vertical scrolling; no overlays hide notes.
- The note monitor can distinguish "MIDI event exists", "instrument key is mapped", and "rendered audio is audible" as separate states.
- It is possible to audition the questionable note without replacing source audio or accepting a stem.
