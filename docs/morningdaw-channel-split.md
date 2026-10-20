# MorningDAW handoff and stereo-channel extraction

Status: implementation committed, Windows validation pending.

## MorningDAW
MorningDAW is supported as an optional target in Song Harbor's DAW handoff selector, alongside Waveform Free and Audacity. The editor is available for Windows and supports importing WAV audio files. Official product/manual: https://edu.morningdewmedia.com/pages/morningdaw/ and https://edu.morningdewmedia.com/pages/morningdaw/manual/.

Song Harbor can locate a MorningDAW executable through common Windows install paths, uninstall registry entries, Start Menu shortcuts, or explicit Browse/Locate. It remembers the selected editor on this machine and offers the publisher download page. **Native .mdproject generation and automatic multi-track import are not claimed or implemented.** Prepare stems exports the original six aligned WAVs and manifest, then Launch starts MorningDAW; the user creates a song and manually drags each WAV onto a separate track at 0:00. The bundle contains import instructions; it remains a separate non-destructive export.

## Split stereo channels
The Song Workspace contains a collapsed `Split stereo channels` utility. Select any subset of the existing six stems (all are selected by default) and render their left and right channels to **independent mono 32-bit float WAV files** using the locally configured FFmpeg and FFprobe. Exports are generated under the song's `exports/Channels-<unique-id>/` with a manifest, fixed 0:00 start position, source stem reference and per-channel metadata. There is no original overwrite, no source modification and no registration of outputs as new separator stems in the canonical six-stem set. Each run creates a new folder; a failed run discards its temporary output. Only stereo two-channel sources are accepted; mono/multichannel stems report an error instead of silently duplicating/losing channels.

Important: this is **channel extraction, not further instrument or male/female vocal separation**, and mono tracks will often be highly correlated when the source has a narrow stereo image. Pan them separately only where the underlying channel content supports it; channel splitting alone does not create a wide soundstage.

## Smoke checks
- DAW dialog lists MorningDAW, Detect/Locate remembers a verified installation, Prepare generates six original WAV copies, Launch opens editor without claiming automatic import.
- Stem mixer compact utility permits one/all stem selection, exports twice the number of selected stereo stems, Open files navigates to the generated folder.
- Playback alignment after importing L/R files at 0:00; compare original stereo stem against recombined L/R.
- Verify original hashes unchanged, no partial folder on FFmpeg failure, no clobbering an earlier export.
- Missing FFmpeg goes through existing contextual recovery.
- Check actual executable names/shortcuts on Predator/Omen; user has not been asked to run live tests.
