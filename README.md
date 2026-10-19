# Song Harbor

**Working title** for a standalone, local-first, AI-assisted music production workbench from TWS Studios.

Song Harbor combines structured composition, section-level direction, stem-level editing, multiple interchangeable music models, audio processing, remixing, and reconstruction of imported music. The project owns its arrangement data; no generator owns the project format.

**Current status (2026-10-19):** Local six-stem separation, song Library, saved mixer/projects, and optional Waveform Free/Audacity DAW handoff are implemented. The safe Windows launcher compiles the frontend then runs one Python/FastAPI server on a dynamically selected localhost port; Omen has confirmed launcher operation and Audacity4 detection. The latest Audacity **Launch** implementation requests automatic import of six aligned stems through an Audacity LOF file and attempts to focus Audacity. **Actual Audacity4 LOF import and foreground focus are NOT yet user-verified.** Next QA is on Omen; see the top of [Current handoff](refs/handoffs/currentHandoff.md). Broader testing, true standalone packaging, and DAW-independent in-app editing remain planned.

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
