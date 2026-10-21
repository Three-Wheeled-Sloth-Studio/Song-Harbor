# Future spatial choreography - The Logo and the Maw

Status: **accepted creative direction, not yet implemented**. This is the target for the next section-notation generation and width/delay development slice. Do not insert width directives into a currently active section script while width parsing is unsupported.

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
