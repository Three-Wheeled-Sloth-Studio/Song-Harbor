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


def validate_recipe(recipe: dict) -> dict:
    """Canonical durable preset recipe; library availability is checked on render.

    The recipe stores exact installed identifiers, but does not pin a mutable
    timeline. The renderer verifies selected section IDs still exist.
    """
    if not isinstance(recipe,dict) or recipe.get("schema_version")!=1:
        raise ValueError("Invalid section instrument recipe")
    default=recipe.get("default")
    if not isinstance(default,dict):
        raise ValueError("Missing default instrument")
    def reference(row:dict)->dict:
        if not isinstance(row,dict):
            raise ValueError("Invalid instrument reference")
        pack=row.get("pack_id")
        instrument=row.get("instrument_id")
        if not isinstance(pack,str) or not 1<=len(pack)<=80 or not isinstance(instrument,str) or not 1<=len(instrument)<=120:
            raise ValueError("Invalid installed instrument identifiers")
        return {"pack_id":pack,"instrument_id":instrument}
    base=reference(default)
    overrides=recipe.get("overrides",[])
    if not isinstance(overrides,list) or len(overrides)>MAX_SECTIONS:
        raise ValueError("Too many saved instrument overrides")
    seen=set()
    rows=[]
    for override in overrides:
        if not isinstance(override,dict):
            raise ValueError("Invalid instrument override")
        ident=override.get("section_id")
        if not isinstance(ident,str) or not 1<=len(ident)<=100 or ident in seen:
            raise ValueError("Duplicate or invalid song section identifier")
        seen.add(ident)
        rows.append({"section_id":ident,**reference(override)})
    return {"schema_version":1,"default":base,
            "overrides":sorted(rows,key=lambda row:row["section_id"])}


def resolve_recipe(recipe:dict,selected_ids:list[str],catalogue:dict)->dict[str,dict]:
    """Use only saved, installed presets; reject selected timeline drift."""
    saved=validate_recipe(recipe)
    overrides=[row for row in saved["overrides"] if row["section_id"] in selected_ids]
    return resolve(selected_ids,overrides,saved["default"]["pack_id"],
                   saved["default"]["instrument_id"],catalogue)
