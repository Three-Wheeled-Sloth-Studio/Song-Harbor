"""Linux worker for explicit, user-approved MOSS runtime and checkpoint installation.

Invoked only through the local Windows Song Harbor service. Does not load audio or
touch song projects. All code, checkpoints and cache live under the supplied root.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SGLANG_REVISION = "c28a945853c7fee357f55d976b8abce51874bd94"
SGLANG_URL = "https://github.com/OpenMOSS/sglang.git"
MODELS = {
    "moss-audio-4b": "OpenMOSS-Team/MOSS-Audio-4B-Instruct",
    "moss-music-8b": "OpenMOSS-Team/MOSS-Music-8B-Instruct",
}


def announce(message: str) -> None:
    print(message, flush=True)


def run(*args: str, cwd: Path | None = None) -> None:
    announce("Running: " + Path(args[0]).name + " (" + str(cwd or Path.cwd()) + ")")
    subprocess.run(args, cwd=cwd, check=True, stdin=subprocess.DEVNULL)


def environment(root: Path) -> None:
    root = root.resolve()
    for key, suffix in {
        "UV_CACHE_DIR": "cache/uv", "UV_PYTHON_INSTALL_DIR": "python",
        "UV_TOOL_DIR": "tools", "UV_TOOL_BIN_DIR": "tools/bin",
        "HF_HOME": "cache/huggingface", "HUGGINGFACE_HUB_CACHE": "cache/huggingface/hub",
        "XDG_CACHE_HOME": "cache/xdg", "TORCH_HOME": "cache/torch",
        "PIP_CACHE_DIR": "cache/pip", "TMPDIR": "cache/tmp",
    }.items():
        path = root / suffix
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)


def ensure_uv(root: Path) -> str:
    present = shutil.which("uv")
    if present:
        return present
    announce("Installing uv into isolated bootstrap environment on selected model drive")
    bootstrap = root / "bootstrap"
    if not (bootstrap / "bin/python").exists():
        run(sys.executable, "-m", "venv", str(bootstrap))
    run(str(bootstrap / "bin/python"), "-m", "pip", "install", "uv")
    binary = bootstrap / "bin/uv"
    if not binary.is_file():
        raise RuntimeError("uv bootstrap failed. Python venv/pip may need setup in WSL.")
    return str(binary)


def runtime(root: Path) -> None:
    uv = ensure_uv(root)
    venv = root / "runtime"
    checkout = root / "source" / "sglang-moss-audio"
    if not checkout.exists():
        checkout.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--no-checkout", SGLANG_URL, str(checkout))
    if not (checkout / ".git").is_dir():
        raise RuntimeError("Existing SGLang source folder is not a Git checkout; nothing overwritten.")
    announce("Checking out pinned OpenMOSS SGLang revision " + SGLANG_REVISION)
    run("git", "fetch", "--depth", "1", "origin", SGLANG_REVISION, cwd=checkout)
    run("git", "checkout", "--detach", SGLANG_REVISION, cwd=checkout)
    if not venv.joinpath("bin/python").is_file():
        run(uv, "python", "install", "3.12")
        run(uv, "venv", "--python", "3.12", "--python-preference", "only-managed", str(venv))
    announce("Installing pinned OpenMOSS SGLang package. This may download large CUDA dependencies.")
    run(uv, "pip", "install", "--python", str(venv / "bin/python"),
        "-e", str(checkout / "python") + "[all]")
    run(uv, "pip", "install", "--python", str(venv / "bin/python"),
        "nvidia-cudnn-cu12==9.16.0.29", "huggingface_hub")
    run(str(venv / "bin/python"), "-c", "import sglang,huggingface_hub")
    manifest = {"schema_version": 1, "source": SGLANG_URL,
                "revision": SGLANG_REVISION, "python": str(venv / "bin/python"),
                "verified_import": True, "verified_at": datetime.now(timezone.utc).isoformat()}
    write_atomic(root / "runtime-manifest.json", manifest)
    announce("RUNTIME READY: " + str(venv / "bin/python"))


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".manifest-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def checkpoint(root: Path, identifier: str) -> None:
    if identifier not in MODELS:
        raise ValueError("Unapproved checkpoint identifier")
    repo_id = MODELS[identifier]
    runtime_python = root / "runtime/bin/python"
    if not runtime_python.is_file():
        raise RuntimeError("Install the MOSS runtime first.")
    # Use an isolated helper process to keep the worker's dependencies separate.
    downloader = r'''
import hashlib,json,os,shutil,sys
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
repo_id,root_str,identifier=sys.argv[1:]
root=Path(root_str).resolve()
api=HfApi()
info=api.model_info(repo_id,files_metadata=True)
license_id=str(getattr(info.card_data,"license","") or "").lower()
if license_id not in ("apache-2.0","apache 2.0"):
    raise RuntimeError("License not verified as Apache-2.0. Download refused.")
sizes=[getattr(s,"size",None) for s in info.siblings or [] if str(s.rfilename).endswith(".safetensors")]
if not sizes or any(not isinstance(size,int) for size in sizes):
    raise RuntimeError("Model download size unavailable. Disk preflight failed closed.")
total=sum(sizes)
free=shutil.disk_usage(root).free
if free < int(total*1.3)+2*1024**3:
    raise RuntimeError("Insufficient space for checkpoint and staging. No download started.")
destination=root/"checkpoints"/identifier
staging=root/"staging"/(identifier+"-"+info.sha[:12])
if destination.exists():
    raise RuntimeError("Checkpoint destination already exists. No files overwritten.")
staging.parent.mkdir(parents=True,exist_ok=True)
if staging.exists():
    marker=staging/".songharbor-staging.json"
    if not marker.is_file():
        raise RuntimeError("Unrecognized staging folder. Existing files preserved.")
    identity=json.loads(marker.read_text())
    if identity.get("repo")!=repo_id or identity.get("revision")!=info.sha:
        raise RuntimeError("Staging does not match pinned repository revision. No files overwritten.")
    print("RESUME: matching incomplete checkpoint download",flush=True)
else:
    staging.mkdir(parents=True)
    (staging/".songharbor-staging.json").write_text(json.dumps({"repo":repo_id,"revision":info.sha}))
print("DOWNLOAD: "+repo_id+" revision "+info.sha+" bytes "+str(total),flush=True)
snapshot_download(repo_id=repo_id,revision=info.sha,local_dir=staging)
files=list(p for p in staging.rglob("*") if p.is_file() and ".cache" not in p.parts)
if not files or any(p.is_symlink() or not p.resolve().is_relative_to(staging.resolve()) for p in files):
    raise RuntimeError("Unsafe or incomplete checkpoint inventory")
cfg=staging/"config.json"
if not cfg.is_file():
    raise RuntimeError("Model config missing after download")
data=json.loads(cfg.read_text(encoding="utf-8"))
model_type=str(data.get("model_type","")).lower()
architectures=str(data.get("architectures","")).lower()
family= "moss_music" if "mossmusic" in architectures or "moss_music" in model_type else "moss_audio" if "mossaudio" in architectures or "moss_audio" in model_type else None
if not family: raise RuntimeError("Checkpoint architecture unrecognized")
index=staging/"model.safetensors.index.json"
if index.is_file():
    shards=list(set(json.loads(index.read_text())["weight_map"].values()))
else:
    shards=["model.safetensors"] if (staging/"model.safetensors").exists() else []
if not shards or any(not isinstance(name,str) or Path(name).name!=name or not (staging/name).is_file() for name in shards):
    raise RuntimeError("Missing checkpoint weight shards")
inventory={}
for p in files:
    h=hashlib.sha256()
    with p.open("rb") as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b""):
            h.update(chunk)
    inventory[str(p.relative_to(staging))]={"size":p.stat().st_size,"sha256":h.hexdigest()}
manifest={"schema_version":1,"repo":repo_id,"revision":info.sha,"license":license_id,
          "family":family,"inventory":inventory,"verification":"local-sha256","complete":True}
(staging/"song-harbor-install.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
(staging/".songharbor-staging.json").unlink(missing_ok=True)
destination.parent.mkdir(parents=True,exist_ok=True)
staging.rename(destination)
print("MODEL READY: "+str(destination),flush=True)
'''
    run(str(runtime_python), "-c", downloader, repo_id, str(root), identifier)


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("runtime", "checkpoint"):
        raise ValueError("Usage: worker runtime|checkpoint ROOT identifier")
    operation, root_arg, identifier = sys.argv[1:]
    root = Path(root_arg).resolve()
    if not root.is_absolute() or str(root) in ("/", "/home") or not root.is_dir():
        raise ValueError("Dedicated existing model directory required")
    environment(root)
    if operation == "runtime":
        runtime(root)
    else:
        checkpoint(root, identifier)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        announce("ERROR: " + str(exc) + ". Installation not completed.")
        sys.exit(1)
