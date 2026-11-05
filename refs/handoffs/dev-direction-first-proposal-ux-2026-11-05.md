# DEV checkpoint: direction-first MIDI proposal UX
Date: 2026-11-05
Branch: dev ONLY. Production main stays frozen at 2345c61.

## Why
User screenshots showed the piano roll trapped beneath verbose matching and mock diagnostics, with no main workspace remaining. Matching, applying presets, generating mock velocity changes, inspecting a 240-row diff, and rendering were competing as separate full-width panels. Existing TWS-Design-Principles already prohibited this but the implementation ignored them.

## User-specified happy path
Enter instrument direction -> subtle readiness/icon state for installed preset mapping -> Generate proposal -> compact preview/accept or inspector -> render one combined instrument stem when ready. The user should not need to read explanations or explicitly run Match Library. MIDI and library detail should remain available through icon inspectors, not occupy the canvas.

## Implemented
- One visible direction textarea, one primary Generate proposal button. No Match Library, Apply verified presets or mock-generator button in primary UI.
- Readiness icon (green ready, amber checking, red error/attention, quiet neutral otherwise) with hovertext. Local instrument matching is debounced while typing and stays nonblocking. Click icon to inspect matched default and section variants.
- Separate compact icon for proposed MIDI/recipe changes and another for manually reviewing/editing section presets. A nested Test inspector contains the offline mock velocity generator (dev tooling).
- After Generate, proposal appears in state with checkmark accept and x discard icon buttons. Clicking accept is the explicit acceptance: no redundant confirmation modal. Backend revalidates under project lock, saves a revisioned score, and does not affect audio. Existing Render is still separate.
- Floating inspector is default closed and scrolls internally. Outside click or Escape closes without destroying the editor. Piano-roll container now scrolls vertically and retains at least 180px of editable piano roll content. No large preview panels remain in the primary layout.
- app/backend/midi_proposal_direction.py and POST /api/projects/{ident}/midi-arrangements/{asset_id}/proposal-direction: deterministic, grounded matching of named installed presets to default and song section kinds. Reuses provider-neutral midi_proposal_preview and existing guarded accept endpoint. It is **NOT an LLM** and **does not generate new melodic or rhythmic MIDI notes**; unmatched style instructions remain a future composition task.
- Pass selected stem alias from BassMidiTool into MIDI tool; source Vocals rejected by backend direction route.
- tests/test_midi_proposal_direction.py includes multiple choruses, unsupported variant, and missing selected section scope.

## Shared design governance
Also updated Three-Wheeled-Sloth-Studio/TWS-Design-Principles main apps/App-Design-Principles.md with normative section 25: Happy-Path First (one primary action, quiet readiness icons, off-main diagnostics, mock tooling hidden, scroll and viewport UX gate). Cross-project design repo commit fe9b76b.

## QA gates (NOT yet run here)
1. Windows DEV auto-update and TypeScript build. New code not compiled or executed by connector-only environment.
2. Open 243-note piano roll at default and compact window sizes: direction row and most of piano roll must remain visible. Resize height and verify full panel scroll; inspector must not occupy permanent editor height.
3. Type 'Growlybass Dirty as default, Angry for choruses, Shifty for bridges...' Mapping icon should turn green after local library match (or red if unresolved) without clicking any secondary action.
4. Click Generate proposal; inspect mapping icon and diff icon. Proposal should include Dirty default, Angry on choruses, Shifty on bridges; *no note edits claimed*. Status indicates only preset mapping is supported, not 'industrial' MIDI arrangement.
5. Click ✓ to accept; saved revision increments; reopen should restore section-scoped presets; existing Render creates section previews, then existing combined acceptance adds one stem.
6. Discard, stale revision, no installed pack, vocals, empty direction, small window and Escape/outside click must be safe.
7. Tests: test_midi_proposal_direction.py, test_instrument_direction_match.py, test_midi_proposal_preview.py, test_midi_arrangements.py, test_section_instrument_selection.py. Check connected frontend build.

## Next
- Actual local LLM generation for musically meaningful note/arrangement changes (optional Ollama), still via structured proposal schema and explicit review.
- Secondary toolbars should be audited for reducing icon clutter and ensuring inspector focus in compact viewport.
- Confirm combined audio stems, source masking and channel routing via user's functional QA, not just clean build.
