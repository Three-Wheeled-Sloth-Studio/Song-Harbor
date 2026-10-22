# Song Harbor

**Working title** for a standalone, local-first, AI-assisted music production workbench from TWS Studios.

Song Harbor combines structured composition, section-level direction, stem-level editing, multiple interchangeable music models, audio processing, remixing, and reconstruction of imported music. The project owns its arrangement data; no generator owns the project format.

**Current status (2026-10-21):** Song Harbor is a local, non-destructive, section-scriptable music workbench. Implemented: six-stem separation and split L/R routing, persistent Library/projects, waveform section timeline and shared-clock playback, section pan/width/spatial reflections/reverb, ending fades and wet post-roll, 24-bit WAV export with master output trim recovery, audition-only A/B bypass, three-band per-stem section EQ, and conservative section-aware compression and vocal-keyed ducking. A searchable **in-app Help** dialog is available via the **i** icon beside Settings. The app header also shows the installed Git revision and provides safe update/relaunch. The Windows user reports that soft update/relaunch seems successful; detailed conflict/busy-job cases and fresh audible DSP parity tests still need validation. Full effects rack, plugin support, de-essing, phrase editing, gain-reduction meters and compact icon-first Tools redesign remain planned. See the [current handoff](refs/handoffs/currentHandoff.md) for QA boundaries.

The longer-term product explicitly includes **a full effects rack and third-party plugin support**; current priority is unique, scriptable stem/section/phrase-level operations that would require manual clip editing in a conventional DAW. Source files remain immutable. The right Tools sidebar needs a future compact, icon-first/pop-out inspector redesign. Historical Audacity4 six-track LOF import/focus remains unverified and is not an immediate roadmap blocker. **Current task state and QA gates:** see the [START HERE handoff](refs/handoffs/currentHandoff.md).

**New to Song Harbor?** Start with the [user guide](docs/user-guide.md), also available directly from the header Help icon.\n\n**Run Song Harbor:** [setup and acceptance checks](app/README.md). The frontend consumes [TWS UI](https://github.com/Three-Wheeled-Sloth-Studio/TWS-UI), whose canonical guidance is [TWS Design Principles](https://github.com/Three-Wheeled-Sloth-Studio/TWS-Design-Principles).

Start here:
- [Product vision](refs/product/vision.md)
- [Requirements](refs/product/requirements.md)
- [Architecture direction](refs/architecture/overview.md)
- [Recorded decisions](refs/planning/decisions.yaml)
- [Open questions](refs/planning/openQuestions.yaml)
- [Roadmap](refs/planning/roadmap.yaml)
- [Current handoff](refs/handoffs/currentHandoff.md)

Documentation follows the [Agent Academy](https://github.com/Three-Wheeled-Sloth-Studio/Agent-Academy) `refs/` conventions. Full template tooling and generated indexes are pending bootstrap; these records are authoritative in the meantime. No Infra Choir branding or promotional dependency is part of this product.
