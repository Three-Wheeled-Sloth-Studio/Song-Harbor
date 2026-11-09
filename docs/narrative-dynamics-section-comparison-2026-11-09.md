# Narrative dynamics and section-to-section audition

Status: 2026-11-09 floating-tool UI and section audition integration committed on dev. Frontend build and local browser/audio QA still required.

## User goal
Make section dynamics legible as narrative movement. Compare sections or versions without louder automatically winning. Never auto-correct a deliberate artistic choice.

## Existing foundations
- SectionInsights.ts computes actual post-mix RMS, peak, side/mid stereo width, L/R balance and relative section intensity.
- SharedClockAudition.analyzeMix() renders the full mix on demand; StemMixer passes insights into section header UI.
- Existing A/B in StemMixer bypasses processing and auditions candidates; it is not an arbitrary section-vs-section, level-matched comparison.
- Keep this separate from existing sound cleanup defect detection and auto.pan solver.

## First slice delivered
- NarrativeDynamics.ts exposes inspectNarrativeShifts(): adjacent section differences, detecting changes in RMS, crest-factor proxy, stereo width and balance. These are observations, not defect labels.
- sectionMatchTrim() calculates a bounded, peak-aware RMS gain suggestion for a proposed A/B preview. It does not modify saved automation or audio.
- Unit tests cover level/width changes, silent inputs, clipping limits and adjustment limits.
- Floating-tool UI added in NarrativeDynamicsPanel.tsx, registered in WorkbenchTools, and connected to StemMixer. Preview-only monitor gain added to SharedClockAudition. LUFS normalization, prior-render comparison and local listening QA remain outstanding.

## Next implementation slice: narrative analysis UI
1. Add a 'Narrative dynamics' tool within existing floating-tool system or as a subpanel of Sound cleanup. No giant new modal.
2. Feed it *fresh* SectionInsights from the existing explicit Analyze mix action. Reuse existing stale-data invalidation. Do not render another full-song scan.
3. Show one row per section transition: section names and time ranges, RMS delta (dB), crest factor delta (dB), width delta (dB side/mid), L/R balance shift (dB). Sort chronologically. Toggle a threshold filter, default significant changes only.
4. Support jump-to-section and loop transition (last 2 seconds of A, first 2 seconds of B). No mutation.
5. Optional author-supplied narrative tags ('victory', 'unease', 'dread') are creative intent metadata, NOT inferred truth. Compare measured movement to the stated goal as suggestions only.
6. Avoid judgmental warnings like 'too loud'. Good narrative analysis explains where a mix changes and what is not changing.

## Next implementation slice: section-to-section A/B
1. In existing A/B popover, add comparison mode 'Section vs section' with selectors A and B, initially adjacent sections; an optional 'Current vs previous render' mode requires separately retained prior audio and is not implied by same-project snapshots.
2. Use SharedClockAudition's synchronized clock and existing decoded buffers; route preview-only gain for B, never alter saved stem faders, section automation, or WAV render.
3. Precompute both comparison regions from *actual rendered mix* to avoid mismatch when reverb/automation/effect tails extend across boundaries. Use equal-length windows where possible and show if truncation occurs.
4. Implement loudness match using gated LUFS for sufficiently long windows; fallback to RMS with explicit label for short, quiet or sparse sections. Cap gain and maintain -1 dBFS preview peak guard. Disable matching if either region is silent.
5. A/B switch keeps the same monitor gain and uses a short click-free crossfade. Offer transport controls A, B, rapid toggle and repeat; no automatic continuous playback on opening.
6. Display both raw levels and preview-only trim, with 'Level match ON' default and OFF for checking intended absolute intensity. Preview gain must never persist on Accept.
7. Save analytical comparison data separately from sound corrections, and invalidate on any mix/section edit.
8. For changes to source rendering, preview and export must use matching DSP. Test split L/R, muted stems, offsets, tails and section overlaps.

## Testing and release gate
- Run npm run build --prefix app/frontend, relevant node tests and existing frontend/backend suite.
- Browser smoke test in the actual portable launch on Windows.
- Listening QA at 48kHz: adjacent section transition, short 5-second chant, final chorus vs outro, silence, deliberate stereo imbalance, -1 dBFS peak, ongoing reverb tails.
- Verify no additional render or memory allocation until explicitly requested.
- Check no project mutation, same result after reopen, no automatic playback, and no source/master confusion.
- Do not claim 'level matched' until audible preview switching is wired and verified.

## Parade for the Drowned King acceptance fixture
Expected user-defined arc: genuine communal triumph, subtle unease, mechanical takeover, celebratory final chorus, ambiguous eerie outro. Detect and display changes objectively. Do NOT automatically lower outro or narrow final chorus. Compare 0:55.876-1:21.653 against 2:34.421-3:02.469; then 2:34.421-3:02.469 against 3:02.469-3:47.280. Keep 'Raise the flags and pour the black' unchanged.

Future: compare alternate production renders, narrative target overlay, automated *suggestions* linked to reversible section scripting; never infer genre or author intent from volume alone.

## 2026-11-09 integrated UI slice

- Open **Narrative dynamics** in the right floating-tools palette. Click **Analyze mix**; findings show chronological transitions and a **Listen across transition** action that loops a short boundary window. **Show small changes** includes transitions below the default threshold.
- Open **A/B comparison** and use **Section A** and **Section B**, then **Play A** or **Play B**. The comparison loops the chosen full section. RMS match for B is on by default; turn it off to hear the intended original loudness contrast. Analysis must be fresh for calculated gain; otherwise audition is available without matching.
- Gain matching is audition-only in SharedClockAudition's master monitoring stage; no save/export path is changed. Stopping or closing the tool restores gain. Limit is +/-12 dB with a peak headroom guard based on the last scan.
- Explicitly NOT included: a crossfade between A/B, equal-length windows, integrated LUFS, on-disk prior-version A/B, or automatic narrative corrections. These still need work and should not be described as shipped.
- QA status: GitHub connector successfully wrote the files; no CI statuses or PR-triggered Actions runs were reported for the latest commit. **No build or audible browser smoke test has been executed.** Run npm run build --prefix app/frontend and frontend tests before treating this as release-ready.
