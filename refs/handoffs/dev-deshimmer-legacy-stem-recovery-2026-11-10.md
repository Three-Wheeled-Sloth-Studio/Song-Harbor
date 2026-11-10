# Coding-agent handoff: Recover current song after legacy Deshimmer imports
Date: 2026-11-10
Branch: dev
Priority: Immediate, before any additional Deshimmer acceptance on the affected song.

## Problem and fix
The previous Deshimmer Accept path called /tracks/add with stem_alias Clean_<original>, display_name Cleaned <original>, original_gain_percent=0 and replace_source_track_id. It created extra visible stems and replacement masks, while existing script directives continued addressing the original filename/alias. UI clipped primary track labels (e.g. Cleane...). This was a product/architecture error, not a user workflow issue.

New code in dev uses /cleanup/deshimmer/{candidate_id}/accept and deshimmer_versions.adopt to version the WAV under the SAME existing working filename, track ID, display name and script alias; original WAV backed up under stem_versions and undo API provided. It must not add a new stem or replacement mask. Frontend clears candidate state on Accept while retaining the window, and explicitly reloads audio in StemMixer.

## Recovery instructions for the affected local song

Do NOT guess paths or act on a different song. Resolve the active project ID through the local application/Library and confirm its title before any changes. All operations local, offline.

1. Stop playback and stop the Song Harbor backend; confirm no in-progress Deshimmer jobs, exports or edits.
2. Identify DATA_ROOT from SONG_HARBOR_DATA or app setting. Locate DATA_ROOT/jobs/<project_id>/song-harbor.json. Make a timestamped COPY of the entire project folder outside the mutable job directory or otherwise take a verified filesystem-level snapshot, including song-harbor.json, stems/, originals/, channels/, candidate assets, exports and version history. Preserve all raw audio. Record SHA-256 of manifest and every WAV before mutation. Never delete or overwrite an unsnapshotted file.
3. Read the complete saved manifest and enumerate source_tracks, files, stems, replacement_masks, section_production and all section_* automation, channel_children, stem_groups, clip offsets, echo and provenance. Produce a proposed before/after diff. Source-of-truth is stable track_id + immutable working_filename, not the truncated UI text.
4. Identify ONLY legacy Deshimmer-generated imported tracks, by combined evidence: imported=True, alias beginning Clean_, display_name beginning Cleaned, original_filename generated from deshimmer-<candidate>.wav AND replacement_masks linking their replacement_track_id to an original source track. Reject ambiguous cases for manual review. Do not remove user-created instruments or non-Deshimmer imported tracks. If aliases were renamed, trace provenance and candidate WAV hashes rather than matching strings alone.
5. For each such accepted legacy repair, plan removal of the associated replacement masks. Original stems still exist as regular working WAVs; masks apply original_gain=0 during the replaced span. Remove the masks so original volume is restored as programmed. Preserve the user's existing saved mixer gain and all original section gain/volume automation. **Do not blindly reset gain to 100%**: if a prior manifest snapshot establishes changes resulting from cleanup, restore those exact pre-cleanup values; otherwise retain the user's current purposeful fader levels and document uncertainty.
6. Remove only confirmed Deshimmer-generated imported tracks from the manifest using track_lifecycle.remove semantics, including source_tracks, files, stems, section references and channel_children, plus associated replacement_masks. Repair any now-invalid stem_group references before committing; do not silently delete unrelated groups or production directives. Keep original Vocals/Drums/Bass/etc track_id and stem_alias unchanged. Preserve existing whole-song section text verbatim, including timestamps, lyrics, all stem automation, pan/width/reverb/eq/volume, and ending settings. Detect whether any directives were explicitly added to Clean_* tracks; report them for manual review rather than dropping musical decisions silently.
7. For removed imported stems, MOVE their working copies, originals and linked derived channel files to a labeled recovery archive (do not delete). Preserve Deshimmer candidate files and optimize recipes as history. Update song-harbor.json atomically using projects.write_project. Verify that the resulting files exactly match the manifest's track list, that all aliases are unique, and no replacement mask references a removed track.
8. Dry-run verification: render_tags and section_import.apply on a copied manifest with the existing script; confirm parse succeeds and semantic automation targets still reference original primary stems. Ensure source faders, pan, width, L/R control and section dynamics are preserved. Compare serialized section directives/lyrics against the snapshot, and show any intentional differences.
9. Relaunch Song Harbor dev, reopen affected song, confirm primary labels again read Vocals, Drums, Bass, etc., no Clean_* rows appear, no orphaned replacement masks remain, and old script still controls the same stems. Listen to the opening chorus, both bridges and outro. Analyze mix and confirm original source balance is restored.
10. Test a new Deshimmer run on ONE source stem. A/B Original/Cleaned at an identical playhead; Accept. Confirm **no added track**, same source filename, same alias and same display label, same mixer gain, no new replacement mask, new stem_cleanup_versions record, and changed audio actually reloaded in synchronized player. Check Save/Reopen and 24-bit export parity. Use /cleanup/deshimmer/undo to restore original and verify hash and script parity.
11. On any uncertainty or failed validation, roll back entire folder from snapshot rather than making partial destructive edits. Report the exact project ID, identified candidates, archive path, SHA evidence and operations performed. No blind deletion, no renaming original aliases, no whole-song reimport, and no regenerating stems.

## Additional engineering QA
- Review /cleanup/deshimmer/{id}/accept, deshimmer_versions.adopt/undo, and StemMixer sourceAudioRevision. Verify active split channels are rejected with an actionable notice and cleaned candidate can never silently overwrite a manually revised current stem. Ensure version history survives project reload.
- Run python -m unittest discover -s app/backend/tests -p 'test_deshimmer*.py' -v plus backend project/track lifecycle tests and npm run build --prefix app/frontend.
- Check acceptance errors preserve the candidate and release the busy lock. Test save/undo rollback, stale source hashes, simultaneous process submissions, and restart behavior.
- Validate actual preview versus saved render processing chain: current preview candidate is injected downstream of the original stem effects, which can make A/B differ from final accepted version. **Parity is not yet proven**. Log the gap, implement a version-swap preview at the stem buffer stage before claiming production fidelity.
- The existing clean play/pause + Original/Cleaned toggle and darkened busy lock worked in listening QA. Retain them.
- Apply canonical TWS Design Principles: apps/App-Design-Principles.md and apps/Studio-UI-Style-Guide.md, especially 'clarity of state and next action', 'compact action surfaces', 'minimum necessary text', and 'reversible operations'.

## Acceptance checklist
[ ] Backup and original SHA-256 evidence retained
[ ] Only legacy Deshimmer-generated extra stems archived
[ ] Original fader values and masks correctly restored
[ ] Original aliases, track IDs, lyrics and production instructions preserved
[ ] No bogus Clean_* UI rows or truncated primary labels
[ ] New Accept remains in open cleanup window; ready for another stem
[ ] New cleanup version preserved and undo works after reopen
[ ] A/B preview, accepted playback and exported mix parity checked
[ ] Tests/build and browser smoke pass
