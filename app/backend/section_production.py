"""Song Harbor production block notation, deliberately separate from section tags.

MVP executes pan, mid/side width, reverb send and reset. Other effects are rejected explicitly, not silently
accepted or misrepresented as applied audio processing.
"""
from __future__ import annotations
import re
from typing import Any

TOKEN = re.compile(
    r"(?i)^(?:(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.(?P<parameter>pan|reverb|width|space):(?P<value>center|left(?:\.\d{1,3})?|right(?:\.\d{1,3})?|reset|\d{1,3})"
    r"|(?P<reset>all\.reset|[A-Za-z][A-Za-z0-9_-]*\.reset))"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
ALIASES = ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")
def source_map(files:list[str], tracks:list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None)->dict[str,str]:
    """Resolve editable aliases to immutable working files, including legacy stems."""
    mapping={}
    for row in tracks or []:
        filename=row.get("working_filename")
        alias=row.get("stem_alias")
        if filename in files and isinstance(alias,str):
            if alias.casefold() in {key.casefold() for key in mapping}:
                raise ValueError("Duplicate project stem alias")
            mapping[alias]=filename
    assigned=set(mapping.values())
    for filename in files:
        if filename in assigned: continue
        match=re.search(r"\(([A-Za-z][A-Za-z0-9_-]*)\)",filename)
        if match:
            alias=match.group(1)
            if alias.casefold() in {key.casefold() for key in mapping}:
                raise ValueError("Duplicate project stem alias")
            mapping[alias]=filename
    # Child targets are stable virtual keys and never rename an audio file.
    # Keep them addressable only when a validated L/R split is attached.
    parents=list(mapping.items())
    for alias,filename in parents:
        entry=(children or {}).get(filename)
        if isinstance(entry,dict) and entry.get("export"):
            for side in ("left","right"):
                child_alias=alias+"-"+side
                if child_alias.casefold() in {key.casefold() for key in mapping}:
                    raise ValueError("Channel alias collides with an existing stem alias")
                mapping[child_alias]=filename+":"+side
    return mapping


def source_aliases(files:list[str], tracks:list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None)->tuple[str,...]:
    return tuple(source_map(files,tracks,children))


EQ_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.eq(?P<band>[123]):"
    r"(?P<freq>\d{2,5}),(?P<q>\d+(?:\.\d{1,2})?),(?P<gain>[+-]?\d+(?:\.\d)?)"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
DYNAMICS_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.(?P<kind>comp|duck):"
    r"(?P<value>-?\d+(?:\.\d+)?)(?:,(?P<ratio>\d+(?:\.\d+)?))?"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
DEESS_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.deess:"
    r"(?P<freq>\d{4,5}),(?P<q>\d+(?:\.\d{1,2})?),"
    r"(?P<threshold>-\d+(?:\.\d{1,2})?),(?P<reduction>\d+(?:\.\d{1,2})?)"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
VOLUME_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.volume:(?P<percent>\d{1,3})"
    r"(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s"
    r"(?::(?P<curve>smooth|linear))?$"
)
GAIN_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.gain:(?P<gain>[+-]?(?:\d+(?:\.\d{1,2})?|\.\d{1,2}))"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
# Linked accepted replacement, editable in the section script without replacing
# the track's independently authored gain automation.
ORIGINAL_MIX_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.original:(?P<percent>\d{1,3})%"
    r"@(?P<start>\d+(?:\.\d{1,3})?)-(?P<end>\d+(?:\.\d{1,3})?)"
    r"#(?P<replacement>trk_[A-Za-z0-9_-]{1,64})$"
)
AUTO_PAN_TOKEN = re.compile(
    r"(?i)^auto\.pan:center(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s"
    r"(?::(?P<curve>smooth|linear))?)?$"
)
EVOLUTION_TOKEN = re.compile(
    r"(?i)^(?P<track>[A-Za-z][A-Za-z0-9_-]*)\.evolve:menacing"
    r"(?:(?P<anchor>[@#])(?P<seconds>\d+(?:\.\d{1,3})?)s(?::(?P<curve>smooth|linear))?)?$"
)
EVOLUTION_VERSION = 1
FINISH = re.compile(r"(?i)^Master\.(fade|tail):(\d+(?:\.\d{1,3})?)s(?::(smooth|linear))?$")


def parse_block(text: str, aliases:tuple[str,...]=ALIASES) -> list[dict[str, Any]]:
    if len(text) > 32768 or not text.startswith("{") or not text.endswith("}"):
        raise ValueError("Production instructions must be enclosed in one {...} block")
    tokens = text[1:-1].strip().split()
    if len(tokens) > 512:
        raise ValueError("Maximum 512 production directives per section")
    directives = []
    touched = set()
    for token in tokens:
        volume=VOLUME_TOKEN.fullmatch(token)
        if volume:
            canonical=next((a for a in aliases if a.casefold()==volume.group("track").casefold()),None)
            if not canonical or canonical.casefold().endswith(("-left","-right")):
                raise ValueError("Volume must target an existing parent stem")
            percent=int(volume.group("percent"))
            duration=float(volume.group("seconds"))
            if percent>100 or not .05<=duration<=30:
                raise ValueError("Volume needs 0..100 and .05..30s transition")
            key=canonical.casefold()+".volume"
            if key in touched:
                raise ValueError("Duplicate volume directive in section")
            touched.add(key)
            directives.append({"kind":"volume","track":canonical,"percent":percent,
                               "transition_seconds":duration,
                               "transition_anchor":"end" if volume.group("anchor")=="#" else "start",
                               "curve":(volume.group("curve") or "smooth").lower()})
            continue
        original=ORIGINAL_MIX_TOKEN.fullmatch(token)
        if original:
            canonical=next((a for a in aliases if a.casefold()==original.group("track").casefold()),None)
            if not canonical or canonical.lower().endswith(("-left","-right")):
                raise ValueError("Original mix must target an existing parent stem")
            percent=int(original.group("percent"))
            begin=float(original.group("start"))
            end=float(original.group("end"))
            if percent>100 or not 0<=begin<end or end-begin>900:
                raise ValueError("Original mix needs 0..100% and a valid time span")
            replacement_id=original.group("replacement")
            key="original:"+replacement_id
            if key in touched:raise ValueError("Duplicate original mix for replacement")
            touched.add(key)
            directives.append({"kind":"original_mix","track":canonical,"percent":percent,
                               "start_seconds":begin,"end_seconds":end,
                               "replacement_track_id":replacement_id})
            continue
        evolution=EVOLUTION_TOKEN.fullmatch(token)
        if evolution:
            canonical=next((a for a in aliases if a.casefold()==evolution.group("track").casefold()),None)
            if not canonical or canonical.lower().endswith(("-left","-right")):
                raise ValueError("Evolution macro must target an existing parent stem")
            duration=float(evolution.group("seconds") or 20)
            if not .05<=duration<=30:
                raise ValueError("Evolution duration must be 0.05-30 seconds")
            key=canonical.lower()+".evolve"
            if key in touched or "all" in touched:
                raise ValueError("Duplicate or conflicting evolution macro")
            touched.add(key)
            directives.append({"kind":"evolve","track":canonical,"preset":"menacing",
                               "version":EVOLUTION_VERSION,"transition_seconds":duration,
                               "curve":(evolution.group("curve") or "smooth").lower(),"transition_anchor":"end" if evolution.group("anchor")=="#" else "start"})
            continue
        auto_pan=AUTO_PAN_TOKEN.fullmatch(token)
        if auto_pan:
            if "auto.pan" in touched or "all" in touched:
                raise ValueError("Duplicate or conflicting auto.pan")
            duration=float(auto_pan.group("seconds") or 8)
            if not (.05<=duration<=30):
                raise ValueError("Auto-pan transition must be .05-30 seconds")
            touched.add("auto.pan")
            directives.append({"kind":"auto_pan","track":"auto",
                               "transition_seconds":duration,
                               "curve":(auto_pan.group("curve") or "smooth").lower(),"transition_anchor":"end" if auto_pan.group("anchor")=="#" else "start"})
            continue
        gain_match=GAIN_TOKEN.fullmatch(token)
        if gain_match:
            canonical=next((a for a in aliases if a.lower()==gain_match.group("track").lower()),None)
            if not canonical and gain_match.group("track").lower()=="all": canonical="all"
            if not canonical: raise ValueError("Unknown gain stem")
            gain_db=float(gain_match.group("gain"))
            duration=float(gain_match.group("seconds") or 1)
            if not (-24<=gain_db<=12 and .05<=duration<=30):
                raise ValueError("Stem gain must be -24..+12 dB with .05..30s transition")
            key=canonical.lower()+".gain"
            if key in touched or "all" in touched or canonical.lower() in touched:
                raise ValueError("Duplicate or conflicting gain directive")
            touched.add(key)
            directives.append({"kind":"gain","track":canonical,"gain_db":gain_db,
                               "transition_seconds":duration,
                               "curve":(gain_match.group("curve") or "smooth").lower(),"transition_anchor":"end" if gain_match.group("anchor")=="#" else "start"})
            continue
        deess=DEESS_TOKEN.fullmatch(token)
        if deess:
            canonical=next((a for a in aliases if a.lower()==deess.group("track").lower()),None)
            if not canonical:raise ValueError("Unknown de-esser stem")
            frequency=int(deess.group("freq"))
            q=float(deess.group("q"))
            threshold=float(deess.group("threshold"))
            reduction=float(deess.group("reduction"))
            transition=float(deess.group("seconds") or 1)
            if not (3000<=frequency<=11000 and .4<=q<=8 and -70<=threshold<=-10
                    and 0<=reduction<=12 and .05<=transition<=30):
                raise ValueError("De-esser requires frequency 3000-11000 Hz, Q .4-8, threshold -70..-10 dBFS and reduction 0..12 dB")
            key=canonical.lower()+".deess"
            if key in touched or "all" in touched or canonical.lower() in touched:
                raise ValueError("Duplicate or conflicting de-esser directive")
            touched.add(key)
            directives.append({"kind":"deess","track":canonical,"frequency":frequency,
                               "q":q,"threshold_db":threshold,"max_reduction_db":reduction,
                               "transition_seconds":transition,
                               "curve":(deess.group("curve") or "smooth").lower(),"transition_anchor":"end" if deess.group("anchor")=="#" else "start"})
            continue
        dynamics=DYNAMICS_TOKEN.fullmatch(token)
        if dynamics:
            canonical=next((a for a in aliases if a.lower()==dynamics.group("track").lower()),None)
            if not canonical:
                raise ValueError("Unknown dynamics stem")
            kind=dynamics.group("kind").lower()
            value=float(dynamics.group("value"))
            ratio=dynamics.group("ratio")
            duration=float(dynamics.group("seconds") or 1)
            if not .05<=duration<=30:
                raise ValueError("Dynamics transition must be .05-30 seconds")
            if kind=="comp":
                if ratio is None or not -60<=value<=0 or not 1<=float(ratio)<=4:
                    raise ValueError("Compressor requires threshold -60..0 dB and ratio 1..4")
                directive={"kind":"comp","track":canonical,"threshold_db":value,"ratio":float(ratio)}
            else:
                if ratio is not None or not 0<=value<=12 or canonical=="Vocals":
                    raise ValueError("Ducking requires 0..12 dB on non-vocal stems")
                directive={"kind":"duck","track":canonical,"depth_db":value}
            key=canonical.lower()+"."+kind
            if key in touched or "all" in touched or canonical.lower() in touched:
                raise ValueError("Duplicate or conflicting dynamics directive")
            touched.add(key)
            directive.update(transition_seconds=duration,curve=(dynamics.group("curve") or "smooth").lower(),transition_anchor="end" if dynamics.group("anchor")=="#" else "start")
            directives.append(directive)
            continue
        eq=EQ_TOKEN.fullmatch(token)
        if eq:
            canonical=next((a for a in aliases if a.lower()==eq.group("track").lower()),None)
            if not canonical and eq.group("track").lower()=="all": canonical="all"
            if not canonical:
                raise ValueError(f"Unknown EQ stem: {eq.group('track')}")
            band=int(eq.group("band"))
            frequency=int(eq.group("freq"))
            q=float(eq.group("q"))
            gain=float(eq.group("gain"))
            transition=float(eq.group("seconds") or 1)
            if not (30<=frequency<=16000 and .3<=q<=12 and -12<=gain<=12):
                raise ValueError("EQ frequency 30-16000 Hz, Q 0.3-12, gain -12 to +12 dB")
            if not .05<=transition<=30:
                raise ValueError("EQ transition must be .05-30 seconds")
            key=f"{canonical.lower()}.eq{band}"
            if key in touched or "all" in touched or canonical.lower() in touched:
                raise ValueError("Duplicate or conflicting EQ band")
            touched.add(key)
            directives.append({"kind":"eq","track":canonical,"band":band,
                               "frequency":frequency,"q":q,"gain_db":gain,
                               "transition_seconds":transition,"curve":(eq.group("curve") or "smooth").lower(),"transition_anchor":"end" if eq.group("anchor")=="#" else "start"})
            continue
        finishing = FINISH.fullmatch(token)
        if finishing:
            action, duration, curve = finishing.groups()
            action = action.lower()
            seconds = float(duration)
            if action == "fade" and not (0.05 <= seconds <= 30):
                raise ValueError("Master fade duration must be 0.05-30 seconds")
            if action == "tail" and not (0 <= seconds <= 10):
                raise ValueError("Master tail must be between 0 and 10 seconds")
            key = "master." + action
            if key in touched:
                raise ValueError("Duplicate master ending directive")
            touched.add(key)
            directives.append({"kind": action, "track": "Master", "seconds": seconds,
                               "curve": (curve or "smooth").lower()})
            continue
        match = TOKEN.fullmatch(token)
        if not match:
            raise ValueError(f"Unsupported production directive: {token}. Pan, width, reverb send and reset only for this release")
        name = match.group("track")
        reset = match.group("reset")
        if name:
            canonical = next((a for a in aliases if a.lower() == name.lower()), None)
            if not canonical and name.lower()=="all": canonical="all"
            if not canonical:
                raise ValueError(f"Unknown stem alias: {name}")
            value = match.group("value").lower()
            parameter = match.group("parameter").lower()
            if parameter == "space":
                if not value.isdigit() or int(value)>40:
                    raise ValueError("Spatial reflection send must be 0-40 percent")
                directive = {"kind":"space", "track":canonical, "amount":int(value)}
            elif parameter == "width":
                if not value.isdigit() or int(value) > 200:
                    raise ValueError("Width must be 0-200 percent (100 is original width)")
                directive = {"kind": "width", "track": canonical, "width": int(value)}
            elif parameter == "reverb":
                if not value.isdigit() or int(value)>100:
                    raise ValueError("Reverb send must be 0-100 percent")
                directive = {"kind": "reverb", "track": canonical, "wet": int(value)/100}
            elif parameter == "pan" and value in ("center", "reset"):
                pan = 0.0
            elif parameter == "pan":
                if not (value.startswith("left") or value.startswith("right")):
                    raise ValueError("Pan target must be center, left or right")
                direction, _, amount = value.partition(".")
                n = int(amount) if amount else 100
                if n > 100:
                    raise ValueError("Pan percentage cannot exceed 100")
                pan = n / 100 * (-1 if direction == "left" else 1)
            key = canonical.lower() + "." + parameter
            if parameter == "pan":
                directive = {"kind": "pan", "track": canonical, "pan": pan}
        else:
            canonical = "all" if reset.lower() == "all.reset" else next(
                (a for a in aliases if a.lower() == reset[:-6].lower()), None)
            if not canonical:
                raise ValueError(f"Unknown reset scope: {reset}")
            key = canonical.lower() if canonical == "all" else canonical.lower()
            directive = {"kind": "reset", "track": canonical}
        if canonical.lower() in touched and canonical != "all":
            raise ValueError(f"{canonical}.reset conflicts with other {canonical} settings in this section. To reset compression only, use {canonical}.comp:-18,1@2s:smooth and retain explicit pan/width/space values.")
        if key in touched or ("all" in touched):
            raise ValueError("Duplicate or conflicting production directives within a section")
        if canonical == "all" and directive["kind"] == "reset" and any(not x.startswith("master.") for x in touched):
            raise ValueError("all.reset cannot be combined with stem directives")
        touched.add(key)
        duration = float(match.group("seconds") or 1)
        if duration < 0.05 or duration > 30:
            raise ValueError("Transition must be between 0.05 and 30 seconds")
        directive["transition_seconds"] = duration
        directive["curve"] = (match.group("curve") or "smooth").lower()
        directive["transition_anchor"] = "end" if match.group("anchor")=="#" else "start"
        directives.append(directive)
    return directives


def render_block(directives: list[dict[str, Any]]) -> str:
    rendered = []
    for d in directives:
        if d["kind"] == "original_mix":
            rendered.append(
                f"{d['track']}.original:{int(d['percent'])}%"
                f"@{float(d['start_seconds']):.3f}-{float(d['end_seconds']):.3f}"
                f"#{d['replacement_track_id']}")
            continue
        if d["kind"] == "evolve":
            if d.get("preset")!="menacing" or d.get("version")!=EVOLUTION_VERSION:
                raise ValueError("Unknown evolution macro version")
            rendered.append(f"{d['track']}.evolve:menacing{'#' if d.get('transition_anchor')=='end' else '@'}{d['transition_seconds']:g}s:{d['curve']}")
            continue
        if d["kind"] == "auto_pan":
            rendered.append(f"auto.pan:center{'#' if d.get('transition_anchor')=='end' else '@'}{d['transition_seconds']:g}s:{d['curve']}")
            continue
        if d["kind"] in ("fade", "tail"):
            head = f"Master.{d['kind']}:{float(d['seconds']):g}s"
            if d["kind"] == "fade":
                head += ":" + d["curve"]
            rendered.append(head)
            continue
        suffix = f"{'#' if d.get('transition_anchor')=='end' else '@'}{d['transition_seconds']:g}s:{d['curve']}"
        if d["kind"] == "reset":
            head = "all.reset" if d["track"] == "all" else d["track"] + ".reset"
        elif d["kind"] == "gain":
            head = f"{d['track']}.gain:{float(d['gain_db']):+g}"
        elif d["kind"] == "volume":
            head = f"{d['track']}.volume:{int(d['percent'])}"
        elif d["kind"] == "deess":
            head = f"{d['track']}.deess:{d['frequency']},{float(d['q']):g},{float(d['threshold_db']):g},{float(d['max_reduction_db']):g}"
        elif d["kind"] == "comp":
            head = f"{d['track']}.comp:{float(d['threshold_db']):g},{float(d['ratio']):g}"
        elif d["kind"] == "duck":
            head = f"{d['track']}.duck:{float(d['depth_db']):g}"
        elif d["kind"] == "eq":
            head = f"{d['track']}.eq{d['band']}:{d['frequency']},{float(d['q']):g},{float(d['gain_db']):+g}"
        elif d["kind"] == "space":
            head = f"{d['track']}.space:{d['amount']}"
        elif d["kind"] == "width":
            head = f"{d['track']}.width:{d['width']}"
        elif d["kind"] == "reverb":
            head = f"{d['track']}.reverb:{round(float(d['wet'])*100)}"
        else:
            value = float(d["pan"])
            if value == 0:
                pos = "center"
            else:
                pos = ("left" if value < 0 else "right") + f".{round(abs(value)*100)}"
            head = f"{d['track']}.pan:{pos}"
        rendered.append(head + suffix)
    return "{\n  " + "\n  ".join(rendered) + "\n}" if len(rendered)>1 else "{" + " ".join(rendered) + "}"




def expand_evolution(blocks:dict[str,list[dict[str,Any]]],
                     parents:tuple[str,...],
                     aliases:tuple[str,...]) -> dict[str,list[dict[str,Any]]]:
    """Compile versioned menacing intent to inspectable, existing DSP targets.

    All effects retain normal song-time section inheritance. Explicit
    directives always override macro-generated targets for the same stem,
    parameter and EQ band. No source audio or authored intent is overwritten.
    """
    available={alias.casefold():alias for alias in aliases}
    output={}
    for section_id,directives in blocks.items():
        explicit={(d["track"].casefold(),d["kind"],d.get("band"))
                  for d in directives if d["kind"]!="evolve"}
        expansions=[]
        for directive in directives:
            if directive["kind"]!="evolve":
                continue
            alias=directive["track"]
            if alias not in parents or directive.get("preset")!="menacing" or directive.get("version")!=EVOLUTION_VERSION:
                raise ValueError("Unsupported spatial evolution macro")
            base=[
                ("pan",{"pan":.18}),("width",{"width":125}),
                ("space",{"amount":18}),("reverb",{"wet":.16}),
                ("eq",{"band":1,"frequency":380,"q":.9,"gain_db":1.1}),
                ("eq",{"band":2,"frequency":3200,"q":.8,"gain_db":-1.7})
            ]
            # When split channels exist, asymmetry is created before the
            # parent bus, without moving bass or other unrelated stems.
            for side,wet,freq,cut in (("left",.11,3500,-.8),
                                       ("right",.23,2600,-2.1)):
                key=available.get((alias+"-"+side).casefold())
                if key:
                    base.extend([
                        ("reverb",{"track":key,"wet":wet}),
                        ("eq",{"track":key,"band":2,"frequency":freq,
                               "q":.9,"gain_db":cut})
                    ])
            for kind,params in base:
                target=params.get("track",alias)
                key=(target.casefold(),kind,params.get("band"))
                if key in explicit:
                    continue
                expansions.append({"kind":kind,"track":target,
                                   "transition_seconds":directive["transition_seconds"],
                                   "curve":directive["curve"],
                                   **{k:v for k,v in params.items() if k!="track"}})
                explicit.add(key)
        output[section_id]=[d for d in directives if d["kind"]!="evolve"]+expansions
    return output

def expand_broadcast(blocks: dict[str, list[dict[str, Any]]],
                     aliases: tuple[str,...]) -> dict[str, list[dict[str, Any]]]:
    """Compile all.effect defaults without altering the authored script.

    Explicit stem/effect directives win regardless of textual ordering.
    EQ overrides are per band, not whole-EQ. This does not implement auto solvers.
    """
    result={}
    for section_id, directives in blocks.items():
        explicit={(d["track"].lower(),d["kind"],d.get("band"))
                  for d in directives if d["track"].lower() not in ("all","master")}
        expanded=[]
        for directive in directives:
            if directive["track"].lower()!="all" or directive["kind"]=="reset":
                expanded.append(directive)
                continue
            for alias in aliases:
                if (alias.lower(),directive["kind"],directive.get("band")) in explicit:
                    continue
                expanded.append({**directive,"track":alias})
        result[section_id]=expanded
    return result



def materialize_auto_pan(sections: list[dict[str, Any]],
                         blocks: dict[str, list[dict[str, Any]]],
                         files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    """Emit per-section intent and protected inherited pan positions.

    Auto pan is not implicitly sticky; each requesting section is independent.
    Explicit and broadcast pan settings persist as protection until reset.
    """
    aliases=source_aliases(files,tracks)
    stems=source_map(files,tracks)
    protected=set()
    protected_gain=set()
    output=[]
    for section in sorted(sections,key=lambda x:x["start_seconds"]):
        directives=blocks.get(section["id"],[])
        for d in directives:
            if d["kind"]=="reset":
                if d["track"]=="all":
                    protected.clear()
                    protected_gain.clear()
                else:
                    protected.discard(d["track"])
                    protected_gain.discard(d["track"])
            elif d["kind"]=="pan":
                if d["track"]=="all": protected.update(stems)
                else: protected.add(d["track"])
            elif d["kind"]=="gain":
                if d["track"]=="all": protected_gain.update(stems)
                else: protected_gain.add(d["track"])
        for d in directives:
            if d["kind"]=="auto_pan":
                output.append({"section_id":section["id"],"target":"center",
                               "protected_sources":[stems[a] for a in aliases if a in protected and a in stems],
                               "protected_gain_sources":[stems[a] for a in aliases if a in protected_gain and a in stems],
                               "transition_seconds":d["transition_seconds"],"transition_anchor":d.get("transition_anchor","start"),"curve":d["curve"]})
    return output


def materialize_pan(sections: list[dict[str, Any]],
                    blocks: dict[str, list[dict[str, Any]]],
                    files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    """Compile inheritance and resets into explicit per-section pan targets.

    This representation is compatible with the existing shared-clock preview.
    Missing directives hold the previous target. A reset restores track default
    (currently center), but does not alter manual mixer settings.
    """
    stems = source_map(files,tracks,children)
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for d in blocks.get(section["id"], []):
            if d["kind"] in ("reverb", "width", "space", "fade", "tail", "eq", "comp", "duck", "deess", "gain", "volume", "auto_pan"):
                continue
            targets = stems.keys() if d["kind"] == "reset" and d["track"] == "all" else [d["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Production track {alias} does not exist in this song")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "pan": d["pan"] if d["kind"] == "pan" else 0.0,
                    "transition_seconds": d["transition_seconds"],"transition_anchor":d.get("transition_anchor","start"),
                    "curve": d["curve"],
                })
    return output


def materialize_reverb(sections: list[dict[str, Any]],
                       blocks: dict[str, list[dict[str, Any]]],
                       files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    stems = source_map(files,tracks,children)
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for directive in blocks.get(section["id"], []):
            if directive["kind"] in ("pan", "width", "space", "fade", "tail", "eq", "comp", "duck", "deess", "gain", "volume", "auto_pan"):
                continue
            targets = list(stems) if directive["kind"] == "reset" and directive["track"] == "all" else [directive["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError("Reverb target not in project")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "wet": directive["wet"] if directive["kind"] == "reverb" else 0.0,
                    "transition_seconds": directive["transition_seconds"],"transition_anchor":directive.get("transition_anchor","start"),
                    "curve": directive["curve"],
                })
    return output



def materialize_width(sections: list[dict[str, Any]],
                      blocks: dict[str, list[dict[str, Any]]],
                      files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    """Compile explicit width changes; omitted sections inherit previous value."""
    stems=source_map(files,tracks,children)
    output = []
    for section in sorted(sections, key=lambda s: s["start_seconds"]):
        for directive in blocks.get(section["id"], []):
            kind = directive["kind"]
            if kind not in ("width", "reset"):
                continue
            targets = (list(stems) if kind == "reset" and directive["track"] == "all"
                       else [directive["track"]])
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Width target {alias} not in project")
                output.append({
                    "section_id": section["id"], "source_key": stems[alias],
                    "width": directive["width"] if kind == "width" else 100,
                    "transition_seconds": directive["transition_seconds"],"transition_anchor":directive.get("transition_anchor","start"),
                    "curve": directive["curve"],
                })
    return output

def materialize_space(sections: list[dict[str, Any]],
                      blocks: dict[str, list[dict[str, Any]]],
                      files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    stems=source_map(files,tracks,children)
    output=[]
    for section in sorted(sections,key=lambda s:s["start_seconds"]):
        for d in blocks.get(section["id"], []):
            if d["kind"] not in ("space","reset"):
                continue
            targets=list(stems) if d["kind"]=="reset" and d["track"]=="all" else [d["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Spatial reflection target {alias} not in project")
                output.append({"section_id":section["id"], "source_key":stems[alias],
                               "amount":d["amount"] if d["kind"]=="space" else 0,
                               "transition_seconds":d["transition_seconds"], "curve":d["curve"]})
    return output


def materialize_eq(sections: list[dict[str, Any]],
                   blocks: dict[str, list[dict[str, Any]]],
                   files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    stems=source_map(files,tracks,children)
    out=[]
    for section in sorted(sections,key=lambda s:s["start_seconds"]):
        for d in blocks.get(section["id"],[]):
            if d["kind"] not in ("eq","reset"):
                continue
            targets=(list(stems) if d["kind"]=="reset" and d["track"]=="all"
                     else [d["track"]])
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"EQ target {alias} not found")
                bands=range(1,4) if d["kind"]=="reset" else [d["band"]]
                for band in bands:
                    out.append({"section_id":section["id"],"source_key":stems[alias],
                                "band":band,
                                "frequency":d["frequency"] if d["kind"]=="eq" else 1000,
                                "q":d["q"] if d["kind"]=="eq" else 1.0,
                                "gain_db":d["gain_db"] if d["kind"]=="eq" else 0.0,
                                "transition_seconds":d["transition_seconds"],
                                "curve":d["curve"]})
    return out


def materialize_ending(sections: list[dict[str, Any]],
                       blocks: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """End-anchored dry mix fade and wet-tail extension.

    An explicit ending is restricted to the final audible section. The full
    post-roll is a single project-level setting, not a per-stem effect.
    """
    ordered = sorted(sections, key=lambda s: s["start_seconds"])
    ending = {"fade_seconds": 0.0, "tail_seconds": 0.0, "curve": "smooth"}
    final_id = ordered[-1]["id"] if ordered else None
    for section in ordered:
        for directive in blocks.get(section["id"], []):
            if directive["kind"] not in ("fade", "tail"):
                continue
            if section["id"] != final_id:
                raise ValueError("Master.fade and Master.tail belong to the final section")
            if directive["kind"] == "fade":
                if directive["seconds"] > section["end_seconds"]-section["start_seconds"]:
                    raise ValueError("Fade cannot be longer than the final section")
                ending["fade_seconds"] = directive["seconds"]
                ending["curve"] = directive["curve"]
            else:
                ending["tail_seconds"] = directive["seconds"]
    return ending

def materialize_dynamics(sections: list[dict[str, Any]],
                         blocks: dict[str, list[dict[str, Any]]],
                         files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    """Only explicit dynamics or resets appear; older projects stay neutral."""
    stems=source_map(files,tracks,children)
    out=[]
    for section in sorted(sections,key=lambda item:item["start_seconds"]):
        for directive in blocks.get(section["id"],[]):
            kind=directive["kind"]
            if kind not in ("comp","duck","deess","reset"):
                continue
            targets=list(stems) if kind=="reset" and directive["track"]=="all" else [directive["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError(f"Dynamics target {alias} not found")
                for operation in (("comp","duck","deess") if kind=="reset" else (kind,)):
                    if operation=="duck" and alias=="Vocals":
                        continue
                    out.append({"section_id":section["id"],"source_key":stems[alias],
                                "kind":operation,
                                "threshold_db":directive.get("threshold_db",-18) if kind!="reset" else -18,
                                "ratio":directive.get("ratio",1) if kind!="reset" else 1,
                                "depth_db":directive.get("depth_db",0) if kind!="reset" else 0,
                                "frequency":directive.get("frequency",6500) if kind!="reset" else 6500,
                                "q":directive.get("q",2) if kind!="reset" else 2,
                                "max_reduction_db":directive.get("max_reduction_db",0) if kind!="reset" else 0,
                                "transition_seconds":directive["transition_seconds"],"transition_anchor":directive.get("transition_anchor","start"),"curve":directive["curve"]})
    return out

def materialize_volume(sections:list[dict[str,Any]],
                       blocks:dict[str,list[dict[str,Any]]],
                       files:list[str],tracks:list[dict[str,Any]]|None=None,
                       children:dict[str,Any]|None=None)->list[dict[str,Any]]:
    """Relative stem-volume automation, independent of existing dB gain scripts."""
    stems=source_map(files,tracks,children)
    output=[]
    for section in sorted(sections,key=lambda entry:entry["start_seconds"]):
        for d in blocks.get(section["id"],[]):
            if d["kind"]!="volume":continue
            duration=d["transition_seconds"]
            if duration>section["end_seconds"]-section["start_seconds"]+1e-6:
                raise ValueError("Volume transition cannot exceed its section")
            output.append({"section_id":section["id"],"source_key":stems[d["track"]],
                           "volume":d["percent"]/100,
                           "transition_seconds":duration,
                           "transition_anchor":d.get("transition_anchor","start"),
                           "curve":d["curve"]})
    return output


def materialize_gain(sections: list[dict[str, Any]],
                     blocks: dict[str, list[dict[str, Any]]],
                     files: list[str], tracks: list[dict[str, Any]]|None=None, children:dict[str,Any]|None=None) -> list[dict[str, Any]]:
    """Section gain in dB relative to saved mixer level; resets are neutral."""
    stems=source_map(files,tracks,children)
    output=[]
    for section in sorted(sections,key=lambda item:item["start_seconds"]):
        for directive in blocks.get(section["id"],[]):
            if directive["kind"] not in ("gain","reset"):
                continue
            targets=list(stems) if directive["kind"]=="reset" and directive["track"]=="all" else [directive["track"]]
            for alias in targets:
                if alias not in stems:
                    raise ValueError("Gain target not in project")
                output.append({"section_id":section["id"],"source_key":stems[alias],
                               "gain_db":directive["gain_db"] if directive["kind"]=="gain" else 0.0,
                               "transition_seconds":directive["transition_seconds"],
                               "curve":directive["curve"]})
    return output
