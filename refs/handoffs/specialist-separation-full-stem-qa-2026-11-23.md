# Specialist separation QA follow-up - 2026-11-23

## Reported
- Installed model only became usable after closing and reopening Stem Tools.
- Dark buttons with black labels were unreadable.
- A/B compared only 30 seconds and offered no complete stem workflow.
- Raw output filenames such as Instrumental and Vocals were ambiguous for male/female duet separation.

## Changes
- On install completion, refresh the model catalog before retiring the poll, allowing immediate comparison without reopening the modal.
- Give preview, full render, install, and A/B buttons readable text/contrast.
- Label outputs with cautious explanations; Karaoke 2 separates lead-like versus backing-like content, not singer identities.
- Offer explicit **Render full stem**, producing model outputs across the selected canonical stem's complete clip, in the song's exports. The original and section script remain untouched.
- Expose a download link for each selected completed full-stem WAV and maintain A/B audition.
- Continue 30-second preview for fast model comparison.
- 30-minute duration ceiling, 60-minute separator timeout for full stem, and one active separation job at a time.

## Follow-up
- Acceptance into mixer as editable stems remains unimplemented; full outputs are saved only, not automatically inserted.
- Real multi-singer separation, including female/male speaker identity and overlap, remains a future model evaluation.
- Windows runtime GPU test and UI QA needed after updating dev.
