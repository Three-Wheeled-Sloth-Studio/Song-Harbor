# Artifact real-corpus manifest (2026-10-27)

## Status

The user declared Song Harbor job `586a03b40c9c` rights-cleared for local evaluation on 2026-10-27. Rights were user-attested, not independently audited. Audio remains outside the public repository. There are still zero completed listener judgments, so no real-world precision, recall, audible-objectionability or repair-efficacy rate is claimed. Synthetic fixtures are documented separately and are not listed as real music.

Private or copyrighted recordings must remain outside the public repository. Local paths must not be committed.

## Required record per future asset

Record metadata separately from audio:

| Field | Requirement |
| --- | --- |
| Corpus ID | Stable non-sensitive identifier |
| Rights | Owner, license, permitted storage/testing scope |
| Source | Acoustic / Suno / YuE2 / ACE / intentional electronic control; exact model/version when applicable |
| Generation | Date and disclosed settings where known |
| Chain stage | Source, remix, separated stem, accompaniment, mastered Song Harbor export |
| Technical | Duration, channels, sample rate, bit depth/codec and SHA-256 |
| Annotation | Acoustic event kind, start/end, annotator and annotation version |
| Listening | Blind/level-matched protocol, listener count, objectionable yes/no/uncertain |
| Attribution | Stage responsible and A/B evidence, or unknown |
| Repair | Eligible yes/no/uncertain; preview/accept/export evidence if attempted |

## Minimum control matrix before field claims

- Transient: dry percussion, processed slow onset, intentional soft pad, cymbal, saturated kick and hard-gated layer.
- Reverb: natural room/hall, freeze/shimmer, intentional gate and confirmed unintended render cutoff/stall.
- Stereo: aligned, Haas-wide, antiphase, moving pan and processing-induced collapse.
- Spectral: pitched resonance, industrial harmonics, cymbal noise, vocal sibilance and codec/resampling artifacts.
- Vocal: real annotated breaths, formant changes, harmonies and lead/backing bleed before phoneme claims.
- Chain: original plus each available remix, separation, accompaniment, mastering and export stage.

Acoustic presence, audible objectionability, responsible stage and reversible-repair eligibility remain four separate labels.

## Corpus entry: 586a03b40c9c

- Source full mix: 341.360 seconds, 48 kHz stereo, 16-bit PCM; SHA-256 `AA91F1471D46982E2596F895D169AF7351AAD713E453247F6C8AFA991EEE341D`.
- Source separation: six `htdemucs_6s` stems of equal duration.
- Imported stage: a 10.683-second, 48 kHz stereo, 24-bit ACE cello approximation at project time 71.719 seconds; SHA-256 `3A9F3459505601BDF44D5FADEB9B660F9BDB4055BD3C1A039803D4A3F03E0496`.
- ACE metadata: `acestep-v15-turbo`, source-conditioned cover, seed 150719, followed by separation cleanup. Existing generation documentation records that the cleaned layer is an approximation, not native isolated-instrument Lego output.
- Annotation status: production diagnostics only; acoustic findings have not been listener-confirmed as objectionable.

The production analyzer was run read-only at 24 kHz analysis rate over the source, six stems and imported cello. Finding counts are capped at six per kind and therefore are not prevalence estimates. The source full mix returned 6 attack-rise, 6 pumping, 3 harshness, 1 sibilance and 1 reverb-tail observation. The reverb-tail observation at 30.570 seconds exists in the source itself, so it cannot be attributed to Song Harbor processing from this evidence.

Stem scans exposed the confound rate: bass and drums each reached the six-observation cap for `reverb_tail`, mostly on ordinary decays into musical gaps. These are review candidates, not six proven reverb defects. Attack-rise likewise appeared across every instrument family except no family was manually labeled.

### Traceable cello stage comparison

| Stage | Attack rise | Pumping | Reverb tail | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Raw ACE target crop | 4 | 2 | 0 | Strong documented vocal/percussion leakage; not an acceptable replacement merely because no cutoff is flagged |
| Separation-cleaned/current | 1 | 1 | 1 at local 2.080 s | Cleanup removed measurable leakage but created a near-silence transition; no click-sized sample jump was observed |
| Local continuity preview | 1 | 1 | 0 | 400 ms of preserved raw crop blended at -24 dB; detector clears, but a small amount of raw bleed is reintroduced |

The preview is not in the project manifest and is not accepted. It preserves -17.9 LUFS and -5.3 dBTP, changes 0.400 seconds, and adds energy at -33.2 dB relative to the cleaned file. Its SHA-256 is `0C47BFB00243729CEF0716D68118666BC298EEFA0A3FC5D56B46C44EB29AB2B3`. A blind, level-matched user audition under the full mix is required before any import or replacement.

### Non-cello stem cleanup assessment

The six original Demucs stems were checked separately for immediate cleanup need. No stem had flattened/clipped samples, samples at or above 0.998, a production `phase` finding, or an abrupt-transition finding at the analyzer's threshold.

| Stem | Integrated loudness | True peak | Global stereo correlation | Follow-up decision |
| --- | ---: | ---: | ---: | --- |
| Bass | -18.4 LUFS | -5.7 dBTP | 0.912 | No immediate cleanup |
| Drums | -17.4 LUFS | -3.0 dBTP | 0.970 | No immediate cleanup |
| Guitar | -18.4 LUFS | -6.1 dBTP | 0.935 | No immediate cleanup |
| Other | -23.1 LUFS | -6.0 dBTP | 0.731 | No immediate cleanup; widest stem, but globally positive correlation |
| Piano | -54.3 LUFS | -24.8 dBTP | 0.887 | Review whether the very quiet stem is useful; do not normalize automatically |
| Vocals | -17.6 LUFS | -4.7 dBTP | 0.791 | Only stem needing targeted near-term audition |

The six-stem sum measured -14.1 LUFS, matching the source integrated loudness, with true peak -3.7 dBTP versus source -4.0 dBTP. Source-minus-sum residual measured -33.8 LUFS, 19.7 LU below the source. This indicates useful but nontransparent reconstruction; it is not proof that individual separation artifacts are inaudible.

The strongest vocal candidates occur in both the vocal stem and source full mix: presence-band/harshness at 18.859, 28.928 and 147.200 seconds, plus sibilance at 260.352 seconds. Other vocal-only detections are masked in the supplied full mix and do not justify immediate treatment from measurement alone.

Project-state follow-up:

1. Render the current processed mix before changing raw stems.
2. Audition the Intro at 18.859 and 28.928 seconds.
3. At 147.200 seconds, compare the current Pre-Chorus 2 vocal boost of +1.5 dB at 3.2 kHz against neutral or a conservative reduction; do not assume the raw-source harshness remains objectionable after rendering.
4. At 260.352 seconds, verify the existing 6.5 kHz de-esser (maximum 4 dB reduction) rather than stacking another de-esser.
5. Leave Bass, Drums, Guitar and Other unchanged unless rendered-mix listening identifies a specific fault. Treat Piano as an arrangement/usefulness choice, not a cleanup target.
