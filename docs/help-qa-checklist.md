# In-app Help acceptance checklist (2026-10-21)

The top-right **i** icon, immediately next to Settings, opens a searchable user guide without leaving the current Library or song session. Implemented in `app/frontend/src/HelpDialog.tsx`, integrated through `main.tsx`, and styled with `song-harbor.css`. Corresponding stand-alone documentation is `docs/user-guide.md`.

## User testing checklist

- Launch in Library. Confirm **Settings gear** and **Help i** are adjacent, readable, keyboard-focusable and do not crowd the installed version badge or other header actions at 1366px and 1920px widths.
- Open Help. Confirm a dialog appears over the current Library, rather than navigating elsewhere. Close using dialog close affordance and Escape; verify focus returns to the original interface according to the shared TWS Dialog contract.
- Search for `ducking`, `reset`, `FFmpeg`, `download`, and `reverb`. Matching topics should expand and show practical explanations; search `zzzznonexistent` should display a no-results message. Clear search to restore all collapsed topics.
- Confirm the help dialog does not force a new page refresh, clear waveform/section changes, or alter mixer state. Test while viewing an existing song session.
- Confirm scrollable content and readable monospace examples on a narrow laptop viewport. Header and waveform should retain their normal width once the dialog is dismissed.
- Verify Help remains available when backend health is degraded. Documentation content is bundled in the built frontend; only the optional issue-tracker link requires internet.
- Validate that `Track.reset` versus neutral compressor/duck reset, the Download WAV second click, and the session-only master trim limitation are documented accurately.
- Confirm Settings still opens independently, with component recovery, and update/relaunch still works. Test keyboard-only traversal.
- When a release changes supported production grammar, section tools, routing, or export, update BOTH `HelpDialog.tsx` and `docs/user-guide.md`; adjust checks accordingly.

## Support collection

For tester reports, ask for version badge (e.g. `main@1234abcd`), Windows version, action/expected/result, complete error message, and whether content was saved before any update. Do not request private audio for routine bug reports.

## Implementation scope

No model, media, project or DSP files are modified by opening Help. This is documentation-only UI. An interactive guided tour, external searchable docs portal, context-sensitive topic links and onboarding flows are deferred; do not label them implemented.
