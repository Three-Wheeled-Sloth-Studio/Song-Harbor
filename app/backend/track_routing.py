"""Persistent non-destructive stereo child routing for six original stems.

Store paths relative to a validated project export directory. Active child audio
replaces its parent; both never enter the same mix. Legacy six-stem projects work.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import projects

def valid_children(root:Path, project:dict[str,Any]) -> dict[str,dict[str,Any]]:
    result={}
    job=root/"jobs"/project["id"]
    for filename in project.get("files",[]):
        entry=project.get("channel_children",{}).get(filename)
        if not isinstance(entry,dict):continue
        export=entry.get("export")
        if not isinstance(export,str) or not export.startswith("Channels-") or "/" in export or "\\" in export:continue
        base=job/"exports"/export
        manifest=base/"manifest.json"
        try:
            payload=json.loads(manifest.read_text(encoding="utf-8"))
            if payload.get("source_project_id")!=project["id"]:continue
            tracks={t["channel"]:t for t in payload.get("tracks",[]) if t.get("source")==filename}
            if set(tracks)!={"left","right"}:continue
            paths={}
            for channel in ("left","right"):
                name=tracks[channel]["file"]
                if not isinstance(name,str) or Path(name).name!=name or not name.endswith(".wav"):raise ValueError()
                path=base/name
                if not path.is_file():raise ValueError()
                paths[channel]={"file":name,"url":f"/api/projects/{project['id']}/channels/stream/{filename}/{channel}"}
            result[filename]={"export":export,"active":bool(entry.get("active",False)),"tracks":paths}
        except (OSError,ValueError,KeyError,TypeError):
            continue
    return result

def attach(root:Path, project:dict[str,Any], folder:Path, filenames:list[str]) -> dict[str,Any]:
    if folder.parent != root/"jobs"/project["id"]/"exports" or not folder.name.startswith("Channels-"):
        raise ValueError("Invalid channel export")
    manifest=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    if manifest.get("source_project_id")!=project["id"]:raise ValueError("Channel export does not match song")
    available={t.get("source") for t in manifest.get("tracks",[])}
    if any(f not in available for f in filenames):raise ValueError("Missing channel outputs")
    config=project.setdefault("channel_children",{})
    for filename in filenames:
        config[filename]={"export":folder.name,"active":True}
    projects.write_project(root,project)
    return valid_children(root,project)

def switch(root:Path,project:dict[str,Any],filename:str,active:bool)->dict[str,Any]:
    if filename not in project.get("files",[]):raise ValueError("Unrecognized source stem")
    children=valid_children(root,project)
    if filename not in children:raise ValueError("Split this stem first")
    project["channel_children"][filename]["active"]=bool(active)
    projects.write_project(root,project)
    return valid_children(root,project)

def child_path(root:Path,project:dict[str,Any],filename:str,channel:str)->Path:
    if channel not in ("left","right"):raise ValueError("Invalid channel")
    children=valid_children(root,project)
    if filename not in children:raise ValueError("Derived channel unavailable")
    return root/"jobs"/project["id"]/"exports"/children[filename]["export"]/children[filename]["tracks"][channel]["file"]

def audio_inputs(root:Path,project:dict[str,Any],settings:list[Any])->list[tuple[Path,float,str,float]]:
    """Flatten exactly one audio source per original stem: stereo parent or two mono children."""
    children=valid_children(root,project)
    any_solo=any(x.solo for x in settings)
    output=[]
    positions={row.get("working_filename"):float(row.get("start_seconds",0))
               for row in project.get("source_tracks",[])}
    for x in settings:
        gain=0.0 if x.mute or (any_solo and not x.solo) else x.gain
        start=positions.get(x.filename,0.0)
        entry=children.get(x.filename)
        if entry and entry["active"]:
            for channel in ("left","right"):
                output.append((child_path(root,project,x.filename,channel),gain,channel,start))
        else:
            output.append((root/"jobs"/project["id"]/"stems"/x.filename,gain,"stereo",start))
    return output
