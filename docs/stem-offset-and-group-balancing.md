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

## Next feature: group-aware gain and pan balancing (design only)

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

A group names stable stem aliases and defines the scope of the solver. `auto.pan:center` conserves total stereo energy balance WITHIN the group, not across unrelated stems. `auto.gain:0` preserves baseline group loudness when a member is boosted, compensating among the OTHER eligible members. Explicit pan/gain directives must remain protected; if constraints conflict, report residual imbalance rather than silently overriding user instructions. Group definitions, parser and group solver are not yet implemented.

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
