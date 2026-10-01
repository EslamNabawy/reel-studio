<div align="center">

# Reel Studio — desktop app

**AI voice-over and burned-in subtitles for videos and images. Arabic and English.**

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EslamNabawy/reel-studio?color=7C5CFF)](https://github.com/EslamNabawy/reel-studio/releases)

[⬇ Download](https://github.com/EslamNabawy/reel-studio/releases) · [Root README](../../README.md) · [Architecture](../../docs/architecture.md) · [Troubleshooting](../../docs/troubleshooting.md)

</div>

---

Drop in a video or a photo. Reel samples frames, captions them with BLIP, writes
a spoken script with Gemini, synthesizes a voice with edge-tts, and burns in
subtitles with ffmpeg. Images get a full frame engine: aspect, fit, zoom, Ken
Burns motion and a click-to-set focal point with a live crop preview.

## Run

From the repo root:

```bash
pip install -r apps\studio\requirements.txt
python apps\studio\app.py            # GUI
python apps\studio\app.py clip.mp4   # CLI
```

Needs **Python 3.11+** and **ffmpeg** on `PATH`.

<details>
<summary>First run — fetch the local models</summary>

```bash
python apps\studio\app.py --install-models   # ~1 GB, once
python apps\studio\app.py --models           # status only
```

Models land in `apps/studio/models/` and are shared by the GUI, the CLI and a
frozen build. Without them the app still runs and speaks raw captions.
</details>

## The GUI adapts to the media

**Image** → the Frame card appears: aspect, height, fit, zoom, Ken Burns motion
and minimum clip length. The preview renders the real crop — **click it to move
the focal point**.

**Video** → Frame is replaced by Frame sampling: seconds per frame and a frame
cap.

Narration source switches between a Gemini-written script, raw BLIP captions, or
your own text. Subtitle size, outline, margin and colour are live, and so is
speech rate.

The options column is split into sections — `All · Frame · Voice · Text ·
Output` — so you are not scrolling past everything to change one setting.

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Browse for media |
| `Ctrl+Enter` | Generate |
| `Esc` | Cancel |
| `Ctrl+K` | API key |

## CLI

`app.py <file-or-folder> [flags]`

```bash
python app.py photo.jpg --aspect 9:16 --fit blur --motion zoom-in
python app.py clip.mp4 --lang ar --voice ar-EG-ShakirNeural --rate -10%
python app.py photo.jpg --caption "First line. Second line." --no-subtitles
python app.py videos\ --interval 1 --quality draft --keep
```

| Group | Flags |
| --- | --- |
| general | `--lang {auto,ar,en}` `--interval` `--max-frames` `--voice` `--rate` `--pitch` `--caption` `--raw-captions` `--no-subtitles` |
| frame (images) | `--aspect` `--height` `--fit {cover,contain,blur}` `--zoom` `--fx` `--fy` `--motion` `--min-duration` |
| subtitles | `--sub-font` `--sub-size` `--sub-outline` `--sub-margin-v` `--sub-color` |
| output | `--quality {draft,good,high}` `--keep` |
| app | `--install-models` / `-m` · `--models` |

Output: `output\<name>_voiceover_<lang>.mp4`

Run `python ../../tools/dump_cli.py` from the repo root to print this list from
the code.

## API key

`GEMINI_API_KEY` (or `GOOGLE_API_KEY`) is resolved in this order: the process
environment (the GUI passes it to the CLI), then the per-user store at
`%APPDATA%\Reel\.env`, then a legacy `.env` beside the app.

Entering the key from **⚙ API key** writes it to the **per-user store**, never
into the app folder — so a portable copy of Reel can be shared without carrying
your key. A key left beside the exe by an older build is migrated on first
launch and the old file removed.

Without a key the app speaks the raw BLIP captions.

## Build

```powershell
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-<version>.exe
```

Produces `VideoVoiceOver.exe` (GUI, no console) and `VideoVoiceOver_CLI.exe`.
AI model weights are **not** bundled — the app installs them on demand via the
Models card or `--install-models`.

Pushing a `v*.*.*` tag does all of this in CI and attaches the results to a
GitHub Release.

## Layout

| File | Role |
| --- | --- |
| `app.py` | entry point / router: GUI, CLI, model commands |
| `gui.py` | theme, widgets, layout, worker threads |
| `voiceover.py` | the pipeline — no Tk imports, so it stays testable |
| `keystore.py` | key storage in the user profile + legacy migration |
| `models_setup.py` | local model status and download |
| `build.ps1` · `install.iss` · `VideoVoiceOver.spec` | packaging |

## Stack

`edge-tts` · `faster-whisper` · `BLIP` (transformers + torch) · `Google Gemini`
· `ffmpeg` · `tkinter` · PyInstaller · Inno Setup

`models/`, `build/`, `dist/`, `release/`, `output/`, `work/` are git-ignored.
