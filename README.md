# Song Harbor

**Working title** for a standalone, local-first, AI-assisted music production workbench from TWS Studios.

Song Harbor combines structured composition, section-level direction, stem-level editing, multiple interchangeable music models, audio processing, remixing, and reconstruction of imported music. The project owns its arrangement data; no generator owns the project format.

**Current status (2026-10-21):** Song Harbor has progressed from the initial separator/DAW handoff into a local, non-destructive, section-scriptable music production workbench. Implemented: six-stem separation and split L/R routing, saved Library/projects and aligned section waveform timeline, phase-coherent shared-clock playback, pan, stereo width, cross-channel spatial reflections, reverb, ending fades/wet post-roll, non-clipping 24-bit WAV export with master trim recovery, audition-only A/B bypass, and **three-band per-stem parametric EQ** with smooth section automation. Recent Windows user listening QA: spatial arrangement described as “very good and epic”; processed in-app playback and exported WAV both sound good after the fade fix; EQ judged “subtle, but good”. The new **in-app check-for-updates / install-and-relaunch** flow is committed but **not yet Windows QA-verified**. Next: verify updater/build, then section-aware compression and vocal-keyed ducking, followed by the detection-first sound cleanup workbench.

The longer-term product explicitly includes **a full effects rack and third-party plugin support**; current priority is unique, scriptable stem/section/phrase-level operations that would require manual clip editing in a conventional DAW. Source files remain immutable. The right Tools sidebar needs a future compact, icon-first/pop-out inspector redesign. Historical Audacity4 six-track LOF import/focus remains unverified and is not an immediate roadmap blocker. **Current task state and QA gates:** see the [START HERE handoff](refs/handoffs/currentHandoff.md).

**Run Song Harbor:** [setup and acceptance checks](app/README.md). The frontend consumes [TWS UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), whose canonical guidance is [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles).

Start here:
- [Product vision](refs/product/vision.md)
- [Requirements](refs/product/requirements.md)
- [Architecture direction](refs/architecture/overview.md)
- [Recorded decisions](refs/planning/decisions.yaml)
- [Open questions](refs/planning/openQuestions.yaml)
- [Roadmap](refs/planning/roadmap.yaml)
- [Current handoff](refs/handoffs/currentHandoff.md)

Documentation follows the [Agent Academy](https://github.com/Three-Wheeled-Sloth-Studio/Agent-Academy) `refs/` conventions. Full template tooling and generated indexes are pending bootstrap; these records are authoritative in the meantime. No Infra Choir branding or promotional dependency is part of this product.
