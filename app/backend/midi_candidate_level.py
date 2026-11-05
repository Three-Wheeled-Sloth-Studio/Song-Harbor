"""Conservative, deterministic leveling of newly generated MIDI preview WAVs.

This is a peak headroom lift, not compression or loudness matching. It never
touches the source stems, and it does not amplify silence/noise-only output.
"""
from __future__ import annotations

import math
import os
import tempfile
import wave
from pathlib import Path

import numpy as np

TARGET_PEAK = 0.5  # -6.02 dBFS, leaving room for mix/section automation
MAX_BOOST = 4.0   # +12.04 dB; avoid wild boosts for very quiet patches
MIN_PEAK = 512    # roughly -36 dBFS; lower signals need manual inspection
CHUNK_FRAMES = 65536


def level_candidate_wav(path: Path) -> float:
    """Bounded gain on a 16-bit PCM candidate. Returns applied gain in dB.

    Samples and gain are scanned before writing, so failures leave WAV intact.
    Boost-only: if a patch is already loud enough, do not attenuate it.
    """
    source = Path(path)
    with wave.open(str(source), "rb") as audio:
        if audio.getcomptype() != "NONE" or audio.getsampwidth() != 2 or audio.getnchannels() not in (1, 2):
            raise ValueError("Candidate leveling requires 16-bit mono/stereo PCM WAV")
        params = audio.getparams()
        peak = 0
        while True:
            data = audio.readframes(CHUNK_FRAMES)
            if not data:
                break
            samples = np.frombuffer(data, dtype="<i2").astype(np.int32)
            if samples.size:
                peak = max(peak, int(np.max(np.abs(samples))))
    if peak < MIN_PEAK:
        return 0.0
    gain = min(MAX_BOOST, TARGET_PEAK * 32767 / peak)
    if gain <= 1.0:
        return 0.0
    target = None
    try:
        with tempfile.NamedTemporaryFile(prefix="sh-level-", suffix=".wav", dir=source.parent, delete=False) as handle:
            target = Path(handle.name)
        with wave.open(str(source), "rb") as audio, wave.open(str(target), "wb") as output:
            output.setparams(params)
            while True:
                data = audio.readframes(CHUNK_FRAMES)
                if not data:
                    break
                samples = np.frombuffer(data, dtype="<i2").astype(np.float64)
                adjusted = np.rint(np.clip(samples * gain, -32768, 32767)).astype("<i2")
                output.writeframes(adjusted.tobytes())
        os.replace(target, source)
        return round(20 * math.log10(gain), 2)
    finally:
        if target is not None:
            target.unlink(missing_ok=True)
