# Premium Cloud Sync — Local-first multi-device Song Harbor

Status: **Architecture and commercial development plan; not implemented**
Created: 2026-10-23
Owner: Song Harbor product and engineering
Roadmap: SH-RM-260 (sync foundations), SH-RM-265 (premium multi-device sync), SH-RM-270 (commercial hardening)
Related: `app/backend/projects.py`, `app/backend/library.py`, `app/backend/track_lifecycle.py`, `app/frontend/src/AppSettings.tsx`, `refs/planning/roadmap.yaml`.

## Product outcome

A premium Song Harbor subscriber can sign into a second device, discover their synced
songs, download/open a song with the editable source tracks, sections, lyrics, FX and
automation intact, make changes offline, and synchronize after reconnecting. Full
music production and project export must remain available offline with no account.
Cloud sync is an optional convenience/continuity service, **not** a prerequisite
for local work or an online DRM gate.

The user already works across multiple production PCs and may select a Google
Drive-mirrored working folder. Design migration from that use case without
requiring a shared mutable SQLite file. Cloud sync is distinct from collaboration
and real-time simultaneous coediting.

## Current repo state / prerequisites (confirmed)

- `projects.PROJECT_VERSION=1`; per-song manifest JSON and immutable
  source/stem files under a user-selected data root. `write_project` uses
  temp file + atomic `os.replace` (good local write atomicity).
- `library.SCHEMA_VERSION=1`; SQLite indexes songs, collections, sources,
  separations, versions and assets with persistent IDs and SHA-256 on
  original sources. Index holds absolute `storage_path` references.
  The sidecar JSON permits library recovery if local DB is rebuilt.
- Track identity and human alias are separated; track IDs are stable
  under renaming. Existing channel children, sections, automation,
  additive clips and DAW exports add references needing a complete
  dependency manifest.
- Settings currently advise using a Google Drive mirrored directory and
  **not** opening the same synced Library database on two machines
  simultaneously. That workaround does not provide atomic cross-device
  conflict handling, revision history or dependable consistency.
- This plan does not claim current cross-device support.

### Architectural non-negotiables

1. **Local remains canonical while editing.** A sync worker observes committed
   local revisions, never writes directly into a live audio playback buffer
   or blocks Save/Play/Export on network service availability.
2. **Do not synchronize an open SQLite DB file or machine-specific paths.**
   Sync *semantic metadata* (song/collection/version graphs, stable IDs)
   through a versioned portable manifest. Reconstruct/update each device's
   SQLite index transactionally. Preserve local absolute path mapping.
3. **Audio/media assets are immutable by content hash** (e.g. SHA-256) with
   content-addressed identifiers; project revision manifests reference
   hashes, sizes, codec/sample rate, semantic role and track ID. Never
   rewrite canonical source WAV merely to sync or reposition.
4. **No last-writer-wins loss of edits.** Each song revision has parent
   revision ID(s) plus device ID and mutation provenance. Conditional
   compare-and-swap commits; concurrent edits create diverged branches
   and user-visible named conflict copies or a merge review. Auto-merge
   only disjoint, verified safe metadata operations.
5. **No duplicate upload of unchanged stems.** Hash/deduplicate bytes
   within a tenant, resumable multipart/chunk transfer, checksum verify,
   staging/atomic promotion and safe cleanup of abandoned parts.
6. **Portable dependencies:** manifest references project originals,
   derived stems, imported tracks, accepted generated clips, authoritative
   section/lyrics/production settings, channel children, saved mix versions,
   thumbnails/previews as explicit optional artifacts. Caches, downloaded
   models, FFmpeg binaries, local temporary renders, per-device preferences
   and DAW app installations are *not* sync-required.
7. **Explicit availability:** per-song `local / metadata-only /
   downloading / ready / sync-pending / conflict / error`. A song is
   playable only when its required assets are present and verified;
   metadata-only placeholders cannot masquerade as complete songs.
8. **Offline and cancellation resilience:** durable local outbox,
   retry/backoff, idempotent upload/download, crash recovery, partial
   resume, device offline editing and safe conflict notification.
9. **Trust/privacy:** authenticated/authorized scoped API, per-tenant
   isolation, private objects, short-lived scoped signed URLs, TLS at
   transport, encryption at rest, server-side deletion/retention limits,
   audit logging and no collection of audio for model training. Evaluate
   optional end-to-end encryption later, with its key-loss/support tradeoffs.
10. **Ownership:** cancellation, downgrade, expired payment, quota,
    sign-out and service outage never lock already-downloaded projects.
    Downgrade stops new uploads after grace period; retention/deletion
    policy is disclosed, with explicit local export/restore workflow.
11. **No implicit shared folder edits:** avoid syncing local
    `library.sqlite` or writing into a running DAW's project store.
    Sync coordinator applies verified revisions to a staging directory,
    then materializes local files and updates metadata transactionally.

## Product tiers (proposal, pricing TBD)

**Free / local**
- Fully usable offline music production, normal import/edit/export, local
  backup and manual project transfer remain free.
- No cloud login requirement, no forced sync or telemetry gate.

**Song Harbor Premium Sync**
- Private account and device enrollment.
- Automatic cross-device project metadata + media sync with selective
  per-song downloads and offline edits.
- Sync history and recovery, conflict-copy resolution, device list/revoke,
  transfer progress/pause, usage/quota indicator and self-service deletion.
- Storage quota and fair-use transfer policy shown transparently; additional
  storage could be a separate paid add-on rather than unlimited default.
- Proposed pilot: **2 devices and a conservative quota**, adjustable after
  measuring actual stems, peak bandwidth and support costs.

**Later optional**
- More devices, team sharing/collaboration, web previews, generated-stem
  cloud compute, E2EE, family/shared libraries. These are not MVP scope.

Use a server-authoritative entitlement: verified purchase/subscription
status and quota drive access to *upload and sync services*, never access
to local files or basic DAW functionality. Do not trust a local boolean
for billing enforcement. Don't ship pricing or quotas without unit economics.

## Architecture (proposal)

```
Song Harbor desktop A                         Song Harbor desktop B
  Local project JSON + SQLite Library         Local project JSON + SQLite Library
     | semantic manifest exporter                ^ manifest materializer
  Durable local change outbox                  Local sync outbox
     |                                           |
  Local sync daemon <--- authenticated sync API ---> Local sync daemon
                            |
                 account + entitlement DB
                 device / revisions DB
                 per-song revision DAG
                 quotas, audit, tombstones
                            |
                  private S3-compatible
                  content-addressed blobs
```

Separate three channels:

- **Control plane** (small): auth, entitlement, library project catalog,
  revision commit/HEAD via compare-and-swap, conflicts, manifests, quotas,
  device enrollment and tombstone/recovery metadata.
- **Data plane** (large): audio, stems and accepted generated assets in
  S3-compatible object store, transferred direct with limited presigned
  operations, multipart resume, hash/size checks and encryption.
- **Local sync engine**: resilient queue and state DB, manifest diff,
  portable path mapping and transfer prioritization. Sync metadata first;
  assets on-demand or pinned per project; don't block transport.

Provider candidates: Cloudflare R2 or Backblaze B2 object storage; managed
Postgres/auth (or equivalent account service); Stripe Billing or another
subscription provider. **Vendor selection deferred** until prototype
benchmarks and legal/privacy review. Keep storage provider-specific code
behind a narrow adapter. Do not store billing secrets or long-term object
credentials in desktop clients.

## Portable schema and minimal protocol proposal

`song-sync-manifest/v1`:
- schema version; song/library stable IDs; ordered track IDs;
  current and parent revision IDs; author device ID; timestamp and
  monotonic per-device sequence; content integrity digest.
- song title, collection membership, section boundaries and lyrics,
  production and dynamics automation, per-track gain/mute/solo and
  user-defined aliases, external/imported clip offsets and split child
  routing, saved mix versions and provenance.
- asset references: `asset_id`, `sha256`, `size_bytes`, `media_type`,
  `sample_rate`, `channels`, `duration`, `role`, `track_id`, and
  relative logical path. No absolute OS paths.
- optional `missing_on_device` asset state in the **local index only**.

Minimal service operations (endpoints examples, not API promises):
- `GET /v1/account/entitlements`
- `GET /v1/library/heads?since=cursor`
- `GET /v1/songs/{id}/revisions/{revision}`
- `POST /v1/assets/prepare` (hash/size presence check, signed multipart)
- `POST /v1/songs/{id}/commit` with `expected_parent_revision`
- `POST /v1/devices/enroll`; `POST /v1/devices/{id}/revoke`
- `POST /v1/songs/{id}/delete` creates tombstone, **not** immediate
  silent deletion on another device.

Enforce version compatibility: newer schema read-only or reject safely;
old clients cannot overwrite data they do not understand.

## Work breakdown and LOE

Estimates below assume **one experienced full-stack engineer**, existing
local Song Harbor functionality remains stable, managed identity/object
storage/billing services, and focused review/test support. Person-weeks
are approximate active engineering effort; elapsed calendar may be
longer because of security, provider onboarding, external reviews, tests.

| Phase | Deliverable | LOE | Gate |
| --- | --- | --- | --- |
| 0. Discovery/fixtures | 2-device workflow, representative 6/16/32 stems, quotas, media sizes, data mapping and threat model | 3-5 engineer-days | approved manifest boundaries and test corpus |
| 1. Sync-ready foundation | Versioned portable manifest, logical asset references, revision IDs, hash integrity, dependency closure, export/import without provider | 1-2 weeks | same project reconstructs on second Windows device offline |
| 2. Metadata-only proof | Local durable outbox, mock control plane, device/revision semantics, conflict copies and atomic merge/recovery | 1-2 weeks | two offline PCs cannot silently lose edits |
| 3. End-to-end media sync | Authenticated API, object storage adapter, uploads/downloads, resumability, dedupe, local availability/pinning UI | 3-5 weeks | full editable song with all stems survives sync and reopen |
| 4. Premium service integration | Auth/device management, verified subscription entitlements and quota enforcement, Stripe webhooks, billing failure/deletion states, docs | 2-3 weeks | payment and downgrade scenarios pass; local data unaffected |
| 5. Production hardening | Windows multi-device QA, security/access testing, corruption/retry/failure injection, observability, backups, account export/delete, cost controls | 2-4 weeks | production readiness and controlled beta |
| **Full paid offering** | **All phases** | **~12-21 calendar weeks** | stable private beta then commercial launch |

Milestone estimates:
- Foundation and metadata-only proof: **~3-5 weeks**.
- Usable two-device sync MVP with media, no commercial billing: **~8-13 weeks total**.
- Premium launch with entitlement, support and security: **~12-21 weeks total**.
Allow ~20-30% contingency when stems are unusually large or concurrency
semantics are more complex than expected. A narrow one-way encrypted
project **backup/restore** spike could be done faster (roughly 1-2 weeks)
but must never be marketed as conflict-safe device sync.

### Testing matrix

- New PC first sign-in, device revocation and selective song download.
- 6-, 16-, 32- and 64-stem projects including split children, imported
  clips, renamed aliases, section macros, original audio and accepted
  generated accompaniment; verify every referenced asset resolves.
- Offline edits on A and B, reconnect order permutations; same-field
  conflict produces preserved named branch, disjoint edits merge only if
  operation semantics prove safe.
- Upload interruption (1%, 50%, 99%), slow link, dedupe and hash mismatch;
  interrupted local write or service outage cannot corrupt saved project.
- Rename/delete vs modify; tombstones, undo grace, device reset and a
  stale client that reconnects after months.
- Windows path relocation and restored Library indexing; never copy
  `library.sqlite` raw across hosts. Keep non-reconstructed model cache
  local and tolerate missing plugins.
- Multi-hour offline editing; subscription expires mid-session; quota
  reached mid-upload; billing webhook duplicates/replay.
- Privacy/per-user authorization (including signed URL scope), path
  traversal, oversized asset denial, storage quota bypass and secrets
  exposure; account removal and delete/retention behavior.
- Golden acceptance: source/stem SHA-256 equality; sample-accurate
  alignment, automation output equivalence, deterministic WAV export
  comparison under the same processing engine and settings.
- No new startup requirements, GPU consumption or network calls required
  for local-only Free mode.

## Unit economics / pricing research — public indicative figures October 2026

R2 standard: ~$0.015/GB-month with zero egress fees, plus request
charges (Cloudflare pricing). B2: starts ~$6.95/TB-month with up to
3x stored-volume free egress, then overages (Backblaze 2026 pricing).
Managed auth, metadata DB, API compute, payment processing, logging,
fraud/abuse, storage versions, bandwidth above included and support
are incremental. These are **storage list rates, not a user price**.

Illustrative *storage-only* scenario, excluding free allowances, request
charges, extra replica/history overhead:
- 100 premium users × 20 GB average = 2,000 GB.
- R2 storage: **~$30/month**.
- B2 at $6.95/1,000GB: **~$13.90/month**.
- Effective provider invoice may differ materially due to bandwidth,
  object operations, safety replicas, data retention and actual average
  consumption. Don't choose on storage sticker price alone.

Revenue gates: compute contribution margin by storage percentile (P50/
P90/P99), monthly transfer/churn, device count, minimum margin,
chargeback/refund cost and support. Establish hard quota plus explicit
overage options; don't offer unbounded sync included at a low flat price.

## Product / UX acceptance

In Settings: **Cloud Sync (Premium)** with clear off / signed out /
syncing / synced / action needed state; account/device/quota/billing.
Library per-song cloud icon and `Keep on this device` action, transfer
progress and last sync timestamp. Conflict drawer shows both versions,
devices, timestamp and choices (`Keep both`, `Use A`, `Use B`,
manual comparison); default is **Keep both**, never destructive overwrite.
Paused/offline mode, metered network toggle and background bandwidth
limit. No large placeholder panels in the main waveform workbench.
Access to local projects persists after cancellation.

## Dependencies, risks and decisions to resolve

1. **Manifest and local index** first: how we serialize versioned
   projects and their complete transitive media dependencies.
2. **Storage vendor choice** on measured transfer patterns and abuse
   protection (B2 vs R2; S3-compatible adapter).
3. **Auth/payment** options and legal terms/privacy/deletion obligations.
4. **Premium plan definition:** device count, quota, max file, revision
   retention, restore policy, pricing and billing cadence.
5. **Conflict semantics:** choose coarse song revisions first; never
   promise automatic track-level collaborative merges until independently
   tested.
6. **Portable versions:** full immutable media versioning vs derived
   asset regeneration and snapshots, with long-term data retention cost.
7. **Optional BYO storage:** possible future use for Google Drive/OneDrive
   providers, but production correctness must be defined by Song Harbor's
   own manifests; don't just point multiple apps at live shared SQLite.
8. **Device trust:** protect auth tokens with Windows Credential Manager
   or equivalent secure store, rotate/revoke independently, never keep
   bucket-wide credentials client-side.
9. **Licensing/product constraints:** privacy disclosures, consent,
   commercial data retention, acceptable use and incident response.

## Recommended sequencing

Implement **Phase 0-1 portable snapshot/restore design first** while
Song Harbor is still growing its asset graph. Do **not** interrupt current
audio-engine/spatial scripting QA or paid release for a speculative full
cloud build. Then pilot metadata and conflict handling with the user's
two production machines. Add direct managed cloud media sync and paid
entitlements only after integrity tests prove song reconstruction on
another machine.

**Explicit non-goals in initial paid sync release:** simultaneous
multiplayer editing, browser DAW, cloud GPU rendering, sharing copyrighted
audio publicly, streaming unfinished stems without local availability,
cloud-only project storage, automatic merging of arbitrary conflicting
section scripts, or forced cloud login.
