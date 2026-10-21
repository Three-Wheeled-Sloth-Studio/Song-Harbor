# Timeline navigation and timed section import QA

Status: committed on 2026-10-20; Windows frontend build and end-to-end runtime QA not verified.

## UI behavior
- Existing 1× / 2× / 4× / 8× / 16× dropdown continues to control zoom.
- The adjacent range slider is now **Timeline zoom**, using the same five levels; the original slider was horizontal pan and disabled at 1×, causing confusion.
- A separately labeled **Pan** slider appears at zoom >1, controlling horizontal viewport offset.
- Native non-passive wheel event on production timeline zooms around the waveform pointer position. Shift+wheel pans; wheel gestures on text editor, buttons, inputs or dropdowns are left alone so those elements remain usable.
- Section lane and original/derived stem waveforms share viewStart/viewEnd and drag-to-time conversion; viewport width stays within the current full-width song workspace. Do not widen the layout into the future effects sidebar without a real panel design.

## New import/edit workflow
- Sections > **Import / edit sections** exposes a small textarea.
- **Open .txt / .json** picks a local file, reads the text in the browser (100 KB max), and fills that same textarea.
- **Edit saved tags** reads existing project sections/proposals into the textarea in concise bracket notation.
- The user chooses **Replace existing** (default) or **Append**, and clicks **Apply timed sections**.
- Backend `section_import.py` validates the entire file and duration/overlaps before persisting the full replacement or append. Errors are displayed without mutating saved sections.
- Supported timed text:
  ```
  [Intro 0:00-0:15]
  [Verse 1 0:15-0:45]
  [Chorus 0:45-1:15 Vocal1:Expansive-Left Drums:Narrow-Right Bass:Moderate]
  ```
- JSON is also supported as `[{"kind":"Verse","number":1,"start_seconds":15,"end_seconds":45}]` or `{"sections":[...]}`.
- Untimed YuE2/ACE lyric headers are **not** sufficient to position markers and are rejected. The import does not infer time boundaries from audio or lyrics.
- Optional `Track:Width[-Bias]` tokens are stored as **section_spatial_proposals**, keyed by the generated stable section ID; these are intentions, not active DSP. The normal section boundary editor preserves these proposals when moving tags and removes proposals when deleting their sections. Source audio is never modified.
- New APIs: POST `/api/projects/{id}/sections/import` and GET `/api/projects/{id}/sections/export`. Tests: `app/backend/tests/test_section_import.py`.

## Suggested Windows smoke test
1. Relaunch using the normal launcher; confirm TS frontend build succeeds.
2. Open a song and drag the Zoom slider from 1× to 4×; verify the waveform changes size.
3. Use mouse wheel over the waveform to zoom and verify the time under the cursor stays approximately stationary.
4. At 4×, use the Pan slider and Shift+wheel to navigate to later choruses.
5. Import the sample timed tags through paste and through .txt; verify three section blocks are drawn.
6. Use Edit saved tags, change Chorus bounds without overlap, Apply Replace; reload project and verify persistence.
7. Test a malformed/overlapping tag and verify error with previous project data untouched.
8. Import Chorus spatial cues and Edit saved tags again; verify `Vocal1:Expansive-Left` remains.
9. Drag Chorus boundary, reload Edit saved tags; verify same spatial proposal follows it.
10. Confirm ordinary mouse wheel over section textarea scrolls text instead of changing zoom.

No CI or Windows build results are asserted for these changes. The internal transport is still independently streamed HTMLMediaElement sources; this slice does not address synchronization accuracy or realtime DSP.

## Untimed section imports and boundary alignment (2026-10-20 follow-up)

User QA: asking for explicit timestamps before identifying musical boundaries was tedious. Song Harbor now accepts **untimed section headers** and auto-spreads them evenly over the actual track duration, from 0 to song end. This is only an initial layout, not structure detection. Example:

```text
[Intro]
[Verse 1]
[Chorus]
[Verse 2]
[Chorus Vocal1:Expansive-Left]
[Outro]
[End]
```

A final untimed `[End]` is treated as a terminator and does **not** consume an entire section slot. Untimed headers can be pasted directly, included in `.txt` files, or represented as JSON objects without start/end. Ordinary lyric lines between recognized bracketed headers are ignored; unknown square-bracket directions are rejected rather than silently interpreted as structure. Header spatial proposals remain linked to their generated section IDs. All-timed imports preserve their explicit times. Mixed timed and untimed headers in the same import are rejected with a clear error; import them separately instead of guessing which boundaries are authoritative.

**Replace** distributes all imported audible sections across the song. **Append** allocates equal blocks in the remaining time after the existing final section, rejecting impossible placements rather than overlapping. User can then adjust the generated blocks against the waveform. Dragging a shared boundary between adjacent sections now adjusts *both sides of that boundary together* so there is no need to create a gap, then expand the neighbor manually. Keyboard nudges use the same rule. No original media changes.

Added untimed distribution, append, lyrics-list and safe-rejection tests in `app/backend/tests/test_section_import.py`. Unverified Windows build and manual UX test remain pending.

## Duration recovery and compact UX QA (2026-10-20)

User QA found "Import rejected: Song duration is required to place untimed sections" despite the song being playable, alongside complaints about strict undisclosed section types and creeping text-heavy controls.

**Fixed server duration recovery:** the missing field arose from recovered legacy project manifests with `source_duration_seconds: null`; the media player learned duration from loaded audio but the backend import validated only saved/job metadata. New `resolved_song_duration(record,job)` in `server.py` resolves existing valid project/job duration, else probes the original source and then available stem WAV files via configured FFprobe. On success stores the real duration in `song-harbor.json` and the in-memory job for future imports. Both the section import and manual section-save endpoints use this resolver. If all media/probing genuinely fails, the error is explicit and does not fabricate time. Tests in `test_duration_recovery.py`.

**Compact editing:** `SectionEditor.tsx` now shows concise `⇪ Import`, `✎` edit-saved, file-load, collapsed `＋ Manual` and small `?` help, with a section count. Detailed supported types and import rules are hidden in the `?` disclosure; manual In/Out/type/number/add controls and saved section list are collapsed. Import area appears on demand; success notifications are terse. Broader section vocabulary and a reusable contextual-help primitive remain an explicit *later* design task, not scope creep here. All import, save, section-boundary and duration behavior stays non-destructive.

Regression caveat: previous tests in `test_section_import.py` had accidental literal escaped `\\n` instead of newline escapes in sample tags. Corrected fixtures. **GitHub commits do not imply a verified local Windows build or passing CI.** On user machine test legacy saved song missing recorded duration, paste `[Intro]`/`[Verse 1]`/`[Chorus]`/`[Outro]`, apply and check evenly distributed section blocks and waveform guides; reopen song and verify saved result; expand help and manual controls when needed.
