# Reel Studio

Desktop app that adds AI voice-over and burned subtitles to videos and images.
Images become a short video: still frame + voice + subtitles, with real framing
control (aspect, fit, focal point, Ken Burns motion).

> The PDF-RAG tool used to live here — it moved to `../ragmodel/`.

## Layout

```
apps/
  studio/     # Reel studio app (GUI + CLI + installer)
  caption/    # BLIP image captioning / VQA CLI
tests/        # pytest suite
.github/      # CI + Release workflows
.env          # secrets, git-ignored
```

## Apps

| App | What it does | Run |
| --- | --- | --- |
| `apps/studio` | Reel studio: BLIP captions → Gemini script → edge-tts voice + burned subs. GUI + CLI, PyInstaller + Inno Setup. | `python apps\studio\app.py` |
| `apps/caption` | BLIP image captioning / VQA. Writes results to CSV. | `python apps\caption\caption.py images\` |

## Quickstart

```bash
pip install -r apps\studio\requirements.txt
python apps\studio\app.py                 # GUI
python apps\studio\app.py clip.mp4        # CLI
```

```bash
python apps\studio\app.py photo.jpg --lang ar
python apps\studio\app.py videos_folder\ --interval 1 --voice ar-EG-ShakirNeural
```

## API keys

Put keys in `.env` at repo root (git-ignored):

```
GEMINI_API_KEY=your-key
```

`.env` is never committed. Keep `.env.example` keys documented instead.

## Tests

```bash
pip install pytest Pillow python-dotenv
python -m pytest tests/ -q
```

## Release

```powershell
cd apps\studio
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-<version>.exe
```

Or push a `v*.*.*` tag — the Release workflow builds the exe + installer
and attaches both to a GitHub Release automatically.
