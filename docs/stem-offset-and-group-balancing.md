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
