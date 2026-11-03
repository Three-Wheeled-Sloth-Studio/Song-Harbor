"""Bounded, data-only import for user-provided SFZ ZIP packs.

No downloaded samples, no code execution, no support for external paths.
This intentionally supports self-contained SFZ and sample files only.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath

MAX_ARCHIVE_BYTES = 768 * 1024 * 1024
MAX_UNPACKED_BYTES = 1536 * 1024 * 1024
MAX_FILES = 12000
MAX_SFZ_BYTES = 2 * 1024 * 1024
EXTENSIONS = {".sfz", ".wav", ".flac", ".aif", ".aiff", ".ogg"}
UNSAFE_SFZ = re.compile(r"(?im)^\s*#\s*(?:include|define)\b|(?:^|\s)(?:sample|default_path)\s*=\s*(?:[A-Za-z]:|/|\\\\|\\)")
SAMPLE_REF = re.compile(r"(?im)(?:^|\s)sample\s*=\s*([^\r\n]+)")


def safe_member(name: str) -> PurePosixPath:
    if "\\" in name or "\x00" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        raise ValueError("SFZ archive contains an unsafe path")
    path = PurePosixPath(name)
    if any(p in ("", ".", "..") for p in path.parts) or not path.parts:
        raise ValueError("SFZ archive contains a traversal path")
    return path


def inspect_archive(archive: Path) -> list[zipfile.ZipInfo]:
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("SFZ archive is too large")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not 1 <= len(members) <= MAX_FILES:
            raise ValueError("SFZ pack has an invalid number of files")
        total = 0
        seen: set[str] = set()
        for member in members:
            path = safe_member(member.filename)
            canonical = str(path).casefold()
            if canonical in seen:
                raise ValueError("Duplicate SFZ archive paths")
            seen.add(canonical)
            kind = (member.external_attr >> 16) & 0o170000
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("SFZ archive links and special files are forbidden")
            if member.is_dir():
                continue
            if path.suffix.lower() not in EXTENSIONS:
                raise ValueError("SFZ ZIP contains unsupported file type")
            if member.file_size < 0 or member.file_size > MAX_UNPACKED_BYTES:
                raise ValueError("Oversized sample in SFZ archive")
            if path.suffix.lower() == ".sfz" and member.file_size > MAX_SFZ_BYTES:
                raise ValueError("SFZ definition exceeds size limit")
            total += member.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("SFZ archive exceeds uncompressed size limit")
        if not any(PurePosixPath(m.filename).suffix.lower() == ".sfz" for m in members):
            raise ValueError("SFZ archive contains no instrument")
        return members


def install_zip(runtime: Path, archive: Path, name: str) -> dict:
    """Install self-contained samples, rejecting unsafe references and malformed archives."""
    members = inspect_archive(archive)
    root = runtime / "instrument-packs"
    root.mkdir(parents=True, exist_ok=True)
    identifier = "sfz-" + uuid.uuid4().hex[:16]
    destination = root / identifier
    destination.mkdir()
    try:
        with zipfile.ZipFile(archive) as z:
            for member in members:
                relative = safe_member(member.filename)
                target = destination.joinpath(*relative.parts)
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024*1024)
        definitions = sorted(p for p in destination.rglob("*") if p.suffix.lower() == ".sfz" and p.is_file())
        manifest_instruments = []
        for index, definition in enumerate(definitions):
            text = definition.read_text(encoding="utf-8-sig")
            if UNSAFE_SFZ.search(text) or ".." in text:
                raise ValueError("SFZ definition uses external paths or unsupported preprocessing")
            # Permit references to samples inside the imported archive only. No shell or plugin scripts.
            for found in SAMPLE_REF.finditer(text):
                sample = found.group(1).strip().strip('"').replace("\\", "/")
                if not sample or sample.startswith("/") or re.match(r"^[A-Za-z]:", sample):
                    raise ValueError("Unsafe SFZ sample reference")
                if any(part == ".." for part in PurePosixPath(sample).parts):
                    raise ValueError("SFZ sample reference escapes pack")
            relative = definition.relative_to(destination).as_posix()
            manifest_instruments.append({"id": f"sfz-{index}", "name": definition.stem[:100],
                                         "sfz_path": relative, "program": 0, "bank": 0})
        digest = hashlib.sha256()
        for path in sorted(p for p in destination.rglob("*") if p.is_file()):
            digest.update(path.relative_to(destination).as_posix().encode("utf-8"))
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        manifest = {"schema_version": 1, "id": identifier, "name": name.strip()[:100] or "SFZ pack",
                    "engine": "sfz", "source": "user-installed",
                    "sha256": digest.hexdigest(), "instruments": manifest_instruments}
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"pack_id": identifier, "instruments": len(manifest_instruments)}
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
