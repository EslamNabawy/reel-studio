# Reel Studio

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EslamNabawy/reel-studio)](https://github.com/EslamNabawy/reel-studio/releases)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-windows-lightgrey)](https://github.com/EslamNabawy/reel-studio/releases)

Turn any video or image into a narrated clip — **AI captions → spoken voice-over →
burned-in subtitles**. Arabic and English, one click.

> The PDF-RAG sidekick used to live here — it moved to [`../ragmodel/`](../ragmodel/).

## Install (no Python needed)

Grab the latest installer from
[**Releases**](https://github.com/EslamNabawy/reel-studio/releases):

| File | What |
| --- | --- |
| `Reel-Setup-<version>.exe` | Guided installer (Start Menu + Desktop icon) |
| `VideoVoiceOver-<version>-portable.zip` | Portable bundle, run anywhere |

On first launch add your Gemini key under **⚙ API key** — it unlocks the
script-rewrite step (without it, raw BLIP captions are spoken).

## Features

- **Frame engine** — aspect (16:9 / 9:16 / 1:1 / 4:5), fit (Fill / Fit / Blur BG),
  zoom, Ken Burns motion, click-to-set focal point with live preview
- **Sectioned options** — jump between All / Frame / Voice / Text / Output instead
  of scrolling one long column
- **AI narration** — BLIP describes frames, Gemini writes a spoken script
  (or bring your own script / raw captions)
- **Voices** — Edge-TTS, Arabic (EG/SA) + English (US/GB), speech-rate control
- **Subtitles** — burned in, styled, with live size + margin control
- **Pipeline panel** — see what runs locally (ffmpeg, BLIP, Whisper) vs cloud
  (TTS, Gemini), plus one-click local model install (~1 GB, then fully offline
  except voice + script)
- **Shortcuts** — `Ctrl+O` browse · `Ctrl+Enter` generate · `Esc` cancel

## Run from source

```bash
pip install -r apps\studio\requirements.txt
python apps\studio\app.py                 # GUI
python apps\studio\app.py clip.mp4        # CLI
```

```bash
python apps\studio\app.py photo.jpg --lang ar
python apps\studio\app.py videos_folder\ --interval 1 --voice ar-EG-ShakirNeural
```

## Apps

| App | What it does | Docs |
| --- | --- | --- |
| `apps/studio` | Reel studio GUI + CLI + Windows installer | [README](apps/studio/README.md) |
| `apps/caption` | BLIP image captioning / VQA CLI (CSV out) | [README](apps/caption/README.md) |

## API keys

`.env` at repo root (git-ignored):

```
GEMINI_API_KEY=your-key
```

`.env` is never committed — the installer ships `.env.example` only.

## Tests

```bash
pip install pytest Pillow python-dotenv
python -m pytest tests/ -q        # logic
python tools/gui_smoke.py         # builds the real window, checks layout
```

CI runs both, plus a compile check on every push/PR.

## Release

```powershell
cd apps\studio
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-<version>.exe
```

Or push a `v*.*.*` tag — the Release workflow builds the bundle + installer
and attaches both to a GitHub Release automatically.

## Layout

```
apps/
  studio/     # Reel studio app (GUI + CLI + installer)
  caption/    # BLIP captioning CLI
tests/        # pytest suite
.github/      # CI + Release workflows
.env          # secrets, git-ignored
```

## Notes

- `models/`, `build/`, `dist/`, `release/`, `output/`, `work/` are git-ignored —
  regenerate or keep local.
- First run downloads BLIP / Whisper (Models card → Install,
  or `python apps\studio\app.py --install-models`).
