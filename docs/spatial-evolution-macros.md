## 2026-10-23 first executable implementation (supersedes proposal-only status above)

The deterministic `menacing` preset is now recognized by Song Harbor production
script imports; use `Other.evolve:menacing@20s:smooth`. This is the
**first constrained macro slice**, not the complete adaptive evolution system.
Older proposal statements saying the macro is unimplemented are historical.

### Usage

```text
[Bridge 2:53-3:56]
{Other.evolve:menacing@20s:smooth}
```

Keep the whole original lyric sheet and existing directives intact. Place a
single macro in the existing one-line curly-brace production block for the
target section. The example section header is illustrative, not a request
to replace the song's saved section sheet. A 20-second smooth evolution
starts at the section's start and remains part of the inherited automation;
subsequent explicit directives can redirect it. The engine's existing
section-clock transition compiler remains the timing authority.

### Preset v1 (deterministic existing DSP, song-relative timing)

For the named parent stem ONLY, the resolver emits:
- `pan:right.18`, `width:125`, `space:18`, `reverb:16`;
- EQ1 380 Hz / Q .9 / +1.1 dB; EQ2 3200 Hz / Q .8 / -1.7 dB.
- If split L/R children are available, left gets a reverb send 11%
  and EQ2 3500 Hz / Q .9 / -0.8 dB; right gets reverb 23% and
  EQ2 2600 Hz / Q .9 / -2.1 dB. If not split, a parent-only fallback
  applies. No other parent stems or vocals are changed.
- All generated controls inherit the requested `@Ns:smooth|linear`
  timing. Source WAVs are not rewritten.

Explicit authored effects for the same target, type and EQ band *within the
same section* win regardless of token order. Parent effects remain independent
of child effects; child reverb overrides are not additive. The authored
macro remains in saved section text and is expanded to ordinary typed
automation targets during materialization; manual macro resolution is
deterministic and versioned `v1`. The same automation arrays are used
in in-app audition and offline WAV export.

### Limitations and QA remaining

- No adaptive correlation/mono/true-peak safety controller yet, no dynamic
  reflection predelay, no generative layers, and no independent macro-only
  bypass or visible expansion editor. Compare processed/original with the
  existing effect-bypass view and check stereo *and mono* on an actual mix.
- All generated effects are real existing controls; no model downloads or
  GPU requirement. Local Windows listening/export and transport QA pending.
- Macro override precedence currently addresses **the same section**.
  Cross-section hand-authored automation follows normal inherited section
  rules. Future macro/UI iteration should surface the generated curves and
  add single-macro bypass, per-effect intensity, and overlapping macro
  conflict visualization.
- Do not silently claim automatic center/mono protection until measured
  and calibrated.

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

## Architecture review (2026-10-23) — recommendation, not implementation approval

**Assessment:** Strong product direction. Prioritize deterministic, inspectable
automation over any opaque, model-driven 'make it menacing' effect. The
existing engine provides parent gain/pan/width/EQ/reverb, simple 13/19 ms
cross-reflections, and split-child gain/pan/EQ/reverb. There is no need for
a new model, GPU or external process for a first proof. Actual DSP
quality/mono safety still requires measured listening tests.

### Decisions proposed for an initial spike

1. **Keep macro intent distinct from explicit effect directives.** The
   illustrative `Other.auto.space:menacing@20s:smooth` is not accepted
   grammar. The `.auto.` namespace is already associated with solver
   behavior (`auto.pan`) and `Other.space` means a bounded reflection send,
   not a scene-level transformation. Consider
   `Other.evolve:menacing@20s:smooth` as a clearer separate family,
   or explicitly standardize `Other.auto.space` if preserving that
   vocabulary matters. Do not silently reuse the numeric `.space` token.
2. **Define the target as a song-time span.** `@20s` describes evolution
   duration, not a transition reset at the next section boundary. Store
   an anchored start time, macro duration, intensity/defaults, schema
   version, source track ID, and resolved envelope revision. Support
   deterministic re-resolution when the user intentionally refreshes,
   but preserve already accepted rendered automation in saved mixes.
3. **Prefer an inspectable macro compilation layer:** authored intent ->
   versioned resolution -> existing typed target curves -> the same live
   and offline audio graph. Show the resolved child EQ/gain/reverb and
   parent width/pan/space curves, with manual A/B/bypass and restore.
   Do not paste expanded macros into lyric lines or overwrite the
   user's carefully maintained whole-song script without an explicit
   accept operation.
4. **Precedence must be effect-specific and stable:** manual child
   directive wins for that child/effect; manual parent directive wins
   for parent effect; macro fills unclaimed targets. This rule should
   hold independent of textual directive ordering. Same-effect macro
   collisions should be rejected or surfaced for explicit choice.
   `all.*` remains a parent baseline. Source alias changes must
   migrate macro references by immutable track ID.
5. **The current DSP only enables a partial first result.** Parent
   mid/side width cannot widen truly mono input. Existing `space`
   cross-reflections have fixed delay times and symmetric send
   automation, so they provide decorrelation but do not implement the
   promised independently evolving reflection balance/predelay.
   The single common reverb convolver has limited channel-isolated
   placement, and split-child reverb is tapped before parent bus FX.
   First test an all-existing-effects preset; add distinct bounded
   L/R reflection sends and/or predelay only if listening demonstrates
   the missing effect.
6. **Split-state behavior must be explicit.** Split-child EQ/reverb
   curves operate only with active children. If unsplit stereo is
   selected, do not report that child asymmetry is active; either
   provide a documented parent-only fallback with reduced capability
   or require splitting with an actionable warning. Never silently
   split tracks, duplicate stems or swap native L/R routing.
7. **Safeguards are measurements before they are promises.** Track
   stereo correlation, frequency-dependent side energy, mono
   fold-down loss, integrated loudness and true peak, including short
   moving windows. The existing sound cleanup checks are not a
   comprehensive true-peak / integrated-LUFS verification. Start by
   warning/limiting parameter ranges and matching loudness in A/B.
   Add adaptive constraints only after calibration on representative
   music; don't apply an unmeasured 'safe' threshold.
8. **Preserve the musical anchor.** The macro targets only `Other`
   in the pilot. The contrasting narrow/dry `Vocals` progression is
   an explicit separate script or another accepted macro. Never
   spread macro directions to unrelated drums/bass/vocals implicitly.

### Suggested staged LOE (engineering estimates, not measurements)

- **Proof with existing automation and level-matched listening:**
  ~0.5–1 day. Build a manually expanded `Other` progression for the
  specified bridge/final chorus, compare to `width` alone, and record
  stereo/mono observations. No new parser token yet.
- **First usable deterministic macro resolver and UI preview:**
  ~2–4 days if using existing DSP. Extend typed manifest/scripts,
  resolve immutable envelopes, provide clear precedence/overrides,
  enable/reject/accept/bypass and test reopening/export parity.
- **Refined asymmetric reflections/predelay, robust automation
  collision handling and objective safeguards:** another ~3–7 days
  depending on signal-path and QA findings. Especially test
  per-child routing with parent processing and true mono compatibility.
- **Overall targeted pilot:** approximately 1–2 engineering weeks
  for a polished adaptive effect, potentially shorter for a deliberately
  constrained `menacing` preset. The macro family is out of scope.

### Release gates

- Listening tests on highly correlated `Other`, broad stereo
  ambience, and bleed-heavy separated material.
- Separate loudness-matched stereo and mono auditions; no automatic
  claim of human-like or 'naturally wide' sound from detector scores.
- Smooth behavior on play, seek, loop, sections shorter than macro
  duration, save/reopen, and full-duration 24-bit export.
- Macro versioning, precedence, renamed stems, split-on/off and
  undo/revert semantics verified by regression tests.
