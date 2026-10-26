# Vocal generation and voice identity — exploration (2026-10-26)

Status: exploration, not implemented. Goal: keep distinct and repeatable Infra Choir lead/backing singer identities while letting Song Harbor add or replace vocal phrases.

## Separate performance and identity

1. **Performance generator**: produces phonemes/lyrics, pitch contour, timing and expression from melody/scoring or reference singing.
2. **Voice identity conversion**: adapts a clean isolated vocal performance to a trained or prompted singer timbre.
3. **Mix placement**: position, de-ess, dynamic width/reverb, A/B, and reversible regional acceptance in Song Harbor.

### Paths

- **Applio/RVC**: local voice conversion with speaker model trained on clean isolated examples. Best near-term option for repeatable voice identity while preserving the source pitch/words/timing. Requires a sung performance as input; not text-to-singing. Validate soprano range, vibrato, breathiness, and consonants on own or permissioned voice data before integrating.
- **DiffSinger via OpenUtau**: score- and phoneme-driven singing synthesis; supports custom voicebanks with substantially greater training/data preparation complexity. Best for exact harmony, syllable timing, replacement phrases, and later YuE/ABC/MIDI score consumption.
- **ACE-Step Base Lego**: native documented classes include `vocals` and `backing_vocals`; prototype separately with lyrics and instrumental backing. It does **not** give assured continuity of a specific singer merely by selecting the class. Existing instrumental-Lego validation rules should not be extended to vocals without independent QA.
- **Seed-VC**: supports zero-shot singing voice conversion and optional fine-tuning. Original project repository archived in 2025; treat as research only.
- **ACE reference audio / LoRA**: can nudge acoustic style and vocal timbre but does not promise repeatable exact singer identity; useful broad style control, not a drop-in RVC replacement.

## Suggested POC

1. Identify a short clean isolated lead vocal reference (with necessary permissions). Keep project audio local.
2. Produce or reuse a short sung phrase with known lyrics and melody.
3. Convert with Applio/RVC to the target singer. Evaluate timbral continuity, pitch, vibrato, lyric intelligibility, artifacts and natural transitions to the existing vocalist.
4. Compare a score-driven DiffSinger generated performance plus optional RVC identity conversion.
5. Test ACE Lego vocals/backing_vocals on a low-stakes 15–25 s instrumental region and reject any source-shadow duplication, just as with instrumental Lego.
6. Introduce an engine-neutral `Singer Profile` registry (stable ID, model/provider, reference dataset/version, comfortable tessitura, language, allowed usage/consent, default cleanup).
7. Production implementation only after measurable QA: generate candidate, waveform/playhead, solo, level match, regional A/B and reversible acceptance. Preserve original unconverted singing and model provenance.

## Other QA backlog

- Generation overlay must cover **only the accompaniment popover content**, not the full Song Harbor app. UI containment CSS patched 2026-10-26; runtime test pending.
- Near-term: reference-safe candidate archive/cleanup; protect accepted or provenance-linked recordings.
- Update/relaunch: bring the new Song Harbor window to foreground.
- Global header pinned to top of viewport.

References:
- https://docs.applio.org/reference/architecture/
- https://docs.applio.org/getting-started/inference/
- https://github.com/openutau/OpenUtau/wiki/DiffSinger-support
- https://github.com/Plachtaa/seed-vc
- https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE
