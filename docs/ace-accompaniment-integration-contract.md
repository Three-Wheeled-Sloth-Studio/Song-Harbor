# Accompaniment Generator: ACE integration contract

Status: implementation-ready design, local ACE startup/endpoint validation pending
Date: 2026-10-23
Evidence: `docs/ace-step-accompaniment-poc.md`, `docs/ace-step-cello-poc-run.json`

## Ownership and non-destructive rules

Song Harbor owns selection, song sections, candidate records, audition, project state, and clip insertion. ACE is a replaceable local generation adapter. Generated assets are **candidates**, not project tracks, until explicitly accepted. Preserve raw output, model, seed, request, and transformation provenance. Never rewrite source stems. Never pad a short candidate to full-song duration for import. Reuse existing track insertion/positioning and shared-clock playback.

## Range semantics (required, not single-section-only)

- User selects **From section** and **To section**, inclusive, in chronological order; identical values mean one section. Optionally allow free timestamp selection. Resolve against persisted section identifiers and current boundaries, not display labels alone.
- Target interval `[target_start, target_end)` spans the beginning of From through the end of To, including all intervening sections.
- Separate context boundaries `[context_start, context_end)` may extend before/after the target, clamped to song bounds. Defaults should give useful adjacent-section lead-in where available; expose controls. A later section change must invalidate stale candidates or require explicit revalidation.
- ACE receives the context extract. Returned audio is aligned to **context_start** and cropped to the exact target interval using measured audio duration/sample offsets. Do not mistake context position for target position. Reject insufficient-length output rather than silently changing target alignment.
- Initial regression: `Call of the Electric Siren`, From=To=Pre-Chorus 1, target 71.719-82.402s, context 39.699-82.402s; also test multi-section ranges, first/last song boundaries, and noninteger sample offsets.
- For models that do not truly condition outside their generated output duration, label this explicitly; the turbo cover POC does not prove native independent additive generation.

## Candidate job contract

A job records `project_id`, immutable source revision/hash, target section IDs and resolved sample ranges, context sample range, adapter, model/checkpoint, task type, instrument/track name, prompt, BPM/key/meter overrides, seed, all engine parameters, lifecycle status, and resulting candidate asset IDs. Store filesystem paths server-side, never accept client-supplied arbitrary output paths. Save derived crop, cleanup, and preview variants as separate assets tied to the original. Report validation and actual timing/VRAM as measured, not estimated from a different model.

Canonical states: `queued -> starting -> generating -> processing -> ready` or `failed/cancelled`. Cancellation must stop jobs without deleting established candidates or interrupting Song Harbor playback. A retry creates a new candidate/job identity; explicit regeneration may reuse the seed.

The adapter interface exposes `discover()`, `start()` (only for trusted configured local installation), `capabilities()`, `submit()`, `status()`, `cancel()`, `release_idle_resources()`. Include adapter health, API endpoint and checkpoint availability. Keep model support capability-driven: installed turbo cover/repaint is experimental **cover + optional separation cleanup**; base/XL-base Lego/Extract only when independently verified. No automatic model downloads.

## Discovery and enablement

Discover configured local ACE installation and native API health (POC API on localhost:8001). Show three distinct statuses: **Not configured**, **Installed but stopped**, **Connected**; plus **Unavailable/Error** diagnostics. Settings manages trusted installation path, port, launch/stop, idle unload, and resource policy. Accompaniment panel shows compact status and an Enable action. Discover existing running API before launching. Do not start a server found at an untrusted remote host, execute arbitrary user-supplied commands, or claim a supported model without validating /v1/models + relevant documented capabilities. Local Windows agent must verify exact launch/stop commands and endpoint payloads before enabling automatic startup.

Backend owns API calls; browser does not reach ACE directly. Use timeouts, explicit limits on prompts/selection/duration, secure local-only binding, controlled output directories, and actionable errors. Don't assume native ACE cancellation endpoint exists until verified; mark best-effort behavior clearly.

## User flow and audition

1. Open Accompaniment tool; select From and To sections and independent surrounding context.
2. Choose musical target/instrument, prompt, installed model, candidate count and optional advanced generation controls; invalid combinations disabled with explanation.
3. Generate candidates without altering the project. Keep source/raw/cleaned variants explicit with isolation warnings.
4. A/B audition original mix (A) versus original mix + temporary candidate (B) on the same shared audio clock and exactly the same timeline position. Default five-second pre-roll before target (clamped to song start), adjustable. Toggling A/B does **not** restart or seek; switching is click-free if practicable. Candidate audio should be muted outside its actual clip interval. Avoid duplicating the original mix.
5. **Accept and insert** commits only the selected asset through existing imported-track flow at target_start, creates a stable track alias and history/provenance link. Candidate remains reusable after insertion. Reject any placement exceeding song end and avoid accidental duplicate insertion on repeated clicks.
6. Rejected candidates do not alter tracks; existing imported-track remove/reposition features remain authoritative.

## Rollout / tests

P0: range resolution, ACE discovery/enablement UI, submit/poll/store with running turbo, candidate preview A/B with pre-roll, explicit accept/insert, cleanup and error paths.
P1: native Lego after compatible checkpoint and local VRAM evidence; optional multiple candidates concurrently only if resources permit.
Tests: single+multi section inclusive bounds; sample-accurate context crop; first/last song edges; stopped API; wrong checkpoint; timeout; cancel; duplicate Accept; invalidated section/source revision; recovery after failure; no mutation before Accept; 5s pre-roll and A/B position preservation; track deletion and playback/export regressions. Never assert 1.58s DiT / ~5s warm turbo timing for Lego.

## Existing reuse points

- `app/backend/server.py`: backend HTTP routes and existing imported-track endpoint.
- `app/backend/track_lifecycle.py`: imported clip start_seconds, move/remove.
- `app/frontend/src/SharedClockAudition.ts`: single clock for playback.
- `app/frontend/src/StemMixer.tsx`, `WorkbenchTools.tsx`: tools/workbench wiring.
- `app/backend/tests/test_stem_import.py`: import non-destructive regression.
- `refs/architecture/overview.md`: model-neutral task orchestrator and provenance boundaries.

**Local-agent validation gate:** confirm actual ACE CLI invocation, API schemas, model discovery, safe unload/shutdown, cancellation support, and live turbo workflow before committing OS-dependent server management. No checkpoint download or GPU-intensive benchmark required to answer the discovery questions.
