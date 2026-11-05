"""Deterministic library-grounded instrument proposal, not a generative LLM.

Converts explicit installed instrument names and section qualifiers into a
review-only MIDI preset recipe. The rest of the user's musical direction is
retained as text, not falsely presented as completed note edits.
"""
from __future__ import annotations
import instrument_direction_match
import section_instrument_selection


def propose(asset:dict, sections:list[dict], selected_ids:list[str],
            target_stem:str, instruction:str, catalogue:dict)->tuple[dict,dict]:
    if not isinstance(selected_ids,list) or not 1<=len(selected_ids)<=64 or len(set(selected_ids))!=len(selected_ids):
        raise ValueError("Select 1 to 64 unique song sections")
    by_id={row.get("id"):row for row in sections if isinstance(row,dict)}
    if any(section_id not in by_id for section_id in selected_ids):
        raise ValueError("Selected song section no longer exists")
    match=instrument_direction_match.resolve(instruction,catalogue)
    if match["status"]!="matched":
        raise ValueError("Instrument mapping is unresolved; inspect the mapping icon for details")
    matches=match.get("assignments",[])
    defaults=[item for item in matches if item.get("section")=="default"]
    if len(defaults)!=1:
        raise ValueError("Specify one installed default instrument variant")
    default=defaults[0]
    overrides={}
    for entry in matches:
        if entry.get("section")=="default":continue
        scope=entry["section"].replace("_","").casefold()
        hits=[section_id for section_id in selected_ids
              if "".join(ch for ch in str(by_id[section_id].get("kind","")).casefold() if ch.isalnum())==scope]
        if not hits:raise ValueError("No selected sections match "+str(entry["section"]))
        for section_id in hits:
            chosen=(entry["pack_id"],entry["instrument_id"])
            if section_id in overrides and overrides[section_id]!=chosen:
                raise ValueError("Conflicting presets assigned to section "+section_id)
            overrides[section_id]=chosen
    recipe=section_instrument_selection.validate_recipe({
        "schema_version":1,"section_ids":selected_ids,
        "default":{"pack_id":default["pack_id"],"instrument_id":default["instrument_id"]},
        "overrides":[{"section_id":section_id,"pack_id":pack,"instrument_id":instrument}
                     for section_id,(pack,instrument) in overrides.items()]
    })
    section_instrument_selection.resolve_recipe(recipe,selected_ids,catalogue)
    return {
        "schema_version":1,"base_revision":asset["revision"],
        "source_track_id":asset["source"]["track_id"],"target_stem":target_stem,
        "sections":[{"section_id":section_id,"intent":"Instrument preset selection"}
                    for section_id in selected_ids],
        "operations":[],"instrument_sections":recipe
    },match
