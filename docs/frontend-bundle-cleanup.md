# Deferred maintenance: Frontend bundle sizing and lazy loading

Status: Planned housekeeping, not a runtime error. Logged October 23, 2026.
Priority: P2, after audio routing/playback regression QA.

## Issue
Vite reports: `Some chunks are larger than 500 kB after minification`.
This warning is informational and does not mean the in-app updater failed.
Current `app/frontend/vite.config.ts` has no explicit chunking configuration.
`main.tsx` eagerly imports `StemMixer`, which eagerly imports the playback
engine, effect tools, analysis tools, section inspectors, and DAW handoff.
The exact generated chunk sizes and imports must be measured during the pass;
we have **not** completed a production bundle composition analysis.

## Scope and level of effort

- Cosmetic suppression: 5-10 minutes, **not** a substantive fix; avoid as
  the first response.
- Targeted true lazy loading of the library -> song workstation boundary:
  ~30-60 minutes; React.lazy/Suspense with an actual fallback and a stable
  import graph.
- Opportunistic lazy loading of substantial nonessential inspectors:
  ~45-90 minutes, only where code-split bundles improve startup or memory.
- Bundle inspection, build tests and update/open-song/audio-tool smoke QA:
  ~30-60 minutes.
- Planning allowance: **1-3 hours**, nominally ~2 hours. A broad
  `StemMixer` restructuring would be a separate 4-8+ hour refactor and
  is NOT justified merely by this warning.

## Implementation guardrails
1. Capture baseline built assets (minified bytes and compressed bytes where
   available), dependency graph and startup network activity. Separate app
   JS chunks from CSS and wasm/model/media content.
2. Add a library-to-workstation dynamic import, ensuring existing
   song/project state and saved working script aren't lost while loading.
3. Lazy-load auxiliary tools only if they are large, infrequently used and
   can mount without affecting clock/transport ownership or open-editor
   draft preservation. Do not split the shared playback clock engine across
   distinct independently initialized audio engines.
4. Do not introduce extra dependencies merely to split chunks; Vite/Rollup
   and React.lazy are already present.
5. Verify update/relaunch, Library and session transitions, waveform,
   playback, sections script edit, A/B, audio forensics and WAV export.
   Confirm that asset URLs and cached static bundles remain valid after
   local updater relaunch. Check network fallback loading/error states.
6. Compare emitted chunk report to baseline and note whether warning
   disappears naturally. Raise `build.chunkSizeWarningLimit` **only**
   if a remaining large chunk is justified and documented.
7. Keep source audio and the 768 MiB decoded-audio playback budget out
   of scope; 500 kB minified JS is an unrelated concern.

## Acceptance
- Reduced initial JS parsing/loading (quantified against captured baseline).
- No warning at default threshold if achievable without artificial
  fragmentation; otherwise documented rationale for intentionally sized chunks.
- Clean CI TypeScript/Vite build and Windows updater/session audio smoke QA.
- No changes to rendered audio, section automation or project persistence.
