# Vocal pan smoke test: "The Logo and the Maw" (4:00)

This fixture is for the local song already marked with the exact timestamps below. It deliberately preserves the lyric content. Import using **Sections > Replace existing**, not Append. All six stems may remain split L/R. The Vocals directive controls the combined vocal stereo group and does not collapse child channel routing at center.

```text
[Intro 0:00-0:12.323]
{Vocals.pan:center@1s:smooth}
(whispered, distant)
Salt in the circuit, rust in the vein
Black water calling my old name again
Hull full of secrets, hands full of wire
Night on the ocean, bright mouth of fire

[Verse 1 0:12.323-0:34.429]
{Vocals.pan:left.60@2s:smooth}
We drag the wake where the dead nets swing
Sell what we find to the pale neon kings
Steel in the water, ghosts in the foam
Every black tide says the machine wants home
I seen the red lights blink through the mist
Cold little saints with a barcode kiss
One for the buyer and one for the grave
One for the fool who gets paid to behave

[Pre-Chorus 0:34.429-0:45.409]
{Vocals.pan:center@2s:smooth}
Count the crates and count the bones
Count the voices in the radios
Count the seconds, count your breath
Everybody on this deck owes death

[Chorus 0:45.409-1:09.278]
{Vocals.pan:right.60@2s:smooth}
Hoist and haul, keep your head down low
The sea keeps score and the red lights glow
Hoist and haul, hear the long horn moan
No one owns the tide, but it owns us all
Hoist and haul, feel the cables strain
Blood in the bilge and oil in the rain
Hoist and haul, sing it soft, not loud
The ocean takes the lost and feeds the crowd

[Verse 2 1:09.278-1:31.339]
Saw a girl with a halo spine
Chrome in her jaw and a contract sign
Said keep moving, keep stacking the dead
Corps pay extra when the data is fresh
Saw a boy with a prayer in code
Hands on the rail where the black moss glowed
He said freedom is a word men sell
Right before they trade your name as well

[Pre-Chorus 1:31.339-1:42.324]
{Vocals.pan:left.60@2s:smooth}
Count the scars and count the tags
Count the things in the dragging bags
Count the lies that the buyers tell
Heaven looks a lot like a cargo cell

[Chorus 1:42.324-2:05.355]
{Vocals.pan:right.60@2s:smooth}
Hoist and haul, keep your head down low
The sea keeps score and the red lights glow
Hoist and haul, hear the long horn moan
No one owns the tide, but it owns us all
Hoist and haul, feel the cables strain
Blood in the bilge and oil in the rain
Hoist and haul, sing it soft, not loud
The ocean takes the lost and feeds the crowd

[Bridge 2:05.355-2:28.384]
{all.reset@2s:smooth}
(sparser, eerie)
In the hold, in the hold
Something learning in the cold
In the wires, in the teeth
In the prayers beneath the reef
And the bosses on the shore want a cleaner kind of sin
And the thing below the hull only wants to let us in
And the line between a wage and a collar made of steel
Gets thinner every time we trade a wound for one more meal

[Instrumental 2:28.384-2:38.955]
(chanted, layered)
Drag the chain
Mark the gain
Salt the wound
Hide the stain
Drag the chain
Mark the gain
If it speaks
Do not say your name

[Verse 3 2:38.955-3:02.815]
{Vocals.pan:left.60@2s:smooth}
Morning never really gets here now
Just a paler shade of anyhow
We cash our checks in a drowning town
Buy fake halos when the lights go down
Some men serve the logo, some the maw
Some just learn to love the locking jaw
Me, I sing so I can hear what's mine
One thin thread in the engine whine

[Pre-Chorus 3:02.815-3:13.386]
{Vocals.pan:center@2s:smooth}
Count the decks and count the doors
Count what still comes back to shore
Count the ones who came back wrong
Then tell me this ain't just another song

[Chorus 3:13.386-3:48.183]
{Vocals.pan:right.60@2s:smooth}
Hoist and haul, keep your head down low
The sea keeps score and the red lights glow
Hoist and haul, hear the long horn moan
No one owns the tide, but it owns us all
Hoist and haul, feel the cables strain
Blood in the bilge and oil in the rain
Hoist and haul, sing it hard, not proud
The ocean keeps the truth beneath the sound
Hoist and haul, keep the lantern dim
Some get rich and some get taken in
Hoist and haul, when the black wakes call
No one owns the tide, but it owns us all

[Outro 3:48.183-4:00]
{all.reset@2s:smooth}
(soft, fading)
Salt in the circuit, rust in the vein
Black water calling my old name again
Hull full of secrets, hands full of wire
Night on the ocean, bright mouth of fire
```

## Listen/verify
1. The first Verse moves vocals left at 0:12.323, its Pre-Chorus recenters at 0:34.429, and the first Chorus moves right at 0:45.409.
2. **Verse 2 has no brace line:** it should stay right. This is the inheritance check.
3. The next Pre-Chorus moves left at 1:31.339, next Chorus right at 1:42.324.
4. The Bridge `all.reset` centers all section-automated pan and should not change mixer mute/solo/volume.
5. After the Verse 3 left target, the final Chorus shifts right and the Outro resets to center.
6. Pay particular attention to L/R phase/timing and the previously troublesome middle-song passage. Do not combine the already split child audio with its inactive stereo parent.
7. Reload and confirm brace lines survived. WAV export is intentionally blocked while automation is present.

Known constraints: Pan-only; no reverb, width or processed offline export. The 60% moves are deliberately exaggerated to hear them clearly; they are NOT recommended final mix settings.
