"""Grounded instrument-family and variant matching for future LLM arrangement plans.

This module never calls a model, downloads packs, or interprets arbitrary
creative directions. It only resolves explicit references against the installed
catalogue, retaining any unmatched text for downstream musical interpretation.
"""
from __future__ import annotations
import re

MAX_INSTRUCTION = 3000
MAX_INSTRUMENTS = 4096
WORD = re.compile(r"[a-z0-9]+")
SECTION_TOKENS = {
    "chorus": ("chorus", "choruses"),
    "bridge": ("bridge", "bridges"),
    "verse": ("verse", "verses"),
    "intro": ("intro", "intros"),
    "outro": ("outro", "outros"),
    "pre_chorus": ("prechorus", "prechoruses", "pre chorus", "pre choruses"),
}
IGNORED_NAME_WORDS = {"karoryfer", "samples", "sample", "instrument", "instruments", "sfz", "sf2"}


def words(value: str) -> list[str]:
    return WORD.findall(value.casefold())


def names(value: str) -> set[str]:
    tokens=words(value)
    return {"".join(tokens), " ".join(tokens)} if tokens else set()


def _mentions(text: str, needle: str) -> bool:
    target=words(needle)
    if not target:return False
    source=words(text)
    size=len(target)
    return any(source[i:i+size]==target for i in range(len(source)-size+1)) or (
        len(target)>1 and "".join(target) in source
    )


def _variants(instrument: dict, family: str) -> set[str]:
    labels=[str(instrument.get("id","")),str(instrument.get("name",""))]
    variants=set()
    for label in labels:
        tokens=words(label)
        fam=words(family)
        if not tokens:continue
        if fam and tokens[:len(fam)]==fam:tokens=tokens[len(fam):]
        elif fam and tokens and tokens[0]=="".join(fam):tokens=tokens[1:]
        tokens=[token for token in tokens if token not in IGNORED_NAME_WORDS and not token.isdigit()]
        if tokens:variants.add(" ".join(tokens))
    return variants


def resolve(instruction: str, catalogue: dict) -> dict:
    """Produce a reviewable resolution trace without guessing nonexistent IDs."""
    if not isinstance(instruction,str) or not 1<=len(instruction)<=MAX_INSTRUCTION:
        raise ValueError("Musical instruction must be 1 to 3000 characters")
    if not isinstance(catalogue,dict):
        raise ValueError("Instrument catalogue is missing")
    packs=catalogue.get("packs",[])
    instruments=catalogue.get("instruments",[])
    if not isinstance(packs,list) or not isinstance(instruments,list) or len(instruments)>MAX_INSTRUMENTS:
        raise ValueError("Invalid instrument catalogue")
    family_candidates=[]
    for pack in packs:
        if not isinstance(pack,dict):continue
        pack_id=pack.get("id")
        if not isinstance(pack_id,str):continue
        display=str(pack.get("name",""))
        family_aliases=[str(pack.get("curated_id") or ""),pack_id,display]
        family_aliases += [w for w in words(display) if w not in IGNORED_NAME_WORDS and len(w)>=5]
        matching=[alias for alias in family_aliases if alias and _mentions(instruction,alias)]
        if matching:
            family_candidates.append((pack_id,display,max(matching,key=len)))
    # Do not let broad aliases silently choose among two library packs.
    if len({x[0] for x in family_candidates})!=1:
        return {"status":"ambiguous" if family_candidates else "no_family_match",
                "families":[{"pack_id":x[0],"name":x[1],"evidence":x[2]} for x in family_candidates],
                "assignments":[],"unresolved_text":instruction}
    pack_id,pack_name,evidence=family_candidates[0]
    family_alias=next((alias for alias in [str(next((p.get("curated_id") for p in packs if p.get("id")==pack_id),"") or ""),
                                  *[w for w in words(pack_name) if w not in IGNORED_NAME_WORDS]]
                       if alias and _mentions(instruction,alias)),pack_id)
    candidates=[]
    for item in instruments:
        if not isinstance(item,dict) or item.get("pack_id")!=pack_id:continue
        variants=_variants(item,family_alias)
        for variant in variants:
            if variant and _mentions(instruction,variant):
                candidates.append({"pack_id":pack_id,"instrument_id":item.get("id"),
                                   "instrument_name":item.get("name"),
                                   "variant":variant,"evidence":variant})
    # Treat each variant mention as its own phrase. A following qualifier
    # belongs to the preceding variant, never to the next named variant.
    # Examples: "Dirty default, Angry for choruses, Shifty for bridges".
    tokens=words(instruction)
    occurrences=[]
    for item in candidates:
        needle=words(item["variant"])
        for index in range(len(tokens)-len(needle)+1):
            if tokens[index:index+len(needle)]==needle:
                occurrences.append((index,index+len(needle),item))
    occurrences.sort(key=lambda row:(row[0],-(row[1]-row[0])))
    # Exclude duplicate matches for the same instrument at the same position.
    unique=[]
    seen=set()
    for begin,finish,item in occurrences:
        key=(begin,finish,str(item["instrument_id"]))
        if key not in seen:
            seen.add(key)
            unique.append((begin,finish,item))
    resolved=[]
    for number,(begin,finish,item) in enumerate(unique):
        preceding=unique[number-1][1] if number else 0
        following=unique[number+1][0] if number+1<len(unique) else len(tokens)
        # Postfix syntax takes precedence: "angry for choruses".
        after=tokens[finish:min(following,finish+5)]
        before=tokens[max(preceding,begin-4):begin]
        def scope_for(fragment:list[str])->str|None:
            if any(word in fragment for word in ("default","normally","usually")):
                return "default"
            for scope,aliases in SECTION_TOKENS.items():
                for alias in aliases:
                    label=words(alias)
                    if any(fragment[i:i+len(label)]==label
                           for i in range(len(fragment)-len(label)+1)):
                        return scope
            return None
        after_scope=scope_for(after)
        before_scope=scope_for(before)
        # "Dirty default, Angry chorus" must not let the previous
        # instrument's trailing "default" qualify the next variant.
        if before_scope=="default" and number>0:
            before_scope=None
        # "chorus Angry, bridge Shifty" names the *next* section
        # before its variant. Without an explicit connector like "for",
        # prefer the section immediately before Angry.
        after_connector=any(token in after[:2] for token in ("for","in","during","on","as"))
        scope=(before_scope if before_scope and after_scope and not after_connector
               else after_scope or before_scope or "default")
        resolved.append({**item,"section":scope})
    assignments=[]
    conflicts=[]
    for section in sorted({r["section"] for r in resolved}):
        matches={str(r["instrument_id"]):r for r in resolved if r["section"]==section}
        if len(matches)>1:
            conflicts.append({"section":section,"candidates":list(matches.values())})
        elif matches:
            assignments.append(next(iter(matches.values())))
    # No token erasure here: the LLM gets full user direction and grounded
    # choices, while any unverified term stays creative direction, not an ID.
    return {"status":"ambiguous" if conflicts else "matched",
            "family":{"pack_id":pack_id,"name":pack_name,"evidence":evidence},
            "assignments":assignments,"conflicts":conflicts,
            "unresolved_text":instruction,
            "rule":"Verified catalogue selections precede creative interpretation" }
