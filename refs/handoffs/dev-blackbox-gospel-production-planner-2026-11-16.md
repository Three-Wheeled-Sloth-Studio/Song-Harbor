# Song Harbor DEV: Blackbox Gospel production planner, first functional slice

Date: 2026-11-16
Branch: dev only. Main/production remains untouched.

## Intent

One compact **Production planner** in the existing tools rail analyzes the current effects-processed mix and existing dry source stereo fingerprints, combines those with saved song sections/lyrics and a built-in Infra Choir aesthetic profile, and generates reviewable import-ready production section text. Do not reinterpret a tonal texture as an instrument or assume a single model can establish all facts. Preserve author-created arrangement, section boundaries, lyrics and prior section automation. Human review and Save are required.

## Implemented in source

- `app/frontend/src/ProductionPlannerTool.tsx`: profile shown as Infra Choir (v1), direction selection, bounded spatial/dynamic ambition controls, Generate plan, compact count and evidence, read-only generated text, Copy, Review in editor. No model download, MOSS execution or automatic project save.
- `app/frontend/src/StemMixer.tsx`: planner uses `SharedClockAudition.analyzeMix(timelineSections)` on the actual currently effects-processed render. Blocks unsaved section previews, unloaded repairs and conflicting export; guards mid-analysis revision changes. Existing analysis findings and section insights are refreshed for other tools. Stages reviewed proposal as a distinct **unsaved** whole-song section draft; warns before overwriting an already-open editor or previous planner draft.
- `app/frontend/src/SharedClockAudition.ts`: inspect decoded source track L/R energy, side/mid width and correlation and hard-panned source identities, without changing source data or audio routing. These source fingerprints supplement, but are not substitutes for, the section-level *processed mix* measurements. Currently whole-source statistics, not per-section post-effect stem/channel meters.
- `app/backend/production_planner.py`: isolated deterministic v1 proposal provider. Existing canonical section IDs/lyrics/timings and existing directives are authoritative. Validates complete section-metric coverage, finite metrics, stereo evidence and bounds. Protects existing target-specific author controls, split stems, measured source L/R differentiation, already wide or polarized mixes, near-mono sources where width effects would be ineffective, muted/non-soloed sources, and lead vocals/bass. Adds only supported bounded width/reverb/pan/gain directives for eligible atmospheric/backing parent aliases; long smooth transitions relative to section duration; only modest attenuation for near-clipping backing; preserves deliberately quiet passages. Spatial movement mode can stage modest pan on unprotected candidate sources, returning toward center at chorus or ending. No invented instrument identities, authored score edits, master auto-gain, or false loudness guarantee.
- `app/backend/server.py`: `POST /api/projects/{ident}/production-plan/preview` local-origin-only, bounded read-only preview. Returns validated whole-song section text plus per-section directives, mix measurements, notes, stereo provenance, style profile and explicit limitation.
- `app/frontend/src/SectionsTool.tsx`: can accept the produced text as an unsaved draft in existing Whole-song Section Text editor, retaining normal explicit Apply/Save/Discard and ability to Reload the saved text. It does **not** automatically import/apply.
- `app/frontend/src/WorkbenchTools.tsx`: new planner tool item.
- `app/backend/tests/test_production_planner.py`: regression fixtures for preservation of section IDs, lyric words and original directives, source stereo protection, anti-hallucination for near-mono and silent sections, invalid metrics, draft/no-op and import round-trip.

## Evidence hierarchy and limitations

1. Authored section and lyric text + existing project scripts: source of truth.
2. Processed mix RMS, peaks, width, balance from the same offline audio graph as export: measured. May not exactly match a separate DAW/master.
3. Per-source raw stereo fingerprints / split status: measured baseline, *not* section-specific post-effect stem energy.
4. Infra Choir v1 production profile: built-in style preference, not a learned listener.
5. Suggested directives: bounded deterministic heuristic, not claims about instrumentation or musical taste quality.

**Not yet implemented**: validated MOSS/SMU observation ingestion and resolution, actual harmonic/tempo awareness, editable persistent profile library, per-stem per-section effects-processed evidence, audio-rendered proposed A/B, true LUFS-based adaptive overall loudness controller, automatic iterative optimization. Do not claim these in UI/release notes. The current dynamics slider influences only bounded backing peak-guard opportunities; it is not a full leveler.

## Windows QA requested

1. Update/relaunch dev. Run `npm run build --prefix app/frontend` or normal launcher. Check Python import/startup and execute `python -m unittest discover -s app/backend/tests -p 'test_production_planner.py' -v` in the backend runtime.
2. Open Blackbox Gospel with its saved canonical sections, lyrics and stems. Open **Production planner**; choose default Infra Choir profile and `Enhance arrangement`. Click Generate plan. Verify visible busy state and a returned full-song draft with exact timestamps/lyrics and previously saved directives intact.
3. Test `Review in editor`; confirm it opens Whole-song section text as **unsaved**, not auto-accepted. Discard/reload, then separately import a reviewed draft. Reopen project and check expected persistence and normal export. Verify source files and original scripts unchanged before acceptance.
4. Inspect spatial evidence for an already stereo-differentiated parent, a hard split child, and a nearly mono source. Wide/imbalanced sources should not be needlessly widened, nor should near-mono sources be mislabeled as independently stereo. Check existing authored pan/reverb/width are not overridden or duplicated.
5. Try different direction/ambition settings. Without a qualifying mix/section/stem evidence signal, generated result may deliberately contain few or zero additions; explain why in Changes and evidence.
6. Test no saved sections, stale analysis after changing a fader/section, mid-preview edit, conflicting export, and invalid/quiet sections. Expect explicit errors or conservative suggestions, never project mutation.
7. Audition a preview manually and compare level-matched original vs proposed mix; verify chorus impact, lead intelligibility, mono compatibility, headroom and drum transients. No automatic A/B or LUFS matching is yet implemented.
8. Specific track test: compare Blackbox Gospel from quiet opening through contrasting sections and keep high-value production changes only.

## Follow-on slices

1. Profile persistence/editable album or artist profiles with explicit author intent, spatial aesthetics and user correction history.
2. Integrate section-aware MIDI / authored lyrics and verified MOSS observations via SMU, contradictions explicitly unverified. Suggest changes with explanation and source evidence.
3. Analyze effects-processed per-stem per-section L/R and semantic masking to create richer movement while respecting already differentiated channels.
4. Render proposed script to an immutable audition candidate and perform loudness-matched A/B with peaks, mid/side, correlation and masking guardrails.
5. Separate bounded, opt-in perceived loudness normalization `auto.gain` from creative dynamics and preserve intentional dramatic contrast.

Status: implementation committed to dev, **frontend build/backend unit tests and actual Windows listening QA not executed via connector**. Do not promote to main until these pass.


## Post-implementation safeguards (later dev commits)
- Raw per-source stereo measurements now gate any new width/pan suggestion; without matching source evidence the planner does not invent stereo advantages.
- Nearly mono source signals, already spatialized signals, hard split children, and muted/non-soloed sources are protected.
- **Inherited authored directives are globally protected by effect dimension**; an earlier author pan/width/reverb/gain in any section cannot be unexpectedly overridden by this initial rule-based provider in a later section. This is intentionally conservative and can yield few suggestions.
- Existing project chorus width and earlier spatial placement now have regression coverage; near-mono and silent-metric fixtures are included.
- No compiler or unittest run was available through GitHub connector. Latest dev source commit after these refinements: `33d870c`.


## 2026-11-16 QA follow-up: near-mono creation and hidden controls

User's dev build and actual plan generation **passed**. User screenshot showed the planner first line containing Profile / Direction / Space 65, with remaining dynamics slider and Generate button apparently pushed horizontally out of view and a huge blank panel below. User also found production proposals far too sparse (mostly reverb and small gain changes). Clarified that source near-mono material is a central **opportunity for creating meaningful space**, not a reason to avoid all processing.

Committed corrections on dev:
- Scoped responsive CSS in `song-harbor.css`: planner dialog opens wider (bounded by viewport), inner tool flex scrolls, controls use a two-column responsive grid and single-column layout on narrow screens; Generate action occupies a visible row, output text/evidence can scroll, controls wrap instead of overflowing. Profile now compact and proposal evidence shows count of actual mono-like source profiles.
- `production_planner.py`: replaced single-'Other' conservatism with eligible independent *stem files*, leaving Vocals/Bass/Drums as protected anchors. Plans complementary panning of distinct backing stems, changes across sections, depth using deterministic `.space` reflections and reverb where appropriate, and moderate vocal-keyed backing ducking for depth without flattening the main master. Existing channel differentiation, hard pans and split routing remain protected; there is no unsupported claim that a plain width directive can create separate information in a near-mono signal. For mono-like backing stems, propose spatial reflections instead of fake width; individual, measured, non-silent sources are required. Original user-authored directives (including ones in later sections) are protected at that effect dimension. Whole-script import validation and no-mutation semantics retained.
- `SharedClockAudition.ts`: source stereo fingerprints now also include dry RMS, so truly silent/near-silent stems are not given pointless spatial treatments.
- Added regression fixtures for two distinct mono backing stems creating opposite lateral positions, reflections and ducking; split and authored pan protections; silent stem suppression. Tests **not executed on Windows** here.

**Known scope limitations**: This remains a deterministic style/measurement planner, not a semantics-aware creative LLM. It does not inspect per-stem time-varying content, L/R cross-stem correlation, authored intent beyond section types/lyrics preservation, or actual loudness-matched proposed-vs-original renders. Do not equate 'separate stem files' with statistically independent source content. Current lateral pattern is bounded and section-driven, not yet melody-aware. Do not auto-apply. User should first verify all controls are visible, then generate on Blackbox Gospel using Movement/space around 75-85, compare with default Enhance, inspect proposed directives, and review in editor only after listening checks.

**QA**: update/relaunch dev, run TypeScript/Vite and Python tests, ensure no runtime startup errors; inspect narrow and widened popup, keyboard scroll and large draft; compare generated plans and protection of lead/bass/known source L/R. Under existing authored full spatial automation, there may still be few permissible directives, which is a correct protection unless user explicitly selects an override mode (not implemented).


## 2026-11-16 next slice: section-aware stem presence and authored performance cues

User QA: dev relaunch **clean**, floating window flow good, spatial direction much more reasonable. Noted split L/R stem channels are not yet leveraged and explicitly **deferred** that optimization. Proceeded on dev only.

Implemented:
- `SharedClockAudition.sourceSectionProfiles(sections)`: bounded read-only dry stem/source observations aligned to real timeline offsets and canonical song section start/end. Per section/working filename: RMS, width, L/R balance, correlation, channel count, sample coverage, and source start. This is **raw/effective stem audio**, NOT effects-processed per-stem section output and NOT a guarantee of independent instrument separation.
- Production planner frontend now passes these observations as `section_stems` alongside current processed-mix section metrics and whole-source stereo profiles. Server accepts at most 8192 observations.
- Planner validates each canonical source observation, rejects unknown section IDs/invalid values, ignores noncanonical split-child/ephemeral track filenames, and handles multiple physical channels sharing one source filename without crashing (strongest RMS lane retained only for activity evidence). This does NOT optimize split-channel positioning yet.
- Section-specific eligibility: backing stems with measured silence, too little temporal coverage, or no actual presence are not positioned or effect-processed in that section. Vocal-keyed ducking is proposed only when a vocal source is actually active in that section (not merely somewhere in the song). Legacy callers without section observations still get previous whole-song heuristic.
- Only explicit parenthetical authored stage/performance notes from `section_lyrics` are considered for simple intimate/expansive direction cues. The planner does not infer author intent from lyric text itself or pretend to have semantic audio understanding. The original lyrics and cues remain unchanged. The existing mix, stems, project scripts and assets remain unchanged until a user explicitly reviews and imports.
- Compact UI evidence shows count of section-stem readings. Tests added for absent/active stem across two sections, vocal absence preventing ducking, duplicate split-child lanes, explicit cues vs lyrics, and regressions for original protections. Windows execution of revised tests and build **not yet verified**.

QA: update dev, launch, generate default and spatial-movement plans for Blackbox Gospel. Compare sections where a backing stem enters/exits, check that staged effects follow the active source, review in existing whole-song editor and ensure no overwritten lyrics, existing automation, or automatic application. Inspect plan's Changes/Evidence for section-local readings. Listen for inappropriate early ducking and changes on silent stems.

Remaining limitations: Per-stem **post-effects** section analysis, semantic understanding from MOSS/SMU and cross-stem overlap, proposed-mix loudness matched A/B, editable profile history, and adaptive overall loudness solver are still future work. Split-channel optimization remains explicitly pinned for a later slice.


## 2026-11-16 Slice C4: reviewed musical understanding (dev, untested on Windows)

User reported the previous section-local stem activity slice builds clean and instructed proceeding. Dev remains the only updated branch. The next slice integrates user-confirmed expressive direction as provider-neutral context, **without allowing experimental Q4 text to authorize script changes**.

Delivered:
- `production_context.py` new durable JSON sidecar under `<runtime>/data/jobs/<id>/generated/production-context.json`. Revisioned, atomic and non-destructive; user-saved per-canonical-section directions: intimate, restrained, ominous, rising, expansive, driving, suspended, neutral. Optional short intent note. Origin `author` or `q4-reviewed`, with mandatory source run ID and SHA for Q4-reviewed entries.
- `server.py` GET/PATCH `/api/projects/{ident}/production-context`, read-only `/api/projects/{ident}/production-listening`, using existing song identity/local-origin protections and write lock. Q4 review is offered **only** for the last complete, nontruncated Q4 run on exactly one canonical section of the same project with an analysis snapshot. Source is still unverified; model claims about tempo, chords, lyrics and instruments are **not parsed or auto-accepted**. Backend checks explicit user-confirmed Q4 origin against run ID, snapshot ID's project/section and source SHA. Prior reviewed entries remain valid historical records and don't require the currently active Q4 job when saving a separate section.
- `ProductionContextReview.tsx` collapsed editor in Production Planner: choose section, tone, optional note and basis; optionally inspect an appropriately scoped Q4 review and explicitly confirm it. Save/Clear/Refresh with revision checks, no auto-run of model and no changes to section text. The next plan-generation action reads only saved human-reviewed context.
- `production_planner.generate()` now accepts reviewed context as a separate, validated input, respecting existing artist/authored effects, lyrics, section metrics and stem activity. Confirmed tone can shape lateral separation, spatial reflections/reverb and voice-keyed ducking. Explicit parenthetical lyric-stage directions remain available as fallback. No generated plan is automatically accepted. UI displays count of reviewed sections in evidence.
- Offline tests `test_production_context.py` and additional `test_production_planner.py` fixtures verify save/revision/provenance, rejection of invented model claims, and unchanged original lyrics/automation.

**Known safety caveats / not claimed:** This is a human-in-the-loop MOSS bridge, **not automatic semantic extraction from Q4**, since Q4 was known to invent structure, BPM and instruments. A previously reviewed Q4 context is historical source-specific evidence and does not currently perform automatic full-mix freshness checking; when arrangement/mix changes it should be re-reviewed. Orphaned context after section-ID changes currently fails loudly with a conflict instead of silently remapping. Split L/R fine-grained planning, post-effects per-stem section metering, tempo/harmonic SMU fusion, editable production profile and loudness-matched A/B remain pending.

**Windows QA checklist:**
1. Update/relaunch `dev` and verify TS/Vite build and backend startup. Run `python -m unittest discover -s app/backend/tests -p 'test_production_context.py' -v` plus existing `test_production_planner.py`.
2. Blackbox Gospel > Production planner > **Reviewed listening context**; save an authored direction for one actual section (e.g. ominous or rising), generate plan; check the count and altered eligible spatial/duck suggestions. Reload tool, confirm persisted context.
3. If a current Q4 run exists and is a complete **single-section** Blackbox Gospel review, inspect it and explicitly confirm tone. A Q4 run on another song, external WAV, whole mix or multiple sections must **not** be offered as section-level evidence.
4. Change saved direction and re-generate; ensure prior proposal is cleared, no auto-import or overwrite, and existing section text unchanged until reviewed and explicitly accepted.
5. Test Clear, stale revision conflict, quiet sections and rejected invalid/unaligned review provenance. The open tool and default plan should work even without Q4 installed or having analyzed Blackbox Gospel.

Source implementation is committed to `dev`, but **this slice is not yet Windows build/unit/lifecycle validated**. No automatic model inference, downloads or changes to project audio occurred.


### Reviewed-context follow-up safeguards

- Orphaned per-section reviews are now archived when saved section IDs are retired; archived records are retained in the sidecar for audit and excluded from new section proposals. Fresh edits containing unknown IDs are rejected rather than silently archived or remapped.
- Existing Q4-reviewed notes can be edited or saved in subsequent sessions without the old Q4 worker still being active. The original model run identity and snapshot hash remain attached. A newer Q4 run never silently replaces that approval's provenance; to attach a new run, clear and explicitly review again.
- Source model output remains unverified, optional, explicit-review only. No Q4 inference is launched by opening or generating a Production Planner draft.
- Additional regression fixture checks archived retirement and restoration behavior. Latest source revision: `c011b63` on dev, pending Windows build and regression execution.


## 2026-11-16 QA: narrow role coverage despite clean build

User confirmed dev build clean but the plan still gives only modest adjustments to Other, Piano and occasional Guitar. Root cause verified in `production_planner.generate`: the generic eligible-source pool **explicitly excluded Vocals/Bass/Drums** (`protected_aliases`), and only the remaining eligible pool received spatial planning/ducking. Human-reviewed direction alone did not make those rhythm/lead roles participate.

Dev correction:
- Keep the independent backing-stem spatialization logic and existing authored automation guards.
- Add **separate role-aware rules** (only when source is active in the section per measured sample coverage/RMS, with legacy source evidence fallback): Vocals receive direction-aware reverb depth without panning the lead; active drums receive an opt-in bounded +0.7 to +2.0 dB transient-preserving gain lift in chorus/expansive/driving passages *only with at least 3.5 dB measured mix peak headroom*, or restrained industrial reflections in darker bridge passages; bass receives subtle reflections in ominous/suspended passages while maintaining its central low-end anchor. All routes respect solo/mute/zero-gain state, current authored directives across the song, and existing exact section boundaries.
- Explicitly **did not** automatically compress aggressive drum crashes. A prior idea for default drum compression was replaced with bounded lift to keep messy impact. Peak prediction remains approximate; a proposed dry drum lift needs post-render headroom and mono QA.
- Added regression tests covering vocal/drum/bass involvement, absence of unintended pan for these roles, preserved lyrics, and silence/author protection.

Current implementation is still a **heuristic** compiler, not musical phrase identification, multi-provider model reasoning, verified loudness-matched A/B or a mastering limiter. The aim of this incremental change is broader, meaningful section direction grounded in actual audio and authored performance tags. There is no fake promise of automatic perceptual level matching.

QA after updating dev: rebuild and compare Blackbox Gospel with Spatial movement 85 / Dynamics 75. Expect role directives for active Vocals, Drums and Bass when appropriate and when no prior author control blocks them. If missing, inspect existing authored automation and section-level stem activity, not force commands. Audition drums with peaks monitored (no clipping). Existing stage/apply workflow remains explicit and non-destructive. Production main unchanged.


## 2026-11-16 QA: broadened production is more interesting; channel-level work next

User listening QA after role-aware pass: **"Looking better/more interesting."** Still observes primarily `space`, `reverb`, and `duck`, and **effects target whole parent stems rather than their existing left/right channels**. This is a useful positive checkpoint but NOT approval of a finished planner.

Source contract review:
- `section_production.source_map(..., channel_children)` already exposes valid `<alias>-left` and `<alias>-right` virtual channels for actually split parent stems. No new splitter or routing engine needed.
- `production_planner.generate` still builds candidates from parent aliases, excludes left/right children from its eligible pool, and refuses lateral pan for split parents. Role-specific treatment of vocals/bass/drums acts on parents.
- Existing `SharedClockAudition.sourceSectionProfiles` returns dry source statistics, but does not currently report reliable separately attributed **post-effect L/R split-child** activity per section. Treat this measurement gap honestly.

Next recommended slice:
1. Extend planner evidence input with verified split-child identities, section-scoped channel activity and independently measured L/R RMS/width/balance; preserve original parent-child alias binding and channel-specific author directives.
2. Use `<alias>-left` / `<alias>-right` for **complementary, bounded, reversible** spatial work: gradual pan shifts, asymmetrical reverb/space sends, careful width or gain modulation, and selected end-of-section ramps; do not decorrelate low bass/kick or accidentally collapse the original stereo scene. For near-mono input, work with distinct rendered split lanes only when measured differences support it; avoid fake widening.
3. Broaden to additional compatible directives where measured evidence and existing author intent justify them (pan, width, gain, selected EQ), rather than inflating the directive count with unnecessary movement. Keep lead intelligible, aggressive drum transients, headroom and mono integrity.
4. Run parser and round-trip tests with split virtual aliases, authored left/right overrides, muted/silent channels, absent split assets, and section transitions; all plans remain unsaved previews.
5. Follow with rendered proposal-vs-original level-matched A/B and measurable effect QA. No claim of automatic perceived-loudness consistency yet.

Do **not** treat the user's feedback as proof of runtime pass for any new implementation. As of this entry, this is a captured next-slice design decision and QA note, not a claim that split-child optimization is implemented.


## 2026-11-16 next implementation: channel-aware production planner (Windows QA pending)

User approved proceeding after noting that the planner is improving but still mostly generates `space`, `reverb` and `duck` on parent stems instead of treating already split left/right channels independently.

**Committed on dev**:
- `SharedClockAudition.splitSectionProfiles(sections)` reads the **actual active, split source lane buffers** already installed in the synchronized mixer (`<filename>:left` and `:right`), compares sample-aligned raw lanes over canonical sections, and outputs bounded section-local left/right RMS, dry inter-lane correlation, and temporal coverage. This is a dry measurement, not a post-effect mix meter.
- Production Planner frontend passes `split_sections` alongside existing per-section mix and parent-stem evidence. Server bounds this input to 4096 rows and planner rejects nonfinite, out-of-range, duplicate and unknown source/section measurements.
- Planner cross-checks `channel_children` and `section_production.source_map` for **verified, script-addressable** `Stem-left`/`Stem-right` aliases. It only generates split directives where *both real lanes* have sufficient active signal (>= -48 dBFS, >=40% temporal coverage). It **does not** invent split assets, assume near-mono channels are independent musical instruments, or repan the already hard-L/R channels.
- Complementary, bounded `<alias>-left.space` and `<alias>-right.space` across sections introduce differentiated reflections (different values, with direction/section-sensitive amounts). For **measurably differentiated** L/R dry channels only (correlation <.985, similar channel levels, enough headroom and dynamics ambition), a modest -0.8 dB gain adjustment of the stronger channel is proposed. Correlated/near-mono channels get reflections but no fake gain/pan/width claim. Aggressive low-end/drum parent roles remain protected by excluding them from split optimization in this increment.
- Parent-generated `space`/`reverb` proposals now exclude split rows; the original existing author controls on parent and children are protected. On later section loss of both channel signals, generated child space/gain values are returned to neutral through valid scripted ramps. No project state or audio mutates until the user explicitly accepts the proposal in Section Text.
- Added regression coverage in `test_production_planner.py`: actual split L/R directive output, parent/child authored controls, absent routing, silent/weak lane, and return-to-neutral after dropout. Existing section text/lyrics/import round-trip guards remain.

**Important constraints / next improvements**:
- Raw L/R source evidence is not the same as *post-effects* per-child mix; results must be auditioned and headroom/mono checked.
- Near-identical channels can be treated differently with bounded reflection sends, but this should not be represented as verified independence or guaranteed mono compatibility.
- The existing mix analysis and project section scripts still set the creative and safety constraints. No automatic `auto.gain`, time-warp, melody transcription or large EQ shift was introduced.
- A later step should render original/proposed audio for level-matched A/B and measured mono/headroom QA before automatic accept. Channel-specific EQ and more adventurous movement can be considered after those safeguards are demonstrated.

**Windows QA** (not executed by GitHub connector):
1. Update and relaunch dev; confirm TypeScript/Vite build and backend startup. Run backend `python -m unittest discover -s app/backend/tests -p 'test_production_planner.py' -v`.
2. Blackbox Gospel > Production planner > Spatial movement 85, Dynamics 75. Generate. Verify active split backing stems now yield `<name>-left.space` and `<name>-right.space` with different values in appropriate sections, plus occasional bounded channel gain only where measured variation/headroom supports it.
3. Verify absent split files, absent/quiet L/R lane, or absent section coverage **do not** trigger new child controls. Existing authored parent and child effects remain untouched; no accidental change to hard-panned routing.
4. Audition the result, checking lead clarity, drum transients, and mono compatibility. Verify current saved project untouched until explicit Review in editor / Apply.
5. If no split directives appear, inspect actual `channel_children` export registration, active mixer split track keys, dry lane RMS/correlation and authored effects: the generator intentionally fails closed on missing or weak evidence.

Latest code changes are on `dev` only. No production merge. QA gate remains open.


## 2026-11-16 QA blocker: split child `.space` rejected

User reported `Production preview rejected: Child split channels currently support gain, pan, EQ and reverb only` immediately after first split-channel planner deployment. Confirmed against actual `app/backend/section_import.py` child compatibility validator: child directives support `gain`, `pan`, `eq`, `reverb`, `reset`, not `space`. My planner's initial L/R generator wrongly issued `Stem-left.space` / `Stem-right.space`, then attempted to reset `space:0`. This was a **planner bug**, not an issue with the user's stems or project.

**Fixed on dev:** L/R asymmetrical sends and corresponding reset transitions now use **`<alias>-left.reverb:<percent>` / `<alias>-right.reverb:<percent>`**, a supported child effect. Parent `.space` remains available and unchanged for unsplit sources. Child gain correction continues to use existing supported `.gain` syntax. Existing user-owned parent reverb automation blocks competing new child reverb proposals. Tests updated for author protections and neutral resets, with a new regression fixture checking actual full-script `section_import.apply(..., "replace", ...)` round-trip of near-correlated split channels to catch this type of API-contract mismatch.

**QA gate:** Update/relaunch `dev`, regenerate Blackbox Gospel plan, check successful preview and child `.reverb` rather than child `.space`. Inspect emitted lines for valid existing parent/child scripts. No build or Windows runtime verification performed via GitHub connector. No production merge.
