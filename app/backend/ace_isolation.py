"""Fast, conservative leakage screening for native ACE Lego candidates.

Checks whether a supposed isolated instrument is a near-copy of its input.
High correlation triggers review, not proof of which instruments are present.
"""
from __future__ import annotations

import math
import subprocess
from array import array
from pathlib import Path

SIMILARITY_THRESHOLD = 0.80
SEGMENT_SECONDS = 5.0
SAMPLE_RATE = 4000


def _mono_excerpt(ffmpeg: str, audio: Path, start: float) -> array:
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-ss", f"{start:.3f}", "-t", str(SEGMENT_SECONDS),
            "-i", str(audio), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
            "-f", "f32le", "pipe:1"]
    result = subprocess.run(
        args, capture_output=True, check=True, timeout=35,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    values = array("f")
    values.frombytes(result.stdout)
    return values


def correlation(first: array, second: array) -> float:
    """Normalized waveform correlation for two same-clock PCM excerpts."""
    n = min(len(first), len(second))
    if n < SAMPLE_RATE * 2:
        raise ValueError("Insufficient audio for similarity assessment")
    a = first[:n]
    b = second[:n]
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    ss_a = ss_b = dot = 0.0
    for x, y in zip(a, b):
        x -= mean_a
        y -= mean_b
        ss_a += x*x
        ss_b += y*y
        dot += x*y
    if ss_a < 1e-8 or ss_b < 1e-8:
        return 0.0
    return dot / math.sqrt(ss_a*ss_b)


def assess_context_leakage(ffmpeg: str, context: Path,
                           generated: Path, duration: float) -> dict:
    """Flag likely source-mix duplication at multiple distributed excerpts.

    This is a conservative identical-timeline test, not perceptual audio
    isolation verification. A passing score does not certify stem purity.
    """
    if duration < SEGMENT_SECONDS + 1.0:
        return {"status": "unknown", "reason": "Not enough audio for isolation check"}
    anchors = sorted(set(round(max(0.0, (duration-SEGMENT_SECONDS)*fraction), 3)
                         for fraction in (0.12, 0.38, 0.7)))
    scores = []
    try:
        for anchor in anchors:
            a = _mono_excerpt(ffmpeg, context, anchor)
            b = _mono_excerpt(ffmpeg, generated, anchor)
            scores.append(round(correlation(a, b), 4))
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError, OverflowError) as exc:
        return {"status": "unknown", "reason": str(exc)[:180]}
    matching = sum(score >= SIMILARITY_THRESHOLD for score in scores)
    status = "suspected_source_leakage" if matching >= 2 else "not_detected"
    return {"status": status, "correlations": scores,
            "threshold": SIMILARITY_THRESHOLD, "matching_windows": matching,
            "note": "Waveform correlation is a leakage screen, not a full isolation certification"}
