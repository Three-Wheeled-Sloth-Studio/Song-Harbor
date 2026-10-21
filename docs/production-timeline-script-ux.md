# Production timeline UX and canonical section script — 2026-10-21

Status: code committed to default branch, **not runtime/build verified on Windows**.

## Workstation UI
- Main working lane: compact **transport** immediately above **section blocks**, then aligned **stem waveforms**, then **stem mixer**. Transport has play/pause, stop (pause + return to song start), back/forward by five seconds, playback seek and monitor volume. Right-click the rewind button jumps to song start without opening a context menu.
- Space toggles playback. Left / right arrow jump -5 / +5 seconds, clamped to track length. Shortcuts do **not** override text input, buttons, native form controls, or accessible section sliders. Shortcuts are global while Song Harbor is focused; no new native OS hotkeys.
- Section lane icon **≡** at left expands manual In/Out/type/number/marker tools. Double-click the body of a visual section header opens the section script in tools, focusing that section where possible.
- Right tools panel: canonical **Sections** script, zoom and horizontal position controls, optional loop in/out, split channels (with its file-folder action), WAV mix download, and external DAW exchange. Main timeline no longer has verbose edit/zoom/loop toolbars between transport and waveform. Responsive stacking on smaller screens.
- Zoom remains accessible with wheel over waveforms; Shift+wheel horizontal pan.
- Existing source separation, non-destructive routing and export remain unchanged.

## Canonical section script
- `app/frontend/src/SectionsTool.tsx`: On-demand side-panel text editor reads **the saved project text** from `GET /api/projects/{id}/sections/export`; `POST /api/projects/{id}/sections/import` validates and atomically saves edits.
- Every section header is auto-timestamped in this view after import. Manual boundary drags update canonical `sections`; side-panel script reloads when its text is not dirty. If the user already edited unsaved script text, it displays a stale warning instead of overwriting that draft. Reload icon explicitly restores the saved state.
- `app/backend/section_import.py` now preserves non-bracket lyric lines attached to each section as `section_lyrics` and round-trips them alongside timestamped headers and spatial proposals. `server.py` persists the lyric mapping, keeps it for retained section IDs on visual changes, and drops it for deleted sections. Text edits preserving the ordered section identity reuse existing stable IDs so other future metadata is not lost unnecessarily.
- Sections text is now a structured, editable view of **persistent project truth**, not a replacement for the typed sections/IDs/media lineage model. Spatial proposals remain nonexecuting. Supported section tags remain narrow; expand dictionary in a later pass.
- Importing a replacement updates shared visual section state and resets zoom to full song. Type/time/overlap errors remain atomic.
- `app/backend/tests/test_section_import.py`: lyric round-trip and stable-ID timestamp re-edit checks added. Tests not executed by connector.

## Next UX/engineering tasks (not implemented)
1. Double-click section title enters more capable editing; add *insert before*, *insert after*, *merge with prior*, *merge with next*. Preserve scripts/lyrics/proposals with conflict checks.
2. Section-aware rewind: if >=5 s into current section, jump to that section's start; otherwise jump to previous section; forward always jumps to next section. Keep transport + keyboard semantics identical.
3. Improve waveform time-resolution at high zoom and shared-clock audio transport to eliminate follower drift for phase-sensitive listening.
4. Musical section alignment: start with local lyrics alignment against **existing Demucs vocal stem** and confidence labels. Candidate forced aligners [stable-ts](https://github.com/jianfch/stable-ts) (known transcript `model.align`) and [WhisperX](https://github.com/m-bain/whisperX) (word timestamps), plus nonlyrical novelty/change-point analysis. Singing, choral layers, word repetition, spoken rap, skipped lines and instrumental bridges are weak cases and must permit manual correction. Estimate: 3-6 developer days prototype on vocal alignment; 1-2 weeks for useful hybrid + QA; additional weeks for robust production support. Actual model download/license/performance unknown.
5. Help reference for section vocabulary and contextual audio-processing directives.

## Windows verification checklist
- Launch normally: ensure frontend TypeScript builds and project loads.
- Space play/pause; Left/Right advance five seconds outside text input; arrow keys move caret inside script textarea, not transport.
- Stop resets playhead to zero. Right-click rewind resets to zero, ordinary click rewinds five seconds.
- Ensure playback seek line is directly above **section bar**, then six aligned waveform rows, then six stem controls.
- Open Sections on right. Import bare tags + lyric lines, press Apply, verify visual sections, timecodes and lyrics. Double-click Chorus header, check script opens and cursor/selection is near the corresponding tag.
- Drag a shared section boundary. If script clean, verify auto-updated timestamps. If script dirty, verify unsaved text is retained and a stale warning appears.
- Split stem, export WAV and open derived files via tools panel, verify corresponding old functionality unaffected.
- On narrow display, ensure tool panel moves below main timeline without making the waveform unusably narrow.

Avoid advertising completed sample-accurate rendering, automated lyric alignment, or insert/merge controls yet.
