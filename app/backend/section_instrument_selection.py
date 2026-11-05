"""Validate explicit per-section instrument choices without modifying MIDI scores.

The renderer consumes this selection before generating independent section
previews. Existing section-composition then produces one stem for the part.
"""
from __future__ import annotations

MAX_SECTIONS = 8


def resolve(selected_ids: list[str], assignments: list[dict], default_pack: str,
            default_instrument: str, catalogue: dict) -> dict[str,dict]:
    if not isinstance(selected_ids,list) or not 1<=len(selected_ids)<=MAX_SECTIONS or (
        any(not isinstance(x,str) or not x for x in selected_ids)
        or len(set(selected_ids))!=len(selected_ids)
    ):
        raise ValueError("Choose 1 to 8 unique song sections")
    if not isinstance(assignments,list) or len(assignments)>MAX_SECTIONS:
        raise ValueError("Too many section instrument overrides")
    available={(row.get("pack_id"),row.get("id")):row for row in catalogue.get("instruments",[])
               if isinstance(row,dict) and row.get("engine") in ("sf2","sfz")}
    if (default_pack,default_instrument) not in available:
        raise ValueError("Default instrument must be an installed SF2 or SFZ preset")
    choices={section:{"pack_id":default_pack,"instrument_id":default_instrument} for section in selected_ids}
    seen=set()
    for assignment in assignments:
        if not isinstance(assignment,dict):
            raise ValueError("Invalid section preset override")
        section=assignment.get("section_id")
        if section not in choices or section in seen:
            raise ValueError("Section preset override is duplicated or outside the selection")
        seen.add(section)
        pack=assignment.get("pack_id")
        instrument=assignment.get("instrument_id")
        if (pack,instrument) not in available:
            raise ValueError("Section preset override is not installed")
        choices[section]={"pack_id":pack,"instrument_id":instrument}
    return choices
