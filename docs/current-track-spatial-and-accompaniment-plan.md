# Call of the Electric Siren / A Kinder Law — spatial production pass and selective accompaniment

Date: 2026-10-26. Applies to the 5:41.36 timestamped current section sheet.

## Paste-ready spatial candidate

Full, complete importable section sheet (all 13 sections, every original lyric and timestamp):
[qa-current-track-spatial-approach-full.txt](qa-current-track-spatial-approach-full.txt)

Source: user-supplied current section text, not an audio analysis. **Proposed listening candidate, not an approved master.**

### Movement concept

- The singer progressively comes closer: center-anchored vocal width 85 -> 30%, wet send 29 -> 5%, space 10 -> 0%, modest gain -1 -> +1 dB. Distant at entry, intimate at end.
- The environment expands *around* the closer singer: Other width 75 -> 150%, space 5 -> 40%, while overall environmental reverb reduces 45 -> 18%. The last sections surround via lateral width/reflections rather than making the foreground singer distant.
- Bass moves left/right on alternating sections, up to 42% pan in the bridges; Other parent pan alternates opposite each time. Bass width remains mono (0) and Drums.pan stays centered to retain a coherent rhythmic anchor.
- The Other-left and Other-right reverb sends alternate focus by section. These are **asymmetric send levels into the existing common reverb path**, not independent time-delayed left/right echo engines. This is a deliberately achievable approximation, not a claim of discrete ping-pong delays.
- Transitions typically use 40-45% of section duration (capped at 30s) and 5s for short pre-choruses, consistent with Infra Choir preference for extended development.
- Original EQ/dynamics and drum/bass gains retained. This does **not** automatically loudness-match L/R channels; measure and listen for side balance, low-frequency instability, true peaks and mono collapse after import.
- The split child `Other-left` and `Other-right` routing must exist/operate. If the project is not in L/R split mode or aliases differ, the import must not silently drop these directives.

### Accompaniment shortlist (separate experiments, not directives)

1. **First choice: Bridge, 2:50.221–3:34.548 — cello counterpoint / sustained bowed low strings.**
   Instrument family `strings`. Suggested direction: *“One exposed, mournful low cello answering the vocal phrases with a slowly rising two- or three-note motif; long bowed notes, restrained attack, no choir, no drums, no doubled vocals, leave the voice clear.”* Keep the initial phrase sparse; add movement into “Join the pulse inside the rain.” Best chance to support the increasingly intimate siren without making choruses busier.
2. **Second: Intro, 0:00–0:38.777 — distant high harmonics / metallic glass-pad.**
   `strings` or `synth`. Direction: *“Distant harmonics and unstable soft upper-register shimmer, sparse, nonrhythmic, ghostly and submerged, no melody doubling or percussion, rise softly behind the first four sung lines.”* Helps make the opening distant and sets up the closing spatial arrival.
3. **Third: Final chorus, 4:28.788–5:02.941 — high strings or dark brass swell.**
   `strings` or `brass`. Direction: *“Sustained harmonic counterline and breath-like swells, increase the emotional scale without doubling lead melody; narrow note density under sung lyrics, no new vocals/drums.”* Keep subtle; the chorus is already dense and all newly generated candidates need isolation listening.
4. **Optional: Outro, 5:02.941–5:41.360 — sparse celesta/synth bell responses.**
   `keyboard` or `synth`. Direction: *“Two or three soft crystalline answering notes between lines, gradually brighter and closer but never busy, leave the final lyric and fade unobstructed.”* Avoid new sounds during the final 5s fade.

The two brief pre-choruses can also benefit from a rising accent but are less attractive for a release-bound POC because their ~11s span and dense lyrical transition give limited musical room.

## Release-safe evaluation

- Preserve the current working project before importing the new section block. A new QA candidate/backup is safer than overwriting production without A/B.
- Import whole sheet (Append unchecked), confirm all 13 sections and original lyrics survive. Compare first intro, two alternate side swaps, first bridge, final chorus and full ending.
- Solo L/R stems if the lateral difference is unclear, and check the same export in headphones, speakers and mono. Bass-heavy asymmetry can be distracting at 35-42% pan; if needed lower Bass to 20-25% while retaining opposite Other motion.
- Keep existing ACE Lego source-leakage safeguard. `not_detected` is not guaranteed artifact-free output; Solo-listen to every candidate before acceptance. If no addition clearly improves the track, release without it.
- Do not treat a proposed 5:41.36 timeline as an exported 5:41.36 final WAV: the configured 3s tail and 5s fade need verification in rendered audio.
