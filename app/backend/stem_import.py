"""Import externally prepared tracks into an aligned Song Harbor project.

Original audio is retained; working WAVs are rendered to one common duration.
"""
from __future__ import annotations

import re
from pathlib import Path

ROLES=("Vocals","Drums","Bass","Guitar","Piano","Other")
ROLE_WORDS={
    "Vocals":("vocals","vocal","vox","voice","lead vocal","backing vocal","bgv"),
    "Drums":("drums","drum","percussion","perc","beats"),
    "Bass":("bass",),
    "Guitar":("guitar","guitars","gtr"),
    "Piano":("piano","keys","keyboard"),
    "Other":("other","instrumental","instruments","music"),
}
TRAILING=re.compile(r"(?i)(?:[\s._-]*(?:stem|track|take|mix|audio)[\s._-]*\d*)+$")
SPLIT=re.compile(r"[\s._-]+")


def infer_role(filename:str)->str|None:
    stem=Path(filename).stem.lower()
    # Demucs/Song Harbor names often use "(Vocals)_htdemucs_6s.wav".
    # Match role words as independent terms, never substrings of song titles
    # (e.g. "Guitarist" should not be silently classified Guitar).
    for role,aliases in ROLE_WORDS.items():
        for alias in aliases:
            if re.search(r"(?<![a-z0-9])"+re.escape(alias)+r"(?![a-z0-9])",stem):
                return role
    return None


def guess_song_title(filenames:list[str])->str:
    """Common descriptive prefix with stem role suffix removed; safe fallback."""
    if not filenames:return "Imported song"
    names=[]
    for filename in filenames:
        stem=Path(filename).stem
        # Drop recognizable terminal stem label with optional separator and index.
        stem=re.sub(r"(?i)[\s._-]*\(?"
            r"(vocals?|vox|voice|drums?|percussion|perc|beats|bass|guitars?|gtr|piano|keys|keyboard|other|instrumental|instruments|music)"
            r"\)?(?:[\s._-]*\d{1,2})?$","",stem).strip(" ._-")
        names.append(stem)
    tokens=[list(filter(None,SPLIT.split(name))) for name in names]
    prefix=[]
    for parts in zip(*tokens):
        if len({word.casefold() for word in parts})!=1:break
        prefix.append(parts[0])
    title=" ".join(prefix).strip(" ._-")
    if not title and len(names)==1:title=names[0]
    return title[:120] or "Imported song"


def assign_tracks(filenames:list[str])->list[dict[str,str]]:
    """Recognize at most one of each canonical stem, preserve extras distinctly."""
    used:set[str]=set()
    result=[]
    for filename in filenames:
        role=infer_role(filename)
        if not role or role in used:
            next_index=1
            while f"Track{next_index:02d}" in used:next_index+=1
            role=f"Track{next_index:02d}"
        used.add(role)
        result.append({"original_filename":filename,"stem_alias":role})
    return result
