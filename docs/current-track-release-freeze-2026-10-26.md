# Infra Choir current-track release freeze — 2026-10-26

Status: **Production wrap / pending listening and export QA.** Do not interpret this document as confirming that a release master has been exported or approved.

Working track: **Call of the Electric Siren / A Kinder Law** (production context from the current Song Harbor session; verify the final release-facing title in project metadata before publication).

## Freeze direction

The current production goal is to finish and release the strongest version already assembled, not continue developing or experimenting with models. Freeze Song Harbor feature work for this track, including RVC/DiffSinger, new ACE Lego variants, Replace Instrument, and candidate-generation prompt experiments unless an existing mix defect makes them unavoidable.

## Release-safe path

1. **Save a non-destructive project revision** under the track's release candidate name. Preserve original recording, extracted stems, existing mix automation, and candidate provenance. Do not overwrite originals.
2. **Choose the mix using listening judgment.** Keep only accepted and musically beneficial enhancements. If an experimental Lego instrument is weak or questionable, leave it out of the release mix. Do not treat `not_detected` source-leakage status as proof of clean isolation.
3. **Inspect the whole song** for vocal intelligibility, balance, bass/kick interaction, unwanted masking, scene changes, transient artifacts, clipping, section changes, positional alignment, unwanted ending silence, and actual exported fade-out. Play transitions and the entire ending, not only the generator preview.
4. **Render the release candidate through Song Harbor's existing export path**. Make sure candidate preview-only crossfade and preview gain trim are NOT expected to appear in export unless the candidate was actually accepted into the project with explicit saved mix controls.
5. **A/B the exported WAV against in-app playback**, with equal monitoring level. Run peak/headroom and loudness checks with the existing analyzer. Apply conservative final output trim if needed; don't invent a target LUFS without choosing a distribution format.
6. **Archive the approved mix and metadata** (project state, WAV, lyrics/section timestamps, credits/artwork notes, revision ID). Make separate distribution derivatives only after the WAV is approved.
7. **Release packaging**—artwork, final title, video and YouTube copy—happens after audio sign-off. Use the established Infra Choir credit wording, and verify section timestamps from the release render rather than an older version.

## Explicit deferments

- Vocal identity pipeline: see `docs/vocal-generation-voice-identity-exploration.md`.
- Instrumental Lego production quality, native instrument isolation, and replacement workflow: see `docs/ace-instrument-lego-add-replace.md`.
- Reference-safe candidate cache retention/cleanup: near-term app maintenance, not this song's audio blocker.
- Popover-only generation status: code updated but browser QA pending.
- Update/relaunch foreground focus; global header fixed to top; broad UI refinements: schedule in app polish, not while mastering.

## Acceptance status

No final song master, saved Song Harbor mix state, analyzer report, or export confirmation was provided in this conversation. Therefore **release authorization remains a listening/export QA gate**, not a claimed completed export. This is a handoff checklist to finish in Song Harbor without additional development.
