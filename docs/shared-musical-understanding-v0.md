# Shared Musical Understanding (SMU) v0 design
Status: schema contract, no inference enabled
Date: 2026-11-10

## Asset boundary
SMU is a local, versioned sidecar asset. It never modifies source PCM, section scripts, track aliases, or approved candidates. An SMU revision references a project revision and explicit source identities.

## Proposed JSON envelope
```json
{
  "schema_version": 1,
  "asset_id": "uuid",
  "project_id": "project-id",
  "project_revision": "revision-id",
  "created_at": "ISO-8601",
  "sources": [{"source_id":"mix-or-stem-id","kind":"mix","sha256":"hex","render_recipe_revision":"id"}],
  "sections": [{"section_id":"stable-id","start_sample":0,"end_sample":441000,"sample_rate":44100,"timeline_revision":"id"}],
  "measurements": [{"section_id":"stable-id","source_id":"mix-or-stem-id","metric":"rms_dbfs","value":-18.0,"unit":"dBFS","method":"versioned-dsp-method","source_sha256":"hex","render_recipe_revision":"id"}],
  "observations": [{"id":"uuid","section_id":"stable-id","claim":"possible bowed strings","source_id":"mix-or-stem-id","source_sha256":"hex","range_samples":[0,441000],"method":"model","model_id":"repository/revision","model_settings_hash":"hex","confidence":null,"uncertainty":"unverified","status":"candidate"}],
  "authored_intent": [{"id":"uuid","section_id":"stable-id","text":"preserve lead vocal","author":"user","revision":"id"}],
  "corrections": [{"id":"uuid","observation_id":"uuid","author":"user","action":"reject","reason":"not strings"}],
  "dependencies": [],
  "validation": {"status":"unvalidated","errors":[]}
}
```

The sample values above illustrate the contract, not actual analysis results. Confidence may be null; no invented percentages.

## Invalidation rules
- Source audio SHA changes: invalidate observations and measurements that depend on that source, not unrelated stems or authored intent.
- Mix recipe changes: invalidate mix-derived metrics and observations; preserve original-stem findings where the stem SHA is unchanged.
- Section timing changes: mark affected time-aligned observations as needing remap; never silently attach old observations to new boundaries.
- Model/version/settings changes: previous findings remain as historical records, but are not current findings for the new analysis profile.
- Prompt or user intent changes: update authored constraints and proposal revisions; do not rescan audio unless audio inputs change.
- User corrections persist as independent authored records across re-analysis and must not be overwritten by model output.

## Proposal contract
A proposed accompaniment plan references SMU asset revision, source hashes, section IDs, objective evidence IDs, user constraints, role, instrument, ACE task family, prompt, negative constraints and uncertainty. Validate engine capabilities and section boundaries before submission. Proposed text cannot execute arbitrary section directives. Reuse existing ACE candidate lifecycle and shared-clock A/B. Explicit Accept is mandatory.

## Model management sequencing
1. Shared model root and validation (source implementation committed, Windows QA pending).
2. Registry: discovered vs registered vs verified vs installed vs loaded are distinct states. Do not infer readiness from files existing.
3. Discovery: explicit user-selected roots and registered paths only, no recursive whole-disk scan.
4. Install: explicit approval, license/runtime compatibility gate, disk-space preflight, pinned revision, staging, hash verification, atomic publish, recoverable failure.
5. Load/unload: isolated optional worker, serialized heavy GPU usage, actual health/readiness and resource measurements.
6. Listening benchmark: fixed reference clips and human annotations before enabling automatic structured observations.

## Model research gates
Compare MOSS-Music-8B-Instruct and MOSS-Audio-4B-Instruct using upstream cards and pinned checkpoint revisions. Verify licenses, architecture-specific audio frontend, supported Transformers/PyTorch versions, trust_remote_code requirements, quantization support and real VRAM/RAM before exposing Install. A smaller parameter count alone does not establish music-understanding accuracy or compatibility. No runtime download or inference is authorized in this phase.

## Validation required
Schema validator and fixtures for source mutation, mix-only mutation, section boundary mutation, prompt-only changes, user corrections and stale proposal rejection. Validate local Windows path behavior and audio A/B independently.
