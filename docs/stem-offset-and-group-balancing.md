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

## Implemented: group-scoped gain and pan balancing

```text
[Intro 0:00-0:25.045]
{
  group.DrumPair:Drums,Taiko
  Taiko.offset:150ms
}
[Chorus 1:13.569-1:36.195]
{
  Drums.gain:+.75@10s:smooth
  DrumPair.auto.pan:center@10s:smooth
  DrumPair.auto.gain:0@10s:smooth
}
```

A group names stable stem aliases and defines the scope of the solver. `auto.pan:center` conserves total stereo energy balance WITHIN the group, not across unrelated stems. `auto.gain:0` preserves baseline group loudness when a member is boosted, compensating among the OTHER eligible members. Explicit pan/gain directives must remain protected; if constraints conflict, report residual imbalance rather than silently overriding user instructions. Group definitions, import/export and initial group-aware solvers are implemented. Loudness compensation uses section-sampled dry energy, preserves explicit gain and volume, and limits corrections to +/-4 dB. Group pan uses the existing constrained pan solver but only includes that group. Auto-processing remains an estimate, not a mastering guarantee.

Next improvements: group editing UI, named groups outside section blocks, precise processed-signal feedback, nested groups, automatic reinstrumentation membership, explicit per-member lock controls, and group-aware effect inheritance. Current corrections stay virtual and reversible; no source audio is rewritten.

Separate echo/delay-line processor remains planned: slapback, stereo ping-pong, rhythmic repeats, filtered feedback and reliable reverb/echo tails. Do not implement echo by shifting the original stem.
