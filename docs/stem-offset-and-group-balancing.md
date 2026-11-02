# Stem timing offset and grouped automation roadmap

## Implemented: static stem timing offset

`Taiko.offset:150ms` means play every Taiko sample once, 150 milliseconds behind its original timeline. It is **not** an echo, feedback, or tempo-dependent delay. Author the directive once in the section text; it applies throughout the song, including split children, playback, seek and export. Supported range: 0-500 ms. To remove, delete the directive and re-import with Replace mode.

```text
[Intro 0:00-0:25.045]
{
  Drums.pan:right.55@10s:smooth
  Taiko.pan:left.55@10s:smooth
  Taiko.offset:150ms
}
```

Future variable offsets must be implemented as clip splits/crossfades, not by jumping the playback cursor within a song.

## Group-aware gain and pan balancing (initial integration; combined QA pending)

```text
[group DrumPair]
{
  Drums
  Taiko
}
[Chorus 1:13.569-1:36.195]
{
  DrumPair.auto.pan:center
  DrumPair.auto.gain:0
  Drums.gain:+.75@10s:smooth
}
```

A group names stable stem aliases and defines the scope of the solver. `auto.pan:center` conserves total stereo energy balance WITHIN the group, not across unrelated stems. `auto.gain:0` preserves baseline group loudness when a member is boosted, compensating among the OTHER eligible members. Explicit pan/gain directives must remain protected; if constraints conflict, report residual imbalance rather than silently overriding user instructions. Group definitions, parser, and derived automation solver are now implemented in the initial slice; combined listening and render QA remain pending.

Initial implementation should: measure group power in short representative windows with timing offsets applied; honor explicit automation, sidechain and pan locks; offer preview and undo; limit automated corrections and expose an intelligible explanation of unlocked members. Follow with nested groups and inheritance after the basic contracts pass.

Separate echo/delay-line processor remains planned: slapback, stereo ping-pong, rhythmic repeats, filtered feedback and reliable reverb/echo tails. Do not implement echo by shifting the original stem.


## Implementation slice: group-aware balancing MVP

Scope: flat named groups only, section-scoped automation, reversible derived gain/pan envelopes. No nested groups, buses, new routing graph, or destructive stem writes in this slice.

1. **Parse and validate** group declarations before section directives. Require unique group names (case-insensitive), existing parent aliases, at least two distinct members, and no duplicate members. Reject cyclic/nested references for MVP. Keep existing per-stem directives working unchanged. Preserve group definitions through export/import and project reload.
2. **Baseline measurement** at the beginning of each section, before proposed group adjustments, using the same offset-aware timeline as playback/export. Measure per-channel energy over representative windows, with silence and near-silence guarded. Use a deterministic baseline snapshot rather than chasing live levels.
3. **Lock hierarchy**: user-authored stem pan/gain automation wins; group automation may only adjust unlocked members. Respect mute, solo, replacement masks, split-child routing, and existing sidechain/ducking. If no free member can satisfy the target, report a bounded residual rather than modifying locked tracks.
4. **Solve** `Group.auto.gain:0` by preserving the group's baseline combined power, distributing compensation over eligible members with bounded adjustments and smooth section transitions. Solve `Group.auto.pan:center` against group left/right energy, without changing unrelated stems. Prevent division-by-zero and runaway boosts in quiet sections. Never interpret `gain:+.75` as an arbitrary 75% volume boost: use the existing gain unit and parser contract.
5. **Preview and undo**: show which members are adjusted, by how much, and whether the target is fully met. The generated automation is derived state, not an edit to user directives. Recompute when group membership, offsets, routing, section boundaries, or source automation changes. Provide a one-action revert.
6. **Parity**: preview, seek, analyzer, and WAV export must use identical computed envelopes. Validate group power on the *rendered* mix, not merely against dry stem statistics.

### Acceptance tests

- DrumPair with Drums and Taiko: raising Drums under `DrumPair.auto.gain:0` lowers only unlocked Taiko enough to maintain baseline group power, within solver tolerance.
- Explicit `Taiko.volume` or `Taiko.pan` locks the corresponding dimension; solver reports residual if target cannot be met.
- A third unrelated stem is byte-for-byte unaffected in its automation and has unchanged gain/pan.
- Offsets of 0, 150, and 500 ms yield consistent playback, seek, analysis, and export.
- Silent stems, very short sections, clipped peaks, opposite-channel material, and all-locked groups do not create NaN, clipping amplification, or runaway compensation.
- Split L/R children, muted members, removed or renamed stems, and reinstrumentation replacement masks have explicit regression coverage.
- Import -> export -> reimport preserves group declarations and user-authored directives; undo restores the original mix.
- A/B audio comparison and deterministic fixture tests pass before shipping.

### Follow-on effect processor (separate from timing offsets)

Add a true wet/dry echo bus with milliseconds and beat-synced time, feedback, low/high-pass feedback filtering, stereo ping-pong, and tail management. Echo repeats must not shift or double the dry source. Test feedback stability, zero feedback, seek, end-of-song tails, and offline render parity. Implement only after the group MVP is validated.

## Implementation status (2026-11-02)

- Pure group gain compensation and group-scoped pan solver adapter added in `app/frontend/src/GroupAutomation.ts`; connected to section scripts and derived gain/pan automation in the later combined slice described below.
- Unit fixtures added in `app/frontend/tests/group-automation.test.mjs`, and included in frontend CI workflow.
- Group parser/storage, offset-aware measurement and derived automation scheduling were added in the subsequent slice. Remaining: robust group preview/undo UI, rendered-output validation, combined listening QA and complete end-to-end testing.
- The gain solver accepts *linear RMS power estimates*, not amplitudes or LUFS. Explicitly boosted stems must be marked gainLocked so their authored gains cannot be overwritten; unrelated stems must never enter the group list.
- Group directives are now accepted by the section script; final audio parity and quality require the combined QA pass.


## Combined echo + groups implementation handoff (2026-11-02)

The initial group scripting and mixing integration is now in source. Group definitions are expressed inside a section's production block, not as a separate section type:

```text
[Intro 0:00-0:25.045]
{
  group.DrumPair:Drums,Taiko
  Drums.pan:right.55@10s:smooth
  Taiko.pan:left.55@10s:smooth
  Taiko.offset:150ms
  Taiko.echo:180ms,18,25,6500
}
[Chorus 0:25.045-0:55.000]
{
  DrumPair.auto.gain:0@10s:smooth
  DrumPair.auto.pan:center@10s:smooth
  Drums.gain:+0.75@10s:smooth
}
```

- `group.NAME:StemA,StemB` declares a flat group once per song. Groups refer to stable parent stem aliases in the script; the backend resolves filenames for execution.
- `NAME.auto.gain:0` requests preservation of approximate dry-stem baseline group power through bounded, unlocked-member compensation.
- `NAME.auto.pan:center` reuses the restrained auto-pan algorithm but is limited to group members.
- `Stem.echo:180ms,18,25,6500` is song-wide delay time, wet percentage, feedback percentage, low-pass Hz. Unlike `.offset`, this adds genuine repeats and preserves the dry source.
- Echo is routed from each stem bus to a wet feedback loop in both live and offline render. Effects are non-destructive. Tail extension is bounded; source media is not shifted.
- Mixer Echo toggle, delay and wet controls are available for quick audition. These are not automatically written to the song script; use an echo directive for a durable setting.
- Backend persists `stem_groups`, `section_group_targets`, and `stem_echo_settings`; section export and subsequent reload carry these settings.

**QA status:** Implementation committed but not yet verified by a successful end-to-end browser/render test in this session. Automated regression tests for parsing, echo validation and group solver were added to their existing suites. Do not claim audio perceptual parity, correct group compensation on real stems, or complete CI success until observed.

### Combined QA to run next

1. Import the example using actual aliases and confirm export/reimport is stable. Invalid group aliases, duplicate declarations and out-of-range echo values must report actionable import errors.
2. Preview and render taiko with 0, 150 and 500 ms offsets. A single dry hit must remain single, while echo creates genuine wet repeats; verify no offset is applied twice.
3. Toggle echo and vary wet/feedback; compare live and exported WAV, including the tail beyond the source duration and seek behavior.
4. Boost Drums with group gain holding baseline, inspect the amount of Taiko compensation and residual if limits prevent complete balance. Confirm unrelated stems remain unchanged.
5. Apply explicit Taiko gain/pan then group automation. Manual values must remain locked; inspect diagnostics and compare processed WAV.
6. Repeat with split L/R channels, solo, mute, accepted replacement masks, audio analysis, export and re-import.
7. Verify high feedback never runs away, silence never produces NaN, and echo changes invalidate stale QC findings.

**Not in this first slice:** tempo-synced echo, ping-pong/cross-channel feedback, nested groups, effect-bus routing UI, fully processed loudness optimization, per-section echo automation, permanent group UI editor. Group solver currently uses dry power estimates; rendered WAV analysis remains authoritative.
