# Section intelligence and dynamic scripting — approved sprint

Approved Oct 22, 2026 after mastering The Logo and the Maw. User wants concise section-header hue driven by intensity, and *neutral unused space at the opposite edge* to represent channel imbalance.

## Delivered first slice

Sound cleanup → Analyze mix now extracts post-processing stereo section metrics and paints the existing draggable section headers. Hue runs subtly from cool (less intense) to warm (more intense); intensity is normalized within the song. If left-heavy, neutral background shows at the **right edge**; if right-heavy, neutral space shows at the **left edge**. Tooltips give section RMS, peak, L/R balance and side/mid width. No fake defaults or source-only visual estimates before the mix scan. The header design retains section boundaries, resize/drag, and the existing full-width timeline. This is a measure, not a DSP modification.

## Delivered second slice: explicit stem gain (awaiting local audio QA)

The section sheet now recognizes `Drums.gain:+0.75@2s:smooth` and `Vocals.gain:-2.5@1s:linear`.
Gain is expressed in dB relative to the saved manual stem fader; the audio engine
uses multiplicative gain curves in both synchronized audition and offline WAV export.
Gain inheritance is sticky across sections and `all.reset` restores a neutral 0 dB
section offset. Added parser/import/reset regression tests. This does not implement
`auto.gain` or `all.gain`. Local build and listening QA are still required.

## Delivered third slice: broadcast defaults and editor focus

Whole-song editor no longer re-selects a section header on every text change.
Broadcast directives now support `all.gain`, `all.pan`, `all.width`,
`all.reverb`, `all.space`, and `all.eq1` through `all.eq3`.
Explicit stem/effect directives override broadcast defaults in the same
section, regardless of token order. EQ precedence is per band. The authored
`all.*` notation persists in round-trip exports; import expands it for
the existing DSP pipelines. `all.reset` remains an exclusive operation.
Unsupported `auto.*`, `all.comp`, `all.duck`, and `all.deess` are
rejected until dedicated semantics are implemented. CI and local audition QA
are required before this slice can be considered fully verified.

## Fourth slice: hybrid auto-pan (implementation awaiting local listening QA)

`auto.pan:center@6s:smooth` now compiles into a section-scoped, bounded solver.
The backend persists request metadata, explicit/inherited protected pan sources,
and separately protected explicit/inherited gain sources. Browser-side DSP uses
decoded stems and saved mixer faders, estimates dry-stem section channel energy,
and selects small complementary pan corrections on unprotected stems.

- Explicit/inherited stem or broadcast pan remains locked; `all.reset` clears
  protection for subsequent sections.
- The pan-search cap is 0.24 pan units from the current setting; gain compensation
  is secondary and limited to +/-0.35 dB, never on explicit gain-protected stems.
- Smooth transitions default to 8 seconds; specify `@6s:smooth` to change.
- The solver runs on section/mixer updates, not as a continuously moving servo.
- It reports predicted before/after stereo balance and warns when the target
  is unattainable with available stems. The estimate is computed from *dry*
  source energy and does not account for downstream EQ, compression, space,
  reverb or inter-stem phase interactions. Sound Cleanup > Analyze Mix remains
  the authoritative effects-processed measurement after rendering.
- No automatic master loudness adjustment and no `auto.gain:0` solver yet.
  Offline WAV export and playback use the same generated curves, with a strict
  peak/headroom check still required before publishing.

**Important:** A song sheet that explicitly pans every stem in every section
leaves the solver with no freedom. For the Logo and the Maw, import
`docs/qa-the-logo-and-the-maw-auto-pan.txt`, which preserves intentionally
placed vocals/bass/guitar while leaving drums/piano/other eligible for balancing.
Do not compare auto-pan using the old fully pinned sheet and expect it to move.

## Next steps — remaining syntax accepted in principle, not yet executable

Example proposed section: 

```text
[Verse 2 1:09.278-1:31.339]
{Vocals.pan:left.32@4s:smooth Drums.gain:+0.75@3s:smooth auto.pan:center@8s:smooth auto.gain:0@8s:smooth}
```

The importer supports explicit/broadcast effects and `auto.pan:center`. Other `auto.<effect>` solvers, including `auto.gain:0`, remain unimplemented. Do not copy the full illustrative example into saved sections until `auto.gain` exists.

- `Stem.effect`: explicit, highest priority; must never be silently overridden by automation.
- `all.effect`: default target broadcast to all eligible stems not explicitly set in that section. Explicit stem directive wins. This is not an analyzer.
- `auto.effect`: analyzes rendered section to optimize remaining unprotected, eligible stems within safe bounds; report any unmet goal. Deterministic, non-destructive, A/B previewable.
- `auto.pan:center`: keep fixed intentionally left-panned vocals while using free stems for complementary offset. Target post-processing L/R loudness near center, not exact sample-level equality. Preserve inherited protected pans. Maximum pan correction cap and deadband configurable; calculate once per section, no constantly moving live pan servo.
- `Drums.gain:+0.75`: stem-specific section gain in *dB relative to saved base stem level*. Gain transitions in seconds with smooth/linear curves. No accumulation across renders.
- `auto.gain:0`: maintain this section's existing reference perceived loudness (0 dB change versus the same section before proposed stem-gain edits), adjusting only unprotected stems. Example: lift drums +0.75 dB and reduce remaining free stems to compensate. **Not** target of 0 dBFS or 0 LUFS. Use gated section LUFS, and have a deterministic fallback for short/quiet sections. Report target tolerance/errors and ensure no peak clipping.
- For simultaneous `all.effect` and `auto.effect`, protected explicit/all choices may exhaust optimization freedom: report unattainable goal rather than violate settings.
- Future `auto.gain:+1` may request the entire section +1 dB vs reference; `auto.pan:left.20` may request a left-biased overall mix. Only implement effect names when solver exists; reject unknown names loudly.

Suggested implementation sequence: Section visualization → per-section stem gain → all.effect grammar and overrides → auto.pan:center → auto.gain reference matching → independent longer reverb returns / dry fade → loudness-matched A/B. Gain-before-auto.gain reduces moving parts.

## Fifth slice: audible atmospheric ending and visible scan diagnostics

- When `Master.tail` is nonzero, the deterministic room impulse grows from
  1.7 seconds to as much as 7 seconds, decaying more slowly.
- Dry audio follows `Master.fade`; wet excitation stays active through most
  of the musical fade, ramps down during the last 0.8 seconds, and previously
  produced reverb continues naturally into the post-roll.
- The same convolution impulse and wet-drive envelope run in synchronized
  playback and offline export. Existing songs without a tail retain the short
  impulse response.
- Timeline color scanning is still **on demand**. In a screenshot showing
  `Scan`, no measurements are currently available. Click Scan, and the
  button changes to Redo with stronger visible intensity hues. Errors now
  appear directly under the section lane, not only in Sound Cleanup.
- QA script: `docs/qa-the-logo-and-the-maw-extended-fade.txt` includes all
  13 sections, adjusts the final outro to `Master.fade:7s:smooth`,
  `Master.tail:5s`, and increases the outro vocal reverb send from 35 to 45.
  Confirm the resulting 4:05 export rings naturally rather than chopping.
  Compare against the earlier 4:03 version using level-matched listening.
- Long convolution buffers cost extra RAM and DSP. For now, tail settings
  are limited to 10 seconds and the impulse is capped to 7 seconds.
  Real-time/local listening and export peak QA remain required.

## Pre-0.2.1 completion: timestamped YouTube captions and section hover diagnostics

- Current track is accepted musically; no `auto.gain:0` treatment is needed for
  *The Logo and the Maw*. The right-biased second pre-chorus is deliberate.
- The center draggable section title hover now exposes the same scanned
  intensity, RMS, peak, stereo balance, and side/mid width metrics as its
  background strip. Hovering no longer loses the analysis to the drag hint.
- Whole Song Section Text now includes **Lyrics SRT**. After applying the
  saved section sheet, generate an editable, timestamped .srt preview, inspect
  it against the vocals, and download a UTF-8 YouTube-compatible caption file
  named after the song.
- Caption grouping defaults to two lyric lines per cue, uses three short lines
  when practical without stranding the last line, or a single exceptionally
  long line. Timing is estimated by evenly distributing lyric lines between
  saved section boundaries. Blank lines and standalone parenthetical performance
  directions are excluded. Instrumental sections with no lyric text produce no
  cue. Lyric export never changes saved source data.
- Captions are *estimated*, not phoneme-aligned. Review the exported file
  against playback and adjust the editable SRT preview for actual entrances
  and holds. YouTube Studio > Subtitles > Upload file > With timing accepts
  plain UTF-8 SRT.
- Backend SRT unit tests cover deterministic output, cue grouping, timing,
  skipped directions, skipped lyric-less sections and missing-data errors.
  Full user QA of timed lyrics is pending.

## Ending treatment

Retain separate dry bus and wet return. The existing 1.7-second room impulse decays quickly, so the current exported extra seconds contain little reverberant energy. Add longer adjustable IR/decay and separately automated wet-return levels/width at the end. Source stops, effect return rings naturally; allow vocal to fade into environmental texture rather than cut off. Verify offline export and synchronized audition match.

## QA requirements

Use the source/master A/B as the established baseline; do not increase whole-song compression or broaden loudness range by default. Test all-protected stems, mute/solo, split L/R channels, near-silence, short sections, zoom, timing boundaries, gain headroom, monotonic/clear transitions and no clip-on-export. On any mix change, mark section insight colors stale or clear them until re-analysis. Show exact metrics and calculated auto compensation in a review UI before applying; never silently modify user intent.