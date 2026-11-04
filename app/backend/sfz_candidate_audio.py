"""Render SFZ MIDI into a candidate-compatible, aligned WAV.

The caller owns candidate metadata. Raw renders and temporary MIDI stay in a
temporary directory; the published candidate WAV is replaced only on success.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
import wave
from pathlib import Path
import sfz_render_adapter


def render_candidate(
    midi_bytes: bytes,
    sfz_path: Path,
    candidate_wav: Path,
    duration: float,
    ffmpeg: str,
    config_root: Path,
) -> None:
    if not 0.1 <= duration <= 600:
        raise ValueError("SFZ preview duration must be between 0.1 and 600 seconds")
    if not midi_bytes.startswith(b"MThd"):
        raise ValueError("Expected a valid standard MIDI header")
    candidate_wav.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sh-sfz-", dir=candidate_wav.parent) as tmp:
        scratch=Path(tmp)
        midi=scratch/"notes.mid"
        midi.write_bytes(midi_bytes)
        raw=scratch/"raw.wav"
        sfz_render_adapter.render_sfz(midi,sfz_path,raw,config_root=config_root,
                                      timeout_seconds=min(360,max(30,int(duration*2))))
        aligned=scratch/"aligned.wav"
        completed=subprocess.run([
            ffmpeg,"-hide_banner","-loglevel","error","-nostdin","-y",
            "-i",str(raw),"-af",f"apad,atrim=duration={duration:.3f}",
            "-ar","48000","-ac","2","-c:a","pcm_s16le",str(aligned)
        ],capture_output=True,text=True,timeout=180,
          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if completed.returncode or not aligned.is_file() or aligned.stat().st_size < 44:
            raise ValueError("Could not align SFZ preview to MIDI duration")
        try:
            with wave.open(str(aligned), "rb") as wav:
                if (wav.getframerate() != 48000 or wav.getnchannels() != 2 or
                        wav.getsampwidth() != 2 or
                        abs(wav.getnframes()/48000-duration) > 0.05):
                    raise ValueError("SFZ preview must be aligned 48-kHz stereo PCM WAV")
        except (EOFError, wave.Error) as exc:
            raise ValueError("SFZ preview is not a valid PCM WAV") from exc
        # os.replace publishes only the finished candidate. Source stem untouched.
        os.replace(aligned,candidate_wav)
