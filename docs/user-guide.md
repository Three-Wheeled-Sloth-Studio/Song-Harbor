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

**Current alignment and originals:** Working copies are 48-kHz PCM WAVs aligned at **0:00**. Shorter source audio is padded with silence without time stretching, BPM sync or automatic source offset detection. Unmodified original uploads remain in the local song directory. Manifest imports preserve original mono channels as active L/R child tracks and rebuild their stereo parent working copy. **Future short accompaniment clips (not yet implemented):** an imported/generated passage will keep its original duration, have virtual silence outside the waveform, and be freely draggable along the song timeline. Align-to-section will be an initial position suggestion, with visible but never enforced snap cues. Planned alongside the first ACE-Step accompaniment test.

**Current playback limits:** The project model and import accept up to 64 parent stems (or up to 128 channel files with a complete split manifest). The shared-clock browser audition engine still has a **768 MiB decoded-audio budget** and the offline WAV renderer retains its existing 15-minute limit. Dozens of long/high-resolution tracks may exceed those memory limits even though the project and DAW exports support the track count. Chunked streaming is not implemented yet; don't treat the 64-track model limit as a guarantee that all 64 can be previewed simultaneously.

**Add and rename existing tracks (pending local QA):** In the mixer, use **+ Add stem** to import an additional prepared audio file or the pencil icon to edit a track's display name and script alias. Each track has a stable ID and immutable working filename. Rename updates saved structured production guidance and keeps audio source identity unchanged. Apply and close Whole Song Section Text before adding or renaming; new capabilities await Windows audio acceptance.

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

The compressor has conservative fixed attack/release and no automatic makeup gain. Ducking currently uses a deterministic envelope from the separated vocals, not an unrestricted external sidechain. Dynamic EQ, a full effects rack, plugin hosting and phrase-level artifact repairs are planned; conservative per-stem de-essing and live dynamics meters are available.

## Export and external DAWs

**Export mix WAV** uses the current saved production settings, stem levels, end fade and reverb tail. The WAV is a rendered stereo mix. You must click **Download WAV** after rendering; the browser handles the save destination. If a clipping warning appears, apply the suggested master output trim and render again. Master trim is session-only at present.

A/B bypass is **audition-only**, not saved in WAV. **Bypass compression** and **Bypass ducking** are independent checkboxes so each new dynamics effect can be heard separately. **B · Original** bypasses both; **A · Processed** restores both. Changing stem levels no longer intentionally restarts playback just to rebuild ducking.

**Export to DAW** prepares original aligned stem WAVs for use in an external editor. This is not a processed stereo mix, and the DAW import experience depends on the installed editor. Audacity and Waveform are supported as handoff targets, with varying automatic-import capability.

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

### Updated floating tool layout

The right-hand tool rail is **54px wide**, with icons enlarged to occupy most of the reserved width. It no longer retains the old wide inspector column. Open multiple tools at once by clicking their icons; each window can be dragged by its title bar, resized by the lower-right corner, brought to front, and dismissed individually. Content outside those windows remains interactive.

**Edit sections** replaces the separate Pan, Reverb, Stereo width, Reflections, and EQ icons. Choose the shared **Section** dropdown, then select an effect tab or **Script** for the full production block. Double-clicking any section on the playback timeline opens Edit sections with that section selected and Pan shown. The child effect editor inherits the shared section selection. Unapplied script edits are retained in memory when switching tabs or tools, but only Apply persists them.

The previous DAW Handoff tool is now **Download**. Its panel says Download tracks and provides local aligned track export, with optional DAW launch explicitly separate. Processed mix WAV export remains in the song's existing export footer.

## Session safety and Section Edit audition

**Monitoring volume now persists on this device and browser profile.** Song Harbor saves the Playback monitoring volume slider locally after every adjustment and restores that value when relaunched. A fresh installation/browser profile defaults to **25%**, rather than the previous louder 75%. This setting affects listening only, not the saved stem balances or rendered WAV. Browser storage restrictions can prevent persistence; Song Harbor falls back to 25% rather than interrupting playback.

**Floating tool wheel scrolling:** Place the pointer anywhere within a tool's scrollable content and roll the mouse wheel to scroll that tool instead of the waveform/page. The window's resizable corner is independent of scrolling; scrollbars also remain available.

**Edit sections → Edit whole-song section text…** opens a distinct, wide, resizable **Whole-song section text** floating window. It loads the authoritative section export containing **all section headers, their full production blocks and all lyrics**, not just the currently selected section. You may edit the complete song and click **Apply** to validate and save it. This command deliberately remains outside the primary row of effect tabs. Unapplied edits stay in memory while switching tools; save them before restarting the app. The Section dropdown still scopes the individual effect tabs.

**Section Edit A/B (effect tabs):** The floating section editor has an **A · Saved / B · Draft preview** switch. Select a section and an effect tab (Pan, Reverb, Width, Reflections, EQ or De-ess), choose B and the selected section loops automatically. Adjust the controls while the music plays; those values are temporary, and changing them does not save the project. Switch to A to hear the saved settings. Click the effect's **Save / Apply** to commit a setting; closing the tool or choosing a different section/effect discards the temporary preview. The rendered WAV remains tied to saved settings; export is blocked while an unsaved B preview is active. Direct edits in the whole-song text editor are not previewed until Apply—they go through complete grammar validation.

These A/B switches are separate from the analyzer's correction-trial A/B. This is an initial live audition mechanism, **not** a fully loudness-matched blind test. When in doubt, return to A, reopen B at modest values and verify differences on a short loop.

## Dynamics visibility and section-aware de-essing

The **A/B comparison** tool now has an independent **Bypass deess** checkbox alongside compression and ducking. It shows live per-stem gain-reduction readouts when there is measurable processing. Compression uses the Web Audio compressor's live gain-reduction estimate; vocal-keyed ducking and de-essing read their scheduled AudioParam attenuation. These values are *per stem, approximate*, and not integrated loudness measurements.

In Sound cleanup, a **Repeated loudness dips** or **Sibilance-like high-frequency burst** candidate can open **Try correction A/B**. Use **A Saved** versus **B Proposed** while listening to the same loop. The correction tool now shows separate compressor, ducking and de-esser meters. To make a subtle change easier to identify, set **Audition strength → Exaggerated · 3×**. The exaggeration affects only the current live preview and never changes the accepted values. For loudness dips, prefer checking whether the original gain-reduction meter actually moves before deciding to adjust compression/ducking.

A conservative per-stem **de-esser** now supports a frequency-targeted peaking filter controlled by the energy of the target stem above an adjustable high-frequency cutoff. A detector with short attack and release dynamically attenuates the selected band rather than globally reducing all treble.

It supports this section production directive:

```text
[Chorus 1:42-2:05]
{Vocals.deess:6500,2,-40,4@2s:smooth}
```

The four values are **center frequency Hz** (3000–11000), **Q** (.4–8), **detector threshold dBFS** (-70 to -10) and **maximum frequency-band reduction dB** (0–12). Transition duration is .05–30 seconds. A stem reset restores neutral de-essing. Older projects without this directive do not de-ess by default.

You can access the de-esser directly through **Edit sections → De-ess**, choosing the section and track before adjusting center frequency, Q, threshold and maximum reduction. The **Script** tab remains the complete original text editor. For a sibilance-like finding, choose **Try correction A/B** to audition the same de-esser controls in context. **Accept** writes a validated instruction for the containing section; **Discard** restores previous processing. The live audition and offline WAV render share the same detector and filter graph; no original WAV is overwritten.

**Limits:** This is a spectral heuristic, not a voice or sibilant classifier. Cymbals, strings, synths and industrial distortion can cause similar high-frequency triggers. There is no guaranteed level-matched A/B, machine-learned artifact recognition, or automatic repair yet. An exaggerated preview is explicitly *not* the saved processed sound. Confirm actual 1× comparison before accepting.

## Acoustic signal audit (release screening)

Sound cleanup now includes a separate **Signal audit** category in the normal **Analyze mix** pass. This performs a conservative **local, non-destructive acoustic screening** on the actual processed mix that will be exported, looking for a stable narrowband spectral feature (e.g. a long-lived high-frequency tonal line). Findings include a timestamp, frequency in hertz, a sampled persistence percentage, and local spectral prominence. Click to seek or loop and evaluate the passage in context. The scanner does not inspect external servers, send audio to anyone, mute/filter tones or rewrite media.

**Do not interpret a finding as a watermark or fingerprint.** Common synth notes, resonances, feedback and other intended musical elements can produce persistent high-frequency lines. Absence of narrowband findings also cannot rule out spread-spectrum, time-domain or provider-specific acoustic watermarking; definitive provider watermark or fingerprint verification requires the provider's detector or another validated matching system. Song Harbor deliberately gives no "watermark detected" verdict.

**C2PA metadata is separate from acoustic screening.** Song Harbor's processed WAV export writes a fresh 44-byte PCM RIFF header containing `fmt ` and `data` chunks only (24-bit stereo). It does **not** copy or embed source C2PA (`c2pa`), ID3, INFO or provider-specific metadata from the input file. Consequently the source's C2PA chunk is not present in the newly rendered WAV. This is a property of the **new file**, not evidence that an acoustic fingerprint has vanished or would stop matching; no watermark removal step is performed. Re-encoding or editing media does not guarantee an audio-content fingerprint ceases to identify it.

The screen is intentionally limited to durable, high-prominence narrowband features lasting over ten seconds; ordinary transient/cymbal energy should not dominate it. Heavy audio analysis can take several seconds on long tracks. Findings remain suggestions, and exporting never automatically removes or changes a suspected signal.

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

### Experimental Audio Forensics inspector

Open the **⌁ Audio forensics (experimental)** icon on the right-hand tools
palette. Choose **Scan current mix** to inspect the current effects-processed
audio for spectral texture, transient/dynamics anomalies, stereo phase and
peak integrity. Click a category to filter the results; each finding can
seek to its timestamp or loop the surrounding passage. Scanning is local,
on-demand, non-destructive and shares the existing Sound Cleanup analysis.
No new model download is required. This experimental panel does **not**
determine whether a recording is human-made or detect all fingerprints or
watermarks; a flagged tone may be intentional music. Source-versus-output
comparison is future work.

**Navigating import errors:** If applying whole-song section text reports `Line N:` (for example, an unsupported section name or invalid production directive), select **Go to line N ↗** next to the error. Song Harbor selects the offending line in the text editor so you can correct it without losing your unsaved draft. The button appears only when the validator identifies a line number.

### Independent left/right child-channel automation (experimental; Windows QA pending)

After using **Split channels** and activating the L/R child routing, the whole-song
section script can target each child independently. The parent alias is still
the shared reconstructed stereo stem. For example, on a **single** production
instruction line after a section heading:

```text
[Chorus 1:42-2:05]
{Drums.reverb:10@2s:smooth Drums-right.reverb:18@2s:smooth Drums-left.gain:-0.75@2s:smooth Drums-right.eq1:1000,1,-2@2s:smooth}
```

The parent reverb value is the effective baseline for the two channels.
`Drums-right.reverb:18` overrides the **right** channel to 18%, rather than
adding 18% to 10%. The left channel retains the parent 10% value. Parent
EQ, pan and processing remain on the combined bus; supported child effects
are gain, pan, three-band EQ and reverb send, applied before the shared bus.
Parent and child gains multiply. Child pan defaults to original hard-left/
hard-right placement; a child `.pan:` instruction explicitly repositions it.

Split-channel source identities are virtual targets based on the existing
parent track and do not add independent mixer rows or rewrite source WAVs.
When the parent is switched back to original stereo routing, child effects
are dormant, not applied to the unsplit stereo source. Parent alias renaming
migrates its existing `-left` and `-right` directives. Child-target width,
space, compression, ducking, and de-essing are **not supported in this slice**:
the importer rejects them rather than ignoring them. This uses Song Harbor's
existing CPU/audio graph, with extra lightweight nodes per active split child.

**Acceptance:** verify center/left/right pan, gain, EQ, send inheritance,
script rename/reopen and parity between live audition and 24-bit WAV export.

### Spatial evolution macro (experimental)

The first deterministic spatial macro is available in whole-song section text:

```text
[Bridge 2:53-3:56]
{Other.evolve:menacing@20s:smooth}
```

This asks Song Harbor to evolve the named **parent stem** over 20 seconds
using existing parent pan, width, early reflections, EQ and reverb sends.
If its split L/R channels are attached, it also applies restrained
left/right EQ coloration and asymmetric reverb. The original source remains
unchanged, with effects rendered both during synchronized playback and WAV
export. The source script retains the readable `.evolve:menacing` intent;
internal generation uses versioned `menacing` v1 typed curves.

You can place explicit effects on the same production line to override
individual macro settings for that section, for example:

```text
{Other.evolve:menacing@20s:smooth Other.reverb:10@2s:smooth}
```

The explicit reverb value wins, while the other macro parameters still apply.
Use only one production block on a single line beneath the section header;
do not replace your whole lyric sheet with these illustrative fragments.

The macro is a *preset*, not yet an adaptive spatial safety system. It
does not automatically check true peak, adjust stereo correlation or protect
mono fold-down, and it has no dedicated per-macro A/B control. Start with
an audition of the original and processed mix at similar perceived volume.
Existing `A/B comparison` lets you bypass effect families. Child L/R
components appear only when a valid split is attached.

**Transport QA note:** natural song completion now resets the waveform
playhead and underlying shared-clock transport to 0:00. Ordinary Pause
continues to retain the pause position.

### Multiline production directives (LF and Windows CRLF supported)

For legibility, production directives may be separated by spaces, Unix LF or Windows
CRLF **inside the same curly-brace block**. One directive per line is recommended:

```text
[Chorus 1:42-2:05]
{
  Drums.pan:center@2s:smooth
  Drums-right.reverb:18@2s:smooth
  Other.evolve:menacing@20s:smooth
}
These are the original lyrics.
```

Single-line `{Drums.pan:center Drums.reverb:18}` remains valid. Braces
must enclose one complete production block per section; a second block,
nested blocks or an unterminated block are rejected without saving.
Production directives **outside** braces are not interpreted as effects;
keep ordinary lyric lines outside braces. Song Harbor renders saved
multi-directive blocks one directive per line when reloading the whole-song
editor; your lyrics and original effect semantics are unchanged.

Validation errors still report `Line N` based on the actual imported
text lines, compatible with **Go to line N** in the editor. The parser
accepts mixed spaces and line endings; it does not require you to convert
Windows text files before importing.
