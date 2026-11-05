"""Persistent, versioned MIDI arrangements independent of audio candidate renders.

Pure Python, no model/runtime dependencies. Notes have stable IDs and sample-grid
positions; patches are deterministic and revision guarded for human/LLM editing.
Original stems are never written by this module.
"""
from __future__ import annotations
import copy
import json
import math
import os
import re
import uuid
from pathlib import Path
import drum_keymaps

SCHEMA_VERSION=1
MAX_NOTES=20000
MAX_OPERATIONS=2000
MAX_DURATION_S=3600
ID_RE=re.compile(r"^[a-f0-9]{32}$")
RATE=48000

def _identifier(value: str)->str:
    if not isinstance(value,str) or not ID_RE.fullmatch(value):
        raise ValueError("Invalid arrangement/note identifier")
    return value

def _integer(value: object, name: str, minimum:int, maximum:int)->int:
    if type(value) is not int or not minimum<=value<=maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
    return value

def _note(row:dict, length:int)->dict:
    if not isinstance(row,dict):raise ValueError("Note must be an object")
    ident=_identifier(row["id"])
    start=_integer(row["start_sample"],"start_sample",0,length)
    end=_integer(row["end_sample"],"end_sample",0,length)
    if end<=start:raise ValueError("Note end must follow start")
    return {"id":ident,"start_sample":start,"end_sample":end,
            "pitch":_integer(row["pitch"],"pitch",0,127),
            "velocity":_integer(row["velocity"],"velocity",1,127),
            "channel":_integer(row.get("channel",0),"channel",0,15)}

def validate(asset:dict)->dict:
    if not isinstance(asset,dict) or asset.get("schema_version")!=SCHEMA_VERSION:
        raise ValueError("Unsupported MIDI asset schema")
    _identifier(asset.get("asset_id"))
    _integer(asset.get("revision"),"revision",0,1000000)
    duration=_integer(asset.get("duration_samples"),"duration_samples",1,RATE*MAX_DURATION_S)
    if asset.get("sample_rate")!=RATE:raise ValueError("Unsupported arrangement sample rate")
    source=asset.get("source")
    if not isinstance(source,dict):raise ValueError("Missing provenance")
    if not isinstance(source.get("track_id"),str) or not source["track_id"] or len(source["track_id"])>100:
        raise ValueError("Invalid source track")
    _integer(source.get("start_sample"),"source start",0,RATE*MAX_DURATION_S)
    if len(str(source.get("method","")))>180:raise ValueError("Source method too long")
    rows=asset.get("notes")
    if not isinstance(rows,list) or len(rows)>MAX_NOTES:raise ValueError("Too many notes")
    notes=[_note(n,duration) for n in rows]
    if len({n["id"] for n in notes})!=len(notes):raise ValueError("Duplicate note IDs")
    clean=copy.deepcopy(asset)
    percussion=clean.get("percussion")
    if percussion is not None:
        if not isinstance(percussion,dict) or percussion.get("mode")!="drums":
            raise ValueError("Invalid percussion arrangement metadata")
        keymap=drum_keymaps.validate_keymap(percussion.get("keymap"))
        if any(n["channel"]!=9 for n in notes):
            raise ValueError("Drum arrangement requires MIDI channel 10")
        missing={n["pitch"] for n in notes}-{lane["pitch"] for lane in keymap["lanes"]}
        if missing:raise ValueError("Unmapped drum pitches: "+", ".join(map(str,sorted(missing))))
        clean["percussion"]={"mode":"drums","keymap":keymap}
    clean["notes"]=sorted(notes,key=lambda n:(n["start_sample"],n["pitch"],n["id"]))
    return clean

def create(track_id:str,start_seconds:float,duration_seconds:float,notes:list[dict],method:str="manual")->dict:
    if not isinstance(track_id,str) or not 0<len(track_id)<=100:raise ValueError("Invalid track ID")
    if not all(isinstance(x,(float,int)) and math.isfinite(x) for x in (start_seconds,duration_seconds)):
        raise ValueError("Invalid duration")
    if start_seconds<0 or duration_seconds<=0 or start_seconds+duration_seconds>MAX_DURATION_S:
        raise ValueError("Arrangement region exceeds bounds")
    length=round(duration_seconds*RATE)
    rows=[]
    for raw in notes:
        if not isinstance(raw,dict):raise ValueError("Invalid note")
        start=round(float(raw["start"])*RATE)
        end=round(float(raw["end"])*RATE)
        rows.append({"id":uuid.uuid4().hex,"start_sample":start,"end_sample":end,
                     "pitch":raw["pitch"],"velocity":raw.get("velocity",85),"channel":0})
    asset={"schema_version":SCHEMA_VERSION,"asset_id":uuid.uuid4().hex,
           "revision":0,"sample_rate":RATE,"duration_samples":length,
           "source":{"track_id":track_id,"start_sample":round(start_seconds*RATE),"method":method},
           "notes":rows}
    return validate(asset)

def apply_patch(asset:dict,base_revision:int,operations:list[dict],percussion:dict|None=None,*,update_percussion:bool=False)->dict:
    """Atomic edit transaction. Operations: add, update, remove.

    Update explicitly supplies a patch of note fields. No silent moving of
    other notes; polyphony is permitted. Caller must audition accepted edits.
    """
    current=validate(asset)
    if base_revision!=current["revision"]:raise ValueError("Stale MIDI revision")
    if not isinstance(operations,list) or len(operations)>MAX_OPERATIONS or (not operations and not update_percussion):
        raise ValueError("Invalid MIDI edit transaction")
    notes={n["id"]:n for n in current["notes"]}
    for op in operations:
        if not isinstance(op,dict) or op.get("op") not in ("add","update","remove"):
            raise ValueError("Unknown MIDI operation")
        kind=op["op"]
        if kind=="add":
            raw=op.get("note")
            if not isinstance(raw,dict):raise ValueError("Missing note")
            note=_note(raw,current["duration_samples"])
            if note["id"] in notes:raise ValueError("Duplicate note ID")
            notes[note["id"]]=note
        else:
            ident=_identifier(op.get("id"))
            if ident not in notes:raise ValueError("Note not found")
            if kind=="remove":del notes[ident]
            else:
                changes=op.get("changes")
                allowed={"start_sample","end_sample","pitch","velocity","channel"}
                if not isinstance(changes,dict) or not changes or set(changes)-allowed:
                    raise ValueError("Invalid MIDI note changes")
                notes[ident]=_note({**notes[ident],**changes},current["duration_samples"])
    current["notes"]=list(notes.values())
    if update_percussion:
        if percussion is None:current.pop("percussion",None)
        else:current["percussion"]=percussion
    current["revision"]+=1
    return validate(current)

def asset_path(job_root:Path,asset_id:str)->Path:
    return job_root/"generated"/"midi-arrangements"/(_identifier(asset_id)+".json")

def read(job_root:Path,asset_id:str)->dict:
    return validate(json.loads(asset_path(job_root,asset_id).read_text(encoding="utf-8")))

def save(job_root:Path,asset:dict)->Path:
    clean=validate(asset)
    target=asset_path(job_root,clean["asset_id"])
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+"."+uuid.uuid4().hex+".tmp")
    try:
        with temp.open("x",encoding="utf-8") as output:
            json.dump(clean,output,indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp,target)
    finally:temp.unlink(missing_ok=True)
    return target

def list_assets(job_root:Path)->list[dict]:
    folder=job_root/"generated"/"midi-arrangements"
    if not folder.is_dir():return []
    items=[]
    for path in sorted(folder.glob("*.json")):
        try:
            item=validate(json.loads(path.read_text(encoding="utf-8")))
            items.append({"asset_id":item["asset_id"],"revision":item["revision"],
                          "source":item["source"],"note_count":len(item["notes"]),
                          "duration_samples":item["duration_samples"],
                          "percussion":item.get("percussion")})
        except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError):continue
    return items
