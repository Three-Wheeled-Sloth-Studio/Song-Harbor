# Separation and musical analysis exploration
Date: 2026-10-25
Status: Research / candidate evaluation, not implementation approval

## Goal
Extend Song Harbor beyond its existing six-stem separation, emphasizing distinct lead, backing, and countervocal manipulation for Infra Choir; improve targeted instrumental refinement; explore automatic section detection, transcription, tempo/key analysis, and eventual audio-to-score workflows.

## Design principles
- Local-first; fit primary 12 GB RTX 4070 / 96 GB host with CPU fallback and step-down presets.
- Non-destructive: preserve original audio and parent stems; child stems are additive until user accepts replacements.
- No model distribution without verifying checkpoint licensing, not merely runtime package licensing.
- Avoid rerunning models unnecessarily; store provenance, model/version, settings and input hashes.
- Side-by-side listening and measured evaluation before replacing defaults.
- Model outputs must not be labeled male/female just because they are lead/backing.

## Opportunity 1: Hierarchical vocal separation (P0 research)
Existing 6-stem vocals -> secondary on-demand lead/backing splitter -> optional singer-specific splitter or choir-specific extraction.
Initial candidate: UVR-MDX-NET Karaoke 2, as implemented via audio-separator in StemDeck.
Comparison: Mel-Band RoFormer Karaoke, BS-RoFormer Karaoke, SCNet XL IHF; check legally distributable weight sources and local runtime compatibility. Compare Medley Vox separately for overlapping singers (may be service-only).
UX: vocals expand into Lead / Backing; preserve original Vocals. Support audition, solo, A/B, revert, swap, accept, export; future user-assigned labels such as 'soprano', 'countervocal', and 'choir'.
Test failure modes: countervoice categorized as lead, soprano harmonics left in choir, instrumental bleed, audible phoneme degradation, reverberation tails, phase/timing mismatch.

## Opportunity 2: Separation models and profiles (P0/P1 research)
Keep Demucs htdemucs_6s as baseline. Compare target-specialist RoFormer models, select by goal: clean vocals, clean instrumentals, lead/back, guitar, piano, strings, percussion.
Evaluate specialized second-stage extraction instead of global model replacement.
Investigate a model registry/adapter using existing audio-separator where supported: manifest with architecture, filename, checksum, origin, checkpoint license, input targets, output schema, memory requirements, model status; no automatic model install without disclosure/consent.
Candidate quality references: MVSep algorithm tables, python-audio-separator's model mapping. Published SDR scores are not cross-dataset universal and do not replace project listening tests.

## Opportunity 3: Automatic song sections (P1 research)
Investigate All-In-One / all-in-one-infer as used in StemDeck.
Output provisional [Intro], [Verse], [Chorus], [Bridge], [Outro] markers with confidence; map to Song Harbor's supported section tags. Do not overwrite manual time alignment. Support reject/merge/adjust, waveform overlays, and changes to timing.
Measure whether sections align to musical transitions in hybrid industrial, metal, orchestral, shanty and AI-produced tracks.

## Opportunity 4: Lyrics and timing (P1/P2)
Whisper transcription on vocal-only stem; retain imported authored lyrics as source of truth, since transcription can mishear heavy effects, countervocals and choirs.
Align known lyrics to audio and retain confidence per word/line; output YouTube timing and section map. Distinguish transcription from alignment.

## Opportunity 5: Tempo, meter, key, and future scoring (P1/P2)
Use librosa baseline for beat/tempo/key candidates; evaluate alternatives for changing tempo/meter, double/half-time errors and modal/harmonic ambiguity.
Scoring requires more than tempo and key: evaluate isolated-stem note/MIDI transcription separately. Spotify Basic Pitch is a lightweight reference and notes best results on one instrument at a time. Eventually align vocal phonemes/notes, chord changes, melody and section annotations to time, importing YuE scoring when available.
Preserve uncertainty and avoid fabricating authoritative scores.

## Test matrix
Use at least 3 representative, rights-cleared songs or 30-60s excerpts:
A) soprano lead plus male countervocal plus backing choir, with simultaneous overlapping phrases;
B) dense metal/orchestral passage with strings, distorted guitar and industrial percussion;
C) shanty/rhythmic track with tempo changes, chant, call-response and reverb.
For each model, retain version, checkpoint source/license, GPU memory peak, elapsed wall time, stem count and output files. Use blind listening plus checks for bleed, missing material, word clarity, onset integrity, transients, musical fullness, spectral artifacts, channel/time alignment and reconstruction error. Note SDR only for material with true reference stems; don't estimate SDR against mixed production masters.

## First experiment
1. Inventory Song Harbor's current six-stem models/settings and output alignment behavior.
2. Enable UVR-MDX-NET Karaoke 2 as independent vocal-subdivision experiment through audio-separator.
3. Choose one verified, compatible, licensed RoFormer karaoke checkpoint, if available, and compare identical excerpts.
4. Test lead/back outputs separately from a multi-singer model; document whether male/soprano countervocals can be isolated.
5. Prototype optional section detection separately from stem generation.
6. Gate integration on audible improvement, reliable model distribution, reproducible timings, GPU feasibility and low-friction A/B/revert.

## References
- https://github.com/stemdeckapp/stemdeck
- https://github.com/stemdeckapp/stemdeck/blob/main/docs/models.md
- https://github.com/nomadkaraoke/python-audio-separator
- https://github.com/nomadkaraoke/python-audio-separator/blob/main/docs/deton24-model-mapping-and-ensemble-guide.md
- https://mvsep.com/en/algorithms
- https://mvsep.com/en/full_api
- https://github.com/spotify/basic-pitch

## Development status
Research document only. No dependencies added, no models downloaded, and no app behavior changed.
