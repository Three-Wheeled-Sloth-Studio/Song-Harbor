"""Local, data-only instrument pack registry and bounded FluidSynth SF2 renderer.

User-imported SoundFonts are never redistributed, modified, or downloaded.
Only trusted local executable discovery; pack files cannot supply code.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

SOUNDFONT_LIMIT=512*1024*1024
PACK_ID=re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PACK_DIR="instrument-packs"
BUILTIN=[
    {"id":"bowed","name":"Bowed strings","pack_id":"song-harbor-core","engine":"synthetic","program":42,"bank":0},
    {"id":"plucked","name":"Plucked bass","pack_id":"song-harbor-core","engine":"synthetic","program":32,"bank":0},
    {"id":"warm_pad","name":"Warm pad","pack_id":"song-harbor-core","engine":"synthetic","program":89,"bank":0},
]

def pack_root(runtime:Path)->Path:
    return runtime/PACK_DIR

def _safe_label(value:str)->str:
    label="".join(x for x in value if x.isprintable()).strip()
    return label[:100] or "SoundFont"

def sf2_presets(path:Path)->list[dict[str,Any]]:
    """Read SoundFont RIFF/pdta/phdr; reject malformed or oversized chunks."""
    size=path.stat().st_size
    if size<64 or size>SOUNDFONT_LIMIT:raise ValueError("SoundFont must be 64 bytes to 512 MB")
    presets=[]
    with path.open("rb") as fh:
        header=fh.read(12)
        if header[:4]!=b"RIFF" or header[8:12]!=b"sfbk":
            raise ValueError("Expected an SF2 SoundFont RIFF file")
        if int.from_bytes(header[4:8],"little")+8>size:
            raise ValueError("Truncated SoundFont")
        def chunks(limit:int):
            while fh.tell()+8<=limit:
                tag=fh.read(4)
                length=int.from_bytes(fh.read(4),"little")
                end=fh.tell()+length
                if end>limit:raise ValueError("Malformed SoundFont chunk")
                yield tag,length,end
                fh.seek(end+(length&1))
        for tag,length,end in chunks(min(size,int.from_bytes(header[4:8],"little")+8)):
            if tag!=b"LIST" or length<4:continue
            fh.seek(end-length)
            list_type=fh.read(4)
            if list_type!=b"pdta":continue
            for sub,size_sub,stop in chunks(end):
                if sub!=b"phdr":continue
                if size_sub%38 or size_sub<76:raise ValueError("Invalid SF2 preset header")
                for _ in range(size_sub//38-1): # final preset is EOP sentinel
                    row=fh.read(38)
                    name=_safe_label(row[:20].split(b"\x00")[0].decode("latin-1","replace"))
                    program,bank=struct.unpack_from("<HH",row,20)
                    if program<=127 and bank<=16383:
                        presets.append({"name":name,"program":program,"bank":bank})
                if len(presets)>4096:raise ValueError("Too many instrument presets")
                fh.seek(stop)
            break
    if not presets:raise ValueError("No playable SF2 presets discovered")
    return presets

def catalogue(runtime:Path)->dict[str,list[dict]]:
    packs=[{"id":"song-harbor-core","name":"Song Harbor Core","engine":"synthetic","source":"built-in"}]
    instruments=[dict(row) for row in BUILTIN]
    root=pack_root(runtime)
    if root.is_dir():
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or not PACK_ID.fullmatch(folder.name):continue
            manifest=folder/"manifest.json"
            if not manifest.is_file():continue
            try:
                doc=json.loads(manifest.read_text(encoding="utf-8"))
                if doc.get("id")!=folder.name or doc.get("engine")!="sf2":continue
                sf2=folder/"bank.sf2"
                if not sf2.is_file() or sf2.stat().st_size>SOUNDFONT_LIMIT:continue
                entries=doc.get("instruments",[])
                if not isinstance(entries,list) or len(entries)>4096:continue
                packs.append({"id":folder.name,"name":_safe_label(str(doc.get("name","SoundFont"))),
                              "engine":"sf2","source":"user-installed"})
                for row in entries:
                    if not isinstance(row,dict):continue
                    program,bank=row.get("program"),row.get("bank")
                    if type(program)!=int or not 0<=program<=127 or type(bank)!=int or not 0<=bank<=16383:continue
                    instruments.append({"id":str(row.get("id","")),"name":_safe_label(str(row.get("name","Instrument"))),
                                        "pack_id":folder.name,"engine":"sf2","program":program,"bank":bank})
            except (OSError,ValueError,TypeError):continue
    return {"packs":packs,"instruments":instruments}

def resolve_instrument(runtime:Path,pack_id:str,instrument_id:str)->tuple[dict,Path|None]:
    data=catalogue(runtime)
    found=next((i for i in data["instruments"] if i["pack_id"]==pack_id and i["id"]==instrument_id),None)
    if not found:raise ValueError("Instrument is not installed in the selected pack")
    path=None if found["engine"]=="synthetic" else pack_root(runtime)/pack_id/"bank.sf2"
    return found,path

def install_sf2(runtime:Path,staged:Path,name:str)->dict:
    presets=sf2_presets(staged)
    root=pack_root(runtime)
    root.mkdir(parents=True,exist_ok=True)
    identifier="user-"+uuid.uuid4().hex[:16]
    directory=root/identifier
    directory.mkdir()
    try:
        destination=directory/"bank.sf2"
        os.replace(staged,destination)
        items=[{"id":f"p-{i}-b-{p['bank']}-n-{p['program']}","name":p["name"],
                "bank":p["bank"],"program":p["program"]} for i,p in enumerate(presets)]
        manifest={"schema_version":1,"id":identifier,"name":_safe_label(name),"engine":"sf2",
                  "source":"user-installed","sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
                  "instruments":items}
        (directory/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
        return {"pack_id":identifier,"instruments":len(items)}
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise

def find_fluidsynth(runtime:Path)->str|None:
    locations=[os.environ.get("SONG_HARBOR_FLUIDSYNTH",""),
               str(runtime/"tools"/"fluidsynth"/"bin"/("fluidsynth.exe" if os.name=="nt" else "fluidsynth")),
               shutil.which("fluidsynth") or ""]
    for location in locations:
        if not location:continue
        path=Path(location).expanduser()
        if not path.is_file():continue
        try:
            result=subprocess.run([str(path),"-V"],capture_output=True,text=True,timeout=8,
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if result.returncode==0 and "fluid" in (result.stdout+result.stderr).lower():return str(path.resolve())
        except (OSError,subprocess.TimeoutExpired):pass
    return None

def render_sf2(runtime:Path,instrument:dict,soundfont:Path,midi_bytes:bytes,
               target:Path,duration:float,ffmpeg:str)->None:
    exe=find_fluidsynth(runtime)
    if not exe:raise ValueError("FluidSynth is not installed. Configure SONG_HARBOR_FLUIDSYNTH or install it on PATH.")
    if not soundfont.is_file():raise ValueError("The selected SoundFont is missing")
    if not .1<=duration<=600:raise ValueError("Invalid render duration")
    # External program receives fixed, validated input paths, never user shell text.
    with tempfile.TemporaryDirectory(prefix="sh-sf2-") as tmp:
        root=Path(tmp);midi=root/"notes.mid";raw=root/"render.wav"
        midi.write_bytes(midi_bytes)
        command=[exe,"-n","-i","-F",str(raw),"-r","48000",str(soundfont),str(midi)]
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=min(360,max(30,int(duration*2))),
                                  creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        except subprocess.TimeoutExpired as exc:raise ValueError("SoundFont render timed out") from exc
        if result.returncode or not raw.is_file() or raw.stat().st_size<44:
            raise ValueError("FluidSynth render failed: "+(result.stderr or "")[-250:])
        staged=root/"aligned.wav"
        processed=subprocess.run([ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
                                  "-i",str(raw),"-af",f"apad,atrim=duration={duration:.3f}",
                                  "-ar","48000","-ac","2","-c:a","pcm_s16le",str(staged)],
                                 capture_output=True,text=True,timeout=180,
                                 creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if processed.returncode or not staged.is_file() or staged.stat().st_size<44:
            raise ValueError("Could not align SoundFont render to the selected region")
        target.parent.mkdir(parents=True,exist_ok=True)
        os.replace(staged,target)
