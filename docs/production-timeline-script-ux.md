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

## 2026-10-21 playback and screen-utilization QA fixes

User reported Space often activated the last-focused button, audio stuttering, and a cramped mixer despite unused wide outer margins. Root causes found by code inspection:

- Global keyboard handler intentionally **excluded every button**, so focused buttons received the browser's native Space-to-click action rather than play/pause. `StemMixer.tsx` keyboard listener now runs in capture phase, prevents default Space when focus is on a button/waveform, and routes to playback. Text fields, selects, contenteditable regions, native range inputs and accessible section sliders still keep ordinary typing/arrow behavior.
- Independently streaming six (or more) HTML media elements used **hard seeks whenever drift >90ms, on every 120ms interval**, likely causing repeated decoder flushing and audible stutter. Changed audio `preload` to `auto`; transport retains position on resume without unnecessary seeking; gentle 0.975/1.025x playback-rate correction handles modest follower drift, with hard resync reserved for gross >1.5s desync on ready media, throttled to once per 4s. Playback start/stop uses generation IDs to avoid late `Promise.all(play())` completion reviving a stopped transport.
- Active song was still constrained by global `.workspace{max-width:1440px;margin:auto}`. `main.tsx` marks active song sessions `workspace--song-session`; CSS unsets this cap, fills viewport with responsive outer gutters and bounded 245–350px tools inspector alongside flexible main timeline. Below ~900px the inspector stacks. Standard home/import/read pages may remain intentionally bounded.

**Architectural caution:** reduced stutter is a mitigation, not verified sample-accurate multi-stem playback. Long-term fix remains one shared-clock Web Audio/native transport with prebuffered chunks and preview/export parity; do not promise sample alignment on HTMLMediaElement implementation. Actual user hearing test essential.

Studio-level principle updates (not just local CSS) committed to `Three-Wheeled-Sloth-Studio/TWS-Design-Principles`: `apps/App-Design-Principles.md` and `apps/Studio-UI-Style-Guide.md` now explicitly forbid letterboxed active editing surfaces and require two desktop width QA checks (1366px and 1920px); sidebars consume unused outer space **before** taking width from the primary editor. This elevates repeated user QA feedback to enforceable cross-project acceptance criterion.

Smoke test after syncing launcher: open at full display width, verify timeline fills wide space with small outer gutters and inspector beside it. Click a random toolbar button, then press Space: playback toggles, button does not react again. Click waveform, then press Space: playback toggles. Test arrows with browser focus on waveform versus section script text, verify text editing retains native caret movement. Play uninterrupted for 2–3 minutes, repeatedly pause/resume, seek and loop; note any stuttering/offsets. On 1366px and 1920px/resized browser check flexible width and correct inspector stacking. Frontend build and real Windows audio behavior **not yet verified**.

## 2026-10-21 frozen playhead during audible playback

QA: audio continues but waveform playhead/current-position display freezes, making section alignment impractical. Verified source-level cause: `StemMixer.tsx` transport polling always used `players[0].currentTime`; the first HTMLAudioElement could stall while five other routed stems keep playing. This made the waveform cursor freeze and also used the stalled source as the synchronization reference.

Fix committed: polling samples the `currentTime` of all active media elements. A reference candidate must be actively advancing (>12ms and <1s since previous poll), unpaused, not ended/seeking, and have available audio data. Prefer audible candidates given current parent-level mute/solo settings and monitoring volume. Use their median timestamp as the displayed transport position and synchronization target. A stalled/underrunning source is excluded; avoid fictitious wall-clock position increments. If all audio truly stops buffering, hold the last legitimate position; if all media elements ended, stop. Reset clock samples after pause, seek, resume, source-routing changes, and loop wrap. Continue low-rate drift correction only for advancing media, not a stalled first stem.

**Known limitation:** Multiple independently streamed media elements are still not sample locked. The active median clock prevents first-stem frozen UI but it does not guarantee that every stream remains perfectly aligned or can never stutter. Prioritize a single clocked audio engine if discrepancies continue. Windows runtime/CI verification is still outstanding.

Smoke QA: 1) Play an existing song for several minutes watching the cursor, especially through intro-to-chorus; cursor should continue when audible audio advances. 2) Mute/solo and split channels; cursor should follow audible streams. 3) Pause/resume, seek, rewind, jump, and loop; position should update without false forward movement during genuine audio buffering. 4) Play through song end; transport stops. 5) While following a chorus, drag the section boundary and confirm both the marker and playhead remain synchronized with actual audio.

## 2026-10-21 hard sync regression: stereo L/R and stems drift apart mid-song

QA: six independently streamed audio elements audibly lose alignment halfway into a song, particularly the extracted left/right channels. Previous mitigations (first-element clock → moving median clock; playbackRate ±2.5%/occasional seek) did not solve the fundamental issue and could change timing/pitch. **Replaced the complete in-browser multi-stream audition transport** with `app/frontend/src/SharedClockAudition.ts`, a single AudioContext and decoded AudioBufferSourceNodes.

### New invariant
Every active stem or split-channel buffer is started using **the same AudioContext start timestamp and the same source offset**. Pause stores `AudioContext.currentTime`-derived offset, seek recreates all buffer sources with a shared timestamp, and playhead reads that same clock. Each stem has independent GainNode; mono derived left/right route through hard-left/right StereoPannerNodes. Gain/solo/mute, monitor volume, exclusive parent/children routing and FFmpeg export remain as before. No more HTMLAudioElement transport, dynamic median clocks, per-stem playbackRate modification, or follower hard seek.

### MVP constraints
- Full audio is fetched and decoded into memory, sequentially, **before Play is enabled**; a compact `Preparing synchronized audio X/Y tracks` status is displayed. This may require noticeable preparation time on longer songs.
- Hard budget **768 MiB decoded PCM** to avoid unbounded browser memory growth. If exceeded, playback is unavailable and a clear error directs to DAW export; it does **not** switch back to unsynchronized audition. Longer tracks need shared-clock **chunked streaming** later, not another collection of media elements.
- Validate all decoded track durations agree within 150ms. Refuse badly mismatched media rather than pretending phase lock with unaligned files. Project audio is untouched.
- AudioBufferSources are one-shot; every seek/pause/resume rebuilds their sources, but all schedule together. Browser context output latency may remain, though it should be constant across stems.
- Changes exist in remote GitHub but **full Windows runtime and npm frontend build have NOT been verified**.

### Mandatory smoke QA
1. Launch Song Harbor normally and open the same problem song; observe `Preparing synchronized audio X/Y tracks` until ready.
2. Play the full song and listen closely halfway through where stereo left/right previously flammed/phased. Stereo image and drum transients must remain aligned.
3. Split a stereo stem, activate L/R children, play halfway through, and compare their timing and reconstructed stereo image against the parent mode (which needs a new preparation pass).
4. Repeat pause/resume, Space, arrow-jumps, drag seek, and section-boundary editing. One playhead must stay locked to all audible buffers.
5. Mute and solo stems *during* playback; changes must apply immediately without reloading/seek drift. Export mix still uses same chosen source set and respects parent controls.
6. Test a >768MiB decoded project and an intentionally mismatched track if possible; clear actionable error, no automatic fallback or partial playback.
7. Inspect memory use during playback and after switching songs/channel routing; decoded buffers must be released after engine dispose.

### Next engineering milestone
Replace full-buffer predecode with a native/Web Audio shared-clock chunk scheduler or AudioWorklet ring buffers so arbitrary-length songs work with bounded memory. Maintain a single timeline clock and explicit level/pan routing. Do NOT revive six independent HTMLAudioElements. Add automated null/mid-side/stereo reconstruction tests comparing export versus preview where test harness supports audio capture.
