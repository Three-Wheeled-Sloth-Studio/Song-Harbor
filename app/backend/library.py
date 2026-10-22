"""SQLite-backed Song Harbor Library: virtual organization over immutable media paths.

P0 is additive: adopt legacy projects without moving files, changing stems or
altering existing song UUID/job IDs. The DB indexes canonical relationships; a
sidecar project JSON preserves recovery metadata if the library DB is rebuilt.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
import uuid
from pathlib import Path

import projects

SCHEMA_VERSION = 1
SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY,
    legacy_job_id TEXT UNIQUE,
    title TEXT NOT NULL,
    imported_filename TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL
);
CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES collections(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    deleted_at REAL
);
CREATE TABLE IF NOT EXISTS collection_songs (
    collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    added_at REAL NOT NULL,
    PRIMARY KEY (collection_id, song_id)
);
CREATE TABLE IF NOT EXISTS song_links (
    child_song_id TEXT PRIMARY KEY REFERENCES songs(id) ON DELETE CASCADE,
    parent_song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    sha256 TEXT,
    kind TEXT NOT NULL DEFAULT 'original',
    imported_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS separations (
    id TEXT PRIMARY KEY,
    song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    model TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS versions (
    id TEXT PRIMARY KEY,
    song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES versions(id) ON DELETE SET NULL,
    separation_id TEXT REFERENCES separations(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    mix_manifest TEXT,
    created_at REAL NOT NULL,
    deleted_at REAL
);
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    song_id TEXT NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    version_id TEXT REFERENCES versions(id) ON DELETE SET NULL,
    separation_id TEXT REFERENCES separations(id) ON DELETE SET NULL,
    artifact_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    source_filename TEXT,
    sha256 TEXT,
    created_at REAL NOT NULL,
    deleted_at REAL,
    UNIQUE (song_id, storage_path)
);
CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title);
CREATE INDEX IF NOT EXISTS idx_versions_song ON versions(song_id, created_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_song ON artifacts(song_id, artifact_type);
CREATE INDEX IF NOT EXISTS idx_sources_song ON sources(song_id);
CREATE INDEX IF NOT EXISTS idx_collections_parent ON collections(parent_id);
"""


def fingerprint(path: Path) -> str:
    """Hash exact source bytes, not titles or paths; same media is one library song."""
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def database_path(data_root: Path) -> Path:
    return data_root / "library" / "library.sqlite"


def connect(data_root: Path) -> sqlite3.Connection:
    path = database_path(data_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SQL)
    conn.execute("INSERT OR IGNORE INTO schema_meta(name,value) VALUES('version',?)",
                 (str(SCHEMA_VERSION),))
    conn.commit()
    return conn


def _id(prefix: str, suffix: str) -> str:
    """Deterministic IDs make repeated adoption safe across DB resets."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"song-harbor:{prefix}:{suffix}"))


def adopt_jobs(data_root: Path) -> dict:
    """Read-only scan of existing media; only DB records are created/updated."""
    candidates = projects.list_projects(data_root)
    count = 0
    with connect(data_root) as conn:
        for entry in candidates:
            legacy_id = entry["id"]
            project = projects.read_project(data_root, legacy_id)
            if not project:
                continue
            song_id = _id("song", legacy_id)
            created = float(project.get("created_at") or time.time())
            conn.execute("""
                INSERT OR IGNORE INTO songs
                (id,legacy_job_id,title,imported_filename,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
            """, (song_id, legacy_id, project.get("title") or entry["filename"],
                  project["filename"], created, created))
            # Keep explicit Library renames; manifest renames are normally updated
            # through rename_song, which writes the manifest and DB together.
            source_id = _id("source", legacy_id)
            source = (data_root / "jobs" / legacy_id /
                      ("originals" if project.get("imported_tracks") else "") /
                      project["source_filename"])
            if not source.is_file():
                continue
            current = conn.execute("SELECT sha256 FROM sources WHERE id=?", (source_id,)).fetchone()
            # Existing hashes are persistent; scanning library does not rehash each source.
            source_hash = current["sha256"] if current and current["sha256"] else fingerprint(source)
            conn.execute("""
                INSERT OR IGNORE INTO sources
                (id,song_id,original_filename,storage_path,sha256,imported_at)
                VALUES(?,?,?,?,?,?)
            """, (source_id, song_id, project["source_filename"], str(source), source_hash, created))
            if current and not current["sha256"]:
                conn.execute("UPDATE sources SET sha256=? WHERE id=?", (source_hash, source_id))
            separation_id = _id("separation", legacy_id)
            conn.execute("""
                INSERT OR IGNORE INTO separations
                (id,song_id,source_id,model,created_at)
                VALUES(?,?,?,?,?)
            """, (separation_id, song_id, source_id,
                  project.get("model") or "htdemucs_6s.yaml", created))
            version_id = _id("version", legacy_id)
            manifest_path = projects.project_path(data_root, legacy_id)
            conn.execute("""
                INSERT OR IGNORE INTO versions
                (id,song_id,separation_id,title,mix_manifest,created_at)
                VALUES(?,?,?,?,?,?)
            """, (version_id, song_id, separation_id, "Initial mix",
                  str(manifest_path), created))
            for filename in project["files"]:
                path = data_root / "jobs" / legacy_id / "stems" / filename
                if not path.is_file():
                    continue
                conn.execute("""
                    INSERT OR IGNORE INTO artifacts
                    (id,song_id,version_id,separation_id,artifact_type,storage_path,
                     source_filename,created_at)
                    VALUES(?,?,?,?,?,?,?,?)
                """, (_id("stem", legacy_id + ":" + filename), song_id, version_id,
                      separation_id, "stem", str(path), filename, created))
            count += 1
        conn.commit()
    return {"examined": count, "database": str(database_path(data_root))}


def list_songs(data_root: Path, collection_id: str | None = None,
               query: str = "", include_deleted: bool = False) -> list[dict]:
    """One library row per identical source recording; separate jobs become variants."""
    with connect(data_root) as conn:
        rows = [dict(x) for x in conn.execute("""
            SELECT s.id, s.legacy_job_id, s.title, s.imported_filename, s.created_at,
                   s.updated_at, s.deleted_at, src.sha256,
                   (SELECT COUNT(*) FROM versions v WHERE v.song_id=s.id
                    AND v.deleted_at IS NULL) AS own_versions
            FROM songs s LEFT JOIN sources src ON src.song_id=s.id
            ORDER BY s.created_at ASC, s.id ASC
        """)]
        membership = set()
        if collection_id:
            membership = {x[0] for x in conn.execute(
                "SELECT song_id FROM collection_songs WHERE collection_id=?", (collection_id,))}
    with connect(data_root) as conn:
        links = {row["child_song_id"]: row["parent_song_id"] for row in
                 conn.execute("SELECT child_song_id,parent_song_id FROM song_links")}
    # Manual grouping overrides file fingerprints. It never alters sources.
    hash_leaders: dict[str, str] = {}
    for song in rows:
        if song["sha256"] and song["sha256"] not in hash_leaders:
            hash_leaders[song["sha256"]] = song["id"]
    def root_id(ident: str) -> str:
        seen = set()
        while ident in links and ident not in seen:
            seen.add(ident)
            ident = links[ident]
        return ident
    groups: dict[str, list[dict]] = {}
    for song in rows:
        ident = hash_leaders.get(song["sha256"], song["id"]) if song["sha256"] else song["id"]
        groups.setdefault(root_id(ident), []).append(song)
    result = []
    for group in groups.values():
        visible = [s for s in group if not s["deleted_at"]]
        candidates = group if include_deleted else visible
        if not candidates:
            continue
        if collection_id and not any(s["id"] in membership for s in group):
            continue
        # Earliest known copy is stable canonical identity; if removed, show next.
        primary = next((s for s in candidates if root_id(s["id"]) == root_id(group[0]["id"])), candidates[0])
        title = primary["title"]
        if query and query.lower() not in (
            title + " " + " ".join(s["imported_filename"] for s in group)
        ).lower():
            continue
        result.append({
            "id": primary["id"], "legacy_job_id": primary["legacy_job_id"],
            "title": title, "imported_filename": primary["imported_filename"],
            "created_at": primary["created_at"],
            "version_count": sum(s["own_versions"] for s in group),
            "variant_count": len(group),
            "fingerprint": (primary["sha256"] or "")[:12],
            "removed": not bool(visible),
            "variants": [
                {"id": s["id"], "legacy_job_id": s["legacy_job_id"],
                 "filename": s["imported_filename"], "created_at": s["created_at"],
                 "removed": bool(s["deleted_at"])}
                for s in group
            ],
        })
    result.sort(key=lambda item: item["created_at"], reverse=True)
    return result


def combine_takes(data_root: Path, parent_id: str, child_id: str) -> dict:
    """Make a user-selected source a take of another song, even if bytes differ."""
    if parent_id == child_id:
        raise ValueError("Select two different songs")
    with connect(data_root) as conn:
        ids = {row[0] for row in conn.execute(
            "SELECT id FROM songs WHERE id IN (?,?) AND deleted_at IS NULL",
            (parent_id, child_id))}
        if ids != {parent_id, child_id}:
            raise ValueError("Both songs must be available in the Library")
        current = conn.execute(
            "SELECT parent_song_id FROM song_links WHERE child_song_id=?", (parent_id,)
        ).fetchone()
        if current:
            raise ValueError("Choose a parent song that is not already a linked take")
        descendants = {row[0] for row in conn.execute(
            "SELECT child_song_id FROM song_links WHERE parent_song_id=?", (child_id,)
        )}
        if parent_id in descendants:
            raise ValueError("This link would create a cycle")
        conn.execute("""INSERT INTO song_links(child_song_id,parent_song_id,created_at)
                        VALUES(?,?,?)
                        ON CONFLICT(child_song_id) DO UPDATE SET
                          parent_song_id=excluded.parent_song_id""",
                     (child_id, parent_id, time.time()))
        conn.commit()
    return {"combined": True, "source_files_preserved": True}


def _group_ids(conn: sqlite3.Connection, song_id: str) -> set[str]:
    """Find the requested song and all exact-hash/manual variants, even if hidden."""
    row = conn.execute("""SELECT s.id,src.sha256 FROM songs s
                          LEFT JOIN sources src ON src.song_id=s.id
                          WHERE s.id=?""", (song_id,)).fetchone()
    if not row:
        raise ValueError("Library song not found")
    parent = conn.execute(
        "SELECT parent_song_id FROM song_links WHERE child_song_id=?", (song_id,)
    ).fetchone()
    anchor = parent[0] if parent else song_id
    ids = {anchor}
    hashes = {x[0] for x in conn.execute(
        "SELECT sha256 FROM sources WHERE song_id=?", (anchor,)) if x[0]}
    while True:
        current = ids.copy()
        if hashes:
            placeholders = ",".join("?" for _ in hashes)
            ids.update(x[0] for x in conn.execute(
                f"SELECT song_id FROM sources WHERE sha256 IN ({placeholders})", tuple(hashes)))
        parents = ",".join("?" for _ in ids)
        ids.update(x[0] for x in conn.execute(
            f"SELECT child_song_id FROM song_links WHERE parent_song_id IN ({parents})",
            tuple(ids)))
        if ids == current:
            break
    return ids


def remove_song(data_root: Path, song_id: str) -> dict:
    """Hide a song group in one transaction; never move or delete audio."""
    with connect(data_root) as conn:
        ids = _group_ids(conn, song_id)
        now = time.time()
        conn.executemany("UPDATE songs SET deleted_at=? WHERE id=?",
                         [(now, ident) for ident in ids])
        conn.commit()
    return {"removed": True, "files_preserved": True, "variant_count": len(ids)}


def restore_song(data_root: Path, song_id: str) -> dict:
    with connect(data_root) as conn:
        ids = _group_ids(conn, song_id)
        conn.executemany("UPDATE songs SET deleted_at=NULL WHERE id=?",
                         [(ident,) for ident in ids])
        conn.commit()
    return {"restored": True, "files_preserved": True}



def rename_song(data_root: Path, song_id: str, title: str) -> dict:
    clean = title.strip()
    if not clean or len(clean) > 120:
        raise ValueError("Song title must contain 1-120 characters")
    with connect(data_root) as conn:
        entry = conn.execute(
            "SELECT legacy_job_id FROM songs WHERE id=? AND deleted_at IS NULL", (song_id,)
        ).fetchone()
        if entry is None:
            raise ValueError("Song not found")
        legacy_id = entry["legacy_job_id"]
        if legacy_id:
            record = projects.read_project(data_root, legacy_id)
            if record:
                record["title"] = clean
                record["updated_at"] = time.time()
                projects.write_project(data_root, record)
        conn.execute("UPDATE songs SET title=?,updated_at=? WHERE id=?",
                     (clean, time.time(), song_id))
        conn.commit()
    return {"id": song_id, "title": clean}


def list_collections(data_root: Path) -> list[dict]:
    with connect(data_root) as conn:
        return [dict(row) for row in conn.execute("""
            SELECT c.id,c.parent_id,c.title,c.sort_order,
                   COUNT(cs.song_id) AS song_count
            FROM collections c
            LEFT JOIN collection_songs cs ON cs.collection_id=c.id
            WHERE c.deleted_at IS NULL
            GROUP BY c.id ORDER BY c.sort_order,c.title
        """)]


def create_collection(data_root: Path, title: str, parent_id: str | None = None) -> dict:
    clean = title.strip()
    if not clean or len(clean) > 120:
        raise ValueError("Collection title must contain 1-120 characters")
    with connect(data_root) as conn:
        if parent_id is not None and not conn.execute(
                "SELECT 1 FROM collections WHERE id=? AND deleted_at IS NULL",
                (parent_id,)).fetchone():
            raise ValueError("Parent collection not found")
        ident = str(uuid.uuid4())
        conn.execute("INSERT INTO collections(id,parent_id,title,created_at) VALUES(?,?,?,?)",
                     (ident, parent_id, clean, time.time()))
        conn.commit()
    return {"id": ident, "title": clean, "parent_id": parent_id}


def assign_song(data_root: Path, song_id: str, collection_id: str) -> None:
    with connect(data_root) as conn:
        if not conn.execute("SELECT 1 FROM songs WHERE id=? AND deleted_at IS NULL",
                            (song_id,)).fetchone():
            raise ValueError("Song not found")
        if not conn.execute("SELECT 1 FROM collections WHERE id=? AND deleted_at IS NULL",
                            (collection_id,)).fetchone():
            raise ValueError("Collection not found")
        conn.execute("INSERT OR IGNORE INTO collection_songs(collection_id,song_id,added_at) VALUES(?,?,?)",
                     (collection_id, song_id, time.time()))
        conn.commit()
