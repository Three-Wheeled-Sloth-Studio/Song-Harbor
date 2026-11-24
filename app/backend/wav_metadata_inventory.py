"""Read-only bounded inventory of RIFF/WAV container chunks, never tag values."""
from __future__ import annotations

import struct
from pathlib import Path

MAX_CHUNKS = 256
METADATA = {"LIST", "ID3 ", "id3 ", "bext", "iXML", "axml", "cue ", "smpl", "cart", "INFO", "DISP"}
AUDIO = {"fmt ", "data", "fact", "ds64"}


def inspect_wav(path: Path) -> dict:
    size = path.stat().st_size
    result = {"filename": path.name, "container": "unknown", "chunks": [],
              "metadata_chunks": 0, "status": "ok", "message": ""}
    if size < 12:
        return {**result, "status": "unsupported", "message": "File is too short for RIFF/WAV"}
    with path.open("rb") as stream:
        header = stream.read(12)
        if header[:4] not in (b"RIFF", b"RF64") or header[8:12] != b"WAVE":
            return {**result, "status": "unsupported", "message": "Not a supported RIFF/WAV container"}
        result["container"] = header[:4].decode("ascii")
        offset = 12
        for _ in range(MAX_CHUNKS):
            if offset == size:
                break
            if offset + 8 > size:
                result["status"] = "malformed"
                result["message"] = "Incomplete chunk header"
                break
            stream.seek(offset)
            chunk = stream.read(8)
            tag = chunk[:4].decode("ascii", errors="replace")
            length = struct.unpack("<I", chunk[4:])[0]
            end = offset + 8 + length + (length & 1)
            if end > size:
                # RF64 data length may be represented as 0xffffffff; its
                # replacement length requires parsing ds64, which is not done here.
                result["status"] = "unresolved" if result["container"] == "RF64" and length == 0xffffffff else "malformed"
                result["message"] = "Chunk length extends beyond file; inspect with a container-aware tool"
                break
            category = "audio" if tag in AUDIO else "metadata" if tag in METADATA else "other"
            result["chunks"].append({"id": tag, "bytes": length, "category": category})
            result["metadata_chunks"] += category == "metadata"
            offset = end
        else:
            result["status"] = "limited"
            result["message"] = "Chunk count exceeded bounded inventory limit"
    return result
