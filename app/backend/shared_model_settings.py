"""Shared model storage preference. No model downloads, scans or runtime loads."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import workspace_settings


def configured_root(app_root: Path) -> Path:
    configured = workspace_settings.read(app_root).get("shared_model_directory")
    if isinstance(configured, str) and configured.strip() and Path(configured).is_absolute():
        return Path(configured).expanduser().resolve()
    return Path(os.environ.get("SONG_HARBOR_MODELS", str(app_root / "models"))).expanduser().resolve()


def validate_root(app_root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        raise ValueError("ERROR: Choose an absolute model directory. Location not saved.")
    target = Path(value).expanduser().resolve()
    app = app_root.resolve()
    home = Path.home().resolve()
    data = workspace_settings.configured_data(app_root)
    if target == Path(target.anchor) or target in (app, home, data) or app in target.parents or data in target.parents:
        raise ValueError("ERROR: Choose a dedicated model folder outside the application and working files. Location not saved.")
    if (target / ".git").exists() or (target / ".venv").exists():
        raise ValueError("ERROR: This looks like a source checkout or environment. Location not saved.")
    if target.exists() and not target.is_dir():
        raise ValueError("ERROR: Model location is not a directory. Location not saved.")
    if target.exists() and not os.access(target, os.W_OK):
        raise ValueError("ERROR: Model location is not writable. Location not saved.")
    return target


def status(app_root: Path, active_root: Path) -> dict:
    target = configured_root(app_root)
    return {
        "configured_directory": str(target),
        "active_directory": str(active_root.resolve()),
        "restart_required": target != active_root.resolve(),
        "exists": target.is_dir(),
        "downloads_enabled": False,
        "models_loaded": False,
    }


def save(app_root: Path, value: str) -> dict:
    target = validate_root(app_root, value)
    cfg = workspace_settings.read(app_root)
    cfg["shared_model_directory"] = str(target)
    path = workspace_settings.settings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(cfg, handle, indent=2)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return status(app_root, Path(os.environ.get("SONG_HARBOR_MODELS", str(app_root / "models"))))


def browse() -> str | None:
    return workspace_settings.choose_directory()


def configured_runtime_python(app_root: Path) -> str:
    value = workspace_settings.read(app_root).get("moss_runtime_python", "")
    return value if isinstance(value, str) else ""


def save_runtime_python(app_root: Path, value: str) -> str:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute() or not candidate.is_file() or candidate.name.lower() not in ("python.exe", "python3.exe", "python"):
        raise ValueError("ERROR: Select an existing Python executable from an isolated SGLang environment. Runtime not saved.")
    cfg = workspace_settings.read(app_root)
    cfg["moss_runtime_python"] = str(candidate.resolve())
    path = workspace_settings.settings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(cfg, handle, indent=2)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return str(candidate.resolve())
