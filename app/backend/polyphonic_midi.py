"""Deterministic Standard MIDI export for saved polyphonic arrangements.

Events derive from immutable revision snapshots; the original transcription
and source stems are never modified. All times use the shared 48-kHz clock.
"""
from __future__ import annotations
from collections import defaultdict
import midi_arrangements

PPQ=480
BPM=120

def vlq(value:int)->bytes:
    if not 0<=value<=0x0fffffff:raise ValueError("MIDI delta is outside VLQ range")
    items=[value&0x7f]
    value>>=7
    while value:
        items.insert(0,0x80|(value&0x7f))
        value>>=7
    return bytes(items)

def to_midi(asset:dict,program:int,bank:int=0,bpm:int=BPM,*,percussion:bool=False)->bytes:
    data=midi_arrangements.validate(asset)
    if type(program)!=int or not 0<=program<=127:raise ValueError("Invalid program")
    if type(bank)!=int or not 0<=bank<=16383:raise ValueError("Invalid bank")
    if type(bpm)!=int or not 20<=bpm<=300:raise ValueError("Invalid tempo")
    # MIDI channel 10 (zero-based 9) is percussion, not pitched instruments.
    # Drum arrangements must opt in; never silently reinterpret melodic notes.
    if type(percussion) is not bool:raise ValueError("Percussion mode must be boolean")
    if percussion:
        if any(n["channel"]!=9 for n in data["notes"]):
            raise ValueError("Percussion arrangement requires MIDI channel 10 for every note")
    elif any(n["channel"]==9 for n in data["notes"]):
        raise ValueError("Channel 10 is reserved for drums; choose a melodic channel")
    by_key=defaultdict(list)
    for note in data["notes"]:
        by_key[(note["channel"],note["pitch"])].append(note)
    # Same-pitch overlaps on one MIDI channel have ambiguous note-off behavior.
    for family in by_key.values():
        previous_end=-1
        for note in sorted(family,key=lambda x:x["start_sample"]):
            if note["start_sample"]<previous_end:
                raise ValueError("Same-pitch overlapping notes on one MIDI channel require separate channels")
            previous_end=note["end_sample"]
    def tick(sample:int)->int:
        return round(sample*bpm*PPQ/(60*midi_arrangements.RATE))
    channels={n["channel"] for n in data["notes"]} or {0}
    events=[(0,0,b"\xff\x51\x03"+round(60000000/bpm).to_bytes(3,"big"))]
    for channel in sorted(channels):
        if percussion:
            # GM percussion selection uses channel 10 and key number; a
            # melodic program change would misrepresent the kit mapping.
            continue
        events.extend([(0,1,bytes([0xb0|channel,0,(bank>>7)&127])),
                       (0,2,bytes([0xb0|channel,32,bank&127])),
                       (0,3,bytes([0xc0|channel,program]))])
    for note in data["notes"]:
        channel=note["channel"]
        events.append((tick(note["start_sample"]),5,bytes([0x90|channel,note["pitch"],note["velocity"]])))
        events.append((tick(note["end_sample"]),4,bytes([0x80|channel,note["pitch"],0])))
    events.sort(key=lambda e:(e[0],e[1],e[2]))
    track=bytearray()
    last=0
    for at,_,event in events:
        track+=vlq(at-last)+event
        last=at
    end=tick(data["duration_samples"])
    track+=vlq(max(0,end-last))+b"\xff\x2f\x00"
    return (b"MThd"+(6).to_bytes(4,"big")+b"\x00\x00\x00\x01"+
            PPQ.to_bytes(2,"big")+b"MTrk"+len(track).to_bytes(4,"big")+track)
