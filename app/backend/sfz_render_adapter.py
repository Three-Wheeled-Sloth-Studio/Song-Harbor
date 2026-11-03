"""Isolated offline SFZ render adapter.

This module is deliberately NOT wired into project acceptance until Windows
sampler, pack and preview QA pass. The caller owns all file locations.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import wave
from pathlib import Path


class SFZRenderError(RuntimeError):
    """Actionable local renderer failure."""


def locate_renderer(configured: str | None = None) -> Path:
    """Resolve a locally installed sfizz_render executable without a shell."""
    candidate = configured or os.environ.get("SONG_HARBOR_SFIZZ_RENDER")
    if candidate:
        result = Path(candidate).expanduser().resolve()
    else:
        found = shutil.which("sfizz_render") or shutil.which("sfizz-render")
        if not found:
            raise SFZRenderError(
                "sfizz_render is not installed. Configure SONG_HARBOR_SFIZZ_RENDER "
                "to point to the offline renderer executable."
            )
        result = Path(found).resolve()
    if not result.is_file():
        raise SFZRenderError("Configured sfizz_render executable does not exist")
    return result


def render_sfz(
    midi_file: Path,
    sfz_file: Path,
    output_file: Path,
    *,
    renderer: str | None = None,
    timeout_seconds: int = 180,
    sample_rate: int = 48000,
) -> Path:
    """Render trusted server-owned MIDI through a user-installed SFZ bank.

    Rendering is to an unpublished destination; caller must move to the
    candidate store only after additional waveform and project checks.
    """
    if sample_rate != 48000:
        raise SFZRenderError("Song Harbor SFZ renders require 48000 Hz")
    if not 1 <= timeout_seconds <= 600:
        raise SFZRenderError("SFZ render timeout outside allowed bounds")
    midi = Path(midi_file).resolve(strict=True)
    sfz = Path(sfz_file).resolve(strict=True)
    output = Path(output_file).resolve()
    if midi.suffix.lower() not in (".mid", ".midi") or sfz.suffix.lower() != ".sfz":
        raise SFZRenderError("Expected MIDI and SFZ instrument files")
    if not midi.is_file() or not sfz.is_file() or output in (midi, sfz):
        raise SFZRenderError("Invalid SFZ render paths")
    if output.exists():
        raise SFZRenderError("Refusing to overwrite an existing output")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(locate_renderer(renderer)), "--sfz", str(sfz),
        "--midi", str(midi), "--wav", str(output),
        "--samplerate", str(sample_rate),
    ]
    completed = False
    try:
        result = subprocess.run(
            command, shell=False, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
        if result.returncode != 0:
            raise SFZRenderError(
                "sfizz_render failed (exit %d): %s" %
                (result.returncode, (result.stderr or result.stdout)[-1000:])
            )
        with wave.open(str(output), "rb") as audio:
            if audio.getframerate() != sample_rate or audio.getnchannels() != 2:
                raise SFZRenderError("Renderer output is not 48-kHz stereo WAV")
            if audio.getnframes() <= 0 or audio.getsampwidth() not in (2, 3, 4):
                raise SFZRenderError("Renderer output has invalid PCM format or duration")
        completed = True
        return output
    except subprocess.TimeoutExpired as exc:
        raise SFZRenderError("SFZ renderer timed out") from exc
    except (OSError, EOFError, wave.Error) as exc:
        raise SFZRenderError("SFZ renderer output could not be validated") from exc
    finally:
        # Failed or incomplete output is never treated as a candidate.
        # Successful output is retained for the caller's separate review.
        if not completed:
            output.unlink(missing_ok=True)
