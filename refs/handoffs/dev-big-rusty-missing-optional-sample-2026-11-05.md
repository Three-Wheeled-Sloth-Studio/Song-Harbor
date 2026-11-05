# DEV checkpoint: Big Rusty Drums optional missing sample
Date: 2026-11-05
Branch: dev only; main pinned at 2345c61.

## User QA
Import failure after previous safe #include/#define and *silence fixes:
  SFZ references a missing or external sample: ../Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac

## Root cause / evidence
The exact path appears in publisher's Programs/mappings/kick_24/k_rc_sn.sfz. Github source fetch for Samples/kick_24/rc/sn/k_rc_vl1_rr1.flac returned 404; cannot confirm whether binary exists in user's 1.100 release ZIP without inspecting it locally. Publisher 01-full.sfz contains many specialized kick mechanic and click articulations; 02-basic.sfz uses a smaller known subset. Previous importer rejected entire ZIP for one missing sample in *any* SFZ mapping, even if that mapping wasn't referenced by a viable selected program. Thus it was stricter than necessary.

## DEV changes
- app/backend/sfz_pack.py performs recursive program-scoped validation. It discovers standalone programs (those not used as #include snippets), walks each program's include tree, checks only references needed by that program, and excludes any program with incomplete/missing sample or included dependency.
- Paths still must resolve to existing files within pack; unsupported directives, symlinks, traversal, zip bomb limits and missing samples remain blocked for any advertised program. No files are invented, copied from outside, rewritten or silently substituted.
- If at least one valid program exists, import completes with only validated programs available in library. If all programs are invalid, fails and deletes staged pack.
- Import JSON returns unavailable_program_count and a bounded diagnostic list (20) with program names/reasons; Stem Tools confirmation reports playable vs excluded program counts.
- New tests: one missing optional k_rc_sn sample and complete 02-basic program -> imports only 02-basic; all-incomplete pack -> rejects; prior traversal and sample tests retained.

## QA next
1. User updates DEV and retries exact same ZIP. No redownload.
2. Expect one or more imported playable programs; select 02-basic for first drum audition, if available.
3. Import confirmation should mention excluded programs if any. If the basic kit is excluded too, capture the exact error.
4. The installed SFZ programs' include and MIDI keymap behavior with sfizz remains untested; import success does not establish audio correctness.
5. Run backend unit tests: python -m unittest discover -s app/backend/tests -p 'test_sfz_pack.py' -v. No actual user's ZIP or Windows tests available in this session.

Future improvement: instrument inspector should expose per-program missing sample diagnostics. Do not confuse a publisher-provided optional missing sample with path validation errors caused by malformed packaging.
