"""Bounded, cached waveform overview peaks for source stem WAVs.

Peaks are presentation data, not audio rendering or an audio analysis classifier.
No entire decoded recording is loaded into the browser.
"""
from __future__ import annotations
import array
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

SAMPLE_RATE = 4000
BIN_COUNT = 2048

def calculate(path: Path, duration: float, ffmpeg: str) -> dict[str, Any]:
    if not (math.isfinite(duration) and duration > 0):
        raise ValueError("A positive source duration is needed for waveform rendering")
    samples_per_bucket = max(1, math.ceil(duration * SAMPLE_RATE / BIN_COUNT))
    mins = [32767] * BIN_COUNT
    maxs = [-32768] * BIN_COUNT
    count = 0
    args = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(path),
            "-map", "0:a:0", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1"]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        assert proc.stdout is not None
        carry = b""
        while True:
            block = proc.stdout.read(65536)
            if not block:
                break
            values = array.array("h")
            payload = carry + block
            usable = len(payload) - len(payload) % 2
            values.frombytes(payload[:usable])
            carry = payload[usable:]
            if os.sys.byteorder != "little":
                values.byteswap()
            for val in values:
                index = min(count // samples_per_bucket, BIN_COUNT - 1)
                if val < mins[index]: mins[index] = val
                if val > maxs[index]: maxs[index] = val
                count += 1
        if proc.wait(timeout=30) != 0:
            raise RuntimeError("Waveform decode failed")
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    finally:
        if proc.stdout:
            proc.stdout.close()
    if count == 0:
        raise ValueError("Empty audio stream")
    # Sample rate conversion for overview only; peak cache is not for mastering meters.
    return {"version": 1, "bins": BIN_COUNT, "duration_seconds": duration,
            "min": [round(v / 32768.0, 4) if v != 32767 else 0.0 for v in mins],
            "max": [round(v / 32768.0, 4) if v != -32768 else 0.0 for v in maxs]}

def get_or_create(path: Path, cache_path: Path, duration: float, ffmpeg: str) -> dict[str, Any]:
    source = path.stat()
    signature = {"size": source.st_size, "mtime_ns": source.st_mtime_ns}
    if cache_path.is_file():
        try:
            entry = json.loads(cache_path.read_text(encoding="utf-8"))
            if entry.get("source") == signature and entry.get("data", {}).get("bins") == BIN_COUNT:
                return entry["data"]
        except (OSError, ValueError, TypeError):
            pass
    data = calculate(path, duration, ffmpeg)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=cache_path.parent, encoding="utf-8",
                                     suffix=".tmp", delete=False) as f:
        json.dump({"source": signature, "data": data}, f, separators=(",", ":"))
        temporary = Path(f.name)
    try:
        os.replace(temporary, cache_path)
    finally:
        temporary.unlink(missing_ok=True)
    return data
