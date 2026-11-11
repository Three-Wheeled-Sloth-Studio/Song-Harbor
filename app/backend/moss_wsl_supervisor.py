"""WSL-only MOSS worker supervisor and verified process-group shutdown.

Called by Song Harbor through an argument-vector WSL command, never a shell.
The supervisor owns a dedicated Linux session for one SGLang server and stores
its identity in a JSON record on the configured runtime drive.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _start_ticks(pid: int) -> str | None:
    try:
        # /proc/<pid>/stat after the final ')' starts at field 3; starttime = field 22.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".moss-worker-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _record(path: Path, served: str) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = data.get("pid")
        if (not isinstance(pid, int) or pid < 2 or data.get("served") != served
                or not served.startswith("songharbor-moss-")):
            return None
        if _start_ticks(pid) != str(data.get("start_ticks")) or os.getpgid(pid) != pid:
            return None
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        args = raw.split(b"\0")
        if not (b"sglang.launch_server" in args and b"--served-model-name" in args
                and served.encode() in args):
            return None
        return data
    except (OSError, ValueError, TypeError):
        return None


def _group_alive(pgid: int) -> bool:
    """Zombie processes have released CUDA allocations and are not live workers."""
    try:
        for folder in Path("/proc").iterdir():
            if not folder.name.isdecimal():
                continue
            try:
                text = (folder / "stat").read_text().rsplit(")", 1)[1].split()
                if int(text[2]) == pgid and text[0] != "Z":
                    return True
            except (OSError, ValueError, IndexError):
                continue
        return False
    except OSError:
        return True  # fail closed


def stop(path: Path, served: str) -> int:
    data = _record(path, served)
    if data is None:
        # If stale, never kill arbitrary PIDs. Report inconclusive, not unloaded.
        print("ERROR: Cannot verify owned WSL model process. Stop not confirmed.", flush=True)
        return 4
    pgid = data["pid"]
    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            path.unlink(missing_ok=True)
            print("Worker group exited; CUDA release requested.", flush=True)
            return 0
        time.sleep(0.25)
    # Group belongs to this supervisor based on PID, session and model name.
    # Revalidate identity before forcing stop.
    if _record(path, served) is None:
        print("ERROR: Worker identity changed; forced stop refused.", flush=True)
        return 5
    os.killpg(pgid, signal.SIGKILL)
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            path.unlink(missing_ok=True)
            print("Worker group forcibly exited; CUDA release requested.", flush=True)
            return 0
        time.sleep(0.25)
    print("ERROR: Worker group still alive. Unload not confirmed.", flush=True)
    return 6


def run(args: argparse.Namespace) -> int:
    path = Path(args.state)
    if path.exists():
        if _record(path, args.served) is not None:
            raise RuntimeError("Owned model worker already exists; refusing duplicate load.")
        raise RuntimeError("Unresolved old worker state. No new load until inspected.")
    env = os.environ.copy()
    env.update({
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "HF_HOME": args.cache + "/hf-cache",
        "HUGGINGFACE_HUB_CACHE": args.cache + "/hf-cache/hub",
        "TORCH_HOME": args.cache + "/torch",
        "XDG_CACHE_HOME": args.cache + "/cache",
    })
    command = [args.python, "-m", "sglang.launch_server", "--model-path", args.model,
               "--served-model-name", args.served, "--host", "127.0.0.1",
               "--port", str(args.port), "--trust-remote-code"]
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, env=env,
                             start_new_session=True)
    ticks = _start_ticks(child.pid)
    if ticks is None:
        child.terminate()
        raise RuntimeError("Unable to establish owned model process identity.")
    _save(path, {"pid": child.pid, "start_ticks": ticks, "served": args.served,
                 "started_at": time.time()})
    try:
        return child.wait()
    finally:
        # Child has been reaped. Its process-group identifier is still ours, but
        # the leader no longer exists; do not use _record() (which needs leader).
        # We observed the group ownership at process creation in this process.
        if _group_alive(child.pid):
            try:
                os.killpg(child.pid, signal.SIGTERM)
                deadline = time.monotonic() + 12
                while _group_alive(child.pid) and time.monotonic() < deadline:
                    time.sleep(0.2)
                if _group_alive(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                    deadline = time.monotonic() + 6
                    while _group_alive(child.pid) and time.monotonic() < deadline:
                        time.sleep(0.2)
                if _group_alive(child.pid):
                    print("ERROR: Orphaned model worker group remains. Cleanup not verified.", flush=True)
            except (OSError, ProcessLookupError) as exc:
                print("ERROR: Model worker cleanup uncertain: " + str(exc), flush=True)
        path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation", required=True)
    launch = sub.add_parser("run")
    launch.add_argument("--python", required=True)
    launch.add_argument("--model", required=True)
    launch.add_argument("--served", required=True)
    launch.add_argument("--port", type=int, required=True)
    launch.add_argument("--cache", required=True)
    launch.add_argument("--state", required=True)
    shutdown = sub.add_parser("stop")
    shutdown.add_argument("--state", required=True)
    shutdown.add_argument("--served", required=True)
    args = parser.parse_args()
    if args.operation == "stop":
        return stop(Path(args.state), args.served)
    if not args.served.startswith("songharbor-moss-") or args.port != 18791:
        raise ValueError("Unsupported model identity or port.")
    return run(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("ERROR: MOSS WSL supervisor: " + str(exc), flush=True)
        sys.exit(1)
