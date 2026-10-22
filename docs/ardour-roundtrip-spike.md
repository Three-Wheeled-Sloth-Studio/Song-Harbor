# Ardour round-trip proof: deliberately limited integration spike

Status: approved as a narrowly scoped P1 experiment, 2026-10-22.
Ardour is installed on the user's Windows machine. No integrated adapter is
implemented or locally tested yet.

## Question

Can a Song Harbor authored instruction be executed in Ardour on an aligned
track, then can its *processed audio* be exported and imported back into
the original Song Harbor project as a new, reversible track version?

## Minimal vertical slice

1. Locate the installed Ardour executable as an **optional** DAW target.
   Do not require it for startup or standard Song Harbor export.
2. Export 2-6 aligned WAVs (including cello or guitar test track), stable
   IDs/aliases and section bounds with a manifest.
3. In Ardour, import the stems as separate tracks starting at 0:00.
   Prefer documented public Lua editor-action interfaces for creating
   automation curves and OSC for live control; exact API bindings and
   Windows-version support MUST be inspected before coding, not guessed.
4. Apply only one measured experiment: e.g. a right-pan ramp and -1dB gain
   to Guitar during an existing section. Verify Ardour's automation lane
   visually and audibly.
5. Export that track through Ardour's **Stem Export** with "Apply track/bus
   processing" enabled. This deliberately bakes effects to audio.
6. Reimport the aligned processed track as a **new version**, linked to the
   original source track_id with a provenance record. Compare durations,
   channels, start alignment and perceptual result; A/B the unmodified
   original vs processed version. Never replace/delete the raw stem.
7. Prove the user can accept, reject or revert that new version.

## Hard scope limit / stop condition

Do not build a generic plugin bridge, Ardour session XML writer, headless
Ardour engine, universal parameter-mapping layer, or modify Ardour itself
during this spike. If Lua automation or processed stem export cannot be
made dependable with documented interfaces in one focused vertical slice,
stop, write down the blocker, and retain manual aligned stem exchange.

## Technical distinctions

- Ardour control is separate from audio transfer. OSC can change transport
  and parameters but does not itself send audio stems.
- An Ardour processed WAV contains audio, **not** portable editable plugin
  automation. Store original Song Harbor instructions and provenance.
- Existing DAW target selector in `app/backend/daw.py` currently lists
  Waveform, Audacity, and MorningDAW; Ardour support must be added.
- Maintain immutable working sources, consistent filenames, track_id,
  section times, and checked imported duration. If the DAW creates a
  fixed offset, report it instead of silently realigning by guess.
- Avoid copying Ardour GPL source into Song Harbor; studying design and using
  documented integration APIs are preferable.

References:
- https://manual.ardour.org/lua-scripting/
- https://manual.ardour.org/working-with-sessions/interchange-with-other-daws/stem-exports/
- https://github.com/Ardour/ardour
