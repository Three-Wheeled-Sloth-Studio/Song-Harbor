"""Non-destructive stereo stem channel extraction using local FFmpeg.

Source stems remain unmodified; each run creates a unique derived-artifact folder.
A stereo file produces two independent mono tracks, never source-separated instruments.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import projects

def split_stems(
    data_root: Path, project: dict[str, Any], filenames: list[str],
    ffmpeg: str, ffprobe: str,
    run: Callable[..., Any] = subprocess.run,
) -> Path:
    folder = data_root / "jobs" / project["id"]
    originals = projects.validated_stems(project, folder)
    by_name = {p.name: p for p in originals}
    if not filenames or len(filenames) != len(set(filenames)) or any(f not in by_name for f in filenames):
        raise ValueError("Select one or more of the six original stems")
    # Maintain canonical stem order, regardless of client order.
    chosen = [p for p in originals if p.name in filenames]
    exports = folder / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    target = exports / ("Channels-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    with tempfile.TemporaryDirectory(prefix=".channels-", dir=exports) as staging_name:
        staging = Path(staging_name)
        tracks: list[dict[str, Any]] = []
        for source in chosen:
            probe = run([
                ffprobe, "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=channels,sample_rate",
                "-of", "json", str(source)
            ], capture_output=True, text=True, check=True, timeout=45,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            streams = json.loads(probe.stdout).get("streams", [])
            if len(streams) != 1 or streams[0].get("channels") != 2:
                raise ValueError(f"{source.name} must contain exactly two audio channels")
            rate = int(streams[0]["sample_rate"])
            name = projects.stem_name(source.name)
            index = projects.ORDER.index(name) + 1
            for channel, number in (("Left", 0), ("Right", 1)):
                output = f"{index:02d} - {name} - {channel}.wav"
                run([
                    ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y",
                    "-i", str(source), "-map", "0:a:0",
                    "-af", f"pan=mono|c0=c{number}", "-c:a", "pcm_f32le",
                    str(staging / output)
                ], capture_output=True, text=True, check=True, timeout=600,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if not (staging / output).is_file() or (staging / output).stat().st_size < 44:
                    raise RuntimeError(f"Failed to render {output}")
                tracks.append({"stem": name, "source": source.name,
                               "channel": channel.lower(), "file": output,
                               "start_seconds": 0.0, "sample_rate_hz": rate})
        manifest = {
            "format": "song-harbor-stereo-channel-split", "version": 1,
            "source_project_id": project["id"], "track_count": len(tracks),
            "sample_format": "32-bit float mono WAV", "tracks": tracks,
            "note": "Derived independent left/right channels, not independent instrument separation."
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (staging / "README.txt").write_text(
            "Song Harbor stereo channel split\n"
            "These files contain unmodified source channels decoded to 32-bit float mono WAV.\n"
            "Left and right are not new instrument stems. Import each at 0:00.\n"
            "Original source files are untouched.\n", encoding="utf-8")
        staging.rename(target)
    return target
