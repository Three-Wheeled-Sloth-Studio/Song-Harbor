# Native Lego instrument workflows: Add and Replace

Status: design and validation contract; Base-model Lego NOT yet installed or tested.
Date: 2026-10-24

## First-class instrumental operations

**Add layer**: Generate one isolated instrumental part using the arrangement as backing context. A/B is original versus original plus candidate. Accept inserts one positioned track only after explicit confirmation.

**Replace part**: Select an existing identified instrument track and a From/To section range. Generate a replacement part using backing that excludes that instrument in the selected target region. A/B is original versus other tracks plus generated instrument IN PLACE OF the original within the range. Other tracks and the original instrument outside the range remain unchanged. Accept writes a reversible regional-replacement edit, never overwrites source WAV.

Both workflows use the existing context-before/context-after range, immutable candidate metadata, source revision, sample-aligned crop, candidate history, no mutations before acceptance, and shared-clock A/B without seek on switching.

## ACE capabilities

Installed Turbo only supports Cover/Repaint and is not an isolated Lego generator. Base and XL-Base support native lego and extract; user approval is required before model download. Never silently fall back from Lego to Cover. Validate checkpoint config, native /v1/model_inventory, exact loaded model, and real Lego output on the local installation before enabling Generate.

Native instrument taxonomy: woodwinds, brass, fx, synth, strings, percussion, keyboard, guitar, bass, drums. Vocal and backing_vocal classes are excluded from these instrumental workflows. Violin and cello use instrument class strings, with timbre and phrasing details in Direction. Bass uses bass.

Payload hypothesis for local validation: /release_task multipart ctx_audio with task_type=lego, track_name canonical instrument class, prompt musical direction, lyrics=[Instrumental], installed Base model, seed, duration and optional musical metadata. Test actual local API behavior before shipping; track_name handling and repainting_start/end semantics must be verified, not assumed.

## Source construction

Add: Render selected project backing over full context, preserving existing source gains, timeline positions, and applicable automation. Lego output should be a separate instrument track aligned to context_start and cropped to target.

Replace: Identify target track by stable track ID, not display name. Build backing from all participating layers except that target over the selected region. Preserve original target as optional conditioning outside the region where supported. If the source is only a full mixed file, do not imply that the original part can be replaced without extraction; require a verified Extract-then-Replace preparation step.

All source inputs need a versioned manifest identifying included/excluded tracks, their positions and gains, selected range, and source fingerprints.

## Audition and acceptance

A: original mix. B Add: original plus candidate. B Replace: original target region gain ramps down as candidate ramps up; only selected range is affected. Both use same shared playback clock; initial pre-roll defaults to five seconds but later A/B toggles do not seek. At region boundaries support short configurable crossfades and avoid doubled bass or silence holes.

Accept Add: positioned track import with duplicate guard. Accept Replace: non-destructive replacement edit referencing target track ID, candidate asset, boundaries and fade settings; supports disabling/undo. Preview, saved playback and export must agree. Do not permanently rewrite or delete original instrument files.

## UI

Compact mode selector: Add instrument / Replace instrument. Instrument family selector from ACE taxonomy. Replace mode adds target track picker with notice that original remains intact. Keep From/To, context offsets and full-width Direction. Hide technical engine details under expandable controls. Show Base checkpoint required when Lego unavailable.

## Wired implementation status (2026-10-25)

- **Add / Lego:** Frontend mode selector now selects native Lego with an instrumental family, keeps experimental Turbo Cover distinct, and sends an explicit `task_type=lego` request when the matching Base checkpoint is loaded.
- Backend checks local ACE inventory for Lego support and current Base readiness. ACE multipart includes `track_name`, explicit `instruction` identifying that family, musical Direction, `[Instrumental]` lyrics, and 50 diffusion steps. Existing candidate history, source-context extraction, crop, A/B preview, and position-aware Add acceptance are reused.
- **Replace:** Reserved in UI but disabled. No destructive substitution or misleading A/B exists. Requires project stem-excluded backing construction, interval-specific muting, and undo/export parity before enablement.
- **Not runtime verified:** No ACE inference occurred on the Laptop-Pred. The pinned ACE checkout has not yet been GPU-tested with this exact payload. Native Lego isolation and temporal alignment must be confirmed on the main desktop.
- **Offline QA:** `python -m unittest discover -s app/backend/tests -p "test_ace*.py"` and `npm run build` from `app/frontend`, then live Base Strings generation using 20-30s context. Capture ACE errors, actual model loaded, wall time, peak VRAM, returned WAV channels/duration, and audible isolated part.
- On acceptance test verify no original track is changed before explicit Add, A/B switching stays on the shared clock, and Turbo Cover still behaves as before.

## Implementation sequence

1. Use Settings > Components > ACE-Step > Details > Install Base model with explicit confirmation. Resolve the checkpoint directory from ACESTEP_CHECKPOINTS_DIR (environment or ACE .env), otherwise under the detected ACE checkout checkpoints directory. Never use Song Harbor's models directory. Load Base, validate a native Lego output, and measure VRAM/runtime before exposing Lego generation. Avoid XL until feasible.
2. Implement model-neutral add/replace request schema, track taxonomy and capability gating. No silent Turbo fallback.
3. Implement project backing render, target instrument exclusion for replace, and immutable provenance.
4. Implement native Lego submit/poll/download and output-isolation validation.
5. Implement region-aware shared-clock A/B attenuation and candidate playback, then reversible replacement edit and export parity.

## QA

Check unavailable checkpoint; model and track-class validation; violin uses strings; Add creates isolated candidate; Replace Bass affects only target region with no doubling; L/R stems and imported position; overlapping regions; original outside region preserved; undo; source revision conflicts; preview and export parity; GPU release; cold/warm VRAM and elapsed times.

Sources: https://ace-step.github.io/ACE-Step-1.5/en/INFERENCE ; https://github.com/ace-step/ACE-Step-1.5/blob/main/acestep/constants.py
## Workbench QA and design follow-up (2026-10-26)

Lego generated a ready candidate using Base / Strings with a violin direction; auditory isolation and its relative signal level are not yet independently measured. Existing evidence is a user-report of a quiet violin candidate in the composite audition.

Current implementation now has:
- Waveform preview taken from decoded candidate audio, rendered after audition.
- Equal-power audition crossfade: 0 is original mix; 100 is candidate only **within its clip interval**. Original remains audible outside. Smooth transition is preview-only and does not mutate project.
- Optional preview-only generated-part trim -12 to +9 dB; not committed into the generated asset, track gain or export. Clipping is possible with positive trim. A future loudness-matched reference comparison should measure integrated/perceptual loudness and peak headroom before applying auto normalization.
- Modal generation status so long-running jobs don't hide progress in the scroll region; expanded default generation window and smaller descriptive text.
- Stem mute/isolate toggles adjacent to each stem name and collapsible mixer-detail region.
- Candidate history picker displays only the latest 12 per song; older candidate records remain on disk for safety. **Do not silently delete candidates** until provenance and accepted-reference protection plus an opt-in retention policy are implemented.

Further work:
1. Replace hardcoded instrument-family UI choices with a versioned engine-neutral instrument registry. ACE currently accepts 10 instrumental classes; map detailed violin, cello, viola, etc. to strings and add instrument-specific prompt templates. A provider/plugin can advertise extra instruments without expanding ACE's native track_names.
2. Add measured waveform envelope and integrated loudness analysis for original vs candidate, then calibrate preview blending for perceived volume and peak headroom; simple equal-power is a first pass, not an asserted constant-loudness mix.
3. Validate waveform preview, regional blend and trim on the desktop with a Lego Strings candidate, including within-range and outside-range behavior and audible silence/noise.
4. Candidate storage limits: decide number/age/quota, preserve references from accepted tracks and edit history, and support explicit cleanup/archival for unreferenced candidates.
5. Confirm stem-panel collapse and the direct name-adjacent M/S controls in narrow and wide windows.


## Workbench compact UI QA (2026-10-26)

- Generator main controls are two inline rows: Method / Operation, then Instrument Family. Verbose readiness, range-summary and isolation-description text removed. A small ACE service indicator is placed in the floating-tool title bar.
- Generated waveform now shows the playback cursor at the project-clock position relative to the candidate's target interval. Outside that interval it clamps to the edges.
- Preview line: Preview, independently clickable Solo (generated-only, without original mix), inline knob-symbol crossfade, and tucked-away pre-roll control. Solo stores/restores the previous crossfade. The 0–100 blend still performs a crossfade, not a mere candidate gain knob.
- Advanced generation parameters and saved candidates are below the generate/preview section. Keep candidacy and error states, but only essential inline text. Candidate cleanup remains visible as a collapsed disclosure.
- **Next-priority retention:** implement reference-aware cleanup (per-project size quota and count/age policy, never delete accepted or referenced assets, show disk use and dry-run preview). The current 12-item dropdown limit is only a display limit.
- **Layout follow-up:** pin the global Song Harbor application header to viewport top, accounting for scrollbar layering, other sticky rails and floating-tool z-index. Avoid pinned subpanels covering the waveforms.
- **QA gates:** ensure Solo starts playback even before Preview was previously loaded, Solo toggling restores old blend without seeking, original mix is fully audible outside candidate interval, waveform cursor moves with main playback/seek, and keyboard input doesn't accidentally affect transport.
