"""SQLite-backed Song Harbor Library: virtual organization over immutable media paths.

P0 is additive: adopt legacy projects without moving files, changing stems or
altering existing song UUID/job IDs. The DB indexes canonical relationships; a
sidecar project JSON preserves recovery metadata if the library DB is rebuilt.
"""
from __future__ import annotations

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
            source = data_root / "jobs" / legacy_id / project["source_filename"]
            if not source.is_file():
                continue
            conn.execute("""
                INSERT OR IGNORE INTO sources
                (id,song_id,original_filename,storage_path,imported_at)
                VALUES(?,?,?,?,?)
            """, (source_id, song_id, project["source_filename"], str(source), created))
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
               query: str = "") -> list[dict]:
    with connect(data_root) as conn:
        sql = """
            SELECT s.id,s.legacy_job_id,s.title,s.imported_filename,s.created_at,
                   COUNT(DISTINCT v.id) as version_count
            FROM songs s
            LEFT JOIN versions v ON v.song_id=s.id AND v.deleted_at IS NULL
        """
        args: list = []
        clauses = ["s.deleted_at IS NULL"]
        if collection_id:
            sql += " JOIN collection_songs cs ON cs.song_id=s.id "
            clauses.append("cs.collection_id=?")
            args.append(collection_id)
        if query:
            clauses.append("(s.title LIKE ? OR s.imported_filename LIKE ?)")
            escaped = "%" + query.replace("%", r"\%").replace("_", r"\_") + "%"
            args.extend([escaped, escaped])
        sql += " WHERE " + " AND ".join(clauses)
        sql += " GROUP BY s.id ORDER BY s.updated_at DESC, s.title ASC"
        return [dict(row) for row in conn.execute(sql, args)]


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
