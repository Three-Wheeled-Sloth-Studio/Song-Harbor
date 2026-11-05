# DEV checkpoint: Big Rusty Drums SFZ ZIP import
Date: 2026-11-05
Branch: dev only; main remains pinned at 2345c61.

## User report
Importing the curated Big Rusty Drums 1.100 ZIP fails immediately with "SFZ ZIP contains unsupported file type".

## Root cause
app/backend/sfz_pack.py was rejecting the entire archive on ANY extension not in its whitelist, even if the file was an unrelated GUI/preset/platform companion. It also rejected #include and #define preprocessing, which the actual publisher SFZ programs 02-basic.sfz, 03-kick.sfz, and nested mappings use heavily.

## Changes
- Inspect all ZIP entries and maintain file/path/size/duplicate/special-file bounds; do not extract unrecognized/support files. Return number of ignored support files in import response and show compact UI message. Rejected symlinks, traversal and missing referenced samples remain rejected.
- Skip platform resource forks like __MACOSX/._*.sfz, even though their suffix looks like an instrument.
- Permit #include and #define in SFZ, reject other unsupported directives; validate included .sfz files and referenced audio exist within extracted pack. Search only the SFZ definition's directory and its ancestors within pack to support Big Rusty's program-relative nested includes and ../Samples references.
- Exclude referenced mapping snippet .sfz files from instrument manifest; expose standalone .sfz programs as selectable instruments.
- New regression tests exercise Big Rusty style nested include/macro/sample hierarchy, non-audio companions, malicious external includes, missing audio, macOS resource forks, and unsupported preprocessor directives.

## Sources checked
Publisher source: https://github.com/sfzinstruments/karoryfer.big-rusty-drums
Example 02-basic.sfz includes keymap/keymap.sfz and mapping .sfz fragments; included kick maps use ../Samples path references; full keymap includes #define pitch names. Publisher v1.100 archive bundles FLAC and WAV samples plus support artifacts.

## QA / risks
- No Windows build or real 620MB ZIP import executed by connector environment. User must update dev and retry same ZIP. If an error persists, exact file/path in error will inform next fix.
- SFZ renderer compatibility is distinct from import success. Big Rusty has vendor-specific CC and effect opcodes; sfizz's support for those remains unverified.
- The full kit uses custom mapping; do not label arbitrary SFZ sample keys as General MIDI unless validated. Drum transcription and rendering must be tested separately.
- Importer still caps archives at 768MB compressed, 1.5GB uncompressed, 12000 files, 2MB per SFZ.
- dev only; production main not modified.
