"""Bounded, read-only discovery and explicit registration of local model checkpoints.

No download, execution, model deserialization, or recursive disk-wide scan.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

import workspace_settings

_LOCK = threading.RLock()
FAMILIES = {
    "moss_music": "MOSS-Music",
    "moss_audio": "MOSS-Audio",
}
MAX_DEPTH = 3
MAX_DIRECTORIES = 400
MAX_SHARDS = 64


def registry_path(app_root: Path) -> Path:
    return workspace_settings.settings_path(app_root).parent / "model-registry.json"


def _load(app_root: Path) -> dict:
    try:
        content = json.loads(registry_path(app_root).read_text(encoding="utf-8"))
        if isinstance(content, dict) and content.get("version") == 1 and isinstance(content.get("models"), dict):
            return content
    except (OSError, ValueError):
        pass
    return {"version": 1, "models": {}}


def _atomic_write(app_root: Path, registry: dict) -> None:
    path = registry_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as output:
            tmp = Path(output.name)
            json.dump(registry, output, indent=2)
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _identify(config: dict) -> str | None:
    types = " ".join(str(config.get(k, "")) for k in ("model_type", "architectures", "auto_map")).lower()
    if "moss_music" in types or "moss-music" in types:
        return "moss_music"
    if "moss_audio" in types or "moss-audio" in types:
        return "moss_audio"
    return None


def inspect(path: Path) -> dict | None:
    """A checkpoint inventory, NOT validation that it will execute or fit memory."""
    folder = path.expanduser().resolve()
    cfg = folder / "config.json"
    if not folder.is_dir() or not cfg.is_file() or cfg.is_symlink() or cfg.stat().st_size > 1024 * 1024:
        return None
    try:
        config = json.loads(cfg.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            return None
    except (OSError, ValueError, UnicodeError):
        return None
    family = _identify(config)
    if not family:
        return None
    index = folder / "model.safetensors.index.json"
    weights = []
    if index.is_file() and not index.is_symlink() and index.stat().st_size < 4 * 1024 * 1024:
        try:
            payload = json.loads(index.read_text(encoding="utf-8"))
            weights = sorted(set(payload["weight_map"].values()))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None
    elif (folder / "model.safetensors").is_file():
        weights = ["model.safetensors"]
    if not weights or len(weights) > MAX_SHARDS:
        return None
    for name in weights:
        if not isinstance(name, str) or not name.endswith(".safetensors") or Path(name).name != name:
            return None
    complete = all((folder / name).is_file() and not (folder / name).is_symlink() for name in weights)
    bytes_present = sum((folder / name).stat().st_size for name in weights if (folder / name).is_file())
    return {"path": str(folder), "name": folder.name, "family": family,
            "files": len(weights), "bytes_present": bytes_present,
            "status": "present-unverified" if complete else "incomplete",
            "runtime": "unconfigured", "loaded": False}


def scan(root: Path) -> list[dict]:
    """At most three directory levels, max 400 directories, no symlink traversal."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        return []
    pending = [(root, 0)]
    found = []
    visited = 0
    while pending and visited < MAX_DIRECTORIES:
        folder, depth = pending.pop(0)
        visited += 1
        candidate = inspect(folder)
        if candidate:
            found.append(candidate)
            continue
        if depth >= MAX_DEPTH:
            continue
        try:
            children = sorted((p for p in folder.iterdir() if p.is_dir() and not p.is_symlink()), key=lambda p: p.name)
        except OSError:
            continue
        pending.extend((p, depth + 1) for p in children[:MAX_DIRECTORIES - visited])
    return found


def list_models(app_root: Path, root: Path) -> dict:
    with _LOCK:
        registry = _load(app_root)
    discovered = scan(root)
    by_path = {item["path"]: item for item in discovered}
    registered = []
    for key, record in registry["models"].items():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            continue
        check = inspect(Path(record["path"]))
        if check is None:
            registered.append({"id": key, "name": record.get("name", key), "path": record["path"],
                               "status": "missing-or-unrecognized", "loaded": False})
        else:
            check["id"] = key
            check["registered"] = True
            registered.append(check)
            by_path.pop(check["path"], None)
    return {"registered": registered, "discovered": list(by_path.values()), "scan_limit": MAX_DIRECTORIES}


def register(app_root: Path, folder: str) -> dict:
    if not isinstance(folder, str) or not folder.strip() or not Path(folder).is_absolute():
        raise ValueError("ERROR: Select an absolute existing model folder. Model not registered.")
    target = Path(folder).expanduser().resolve()
    info = inspect(target)
    if info is None:
        raise ValueError("ERROR: No supported MOSS safetensors checkpoint found. Model not registered.")
    if info["status"] != "present-unverified":
        raise ValueError("ERROR: Checkpoint files are missing. Model not registered.")
    # Stable ID independent of location spelling and controlled by backend.
    import hashlib
    identifier = hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:20]
    with _LOCK:
        registry = _load(app_root)
        registry["models"][identifier] = {"path": str(target), "name": info["name"], "family": info["family"]}
        _atomic_write(app_root, registry)
    return {**info, "id": identifier, "registered": True}


def unregister(app_root: Path, identifier: str) -> None:
    with _LOCK:
        registry = _load(app_root)
        if identifier not in registry["models"]:
            raise ValueError("ERROR: Model is not registered. Nothing changed.")
        del registry["models"][identifier]
        _atomic_write(app_root, registry)
    # Never delete any model files.
