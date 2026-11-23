# UVR-inspired specialist stem separation experiment

Date: 2026-11-23
Branch: dev only
Status: First read-only candidate preview slice; not a new production separator.

## Why
The user is preparing Crown of Hollow Stars and wants higher-quality stem extraction. Song Harbor's primary six-stem job remains htdemucs_6s. UVR demonstrates a useful model ecosystem: Demucs, MDX, VR, optional second passes and ensembles. This phase adds candidate comparisons without replacing or deleting saved stems.

## What this slice does
- Stem Tools has a Separate tab for a selected existing source track.
- Discover only locally installed model files in Song Harbor's existing separator model directory; no automatic downloads, license assumptions or large installs.
- One bounded 0.5 to 30 second region from the current playhead (backend hard cap 60 seconds) and selected source track. Imported clips respect source offset.
- Audio-separator runs asynchronously with configured local FFmpeg, produces candidate WAVs in a unique project-owned exports/Refinement-* folder, and records a source hash, model, offsets and output manifest.
- UI status reports queued/running/failed/ready; user can audition the exact input region or one model output. No acceptance, routing, source overwrite, or script change.
- Error and path validation prevent arbitrary model paths, output browsing, or foreign-project candidate reads.

## Current limits and QA
- No checkpoint installation UI yet. If only htdemucs is installed, alternative comparison is not yet meaningful. The UI states when no models are discovered.
- Candidate playback is a basic A/B player, not yet loudness normalized or waveform-synchronized. Do not promote claims of parity or quality measurements.
- Runtime job registry is in-memory. Completed preview folders remain after a server restart but are not automatically reattached to the interface.
- No instrument specialization or automatic objective/model mapping yet. Model licenses/weights must be verified before in-app install.
- Tests: local Python syntax and focused test contracts; Windows model, GPU, audio comparison and frontend runtime QA needed.
- The first audition should use a 20-30 second vocal section from Crown of Hollow Stars. Compare the original Demucs Vocals source to a verified MDX vocal specialist, then a karaoke lead/backing model when legitimately installed.

## Next slice
1. Per-checkpoint verified model catalog with explicit in-app install approval and checksum/license provenance.
2. Candidate loudness-matched, time-locked A/B and source reconstruction checks.
3. Optional Accept as new stem or section-scoped Replace, using existing reversible track lifecycle.
4. Track model quality, bleed, transient loss, separation latency, VRAM, and subjective Better/Worse notes before changing six-stem defaults.
