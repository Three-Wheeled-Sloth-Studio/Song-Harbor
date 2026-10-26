"""ACE HTTP transport for prepared Song Harbor context and candidate results.

ACE must already be running. No automatic model downloads or process management.
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from ace_adapter import AceClient, AceError, normalize_poll, unwrap

MAX_CONTEXT_BYTES = 96 * 1024 * 1024
MAX_AUDIO_BYTES = 256 * 1024 * 1024
TASK_ID = re.compile(r"^[0-9a-fA-F-]{16,64}$")


def _headers(client: AceClient) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if client.api_key:
        headers["Authorization"] = "Bearer " + client.api_key
    return headers


def submit_instrument(client: AceClient, context_file: Path, model: str, prompt: str,
                 seed: int, bpm: int | None = None, key: str = "",
                 meter: str = "4/4", duration: float | None = None, *, task_type: str = "cover",
                 track_name: str = "") -> str:
    """Multipart ctx_audio submission: ACE owns its temporary upload copy."""
    if not context_file.is_file() or not 44 <= context_file.stat().st_size <= MAX_CONTEXT_BYTES:
        raise ValueError("Context must be a valid-size WAV file")
    if context_file.suffix.lower() != ".wav":
        raise ValueError("ACE context must be a WAV")
    if not model.startswith("acestep-v15-") or not prompt.strip():
        raise ValueError("Model and prompt required")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("Invalid seed")
    if task_type not in ("cover", "lego"):
        raise ValueError("Unsupported ACE instrumental task type")
    if task_type == "lego":
        from instrument_generation import normalize_instrument
        if model != "acestep-v15-base":
            raise ValueError("Native Lego requires the loaded ACE Base model")
        track_name = normalize_instrument(track_name)
    fields: dict[str, Any] = {
        "task_type": task_type, "model": model, "prompt": prompt, "lyrics": "[Instrumental]",
        "thinking": False, "use_random_seed": False, "seed": seed,
        "inference_steps": 50 if task_type == "lego" else 8, "guidance_scale": 7.0, "batch_size": 1,
        "audio_format": "wav", "use_tiled_decode": True,
        "time_signature": meter, "key_scale": key,
    }
    if task_type == "lego":
        fields["track_name"] = track_name
        fields["instruction"] = "Generate the " + track_name.upper() + " track based on the audio context:"
        # Base Lego expects the target-instrument direction in prompt/caption.
        # No cover/noise or cover-mix parameters may leak into this request.
        fields["repainting_start"] = 0.0
        fields["repainting_end"] = -1
        fields["chunk_mask_mode"] = "explicit"
    else:
        fields["audio_cover_strength"] = 0.8
        fields["cover_noise_strength"] = 0.2
    if bpm is not None:
        if not isinstance(bpm, int) or not 30 <= bpm <= 300:
            raise ValueError("BPM must be an integer from 30-300")
        fields["bpm"] = bpm
    if duration is not None:
        if not 0 < duration <= 240:
            raise ValueError("Invalid generation duration")
        fields["audio_duration"] = duration
    boundary = "songharbor" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                      f"{str(value).lower() if isinstance(value, bool) else value}\r\n").encode("utf-8"))
    parts.append((f"--{boundary}\r\nContent-Disposition: form-data; name=\"ctx_audio\"; "
                  f"filename=\"context.wav\"\r\nContent-Type: audio/wav\r\n\r\n").encode("utf-8"))
    parts.append(context_file.read_bytes())
    parts.append(f"\r\n--{boundary}--\r\n".encode("ascii"))
    headers = _headers(client)
    headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    request = urllib.request.Request(client.base + "/release_task", data=b"".join(parts),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=max(30, client.timeout)) as response:
            data = json.loads(response.read(2_000_000))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise AceError("ACE task submission failed") from exc
    submitted = unwrap(data)
    if not isinstance(submitted, dict) or not TASK_ID.fullmatch(str(submitted.get("task_id", ""))):
        raise AceError("ACE did not return a valid task ID")
    return submitted["task_id"]


def submit_cover(client: AceClient, context_file: Path, model: str, prompt: str,
                 seed: int, bpm: int | None = None, key: str = "",
                 meter: str = "4/4", duration: float | None = None) -> str:
    return submit_instrument(client, context_file, model, prompt, seed,
                             bpm=bpm, key=key, meter=meter, duration=duration)

def poll_cover(client: AceClient, task_id: str) -> dict[str, Any]:
    if not TASK_ID.fullmatch(task_id):
        raise ValueError("Invalid ACE task ID")
    return normalize_poll(client.request("/query_result", {"task_id_list": [task_id]}), task_id)


def download_candidate(client: AceClient, asset_uri: str, destination: Path) -> Path:
    """Accept only ACE-owned relative /v1/audio links; never arbitrary URLs."""
    parts = urllib.parse.urlsplit(asset_uri)
    if parts.scheme or parts.netloc or parts.fragment or parts.path != "/v1/audio":
        raise ValueError("ACE result is not an allowed audio download path")
    query = urllib.parse.parse_qs(parts.query)
    if not query.get("path") or len(query["path"]) != 1:
        raise ValueError("ACE audio link lacks a single path parameter")
    url = client.base + asset_uri
    request = urllib.request.Request(url, headers=_headers(client), method="GET")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + "." + uuid.uuid4().hex + ".tmp")
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=max(30, client.timeout)) as response, temporary.open("wb") as output:
            if not response.headers.get("Content-Type", "").lower().startswith(("audio/", "application/octet-stream")):
                raise AceError("ACE returned a non-audio candidate")
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_AUDIO_BYTES:
                    raise AceError("ACE candidate exceeds audio size limit")
                output.write(chunk)
        if size < 44:
            raise AceError("ACE returned empty candidate audio")
        os.replace(temporary, destination)
        return destination
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AceError("ACE candidate download failed") from exc
    finally:
        temporary.unlink(missing_ok=True)
