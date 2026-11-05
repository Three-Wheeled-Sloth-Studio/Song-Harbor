"""Bounded, data-only import for user-provided SFZ ZIP packs.

No downloaded samples, no code execution, no support for external paths.
This intentionally supports self-contained SFZ and sample files only.
"""
from __future__ import annotations
import hashlib
import json
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
# Ignore documentation/GUI resources rather than executing or importing them.
METADATA_EXTENSIONS = {".txt", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".xml", ".html", ".htm", ".json", ".svg", ".nki", ".nkm", ".nkc", ".nkr", ".nkx"}
METADATA_NAMES = {"readme", "license", "copying", "authors", "changelog", "notice"}


def is_ignorable_member(path: PurePosixPath) -> bool:
    """Skip platform sidecars, GUI/docs and unrecognized companions; never execute."""
    if "__macosx" in (part.casefold() for part in path.parts):
        return True
    if path.name.startswith("._") or path.name.casefold() in (".ds_store", "thumbs.db"):
        return True
    return path.suffix.lower() not in EXTENSIONS
SFZ_DIRECTIVE = re.compile(r"(?im)^\s*#\s*([A-Za-z_]+)\b")
INCLUDE_REF = re.compile(r'(?im)^\s*#\s*include\s+["\']([^"\']+)["\']')

DEFAULT_PATH = re.compile(r"(?im)(?:^|\s)default_path\s*=\s*(.+?)(?=\s+[A-Za-z_][A-Za-z_0-9]*\s*=|$)")
SAMPLE_REF = re.compile(r"(?im)(?:^|\s)sample\s*=\s*(.+?)(?=\s+[A-Za-z_][A-Za-z_0-9]*\s*=|$)")


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
            # Third-party packs often include sampler presets, GUI resources,
            # metadata databases or desktop files. Validate their size/path
            # but NEVER extract or execute them. Only whitelisted SFZ/audio
            # members reach the installed instrument folder.
            # A referenced skipped sample will still fail the sample check.
            if member.file_size < 0 or member.file_size > MAX_UNPACKED_BYTES:
                raise ValueError("Oversized sample in SFZ archive")
            if path.suffix.lower() == ".sfz" and member.file_size > MAX_SFZ_BYTES:
                raise ValueError("SFZ definition exceeds size limit")
            total += member.file_size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("SFZ archive exceeds uncompressed size limit")
        if not any(PurePosixPath(m.filename).suffix.lower() == ".sfz"
                   and not is_ignorable_member(PurePosixPath(m.filename)) for m in members):
            raise ValueError("SFZ archive contains no instrument")
        return members


def resolve_pack_reference(definition: Path, value: str, root: Path,
                           *, allowed: set[str], purpose: str) -> Path:
    """Resolve only existing pack-owned files with SFZ program-relative paths.

    Nested Big Rusty mapping includes refer to sample and mapping roots from
    the parent Programs directory rather than the nested include directory.
    Candidate directories are ancestors INSIDE the imported pack only.
    """
    value = value.strip().strip('"').replace("\\", "/")
    if not value or "\x00" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("Unsafe SFZ " + purpose + " reference")
    root = root.resolve()
    folder = definition.parent.resolve()
    while folder.is_relative_to(root):
        candidate = (folder / value).resolve()
        if candidate.is_relative_to(root) and candidate.suffix.lower() in allowed and candidate.is_file():
            return candidate
        if folder == root:
            break
        folder = folder.parent
    raise ValueError("SFZ references a missing or external " + purpose + ": " + value[:120])


def audit_pack(destination: Path) -> tuple[list[dict], list[dict]]:
    """Audit playable programs without changing files or claiming missing samples."""
    definitions = sorted(p for p in destination.rglob("*")
                         if p.suffix.lower() == ".sfz" and p.is_file())
    # Work out which .sfz files are mapping fragments. All are still
    # data-only, but only root programs are advertised to the user.
    included: set[Path] = set()
    for definition in definitions:
        text = definition.read_text(encoding="utf-8-sig")
        for found in INCLUDE_REF.finditer(text):
            try:
                included.add(resolve_pack_reference(
                    definition, found.group(1), destination,
                    allowed={".sfz"}, purpose="include"))
            except ValueError:
                # Validate the complete dependency when the corresponding
                # playable program is inspected, not for unrelated patches.
                pass

    def validate_program(definition: Path, active: set[Path],
                         *, inherited_path: str = "") -> None:
        definition = definition.resolve()
        if definition in active:
            raise ValueError("SFZ includes contain a cycle")
        active.add(definition)
        try:
            text = definition.read_text(encoding="utf-8-sig")
            for directive in SFZ_DIRECTIVE.finditer(text):
                if directive.group(1).casefold() not in {"include", "define"}:
                    raise ValueError("SFZ definition uses unsupported preprocessing")
            defaults = [match.group(1).strip().strip('"').replace("\\", "/")
                        for match in DEFAULT_PATH.finditer(text)]
            if len(defaults) > 1:
                raise ValueError("Multiple SFZ default_path assignments are unsupported")
            prefix = defaults[0] if defaults else inherited_path
            if prefix.startswith("/") or re.match(r"^[A-Za-z]:", prefix):
                raise ValueError("SFZ default_path escapes the imported pack")
            for found in SAMPLE_REF.finditer(text):
                sample = found.group(1).strip().strip('"').replace("\\", "/")
                if sample == "*silence":
                    continue
                resolve_pack_reference(definition, prefix + sample, destination,
                                       allowed=EXTENSIONS - {".sfz"}, purpose="sample")
            for found in INCLUDE_REF.finditer(text):
                child = resolve_pack_reference(
                    definition, found.group(1), destination,
                    allowed={".sfz"}, purpose="include")
                validate_program(child, active, inherited_path=prefix)
        finally:
            active.remove(definition)

    manifest_instruments = []
    unavailable_programs = []
    for definition in definitions:
        if definition.resolve() in included:
            continue
        try:
            validate_program(definition, set())
        except (ValueError, OSError, UnicodeError) as exc:
            unavailable_programs.append({
                "name": definition.stem[:100],
                "reason": str(exc)[:180]})
            continue
        relative = definition.relative_to(destination).as_posix()
        manifest_instruments.append({
            "id": f"sfz-{len(manifest_instruments)}",
            "name": definition.stem[:100],
            "sfz_path": relative, "program": 0, "bank": 0})
    return manifest_instruments, unavailable_programs


def install_zip(runtime: Path, archive: Path, name: str, *, curated_id: str = "") -> dict:
    """Install self-contained samples, rejecting unsafe references and malformed archives."""
    members = inspect_archive(archive)
    root = runtime / "instrument-packs"
    root.mkdir(parents=True, exist_ok=True)
    identifier = "sfz-" + uuid.uuid4().hex[:16]
    destination = root / identifier
    destination.mkdir()
    ignored_files = 0
    try:
        with zipfile.ZipFile(archive) as z:
            for member in members:
                relative = safe_member(member.filename)
                target = destination.joinpath(*relative.parts)
                if member.is_dir():
                    continue
                if is_ignorable_member(relative):
                    ignored_files += 1
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as source, target.open("xb") as output:
                    extracted = 0
                    while chunk := source.read(1024 * 1024):
                        extracted += len(chunk)
                        if extracted > member.file_size or extracted > MAX_UNPACKED_BYTES:
                            raise ValueError("SFZ ZIP entry expanded beyond declared size")
                        output.write(chunk)
                    if extracted != member.file_size:
                        raise ValueError("SFZ ZIP entry has an unexpected size")
        manifest_instruments, unavailable_programs = audit_pack(destination)
        if not manifest_instruments and not curated_id:
            details = "; ".join(item["name"] + ": " + item["reason"]
                                for item in unavailable_programs[:3])
            raise ValueError("SFZ pack contains no complete instrument programs" +
                             (": " + details if details else ""))
        # Retain incomplete curated packs for an explicitly approved repair,
        # never publish their incomplete SFZ programs as usable instruments.
        if not manifest_instruments and not unavailable_programs:
            raise ValueError("SFZ pack contains no instrument programs")
        digest = hashlib.sha256()
        for path in sorted(p for p in destination.rglob("*") if p.is_file()):
            digest.update(path.relative_to(destination).as_posix().encode("utf-8"))
            content_hash = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    content_hash.update(chunk)
            digest.update(content_hash.digest())
        manifest = {"schema_version": 1, "id": identifier, "name": name.strip()[:100] or "SFZ pack",
                    "engine": "sfz", "source": "user-installed",
                    "curated_id": curated_id,
                    "sha256": digest.hexdigest(), "instruments": manifest_instruments,
                    "unavailable_program_count": len(unavailable_programs)}
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"pack_id": identifier, "instruments": len(manifest_instruments),
                "ignored_support_files": ignored_files,
                "unavailable_programs": unavailable_programs[:20],
                "unavailable_program_count": len(unavailable_programs)}
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
