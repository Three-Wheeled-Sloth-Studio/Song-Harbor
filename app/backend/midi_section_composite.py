"""Combine saved 48-kHz stereo PCM MIDI section candidates into one sparse stem.

No resampling, no destructive changes to source stems, and no merging of masks.
The single resulting WAV has silence between disjoint musical regions.
"""
from __future__ import annotations
import wave
from pathlib import Path

RATE=48000
FRAME_BYTES=4
MAX_FRAMES=RATE*600

def compose(clips:list[tuple[Path,float,float]],output:Path)->tuple[float,list[dict]]:
    """clips: (source WAV, absolute start seconds, declared duration seconds)."""
    if not 1<=len(clips)<=64:raise ValueError("Select 1 to 64 clips")
    ordered=sorted(clips,key=lambda row:row[1])
    start=round(ordered[0][1]*RATE)
    if start<0:raise ValueError("Invalid first clip timestamp")
    regions=[]
    last_end=0
    for path,seconds,duration in ordered:
        offset=round(seconds*RATE)-start
        if offset<last_end:raise ValueError("Section clips overlap")
        if duration<=0:raise ValueError("Invalid section duration")
        with wave.open(str(path),"rb") as src:
            if src.getnchannels()!=2 or src.getsampwidth()!=2 or src.getframerate()!=RATE or src.getcomptype()!="NONE":
                raise ValueError("Expected 48-kHz stereo PCM16 section render")
            frames=src.getnframes()
            if abs(frames/RATE-duration)>.06:raise ValueError("Section WAV duration mismatches the render metadata")
        last_end=offset+frames
        if last_end>MAX_FRAMES:raise ValueError("Composite exceeds 10-minute limit")
        regions.append({"start_seconds":seconds,"end_seconds":seconds+frames/RATE})
    output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),"wb") as dest:
        dest.setnchannels(2);dest.setsampwidth(2);dest.setframerate(RATE)
        cursor=0
        for (path,seconds,_),region in zip(ordered,regions):
            offset=round(seconds*RATE)-start
            while cursor<offset:
                count=min(65536,offset-cursor)
                dest.writeframesraw(b"\x00"*(count*FRAME_BYTES))
                cursor+=count
            with wave.open(str(path),"rb") as src:
                while frames:=src.readframes(65536):
                    dest.writeframesraw(frames)
                    cursor+=len(frames)//FRAME_BYTES
        dest.writeframes(b"")
    return start/RATE,regions
