"""ACE-Step runtime boundary. No model downloads, project mutation or subprocess startup.

Model generation and local process ownership are separate integration phases.
"""
from __future__ import annotations

import json
import math
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

LOOPBACK_HOSTS = ("127.0.0.1", "localhost")
TASKS_TURBO = frozenset(("text2music", "repaint", "cover", "cover-nofsq"))
TASKS_BASE = TASKS_TURBO | frozenset(("extract", "lego", "complete"))


class AceError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioRange:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Selection:
    target: AudioRange
    context: AudioRange


def resolve_sections(
    sections: list[dict[str, Any]],
    from_index: int,
    to_index: int,
    song_duration: float,
    context_before: float = 0,
    context_after: float = 0,
) -> Selection:
    """Inclusive section index range, with independent context padding.

    Section times are resolved from current project state, never client-submitted
    timestamps. Caller must separately check the project revision at acceptance.
    """
    if (not isinstance(from_index, int) or isinstance(from_index, bool) or
        not isinstance(to_index, int) or isinstance(to_index, bool) or
        from_index < 0 or to_index < from_index or to_index >= len(sections)):
        raise ValueError("Invalid inclusive from/to section indices")
    values = (song_duration, context_before, context_after)
    if any(not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
        raise ValueError("Song duration and context must be finite")
    if song_duration <= 0 or context_before < 0 or context_after < 0:
        raise ValueError("Invalid song duration or context padding")
    bounds = []
    for section in sections:
        start = section.get("start_seconds")
        end = section.get("end_seconds")
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)):
            raise ValueError("Every section requires finite start_seconds/end_seconds")
        if start < 0 or end <= start or end > song_duration + 0.001:
            raise ValueError("Section is outside song bounds")
        bounds.append((float(start), float(end)))
    if any(bounds[i][0] < bounds[i - 1][1] - 0.001 for i in range(1, len(bounds))):
        raise ValueError("Section boundaries overlap or are unordered")
    target = AudioRange(bounds[from_index][0], bounds[to_index][1])
    return Selection(target, AudioRange(
        max(0.0, target.start - context_before),
        min(float(song_duration), target.end + context_after),
    ))


def normalize_poll(payload: dict[str, Any], expected_task_id: str) -> dict[str, Any]:
    """Decode ACE's double-encoded polling records and report ambiguity honestly."""
    rows = unwrap(payload)
    if not isinstance(rows, list):
        raise AceError("ACE polling result must contain a list")
    match = next((r for r in rows if isinstance(r, dict) and
                  r.get("task_id") == expected_task_id), None)
    if match is None:
        # Some installed ACE builds omit task_id for single-ID result lists.
        if len(rows) == 1 and isinstance(rows[0], dict) and not rows[0].get("task_id"):
            match = rows[0]
        else:
            raise AceError("ACE response did not match requested task ID")
    status = match.get("status")
    raw = match.get("result", [])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError as exc:
            raise AceError("Malformed double-encoded ACE result") from exc
    if not isinstance(raw, list):
        raise AceError("ACE result payload must decode to a list")
    item = next((v for v in raw if isinstance(v, dict)), {})
    stage = str(item.get("stage") or "").lower()
    if status == 1:
        state = "ready" if any(v.get("file") or v.get("wave") for v in raw if isinstance(v, dict)) else "failed"
    elif status == 2:
        state = "cancelled" if stage in ("cancelled", "canceled") else "failed"
    elif status == 0:
        state = "generating" if raw else "pending_or_unknown"
    else:
        raise AceError("Unsupported ACE numeric polling status")
    return {"task_id": expected_task_id, "state": state, "stage": stage or None,
            "progress": item.get("progress"), "error": item.get("error"),
            "assets": [v.get("file") or v.get("wave") for v in raw
                       if isinstance(v, dict) and (v.get("file") or v.get("wave"))],
            "ambiguous": state == "pending_or_unknown"}


def unwrap(response: dict[str, Any]) -> Any:
    if not isinstance(response, dict):
        raise AceError("Invalid ACE response envelope")
    if response.get("error") or response.get("code") != 200:
        raise AceError(str(response.get("error") or f"ACE error {response.get('code')}"))
    return response.get("data")


class AceClient:
    """Loopback-only HTTP client. Never triggers /v1/init or model downloads."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8001,
                 api_key: str | None = None, timeout: float = 5.0):
        if host not in LOOPBACK_HOSTS or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("ACE must use an explicit loopback host and valid port")
        self.base = f"http://{host}:{port}"
        self.api_key = api_key
        self.timeout = timeout

    def request(self, path: str, body: dict[str, Any] | None = None) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Invalid ACE endpoint")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        req = urllib.request.Request(self.base + path, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read(2_000_000).decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise AceError(f"ACE request failed at {path}: {exc}") from exc

    def discover(self) -> dict[str, Any]:
        """Report liveness independently from model initialization readiness."""
        try:
            health = unwrap(self.request("/health"))
        except AceError as exc:
            return {"status": "stopped_or_unavailable", "error": str(exc), "models": []}
        if not isinstance(health, dict) or health.get("status") != "ok":
            return {"status": "error", "error": "ACE health check failed", "models": []}
        try:
            inventory = unwrap(self.request("/v1/model_inventory"))
        except AceError as exc:
            return {"status": "connected", "ready": False, "error": str(exc), "models": []}
        if not isinstance(inventory, dict):
            raise AceError("Invalid ACE model inventory")
        models = []
        for row in inventory.get("models", []):
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", ""))
            tasks = row.get("supported_task_types")
            # ACE's config-less inventory can optimistically claim base support.
            # Do not trust inferred Lego/Extract without validated config.
            if not name.startswith("acestep-v15-") or not isinstance(tasks, list):
                continue
            models.append({"name": name, "reported_tasks": sorted(set(tasks)),
                           "validated_tasks": sorted(TASKS_TURBO & set(tasks)),
                           "advanced_capabilities_unverified": bool(set(tasks) & (TASKS_BASE - TASKS_TURBO)),
                           "loaded": bool(row.get("is_loaded"))})
        return {"status": "connected", "ready": bool(health.get("models_initialized")),
                "loaded_model": health.get("loaded_model") if health.get("models_initialized") else None,
                "models": models}
