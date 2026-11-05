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

MAX_ARCHIVE_BYTES = 4 * 1024 * 1024 * 1024  # Large local sample libraries
MAX_UNPACKED_BYTES = 8 * 1024 * 1024 * 1024  # Still bounded against ZIP bombs
MAX_FILES = 12000
MAX_SFZ_BYTES = 2 * 1024 * 1024
# SFZ #include legitimately uses .txt data fragments (e.g. Muldjord).
# These are inspected as text only, never executed or interpreted as code.
TEXT_EXTENSIONS = {".sfz", ".txt"}
EXTENSIONS = TEXT_EXTENSIONS | {".wav", ".flac", ".aif", ".aiff", ".ogg"}
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
            if path.suffix.lower() in TEXT_EXTENSIONS and member.file_size > MAX_SFZ_BYTES:
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


# Tokenize preprocessing directives wherever they appear in a line.
# Muldjord uses '<global> #include ...' and multiple #defines per line.
PREPROCESSOR = re.compile(r'#\s*(include|define)\b', re.IGNORECASE)
MACRO_NAME = re.compile(r'\$[A-Za-z_][A-Za-z_0-9]*')
MAX_INCLUDE_DEPTH = 40
MAX_REFERENCED_SAMPLES = 30000
MAX_INCLUDE_VISITS = 8000


def audit_pack(destination: Path) -> tuple[list[dict], list[dict]]:
    """Audit SFZ programs, including pack-local .txt fragments and sample macros.

    Validation simulates the data-only subset of SFZ preprocessing. Never
    execute a directive, access outside the installed folder, or substitute a
    missing asset. The actual renderer still handles musical SFZ opcodes.
    """
    definitions = sorted(p for p in destination.rglob("*")
                         if p.suffix.lower() == ".sfz" and p.is_file())
    included: set[Path] = set()
    for definition in definitions:
        for match in re.finditer(r'#\s*include\s+["\x27]([^"\x27]+)["\x27]',
                                 definition.read_text(encoding="utf-8-sig"), re.I):
            try:
                child = resolve_pack_reference(definition, match.group(1), destination,
                                               allowed=TEXT_EXTENSIONS, purpose="include")
                if child.suffix.lower() == ".sfz":
                    included.add(child.resolve())
            except ValueError:
                pass

    def validate_program(definition: Path) -> None:
        # Macros are scoped to the program, but are shared across nested
        # text fragments exactly as SFZ preprocessors intend.
        macros: dict[str, str] = {}
        prefix = ""
        visited = 0
        sampled = 0

        def substitute(text: str) -> str:
            for _ in range(8):
                updated = MACRO_NAME.sub(lambda match: macros.get(match.group(0),
                                                                  match.group(0)), text)
                if updated == text:
                    break
                text = updated
            if MACRO_NAME.search(text):
                raise ValueError("SFZ sample path uses an unresolved macro: " + text[:100])
            return text

        def scan_segment(segment: str, current: Path) -> None:
            nonlocal prefix, sampled
            for match in DEFAULT_PATH.finditer(segment):
                # A path is relative to the program/include context, not to
                # the source machine; validate with each resolved sample.
                prefix = substitute(match.group(1).strip().strip('"').replace("\\", "/"))
                if prefix.startswith("/") or re.match(r"^[A-Za-z]:", prefix):
                    raise ValueError("SFZ default_path escapes the imported pack")
            for match in SAMPLE_REF.finditer(segment):
                sample = substitute(match.group(1).strip().strip('"').replace("\\", "/"))
                if sample == "*silence":
                    continue
                sampled += 1
                if sampled > MAX_REFERENCED_SAMPLES:
                    raise ValueError("SFZ program has too many sample references")
                resolve_pack_reference(current, prefix + sample, destination,
                                       allowed=EXTENSIONS - TEXT_EXTENSIONS,
                                       purpose="sample")

        def scan_file(current: Path, active: set[Path], depth: int) -> None:
            nonlocal visited
            current = current.resolve()
            if current in active:
                raise ValueError("SFZ includes contain a cycle")
            if depth > MAX_INCLUDE_DEPTH:
                raise ValueError("SFZ include nesting is too deep")
            visited += 1
            if visited > MAX_INCLUDE_VISITS:
                raise ValueError("SFZ has too many expanded includes")
            active.add(current)
            try:
                # ZIP members have already passed the per-text-file size check.
                content = current.read_text(encoding="utf-8-sig")
                for raw in content.splitlines():
                    line = raw.split("//", 1)[0]
                    cursor = 0
                    for directive in PREPROCESSOR.finditer(line):
                        scan_segment(line[cursor:directive.start()], current)
                        rest = line[directive.end():]
                        if directive.group(1).lower() == "include":
                            inc = re.match(r'\s*["\x27]([^"\x27]+)["\x27]', rest)
                            if not inc:
                                raise ValueError("Malformed SFZ include directive")
                            child = resolve_pack_reference(
                                current, substitute(inc.group(1)), destination,
                                allowed=TEXT_EXTENSIONS, purpose="include")
                            scan_file(child, active, depth + 1)
                            cursor = directive.end() + inc.end()
                        else:
                            define = re.match(r'\s*(\$[A-Za-z_][A-Za-z_0-9]*)\s+([^\s#]+)', rest)
                            if not define:
                                raise ValueError("Malformed SFZ macro definition")
                            macros[define.group(1)] = define.group(2)
                            cursor = directive.end() + define.end()
                    scan_segment(line[cursor:], current)
                    # Reject any other preprocessor directives explicitly.
                    for unknown in re.finditer(r'#\s*([A-Za-z_]+)\b', line):
                        if unknown.group(1).lower() not in {"include", "define"}:
                            raise ValueError("SFZ definition uses unsupported preprocessing")
            finally:
                active.remove(current)

        scan_file(definition, set(), 0)

    instruments = []
    unavailable = []
    for definition in definitions:
        if definition.resolve() in included:
            continue
        try:
            validate_program(definition)
        except (ValueError, OSError, UnicodeError) as exc:
            unavailable.append({"name": definition.stem[:100],
                                "reason": str(exc)[:180]})
            continue
        instruments.append({"id": f"sfz-{len(instruments)}",
                            "name": definition.stem[:100],
                            "sfz_path": definition.relative_to(destination).as_posix(),
                            "program": 0, "bank": 0})
    return instruments, unavailable


def install_zip(runtime: Path, archive: Path, name: str, *, curated_id: str = "") -> dict:
    """Install self-contained samples, rejecting unsafe references and malformed archives."""
    members = inspect_archive(archive)
    root = runtime / "instrument-packs"
    root.mkdir(parents=True, exist_ok=True)
    identifier = "sfz-" + uuid.uuid4().hex[:16]
    destination = root / identifier
    destination.mkdir()
    ignored_files = 0
    # ZIP metadata was validated before creating the destination. Ensure ample
    # storage for the declared unpacked payload plus a small free-space reserve.
    declared=sum(m.file_size for m in members if not m.is_dir() and not is_ignorable_member(safe_member(m.filename)))
    required=declared + 512 * 1024 * 1024
    if shutil.disk_usage(root).free < required:
        shutil.rmtree(destination,ignore_errors=True)
        raise ValueError("Not enough disk space for SFZ samples (need unpacked size plus 512 MiB reserve)")
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
