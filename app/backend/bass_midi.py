"""CPU-only experimental monophonic bass transcription and bowed-string audition.

No model download, GPU use, network dependency, or mutation of original stems.
First-pass bowed tone is synthesized, NOT an acoustic cello sample.
"""
from __future__ import annotations
import json
import math
import subprocess
import uuid
import wave
from pathlib import Path

import numpy as np

RATE=12000
OUTPUT_RATE=48000
MAX_SECONDS=45.0  # decoded chunk maximum
MAX_REGION_SECONDS=600.0  # whole-song/section-to-section safety ceiling
MAX_NOTES=4000
MIDI_LOW=28
MIDI_HIGH=76

def validate_notes(notes: list[dict], duration: float) -> list[dict]:
    if not isinstance(notes,list) or len(notes)>MAX_NOTES:
        raise ValueError("Maximum 4000 notes")
    clean=[]
    for row in notes:
        if not isinstance(row,dict):
            raise ValueError("Invalid MIDI note")
        try:
            pitch=row["pitch"]
            start=float(row["start"])
            end=float(row["end"])
            velocity=int(row.get("velocity",85))
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError("Invalid note fields") from exc
        if (type(pitch) is not int or not MIDI_LOW<=pitch<=MIDI_HIGH or
            not math.isfinite(start) or not math.isfinite(end) or
            start<0 or end-start<.06 or end>duration+.002 or not 1<=velocity<=127):
            raise ValueError("Note pitch, timing or velocity out of range")
        clean.append({"pitch":pitch,"start":round(start,3),"end":round(end,3),"velocity":velocity})
    clean.sort(key=lambda n:(n["start"],n["end"]))
    if any(b["start"]<a["end"]-.002 for a,b in zip(clean,clean[1:])):
        raise ValueError("First-pass bass transcription is monophonic; notes cannot overlap")
    return clean

def decode_excerpt(source:Path,start:float,duration:float,ffmpeg:str)->np.ndarray:
    if duration<=0 or duration>MAX_SECONDS:
        raise ValueError("Select a region of at most 45 seconds")
    command=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-ss",f"{start:.3f}",
             "-i",str(source),"-t",f"{duration:.3f}","-vn","-ac","1","-ar",str(RATE),
             "-f","f32le","pipe:1"]
    proc=subprocess.run(command,capture_output=True,timeout=40,check=False)
    if proc.returncode or not proc.stdout:
        raise ValueError("Could not decode bass excerpt")
    pcm=np.frombuffer(proc.stdout,dtype="<f4").copy()
    if len(pcm)>int((MAX_SECONDS+.1)*RATE):
        raise ValueError("Decoded excerpt exceeds processing limit")
    if not np.isfinite(pcm).all():
        raise ValueError("Invalid audio sample values")
    return pcm

def transcribe(pcm:np.ndarray)->list[dict]:
    """Harmonic pitch scoring + energy gate. Intended for separated bass, not chords."""
    if len(pcm)<RATE//2:
        raise ValueError("At least 0.5s of source audio required")
    frame=4096
    hop=256
    # Center each analysis window on its audio timestamp so note endings are
    # not truncated by half the FFT window (about 170 ms at 12 kHz).
    padded=np.pad(pcm,(frame//2,frame//2))
    starts=np.arange(0,len(pcm),hop,dtype=np.int64)
    pitches=np.arange(MIDI_LOW,MIDI_HIGH+1,dtype=np.int32)
    frequencies=440.0*2.0**((pitches-69)/12.0)
    window=np.hanning(frame).astype(np.float32)
    picked=[]
    energy=[]
    for at in starts:
        segment=padded[at:at+frame]
        if len(segment)<frame:
            segment=np.pad(segment,(0,frame-len(segment)))
        rms=float(np.sqrt(np.mean(segment*segment)+1e-12))
        spectrum=np.abs(np.fft.rfft(segment*window))
        # Harmonic salience prevents frequently choosing the second harmonic.
        values=np.zeros(len(pitches),dtype=np.float64)
        for harmonic,weight in ((1,1.0),(2,.75),(3,.4),(4,.22)):
            bins=np.rint(frequencies*harmonic*frame/RATE).astype(int)
            bins=np.clip(bins,1,len(spectrum)-2)
            values+=weight*np.maximum.reduce([spectrum[bins-1],spectrum[bins],spectrum[bins+1]])
        chosen=int(pitches[int(np.argmax(values))])
        picked.append(chosen)
        energy.append(rms)
    peak=max(energy,default=0.0)
    if peak<1e-5:return []
    threshold=max(.002,peak*.13)
    # Median of 5 frames suppresses single-frame octave glitches.
    smoothed=[]
    for i,value in enumerate(picked):
        neighbors=[picked[j] for j in range(max(0,i-2),min(len(picked),i+3))
                   if energy[j]>=threshold]
        smoothed.append(int(np.median(neighbors)) if neighbors else -1)
    # Consecutive pitch runs with ~90ms minimum notes.
    groups=[]
    current=-1
    begin=0
    for i,pitch in enumerate(smoothed+[-1]):
        note=pitch if i<len(energy) and energy[i]>=threshold else -1
        if note!=current:
            if current>=0 and (i-begin)*hop/RATE>=.09:
                groups.append({"pitch":current,"start":round(begin*hop/RATE,3),
                               "end":round(min(len(pcm)/RATE,i*hop/RATE),3),
                               "velocity":85})
            begin=i
            current=note
    # Join immediately adjacent same-pitch notes, preserving rests.
    merged=[]
    for note in groups:
        if merged and merged[-1]["pitch"]==note["pitch"] and note["start"]-merged[-1]["end"]<.08:
            merged[-1]["end"]=note["end"]
        else:merged.append(note)
    return validate_notes(merged[:MAX_NOTES],len(pcm)/RATE)

def transcribe_region(source:Path,start:float,duration:float,ffmpeg:str)->list[dict]:
    """Decode bounded 30s chunks and combine one monophonic MIDI timeline.

    Short regions run through the original single-chunk path unchanged.
    Never load the full-song PCM into memory.
    """
    if not math.isfinite(start) or start<0 or not .5<=duration<=MAX_REGION_SECONDS:
        raise ValueError("Region must be 0.5 to 600 seconds")
    if duration<=MAX_SECONDS:
        return transcribe(decode_excerpt(source,start,duration,ffmpeg))
    notes=[]
    offset=0.0
    while offset<duration-.001:
        length=min(30.0,duration-offset)
        if length<.5:
            break
        piece=transcribe(decode_excerpt(source,start+offset,length,ffmpeg))
        for item in piece:
            note=dict(item)
            note["start"]=round(note["start"]+offset,3)
            note["end"]=round(min(duration,note["end"]+offset),3)
            if notes and note["start"]<notes[-1]["end"]:
                note["start"]=notes[-1]["end"]
            if note["end"]-note["start"]<.06:
                continue
            if (notes and notes[-1]["pitch"]==note["pitch"]
                    and note["start"]-notes[-1]["end"]<=.11):
                notes[-1]["end"]=note["end"]
            else:
                notes.append(note)
            if len(notes)>MAX_NOTES:
                raise ValueError("More than 4000 estimated notes; select a smaller region")
        offset+=length
    return validate_notes(notes,duration)


def render_bowed_wav(path:Path,notes:list[dict],duration:float)->None:
    """Original deterministic bowed-string approximation, not sampled cello."""
    notes=validate_notes(notes,duration)
    samples=int(math.ceil(duration*OUTPUT_RATE))
    if samples>int(MAX_REGION_SECONDS*OUTPUT_RATE):
        raise ValueError("Audio duration exceeds limit")
    audio=np.zeros(samples,dtype=np.float32)
    for note in notes:
        a=round(note["start"]*OUTPUT_RATE)
        b=min(samples,round(note["end"]*OUTPUT_RATE))
        if b<=a:continue
        t=np.arange(b-a,dtype=np.float32)/OUTPUT_RATE
        frequency=440.0*2**((note["pitch"]-69)/12)
        # Bow onset, steady friction and slow vibrato. Smooth at edges.
        phase=2*np.pi*frequency*(t+.0015*np.sin(2*np.pi*5*t))
        body=(.74*np.sin(phase)+.32*np.sin(2*phase)+.19*np.sin(3*phase)+
              .10*np.sin(4*phase)+.045*np.sin(5*phase))
        attack=np.minimum(1,t/.095)
        release=np.minimum(1,np.maximum(0,(b-a)/OUTPUT_RATE-t)/.11)
        env=np.minimum(attack,release)
        audio[a:b]+=body*env*min(1,note["velocity"]/100)*.2
    peak=float(np.max(np.abs(audio))) if len(audio) else 0
    if peak>.93:audio*=.93/peak
    pcm=np.rint(np.clip(audio,-1,1)*32767).astype("<i2")
    path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),"wb") as dest:
        dest.setnchannels(1);dest.setsampwidth(2);dest.setframerate(OUTPUT_RATE)
        dest.writeframes(pcm.tobytes())

def _variable(number:int)->bytes:
    data=[number&127]
    number >>=7
    while number:
        data.insert(0,(number&127)|128)
        number >>=7
    return bytes(data)

def midi_bytes(notes:list[dict],duration:float,bpm:int=120)->bytes:
    """Standard MIDI 1, one channel/program, tempo and absolute note timing."""
    notes=validate_notes(notes,duration)
    ticks_per_beat=480
    ticks_per_second=bpm*ticks_per_beat/60
    events=[(0,0,b"\xff\x51\x03"+int(60000000/bpm).to_bytes(3,"big")),
            (0,1,b"\xc0\x2a")] # GM program 43 (zero-indexed 42), cello
    for n in notes:
        events.append((round(n["start"]*ticks_per_second),2,bytes([0x90,n["pitch"],n["velocity"]])))
        events.append((round(n["end"]*ticks_per_second),0,bytes([0x80,n["pitch"],0])))
    events.sort(key=lambda e:(e[0],e[1]))
    track=bytearray()
    tick=0
    for at,_,data in events:
        track+=_variable(at-tick)+data
        tick=at
    track+=b"\x00\xff\x2f\x00"
    return (b"MThd"+(6).to_bytes(4,"big")+b"\x00\x00\x00\x01"+
            ticks_per_beat.to_bytes(2,"big")+b"MTrk"+len(track).to_bytes(4,"big")+track)

def candidate_folder(song_folder:Path,candidate_id:str)->Path:
    if len(candidate_id)!=32 or any(c not in "0123456789abcdef" for c in candidate_id):
        raise ValueError("Invalid candidate ID")
    return song_folder/"generated"/"bass-midi"/candidate_id

def write_json(path:Path,record:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    # Existing candidate metadata is overwritten atomically, sources never touched.
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(record,indent=2),encoding="utf-8")
    temp.replace(path)

def read_json(song_folder:Path,candidate_id:str)->dict:
    path=candidate_folder(song_folder,candidate_id)/"candidate.json"
    if not path.is_file():raise ValueError("Candidate unavailable")
    record=json.loads(path.read_text(encoding="utf-8"))
    if record.get("candidate_id")!=candidate_id:raise ValueError("Candidate identity mismatch")
    return record
