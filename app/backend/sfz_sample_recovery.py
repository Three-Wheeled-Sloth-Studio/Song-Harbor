"""Explicit, bounded SFZ repair for publisher-curated packs only.

Runs inside the API's project lock. No arbitrary URLs, user-supplied paths or
substitute sounds. Locally stage and verify exact audio paths first; optional
publisher retrieval occurs ONLY for this user-invoked endpoint.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse
import curated_sfz
import sfz_pack

MAX_REPAIRS=8
MAX_FILE_BYTES=16*1024*1024
MAX_TOTAL_BYTES=64*1024*1024
MISSING="SFZ references a missing or external sample: "
MAGIC={".flac":b"fLaC",".wav":b"RIFF",".ogg":b"OggS",".aif":b"FORM",".aiff":b"FORM"}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def official_base(entry:dict)->str:
    url=urlparse(entry["source_page"])
    if url.scheme!="https" or url.hostname!="github.com":
        raise ValueError("Curated publisher repository must be on GitHub")
    parts=[p for p in url.path.strip("/").split("/") if p]
    if len(parts)!=2 or parts[0]!="sfzinstruments" or not re.fullmatch(r"[A-Za-z0-9_.-]+",parts[1]):
        raise ValueError("Publisher repository is not on the trusted curated allowlist")
    version=entry["version"]
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}",version):
        raise ValueError("Unrecognized pinned publisher version")
    return "https://raw.githubusercontent.com/"+parts[0]+"/"+parts[1]+"/v"+version+"/"

def relative_sample(reason:str)->PurePosixPath|None:
    if not reason.startswith(MISSING):return None
    supplied=reason[len(MISSING):].replace("\\","/").strip()
    # Resolve only the sample subtree, preserving the exact relative name.
    parts=supplied.split("/")
    try: index=next(i for i,p in enumerate(parts) if p.casefold()=="samples")
    except StopIteration:return None
    tail=parts[index:]
    if len(tail)<2 or len(tail)>12 or any(p in ("",".","..") for p in tail):
        return None
    path=PurePosixPath(*tail)
    if path.suffix.lower() not in MAGIC or len(str(path))>250:
        return None
    return path

def _validated_audio(path:Path)->bool:
    if not path.is_file() or not 8<=path.stat().st_size<=MAX_FILE_BYTES:
        return False
    with path.open("rb") as stream:header=stream.read(12)
    expected=MAGIC.get(path.suffix.lower())
    if header[:4]!=expected:return False
    if path.suffix.lower()==".wav" and header[8:12]!=b"WAVE":
        return False
    return True

def _local_candidate(root:Path, relative:PurePosixPath)->Path|None:
    # Match exact relative suffix, ignoring case; never guess from basename.
    wanted=tuple(part.casefold() for part in relative.parts)
    hits=[]
    for item in root.rglob("*"):
        if not item.is_file() or item.is_symlink() or item.suffix.lower() not in MAGIC:continue
        rel=item.relative_to(root)
        parts=tuple(part.casefold() for part in rel.parts)
        if len(parts)>=len(wanted) and parts[-len(wanted):]==wanted:
            if _validated_audio(item):hits.append(item)
        if len(hits)>1:return None
    return hits[0] if len(hits)==1 else None

def _download_exact(entry:dict, relative:PurePosixPath, target:Path)->bool:
    url=official_base(entry)+"/".join(quote(p,safe="") for p in relative.parts)
    req=urllib.request.Request(url,headers={"User-Agent":"Song-Harbor-SFZ-Repair/1","Accept":"audio/*,application/octet-stream"})
    opener=urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req,timeout=12) as response, target.open("xb") as output:
            if response.status!=200 or urlparse(response.url).hostname!="raw.githubusercontent.com":
                return False
            declared=response.headers.get("Content-Length","")
            if declared.isdigit() and int(declared)>MAX_FILE_BYTES:return False
            n=0
            while True:
                chunk=response.read(256*1024)
                if not chunk:break
                n+=len(chunk)
                if n>MAX_FILE_BYTES:raise ValueError("Publisher sample exceeds bounded repair size")
                output.write(chunk)
        return _validated_audio(target)
    except (OSError,urllib.error.URLError,TimeoutError):
        return False
    finally:
        if target.exists() and not _validated_audio(target):
            target.unlink()

def pack_digest(root:Path)->str:
    digest=hashlib.sha256()
    for file in sorted(p for p in root.rglob("*") if p.is_file() and p.name!="manifest.json"):
        digest.update(file.relative_to(root).as_posix().encode("utf-8"))
        h=hashlib.sha256()
        with file.open("rb") as handle:
            while block:=handle.read(1024*1024):h.update(block)
        digest.update(h.digest())
    return digest.hexdigest()

def repair(runtime:Path, pack_id:str)->dict:
    if not re.fullmatch(r"sfz-[a-f0-9]{16}",pack_id):
        raise ValueError("Invalid installed SFZ pack")
    root=(runtime/"instrument-packs"/pack_id).resolve()
    library=(runtime/"instrument-packs").resolve()
    if not root.is_dir() or root.parent!=library:
        raise ValueError("Installed SFZ pack not found")
    manifest_path=root/"manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("id")!=pack_id or manifest.get("engine")!="sfz":
        raise ValueError("Not a valid installed SFZ pack")
    entry=next((p for p in curated_sfz.CURATED_SFZ if p["id"]==manifest.get("curated_id")),None)
    if not entry:
        raise ValueError("Official repair requires a known curated publisher")
    official_base(entry)  # Validate trusted publisher before any staging.
    before,missing=sfz_pack.audit_pack(root)
    if not missing:
        return {"status":"complete","repaired":0,"playable":len(before),
                "unavailable_program_count":0,"attempted":0}
    attempted:set[str]=set()
    new_files:list[Path]=[]
    total=0
    local_count=0
    official_count=0
    try:
        # Each successful sample can expose the next missing dependency.
        for _ in range(MAX_REPAIRS):
            _,unavailable=sfz_pack.audit_pack(root)
            requested=None
            for problem in unavailable:
                rel=relative_sample(problem["reason"])
                if rel is not None and str(rel).casefold() not in attempted:
                    requested=rel
                    break
            if requested is None:break
            attempted.add(str(requested).casefold())
            destination=(root.joinpath(*requested.parts)).resolve()
            if not destination.is_relative_to(root) or destination.exists():
                continue
            source=_local_candidate(root,requested)
            destination.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="sh-repair-",dir=library) as tmp:
                staged=Path(tmp)/requested.name
                if source:
                    if source.stat().st_size>MAX_FILE_BYTES:continue
                    shutil.copyfile(source,staged)
                elif not _download_exact(entry,requested,staged):
                    continue
                if not _validated_audio(staged):continue
                total+=staged.stat().st_size
                if total>MAX_TOTAL_BYTES:break
                # Do not overwrite, even with concurrent or external changes.
                with staged.open("rb") as inp, destination.open("xb") as out:
                    shutil.copyfileobj(inp,out,256*1024)
                new_files.append(destination)
                if source:local_count+=1
                else:official_count+=1
        valid,remaining=sfz_pack.audit_pack(root)
        if not valid:
            raise ValueError("Repair could not make any SFZ program playable; nothing installed")
        # Publisher assets are fetched via versioned HTTPS. Without a pinned
        # per-file hash this is origin verification, NOT cryptographic identity.
        manifest["instruments"]=valid
        manifest["sha256"]=pack_digest(root)
        manifest["repair_provenance"]={
            "origin":"curated_publisher_version",
            "version":entry["version"],"local_files":local_count,
            "official_files":official_count,"integrity":"format_and_origin_checked_no_publisher_hash"}
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=root,suffix=".tmp",delete=False) as h:
            json.dump(manifest,h,indent=2)
            staged_manifest=Path(h.name)
        try:os.replace(staged_manifest,manifest_path)
        finally:staged_manifest.unlink(missing_ok=True)
        return {"status":"complete" if not remaining else "partial",
                "repaired":len(new_files),"from_local":local_count,
                "from_publisher":official_count,"attempted":len(attempted),
                "playable":len(valid),"unavailable_program_count":len(remaining),
                "unavailable_programs":remaining[:10]}
    except Exception:
        for path in reversed(new_files):path.unlink(missing_ok=True)
        raise
