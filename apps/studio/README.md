# Reel Studio (`apps/studio`)

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EslamNabawy/reel-studio)](https://github.com/EslamNabawy/reel-studio/releases)

Desktop app that adds AI voice-over and burned subtitles to videos and images.
Images become a short video: still frame + voice + subtitles, with real framing
control (aspect, fit, focal point, Ken Burns motion).

No Python? Grab the installer from
[**Releases**](https://github.com/EslamNabawy/reel-studio/releases) ·
back to [root README](../../README.md).

## Run from source

From the repo root:

```bash
pip install -r apps\studio\requirements.txt
python apps\studio\app.py            # GUI
python apps\studio\app.py file.mp4   # CLI
```

CLI examples (run from `apps\studio\`):

```bash
python app.py myvideo.mp4
python app.py photo.jpg --aspect 9:16 --fit blur --motion zoom-in
python app.py photo.jpg --caption "My own script. Second sentence."
python app.py videos_folder\ --interval 1 --voice ar-EG-ShakirNeural
```

## The app adapts to what you drop in

Drop an **image** and the Frame card appears: aspect (Source / 16:9 / 9:16 / 1:1 / 4:5 / 4:3),
height (Auto / 4K / 1080p / 720p / 480p), fit (Fill / Fit / Blur BG), zoom, Ken Burns motion
(Still / Zoom In / Zoom Out / Pan Left / Pan Right) and minimum clip length.
The preview renders the actual crop — **click it to set the focal point**.

Drop a **video** and Frame is replaced by Frame sampling: seconds per frame and a frame cap.
Narration source switches between AI captions, raw BLIP captions, or your own script.
Subtitle size and bottom margin are live, speech rate too.

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Browse for media |
| `Ctrl+Enter` | Generate |
| `Esc` | Cancel |

## API key

The app reads `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) from `.env` next to the
exe, falling back to the repo-root `.env`. Add it via ⚙ API key in the GUI —
never commit it (the build ships `.env.example` only).

## Build exe

```powershell
cd apps\studio
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-<version>.exe
```

Output lands in `dist\VideoVoiceOver\`:

- `VideoVoiceOver.exe` — GUI, no console
- `VideoVoiceOver_CLI.exe` — command line

## Stack

`edge-tts` (speech) · `faster-whisper` (transcription) · `BLIP` (image captioning) · `ffmpeg` (mux + subtitle burn-in, must be on PATH) · PyInstaller (packaging).

`models/`, `build/`, `dist/`, `release/`, `output/`, `work/` are git-ignored.
