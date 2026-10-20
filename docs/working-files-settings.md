# Working files location and cloud sync

Status: implemented settings selection, **not verified on Windows**.

Song Harbor's header gear opens a compact Settings dialog. Choose a dedicated **Working files** folder via the Windows folder picker or by typing a fully qualified path, then Save. The new path takes effect after closing Song Harbor and relaunching it. The location is stored only on this machine in `<runtime>/config/settings.json`; Python, models, application assets and caches remain local.

**No automatic migration.** Changing directories does not copy, delete or relink existing songs, stem files or exports. The old folder remains intact. Returning to it restores access to its existing library. If the new location already has a Song Harbor `jobs/` structure and library, that workspace becomes visible on restart. Copy closed project data deliberately and back it up before attempting a migration. A complete tested migration/reconcile flow is future work.

## Google Drive cautions

This setting is suitable for a **Google Drive for desktop mirrored local folder** when the directory is physically available on the machine. For a streamed/online-only folder, large media and live SQLite operations can produce poor performance or missing-file errors; ensure files are available offline before opening. Confirm the actual local path on every machine instead of assuming matching drive letters.

The current Library uses `library/library.sqlite` with SQLite WAL and stores physical media paths in several tables. Cloud file synchronization is **not** a multi-user database service. Do not open Song Harbor against the same synced workspace on more than one computer at the same time. Close Song Harbor and allow Google Drive to finish sync before switching computers, and keep an independent backup. Different machines' path prefixes may not be portable; existing job manifests are the recovery source and library re-index/relink is needed for robust cross-machine portability. No cross-machine concurrency coordination or transparent database merge is implemented.

**Recommended long-term architecture:** Machine-local SQLite index, model weights, caches and temporary renders; cloud-synced immutable source media, stem assets, portable per-song manifests and finalized versions. Reconstruct local indexes from manifests. Add explicit background sync/reconcile, locking and collision-safe version branching rather than syncing a live SQLite database.

## Dependency settings

The gear opens working-files settings plus a collapsed Components subsection. FFmpeg locate/search/install is available on demand there, while a missing FFmpeg during separation/mix export still opens just-in-time dependency recovery. No large persistent dependency panel belongs in the library/workspace.

## Acceptance checks (pending)

- Change working folder on Predator; restart; verify new data root, preserved old project files and metadata.
- Point to an existing closed Song Harbor working folder; confirm projects are visible without copying.
- FFmpeg remains configured and just-in-time recovery resumes a pending operation.
- Settings responsive and compact, with setup actions hidden unless requested.
- Validate installed Google Drive mirrored path, available-offline behavior, and sequential cross-machine open after sync.
- Verify paths and Library index behavior when Predator and Omen have different directory structures.
