# Section-aware dynamics: initial implementation (2026-10-21)

## Delivered on main

- The shared-clock Web Audio graph now inserts a neutral-by-default DynamicsCompressorNode and a ducking GainNode after the existing three-band EQ and before stereo width/spatial processing. The same topology is built by the offline WAV renderer. Existing EQ, pan, width, spatial reflections, reverb and ending logic are retained.
- Compressor defaults: threshold -18 dBFS, ratio 1:1 (no compression), knee 12 dB, attack 12 ms, release 180 ms; no makeup gain. Scripts may change threshold (-60 to 0 dBFS) and ratio (1 to 4). Attack/release are fixed until a validated control/interface and gain-reduction QA exist.
- Ducking defaults to no attenuation. A deterministic 50Hz RMS detector reads the unmodified decoded vocal buffer(s), combining split L/R when active. Attack 35 ms, release 250 ms. Envelope activity rises between roughly -30 and -15 dBFS; requested reduction is bounded 0..12 dB. The resulting gain curve is scheduled in both live and offline graphs; source stems are never written back. It is approximate envelope ducking, **not** a true Web Audio sidechain input or an AudioWorklet compressor.
- Save script examples:

```text
[Verse 0:12-0:35]
{Other.comp:-18,2@2s:smooth Guitar.duck:3@1s:smooth}

[Chorus 0:35-1:05]
{Other.comp:-23,2.5@2s:smooth Guitar.duck:5@1s:smooth}

[Outro 1:05-1:20]
{Other.reset@2s:smooth Guitar.duck:0@1s:smooth}
```

- `Track.comp:thresholdDb,ratio@transition:smooth` and `Track.duck:depthDb@transition:smooth` are validated by the established one-line production grammar. Dynamics values inherit across omitted sections. `Track.reset` and `all.reset` restore the neutral dynamics defaults too. The import path materializes per-section targets, persists them with the project, and exports them to the frontend. Existing saved projects without dynamics entries remain neutral.
- No UI knob or new sidebar panel was introduced. Author dynamics directly in the existing Sections script editor. Existing compact icon-first Tools redesign remains on roadmap.

## Acceptance and outstanding validation

GitHub Actions frontend TypeScript/build and backend tests are the only available execution checks. This change has not been heard on Windows; the in-app updater/relauncher has not been executed in the user's Windows instance, and the full EQ save-close-reopen plus precise live/offline audio parity has not been verified acoustically/numerically. Do not promote the results to Windows acceptance until tested. Follow `refs/handoffs/currentHandoff.md` for the original regression matrix.

Test a preexisting saved song without new script lines first, including a null-effect WAV regression, unchanged fades/tails, and a vocal split L/R case. Then author very gentle ducking (2-3 dB) on Other/Guitar in one section, compare in-app and WAV, seek into and out of transitions, save and reopen, and ensure the section script round-trips exactly. Test mute/solo behavior of vocal key, successive edits, and exported mix cache invalidation; these are not fully acceptance-tested.

### Important limitations of this first slice

- This is deliberately conservative, source-aware mix automation, not mastering. Metering, makeup gain, knee/attack/release scripting, loudness-matched bypass, robust vocal-key isolation from bleed, true multiband de-essing and full effects-rack UI are subsequent work.
- The duck envelope is scheduled at 50 Hz; large projects with many duck targets may incur AudioParam scheduling overhead. A dedicated shared AudioWorklet detector and per-group gain-reduction metering is a later optimization.
- Duck source derives from decoded unprocessed vocals at the current monitor/export stem level. Verify desired behavior if vocal level, mute/solo, or source-channel mode changes.
- Do not treat offline/preview shared topology as numerical null-test proof. In particular, spatial/reflection/reverb and compressor runtime scheduling still require real QA.

## De-essing foundation and next slice

Use a frequency-selective detector (e.g., band-pass 4-10 kHz, adjustable and tested for voice range), not wholesale static high-frequency EQ. Compare band-limited short-window energy against full-range vocal energy, with hysteresis and tunable sensitivity. Candidate events become time-bounded editable markers and optional phrase-level, non-destructive production instructions. The gain action should be capped initially at 1-3 dB and attack/release should avoid consonant smearing. Start with offline deterministic candidate analysis, then implement a shared live/offline processor with the same detector and automation values (potentially an AudioWorklet) before exposing Apply. Do not claim de-essing is operating in the current release.

## Roadmap retained

Short term: gain-reduction meter, edit/persistence and null/peak regression tests, master trim persistence, true de-esser prototype, phrase/time-range automation and click/fizz/phase/bleed cleanup suggestions. UI debt: compact icon-first Tools, details in inspector/popouts, no lost waveform width. Longer term: full effects rack, VST3/plugin architecture feasibility, DAW integration and targeted Second Take workflow.
