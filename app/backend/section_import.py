"""Section import/export adapters; all imports are validated before persistence.

Readable Song Harbor section tags are independent of generation-engine prompts.
Spatial annotations are stored as nonexecuting proposals keyed to section IDs.
"""
from __future__ import annotations
import json
from typing import Any
import sections
import production_cues

def parse(content:str)->list[dict[str,Any]]:
    stripped=content.strip()
    if not stripped:raise ValueError("No sections supplied")
    if stripped.startswith("{") or stripped.startswith("[{"):
        try:data=json.loads(stripped)
        except json.JSONDecodeError as exc:raise ValueError("Invalid JSON") from exc
        entries=data.get("sections") if isinstance(data,dict) else data
        if not isinstance(entries,list):raise ValueError("Expected a sections array")
        result=[]
        for entry in entries:
            if not isinstance(entry,dict):raise ValueError("Each section must be an object")
            result.append({key:entry[key] for key in (
                "id","kind","number","start_seconds","end_seconds","spatial")
                if key in entry})
        return result
    result=[]
    for index,line in enumerate(content.splitlines(),1):
        line=line.strip()
        if not line or line.startswith("#"):continue
        try:cue=production_cues.parse_cue(line)
        except ValueError as exc:raise ValueError(f"Line {index}: {exc}") from exc
        result.append({**cue["section"],"spatial":cue["spatial"]})
    if not result:raise ValueError("No timed sections found")
    return result

def validate_spatial(raw:Any)->list[dict[str,str]]:
    if not isinstance(raw,list) or len(raw)>64:
        raise ValueError("Spatial directives must be a list with at most 64 entries")
    clean=[]
    used=set()
    for item in raw:
        if not isinstance(item,dict):raise ValueError("Invalid spatial directive")
        alias=item.get("track_alias")
        width=item.get("width")
        bias=item.get("bias","center")
        if not isinstance(alias,str) or not production_cues.NAME.fullmatch(alias) or alias in used:
            raise ValueError("Invalid or duplicate track alias")
        if width not in {x.lower() for x in production_cues.WIDTHS}:
            raise ValueError("Invalid width")
        if bias not in {x.lower() for x in production_cues.BIASES}:
            raise ValueError("Invalid bias")
        used.add(alias)
        clean.append({"track_alias":alias,"width":width,"bias":bias})
    return clean

def apply(project:dict[str,Any],content:str,mode:str,duration:float|None)->dict[str,Any]:
    if mode not in ("replace","append"):raise ValueError("Mode must be replace or append")
    imported=parse(content)
    old=project.get("sections",[])
    combined=(old if mode=="append" else [])+imported
    validated=sections.validate_sections(combined,duration=duration)
    old_proposals=project.get("section_spatial_proposals",{})
    proposals={x["id"]:old_proposals[x["id"]] for x in validated
               if x["id"] in old_proposals and any(y.get("id")==x["id"] for y in old)}
    for item in imported:
        if "spatial" not in item:continue
        spatial=validate_spatial(item["spatial"])
        match=next((s for s in validated if
            s["kind"]==item.get("kind") and s["number"]==item.get("number")
            and s["start_seconds"]==round(float(item["start_seconds"]),3)
            and s["end_seconds"]==round(float(item["end_seconds"]),3)),None)
        if match is None:raise ValueError("Unable to match imported spatial annotation")
        proposals[match["id"]]=spatial
    return {"sections":validated,"section_spatial_proposals":proposals,
            "imported_count":len(imported)}

def render_tags(project:dict[str,Any])->str:
    cues=project.get("section_spatial_proposals",{})
    lines=[]
    for entry in project.get("sections",[]):
        head=sections.display_tag(entry)[:-1]
        edits=cues.get(entry["id"],[])
        for item in edits:
            head+=" "+item["track_alias"]+":"+item["width"].capitalize()
            if item["bias"]!="center":head+="-"+item["bias"].capitalize()
        lines.append(head+"]")
    return "\n".join(lines)
