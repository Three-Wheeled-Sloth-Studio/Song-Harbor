# Instrument library: first SF2 integration (2026-10-29)

**Status:** source committed to **main**; Windows UI, FluidSynth and end-to-end audio rendering QA pending.

## Workflow

- Stem tools -> MIDI -> extract/edit notes -> **Instrument** and **Pack** dropdowns.
- Pack defaults to **All packs** and filters Instrument; choosing an instrument automatically uses its owning pack. Current preset listing is generated from the actual SoundFont `phdr` program/bank table, not a hardcoded General MIDI label list.
- **+ SF2** imports a local user-chosen SoundFont; the UI never downloads a library or claims redistribution rights. Install is capped at 512 MB, validates RIFF/SF2 and stores data-only soundfont and an indexed manifest under `<SongHarbor runtime>/instrument-packs/user-<id>/`.
- Built-in Song Harbor Core synthetic voices remain available without external dependencies.
- To render an imported SF2, install the official **FluidSynth** executable. Song Harbor discovers `fluidsynth` on PATH, `<runtime>/tools/fluidsynth/bin/fluidsynth.exe` or explicit `SONG_HARBOR_FLUIDSYNTH` environment variable pointing to the executable. The UI displays a short required-engine status when unavailable.
- Render reads a validated pack/preset identifier, makes fresh standard MIDI with bank and program selects, runs FluidSynth using fixed CLI arguments, then normalizes duration/channel layout to a replaceable candidate WAV using configured FFmpeg. The source stem never changes.
- MIDI export is independent of the sound engine. Imported preset program changes persist with that MIDI export.
- Acceptance still uses the existing separate removable track; all settings are nondestructive.

## Pack contract and future commercial features

Current per-pack manifest is `schema_version:1` containing `id`, `name`, `engine:sf2`, `source:user-installed`, `sha256`, `instruments[]` with instrument `id`, `name`, `program`, `bank`. The system never loads pack executables.

This is a source-backed adapter seam, **not yet** a TWS commercial-pack marketplace, licensing or entitlement system. For future signed/paid packs: versioned metadata, independent publisher ID, sample hashes, signature, compatible engine/version declarations, archival project pinning, local offline entitlements, removal/upgrade and ownership UX. Permission to use a SoundFont commercially in compositions is not permission to redistribute its samples.

SFZ sample maps and VST3/CLAP hosting are **not implemented** in this release. The SFZ backend must be implemented as a separate, compatible sampler engine with explicit license/security review, rather than falsely treating SF2/SFZ as interchangeable.

## Recommended immediate sound

**MechSounds by John Oestmann**: public-domain/CC0 synthetic mechanical sound bank with a published `.sf2` file, and MIT-licensed creation projects. An unusually good match for Infra Choir's industrial/orchestral palette; choose its SF2 download and import it using + SF2. Official page: https://johnoestmannmusic.com/mechsounds/

**Karoryfer x Bigcat Cello**: real sampled CC0 cello, including sustain/staccato/pizzicato. Excellent next *SFZ* test once SFZ rendering is supported, not a bank this SF2-only release can presently load. Official: https://shop.karoryfer.com/pages/free-karoryfer-x-bigcat-cello

## QA gates

1. `python -m unittest discover -s app/backend/tests -p 'test_instrument_library.py' -v`
2. `python -m unittest discover -s app/backend/tests -p 'test_bass_midi.py' -v`
3. `python -m py_compile app/backend/instrument_library.py app/backend/bass_midi.py app/backend/server.py`
4. `npm run build` from `app/frontend`.
5. Windows: import a real SF2, verify discovered presets and both dropdown filters, install/configure FluidSynth, render preview A/B, MIDI program/bank, save candidate, remove new track, confirm untouched source.
6. Failure tests: no FluidSynth, malformed SF2, oversized SF2, empty/missing preset, import without network, duplicate names across separate packs, bank selection, long region timeouts, and dirty song state.
7. Check project portability: the candidate WAV survives even if an original instrument pack becomes unavailable; a fresh render requires the pack to be reinstalled.

No paid or third-party samples are bundled or repackaged in this slice.


## Starter default library (2026-10-29)

**GeneralUser GS 2.0.3** is the first optional downloadable starter, from the author's official repository. It contains **261 melodic presets and 13 drum kits** in approximately 31 MB and is well suited to FluidSynth 2.3+. Its custom license permits commercial music production; **Song Harbor never bundles, resells, or repackages the bank**. Click **↓ Starter GM** in the MIDI Instrument panel to request an explicit download. The backend validates the HTTPS source, limits size to 40 MB and compares SHA-256 to the reviewed 2.0.3 bank before installing through the same user-import SF2 registry. If upstream changes, the checksum deliberately blocks installation until reviewed. Manual **＋ SF2** import remains available.

In the Instrument dropdown, usable general-purpose presets appear in the initial favorites section with **★**: cello, contrabass, tremolo/pizzicato strings, string ensemble, choir, synth voice, orchestral hit, trombone, French horn, brass/synth brass, distorted guitar, electric/synth bass, warm pad. All other presets remain visible. After starter installation, **Cello** is selected by default while **Pack** selects the installed GeneralUser pack. The global default Pack filter before installation remains **All packs**.

No instrument data enters the source repository. CI tests use a tiny generated fake SF2 fixture and mock network requests; no real download in CI.

Original author: https://www.schristiancollins.com/generaluser

Canonical bank: https://github.com/mrbumpy409/GeneralUser-GS

We should evaluate this bank sonically first; for a genuinely expressive *Blackwater Firmware* solo cello, the CC0 Bigcat Cello SFZ sample instrument is still a better follow-on once SFZ is supported.

**Release QA remaining:** verify Windows download, trust/checksum, FluidSynth discovery, starter preset listing, live audition, and no source mutation through main launcher.


## 2026-10-29: FluidSynth path in Settings

Open header gear **Settings → Components → FluidSynth**. The compact row shows detection status, editable executable path, **Browse** (native Windows file picker), **Detect** (usual installed locations/PATH), and **Verify & save**. Choose `fluidsynth.exe` or its containing `bin` directory. The backend invokes `-V` with an 8-second timeout and checks the FluidSynth response before persisting `fluidsynth_executable` into the same machine-local `config/settings.json` used by FFmpeg and working-directory preferences. This is effective immediately for SF2 previews, without application restart. The installed pack and project data remain in the data root and aren't modified.

FluidSynth auto-discovery still works when no override is configured. Future installer workflow should only be added after the separately installed Windows executable completes real render QA.

The primary app header is sticky at viewport top, beneath floating tools/dialogs, and has compact responsive branding/action spacing. Verify scrolling both Library and Song views, opening menus/dialogs, and narrow widths. This is a layout stabilization, not a full header redesign.


## Candidate level during A/B and acceptance (2026-10-29)

- **MIDI reinstrument** and **ACE accompaniment** both expose compact **◖ Candidate volume** trim during A/B/Solo. Default 0 dB; bounds -12 to +9 dB, 1 dB steps; reset returns to 0 dB.
- Level is handled through the already shared preview engine's `setCandidatePreviewTrimDb` in real time, not by altering the original/generated candidate. Selection persists through repeated auditions of the same candidate; new ACE candidates reset to 0 dB.
- **Accept / Add stem** now posts `preview_trim_db` to the existing track import endpoint. The server validates it before import and applies exactly the same dB volume adjustment **to the imported track's working WAV only** using FFmpeg during conversion. The candidate WAV and original uploaded track remain unmodified. Remove the imported track to undo.
- Positive trim can clip when converting to integer PCM; listen to high-level audio before acceptance. This uses a pre-mixer gain change and does not embed an editable future script automation; imported track mixer gain still works normally.
- All other regular imported stems default to 0 dB trim. Existing projects and generated tracks are unaffected.
- QA: change candidate trim while solo/A-B playback runs; A/B 0 and -6 and +3 dB; accept and compare track level with candidate at same blend/monitor; verify zero trim and existing stem import regression; project save/reload; remove imported track to undo; original/generated WAV hash unchanged.


## 2026-10-29: Combined replacement acceptance workflow

**Integrated acceptance, not standalone acceptance QA**. MIDI re-instrumentation defaults to **Replace region**; ACE accompaniment defaults to **Layer**. Both offer Replace / Layer before adding, and both use the already implemented candidate-volume trim, applied to the added track's working WAV. ACE's optional Replace requires explicit source-stem selection. The eventual ACE/YuE2 regeneration and revoice features should default to Replace when built; this does not claim those operations exist today.

**Replace** is one manifest transaction: add a removable rendered track at its timeline position, persist a short-fade replacement mask linked by stable permanent source/replacement track IDs, and leave the original audio and all existing section-production automation exactly as they were. The mask is stored as `replacement_masks[]` and applied as a **multiplicative independent region-gain layer** after the original scripted section gain. This avoids clobbering other gain, EQ, pan, or reverb instructions or rewriting section scripts. It is an inspectable companion automation record rather than literal inline edits to section text. Removal of the replacement track removes its mask and restores the original stem in the same manifest change. Repositioning a masked replacement or removing its source while linked is blocked until the replacement is undone, preventing silent desynchronization.

**Layer** adds a removable track without touching the original, matching accompaniment expectations.

**Waveforms** render gain-driven opacity (base mixer gain including mute/solo × scripted section gain × independent replacement masks) rather than signal RMS or perceived loudness. Active split L/R children inherit the parent gain and replacement mask, in addition to their channel-specific gain. Fully muted regions become near-background with a minimum opacity for visibility.

**Transport / export parity:** SharedClockAudition now uses a dedicated non-destructive replacement gain node in the live synchronized playback chain, and the same mask envelope is applied in the offline WAV rendering path. Unchanged masks do not restart playback during routine automation refreshes.

### Mandatory combined QA before production use

1. MIDI extraction -> Cello rendering -> A/B candidate volume adjustment -> **Replace** acceptance. Confirm one new instrument stem appears and original Bass attenuates only within replacement span, with short click-free boundaries.
2. A/B the same candidate as **Layer**. Confirm both sources remain audible; no replacement mask is created.
3. Original Bass existing gain/pan/EQ/reverb automation persists byte-for-byte after replacement, after save/reopen, and after removing the replacement. No automation is flattened or reset.
4. Waveform opacity follows base gain, scripted section gain, mute/solo, and replace mask; split-channel L/R rows should inherit the parent gain and mask. Opacity must not depend on waveform RMS.
5. Offline WAV export reproduces the muted original region and adjusted accepted candidate level; compare to live mix at the same trim and headroom.
6. Remove the accepted replacement and confirm immediate restoration of original audio and waveform opacity, including across application restart.
7. ACE accompaniment default Layer and live volume trim carry into accepted track; optional Replace requires a source selection.
8. Ensure invalid/expired source IDs, imported-clip bounds, malformed replacement requests, overlapping replacement regions and duplicate adds fail safely and do not corrupt projects.
9. Confirm the original stem and initial generated candidate WAV hashes are unchanged. Any clipping induced by positive trim must remain detectable; no hidden limiter.
10. Run backend track import/lifecycle tests, frontend replacement-envelope tests, and local Windows TypeScript build. **Do not treat feature implementation as final production QA without these checks.**

Limitations: saved replacement masks are a separate automation layer and do not yet have dedicated editing rows in the textual script editor. The Undo pathway is currently removal of the accepted replacement track. Future inline-script visualization should show replacement masks distinctly instead of overwriting authored instructions.
