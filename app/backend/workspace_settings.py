"""Machine-local working file location settings.

Changes are staged for next launch. Never migrate files or point at an unverified
cloud directory implicitly. User must explicitly adopt/copy existing projects.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

def settings_path(root: Path) -> Path:
    return root / "config" / "settings.json"

def read(root: Path) -> dict:
    try:
        data = json.loads(settings_path(root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, OSError, ValueError):
        return {}

def configured_data(root: Path) -> Path:
    value = read(root).get("working_files_directory")
    if isinstance(value, str) and value.strip() and Path(value).is_absolute():
        return Path(value).expanduser().resolve()
    return (root / "data").resolve()

def choose_directory() -> str | None:
    if os.name != "nt":
        raise RuntimeError("Native directory picker currently requires Windows")
    import tkinter
    from tkinter import filedialog
    window = tkinter.Tk()
    window.withdraw()
    window.attributes("-topmost", True)
    try:
        return filedialog.askdirectory(title="Select Song Harbor working files folder") or None
    finally:
        window.destroy()

def validate_directory(root: Path, value: str) -> Path:
    if not value.strip() or not Path(value).is_absolute():
        raise ValueError("Select an absolute working directory")
    target = Path(value).expanduser().resolve()
    forbidden = [root.resolve(), Path.home().resolve()]
    if target == Path(target.anchor) or target in forbidden:
        raise ValueError("Choose a dedicated subfolder, not a drive root, home directory, or application root")
    if (target / ".git").exists() or (target / ".venv").exists():
        raise ValueError("Choose a data folder, not a source checkout or Python environment")
    if target.exists() and not target.is_dir():
        raise ValueError("Working files location is not a directory")
    # Don't create anything during validation, but confirm an existing path is writable.
    if target.exists() and not os.access(target, os.W_OK):
        raise ValueError("Working files directory is not writable")
    return target

def stage(root: Path, value: str) -> dict:
    target = validate_directory(root, value)
    cfg = read(root)
    cfg["working_files_directory"] = str(target)
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as handle:
        json.dump(cfg, handle, indent=2)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"configured_directory": str(target), "restart_required": True,
            "migration_performed": False}

def status(root: Path, active: Path) -> dict:
    return {"active_directory": str(active.resolve()),
            "configured_directory": str(configured_data(root)),
            "default_directory": str((root / "data").resolve()),
            "restart_required": configured_data(root) != active.resolve(),
            "migration_performed": False,
            "warning": "Changing the location does not move existing projects. "
                       "Do not run Song Harbor from two computers against a synced "
                       "SQLite library at once; close Song Harbor and allow sync to finish "
                       "before switching computers. Keep independent backups."}
