# DEV QA checkpoint: MIDI render lifecycle, sticky labels and note diagnosis
Date: 2026-11-05
Branch: dev only; main frozen at 2345c61.

## QA source
User reports the simplified direction-first piano-roll UI is much better. User requests render blocking progress, completion indication, return keyboard focus to Stem Tools, frozen note/section headers, clearer velocity values, and a future synchronized play/highlight control. They report some visually present notes that do not sound, including a circled very low pitch around G#1 in the piano roll.

## Implemented
- Piano roll Render now uses explicit rendering state. On pending backend render it overlays the popout with dim/fade and animated progress spinner; prevents duplicate activation. On success, the Render action retains a green completed state, closes the popout, and calls parent completion callback. Failure clears busy overlay and reports error without pretending success.
- BassMidiTool registers the Stem Tools root as a focus target and restores keyboard focus after successful render. It retains the existing candidate review, audition and combined stem acceptance workflow. No auto-accept.
- MIDI section ruler has sticky top positioning in the shared scroll viewport. MIDI note/pitch labels are drawn in a separate sticky-left column rather than being locked to the horizontally scrolling SVG. Sticky pitch mapping respects drums and melodic note names. Existing note edit and velocity logic retained.
- Velocity region now has a compact 1-127 label, and each editable velocity bar has a hover tooltip showing exact MIDI strike velocity and noting it is NOT rendered audio loudness.
- Added refs/roadmaps/piano-roll-playback-and-silent-notes-2026-11-05.md for transport-clock-synchronized playback, playhead, note-on highlights, and diagnosing missing SFZ note outputs.

## Current silent-note assessment
The MIDI-to-render path emits note-on and note-off for each saved note. SFZ candidate renderer checks output WAV type/length but currently does NOT validate whether every MIDI key or velocity triggers a playable sample or enough audible signal. Thus a visible note can be a valid MIDI event but absent in the selected SFZ instrument, or masked by articulation/envelope/transient/mix. The circled G#1 note is a strong pitch-range/region-mapping candidate, but this is NOT confirmed without the installed pack and audio. Do not claim root cause. Next diagnostics should inspect SFZ key/velocity regions and offer isolated note render + audio-energy verification.

## QA gates
1. User DEV auto-update/build after these commits. No Windows build or functional audio testing performed in connector session.
2. Render a whole-score and section-specific SFZ arrangement. Popout dims with spinner during work, cannot click conflicting actions; success closes popout, Stem Tools gets focus and presents candidate review. Reopen editor to verify Render control green. Render failure should remain in editor with visible error, no false green.
3. Pan piano roll horizontally: pitch names remain fixed to viewport left. Scroll pitches vertically: section ruler remains visible at top, scroll preserving note alignment. Verify with 243-note score and drum mapping.
4. Hover/select velocity bar: see actual MIDI velocity 1-127; editing still works, note highlighting and selection remain aligned.
5. Compare isolated circled low-pitch note from saved MIDI score with instrument SFZ mapping and rendered audio before diagnosing missing sample.
6. Verify no current-project data, source WAV, scripting, or acceptance logic changed by this slice.
7. Future: shared transport play/pause/playhead note highlighting, diagnostics in roadmap; NOT implemented in this slice.

## Known caution
Rendering readiness is tied to the awaited API response; no realtime percent is asserted. The progress spinner is intentionally indeterminate. If user later requests progress for multi-section rendering, a background job protocol or incremental result API is needed.
