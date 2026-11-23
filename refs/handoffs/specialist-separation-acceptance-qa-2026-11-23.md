# Specialist separation acceptance QA - 2026-11-23

## Motivation
Full-stem render produced useful WAVs but stopped at download/export. The user could not name or accept the results into Song Harbor.

## Implementation
- Full-stem results now offer an editable script-safe stem name and **Add as stem**.
- Each model output is accepted individually. One output can be accepted without silently discarding or automatically importing the others.
- The existing /api/projects/{ident}/tracks/add endpoint is reused: it checks name uniqueness, validates/converts media, updates project tracks and mixer, and uses existing rollback behavior.
- Explicit Layer acceptance preserves the original vocal stem at full gain. After acceptance users can adjust/mute the original in Mix. No replacement automation is silently generated.
- Display green accepted state; prevent duplicate acceptance of the same generated output during the active modal session.
- Acceptance keeps Stem Tools open and invokes the regular parent project-refresh callback.
- Any output can still be auditioned or downloaded before accepting.

## QA
1. Render full vocal stem with MDX Karaoke 2.
2. Choose Vocals output, name RefinedVocals and Add as stem.
3. Verify it appears in the mixer and its timeline position is correct; original vocal stem remains unchanged.
4. Choose Instrumental output, name VocalResidual and Add as stem.
5. Verify both new names appear without creating additional duplicated output from button double-click.
6. Confirm unique-name validation and useful errors; verify audio/automation after playback and save/relaunch.
7. Test 30-second Compare still has no acceptance action.

## Deferred
- Singer-aware male/female extraction remains distinct from lead/backing Karaoke 2.
- Optional Replace acceptance with controlled original-region gain and a multi-output batch transaction requires a separate design and QA slice.
