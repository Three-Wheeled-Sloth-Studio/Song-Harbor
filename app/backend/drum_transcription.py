"""CPU-only exploratory drum transient transcription.

Not a trained drum classifier. Detects attacks in bounded, overlapping chunks,
uses spectral energy ratios to propose GM-labeled kick/snare/hat lanes, and
preserves onset timing. Result MUST be reviewed and kit keymap verified before
rendering. Never quantizes, overwrites sources, or invents a completed take.
"""
from __future__ import annotations
import math
import subprocess
from pathlib import Path
import numpy as np

RATE=12000
FRAME=512
HOP=128
MAX_REGION=600.0
MAX_NOTES=16000
# These pitches are *provisional* GM lane targets, not a Big Rusty keymap.
LANES={36:"Kick (estimated)",38:"Snare (estimated)",42:"Closed hat (estimated)"}


def classify(pcm:np.ndarray)->list[dict]:
    """Spectral-flux onset detector with coarse percussion-family estimates."""
    pcm=np.asarray(pcm,dtype=np.float32)
    if pcm.ndim!=1 or not np.isfinite(pcm).all():
        raise ValueError("Invalid mono drum excerpt")
    if len(pcm)<RATE//2:return []
    window=np.hanning(FRAME).astype(np.float32)
    padded=np.pad(pcm,(FRAME//2,FRAME//2))
    count=int(math.ceil(len(pcm)/HOP))
    bands=np.zeros((count,3),dtype=np.float32)
    energy=np.zeros(count,dtype=np.float32)
    freqs=np.fft.rfftfreq(FRAME,1/RATE)
    masks=[freqs<170,(freqs>=170)&(freqs<2500),freqs>=2500]
    for i in range(count):
        frame=padded[i*HOP:i*HOP+FRAME]
        spectrum=np.abs(np.fft.rfft(frame*window))
        # Squared magnitude helps distinguish kick low end and bright hats.
        power=spectrum*spectrum
        for j,mask in enumerate(masks):
            bands[i,j]=float(np.sum(power[mask]))
        energy[i]=float(np.sum(power))
    if float(np.max(energy))<1e-7:return []
    # Positive spectral flux rather than global RMS catches rapid drum hits.
    flux=np.maximum(bands[1:]-bands[:-1],0).sum(axis=1)
    flux=np.r_[0,flux]
    floor=max(float(np.max(flux))*.055,1e-7)
    peaks=[]
    min_gap=int(.075*RATE/HOP)
    for i in range(2,count-2):
        local=flux[max(0,i-12):min(count,i+13)]
        threshold=max(floor,float(np.median(local))*2.7)
        if flux[i]<threshold or flux[i]<flux[i-1] or flux[i]<=flux[i+1]:
            continue
        if peaks and i-peaks[-1]<min_gap:
            if flux[i]>flux[peaks[-1]]:peaks[-1]=i
            continue
        peaks.append(i)
    notes=[]
    for i in peaks:
        # Attack spectrum; multiple frequency families may be simultaneous.
        segment=bands[i:min(count,i+7)].sum(axis=0).astype(np.float64)
        total=float(segment.sum())
        if total<=1e-9:continue
        low,mid,high=(segment/total).tolist()
        if low>=.27 and low>high*.9:
            pitch=36
        elif high>.48 and low<.18:
            pitch=42
        else:
            pitch=38
        onset=max(0.0,(i*HOP/RATE)-.012)
        end=min(len(pcm)/RATE,onset+.105)
        if end-onset<.025:continue
        strength=min(1.,math.sqrt(float(flux[i])/max(floor,float(np.max(flux))*.3)))
        velocity=max(45,min(120,round(55+strength*52)))
        notes.append({"pitch":pitch,"start":round(onset,4),"end":round(end,4),
                      "velocity":velocity})
    return notes


def transcribe_region(source:Path,start:float,duration:float,ffmpeg:str)->list[dict]:
    if not math.isfinite(start) or not math.isfinite(duration) or start<0 or not .5<=duration<=MAX_REGION:
        raise ValueError("Select a drum region between 0.5 and 600 seconds")
    notes=[]
    # Overlap avoids cut-off attacks at chunk edges, without loading entire track.
    offset=0.
    while offset<duration-.001:
        length=min(20.,duration-offset)
        if length<.5:break
        decode_start=max(0.,offset-.20)
        decode_end=min(duration,offset+length+.20)
        cmd=[ffmpeg,"-hide_banner","-loglevel","error","-nostdin",
             "-ss",f"{start+decode_start:.4f}","-i",str(source),
             "-t",f"{decode_end-decode_start:.4f}","-ac","1","-ar",str(RATE),
             "-f","f32le","pipe:1"]
        output=subprocess.run(cmd,capture_output=True,check=False,timeout=45)
        if output.returncode or not output.stdout:raise ValueError("Could not decode drum stem")
        pcm=np.frombuffer(output.stdout,dtype="<f4")
        if pcm.size>int(21*RATE):raise ValueError("Drum chunk exceeds allowed size")
        for row in classify(pcm):
            at=row["start"]+decode_start
            if at<offset-.0001 or at>=offset+length-.0001:continue
            note={**row,"start":round(at,4),"end":round(min(duration,row["end"]+decode_start),4)}
            if note["end"]<=note["start"]:continue
            notes.append(note)
            if len(notes)>MAX_NOTES:raise ValueError("Too many drum hits; select a smaller region")
        offset+=length
    return sorted(notes,key=lambda row:(row["start"],row["pitch"]))
