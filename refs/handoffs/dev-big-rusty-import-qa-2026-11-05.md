# DEV handoff: Big Rusty Drums import QA
Date: 2026-11-05
Branch: dev only; production main pinned at 2345c61d57407b62cf809fd4f2c68b972eb60f89.

## User-confirmed status
- Big Rusty Drums ZIP imported successfully in the Windows DEV app.
- Exact result: "Imported 26 playable SFZ instruments (3 incomplete programs excluded; e.g. k_rc_sn)."
- No visible loading/generating state during pack import.
- Completion message lacks a clear action to investigate or repair incomplete entries.
- User wants state documented for a new conversation, not more code in this turn.
- Sticky piano-roll pitch column and section row were previously reported working well.
- No user QA yet confirming that imported drum programs render or that missing-sample repair works.

## Meaning of the result
26 denotes validated SFZ instrument definitions, not drum-kit pieces. Three excluded programs do NOT necessarily mean only three missing samples: each program may have multiple broken dependencies or another validation issue. k_rc_sn might be an included mapping snippet, not an intended standalone kit. Inspect its dependency graph and the installed manifest before treating it as a missing user-facing instrument. Import validation success is not audio playback success.

## Implementation already on DEV
- app/backend/sfz_pack.py: bounded ZIP import; safe ignored support files, nested #include and #define handling, *silence support, recursive program-specific dependency validation, incomplete program exclusion and persisted count.
- app/backend/sfz_sample_recovery.py: explicit local-first exact audio match and curated versioned publisher lookup. No arbitrary URL downloads, no sample substitution, no overwrites; up to 8 repairs, 16MB/file and 64MB total. Failure preserves installed pack.
- app/backend/server.py: same-origin POST /api/instruments/sfz/repair-missing, only pack ID, server lock.
- app/backend/instrument_library.py: curated pack provenance and incomplete program count exposed across relaunch.
- app/frontend/src/BassMidiTool.tsx: installSfzPack() sets installingPack, disables inputs, displays text result, but has NO VISIBLE import spinner or blocking busy feedback. repairSfzPack() exists. Repair button currently depends on selected pack filter (recoveryTarget), making it hard to discover from the result.

## Next thin slice: fix the user-facing workflow
1. Immediately show an accessible, visible indeterminate Importing... indicator from selection through upload, ZIP extraction, validation, and library refresh. Prevent accidental duplicates without covering the editing canvas. Do not fabricate progress percentage.
2. Make the completion message actionable: "Big Rusty Drums imported. 26 instruments ready; 3 programs need attention." Display a compact Repair missing samples action directly alongside that result when curated provenance is present. Never require hunting through the pack dropdown.
3. Keep detailed program names, failures and repair sources behind a small info/inspection icon. Distinguish incomplete program count from missing sample file count.
4. Show recovery busy state and final result clearly: successfully recovered exact files, still-incomplete programs, or exact official source unavailable. Leave working programs playable.
5. Keep recovery offered after relaunch and when selecting an incomplete curated pack. Generic uncurated ZIPs do not get remote repair.
6. Follow shared TWS-Design-Principles, apps/App-Design-Principles.md: happy path first, quiet readiness, progressive disclosure, scroll safety.

## After UX fixes: audio QA and drum replacement
- Confirm whether 02-basic and other imported entries are actual standalone playable kit programs rather than mapping snippets.
- Audition Big Rusty kit notes: kick 36, snare 38, hats 42 and 46, toms 41/43/45/47, ride 51, crash 49. Verify actual SFZ mappings, not assumed GM equivalence.
- Only then assess drum-onset transcription/classification, custom key mapping and one combined stereo replacement stem with reversible source volume masking.
- Never auto-render or accept an instrument merely because it imported.

## Test / source pointers
Frontend: app/frontend/src/BassMidiTool.tsx (installSfzPack, repairSfzPack, recoveryTarget, installingPack).
Backend: app/backend/sfz_pack.py (audit_pack, install_zip); sfz_sample_recovery.py (repair); instrument_library.py (catalogue).
Tests: app/backend/tests/test_sfz_pack.py and test_sfz_sample_recovery.py; npm run build in app/frontend.
Tests committed previously, not executed in GitHub connector session.
Preceding handoff: refs/handoffs/dev-integrated-sfz-sample-repair-2026-11-05.md.
Stay on dev. Main unchanged.


## Follow-up QA and prioritization: 2026-11-05, after frontend feedback slice

User screenshot confirms:
- Import progress indicator worked while importing War Tuba; War Tuba had no incomplete programs to test recovery.
- Big Rusty Drums selected as a previously installed pack initially shows no prominent incomplete-pack warning or actionable repair entry.
- Reimport produced 26 ready SFZ definitions and three incomplete definitions; inspection icon works and reveals exact errors:
  - k_rc_sn: `../Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac`
  - k_sc_sn: `../Samples/kick_24/sc/sn/k_sc_vl1_rr1.flac`
  - k_tc_sn: `../Samples/kick_24/tc/sn/k_tc_vl1_rr1.flac`
- Still no user-visible repair button after reimport.

Decision: **Defer repair UX/provenance fixes while testing full-kit audio.** Three errors are kick-related missing sample references, not evidence that the validated top-level `01-full` program is unusable. 26 playable SFZ definitions have passed file-level validation, but no actual audio render has been verified, and no proof yet that `01-full` contains all needed drum articulations. Do NOT claim these three definitions are unneeded until kit audition and mapping inspection.

Likely defect to revisit: The generic Import SFZ flow passes no `curated_id` and installs the pack with `curated_id=""`; the existing repair action requires `curated_id` to be present. The screenshot's ZIP-derived pack name is compatible with generic import, but does not prove which import path the user used. Reimport may simply have repeated the generic path. Even when the catalogue retains an unavailable-program count, the UI only exposes repair for curated packs, and no passive incomplete warning appears on pack selection or after relaunch. In addition, the installer manifest currently stores an incomplete count but not the individual failed programs, so detailed diagnostics for an older import are not persisted.

Follow-up repair backlog:
1. Surface a compact persistent warning on selection of any incomplete installed SFZ pack, even generic packs, without dominating the editing canvas.
2. Expose an Inspect action that can re-audit installed SFZ program definitions on demand and show each failed dependency and whether it is a mapping fragment or independent instrument. Do not equate failed program count with missing audio file count.
3. Safely identify known curated packs at generic import via verified provenance or explicit user confirmation, not a filename-only trust upgrade. Only then offer approved version-specific publisher repair; preserve opt-in, size limits, no substitution and no overwrite.
4. Offer local exact-sample repair for generic packs only when source and destination are verifiably inside the installed pack or a user-selected archive; no arbitrary remote fetch.
5. Avoid reimporting ~620 MB solely to see diagnostics or invoke repair. Check persistent status after relaunch.
6. If full-kit playback reveals missing kick articulations, elevate repair priority and inspect the precise SFZ dependency graph and original ZIP before choosing recovery.

Immediate drum QA gate:
- Audition `01-full` plus a second verified complete kit, using actual SFZ note mapping rather than assuming General MIDI.
- Establish audible kick, snare, closed/open hats, toms, crash and ride with appropriate velocities; note silent notes and unknown mappings.
- Only then proceed to drum onset classification, editable key mapping, and one combined stereo drum replacement stem with reversible original-volume masks.
- No changes to `main`; this appendix is documentation only.
