"""DAW adapter registry and Windows-assisted setup.

Never assume a DAW exists, never download executables from unverified URLs.
Waveform Free is the first target; other adapters can implement the same contract.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import dependencies

OFFICIAL_WAVEFORM_URL = "https://www.tracktion.com/products/waveform-free"
TARGETS = {
    "waveform": {"name": "Waveform Free", "free": True,
                 "download_url": OFFICIAL_WAVEFORM_URL,
                 "format": "six-stem-wav-folder"},
}


def target(target_id: str) -> dict:
    if target_id not in TARGETS:
        raise ValueError("This DAW target is not supported yet")
    return {"id": target_id, **TARGETS[target_id]}


def verify_waveform(path: Path) -> Path | None:
    path = path.expanduser()
    if path.is_dir():
        candidates = [path / n for n in
                      ("Waveform.exe", "Waveform 14.exe", "Waveform 13.exe",
                       "Waveform 12.exe", "Waveform Free.exe")]
        candidates.extend(path.glob("Waveform*.exe"))
    else:
        candidates = [path]
    for candidate in candidates:
        if candidate.is_file() and re.search(r"^Waveform.*\.exe$", candidate.name, re.I):
            return candidate.resolve()
    return None


def common_locations() -> list[Path]:
    results: list[Path] = []
    for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                  os.environ.get("LOCALAPPDATA")):
        if not value:
            continue
        root = Path(value)
        results.extend([
            root / "Tracktion", root / "Tracktion Software",
            root / "Waveform", root / "Waveform Free",
        ])
        for directory in ("Tracktion", "Tracktion Software"):
            parent = root / directory
            if parent.is_dir():
                results.extend(p for p in parent.glob("Waveform*") if p.is_dir())
    return results


def windows_registry_locations() -> list[Path]:
    if os.name != "nt":
        return []
    import winreg
    results: list[Path] = []
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
                                display = str(winreg.QueryValueEx(sub, "DisplayName")[0])
                                if "waveform" not in display.lower():
                                    continue
                                location = str(winreg.QueryValueEx(sub, "InstallLocation")[0])
                                if location:
                                    results.append(Path(location))
                        except (OSError, ValueError):
                            continue
            except OSError:
                continue
    return results


def configured(root: Path) -> str | None:
    daws = dependencies.load_config(root).get("daws", {})
    if not isinstance(daws, dict):
        return None
    item = daws.get("waveform", {})
    return item.get("executable") if isinstance(item, dict) else None


def resolve(root: Path, remember: bool = True) -> str | None:
    candidates = []
    saved = configured(root)
    if saved:
        candidates.append(Path(saved))
    candidates.extend(windows_registry_locations())
    candidates.extend(common_locations())
    candidates.extend(Path(p) for p in (shutil.which("Waveform.exe"),) if p)
    for candidate in candidates:
        executable = verify_waveform(candidate)
        if executable:
            if remember and str(executable) != saved:
                set_location(root, str(executable))
            return str(executable)
    return None


def set_location(root: Path, chosen: str) -> str:
    executable = verify_waveform(Path(chosen))
    if not executable:
        raise ValueError("Choose the installed Waveform executable or its installation folder")
    data = dependencies.load_config(root)
    daws = data.setdefault("daws", {})
    if not isinstance(daws, dict):
        data["daws"] = daws = {}
    daws["waveform"] = {"executable": str(executable), "source": "user"}
    # Atomic settings update; retain FFmpeg and future target preferences.
    file = dependencies.config_file(root)
    file.parent.mkdir(parents=True, exist_ok=True)
    import json
    import uuid
    temporary = file.with_name(file.name + "." + uuid.uuid4().hex[:8] + ".tmp")
    try:
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(temporary, file)
    finally:
        temporary.unlink(missing_ok=True)
    return str(executable)


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
