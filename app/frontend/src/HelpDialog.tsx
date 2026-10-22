import {useMemo,useState} from "react";
import {Dialog} from "@tws-ui/core/react";

/** User-facing copy is kept here in one searchable, offline-friendly help view.
 * Update alongside docs/user-guide.md when behavior changes.
 */
type Topic={id:string;title:string;summary:string;body:string[];examples?:string[]};
export const HELP_TOPICS:Topic[]=[
  {id:"start",title:"Start here",summary:"From an audio file to an editable six-stem song.",
   body:[
     "Song Harbor is a local-first music workbench. Open a saved song from Library, or choose Import song and select an audio recording.",
     "The Import screen has two modes: Single recording separates six stems; Multiple tracks accepts 2-64 already recorded/separated audio files, suggests a song title from their common filename prefix, and lets you edit the title before importing.",
     "Choose Separate stems to create Vocals, Drums, Bass, Guitar, Piano and Other. The first separation can take longer while models load. FFmpeg setup appears if required. Multi-track import does NOT perform AI separation; it aligns tracks at 0:00 and pads shorter tracks with silence without time stretching. For a Song Harbor channel-split export, select every mono WAV plus manifest.json in the same import: the app reconstructs original stereo parents and restores active L/R routing.",
     "When processing finishes, use the shared playback transport, waveform and stem mixer. The six stem categories are model estimates: separation can leave some sound bleeding into other tracks.",
     "Use Sections to paste a time-stamped arrangement. Adjust boundaries in the timeline, audition changes, then render and download a WAV."
   ]},
  {id:"library",title:"Library and projects",summary:"Open, rename, group, and keep your work.",
   body:[
     "Library holds saved songs, including separately imported takes. Double-click a song to open its workbench.",
     "Use each row's menu or right-click for available rename, collection, grouping, remove and restore actions. Combining related takes is a Library link, not a destructive audio merge.",
     "Song titles are metadata; changing a title does not rename source files. Remove from Library is reversible; original source media is retained. Multi-track imports preserve each original file plus a WAV working copy, and show its original name in the mixer.",
     "Imported tracks have an immutable internal ID and a script alias shown below their display name. Production directives can address every named track, not just the six default stem categories. Full synchronized audition still has a 768 MiB decoded-audio memory budget; long projects with dozens of tracks may exceed it.",
     "Save project/mixer changes before closing or using the update/relaunch control. Sections Apply persists the section sheet, but unapplied text in an editor will be lost on restart."
   ]},
  {id:"playback",title:"Playback and stem mixing",summary:"Navigation, split channels, and safe audition.",
   body:[
     "Space plays or pauses when you are not typing in an input. Left/Right arrows move by five seconds. Click the waveform to seek; use timeline zoom and the region loop to work on a passage.",
     "Mouse-wheel always scrolls the page, including over waveforms. Song Harbor now uses a right-hand icon tool rail: choose Zoom, EQ, Sections, Split channels, DAW handoff, or another tool to open one draggable floating context panel above the waveform. Close a tool with its ×. Your unapplied Sections text stays in memory when switching tools. Fullscreen app mode is used by the Windows launcher for supported default browsers; the far-right topbar × confirms shutdown and will not kill unrelated browsers.",
     "Each stem has level, mute and solo controls. Parent stereo and derived left/right tracks are mutually exclusive: a split pair replaces, rather than doubles, the original parent.",
     "The shared-clock audio engine keeps stems synchronized. Loading long audio may take time and the audition engine reports if its decoded-audio budget is exceeded; it does not silently fall back to unsynchronized playback.",
     "Monitor volume is for listening only. It does not set the rendered WAV level."
   ]},
  {id:"sections",title:"Sections and production scripts",summary:"Editable timestamps and non-destructive effects.",
   body:[
     "Open Tools > Sections. Each section begins with one square-bracket header, followed by at most one curly-brace production line and then optional original lyrics. Use Apply to validate and save.",
     "Directives target stem names Vocals, Drums, Bass, Guitar, Piano, Other or Master. Omitted settings carry forward into later sections. Transitions are in seconds and may use smooth or linear curves.",
     "A stem reset clears its pan, width, space, reverb, EQ and dynamics. Do not combine Other.reset with Other.pan or Other.width in the same block. To turn off just compression, set its ratio to 1:1 instead.",
     "Unrecognized directives are rejected rather than silently applied. Not every DAW effect is supported as a script yet."
   ],
   examples:[
     "[Verse 1 0:12-0:35]",
     "{Vocals.pan:left.40@2s:smooth Other.width:130@2s:smooth Guitar.duck:3@1s:smooth}",
     "Original lyrics stay below the instruction line.",
     "[Outro 3:48-4:00]",
     "{Other.comp:-18,1@2s:smooth Master.fade:4s:smooth Master.tail:3s}"
   ]},
  {id:"effects",title:"Effects reference",summary:"Pan, width, reflections, reverb, EQ, compression and ducking.",
   body:[
     "Pan: Track.pan:left.40, Track.pan:right.40 or Track.pan:center. Width: Track.width:125 (0-150%, 100 means unchanged). Space: Track.space:20 (0-40 early reflection amount). Reverb: Track.reverb:25 (0-100 wet send).",
     "Three EQ bands per stem: Track.eq1:320,1.2,-2. Frequency is 30-16000 Hz, Q 0.3-12, gain -12 to +12 dB.",
     "Compression: Track.comp:-18,2 means threshold -18 dBFS and 2:1 ratio; supported ratio 1-4. The compressor defaults to neutral 1:1 when no instruction is active.",
     "Vocal-keyed ducking: Guitar.duck:3 requests up to 3 dB reduction when the detected vocal signal is active. Ducking operates on non-vocal stems only, with 0-12 dB allowed. It is an approximate envelope rather than a fully adjustable external sidechain.",
     "Endings belong to the final section: Master.fade:4s:smooth and Master.tail:3s. The fade reduces dry audio and new reverb excitation; the wet decay may continue into the tail.",
     "Edit sections > De-ess provides the same frequency, Q, detector threshold and max-reduction sliders for the selected section. Edit sections > Script still exposes the full original production block; using Apply preserves lyrics and other directives.",
     "Frequency-selective per-stem de-essing: Vocals.deess:6500,2,-40,4@2s:smooth (frequency 3000-11000 Hz, Q .4-8, detector threshold -70 to -10 dBFS, maximum band reduction 0-12 dB). Neutral unless scripted or accepted from a correction trial. Live gain-reduction meters are available in A/B and correction tools. A full effects rack, plugin hosting, precise artifact repairs and reliable level-matched audition remain planned."
   ],
   examples:["{Vocals.eq1:320,1.2,-2@2s:smooth Other.comp:-18,2@2s:smooth Guitar.duck:3@1s:smooth}"]},
  {id:"export",title:"WAV export and DAW handoff",summary:"How the finished audio leaves Song Harbor.",
   body:[
     "Use Export mix WAV to render the current stems and saved production settings. After rendering, explicitly click Download WAV; the browser decides the destination.",
     "If the mix would clip, Song Harbor reports an additional master trim recommendation. Master trim is session-only at present; keep track of the value before restarting.",
     "Export to DAW prepares six original aligned stems for an external editor. Audacity and Waveform workflows depend on the application installed on your computer; a prepared bundle is separate from Song Harbor's processed stereo mix.",
     "A/B offers independent Bypass compression and Bypass ducking checkboxes. B Original bypasses both; A Processed restores both. All bypass settings affect audition only. WAV export always uses saved production settings.",
     "Open Tools > Sound cleanup and choose Analyze mix; no WAV download is needed. It checks peaks, possible clicks and flattened waveform samples, sibilance-like high-frequency bursts, presence-band harshness, bright residual fizz, hiss-like quiet passages, sustained anti-phase stereo and repeated loudness dips. These are heuristic listening candidates, NOT proven flaws or diagnoses.",
     "Filter by category, click a timestamp to seek, use Loop ± context to audition automatically, and Mark reviewed to hide a candidate until Show reviewed is enabled. Active raw stems are approximate activity hints rather than certain artifact sources. Review flags reset when you change the mix or scan again. The analyzer can suggest a manually adjustable de-esser correction, but it does not automatically apply any repair or rewrite audio.",
     "For near-ceiling peaks, repeated level dips and sibilance-like frequency findings, choose Try correction A/B. The current passage loops while A Saved and B Proposed compare the mix. Adjust master trim (session-only), compressor ratio/threshold, or vocal-keyed ducking reduction and track. Choose targeted de-esser to adjust frequency, Q, threshold and max reduction. A 3× exaggerated audition helps expose subtle changes but does not affect accepted values. Live per-effect gain reduction is shown in the correction trial. Only Accept writes a validated dynamics or de-esser instruction to the saved section script; Discard restores the earlier mix. You cannot export an unaccepted preview. These are listening hypotheses, not automatic fixes."
   ]},
  {id:"updates",title:"Updates and settings",summary:"Version badge, relaunch and local working files.",
   body:[
     "The small badge beside the update icon uses Version:Revision:Build, for example 0.1.0:1:320. Version comes from the app package, Revision is the development revision, and Build counts commits in the local checkout. Hover for branch and Git commit details.",
     "Click the circular update icon to check for a newer checkout; checking does not overwrite files. Install and relaunch saves no un-applied browser edits for you, so Apply changes first.",
     "Update may refuse an active processing job, divergent Git history or conflicting local edits. It must not discard local work or stop unrelated applications.",
     "Settings controls the local working-files directory and component setup. Changing the directory may require a restart and does not automatically move existing project files."
   ]},
  {id:"troubleshooting",title:"Troubleshooting and feedback",summary:"Common blockers and how to report them.",
   body:[
     "Separate stems disabled or failing: check the engine status, FFmpeg configuration in Settings, and the application's launch console.",
     "Missing song after restart: return to Library; confirm the same working-files directory is selected in Settings. Do not delete folders or re-import repeatedly before checking.",
     "Sections Apply rejected: verify one section header per section, at most one production line per section, recognized stem aliases, and no reset-plus-specific-effect collision.",
     "Export does not appear in Downloads: after render, click Download WAV and check your browser's download destination. If clipping is reported, apply the suggested trim and render again.",
     "For a reproducible bug, include the version badge, Windows version, steps to reproduce, expected and observed behavior, and the exact error message. Never upload original recordings or local paths publicly without permission."
   ]}
];

export function filterHelpTopics(query:string):Topic[]{
  const needle=query.trim().toLowerCase();
  return !needle?HELP_TOPICS:HELP_TOPICS.filter(topic=>
    [topic.title,topic.summary,...topic.body,...(topic.examples||[])].join(" ").toLowerCase().includes(needle));
}

export function HelpDialog({open,onOpenChange}:{open:boolean;onOpenChange:(value:boolean)=>void}){
  const [query,setQuery]=useState("");
  const matches=useMemo(()=>filterHelpTopics(query),[query]);
  return <Dialog open={open} onOpenChange={onOpenChange} title="Song Harbor help"
    description="Quick start, production scripting, exports, updates and troubleshooting. Available offline.">
    <section className="song-help" aria-label="Song Harbor user guide">
      <label className="song-help-search-label" htmlFor="song-help-search">Search help</label>
      <input id="song-help-search" className="song-help-search" type="search" value={query}
        onChange={e=>setQuery(e.target.value)} placeholder="Try: ducking, export, reset, FFmpeg..." />
      <div className="song-help-topic-list">
        {matches.length===0?<p role="status">No matching topics. Try a different term.</p>:
          matches.map(topic=><details key={topic.id} className="song-help-topic" open={query.trim()?true:undefined}>
            <summary><strong>{topic.title}</strong><span>{topic.summary}</span></summary>
            <div className="song-help-topic-body">
              {topic.body.map((paragraph,index)=><p key={index}>{paragraph}</p>)}
              {topic.examples&&<pre aria-label={topic.title+" example"}>{topic.examples.join("\n")}</pre>}
            </div>
          </details>)}
      </div>
      <p className="song-help-feedback">Found an issue? <a href="https://github.com/Three-Wheeled-Sloth-Studio/Song-Harbor/issues" target="_blank" rel="noopener noreferrer">Open the project issue tracker</a>. Include your version badge and reproduction steps, but no private audio.</p>
    </section>
  </Dialog>;
}
