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
