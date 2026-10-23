"""Persistent editable track aliases, independent from immutable WAV identity."""
from __future__ import annotations
import copy
import re
import uuid
from pathlib import Path
from typing import Any

import section_import
import section_production

ALIAS=re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
RESERVED={"all","auto","master","reset","end"}

def ensure_identities(project:dict[str,Any])->list[dict[str,Any]]:
    """Preserve existing source IDs; introduce stable IDs for older separated songs."""
    files=project.get("files",[])
    records=copy.deepcopy(project.get("source_tracks",[]))
    seen_files={r.get("working_filename") for r in records}
    seen_ids={r.get("track_id") for r in records}
    for filename in files:
        if filename in seen_files:continue
        alias=section_production.source_aliases([filename])
        if not alias:raise ValueError(f"Missing script-safe stem label in {filename}")
        track_id="trk_"+uuid.uuid4().hex[:16]
        while track_id in seen_ids:track_id="trk_"+uuid.uuid4().hex[:16]
        records.append({"track_id":track_id,"working_filename":filename,
                        "original_filename":filename,"stem_alias":alias[0],
                        "display_name":alias[0]})
        seen_ids.add(track_id)
    if {r.get("working_filename") for r in records}!=set(files):
        raise ValueError("Source-track mapping inconsistent with saved audio files")
    return records

def rename(project:dict[str,Any],track_id:str,alias:str,
           display_name:str)->dict[str,Any]:
    if not ALIAS.fullmatch(alias) or alias.casefold() in RESERVED:
        raise ValueError("Use a script alias of 1-32 letters, numbers, underscores or hyphens, starting with a letter; reserved names are disallowed")
    if not display_name.strip() or len(display_name.strip())>100:
        raise ValueError("Display name must be 1-100 characters")
    updated=copy.deepcopy(project)
    rows=ensure_identities(updated)
    match=next((r for r in rows if r["track_id"]==track_id),None)
    if match is None:raise ValueError("Unknown permanent track ID")
    if any(r["track_id"]!=track_id and r["stem_alias"].casefold()==alias.casefold()
           for r in rows):
        raise ValueError("Alias already belongs to another track")
    old=match["stem_alias"]
    match["stem_alias"]=alias
    match["display_name"]=display_name.strip()
    updated["source_tracks"]=rows
    if old!=alias:
        for directives in updated.get("section_production",{}).values():
            for instruction in directives:
                if instruction.get("track","").casefold()==old.casefold():
                    instruction["track"]=alias
        for proposals in updated.get("section_spatial_proposals",{}).values():
            for instruction in proposals:
                if instruction.get("track_alias","").casefold()==old.casefold():
                    instruction["track_alias"]=alias
    # Reuse exactly the same parser and materializer as a user-edited section
    # sheet, so every stored automation is recomputed with the same immutable
    # source_key, and broken references reject the whole transaction.
    if updated.get("sections"):
        rendered=section_import.render_tags(updated)
        changed=section_import.apply(updated,rendered,"replace",
                       updated.get("source_duration_seconds"))
        for key in ("sections","section_production","section_lyrics",
                    "section_spatial_proposals","section_pan_automation",
                    "section_reverb_automation","section_width_automation",
                    "section_space_automation","section_eq_automation",
                    "section_dynamics_automation","section_gain_automation",
                    "section_auto_pan","section_ending"):
            updated[key]=changed[key]
    return updated
