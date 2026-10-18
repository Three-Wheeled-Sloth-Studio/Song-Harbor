# Song Harbor — Library-first architecture and interaction contract

Status: **approved direction / implementation roadmap** (2026-10-18). Establish the durable data model before redesigning the landing page. Existing separation and mix functions stay available during migration.

## Product entry and navigation

The **Library** is the default home; not a marketing/onboarding page and not a large separator form. Header: product identity + breadcrumb, compact search, import/add, contextual status and settings. Left: collapsible virtual collection tree (including All Songs / Unassigned). Center: compact song list with sortable columns, search and icon actions. Footer: reusable media transport with monitor-only master volume and track info. Open song to enter the **Song Workspace**, with tabs/surfaces for Mixer, Versions, Stems and Exports. Separation is an action in the song workspace, not an alternate product homepage.

No spacious tile farms, instruction cards or persistent setup banners. Icons → brief tooltips → contextual Help / right-click → full docs. A short label is justified only if icons alone are ambiguous. Controls require accessible names, keyboard alternatives and touch/overflow equivalents. Use TWS-UI shared components and extract missing primitives upstream.

## Canonical identity and physical storage

Logical library entries must be completely independent of paths. Use SQLite in `<runtime>/data/library/library.sqlite` as the authoritative **index** for collections, membership, tags, song identity and cross-asset relationships. Persist a portable `song.json` manifest alongside the song's durable assets so the library can be rebuilt from an existing folder or backup. The indexed path is metadata, not identity.

Planned physical layout (migration target; never relocate old data as part of schema initialization):

```text
<runtime>/data/
  library/library.sqlite
  songs/<song-uuid>/
    song.json
    sources/<source-uuid>/<original-filename>
    separations/<separation-uuid>/
    versions/<version-uuid>/
      mix.json
      renders/<render-uuid>.wav
      exports/<export-uuid>/
  jobs/<legacy-job-id>/    # preserved until explicitly migrated
  trash/
```

All large recordings and derived media remain on the configured runtime work drive, never in Git or under a transient build cache. Prefer references and checksums to content duplication; handle external audio relocation through a user-guided relink operation.

### Entities

- **Collection:** UUID, label, optional parent collection, sort order; arbitrary depth; virtual only. Renaming/moving a collection never touches files. Multiple memberships are allowed and must not copy sources.
- **Song:** immutable UUID, **editable display title**, optional artist/album metadata, timestamps and status. Title changes do not rename WAV/MP3 files or invalidate referenced audio. Provide a separate, explicit Rename exported files operation later if needed.
- **Source:** immutable UUID, song ID, physical path, original filename, checksum, decoded duration, format, ingestion time and role (original, alternate master, imported revision). Multiple original/source revisions belong to one song.
- **Separation:** UUID, source ID, model/version/parameters and completion state; each separation owns its derived stem artifacts. Multiple separation attempts coexist.
- **Version:** UUID, song ID, parent version ID (for branching), source/separation reference, display label, non-destructive mix state and timestamp. A saved alternative never overwrites a different named version.
- **Artifact:** UUID, song/version/source/separation IDs as applicable, kind (stem, render, master, DAW exchange, analysis), path, checksum, size, and export provenance. Track multiple exports separately; never silently overwrite.
- **DAW target:** adapter ID, path/config state, supported export format, optional installed executable, last used. Default supported adapter: Waveform Free; REAPER next.
- **Tag:** reusable tags attach to songs, optionally versions and collections.

### Deletion, rename, and retention

- Destructive operations are **soft delete** by default with recovery. Delete a collection = remove grouping/membership, not recordings. Delete a mix/version = mark version and its uniquely owned artifacts for Trash, never shared stem/source files. Delete an export = archive/remove only that export, not its source stems.
- Show effects of permanent deletion, including references from other versions. Prefer checkable trash actions and clear shared-asset retention.
- Rename in place by pencil beside the user-visible title; Enter saves, Escape cancels; never use the physical filename as mutable song identity.
- Never reuse a version/artifact identifier or overwrite existing DAW exports on later handoffs.

## Ingestion, migration and duplication

1. On startup create/upgrade SQLite schema transactionally. Do not move or delete existing `data/jobs/<id>` directories.
2. Scan legacy six-stem projects and import idempotently into the Library by existing job ID; preserve original title and original filename as different fields.
3. Create initial source, separation and version metadata per legacy job; don't pretend additional named versions exist when they don't.
4. Later build optional deduplication/relink workflows: equal SHA-256 indicates identical media, but do not auto-merge creative identities based on filename alone.
5. Detect missing files and surface a small recovery action at point of use instead of dropping song entries from the Library.
6. Verify backup/restore against a copy of existing project folders before making any automatic filesystem migration.

## DAW handoff and dependency recovery

**Export to DAW** is a generic action, not Waveform branding. First click opens a compact target selector (Waveform Free initially; REAPER next). Preparing a portable six-stem exchange does not require the DAW installed. The adapter output contains aligned stems, manifest and import notes, stored as a distinct artifact under the song/version history. Launch/Open in DAW *does* require an executable; if absent, guide Detect → Browse installed → Publisher download → Choose/run signed installer → Detect again, remembering path. No raw `Not Found` UX.

Waveform's download and account/activation steps are publisher-controlled. Open the official publisher destination when necessary, but return the user to the same in-app workflow; never invent an unofficial installer link or bypass account acceptance. Later a vetted silent package mechanism may offer fully automatic installation where legally and technically supported. Native `.tracktionedit` generation follows validation against installed Waveform, not guesswork.

## Cross-project components to extract into TWS-UI

- Dense virtual collection tree + collapsible multi-column song list, selection and accessible context menu.
- Shared icon-first item action + tooltip/help ladder, overflow/touch/keyboard actions and rename-in-place.
- Reusable transport with play/pause, seek, monitoring gain, keyboard controls and optional waveform.
- Unified external-tool discovery/setup dialog and operation feedback.
- Version history/compare strip and soft-delete confirmation patterns.

## Implementation gates

P0: SQLite schema, read-only legacy adoption, non-destructive rename metadata; tests for idempotency and external files.
P1: Library landing with virtual collections, drag/move metadata only, search and compact recent song rows.
P2: Song workspace, branchable named versions, multiple exports and selective restore/delete.
P3: Shared UI extraction, contextual menus, icon/hover/help, monitor volume and accessibility audits.
P4: Adapter-based DAW export/launch, Waveform setup/recovery and validated native format, then REAPER support.

Do not treat this design document as proof every gate is complete: the current backend still indexes legacy per-job manifests rather than the finished canonical SQLite library.
