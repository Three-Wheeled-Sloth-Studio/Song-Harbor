"""Pure, revision-stable section slices of saved MIDI arrangements.

Each section becomes an independent candidate region. This deliberately prevents
non-contiguous selected sections from being represented by one continuous audio
replacement mask, which would silence unselected passages.
"""
from __future__ import annotations
import copy
import math
import midi_arrangements

RATE=midi_arrangements.RATE
MAX_SELECTED_SECTIONS=8
MAX_TOTAL_SECONDS=600


def select_sections(asset:dict, sections:list[dict], selected_ids:list[str])->list[dict]:
    score=midi_arrangements.validate(asset)
    if not 1<=len(selected_ids)<=MAX_SELECTED_SECTIONS or len(set(selected_ids))!=len(selected_ids):
        raise ValueError("Select 1 to 8 distinct sections")
    by_id={section.get("id"):section for section in sections if isinstance(section,dict)}
    if len(by_id)!=len(sections):
        raise ValueError("Timeline contains duplicate section IDs")
    start=score["source"]["start_sample"]
    duration=score["duration_samples"]
    spans=[]
    total=0
    for ident in selected_ids:
        section=by_id.get(ident)
        if section is None:
            raise ValueError("Selected section no longer exists")
        lo=section.get("start_seconds")
        hi=section.get("end_seconds")
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (lo,hi)):
            raise ValueError("Section has invalid timestamps")
        a=round(lo*RATE)-start
        b=round(hi*RATE)-start
        if a<0 or b>duration or b-a<round(.1*RATE) or b-a>600*RATE:
            raise ValueError("Selected section falls outside the saved MIDI arrangement")
        spans.append((a,b,ident))
        total+=b-a
    if total>MAX_TOTAL_SECONDS*RATE:
        raise ValueError("Selected section renders exceed 10 minutes total")
    spans.sort()
    if any(spans[i][0]<spans[i-1][1] for i in range(1,len(spans))):
        raise ValueError("Selected sections overlap; avoid double source replacement")
    result=[]
    for a,b,ident in spans:
        segment=copy.deepcopy(score)
        segment["source"]["start_sample"]=start+a
        segment["duration_samples"]=b-a
        segment["notes"]=[]
        for note in score["notes"]:
            clipped_start=max(a,note["start_sample"])
            clipped_end=min(b,note["end_sample"])
            if clipped_end<=clipped_start:
                continue
            segment["notes"].append({**note,"start_sample":clipped_start-a,"end_sample":clipped_end-a})
        result.append({"section_id":ident,"start_seconds":(start+a)/RATE,
                       "duration_seconds":(b-a)/RATE,"arrangement":midi_arrangements.validate(segment)})
    return result
