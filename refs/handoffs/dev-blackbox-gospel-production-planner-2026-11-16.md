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
