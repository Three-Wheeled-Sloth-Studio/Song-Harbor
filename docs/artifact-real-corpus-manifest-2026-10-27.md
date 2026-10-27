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
