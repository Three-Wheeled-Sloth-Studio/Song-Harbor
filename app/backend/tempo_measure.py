"""Offline onset-based tempo candidates. No model, MIDI mutation or beat-grid claims.

Uses log-spectral positive flux from the actual Song Harbor offline render.
Autocorrelation per overlapping window proposes pulse rates; half/double-time
ambiguity is kept. This is a measurement heuristic, not a ground-truth tempo.
"""
from __future__ import annotations

import math
import uuid
import wave
from pathlib import Path

import numpy as np

METHOD = "spectral-onset-autocorr-v2"
RATE = 48000
HOP = 512
FFT = 2048
WINDOW_SECONDS = 12
STEP_SECONDS = 6
MAX_SECONDS = 900


def _blocks(path: Path):
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 2 or wav.getsampwidth() != 3:
            raise ValueError("ERROR: Expected 24-bit stereo analysis WAV.")
        rate = wav.getframerate()
        if not 8000 <= rate <= 192000:
            raise ValueError("ERROR: Unsupported audio sample rate.")
        frames = wav.getnframes()
        if not 1 <= frames <= rate * MAX_SECONDS:
            raise ValueError("ERROR: Tempo measurement requires 15 minutes or less.")
        while True:
            raw = wav.readframes(32768)
            if not raw:
                break
            data = np.frombuffer(raw, dtype=np.uint8)
            if data.size % 6:
                raise ValueError("ERROR: Misaligned 24-bit PCM frames.")
            samples = data.reshape(-1, 2, 3).astype(np.int32)
            values = samples[:, :, 0] | (samples[:, :, 1] << 8) | (samples[:, :, 2] << 16)
            values = (values ^ 0x800000) - 0x800000
            yield (values[:, 0].astype(np.float32) + values[:, 1].astype(np.float32)) / (2 * 8388608), rate


def novelty(path: Path) -> tuple[np.ndarray, int, float]:
    """Bounded frame-by-frame streaming FFT; never loads an entire song PCM."""
    carry = np.zeros(0, dtype=np.float32)
    prev = None
    values: list[float] = []
    window = np.hanning(FFT).astype(np.float32)
    total = 0
    rate = None
    for mono, rate in _blocks(path):
        total += len(mono)
        carry = np.concatenate((carry, mono))
        while len(carry) >= FFT:
            spectrum = np.abs(np.fft.rfft(carry[:FFT] * window)).astype(np.float32)
            # Log compression limits domination by a loud bass tone.
            current = np.log1p(spectrum * 12)
            if prev is None:
                values.append(0.0)
            else:
                # Positive spectral flux captures attacks without requiring
                # a genre-specific drum classifier.
                values.append(float(np.maximum(current - prev, 0).mean()))
            prev = current
            carry = carry[HOP:]
    if rate is None:
        raise ValueError("ERROR: No audio samples available.")
    return np.asarray(values, dtype=np.float32), rate, total / rate


def _rhythmic_support(onsets: np.ndarray, frame_rate: float, bpm: float) -> bool:
    """Require repeated attacks on a consistent phase, not merely an ACF peak.

    Sparse pads, isolated drum fills and evolving textures can yield strong
    autocorrelation but do not necessarily establish a sustained beat.
    """
    if onsets.size < 4:
        return False
    positive = np.maximum(onsets - float(np.median(onsets)), 0)
    floor = float(np.median(positive))
    spread = float(np.median(np.abs(positive - floor)))
    threshold = max(float(np.percentile(positive, 82)), floor + 2.5 * spread, 1e-7)
    min_gap = max(1, round(frame_rate * .13))
    peaks = []
    for i in range(1, len(positive) - 1):
        if positive[i] < threshold or positive[i] <= positive[i - 1] or positive[i] < positive[i + 1]:
            continue
        if peaks and i - peaks[-1] < min_gap:
            if positive[i] > positive[peaks[-1]]:
                peaks[-1] = i
        else:
            peaks.append(i)
    if len(peaks) < 7:
        return False
    period = 60 * frame_rate / bpm
    # Evaluate phase locking, allowing attacks at subdivisions, but demand
    # several *different* beats, not a single isolated fill cluster.
    phases = np.asarray(peaks, dtype=np.float64) % period
    distances = np.abs(phases[:, None] - phases[None, :])
    distances = np.minimum(distances, period - distances)
    support = np.sum(distances <= period * .13, axis=1)
    best = int(np.argmax(support))
    aligned = [peaks[j] for j in range(len(peaks)) if distances[best, j] <= period * .13]
    if len(aligned) < max(6, math.ceil(len(peaks) * .56)):
        return False
    occupied = {round((p - aligned[0]) / period) for p in aligned}
    if len(occupied) < 6:
        return False
    # A real pulse should extend across much of a window.
    if aligned[-1] - aligned[0] < frame_rate * 5.5:
        return False
    return True


def _window_candidates(curve: np.ndarray, frame_rate: float) -> tuple[float | None, list[float], str]:
    if curve.size < frame_rate * 4:
        return None, [], "too-short"
    # Robust baseline removal and clipping prevent one sharp transient
    # from dominating a 12s interval.
    baseline = float(np.percentile(curve, 35))
    x = np.maximum(curve - baseline, 0)
    upper = float(np.percentile(x, 95))
    if upper <= 1e-6:
        return None, [], "low-onset-activity"
    x = np.minimum(x, upper)
    x -= x.mean()
    if float(np.sqrt(np.mean(x * x))) <= 1e-6:
        return None, [], "low-onset-activity"
    corr = np.correlate(x, x, mode="full")[len(x)-1:]
    if corr[0] <= 1e-8:
        return None, [], "low-periodicity"
    corr = corr / (corr[0] + 1e-9)
    lo = max(1, int(frame_rate * 60 / 210))
    hi = min(len(corr)-1, int(frame_rate * 60 / 50))
    if hi <= lo:
        return None, [], "too-short"
    peaks = []
    for lag in range(lo+1, hi):
        if corr[lag] >= corr[lag-1] and corr[lag] >= corr[lag+1]:
            bpm = 60 * frame_rate / lag
            # First candidate and musically related ambiguous pulses are exposed.
            peaks.append((float(corr[lag]), round(bpm, 2)))
    peaks.sort(reverse=True)
    if not peaks or peaks[0][0] < 0.12:
        return None, [], "low-periodicity"
    strongest, bpm = peaks[0]
    # Do not accept autocorrelation of smooth timbral changes or occasional
    # fills without repeated, phase-coherent onset evidence.
    if not _rhythmic_support(curve, frame_rate, bpm):
        return None, [], "insufficient-beat-evidence"
    candidates = []
    for strength, other in peaks:
        if strength < strongest * .72:
            break
        if all(abs(other - existing) > 4 for existing in candidates):
            candidates.append(other)
        if len(candidates) >= 4:
            break
    alternatives = list(candidates[1:])
    for ratio in (0.5, 2):
        other = round(bpm * ratio, 2)
        if 20 <= other <= 320 and all(abs(other - x) > 2 for x in [bpm, *alternatives]):
            alternatives.append(other)
    # Ranking strength is intentionally not advertised as calibrated confidence.
    return bpm, alternatives[:8], "periodicity-detected"


def measure(path: Path, *, offset_seconds: float = 0) -> dict:
    if not math.isfinite(offset_seconds) or offset_seconds < 0:
        raise ValueError("ERROR: Invalid snapshot time offset.")
    flux, rate, duration = novelty(path)
    frame_rate = rate / HOP
    win = max(1, round(WINDOW_SECONDS * frame_rate))
    step = max(1, round(STEP_SECONDS * frame_rate))
    starts = list(range(0, max(1, len(flux) - win + 1), step))
    if len(flux) > win and starts[-1] + win < len(flux):
        starts.append(len(flux) - win)
    findings = []
    for begin in starts:
        end = min(len(flux), begin + win)
        bpm, alternatives, reason = _window_candidates(flux[begin:end], frame_rate)
        start_seconds = offset_seconds + begin / frame_rate
        end_seconds = offset_seconds + min(duration, end / frame_rate)
        start_sample = round(start_seconds * RATE)
        end_sample = round(end_seconds * RATE)
        if end_sample <= start_sample:
            continue
        findings.append({
            "id": uuid.uuid4().hex, "start_sample": start_sample,
            "end_sample": end_sample, "bpm": bpm, "alternatives": alternatives,
            "status": "unverified", "confidence": None,
            "method": METHOD, "provider": "Song Harbor DSP",
            "evidence": reason,
        })
    return {"method": METHOD, "duration_seconds": duration, "windows": findings,
            "note": "Candidate pulse rates only; sparse passages and subdivisions can mislead the estimator."}
