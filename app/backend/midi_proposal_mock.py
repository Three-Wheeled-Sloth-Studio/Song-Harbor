"""Deterministic offline mock provider for safely exercising MIDI review flows.

Never makes network calls. Only modifies note velocity for notes completely
inside selected song sections, and never touches vocals or source audio.
"""
from __future__ import annotations
import midi_arrangements

def propose(asset:dict,sections:list[dict],selected_ids:list[str],
            target_stem:str,velocity_delta:int=5)->dict:
    score=midi_arrangements.validate(asset)
    if type(velocity_delta) is not int or not -20<=velocity_delta<=20 or velocity_delta==0:
        raise ValueError("Mock velocity adjustment must be between -20 and 20, excluding zero")
    if not isinstance(selected_ids,list) or not 1<=len(selected_ids)<=64 or len(set(selected_ids))!=len(selected_ids):
        raise ValueError("Select 1 to 64 distinct song sections")
    lookup={row.get("id"):row for row in sections if isinstance(row,dict)}
    origin=score["source"]["start_sample"]
    ranges=[]
    for ident in selected_ids:
        row=lookup.get(ident)
        if row is None:raise ValueError("Unknown selected song section")
        lo=round(float(row["start_seconds"])*midi_arrangements.RATE)-origin
        hi=round(float(row["end_seconds"])*midi_arrangements.RATE)-origin
        if not 0<=lo<hi<=score["duration_samples"]:
            raise ValueError("Selected section outside saved MIDI arrangement")
        ranges.append((lo,hi))
    changes=[]
    for note in score["notes"]:
        if any(lo<=note["start_sample"] and note["end_sample"]<=hi for lo,hi in ranges):
            velocity=max(1,min(127,note["velocity"]+velocity_delta))
            if velocity!=note["velocity"]:
                changes.append({"op":"update","id":note["id"],"changes":{"velocity":velocity}})
        if len(changes)>=2000:raise ValueError("Mock proposal exceeds 2000 edits; select fewer sections")
    if not changes:raise ValueError("No eligible notes to adjust in selected sections")
    return {
        "schema_version":1,"base_revision":score["revision"],
        "source_track_id":score["source"]["track_id"],"target_stem":target_stem,
        "sections":[{"section_id":ident,"intent":"Mock velocity adjustment "+str(velocity_delta)}
                    for ident in selected_ids],
        "operations":changes,"instrument_sections":None,
    }
