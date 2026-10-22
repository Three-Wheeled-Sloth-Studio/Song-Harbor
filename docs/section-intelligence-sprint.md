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

## Ending treatment

Retain separate dry bus and wet return. The existing 1.7-second room impulse decays quickly, so the current exported extra seconds contain little reverberant energy. Add longer adjustable IR/decay and separately automated wet-return levels/width at the end. Source stops, effect return rings naturally; allow vocal to fade into environmental texture rather than cut off. Verify offline export and synchronized audition match.

## QA requirements

Use the source/master A/B as the established baseline; do not increase whole-song compression or broaden loudness range by default. Test all-protected stems, mute/solo, split L/R channels, near-silence, short sections, zoom, timing boundaries, gain headroom, monotonic/clear transitions and no clip-on-export. On any mix change, mark section insight colors stale or clear them until re-analysis. Show exact metrics and calculated auto compensation in a review UI before applying; never silently modify user intent.