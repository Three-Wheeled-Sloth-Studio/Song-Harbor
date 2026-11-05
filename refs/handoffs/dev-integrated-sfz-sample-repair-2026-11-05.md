# DEV checkpoint: integrated missing-SFZ-sample repair
Date: 2026-11-05
Branch: dev only. Production main unchanged at 2345c61.

## User goal
Offer a small contextual, safe, integrated attempt to find and retrieve exact missing samples on SFZ pack import, especially curated Big Rusty Drums, instead of failing and requesting manual downloads.

## Implementation
- app/backend/sfz_pack.py: extracted read-only audit_pack(destination). It validates each standalone SFZ program and included sample files. Curated packs with zero playable programs may install *as unavailable* so Repair can be offered; noncurated all-incomplete imports still fail.
- Persist unavailable_program_count into pack manifest; app/backend/instrument_library.py exposes it with curated_id. Unavailable status survives app restart and changing pack selections.
- app/backend/sfz_sample_recovery.py: recover an existing curated pack only by its server-owned ID. Read-only audit first. For each exact missing audio reference:
  1. Parse a bounded Samples/<subpath>.flac/wav/aif/aiff/ogg reference. No arbitrary input paths, URLs, extensions or file substitutions.
  2. Find a unique corresponding sample already inside the imported pack ignoring path case. If necessary, stage a copy under the correct, existing Samples root (including wrapper folders). Do not overwrite.
  3. ONLY on user action, try exact path from the pinned curated publisher GitHub repository tag via raw.githubusercontent.com, not general web search or release archive re-download. HTTPS, no redirects, locked repo owner, configured known source, bounded time and size; allow only recognized audio magic headers.
  4. Check 8 missing references / 16MB per sample / 64MB total per request; re-audit as each repair exposes additional dependencies. Missing source is reported without fabrication.
  5. If at least one program playable, update manifest in staged atomic replace, recompute pack file digest, record provenance. If no program becomes playable, roll back staged new files and return status=unavailable. Exceptions also roll back new files. Original samples and score/audio are untouched.
- POST /api/instruments/sfz/repair-missing accepts pack_id ONLY, requires same-origin request, holds backend lock.
- app/frontend/src/BassMidiTool.tsx: small Repair missing samples action appears only for a selected imported curated pack with incomplete programs. Clicking it explicitly authorizes publisher lookup and summarizes outcome. If pack is completely functional, no repair action appears.
- app/backend/tests/test_sfz_sample_recovery.py: offline mocked curated HTTPS retrieval, local case mismatch, pack wrapper folder, ambiguous Samples folder fails closed, unapproved pack refusal, failed recovery leaves manifest unchanged, existing audio preserved. No live publisher dependency.

## Important limitations / safety
- The publisher's GitHub raw repository may NOT carry every recorded sample. If an exact file is absent, repair reports unavailable. It does not download the full 620MB release ZIP again, query search engines or create substitute samples.
- There are no published per-file sample hashes in the current curated metadata. We validate TLS origin, pinned release tag/path, file size, file magic, and record SHA-256 after import, but cannot prove cryptographic publisher authenticity. The result's provenance notes this explicitly.
- Only complete, validated programs appear in the instrument picker. Repair never automatically renders, accepts audio, modifies the original recording, or replaces an existing sample.
- Only installed user-selected curated packs are eligible; arbitrary imported packs cannot use remote retrieval.

## QA gates
1. Update DEV and build. Backend tests have been added, not executed in this connector environment. Run:
   python -m unittest discover -s app/backend/tests -p "test_sfz_pack.py" -v
   python -m unittest discover -s app/backend/tests -p "test_sfz_sample_recovery.py" -v
   npm run build (frontend)
2. Import the Big Rusty ZIP through its curated Import ZIP action (not generic Import SFZ, which lacks curated provenance).
3. If any program is incomplete, the small Repair missing samples button should appear. Click to approve exact publisher lookup.
4. Confirm incomplete programs remain unavailable and are not advertised as playable. If an exact official file exists, it is staged and published under the correct Samples folder; no existing file overwritten.
5. Confirm attempt of a nonexistent publisher sample reports "no exact replacement found" without changing usable programs. Reopen Song Harbor and ensure repair state persists.
6. Select 02-basic if playable and audition drum notes. Rendering correctness is separate from sample import/recovery.
7. Verify Windows paths/casing and separate-archive wrapper directories, large sample limits, and failure rollback.

## Follow-up
If publisher GitHub raw lacks the audio but release ZIP contains it, avoid redownloading a 620MB archive by using the original user-provided ZIP locally first. That would require retaining or reselecting the source ZIP or storing an approved durable reference. Do not broaden to arbitrary internet search.
