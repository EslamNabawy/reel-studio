# Changelog

All notable changes to Reel Studio are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.1.0] — 2026-10-01

### Added
- Sectioned option rail — `All · Frame · Voice · Text · Output` chips replace the
  single scrolling options column, with a live visible-card count.
- `tools/gui_smoke.py` — constructs the real Tk window headlessly, walks every
  section in every media mode, fires each layout callback and asserts the CLI
  argument build. Wired into CI (xvfb) and the Release workflow.
- GUI smoke job in CI, so layout regressions fail the build.
- Rounded surfaces for cards and the drop zone, a designed empty state in the
  preview, a violet accent strip under the header, and stage connectors.
- Press states on buttons, accent dots on card titles, larger preview canvas.
- Dependabot for `pip` and `github-actions`.
- Issue templates (bug report + feature request) and a PR template.
- `docs/` — architecture, pipeline, troubleshooting.

### Fixed
- `_on_fit` passed a positionally-supplied dict to `Label.configure()`, raising
  `TclError` on every fit-mode change. Now `configure(text=...)`.
- Option cards could land out of order when media mode and section filter
  changed together; repacking now follows a single declared order.

### Changed
- Repository restructured: `video_voiceover/` → `apps/studio/`,
  `image_to_text/` → `apps/caption/`. History preserved via `git mv`.
- Test suite renamed to `tests/test_studio.py`.

## [1.0.0] — 2026-09-30

### Added
- Desktop app (Tkinter) with drag-and-drop, live focal-point preview, adaptive
  frame controls for images and frame sampling for videos.
- Pipeline: frame extraction → BLIP captions → Gemini script → edge-tts voice →
  ffmpeg mux with burned subtitles.
- In-app Gemini key entry with test button.
- In-app model manager for BLIP and Whisper with download progress.
- Local-vs-cloud pipeline panel in the UI.
- 8 neural voices across `ar-EG`, `ar-SA`, `en-US`, `en-GB` with speech rate.
- CLI with a full flag surface, accepting a file or a folder.
- PyInstaller bundle (`build.ps1`) plus Inno Setup installer (`install.iss`).
- CI and Release GitHub Actions workflows.

[Unreleased]: https://github.com/EslamNabawy/reel-studio/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/EslamNabawy/reel-studio/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/EslamNabawy/reel-studio/releases/tag/v1.0.0
