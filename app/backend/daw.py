"""Configurable DAW adapters: locate existing installations, remember paths and launch.

Audacity and Waveform are optional external editors. Song Harbor never requires
either to export a portable stem bundle. No executable is run during discovery.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

import dependencies

TARGETS = {
    "waveform": {
        "name": "Waveform Free", "free": True,
        "download_url": "https://www.tracktion.com/products/waveform-free",
        "format": "six-stem-wav-folder",
    },
    "audacity": {
        "name": "Audacity", "free": True,
        "download_url": "https://www.audacityteam.org/download/windows/",
        "format": "six-stem-wav-folder",
    },
}
EXECUTABLE_NAMES = {
    "waveform": ("Waveform.exe", "Waveform 14.exe", "Waveform 13.exe", "Waveform 12.exe", "Waveform Free.exe"),
    "audacity": ("Audacity.exe",),
}


def target(target_id: str) -> dict:
    if target_id not in TARGETS:
        raise ValueError("Unsupported DAW target")
    return {"id": target_id, **TARGETS[target_id]}


def verify_executable(target_id: str, chosen: Path) -> Path | None:
    target(target_id)
    path = chosen.expanduser()
    names = EXECUTABLE_NAMES[target_id]
    if path.is_dir():
        candidates = [path / name for name in names]
        if target_id == "waveform":
            candidates.extend(path.glob("Waveform*.exe"))
    else:
        candidates = [path]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        basename = candidate.name.lower()
        valid = (basename == "audacity.exe") if target_id == "audacity" else bool(re.fullmatch(r"Waveform.*\.exe", candidate.name, re.I))
        if valid:
            return candidate.resolve()
    return None


def verify_waveform(path: Path) -> Path | None:
    return verify_executable("waveform", path)


def configured(root: Path, target_id: str = "waveform") -> str | None:
    target(target_id)
    entries = dependencies.load_config(root).get("daws", {})
    item = entries.get(target_id, {}) if isinstance(entries, dict) else {}
    return item.get("executable") if isinstance(item, dict) else None


def selected_target(root: Path) -> str:
    data = dependencies.load_config(root)
    chosen = data.get("selected_daw", "waveform")
    return chosen if chosen in TARGETS else "waveform"


def _write_settings(root: Path, data: dict) -> None:
    file = dependencies.config_file(root)
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_name(file.name + "." + uuid.uuid4().hex[:8] + ".tmp")
    try:
        temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temp, file)
    finally:
        temp.unlink(missing_ok=True)


def select_target(root: Path, target_id: str) -> str:
    target(target_id)
    data = dependencies.load_config(root)
    data["selected_daw"] = target_id
    _write_settings(root, data)
    return target_id


def set_location(root: Path, chosen: str, target_id: str = "waveform") -> str:
    executable = verify_executable(target_id, Path(chosen))
    if not executable:
        raise ValueError(f"Select the installed {target(target_id)['name']} executable or its folder")
    data = dependencies.load_config(root)
    daws = data.setdefault("daws", {})
    if not isinstance(daws, dict):
        data["daws"] = daws = {}
    daws[target_id] = {"executable": str(executable), "source": "user"}
    _write_settings(root, data)
    return str(executable)


def common_locations(target_id: str = "waveform") -> list[Path]:
    target(target_id)
    candidates: list[Path] = []
    for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                  os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")):
        if not value:
            continue
        root = Path(value)
        if target_id == "audacity":
            candidates.extend((root / "Audacity", root / "Audacity 4", root / "Audacity 3",
                               root / "Programs" / "Audacity",
                               root / "Microsoft" / "WinGet" / "Links",
                               root / "Microsoft" / "WindowsApps"))
        else:
            candidates.extend((root / "Tracktion", root / "Tracktion Software",
                               root / "Waveform", root / "Waveform Free"))
            for parent in (root / "Tracktion", root / "Tracktion Software"):
                if parent.is_dir():
                    candidates.extend(p for p in parent.glob("Waveform*") if p.is_dir())
    if target_id == "audacity":
        candidates.extend((
            Path.home() / "scoop" / "apps" / "audacity" / "current",
            Path.home() / "scoop" / "shims",
        ))
    return candidates


def windows_registry_locations(target_id: str = "waveform") -> list[Path]:
    target(target_id)
    if os.name != "nt":
        return []
    import winreg
    locations: list[Path] = []
    keys = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for key in keys:
            try:
                with winreg.OpenKey(hive, key) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, index)) as sub:
                                try:
                                    display = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                                except OSError:
                                    continue
                                if target_id not in display.lower():
                                    continue
                                for field in ("InstallLocation", "DisplayIcon"):
                                    try:
                                        raw = str(winreg.QueryValueEx(sub, field)[0]).strip().strip('"')
                                        # DisplayIcon sometimes ends in ",0".
                                        raw = re.sub(r",\s*-?\d+$", "", raw)
                                        if raw:
                                            locations.append(Path(raw))
                                    except OSError:
                                        pass
                        except OSError:
                            continue
            except OSError:
                continue
        # Windows App Paths registrations, including non-PATH Audacity installs.
        if target_id == "audacity":
            try:
                with winreg.OpenKey(hive,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Audacity.exe") as key:
                    value = winreg.QueryValueEx(key, "")[0]
                    if value:
                        locations.append(Path(str(value)))
            except OSError:
                pass
    return locations


def resolve(root: Path, remember: bool = True, target_id: str = "waveform") -> str | None:
    target(target_id)
    saved = configured(root, target_id)
    candidates = [Path(saved)] if saved else []
    candidates.extend(windows_registry_locations(target_id))
    candidates.extend(common_locations(target_id))
    for name in EXECUTABLE_NAMES[target_id]:
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in dict.fromkeys(candidates):
        executable = verify_executable(target_id, candidate)
        if executable:
            if remember and str(executable) != saved:
                set_location(root, str(executable), target_id)
            return str(executable)
    return None


def choose_executable(title: str, installer: bool = False) -> str | None:
    if os.name != "nt":
        raise RuntimeError("Native file selection currently requires Windows")
    import tkinter
    from tkinter import filedialog
    widget = tkinter.Tk()
    widget.withdraw()
    widget.attributes("-topmost", True)
    try:
        return filedialog.askopenfilename(
            title=title, filetypes=[("Windows executable", "*.exe")],
        ) or None
    finally:
        widget.destroy()


def verify_installer(file: Path) -> None:
    if os.name != "nt":
        raise ValueError("Installer assistance currently supports Windows only")
    if not file.is_file() or not file.suffix.lower() == ".exe":
        raise ValueError("Select the Waveform Windows installer executable")
    if "waveform" not in file.name.lower() and "tracktion" not in file.name.lower():
        raise ValueError("Selected installer filename must identify Waveform or Tracktion")
    # Windows signature validation: do not elevate/run arbitrary unsigned binaries.
    import json
    script = (
        "$s=Get-AuthenticodeSignature -LiteralPath $args[0];"
        "[pscustomobject]@{status=$s.Status.ToString();"
        "subject=if($s.SignerCertificate){$s.SignerCertificate.Subject}else{''}}"
        "|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["pwsh.exe", "-NoProfile", "-Command", script, str(file)],
        capture_output=True, text=True, timeout=20,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise ValueError("Could not verify the installer's Windows signature")
    try:
        signature = json.loads(result.stdout)
    except ValueError as exc:
        raise ValueError("Windows signature check did not return valid information") from exc
    if signature.get("status") != "Valid":
        raise ValueError("Installer is not validly signed; select the official publisher installer")
    if not re.search(r"tracktion", signature.get("subject", ""), re.I):
        raise ValueError("Installer signature does not identify Tracktion; refusing execution")


def start_installer(path: str) -> dict:
    file = Path(path).resolve()
    verify_installer(file)
    # Only after the user's explicit selection and click. The vendor installer owns
    # its own destination, licensing and consent screens.
    subprocess.Popen([str(file)], cwd=str(file.parent),
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return {"started": True, "message": "Waveform installer started. After it finishes, choose Detect again."}
