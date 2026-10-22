# Section intelligence and dynamic scripting — approved sprint

Approved Oct 22, 2026 after mastering The Logo and the Maw. User wants concise section-header hue driven by intensity, and *neutral unused space at the opposite edge* to represent channel imbalance.

## Delivered first slice

Sound cleanup → Analyze mix now extracts post-processing stereo section metrics and paints the existing draggable section headers. Hue runs subtly from cool (less intense) to warm (more intense); intensity is normalized within the song. If left-heavy, neutral background shows at the **right edge**; if right-heavy, neutral space shows at the **left edge**. Tooltips give section RMS, peak, L/R balance and side/mid width. No fake defaults or source-only visual estimates before the mix scan. The header design retains section boundaries, resize/drag, and the existing full-width timeline. This is a measure, not a DSP modification.

## Next steps — syntax accepted in principle, not yet executable

Example proposed section: 

```text
[Verse 2 1:09.278-1:31.339]
{Vocals.pan:left.32@4s:smooth Drums.gain:+0.75@3s:smooth auto.pan:center@8s:smooth auto.gain:0@8s:smooth}
```

The current importer **does not implement** these new `all.<effect>` or `auto.<effect>` names or section gain. Only `all.reset` exists. Do not copy the example into saved sections until grammar and DSP are implemented.

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