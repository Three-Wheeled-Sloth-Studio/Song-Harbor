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

The A/B bypass is **audition-only**; it does not change the saved mix or processed WAV. **B · Original** now also bypasses section compression and vocal-keyed ducking. Changes to stem levels no longer intentionally restart the player just to rebuild ducking.

**Export to DAW** prepares six original aligned stem WAVs for use in an external editor. This is not a processed stereo mix, and the DAW import experience depends on the installed editor. Audacity and Waveform are supported as handoff targets, with varying automatic-import capability.

## Initial sound cleanup review

After a **successful Export mix WAV**, expand **Sound cleanup review** in Tools. This first-pass non-destructive scan checks the same rendered floating-point mix used for the 24-bit WAV and flags:
- Peak samples at or above -0.18 dBFS (approximately 0.98 linear), including clipping candidates. The scan accounts for master output trim.
- Single-sample jumps of at least 0.7 linear amplitude, separated by at least 80 ms, as **possible** clicks or other discontinuities. Drums and deliberately distorted audio may trigger false positives.

Click a reported timestamp to seek the audition transport. This is *suggestion-only* QA; it neither repairs sound nor changes exports. The list is capped to keep it usable. It currently runs during mix export, not continuously while playing. Sibilance, separation artifacts, broadband noise, pumping analysis, stem attribution and waveform marker overlays are not yet implemented.

## Updates, Settings and version

- The header revision badge (such as `main@1234abcd`) identifies the Git checkout that is installed; this is **not** a semantic release version.
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
