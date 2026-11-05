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

# GM-compatible initial targets; these pitches were also verified against the
# published Muldjord SFZ keymap. They are still *estimates*, not identified hits.
LANES={
    36:"Kick (estimated)",
    38:"Snare (estimated)",
    42:"Closed hat (estimated)",
    41:"Low tom (estimated)",
    49:"Crash cymbal (estimated)",
}


def classify(pcm:np.ndarray)->list[dict]:
    """Onset-first, multi-band percussion hypotheses.

    Not a trained separator. Band-local spectral flux and post-attack decay
    identify likely acoustic families. Simultaneous strong kick and
    snare/bright events may produce multiple notes. The original WAV is the
    authority; user should inspect every estimated lane before replacing it.
    """
    pcm=np.asarray(pcm,dtype=np.float32)
    if pcm.ndim!=1 or not np.isfinite(pcm).all():
        raise ValueError("Invalid mono drum excerpt")
    if len(pcm)<RATE//2:return []
    window=np.hanning(FRAME).astype(np.float32)
    padded=np.pad(pcm,(FRAME//2,FRAME//2))
    count=int(math.ceil(len(pcm)/HOP))
    bands=np.zeros((count,5),dtype=np.float32)
    freqs=np.fft.rfftfreq(FRAME,1/RATE)
    masks=[
        freqs<135,                                  # kick body
        (freqs>=135)&(freqs<530),                  # tom/snare lower body
        (freqs>=530)&(freqs<2200),                 # snare crack
        (freqs>=2200)&(freqs<4500),                # hat/cymbal
        freqs>=4500,                               # bright metal/air
    ]
    for i in range(count):
        frame=padded[i*HOP:i*HOP+FRAME]
        spectrum=np.abs(np.fft.rfft(frame*window))
        power=spectrum*spectrum
        for j,mask in enumerate(masks):
            bands[i,j]=float(np.sum(power[mask]))
    if float(np.max(bands))<1e-7:return []
    # Take the square root before differencing to avoid one loud snare
    # suppressing all other drum attacks in the same phrase.
    amplitude=np.sqrt(bands)
    novelty=np.maximum(np.diff(amplitude,axis=0,prepend=amplitude[:1]),0.)
    broad=novelty.sum(axis=1)
    high=novelty[:,3]+novelty[:,4]
    low=novelty[:,0]
    middle=novelty[:,1]+novelty[:,2]
    peak=float(np.max(broad))
    floor=max(peak*.038,1e-5)
    candidates=[]
    min_gap=max(1,round(.065*RATE/HOP))
    for i in range(2,count-2):
        if broad[i]<max(floor,float(np.median(broad[max(0,i-12):i+13]))*2.25):
            continue
        if broad[i]<broad[i-1] or broad[i]<=broad[i+1]:
            continue
        if candidates and i-candidates[-1]<min_gap:
            if broad[i]>broad[candidates[-1]]:
                candidates[-1]=i
            continue
        candidates.append(i)

    notes=[]
    last_by_pitch={}
    for i in candidates:
        # Use the whole local attack rather than a single FFT bin; this
        # limits false "only snare" decisions for layered kick+snare hits.
        attack=novelty[i:min(count,i+5)].sum(axis=0).astype(np.float64)
        total=float(attack.sum())
        if total<=1e-6:continue
        frac=attack/total
        bass=float(frac[0])
        body=float(frac[1])
        crack=float(frac[2])
        brilliance=float(frac[3]+frac[4])
        # A sustained bright decay is more likely a cymbal than a short hat.
        now=float(np.sum(amplitude[i,3:]))
        later=float(np.mean(np.sum(amplitude[min(count-1,i+10):min(count,i+19),3:],axis=1))) \
            if i+10<count else 0.
        long_bright=now>1e-5 and later/now>.35
        # Conservative assignment; do not hallucinate multiple drum hits
        # merely because every acoustic sample has both lows and highs.
        pitches=[]
        if bass>=.26 and bass>brilliance*.65:
            pitches.append(36)
            if crack>=.25 and float(low[i])>.0 and float(middle[i])>=float(low[i])*.42:
                pitches.append(38)
        elif body>=.45 and crack<.20 and brilliance<.22:
            pitches.append(41)
        elif brilliance>=.43 and bass<.17:
            pitches.append(49 if long_bright else 42)
            if crack>=.30 and brilliance<.56:
                pitches.append(38)
        elif body>=.37 and crack<.18 and bass<.19:
            pitches.append(41)
        else:
            pitches.append(38)
        onset=max(0.,i*HOP/RATE-.012)
        strength=min(1.,math.sqrt(float(broad[i])/max(floor,peak*.35)))
        for pitch in dict.fromkeys(pitches):
            # Lane-local repeat suppression only. Different instruments may
            # overlap at the same acoustic attack.
            if onset-last_by_pitch.get(pitch,-1e6)<.06:
                continue
            end=min(len(pcm)/RATE,onset+(.14 if pitch in (41,49) else .1))
            if end-onset<.025:continue
            vel=max(38,min(122,round(52+strength*60-(7 if pitch==42 else 0))))
            notes.append({"pitch":pitch,"start":round(onset,4),"end":round(end,4),
                          "velocity":vel})
            last_by_pitch[pitch]=onset
    return sorted(notes,key=lambda row:(row["start"],row["pitch"]))


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
