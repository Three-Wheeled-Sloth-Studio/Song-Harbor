# Song Harbor Deshimmer integration: release-validated workflow
Date: 2026-11-03
Status: Approved direction; implementation and Windows QA pending.

## Production decision
- Current mix is locked for release after a +1 dB drum-stem gain using `Drums.gain:+1`.
- Preserve its rendered WAV and raw mix as immutable reference assets. Never mutate saved stems or silently replace an accepted export.
- User A/B auditioned Deshimmer Optimize on the full stereo mix, found it musically strong, and settled on tonal repair 0.75, side scale 0.45, low EQ -0.5 dB, presence +0.75 dB and air +1 dB (other settings retain the 2026-11-03 optimized JSON from the conversation). Mastering remained disabled.
- Do **not** re-run Optimize just to reproduce this sound: use the exact saved params + source file and validate deterministic export. The accepted EQ/punch/stereo settings are intentional production choices, not evidence of restoration-only behavior.

## First usable user journey
1. In existing **Sound cleanup & forensics**, choose scope: **Current mix** (initially supported), or a short timeline selection. Show a concise **Deshimmer** repair action within this tool, not a separate screen.
2. Default to **Last approved** saved recipe. Explicit **Advanced settings** reveals two groups: **Repair** (shimmer/noise/resonance) and **Mix color** (EQ/tonal, stereo, bass, punch, enhancements). Both groups serialize exactly, with input hash, duration, rate, channels, backend version and params.
3. `Preview` runs an async local process, caches the candidate by input hash+range+params+processor identity, and never autoplays. Offer **Original / Current / Fix** at matched listening level without changing the rendered candidate.
4. Add **Removed by repair** and **Full difference** audition choices to distinguish intended shimmer removal from musical energy changed by enhancement. Keep Accept / Discard visible with A/B controls.
5. `Accept` stores an immutable recipe + candidate asset for the current input revision, not an overwrite of source. Render/export consumes the accepted asset through exactly the same alignment/crossfade pipeline as playback; `Discard` keeps the project unchanged.
6. Report export parity and signal-preservation checks; never optimize or rank against an online AI-detector percentage.

## Technical slice: isolated local processor
- Use the installed local checkout `D:\Apps\deshimmer` as an opt-in executable discovery starting point on Windows. Prefer a separately pinned Python environment launched via explicit configured path, and check import/package version at startup.
- New backend module `deshimmer_adapter.py` handles path discovery, bounded process execution, cancellation/timeouts, version handshake, validated 24-bit WAV in/out and structured JSON. No arbitrary shell strings; use argv lists, subprocess without shell, safe temp directory, and clean up on failure/cancel.
- Adapter worker imports `deshimmer.api.process_audio` (documented upstream); do not directly import Gradio/UI handlers. Confirm return payload schema against pinned upstream commit before wiring. For region previews, use `slice_with_context` and trim/crossfade at exact sample offsets; whole mix path first.
- Only expose server-owned, path-validated project audio inputs: no arbitrary filesystem paths from browser JSON. Reject mismatched rate/channel/frame count, nonfinite samples, invalid params, unexpected processor version, stale source hash, and output above safe peak. Keep candidate outputs out of normal project assets until accepted.
- Integrate with backend FastAPI for capabilities, preview-job create/status/cancel and accept/discard, following existing `declick_recipes` conventions and source-sha protection. Do not block request threads while processing.
- Initial CPU mode only unless testing demonstrates reliable acceleration. Bound concurrent jobs to one; expose cancellation and errors in Sound Cleanup. Cache by source hash + sample region + complete params + external version.

## Tests and QA gates
1. Adapter unit tests with stub worker: executable missing, timeout, crash, malformed JSON, invalid output, cleanup on cancel, stale input, correct stereo shape, finite samples and 24-bit output.
2. Golden fixture: source WAV, exact saved parameter JSON, processor commit and output hash/metrics. Reprocess twice and verify sample- or tolerance-level determinism; compare external saved WAV.
3. Regression: processing disabled is bit-identical to established Song Harbor export; existing accepted gain `Drums.gain:+1` remains honored before creating final mix candidate.
4. Browser A/B: no autoplay; controls stay visible; no timeline jump; Original/Current/Fix and diff auditions follow same section position; no source stem mutation.
5. Export parity: accepted preview and exported 24-bit WAV align exactly in samples; check leading/trailing padding, crossfades, rates, channel mapping, peaks, loudness and stereo balance.
6. Auditory gate: verify bass distortion remains intentional and percussion attacks retain the approved punch; report 1-3/3-8 kHz transient energy, low band energy and side/mid changes vs locked reference.
7. Existing artifact suite `pwsh -File scripts/verify-artifact-suite.ps1`, backend tests, frontend build and Windows portable launcher smoke must pass.

## Staging
- P0: processor handshake + whole-mix preview into existing cleanup comparison, no Accept and no project mutation.
- P1: immutable accept/discard/undo and full-song export parity.
- P2: time-range/section and individual-stem repairs with context+crossfade and persist on reopen.
- P3: optimizer controls behind explicit action, preservation penalties and scored candidate comparison. Never let automatic cleanup remix without a visible change report.

## Known limits
The current local tool is not yet reachable through Song Harbor's API. The repository documentation verifies upstream integration points but neither an installed checkout's exact commit nor repeatable local processing on this machine has been verified by this handoff. Do not state the workflow is integrated until backend code and real-device QA pass.

References: `docs/deshimmer-evaluation-handoff-2026-11-03.md`, `docs/artifact-fingerprint-cleanup-roadmap-2026-10-26.md`, `refs/handoffs/currentHandoff.md`.
