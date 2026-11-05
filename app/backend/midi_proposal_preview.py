"""Read-only, provider-neutral validation of a proposed MIDI arrangement edit.

No models run here. It validates proposed edits against the current saved
revision and returns a human-readable diff without saving or rendering audio.
"""
from __future__ import annotations
import midi_arrangements
import section_instrument_selection

MAX_PROPOSALS=200
ALLOWED_PARTS={"bass","drums","guitar","piano","other"}


def preview(asset:dict, proposal:dict, sections:list[dict], catalogue:dict)->dict:
    score=midi_arrangements.validate(asset)
    if not isinstance(proposal,dict) or proposal.get("schema_version")!=1:
        raise ValueError("Unsupported MIDI proposal schema")
    if proposal.get("base_revision")!=score["revision"]:
        raise ValueError("Stale MIDI proposal revision")
    part=proposal.get("target_stem")
    if not isinstance(part,str) or part.casefold() not in ALLOWED_PARTS:
        raise ValueError("Proposal target must be Bass, Drums, Guitar, Piano or Other")
    if proposal.get("source_track_id")!=score["source"]["track_id"]:
        raise ValueError("Proposal source track differs from saved arrangement")
    changes=proposal.get("operations",[])
    if not isinstance(changes,list) or len(changes)>MAX_PROPOSALS:
        raise ValueError("Too many proposed MIDI operations")
    proposed_sections=proposal.get("sections",[])
    if not isinstance(proposed_sections,list) or not 1<=len(proposed_sections)<=8:
        raise ValueError("Proposal requires 1 to 8 selected sections")
    valid={s.get("id"):s for s in sections if isinstance(s,dict)}
    ids=[]
    for section in proposed_sections:
        if not isinstance(section,dict) or set(section)!={"section_id","intent"}:
            raise ValueError("Invalid section intent")
        ident=section["section_id"]
        intent=section["intent"]
        if not isinstance(ident,str) or ident not in valid or ident in ids:
            raise ValueError("Unknown or duplicate section in proposal")
        if not isinstance(intent,str) or len(intent)>250:
            raise ValueError("Invalid section intent")
        ids.append(ident)
    start=score["source"]["start_sample"]
    finish=start+score["duration_samples"]
    for ident in ids:
        section=valid[ident]
        lo=section.get("start_seconds")
        hi=section.get("end_seconds")
        if not isinstance(lo,(int,float)) or not isinstance(hi,(int,float)) or (
            round(lo*midi_arrangements.RATE)<start or round(hi*midi_arrangements.RATE)>finish
        ):
            raise ValueError("Proposed section lies outside MIDI arrangement")
    if not changes and proposal.get("instrument_sections") is None:
        raise ValueError("Proposal contains no edits")
    # Note validation, including IDs/bounds/velocity, is delegated to the
    # existing atomic transaction, with an in-memory result only.
    proposed_recipe=proposal.get("instrument_sections")
    if proposed_recipe is not None:
        saved=section_instrument_selection.validate_recipe(proposed_recipe)
        if set(saved["section_ids"])!=set(ids):
            raise ValueError("Proposal preset scope differs from its selected sections")
        section_instrument_selection.resolve_recipe(saved,ids,catalogue)
    changed=midi_arrangements.apply_patch(
        score,score["revision"],changes,
        instrument_sections=proposed_recipe,
        update_instrument_sections=proposed_recipe is not None)
    before={row["id"]:row for row in score["notes"]}
    after={row["id"]:row for row in changed["notes"]}
    added=[after[k] for k in after.keys()-before.keys()]
    removed=[before[k] for k in before.keys()-after.keys()]
    edited=[{"before":before[k],"after":after[k]} for k in before.keys()&after.keys()
            if before[k]!=after[k]]
    return {
        "status":"review_only","asset_id":score["asset_id"],"base_revision":score["revision"],
        "target_stem":part.casefold(),"selected_sections":ids,
        "note_diff":{"added":added,"removed":removed,"changed":edited},
        "instrument_before":score.get("instrument_sections"),
        "instrument_after":changed.get("instrument_sections"),
        "proposed_revision":changed["revision"],
        "note_count_before":len(score["notes"]), "note_count_after":len(changed["notes"]),
        "mutated":False,
        "message":"Preview only. No MIDI arrangement, audio, or source stem was changed."
    }
