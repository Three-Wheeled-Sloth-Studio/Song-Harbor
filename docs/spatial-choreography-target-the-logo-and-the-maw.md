# Future spatial choreography - The Logo and the Maw

Status: **creative direction recorded; mid/side width is now implemented, perceptual widening and the full song choreography remain untested**. This is the target for the next section-notation generation and width/delay development slice. Width directives now parse and render (0-150%, with 100% meaning original width). Start with a small QA subset before applying the whole-song choreography.

## Per-stem narrative motion

- **Vocals:** individual vocal stereo components open toward the **left and wide**, moving incrementally toward **center and narrower** over the full four-minute progression. Choruses temporarily expand width substantially; thereafter return to an appropriately narrowed trajectory.
- **Bass / Guitar / Piano / Other:** mirror vocals: initially **right-focused and wide**, then gradually narrow and migrate somewhat toward center. Maintain separation and avoid making the bass feel unfocused or weakening mono compatibility.
- **Drums:** start **narrow**, progressively widen across the piece. Some sections alternate emphasis between left and right; by the ending the drum field is **full-width and environmental**.
- **Choruses, including the section labeled Instrumental:** expand the perceived width significantly across appropriate stems, then return to the current narrower baseline at the next section. Widening should be audible but preserve rhythm and mono compatibility.
- Section directives are *stateful*: missing directives inherit previous values, not silent resets. The entire progression should develop across the song; do not paste fixed settings blindly into every Verse.
- Existing split LEFT/RIGHT children must be treated as *real stereo*, not two independent tracks to duplicate or hard-pan without musical reason.
- The side images are the story: vocals on one side, accompaniment counterbalancing, drums growing from controlled to immersive. Dynamic pan and width must remain distinct parameters.

## Development implications

1. Build a validated `Track.width:nnn@2s:smooth` type and typed storage, preserving the clean `[Section time]` header + production brace line. No silent ignores.
2. Separate **stereo width** (mid/side energy ratio for source material with meaningful side signal) from **perceptual stereo widening** for near-mono stems (short decorrelated reflections / delay). Neither should unexpectedly collapse or invert mono audio.
3. Preview/offline-export fidelity is a hard gate. Ensure width processing occurs consistently in both graphs, after child L/R reconstruction and before final panning and reverb send. Control clipping/headroom and true-peak/mono behavior as separate verification.
4. Support at least one *structured width control* with explicit defaults and per-section interpolation; a section timeline should show inherited values as inherited, not as blank/reset.
5. When the user next asks for a complete section drop-in for this track, use their canonical timestamped four-minute lyric sheet and all 13 section labels, including the 2:28.384-2:38.955 `[Instrumental]`. Preserve lyrics verbatim. Do not invent musical wording or force directives for effects not yet implemented.

## QA story beats

- 0:00 Intro: left/wide vocals vs right/wide melodic/other sources, drums narrow.
- 0:45 first Chorus: noticeable stereo opening without dragging the vocal center away unintentionally.
- 1:09 Verse 2: narrower baseline than Verse 1, inherited or smoothly transitioned.
- 1:42 second Chorus: wider than surrounding sections without a spike in total level.
- 2:28 Instrumental: chorus-like dramatic expansion despite its section label.
- 2:38 Verse 3: baseline tighter and closer to center, drums broader.
- 3:13 final Chorus: most expansive culmination.
- 3:48 Outro: drums reach environmental/full-width; vocals and melodic elements retain the convergent direction. Check final fade/ambience treatments independently.

## 2026-10-21: first width implementation QA

Width notation: `Vocals.width:140@2s:smooth`. Native mid/side values 0-150%; 100% exactly passes through the existing left/right stereo image, 0% sums it to mono, 140-150% boosts existing side signal. The matrix is applied **after split-child reconstruction and before the stem pan and reverb send**, identically in Web Audio audition and offline export. It does **not** create artificial stereo width in a near-mono stem. A later decorrelated spatial delay/early-reflection option will supply perceptual widening when side energy is absent.

**Start small, without replacing the entire lyric sheet:**

```text
[Intro 0:00-0:12.323]
{Vocals.pan:left.45@2s:smooth Vocals.width:135@2s:smooth Drums.width:35@2s:smooth}

[Chorus 0:45.409-1:09.278]
{Vocals.width:150@2s:smooth Guitar.width:145@2s:smooth Drums.width:110@2s:smooth}

[Verse 2 1:09.278-1:31.339]
{Vocals.pan:left.30@3s:smooth Vocals.width:105@3s:smooth Drums.width:70@3s:smooth}
```

These example blocks are *selected test sections only*, not a complete paste-ready replacement. Preserve other section headers, all lyrics, and existing reverb/fade/tail instructions. An instruction omitted in subsequent sections inherits the previous setting; reset instructions return width to 100%. Avoid `all.reset` unless intending to reset pan and reverb as well.

### Listening and export acceptance

1. Run the normal launcher on `main`. All six stems remain split L/R, with child and original-parent audio mutually exclusive.
2. Open **Section stereo width** under Tools and set Vocals width for Intro to 35%, Save. Audition a few seconds, then change to 100%, Save. The narrow/mono behavior should be unmistakable; 100% should return to the original image without changing center location.
3. Set 140% and compare with 100%. A detectable increase depends on true stereo content; if not audible, do **not** assume the control is malfunctioning—check side energy before adding a false widening effect.
4. Apply `Vocals.width:140@2s:smooth` beneath one existing section header, making sure other directives for that section stay in the **same** brace line. Check the section change and subsequent inheritance.
5. Export WAV with automation and compare the same segment at matched loudness. Invert/mono-check L/R in a DAW if available; no missing tracks, left-right swaps, or unexpected phase cancellation should occur. Wider settings can increase peaks—use the existing master headroom remediation if needed.
6. Save/reload, confirm width instructions survive, and edit width in the structured sidebar to confirm the text round-trip remains current. A reset should return width to 100%, not 0%.
7. Important: confirmation of native mid/side behavior does **not** establish satisfaction of the user's desired dramatic width for nearly mono stems. Perceptual decorrelation and stereo delay remain the next slice.

**QA gate:** code committed to `main`; a real browser/WebAudio listening test and independent full Windows build have not yet been confirmed.
