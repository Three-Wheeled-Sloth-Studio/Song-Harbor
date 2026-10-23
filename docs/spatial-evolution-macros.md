# Spatial Evolution Macros: Menacing

Status: Proposal only. Not implemented. 
Origin: Infra Choir production experiment, "Call of the Electric Siren" (October 2026).
Related: [stereo-production-effects-plan.md](stereo-production-effects-plan.md), [user-guide.md](user-guide.md), [production-timeline-script-ux.md](production-timeline-script-ux.md).

## Problem

Section automation now supports independent left/right channel control for gain, pan, three-band EQ, and reverb send, plus parent-stem spatial width and reflections. This enables spatial storytelling, but producing a long organic progression requires repetitive and error-prone directives. Simply widening a correlated near-mono recording may produce little audible effect; naive stereo manipulation can also cause phase cancellation, loss of impact or drifting loudness.

We want reusable *intent-based* spatial macros that create dramatic change over time, while retaining explicit control and the ability to inspect, edit, and bypass their constituent effects.

## First macro: `menacing`

Illustrative candidate notation only, **NOT valid in the current parser**:

```text
{Other.auto.space:menacing@20s:smooth}
```

Desired behavior: gradually turn a narrow environmental stem into a darker, wider, more asymmetric and unnerving acoustic environment. Unlike a generic stereo widener, this macro should create a sensation of something expanding and moving around the listener while preserving a clear central anchor. It should be intentionally restrained rather than an automatic maximal effect.

The flagship musical contrast is an expanding, threatening environment surrounding an increasingly narrow, dry and intimate vocal. This can be authored as separate automation on `Other` and `Vocals`; the macro must **not** silently alter unrelated stems.

### Macro processing intent

1. **Analyze source first.** Estimate interchannel correlation, mid/side energy, low-frequency distribution, perceived loudness and peak headroom. If nearly mono, do not rely on width scaling alone.
2. **Create controlled lateral differentiation.** Gradually vary left/right EQ coloration, early-reflection balance, predelay and stereo ambience. Preserve transients and avoid obvious periodic auto-pan or chorusing unless explicitly requested.
3. **Darken selectively.** Reduce upper-mid harshness in the environment, increase perceived low-mid threat without muddying vocals or drums, and avoid boosting sub-bass into the sides.
4. **Build spatial asymmetry.** One side may feel nearer and more defined while the other is distant and reverberant, with slow evolving movement and no abrupt jump at section boundaries.
5. **Protect the center.** Keep kick, fundamental bass energy and the focused lead voice stable unless the user separately scripts them.
6. **Respect inheritance and duration.** Smooth progression over the requested duration, seamlessly inheriting section automation state rather than resetting at every section boundary.
7. **Level and mono safeguards.** Loudness-match against bypass, constrain true peaks, monitor phase/correlation and mono fold-down, automatically reduce wet or decorrelation strength when compatibility degrades.
8. **Stay non-destructive.** Parameter automation should be inspectable/editable and reversible; do not rewrite source stems.

### Proposed future control surface

- `auto.space:menacing` is the user-facing *intent*. Distinguish it from current numeric `Stem.space:0..40` reflection send.
- Optional intensity, movement, asymmetry, wetness and low-frequency protection parameters could be added later, **after** the minimal macro proves useful.
- Show the generated automation curves/left-right parameters in the UI and provide a single A/B bypass of the macro.
- Allow user-authored explicit child effects to override or coexist with the macro under documented priority rules. Detect contradictory automation rather than silently fighting manual directives.
- A macro should not require cloud inference or a large model: start with CPU-based signal analysis and deterministic DSP. Consider generated environmental layers separately.

## MVP implementation path

**Phase 0: measurement and audition**
- Use representative narrow-stereo sources, particularly `Call of the Electric Siren` with `Other` and `Vocals` stems.
- Confirm what the current channel graph and available reverb/reflection DSP can achieve.
- Establish A/B loudness matching, stereo correlation, mono fold-down, and true peak readouts.

**Phase 1: deterministic preset / script expansion**
- Build a macro resolver that expands `menacing` into supported automation envelopes and any small new DSP parameters required for effective near-mono widening.
- Apply left/right EQ and reverb imbalance with gradual movement; optional decorrelated early reflections as a controlled stereo source.
- Expose expanded directives in the interface. Store the original intent and versioned resolved parameters for reproducibility.

**Phase 2: adaptive safeguards and UI**
- Analyze and adapt macro strength based on stereo correlation, frequency content and loudness without audible pumping.
- Provide intensity and safe-range controls, preview/bypass, and warning/override for mono incompatibility.
- Ensure preview matches exported WAV, including reopening projects and changes across section boundaries.

**Phase 3: macro family (future, not prerequisite)**
- Candidate siblings: `intimate` (focused dry center, diffuse quiet tail), `looming` (slow distant swell), `mechanical` (more rigid spatial movement), and `unraveling` (increasing unstable ambience). These names are exploratory.

## Acceptance criteria

- On a highly correlated stereo stem, produces an audible but restrained widening/depth effect compared with simple width scaling, without merely increasing level.
- On an already wide stereo stem, does not over-expand or introduce intrusive phase artifacts.
- Low frequencies stay anchored; lead vocal intelligibility and rhythmic impact survive in stereo **and mono**.
- Macro onset and end follow specified transitions smoothly; transitions across adjacent sections do not click or abruptly reset.
- Explicit manual directives and macro priority are documented and testable.
- Live audition and export agree, and the source recording is unchanged.
- Provide golden-fixture tests for near-mono, wide-stereo, transient-heavy, vocal-bleed and silence cases; document any unavoidable tradeoffs.

## Track-specific pilot: Call of the Electric Siren

Target the `Other` stem first, evolving from intimate, narrow and relatively dry at the intro to very wide, ominous and asymmetric around the bridges and final chorus. Independently narrow and dry `Vocals` to make the siren feel increasingly close. Preserve centered bass and punchy drums. Compare bridge 2:53-3:56, final chorus 4:28-5:03 and outro 5:03-5:41 against the original recording at matched loudness. If vocal bleed in `Other` makes spaciousness muddy, reduce reflection send or use more selective source material.

## Non-goals

- This is not a new generative music model, instrument separator, or automatic composition tool.
- Do not promise true instrument placement from nearly identical L/R waveforms without decorrelation or additional source information.
- Do not automatically apply `menacing` across all stems or presume the listener always prefers maximal width.

## Open implementation questions

1. Should resolved macros be stored as immutable, versioned envelopes or recalculated when the source stem changes?
2. How should macro and explicit parent/child script settings combine: explicit overrides, effect-specific priorities, or conflict errors?
3. What correlation/mono-compatibility thresholds and loudness tolerances are acceptable for automatic protection?
4. Can existing `space` reflections provide the required asymmetry, or do we need dedicated decorrelated stereo ambience/predelay?
5. How should a macro behave if split L/R child routing is disabled? Prefer a documented parent-stereo fallback rather than a silent no-op.
