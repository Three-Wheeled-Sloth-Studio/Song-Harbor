"""Import externally prepared tracks into an aligned Song Harbor project.

Original audio is retained; working WAVs are rendered to one common duration.
"""
from __future__ import annotations

import re
import json
from pathlib import Path

ROLES=("Vocals","Drums","Bass","Guitar","Piano","Other")
ROLE_WORDS={
    "Vocals":("vocals","vocal","vox","voice","lead vocal","backing vocal","bgv"),
    "Drums":("drums","drum","percussion","perc","beats"),
    "Bass":("bass",),
    "Guitar":("guitar","guitars","gtr"),
    "Piano":("piano","keys","keyboard"),
    "Other":("other","instrumental","instruments","music"),
}
TRAILING=re.compile(r"(?i)(?:[\s._-]*(?:stem|track|take|mix|audio)[\s._-]*\d*)+$")
SPLIT=re.compile(r"[\s._-]+")


def infer_role(filename:str)->str|None:
    stem=Path(filename).stem.lower()
    # Demucs/Song Harbor names often use "(Vocals)_htdemucs_6s.wav".
    # Match role words as independent terms, never substrings of song titles
    # (e.g. "Guitarist" should not be silently classified Guitar).
    for role,aliases in ROLE_WORDS.items():
        for alias in aliases:
            if re.search(r"(?<![a-z0-9])"+re.escape(alias)+r"(?![a-z0-9])",stem):
                return role
    return None


def guess_song_title(filenames:list[str])->str:
    """Common descriptive prefix with stem role suffix removed; safe fallback."""
    if not filenames:return "Imported song"
    names=[]
    for filename in filenames:
        stem=Path(filename).stem
        # Drop recognizable terminal stem label with optional separator and index.
        stem=re.sub(r"(?i)[\s._-]*\(?"
            r"(vocals?|vox|voice|drums?|percussion|perc|beats|bass|guitars?|gtr|piano|keys|keyboard|other|instrumental|instruments|music)"
            r"\)?(?:[\s._-]*\d{1,2})?$","",stem).strip(" ._-")
        names.append(stem)
    tokens=[list(filter(None,SPLIT.split(name))) for name in names]
    prefix=[]
    for parts in zip(*tokens):
        if len({word.casefold() for word in parts})!=1:break
        prefix.append(parts[0])
    title=" ".join(prefix).strip(" ._-")
    if not title and len(names)==1:title=names[0]
    return title[:120] or "Imported song"


def assign_tracks(filenames:list[str])->list[dict[str,str]]:
    """Recognize at most one of each canonical stem, preserve extras distinctly."""
    used:set[str]=set()
    result=[]
    for filename in filenames:
        role=infer_role(filename)
        if not role or role in used:
            next_index=1
            while f"Track{next_index:02d}" in used:next_index+=1
            role=f"Track{next_index:02d}"
        used.add(role)
        result.append({"original_filename":filename,"stem_alias":role})
    return result

MAX_TRACKS=64
MAX_UPLOADS=128
MANIFEST_FORMAT="song-harbor-stereo-channel-split"


def channel_groups(manifest_bytes:bytes, uploaded_names:list[str])->list[dict[str,str]]:
    """Validate the exported split manifest against the actual uploaded mono files.

    Never trust original project IDs or manifest paths. Track pairs are grouped
    by source identity and each source has exactly one L and one R channel.
    """
    if len(manifest_bytes)>256*1024:raise ValueError("Channel manifest exceeds 256 KiB")
    try:
        payload=json.loads(manifest_bytes.decode("utf-8"))
    except (ValueError,UnicodeDecodeError) as exc:
        raise ValueError("Invalid JSON channel manifest") from exc
    if not isinstance(payload,dict) or payload.get("format")!=MANIFEST_FORMAT or payload.get("version")!=1:
        raise ValueError("Expected Song Harbor stereo-channel-split manifest v1")
    tracks=payload.get("tracks")
    if not isinstance(tracks,list) or not 2<=len(tracks)<=MAX_UPLOADS:
        raise ValueError("Manifest must list 2-128 channel files")
    if payload.get("track_count")!=len(tracks):
        raise ValueError("Channel manifest track count mismatch")
    uploaded=set(uploaded_names)
    if len(uploaded)!=len(uploaded_names):raise ValueError("Duplicate uploaded filenames")
    groups:dict[str,dict[str,str]]={}
    used=set()
    for item in tracks:
        if not isinstance(item,dict):raise ValueError("Invalid manifest track")
        filename=item.get("file")
        source=item.get("source")
        channel=item.get("channel")
        if (not isinstance(filename,str) or not isinstance(source,str)
            or not filename or Path(filename).name!=filename
            or not source or len(source)>200 or channel not in ("left","right")
            or filename not in uploaded or filename in used):
            raise ValueError("Manifest contains missing, duplicate or unsafe channel file")
        used.add(filename)
        item_group=groups.setdefault(source,{})
        if channel in item_group:raise ValueError("Repeated channel in manifest")
        item_group[channel]=filename
    if used!=uploaded:raise ValueError("Selected files do not exactly match the channel manifest")
    if any(set(group)!={"left","right"} for group in groups.values()):
        raise ValueError("Each source must have a Left and Right channel")
    if len(groups)>MAX_TRACKS:raise ValueError("Maximum 64 grouped stems")
    return [{"source":source,"left":pair["left"],"right":pair["right"]}
            for source,pair in groups.items()]


def identity_tracks(filenames:list[str],title:str|None=None)->list[dict[str,str]]:
    """Stable IDs and unique script-safe aliases, derived from source names.

    A future UI rename may change display_name and update section tokens,
    but it must never mutate track_id or working WAV filename.
    """
    if len(filenames)>MAX_TRACKS:raise ValueError("Maximum 64 stems")
    prefix=(title or guess_song_title(filenames)).strip()
    used:set[str]=set()
    items=[]
    for index,item in enumerate(assign_tracks(filenames),start=1):
        alias=item["stem_alias"]
        if alias.startswith("Track") and alias[5:].isdigit():
            raw=Path(item["original_filename"]).stem
            if prefix and raw.casefold().startswith(prefix.casefold()):
                raw=raw[len(prefix):].strip(" ._-")
            # Remove common separators, numbers, and reserved effects punctuation.
            candidate=re.sub(r"[^A-Za-z0-9_-]","_",raw).strip("_-")[:32]
            if candidate and candidate[0].isalpha() and candidate.lower() not in (
                    "all","master","reset") and not candidate.lower().startswith("track0"):
                alias=candidate
        base=alias
        suffix=2
        while alias.casefold() in used:
            alias=f"{base[:26]}_{suffix}"
            suffix+=1
        used.add(alias.casefold())
        item["stem_alias"]=alias
        item["track_id"]=f"trk{index:04d}"
        item["display_name"]=Path(item["original_filename"]).stem
        items.append(item)
    return items
