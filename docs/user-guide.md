# Song Harbor User Guide

This guide covers the currently implemented local-first Song Harbor workbench. The **i** icon next to Settings in the top-right application header opens the searchable offline help view. Its topics cover the same workflows below. Song Harbor is in active development; not every planned feature is available.

## Start here: from recording to editable song

1. Launch Song Harbor with the supplied launcher. The app opens in your browser but audio, models, projects and rendering operate locally.
2. Open a song from **Library**, or select **Import song**, choose a WAV/FLAC/MP3/M4A/AIFF/OGG recording, and select **Separate stems**. The first run may require FFmpeg configuration and may take longer to load the separation model.
3. Song Harbor separates six model-estimated stems: Vocals, Drums, Bass, Guitar, Piano and Other. Separation is imperfect, so some instruments may bleed across stem categories.
4. Play the stems in the workspace. Set levels, mute or solo individual stems, inspect the waveform and section timeline.
5. Open **Tools > Sections**, paste or edit your arrangement, and **Apply**. Use timeline markers to correct section boundaries.
6. Adjust production effects, listen, and use **Export mix WAV**. Once rendering completes, click **Download WAV** to save it using your browser's download settings.

## Import prepared tracks and restore split-channel exports

On **Import song**, select **Multiple tracks · already separated**. Choose **2–64** WAV, FLAC, MP3, M4A, AIFF or OGG audio files at once. These become individual tracks in **one song**, without Demucs separation. Song Harbor suggests a title from the common filename prefix; override the editable Song title field before import if necessary.

**Reimport a Song Harbor stereo split export:** Select all **12 mono WAVs plus their original `manifest.json`** together (or the equivalent complete Left/Right pairs for any exported number of stems). The manifest must be `song-harbor-stereo-channel-split` version 1. It is not an optional decorative attachment: Song Harbor uses it to pair each Left/Right file with the correct original parent. Import reconstructs six stereo parents and restores **L/R active** routing so that the player behaves as though you split those stems inside Song Harbor. Source files and the manifest's original project ID are never trusted as filesystem locations; only uploaded validated filenames are used. Do not select `README.txt`.

**Arbitrary numbered/named tracks:** Unknown stems become unique, script-safe names based on the original filenames, with stable internal `track_id` values. On the mixer, the readable source filename appears with its exact section-script alias below (for example, `Synth_01`). Section pan, width, space, reverb, EQ, compression, ducking, and reset directives accept any current source alias rather than only Vocals/Drums/Bass/Guitar/Piano/Other. When an alias is unknown, Apply rejects the production script rather than silently dropping automation.

**Alignment and originals:** Working copies are 48-kHz PCM WAVs aligned at **0:00**. Shorter source audio is padded with silence without time stretching, BPM sync or automatic source offset detection. Unmodified original uploads remain in the local song directory. Manifest imports preserve original mono channels as active L/R child tracks and rebuild their stereo parent working copy.

**Current playback limits:** The project model and import accept up to 64 parent stems (or up to 128 channel files with a complete split manifest). The shared-clock browser audition engine still has a **768 MiB decoded-audio budget** and the offline WAV renderer retains its existing 15-minute limit. Dozens of long/high-resolution tracks may exceed those memory limits even though the project and DAW exports support the track count. Chunked streaming is not implemented yet; don't treat the 64-track model limit as a guarantee that all 64 can be previewed simultaneously.

**Future naming behavior:** Each imported track has a stable ID and immutable working filename, separate from its display name and script alias. The planned track-rename UI must migrate all section-script tokens and stored target references atomically when a name is changed; merely changing the visible label without updating references is not acceptable. The rename UI/migration is not implemented yet.

After import, tracks appear in the standard mixer, timeline and Library. For multi-track audition, verify that related recordings originated at the same start position.

## Library and project safety

- Songs can be reopened from Library. Use the row action menu or right-click for available rename, grouping, collection, remove and restore options.
- Changing a song's Library title does not rename original files.
- Grouping related takes is a metadata link, not a destructive audio merge.
- Removed Library entries are recoverable; original audio is retained.
- **Apply** section text before closing or updating the app. Unapplied browser editor text is not guaranteed to survive restart. Save other project/mixer changes too.

## Playback and navigation

- **Space** plays/pauses unless focus is in an editable text/form control.
- **Left/Right arrow keys** seek backward/forward five seconds.
- Click a waveform position to seek. Use zoom and region loops for more precise passage work.
- Stem levels, mute, and solo affect the audible mix and export according to the current mixer state. Monitor volume affects listening only.
- Derived L/R channels replace their original stereo parent when enabled: they do not play alongside it.
- All stems use one shared playback clock. Long songs can encounter a decoded-audio memory limit rather than silently falling back to unsynchronized streams.

For timeline zoom, use the **Tools > Zoom** dropdown or slider. The mouse wheel scrolls the page normally, even when the pointer is over a waveform; it does not change waveform zoom. True fullscreen app mode and a far-right topbar close control are planned, not yet implemented.

## Sections: notation and persistence

Each section uses a header, optionally **one** production-directive line, and optional lyrics:

```text
[Verse 1 0:12-0:35]
{Vocals.pan:left.40@2s:smooth Guitar.duck:3@1s:smooth}
These are the original lyrics.

[Chorus 0:35-1:05]
{Vocals.width:150@2s:smooth Other.comp:-20,2@2s:smooth}

[Outro 1:05-1:20]
{Other.comp:-18,1@2s:smooth Master.fade:4s:smooth Master.tail:3s}
```

Use recognized stem aliases **Vocals**, **Drums**, **Bass**, **Guitar**, **Piano** and **Other**. Effects carry forward when later sections omit settings. Transitions support smooth or linear ramps. Unknown directives are rejected rather than ignored.

**Important reset distinction:** `Other.reset` resets the stem's effects, including pan, width, spatial reflections, reverb, EQ and dynamics. You cannot use `Other.reset` alongside `Other.pan`, `Other.width` or another explicit Other effect in the same block. To turn off **only compression**, write `Other.comp:-18,1@2s:smooth` (neutral 1:1 ratio). To stop vocal-keyed ducking on Guitar, write `Guitar.duck:0@1s:smooth`.

### Supported effects

| Control | Example | Notes |
| --- | --- | --- |
| Pan | `Vocals.pan:left.40@2s:smooth` | Left/right 0-100% or center |
| Width | `Other.width:135@2s:smooth` | 0-150%, 100% nominal original |
| Space | `Guitar.space:20@2s:smooth` | 0-40 early reflections |
| Reverb | `Vocals.reverb:30@2s:smooth` | 0-100 wet send |
| EQ band 1-3 | `Vocals.eq1:320,1.2,-2@2s:smooth` | Frequency 30-16000 Hz, Q 0.3-12, gain -12 to +12 dB |
| Compression | `Other.comp:-18,2@2s:smooth` | Threshold -60..0 dBFS, ratio 1..4; neutral by default |
| Vocal ducking | `Guitar.duck:3@1s:smooth` | Up to 3 dB attenuation when vocal detected; 0-12 dB range |
| Ending | `Master.fade:4s:smooth Master.tail:3s` | Final section only, preserves wet reverb decay |

The compressor has conservative fixed attack/release and no automatic makeup gain. Ducking currently uses a deterministic envelope from the separated vocals, not an unrestricted external sidechain. Dynamic EQ, a full effects rack, plugin hosting, de-essing, phrase-level artifact repairs and gain-reduction meters are planned, **not** available.

## Export and external DAWs

**Export mix WAV** uses the current saved production settings, stem levels, end fade and reverb tail. The WAV is a rendered stereo mix. You must click **Download WAV** after rendering; the browser handles the save destination. If a clipping warning appears, apply the suggested master output trim and render again. Master trim is session-only at present.

A/B bypass is **audition-only**, not saved in WAV. **Bypass compression** and **Bypass ducking** are independent checkboxes so each new dynamics effect can be heard separately. **B · Original** bypasses both; **A · Processed** restores both. Changing stem levels no longer intentionally restarts playback just to rebuild ducking.

**Export to DAW** prepares six original aligned stem WAVs for use in an external editor. This is not a processed stereo mix, and the DAW import experience depends on the installed editor. Audacity and Waveform are supported as handoff targets, with varying automatic-import capability.

## Fullscreen Song Harbor and floating tool windows

On Windows, when the default browser is Chrome, Edge, Brave or Vivaldi, the launcher now starts a dedicated isolated Song Harbor app window in fullscreen mode. Firefox uses its kiosk mode. Other browser handlers retain a conventional window fallback. The far-right **×** in the Song Harbor top bar confirms shutdown and asks the **current local backend** to quit; it does not close unrelated apps or browser windows. Finish jobs and save work before quitting. Windows launcher behavior still requires local acceptance testing.

The workspace Tools control is a compact **icon rail** along the right edge instead of a permanently wide inspector. Choose one icon for its tool; a movable floating window appears over the main waveform/editor and updates the current song while controls change. Drag the title bar to reposition; **×** dismisses the tool without removing song settings. The rail's icons have hover/keyboard labels. Only the selected tool's controls are mounted, and the waveform keeps the reclaimed horizontal space. The Sections editor retains its own safe Apply/Save behavior.

### Correction trial for a cleanup finding

For **Peak exceeds 0 dBFS** and **Repeated loudness dips**, choose **Try correction A/B** on the finding card after analysis. Song Harbor sets a short listening loop around the finding.

- **A · Saved** means the current saved processing. **B · Proposed** means a temporary auditioning override. These do not overwrite original audio. Change sliders and listen to the loop again.
- A **peak** proposes lowering master output trim to aim at -1 dBFS sample peak. The correction is a **session-only** master output trim pending future persistence; accepting updates the live mix/export setting but won't survive restart.
- For **repeated loudness dips**, the initial suggested trial disables vocal-keyed ducking (0 dB) on an active non-vocal stem. You can instead choose compression, adjust its threshold and ratio, and select the exact stem; trial targets the containing saved section. This is a hypothesis to audition, not a diagnosis of the cause.
- **Accept correction** validates and applies the dynamics directive through the current section-script import pipeline, preserving the other section directives and lyrics. Section automation inheritance still applies. **Discard** reverts the temporary override without changing the saved script. Corrected WAV export continues to use accepted production settings rather than temporary trial state.

Switching an adjustment while playing may reschedule the current audio sources; seamless instantaneous sample-level trial switching is not yet guaranteed. The tool is intentionally conservative: it does not auto-accept suggested changes or claim sound improvement without listening.

## Sound cleanup analyzer: detection and review

Open **Tools → Sound cleanup** and select **Analyze mix**. Song Harbor builds the same non-destructive offline processing graph used for the WAV export, then checks the rendered floating-point audio (with master output trim). It does **not** download a WAV or change stored audio, sections, or effects.

The analyzer now makes *listening suggestions* in these categories:

| Category | Candidate checks | What the result can and cannot mean |
| --- | --- | --- |
| Levels | Peak at/above approximately -0.18 dBFS, sample peaks over 0 dBFS, repeated flat-topped waveform samples | Review master trim, clipping or intentional limiting; **not** an intersample true-peak meter |
| Transitions | Large single-sample waveform jumps | Possible click/pop, kick transient or deliberate distortion |
| Vocal / high frequency | Sustained dominant 5–9.5 kHz bursts (sibilance-like), 2.5–4.9 kHz presence emphasis (harshness), upper-band fizz | Can also identify cymbals, guitars, synthesizers and desired texture. **Not** a voice classifier or automated de-esser |
| Quiet passages | Persistent high-frequency activity during low-level audio | Possible hiss, separation residue or normal room ambience |
| Stereo / mono | Sustained negative left/right correlation during audible passages | Possible mono cancellation; wide creative stereo can produce this on purpose |
| Dynamics | Repeated brief loudness troughs between stronger passages | Possible rhythmic pumping; **not** proof a compressor or sidechain caused it |

The analyzer uses bounded FFT windows for frequency evidence, a broad RMS envelope for dynamics, and correlation windows for mono-compatibility risk. Thresholds favor relatively pronounced candidates, not exhaustive defect identification.

**Review workflow:** Filter by category; click a timestamp to seek; choose **Loop ± context** to mark and play a short repeating region around the candidate; read the conservative suggested next action; mark a candidate reviewed to hide it temporarily. A narrow **QC marker rail** also appears directly above the stem waveforms, so candidates can be located and clicked without duplicating markers on every split track. Use **Show reviewed** to revisit it. Results are sorted by severity then time. Re-analyzing or changing production settings clears prior review decisions; review marks are session-only.

Some findings offer **Active raw stems** as a clue about which inputs contain the strongest local signal or high-frequency activity. These are pre-effect approximate activity rankings, not reliable causal attribution, instrument recognition or a source isolation result.

**A peak at 03:35:** If the finding reports a peak over 0 dBFS, audition that time, lower master output trim according to the suggested amount, then re-render/analyze. A single sample peak says nothing by itself about audible distortion. True-peak, integrated loudness and detailed de-essing are still future work.

The scan requires the current synchronized audio to be loaded and can consume CPU/memory for a full-track offline render. Source media is never rewritten. It is not automatically monitoring live playback, and it does not fix detected candidates.

## Updates, Settings and version

- The header badge uses **Version:Revision:Build**, such as `0.1.0:1:320`. Version comes from the frontend package version; revision identifies the development revision; build is the current Git commit count. Hover to view diagnostic branch/short SHA. This is a development identity, not a published stable release.
- The circular update icon checks for available source updates. Checking does not overwrite local files. On Windows, approved install/relaunch attempts a safe Git fast-forward and restarts the application.
- The updater will not intentionally discard conflicting checkout changes or interrupt an active processing job. Always **Apply** unsaved script edits before restarting.
- Settings controls your local working directory and component dependencies. A new directory may require restart; existing files are not automatically moved.

## Troubleshooting and reporting

| Symptom | First checks |
| --- | --- |
| Separator unavailable | Look at engine status, FFmpeg setup in Settings, and the launcher console |
| Song missing after restart | Check Library and confirm the same working-files directory |
| Section import rejected | Confirm valid headers and timestamps, one directive line, correct alias, bounds and no broad reset conflict |
| Export did not download | Click Download WAV after render; inspect browser download location |
| Mix too loud to export | Review peak warning and apply conservative master output trim |
| Stem timing problems | Check split L/R routing and any reported duration mismatch; capture reproduction steps |
| Update blocked | Check active processing, local Git changes and any divergence; never force reset to solve an update |

For bugs, use the [Song Harbor issue tracker](https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/issues) and include installed revision badge, OS, steps to reproduce, expected/actual behavior and exact error. Do not publish private audio or sensitive local paths without consent.

## Project boundaries

Song Harbor is local-first and uses non-destructive processing scripts. The master output trim is still session-only, and testing preview/export audio parity with real material remains important. Full effects/plugin support, de-essing, audio cleanup suggestions and compact Tools inspector improvements are on the roadmap.
