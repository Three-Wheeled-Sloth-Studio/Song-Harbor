# ACE-Step 1.5 runtime discovery

Date: 2026-10-23

Song Harbor checkout: `D:\Apps\Song-Harbor`

ACE-Step checkout: `D:\Apps\Tools\ACE-Step-1.5`

ACE-Step commit: `ca1e85fe9430179831e6bc6be790c332190a3866`

## Outcome

Song Harbor can own and manage the installed ACE-Step API without opening an
external command window. It should launch the virtual-environment Python
executable directly, use port/HTTP probes for readiness, retain the process
handle, and terminate that exact process on shutdown. It should not invoke the
interactive batch launchers or kill processes by a shared port number.

The native API is usable for the installed turbo model, but it is not yet a
stable integration contract. The most important blockers are:

1. The reviewed integration contract requires capability validation through
   `/v1/models`, but that path is shadowed and does not expose native ACE
   checkpoints. The adapter must use `/v1/model_inventory` or ACE must fix the
   route collision.
2. Cancellation is supplied by uncommitted, installation-local ACE changes;
   it is not present at the recorded ACE commit and has no focused HTTP tests.
3. `GET /v1/models` is shadowed by the OpenRouter-compatible route and does
   not return the native model inventory. Use `GET /v1/model_inventory`.
4. `GET /health` is a liveness check, not a readiness check: it returns
   `status=ok` while `models_initialized=false`, and `loaded_model` names the
   configured default even when that model is not loaded.
5. There is no API endpoint that unloads all DiT/VAE/text/LM models. Stopping
   the owned ACE process is the verified full GPU-unload boundary.
6. Polling uses a legacy, double-encoded result and ambiguous integer statuses.
   An unknown task looks pending (`status=0`), while failure and cancellation
   both use `status=2`.

No model was downloaded and no Song Harbor UI was built.

## Integration contract reconciliation

`docs/ace-accompaniment-integration-contract.md` was reviewed after it arrived
on `origin/main` during the final rebase. This discovery satisfies its local
validation gate for CLI invocation, API schemas, discovery, shutdown/unload,
cancellation provenance, and a live turbo failure/recovery workflow.

The runtime findings reinforce these contract requirements:

- Song Harbor must remain the owner of candidate/job state and map ACE's
  coarse statuses into `starting`, `generating`, `processing`, `ready`,
  `failed`, and `cancelled` without mutating the project before acceptance.
- Browser code must not call ACE. The backend must upload context audio rather
  than pass arbitrary Song Harbor filesystem paths.
- Capability gating must keep installed turbo cover/repaint experimental and
  must not expose Lego/Extract until a compatible checkpoint is independently
  discovered and verified.
- Automatic downloads remain prohibited. `/v1/init` and on-demand selection
  need local-inventory guards because ACE can otherwise fetch weights.
- `release_idle_resources()` can fully release GPU memory only by stopping an
  ACE process owned by Song Harbor. For a trusted API discovered already
  running, Song Harbor may connect but must not terminate it; idle release is
  unavailable unless ACE gains a whole-model unload endpoint.
- Native cancellation must remain best-effort until the local patch is pinned,
  tested, and its lazy-initialization race is fixed. Exact-PID process restart
  is the hard recovery boundary only for a Song Harbor-owned process.

One contract statement needs implementation-time correction: validating
`/v1/models` is insufficient in this installation because that path is the
OpenRouter model list. Native checkpoint/capability discovery is available at
`/v1/model_inventory`.

## Evidence and installation state

The ACE checkout was already dirty before this investigation. It contains 13
modified tracked files and three untracked files. Relevant local additions are
`acestep/api/http/cancel_task_route.py`,
`acestep/generation_cancellation.py`, route/store/worker changes, and
`stop_acestep.bat`. `start_api_server.bat` also has local changes that force
UTF-8 and select the 1.7B LM. These changes must be pinned or moved into a
maintained fork before Song Harbor can depend on them.

Installed checkpoints:

| Kind | Name | Approximate size | Loaded during probe |
| --- | --- | ---: | --- |
| DiT | `acestep-v15-turbo` | 4.46 GB | Yes |
| LM | `acestep-5Hz-lm-0.6B` | 1.28 GB | Yes, through lazy startup policy |
| LM | `acestep-5Hz-lm-1.7B` | 3.50 GB | No |
| Shared | `Qwen3-Embedding-0.6B` | 1.12 GB | As required by ACE |
| Shared | `vae` | 0.31 GB | Yes |

The only installed DiT is turbo. No base or XL-base DiT exists locally.

## Process lifecycle contract

### Start

The installed entry point is `acestep-api = acestep.api_server:main`. The
non-interactive direct command is:

```text
D:\Apps\Tools\ACE-Step-1.5\.venv\Scripts\python.exe \
  acestep\api_server.py --host 127.0.0.1 --port 8001 --no-init
```

The process working directory must be `D:\Apps\Tools\ACE-Step-1.5`.
`--no-init` makes HTTP liveness fast and defers model initialization until the
first generation or explicit init. Omit `--no-init`, or set
`ACESTEP_NO_INIT=false`, for eager initialization. ACE uses an in-memory queue
and job store, so Uvicorn must stay at one worker.

`start_api_server.bat` is not suitable for application ownership. It performs
an update check, may prompt, may run `uv sync`/installation logic, can select a
download source, and occupies a console. It is useful as a human launcher,
not as Song Harbor's subprocess contract.

Song Harbor already uses the required Windows pattern elsewhere:

```python
process = subprocess.Popen(
    [
        r"D:\Apps\Tools\ACE-Step-1.5\.venv\Scripts\python.exe",
        r"acestep\api_server.py",
        "--host", "127.0.0.1",
        "--port", "8001",
        "--no-init",
    ],
    cwd=r"D:\Apps\Tools\ACE-Step-1.5",
    stdin=subprocess.DEVNULL,
    stdout=log_file,
    stderr=subprocess.STDOUT,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    env=ace_environment,
)
```

Use an argument list and `shell=False`. Retain the `Popen` object and an
ownership token; do not adopt or stop an unrelated process merely because it
listens on port 8001. Redirect output to a bounded/rotated log rather than a
pipe that nobody continuously drains.

### Health and readiness

`GET /health` requires no authentication and always uses the standard envelope:

```json
{
  "data": {
    "status": "ok",
    "service": "ACE-Step API",
    "version": "1.0",
    "models_initialized": false,
    "llm_initialized": false,
    "loaded_model": "acestep-v15-turbo",
    "loaded_lm_model": null
  },
  "code": 200,
  "error": null,
  "timestamp": 1792782726353,
  "extra": null
}
```

Treat the signals separately:

- Process liveness: owned process has not exited.
- HTTP liveness: port accepts a request and `/health` returns HTTP 200 with
  `data.status == "ok"`.
- Generation readiness: additionally require
  `data.models_initialized == true` and a matching `data.loaded_model`.
- Requested LM readiness: when the job needs the LM, additionally require
  `data.llm_initialized == true` and the expected `loaded_lm_model`.

Do not use `loaded_model` by itself; it reports the configured default before
loading. The hidden `--no-init` probe reached HTTP liveness in about 0.1 s.
The earlier accompaniment proof of concept measured about 27 s for a cold
API/model startup. During this probe, an initialization call returned in
13.9 s, but it overlapped a lazy initialization race and is not a clean cold
benchmark.

### Stop

There is no HTTP server-shutdown endpoint and no whole-model unload endpoint.
For an owned process:

1. Stop accepting new Song Harbor ACE work.
2. Call installation-local `POST /cancel_all_tasks` when available.
3. Wait a bounded interval for cooperative cancellation.
4. Call `process.terminate()`, wait (recommended 10-15 s), and call
   `process.kill()` only as a fallback.
5. Confirm the owned PID exited and port 8001 is no longer listening.

`stop_acestep.bat` is unsafe for embedding: it force-kills any process found
on ports 7860 or 8001, kills the process tree, and ends with `pause`. It cannot
distinguish an ACE process owned by Song Harbor from another application.

The live hidden-process probe measured GPU use falling from 7,935 MiB to
2,945 MiB after the ACE PID exited; port 8001 also closed. This verifies OS
process teardown as the reliable GPU recovery mechanism. It does not prove a
graceful Uvicorn lifespan shutdown because the Windows termination probe used
process termination.

## Model discovery and capabilities

### Native inventory endpoint

Use authenticated `GET /v1/model_inventory`, not `/v1/models`:

```json
{
  "data": {
    "models": [
      {
        "name": "acestep-v15-turbo",
        "is_default": true,
        "is_loaded": false,
        "supported_task_types": [
          "text2music", "repaint", "cover", "cover-nofsq"
        ]
      }
    ],
    "default_model": "acestep-v15-turbo",
    "lm_models": [
      {"name": "acestep-5Hz-lm-0.6B", "is_loaded": false},
      {"name": "acestep-5Hz-lm-1.7B", "is_loaded": false}
    ],
    "loaded_lm_model": null,
    "llm_initialized": false
  },
  "code": 200,
  "error": null,
  "timestamp": 1792782739929,
  "extra": null
}
```

Inventory is filesystem-derived from immediate subdirectories of
`checkpoints`. DiT directories start with `acestep-`; LM directories start
with `acestep-5Hz-lm-`. Per-model task support is inferred from
`config.json:is_turbo`. A missing or unreadable config is optimistically
classified as base, so Song Harbor should reject malformed entries rather
than trust that fallback.

`GET /v1/models` currently resolves to the OpenRouter-compatible router,
which returned `{"object":"list","data":[]}` during the live probe. A native
route with the same path is registered later but is unreachable because of
route order. This collision should be fixed upstream or treated as a pinned
installation quirk.

### Capability matrix

| Model family | Task types reported by ACE | Song Harbor implication |
| --- | --- | --- |
| Turbo (installed) | `text2music`, `repaint`, `cover`, `cover-nofsq` | Supports new music, source-conditioned covers/remixes, and repaint. Does not provide isolated additive accompaniment. |
| Base / XL-base (not installed) | Turbo tasks plus `extract`, `lego`, `complete` | `lego` is the required native add-a-layer operation; `extract` separates a requested track; `complete` fills partial audio. |

`reference_audio_path` is a timbre/reference input. `src_audio_path` is the
source/context input used by cover, repaint, extract, Lego, and complete flows.
For Song Harbor's isolated accompaniment goal, the installed turbo checkpoint
remains the principal capability blocker.

### Selecting and initializing models

Generation requests may specify `model`. Without special configuration, ACE
uses that model only if it is already loaded in slot 1, 2, or 3. An unknown or
unloaded requested name silently falls back to the primary model. Slots 2 and
3 only exist when `ACESTEP_CONFIG_PATH2` or `ACESTEP_CONFIG_PATH3` was set
before process startup.

`POST /v1/init` accepts:

```json
{
  "model": "acestep-v15-turbo",
  "slot": 1,
  "init_llm": false,
  "lm_model_path": null
}
```

`slot` is 1-3. The endpoint loads/switches that handler and returns inventory.
It calls `ensure_model_downloaded`; therefore Song Harbor must validate the
requested name against the already-discovered local inventory before calling
it. Likewise, keep `ACESTEP_ON_DEMAND_MODEL_LOAD=false`: when enabled with one
queue worker and one API executor, a generation request may fetch an absent
model and replace the primary handler.

## HTTP API contract

### Common envelope and authentication

Most native endpoints return HTTP 200 even for application errors:

```json
{
  "data": null,
  "code": 404,
  "error": "Task not found",
  "timestamp": 1792782739991,
  "extra": null
}
```

Clients must inspect both HTTP status and envelope `code`/`error`.

When `ACESTEP_API_KEY` is set:

- Body-parsing routes (`/release_task`, `/query_result`, cancellation) accept
  `Authorization: Bearer <key>` or body field `ai_token`.
- Dependency-authenticated routes (`/v1/model_inventory`, `/v1/init`,
  `/v1/audio`, `/v1/stats`, `/v1/reinitialize`) require the Authorization
  header.
- `/health` is unauthenticated.

Bind only to `127.0.0.1`. Do not place the API key in logs or persisted request
documents.

### Submit: `POST /release_task`

Accepted content types are JSON, URL-encoded form, and multipart form. A body
that looks like JSON or form data is also parsed when the content type is
missing. Unsupported input returns HTTP 415; malformed JSON returns HTTP 400;
a full queue returns HTTP 429.

Recommended JSON request for the installed turbo model:

```json
{
  "prompt": "Sparse bowed cello counterline, no vocals or drums",
  "lyrics": "[Instrumental]",
  "thinking": false,
  "model": "acestep-v15-turbo",
  "bpm": 84,
  "key_scale": "F minor",
  "time_signature": "4/4",
  "vocal_language": "en",
  "audio_duration": 20.0,
  "batch_size": 1,
  "inference_steps": 8,
  "guidance_scale": 7.0,
  "use_random_seed": false,
  "seed": 150719,
  "task_type": "cover",
  "src_audio_path": "relative-or-system-temp-path.wav",
  "audio_cover_strength": 0.8,
  "cover_noise_strength": 0.2,
  "audio_format": "wav",
  "use_tiled_decode": true
}
```

Absolute manual audio paths are rejected unless they resolve inside the OS
temporary directory. For arbitrary Song Harbor project files, use multipart
uploads. Multipart file keys are `ref_audio`/`reference_audio` and
`ctx_audio`/`src_audio`; corresponding path keys are
`ref_audio_path`/`reference_audio_path` and
`ctx_audio_path`/`src_audio_path`. Uploaded temporary files are removed after
the job finishes.

Canonical request fields consumed by the route are:

| Group | Fields and defaults |
| --- | --- |
| Text/model | `prompt=""`, `global_caption=""`, `lyrics=""`, `thinking=false`, `sample_mode=false`, `sample_query=""`, `use_format=false`, `model=null` |
| Music metadata | `bpm=null`, `key_scale=""`, `time_signature=""`, `vocal_language="en"`, `audio_duration=null` |
| Sampling | `inference_steps=8`, `guidance_scale=7.0`, `use_random_seed=true`, `seed=-1`, `batch_size=null`, `infer_method="ode"`, `shift=3.0`, `use_adg=false`, `cfg_interval_start=0.0`, `cfg_interval_end=1.0` |
| Audio/task | `reference_audio_path=null`, `src_audio_path=null`, `task_type="text2music"`, `audio_cover_strength=1.0`, `cover_noise_strength=0.0`, `audio_code_string=""` |
| Repaint | `repainting_start=0.0`, `repainting_end=null`, `chunk_mask_mode="auto"`, `repaint_latent_crossfade_frames=10`, `repaint_wav_crossfade_sec=0.0`, `repaint_mode="balanced"`, `repaint_strength=0.5` |
| Output | `audio_format="mp3"` (`flac`, `mp3`, `opus`, `aac`, `wav`, `wav32` documented), `use_tiled_decode=true` |
| LM | `lm_model_path=null`, `lm_backend="vllm"`, `lm_temperature=0.85`, `lm_cfg_scale=2.5`, `lm_top_k=null`, `lm_top_p=0.9`, `lm_repetition_penalty=1.0`, `lm_negative_prompt="NO USER INPUT"`, `constrained_decoding=true`, `constrained_decoding_debug=false`, `use_cot_caption=true`, `use_cot_language=true`, `is_format_caption=false`, `allow_lm_batch=true` |
| Base-only task detail | `track_name=""`, `track_classes=null` |
| Analysis | `analysis_only=false`, `full_analysis_only=false`, `extract_codes_only=false` |

The Pydantic model declares `timesteps` and DCW controls, but the HTTP request
builder does not copy `timesteps`, `dcw_enabled`, `dcw_mode`, `dcw_scaler`,
`dcw_high_scaler`, or `dcw_wavelet`; submitted values are currently ignored
and model defaults win. This is an implementation defect if Song Harbor needs
those controls.

Successful submission response:

```json
{
  "data": {
    "task_id": "e0ab4fe2-3a19-4e13-8943-5f058e7c9640",
    "status": "queued",
    "queue_position": 1
  },
  "code": 200,
  "error": null,
  "timestamp": 1792782739995,
  "extra": null
}
```

### Poll: `POST /query_result`

JSON request:

```json
{"task_id_list":["94d5fbb8-8512-4864-a104-38aad1744bbb"]}
```

Form requests may pass `task_id_list` as a JSON string. The response `data` is
an array with one item per ID. Each item's `result` is itself a JSON-encoded
string and must be decoded a second time.

Outer item status meanings:

| `status` | Meaning |
| ---: | --- |
| `0` | queued, running, or unknown task |
| `1` | succeeded |
| `2` | failed or cancelled |

The decoded result array contains `file`, `wave`, `status`, `create_time`,
`env`, and, while active/failed, `progress`, `stage`, and sometimes `error`.
Success additionally contains prompt/lyrics/metas, generation info, seed, LM,
DiT, and an audio path such as `/v1/audio?path=<percent-encoded-path>`.

Important polling defects:

- Unknown IDs return `result="[]", status=0`, indistinguishable from pending.
  Song Harbor must poll only IDs it submitted and enforce its own deadline.
- The disk-cache result is preferred over the in-memory store. The installed
  failure path cached `stage="failed"` but omitted the exception/error text,
  even though the in-memory store retained a traceback.
- `progress_text` is sourced from a shared last-log message and can describe a
  different job when concurrency is enabled.
- Job state is in memory and completed cache entries expire; a process restart
  loses authoritative queue state.

Use authenticated `GET /v1/audio?path=...` to download a successful artifact.
The server restricts this path to its configured API audio temp directory.
Song Harbor must copy/import the file before shutting ACE down or cleaning its
temporary output.

### Cancel: installation-local endpoints

Cancel one:

```http
POST /cancel_task
Content-Type: application/json

{"task_id":"<uuid>"}
```

Responses use the common envelope. A queued task returns
`{"task_id":"...","status":"cancelled"}`; a running task returns
`status="cancelling"`; a terminal task returns its current textual status;
an unknown task returns envelope code 404 with HTTP 200.

Cancel all:

```http
POST /cancel_all_tasks
Content-Type: application/json

{}
```

The response is
`{"cancelled":[{"task_id":"...","status":"cancelled|cancelling"}],"count":N}`.

Queued cancellation was verified live. Running cancellation is cooperative:
the local patch checks between LM tokens and around diffusion work; it cannot
kill the worker thread immediately. Cancellation and failure are both exposed
to polling as integer status 2, so the client must retain the cancel response
and/or inspect decoded `stage`.

There is also a lazy-initialization race. A worker checks cancellation before
model initialization but does not mark the job running until initialization
finishes. If the worker has dequeued the job and Song Harbor cancels while it
still appears queued, the route marks it cancelled, but initialization can
continue in the background before deeper cancellation checks run. This was
observed in the live probe: the cancelled job did not generate audio, but it
triggered model/LM loading. The patch needs a cancellation re-check after
`ensure_models_initialized()` and before `mark_running()`.

## Failure handling and GPU recovery

The worker catches generation exceptions, records the job as failed, updates
the cache, and calls the selected handler's `_empty_cache()` in `finally`.
Cache clearing releases unused allocator blocks but does not unload model
objects. A failed job therefore should not be expected to return ACE to its
pre-start VRAM footprint.

Live recovery sequence:

1. A `cover` request without source audio failed as expected with server log
   `Music generation failed: Task 'cover' requires source audio`.
2. `/health` stayed responsive and reported initialized models.
3. A subsequent 10-second `text2music` job succeeded using the same process in
   7.8 s submit-to-terminal time (ACE reported 2.49 s generation time).
4. Terminating the owned process closed port 8001 and released approximately
   4,990 MiB of GPU memory.

Recommended recovery policy:

- Request validation/application failure: keep the process and allow another
  job; cap consecutive failures and retain server logs.
- CUDA OOM or model-initialization failure: cancel pending work, terminate the
  owned process, wait for exit/VRAM release, and restart once with conservative
  offload settings. Do not loop indefinitely.
- Process exit, health timeout, or wedged request: terminate/kill the owned PID
  using the bounded shutdown sequence, then restart with backoff.
- Do not treat `POST /v1/reinitialize` as a general unload/recovery endpoint.
  It restores components previously unloaded by training/preprocessing and
  clears caches, but does not provide a full reset of all handlers/slots.

## Verification performed

- Hidden, console-free process start with the installed `.venv` Python.
- Live `/health`, `/v1/model_inventory`, `/v1/models`, `/v1/init`,
  `/release_task`, `/query_result`, and `/cancel_task` behavior; static
  inspection of the `/v1/audio` download contract.
- Queued cancellation, deliberate job failure, successful generation after
  failure, process stop, port closure, and GPU release.
- Static inspection of startup, shutdown, route registration, parsing,
  job/cache, model-selection, cancellation, and reinitialization code.
- Targeted ACE test run: 36 tests executed; 34 passed and two errored. Both
  errors are in `release_task_route_http_test` because its `_FakeParser.get`
  accepts one argument while production now calls `get("seed", -1)`. This is
  test drift, not a live request failure, but means the relevant suite is not
  green.
- No cancellation-specific tests were found.

One 10-second WAV was created only to prove recovery after a failure, under
ACE's `.cache\acestep\tmp\api_audio` directory. The attempted automated cleanup
was blocked by the execution environment's destructive-operation policy; the
file is not part of Song Harbor and is not committed.

## Implementation blockers and required decisions

| Priority | Blocker | Required resolution |
| --- | --- | --- |
| P0 | Required isolated-additive task is unavailable | Install/approve a base or XL-base model later, or explicitly accept turbo cover/repaint plus separation as a lower-fidelity fallback. Do not download during implementation without approval. |
| P0 | Cancel API is an uncommitted local patch | Pin a commit/fork or vendor a reviewed patch; add queued, running, init-race, and terminal cancellation tests. |
| P0 | No safe in-process whole-model unload | Make the ACE subprocess the GPU ownership boundary; implement exact-PID terminate/wait/kill and restart recovery. |
| P1 | Health is liveness-only | Add a Song Harbor readiness state machine using `models_initialized`, expected model, and optional LM fields. |
| P1 | `/v1/models` route collision | Use `/v1/model_inventory` now; fix duplicate route registration before treating the native API as stable. |
| P1 | Polling ambiguity and lost failure detail | Maintain Song Harbor task records/deadlines, double-decode `result`, preserve cancel intent, and surface ACE logs. Prefer an upstream typed job-status endpoint later. |
| P1 | Model calls can download absent weights | Disable on-demand loading and validate `/v1/init` names against local inventory. |
| P1 | Targeted ACE tests are not green | Repair parser test fakes and add cancellation/route-conflict/regression coverage in the maintained ACE fork. |
| P2 | Some declared generation controls are ignored | Wire or remove `timesteps` and DCW request fields before exposing them to Song Harbor. |
| P2 | Human batch scripts are interactive/unsafe for embedding | Launch Python directly with `CREATE_NO_WINDOW`; never use the port-killing stop batch from Song Harbor. |

## Recommended integration boundary

Implement a backend-only ACE runtime manager before any UI:

1. Discover and validate the configured ACE root, `.venv` Python, checkpoint
   inventory, port availability, and pinned ACE revision/patch level.
2. Start one owned hidden subprocess, log it, and expose distinct liveness and
   readiness states.
3. Disable downloads/on-demand switching. Initialize only a locally discovered
   model.
4. Submit multipart audio, persist the returned task ID, poll with a deadline,
   double-decode results, download/copy successful audio, and then import it
   through Song Harbor's existing track path.
5. Cancel cooperatively, but retain terminate/restart as the hard recovery and
   GPU-unload boundary.
6. Gate additive accompaniment on a discovered model whose capabilities
   include `lego`; do not infer it from the installed turbo model.
