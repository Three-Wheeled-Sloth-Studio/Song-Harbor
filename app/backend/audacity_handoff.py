"""Safe Audacity import handoff and best-effort Windows foreground activation.

LOF is Audacity's documented List of Files import format (3.x). Audacity 4
support must be established with an installed 4.x smoke test; don't claim that
spawning a process proves that files were imported.
No scripting pipe, desktop keystrokes, or Audacity project files are created.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

STEM_ORDER = ("Vocals", "Drums", "Bass", "Guitar", "Piano", "Other")


def validate_bundle(folder: Path) -> list[Path]:
    """Only hand off six original, ordered WAV exports described by our manifest."""
    folder = folder.resolve(strict=True)
    manifest_file = folder / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("target") != "audacity" or manifest.get("track_count") != 6:
        raise ValueError("Prepare an Audacity stem bundle before launching")
    tracks = manifest.get("tracks")
    if not isinstance(tracks, list) or len(tracks) != 6:
        raise ValueError("The Audacity bundle has an invalid track list")
    paths: list[Path] = []
    for expected, track in zip(STEM_ORDER, tracks):
        if not isinstance(track, dict) or track.get("name") != expected or track.get("start_seconds") != 0.0:
            raise ValueError("The Audacity bundle track order or alignment is invalid")
        filename = track.get("file")
        if not isinstance(filename, str) or not filename.startswith(expected_number(expected) + " - "):
            raise ValueError("An Audacity stem filename is invalid")
        candidate = (folder / filename).resolve()
        if candidate.parent != folder or candidate.suffix.lower() != ".wav" or not candidate.is_file():
            raise ValueError("An Audacity stem is missing or outside the export folder")
        paths.append(candidate)
    if len(set(paths)) != 6:
        raise ValueError("Audacity stem paths are duplicated")
    return paths


def expected_number(name: str) -> str:
    return f"{STEM_ORDER.index(name) + 1:02d}"


def make_lof(folder: Path) -> Path:
    """Create LOF file with six aligned audio tracks; never alter stem WAV files."""
    stem_paths = validate_bundle(folder)
    # Windows paths cannot contain quotes; still reject them and line breaks
    # explicitly to avoid accidentally creating extra LOF commands.
    for path in stem_paths:
        if any(char in str(path) for char in ('"', '\r', '\n')):
            raise ValueError("Unsupported path character in Audacity import")
    # LOF paths relative to its folder avoid non-ASCII Windows path encoding issues.
    lines = ["# Song Harbor six-stem Audacity handoff", "window"]
    lines.extend(f'file "{path.name}" offset 0' for path in stem_paths)
    output = folder / "Song Harbor - Import six stems.lof"
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                            dir=folder, suffix=".lof.tmp", delete=False) as tmp:
        temp = Path(tmp.name)
        tmp.write("\n".join(lines) + "\n")
    try:
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return output


def _foreground_audacity(executable: Path, prefer_pid: int, timeout: float = 14.0) -> bool:
    """Foreground only a visible top-level window owned by the verified executable.

    A new invocation may forward LOF to an already-running Audacity instance.
    In that case, the process ID can differ, so verify the owning process path.
    Do not steal focus from arbitrary applications just because their title
    contains the text 'Audacity'.
    """
    if os.name != "nt":
        return False

    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                      wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

    expected = os.path.normcase(str(executable.resolve()))
    path_cache: dict[int, bool] = {}

    def matches_process(pid: int) -> bool:
        if pid in path_cache:
            return path_cache[pid]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            path_cache[pid] = False
            return False
        try:
            name = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(name))
            ok = bool(kernel32.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(length)))
            path_cache[pid] = ok and os.path.normcase(name.value) == expected
            return path_cache[pid]
        finally:
            kernel32.CloseHandle(handle)

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        windows: list[tuple[int, int]] = []

        @EnumWindowsProc
        def enumerate_window(hwnd: int, unused: int) -> bool:
            if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value or not matches_process(pid.value):
                return True
            windows.append((int(hwnd), int(pid.value)))
            return True

        user32.EnumWindows(enumerate_window, 0)
        windows.sort(key=lambda pair: pair[1] != prefer_pid)
        if windows:
            hwnd = windows[0][0]
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            if user32.SetForegroundWindow(hwnd):
                return True
        time.sleep(0.3)
    return False


def launch_audacity(executable: str, folder: Path) -> dict[str, Any]:
    """Request a new Audacity import and asynchronously focus Audacity's window."""
    executable_path = Path(executable).resolve(strict=True)
    bundle = make_lof(folder)
    process = subprocess.Popen(
        [str(executable_path), str(bundle)],
        cwd=str(executable_path.parent),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    # Importing six long WAVs is asynchronous in Audacity. Return immediately;
    # focus may require retrying while Audacity initializes.
    threading.Thread(target=_foreground_audacity,
                     args=(executable_path, process.pid),
                     daemon=True).start()
    return {
        "status": "started",
        "target": "audacity",
        "import_file": str(bundle),
        "import_requested": True,
        "message": "Audacity launched with the six-stem import list. Check that six tracks appear; Audacity 4 support needs local confirmation.",
    }
