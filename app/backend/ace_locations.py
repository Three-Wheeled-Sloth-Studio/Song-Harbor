"""Bounded local ACE-Step installation discovery, with optional explicit override.

Avoid recursive disk traversal and avoid guessing that an arbitrary Python
installation is ACE. Discovery is intentionally restricted to familiar app
folders, sibling checkouts, configured paths, and shallow named directories.
"""
from __future__ import annotations

import os
import re
import string
from pathlib import Path

ACE_NAME = re.compile(r"^(?:ACE[-_ ]?Step(?:[-_ ]?1(?:[._-]5)?)?|ACE-Step-1\.5)$", re.I)


def valid_installation(folder: Path) -> bool:
    python = folder / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return python.is_file() and (folder / "acestep" / "api_server.py").is_file()


def candidate_roots(app_root: Path, home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    roots = [
        app_root.parent, app_root.parent / "Tools",
        home / "Apps", home / "Apps" / "Tools",
        home / "Tools", home / "Documents", home / "Documents" / "Apps",
    ]
    if os.name == "nt":
        # Target common application folders on every mounted drive, not a
        # machine-specific letter. Avoid recursive scans of whole drives.
        for letter in string.ascii_uppercase:
            volume = Path(f"{letter}:/")
            if volume.exists():
                roots.extend([volume / "Apps", volume / "Apps" / "Tools",
                              volume / "Tools"])
    return list(dict.fromkeys(path.expanduser() for path in roots))


def discover_installation(app_root: Path, configured: str | None = None) -> Path | None:
    """Find a real checkout; explicit settings take precedence over discovery."""
    override = configured or os.environ.get("SONG_HARBOR_ACE_HOME")
    if override:
        folder = Path(override).expanduser().resolve()
        return folder if valid_installation(folder) else None
    for root in candidate_roots(app_root):
        if not root.is_dir():
            continue
        if valid_installation(root):
            return root.resolve()
        # First look for a conventional checkout name without enumeration.
        for name in ("ACE-Step-1.5", "ACE-Step", "ACE-Step-1_5", "ACE_Step_1.5"):
            path = root / name
            if valid_installation(path):
                return path.resolve()
        # Shallow discovery allows variants such as ACE-Step-1.5-main.
        try:
            matches = sorted((path for path in root.iterdir()
                              if path.is_dir() and path.name.lower().startswith(("ace-step", "ace_step", "acestep"))),
                             key=lambda path: path.name.lower())
        except OSError:
            continue
        for path in matches[:30]:
            if valid_installation(path):
                return path.resolve()
    return None
