"""Polyphonic arrangement-to-MIDI encoding regression tests (no FluidSynth needed)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import midi_arrangements
import polyphonic_midi

def events(blob:bytes):
    assert blob[:4]==b"MThd" and blob[14:18]==b"MTrk"
    pos=22
    end=pos+int.from_bytes(blob[18:22],"big")
    ticks=0
    result=[]
    while pos<end:
        delay=0
        while True:
            value=blob[pos];pos+=1
            delay=(delay<<7)|(value&127)
            if not value&128:break
        ticks+=delay
        status=blob[pos];pos+=1
        if status==0xff:
            kind=blob[pos];pos+=1
            size=blob[pos];pos+=1
            payload=blob[pos:pos+size];pos+=size
            result.append((ticks,"meta",kind,payload))
        elif status&0xf0 in (0x90,0x80,0xb0):
            a,b=blob[pos:pos+2];pos+=2
            result.append((ticks,status,a,b))
        elif status&0xf0==0xc0:
            result.append((ticks,status,blob[pos]));pos+=1
        else:raise AssertionError(f"Unknown status: {status:x}")
    return result

class PolyphonicMidiTests(unittest.TestCase):
    def score(self):
        return midi_arrangements.create("bass",1.25,4.0,[
            {"pitch":48,"start":0.0,"end":2.0,"velocity":95},
            {"pitch":52,"start":0.5,"end":1.5,"velocity":67},
            {"pitch":55,"start":1.0,"end":3.0,"velocity":75},
            {"pitch":48,"start":2.0,"end":3.2,"velocity":87}
        ])
    def test_chord_overlap_and_note_off_order(self):
        output=polyphonic_midi.to_midi(self.score(),38,12)
        all_events=events(output)
        attacks=[(t,e[2],e[3]) for e in all_events if isinstance(e[1],int) and e[1]&0xf0==0x90]
        releases=[(t,e[2]) for e in all_events if isinstance(e[1],int) and e[1]&0xf0==0x80]
        self.assertEqual(len(attacks),4)
        self.assertEqual(len(releases),4)
        self.assertEqual(attacks[0],(0,48,95))
        # At the same tick, note-off for repeated pitch must precede new note-on.
        boundary=[e[1]&0xf0 for e in all_events if isinstance(e[1],int) and e[0]==1920 and e[2]==48 and e[1]&0xf0 in (0x80,0x90)]
        self.assertEqual(boundary,[0x80,0x90])
        self.assertTrue(any(e[1]==0xb0 and e[2]==32 and e[3]==12 for e in all_events if isinstance(e[1],int)))
        self.assertEqual(all_events[-1][1:3],("meta",0x2f))
        self.assertEqual(all_events[-1][0],3840)
    def test_reproducible_and_persists_unchanged(self):
        score=self.score()
        before=[dict(n) for n in score["notes"]]
        self.assertEqual(polyphonic_midi.to_midi(score,38,12),polyphonic_midi.to_midi(score,38,12))
        self.assertEqual(score["notes"],before)
    def test_same_pitch_overlap_is_rejected(self):
        score=self.score()
        score["notes"][3]["start_sample"]=48000
        with self.assertRaisesRegex(ValueError,"Same-pitch"):polyphonic_midi.to_midi(score,32)
    def test_melodic_channel_ten_rejected(self):
        score=self.score()
        score["notes"][0]["channel"]=9
        with self.assertRaisesRegex(ValueError,"Channel 10"):polyphonic_midi.to_midi(score,32)
    def test_explicit_percussion_mode_uses_channel_ten_without_program_change(self):
        score=midi_arrangements.create("drums",0,2,[
            {"pitch":36,"start":0.0,"end":0.1,"velocity":108},
            {"pitch":38,"start":0.0,"end":0.1,"velocity":90},
            {"pitch":42,"start":0.25,"end":0.35,"velocity":72}])
        for note in score["notes"]:
            note["channel"]=9
        output=polyphonic_midi.to_midi(score,0,percussion=True)
        all_events=events(output)
        attacks=[e for e in all_events if isinstance(e[1],int) and e[1]&0xf0==0x90]
        self.assertEqual({e[2] for e in attacks},{36,38,42})
        self.assertTrue(all(e[1]==0x99 for e in attacks))
        self.assertFalse(any(isinstance(e[1],int) and e[1]&0xf0==0xc0 for e in all_events))
        self.assertEqual(output,polyphonic_midi.to_midi(score,0,percussion=True))

    def test_percussion_mode_rejects_melodic_notes_and_mixed_channels(self):
        score=self.score()
        with self.assertRaisesRegex(ValueError,"channel 10"):
            polyphonic_midi.to_midi(score,0,percussion=True)
        score["notes"][0]["channel"]=9
        with self.assertRaisesRegex(ValueError,"channel 10"):
            polyphonic_midi.to_midi(score,0,percussion=True)
        with self.assertRaisesRegex(ValueError,"Channel 10"):
            polyphonic_midi.to_midi(score,0)
        with self.assertRaisesRegex(ValueError,"boolean"):
            polyphonic_midi.to_midi(score,0,percussion="yes")

    def test_invalid_program_bank_or_tempo(self):
        score=self.score()
        for args in ((128,0,120),(38,16384,120),(38,0,1)):
            with self.assertRaises(ValueError):polyphonic_midi.to_midi(score,*args)
    def test_dense_chord_and_odd_timing(self):
        score=midi_arrangements.create("keys",0,2,[
            {"pitch":pitch,"start":.137,"end":.691,"velocity":50+pitch%30}
            for pitch in range(40,56)])
        output=polyphonic_midi.to_midi(score,42)
        self.assertEqual(len([x for x in events(output) if isinstance(x[1],int) and x[1]&0xf0==0x90]),16)

if __name__=="__main__":unittest.main()
