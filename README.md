# Reel Studio

Desktop app that adds AI voice-over and burned subtitles to videos and images.
Images become a short video: still frame + voice + subtitles, with real framing
control (aspect, fit, focal point, Ken Burns motion).

> The PDF-RAG tool used to live here — it moved to `../ragmodel/`.

## Projects

| Folder | What it does | Entry point |
| --- | --- | --- |
| `video_voiceover/` | Reel studio: BLIP captions → Gemini script → edge-tts voice + burned subs. GUI + CLI, packaged with PyInstaller + Inno Setup. | `video_voiceover/app.py` |
| `image_to_text/` | BLIP image captioning / VQA. Writes results to CSV. | `image_to_text/caption.py` |
| `tests/` | `pytest tests/` — voiceover logic tests. | — |

## Quickstart

```bash
pip install -r video_voiceover\requirements.txt
python video_voiceover\app.py                 # GUI
python video_voiceover\app.py clip.mp4        # CLI
```

CLI examples:

```bash
python video_voiceover\app.py photo.jpg --lang ar
python video_voiceover\app.py videos_folder\ --interval 1 --voice ar-EG-ShakirNeural
```

## API keys

Put keys in `.env` at repo root (git-ignored):

```
GEMINI_API_KEY=your-key
```

`.env` is never committed. Keep `.env.example` keys documented instead.

## Build exe

```powershell
cd video_voiceover
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-*.exe
```

Pushing a `v*.*.*` tag builds + attaches both via the Release workflow.

## Layout

```
.env                  # secrets, ignored
.gitignore
README.md
.github/workflows/   # ci.yml (tests) · release.yml (exe + installer)
tests/
image_to_text/
video_voiceover/
  app.py · gui.py · voiceover.py · models_setup.py
```

## Notes

- `models/`, `build/`, `dist/`, `release/`, `output/`, `work/` are git-ignored — regenerate or keep local.
- First run downloads BLIP / Whisper (Models card → Install, or `app.py --install-models`).
