# ACE-Step accompaniment capability proof of concept

Date: 2026-10-23  
Target: `Call of the Electric Siren`, Pre-Chorus 1 (`71.719`-`82.402` seconds)

## Outcome

The installed ACE-Step 1.5 environment can condition a remix/cover on existing
audio, but it cannot natively perform the desired isolated "add one instrument"
operation with its currently installed model. ACE calls that operation **Lego**.
Lego is supported by `acestep-v15-base` and `acestep-v15-xl-base`; this machine's
native installation contains only `acestep-v15-turbo`.

A proof of concept was still completed without downloading or duplicating model
weights:

1. A 42.703-second context window (`39.699`-`82.402`) covering Verse 1 and
   Pre-Chorus 1 was extracted from the original recording.
2. The native ACE HTTP API generated a source-conditioned solo-cello cover of
   that window.
3. The requested Pre-Chorus 1 interval was cropped from the result.
4. The raw result was validated with Song Harbor's existing
   `htdemucs_6s.yaml` separator. It contained substantial non-cello material.
5. A fallback cleanup retained only the generated bass- and guitar-classified
   components, then low/high-pass filtered and limited them. A second separation
   classified the cleaned layer as 89.7% bass and 10.3% guitar, with vocals and
   drums effectively zero at the measurement precision used.
6. The cleaned result was padded to the original song length and imported into
   Song Harbor as `CelloPOC` / **ACE Cello POC (cleaned)**.

This is a usable audition candidate and a successful end-to-end integration
test. It is not proof that the installed turbo model can generate a true,
isolated cello counterpoint. The cleaned output is a separation-assisted
approximation from a cover generation.

## Located assets

- Song Harbor runtime: `D:\Apps\SongHarbor`
- Song Harbor data root: `D:\Apps\SongHarbor\data`
- Project ID: `586a03b40c9c`
- Project manifest:
  `D:\Apps\SongHarbor\data\jobs\586a03b40c9c\song-harbor.json`
- Original recording:
  `D:\Apps\SongHarbor\data\jobs\586a03b40c9c\Call of the Electric Siren.wav`
- Six original stems: the project `stems` directory, with Bass, Drums, Guitar,
  Other, Piano, and Vocals at 48 kHz stereo
- Section definition: the project manifest contains 13 sections; Pre-Chorus 1
  is the third section, `71.719`-`82.402`
- ACE-Step installation: `D:\Apps\Tools\ACE-Step-1.5`
- ACE checkpoint: `checkpoints\acestep-v15-turbo` (4.46 GB)
- ACE checkout commit: `ca1e85fe9430179831e6bc6be790c332190a3866`
- Generated artifact directory:
  `D:\Apps\SongHarbor\data\jobs\586a03b40c9c\generated\ace-step-cello-poc-20261023`

The ACE checkout already had unrelated local modifications before this
experiment. No ACE source or model files were changed.

## Verified capability matrix

| Capability | Installed configuration | Evidence / limitation |
| --- | --- | --- |
| Reference-conditioned generation | Yes | Turbo supports reference audio and source-conditioned cover/repaint. |
| Preserve an existing full mix and add one new layer | No, not natively with installed model | Requires Lego, which ACE documents as base-model-only. |
| Generate a nominal single instrument | Promptable but not clean in this test | Turbo cover produced strong drum- and vocal-classified energy before cleanup. |
| Extract an isolated track | No, not with installed model | ACE Extract is also base-model-only. Existing Song Harbor separation remains available as a fallback. |
| BPM, key, time-signature controls | Yes | Native API accepts `bpm`, `key_scale`, and `time_signature`. |
| Short targeted generation | Yes | Cover duration locked to the 42.703-second source clip; the requested interval was cropped afterward. |
| Repaint a selected interval | Yes | Turbo supports repaint, but repaint replaces content inside a mix rather than returning an additive isolated layer. |
| MIDI or ABC input | Not verified in the native API | The installed request schema exposes audio paths and semantic audio codes, not MIDI/ABC inputs. |
| Programmatic control | Yes | Native FastAPI server exposes `/release_task`, `/query_result`, `/v1/audio`, `/v1/models`, and `/v1/init`. |

## Native API versus ComfyUI

Direct ACE execution is the recommended integration path for this machine.

The native API starts locally on port 8001, uses the existing native checkpoint,
accepts deterministic JSON/multipart requests, records model/seed/timing in its
result, and does not require translating a ComfyUI graph.

ComfyUI Desktop was running on port 8000; a second helper instance was running
on port 8190 with all custom nodes disabled. The installation includes native
ACE-Step 1.5 text-to-music templates and RyanOnTheInside examples for cover,
edit, semantic blending, and repaint. It does not contain an installed ACE DiT
checkpoint in the Comfy shared model store. The present templates do not expose
ACE's base-model Lego workflow. Using ComfyUI would therefore require additional
weights or workflow/model adaptation and would be less direct for this test.

No model was downloaded or copied.

## Generation record

- API task: `7388d862-c22b-4139-86fc-c94a777363a4`
- Task type: `cover`
- Model: `acestep-v15-turbo`
- LM: disabled (cover skips LM planning)
- Prompt: `Solo low cello only. Dark sinister cello counterpoint beneath a female lead: sparse sustained bowed notes, slow dissonant semitone movement, restrained threatening swells, intimate low register, 84 BPM, 4/4, gothic industrial trip-hop atmosphere. No vocals, no percussion, no drums, no bass guitar, no piano, no guitar, no synth, no sound effects, no other instruments. Preserve the source timing, phrasing, and harmonic contour.`
- Lyrics: `[Instrumental]`
- Seed: `150719` (fixed)
- Steps: `8`
- Guidance: `7.0`
- Audio cover strength: `0.8`
- Cover noise strength: `0.2`
- Output: WAV, 48 kHz stereo
- ACE-reported DiT generation time: `1.58 s`
- Observed submit-to-saved wall time: approximately `5 s`
- Cold API/model startup: approximately `27 s`
- Highest sampled total GPU use: `10,739 MiB`; lowest sampled free VRAM:
  `1,272 MiB`
- Total GPU use after stopping ACE: `2,253 MiB`

The prompt used the supplied 84 BPM specification. Offline beat tracking did
not verify 84 BPM: the drums and piano stems both estimated about 89.1 BPM,
while the full mix returned the double-time interpretation of 172.3 BPM. The
context's strongest simple chroma-profile estimate was F minor. These are
algorithmic estimates, not authoritative musical transcription. Because cover
generation was source-conditioned, the generated phrase still follows the
source timing despite the 84 BPM metadata.

## Output files

Primary deliverables:

- `cello-prechorus1-cleaned.wav` — 10.683 seconds, 48 kHz stereo, 24-bit PCM,
  integrated loudness -17.9 LUFS, true peak -5.3 dBFS
- `cello-prechorus1-cleaned-aligned-full-song.wav` — 341.360 seconds, same
  audio placed at 71.719 seconds and silence elsewhere

SHA-256:

- Isolated: `3A9F3459505601BDF44D5FADEB9B660F9BDB4055BD3C1A039803D4A3F03E0496`
- Full-length: `2D38D9E9F4F6513383838410427F2A336E04368D7F9D3E833291DD79F96D5231`

Evidence retained beside the deliverables includes the input context, raw ACE
cover, uncleaned target crop/full-length alignment, API logs, request payload,
spectrogram, and first- and second-pass validation stems.

The imported Song Harbor track is:

- Track ID: `trk_5831b4da25d54b70`
- Alias: `CelloPOC`
- Display name: `ACE Cello POC (cleaned)`
- Working file: `trk_5831b4da25d54b70 (CelloPOC).wav`

## Validation details

The raw target crop measured -15.1 LUFS and -2.2 dBFS true peak. Its first
six-stem validation distributed energy as follows:

| Class | Energy share |
| --- | ---: |
| Drums | 43.70% |
| Bass | 29.55% |
| Vocals | 22.93% |
| Guitar | 3.81% |
| Other | 0.01% |
| Piano | 0.01% |

That result fails the clean isolated-cello criterion. The fallback kept only
the generated Bass and Guitar estimates. Re-running the same model on the
cleaned file produced:

| Class | Energy share |
| --- | ---: |
| Bass | 89.70% |
| Guitar | 10.30% |
| Drums | <0.01% |
| Vocals | <0.01% |
| Other | <0.01% |
| Piano | <0.01% |

This demonstrates removal of the measurable vocal/percussion leakage under the
same classifier. It does not independently prove cello timbre or musical taste;
the imported track still needs a human audition against the vocal and full mix.

## Recommendation and next steps

1. Audition `CelloPOC` at conservative gain under Pre-Chorus 1. Treat it as a
   candidate texture, not a production-approved cello performance.
2. If it is musically useful, repeat the same method for later pre-choruses and
   choruses, keeping raw and cleaned files for comparison.
3. For a real session-musician test, obtain access to an already-existing
   `acestep-v15-base` checkpoint if one is present elsewhere on the machine, or
   explicitly approve a model download later. Run native `task_type=lego` with
   `track_name=strings` against the context clip. Do not use turbo for that
   claim.
4. Use the native ACE API as the integration boundary. A small Song Harbor
   adapter can later extract a selected time range, submit a task, poll it,
   align the result, and import it through the existing track endpoint.
5. YuE2 is complementary for score-first, MIDI-driven, cover, and whole-song
   generation experiments. Its installed workflows do not currently offer a
   simpler verified isolated-additive cello path than ACE base/Lego, so it is
   not the next step for this specific requirement.

