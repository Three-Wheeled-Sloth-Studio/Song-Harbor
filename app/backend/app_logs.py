"""Canonical application log locations.

Log data belongs beside the Song Harbor runtime, not under model weights or
source checkouts. No migration/deletion of historical logs is automatic.
"""
from __future__ import annotations

from pathlib import Path
import os

LOG_FILES = frozenset({
    "moss-wsl.log", "moss-runtime.log", "moss-setup.log",
    "moss-repair.log", "wsl-install.log",
})


def log_path(app_root: Path, filename: str) -> Path:
    if filename not in LOG_FILES:
        raise ValueError("Unsupported log filename.")
    return app_root.resolve() / "logs" / filename


def open_log(app_root: Path, filename: str):
    path = log_path(app_root, filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("ab")


def open_logs_folder(app_root: Path) -> dict:
    """Request the OS to open the one canonical log folder after a user click."""
    folder = app_root.resolve() / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        raise RuntimeError("Open logs folder is available in the Windows application only.")
    os.startfile(str(folder))
    return {"requested": True, "directory": str(folder)}
