"""Optional real-FFmpeg fidelity regression for extracted stereo channel reconstruction.

Runs only where ffmpeg and ffprobe are on PATH; fake-command unit tests remain
portable. A split must retain left/right sample alignment and unity gain.
"""
import array
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import channel_split
import projects

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg unavailable")
class ChannelRoundTripTests(unittest.TestCase):
    def test_reconstructed_pcm_tracks_match_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)
            ident="abcdef012345"
            stems=data/"jobs"/ident/"stems"
            stems.mkdir(parents=True)
            files=[]
            length=1000
            source_pairs=[((i*97)%20000-10000,(i*67)%16000-8000) for i in range(length)]
            raw=b"".join(struct.pack("<hh",a,b) for a,b in source_pairs)
            for name in projects.ORDER:
                filename=f"source_({name})_htdemucs_6s.wav"
                with wave.open(str(stems/filename),"wb") as wf:
                    wf.setnchannels(2);wf.setsampwidth(2);wf.setframerate(48000);wf.writeframes(raw)
                files.append(filename)
            project={"id":ident,"files":files,"stems":projects.default_settings(files)}
            exported=channel_split.split_stems(data,project,[files[0]],shutil.which("ffmpeg"),shutil.which("ffprobe"))
            channels=[]
            for side in ("Left","Right"):
                output=exported/f"01 - Vocals - {side}.wav"
                pcm=subprocess.run([shutil.which("ffmpeg"),"-v","error","-i",str(output),
                                    "-f","s16le","-acodec","pcm_s16le","-ac","1","pipe:1"],
                                    capture_output=True,check=True).stdout
                samples=array.array("h");samples.frombytes(pcm)
                if sys.byteorder!="little":samples.byteswap()
                channels.append(samples)
            self.assertEqual(length,len(channels[0]))
            self.assertEqual(length,len(channels[1]))
            # Audio source was PCM16. 32-bit float extraction and PCM16 decoding
            # should preserve every original sample to within one quantization unit.
            self.assertLessEqual(max(abs(channels[0][i]-a) for i,(a,_) in enumerate(source_pairs)),1)
            self.assertLessEqual(max(abs(channels[1][i]-b) for i,(_,b) in enumerate(source_pairs)),1)
            self.assertEqual(raw,(stems/files[0]).read_bytes()[-len(raw):])

if __name__=="__main__":
    unittest.main()
