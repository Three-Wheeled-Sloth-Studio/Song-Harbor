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
