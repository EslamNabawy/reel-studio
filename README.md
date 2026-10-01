<div align="center">

# Reel Studio

**Turn any video or image into a narrated clip — AI captions, spoken voice-over, burned-in subtitles. Arabic and English.**

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/EslamNabawy/reel-studio?label=release&color=7C5CFF)](https://github.com/EslamNabawy/reel-studio/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-7C5CFF)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-35D6ED)](https://github.com/EslamNabawy/reel-studio/releases)
[![Commits](https://img.shields.io/github/commit-activity/m/EslamNabawy/reel-studio?color=3DDC97)](https://github.com/EslamNabawy/reel-studio/commits/main)

[**⬇ Download**](https://github.com/EslamNabawy/reel-studio/releases) · [**Docs**](docs/) · [**Report a bug**](https://github.com/EslamNabawy/reel-studio/issues/new/choose) · [**Changelog**](CHANGELOG.md)

MIT licensed · Windows · Python 3.11+

</div>

---

## What it does

Drop in a clip or a photo. Reel reads the frames, writes a spoken script,
synthesizes a voice, burns in subtitles, and hands you a finished video.

```
  frames ──► BLIP captions ──► Gemini script ──► edge-tts voice ──► ffmpeg mux ──► MP4
   local          local            cloud            cloud             local
```

| Stage | Engine | Runs |
| --- | --- | --- |
| Read media, extract frames, render | `ffmpeg` / `ffprobe` | 🟢 local |
| Describe each frame | `BLIP` (image-captioning-base) | 🟢 local |
| Detect spoken language | `Whisper tiny` | 🟢 local |
| Write the spoken script | `Gemini flash` | 🔵 cloud |
| Synthesize the voice | `edge-tts` (8 neural voices) | 🔵 cloud |
| Mux audio + burn subtitles | `ffmpeg` | 🟢 local |

Install the local models once (~1 GB) and the only things left needing a network
are the script and the voice.

## Highlights

| | |
| --- | --- |
| **Frame engine** | aspect (16:9 / 9:16 / 1:1 / 4:5 / 4:3), fit (Fill / Fit / Blur BG), zoom, Ken Burns motion, click-to-set focal point with a live crop preview |
| **Sectioned options** | jump between All · Frame · Voice · Text · Output instead of scrolling one long column |
| **Narration sources** | Gemini-written script · raw BLIP captions · your own script |
| **Voices** | 8 neural voices — `ar-EG`, `ar-SA`, `en-US`, `en-GB` — with speech rate |
| **Subtitles** | burned in, live size / outline / bottom-margin / colour control |
| **Pipeline panel** | shows exactly what runs locally vs in the cloud, and whether a key is set |
| **Model manager** | in-app download + status for the local models, or `--install-models` |
| **Shortcuts** | `Ctrl+O` browse · `Ctrl+Enter` generate · `Esc` cancel · `Ctrl+K` API key |

## Install

Grab a build from [**Releases**](https://github.com/EslamNabawy/reel-studio/releases):

| Asset | Use |
| --- | --- |
| `Reel-Setup-<version>.exe` | Guided installer — Start Menu + optional Desktop icon, can pre-download models |
| `VideoVoiceOver-<version>-portable.zip` | Portable bundle, no install, run anywhere |

On first launch open **⚙ API key** and paste a Gemini key — it turns the raw
captions into a real script. Without it the app still works and speaks the
captions verbatim.

> The build never bundles a `.env`; it ships `.env.example` only.

## Run from source

```bash
git clone https://github.com/EslamNabawy/reel-studio.git
cd reel-studio

pip install -r apps\studio\requirements.txt
python apps\studio\app.py                 # GUI
python apps\studio\app.py clip.mp4        # CLI
```

Requires **Python 3.11+** and **ffmpeg** on `PATH`.

<details>
<summary>First run: fetch the local models</summary>

```bash
python apps\studio\app.py --install-models   # ~1 GB, once
python apps\studio\app.py --models           # status only
```

Models land in `apps/studio/models/` (git-ignored). The GUI has the same
controls under the **AI models** card.
</details>

## CLI

Everything the GUI does is scriptable. `python apps\studio\app.py <media> [flags]`
accepts a file **or a whole folder**.

```bash
# an image becomes a vertical short
python apps\studio\app.py photo.jpg --aspect 9:16 --fit blur --motion zoom-in

# Arabic narration with a specific voice and slower speech
python apps\studio\app.py clip.mp4 --lang ar --voice ar-EG-ShakirNeural --rate -10%

# your own script, no captions burned in
python apps\studio\app.py photo.jpg --caption "First line. Second line." --no-subtitles

# batch a folder, keep the intermediate files
python apps\studio\app.py videos\ --interval 1 --quality draft --keep
```

| Group | Flags |
| --- | --- |
| general | `--lang {auto,ar,en}` `--interval` `--max-frames` `--voice` `--rate` `--pitch` `--caption` `--raw-captions` `--no-subtitles` |
| frame (images) | `--aspect` `--height` `--fit {cover,contain,blur}` `--zoom` `--fx` `--fy` `--motion` `--min-duration` |
| subtitles | `--sub-font` `--sub-size` `--sub-outline` `--sub-margin-v` `--sub-color` |
| output | `--quality {draft,good,high}` `--keep` |
| app | `--install-models` / `-m` · `--models` |

Output lands in `apps/studio/output/<name>_voiceover_<lang>.mp4`.

## Also in the box

`apps/caption` — BLIP captioning and VQA over a folder of images, written to CSV.

```bash
pip install -r apps\caption\requirements.txt
python apps\caption\caption.py images\ --out captions.csv
python apps\caption\caption.py images\ --question "what is on the table?"
python apps\caption\caption.py images\ --ar
```

## Configuration

`.env` at the repo root (git-ignored):

```ini
GEMINI_API_KEY=your-key
```

`GOOGLE_API_KEY` is also accepted for backwards compatibility.

Entering the key from **⚙ API key** stores it per-user, under
`%APPDATA%\Reel\.env` — never inside the app folder. That is deliberate: it means
a portable copy of Reel can be shared or zipped without carrying your key with
it. A key written beside the exe by an older build is migrated automatically on
first launch and the old file is deleted.

The build ships `.env.example` only, never a real key.

## Project layout

```
apps/
  studio/     Reel studio — app.py (router) · gui.py · voiceover.py · models_setup.py
              build.ps1 · install.iss · VideoVoiceOver.spec · icon.ico
  caption/    BLIP captioning / VQA CLI
tests/        pytest suite for the engine
tools/        gui_smoke.py — builds the real window headlessly
docs/         architecture · troubleshooting · pipeline
.github/      ci.yml · release.yml · issue + PR templates · dependabot
```

`app.py` is the single entry point:

| Invocation | Result |
| --- | --- |
| `app.py` | GUI |
| `app.py <media> …` | CLI |
| `app.py --install-models` | download the local models |
| `app.py --models` | model status |

## Development

```bash
pip install pytest Pillow python-dotenv

python -m pytest tests/ -q     # engine logic
python tools\gui_smoke.py      # constructs the real Tk window, checks layout
python tools\check_docs.py     # every documented flag, shortcut and link is real
python tools\dump_cli.py       # prints the CLI surface the docs must match
```

CI runs the tests, the GUI smoke test and the docs check on every push and PR,
plus a compile check of every entry point. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## Releases

Push a `v*.*.*` tag and the Release workflow takes over: it stamps the version
into the Inno Setup script, runs the test suite and the GUI smoke test, builds
the PyInstaller bundle and the installer, and attaches both to a GitHub Release.

```bash
git tag v1.2.0 && git push origin v1.2.0
```

To build by hand:

```powershell
cd apps\studio
.\build.ps1        # → dist\VideoVoiceOver\
iscc install.iss   # → release\Reel-Setup-<version>.exe
```

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ffmpeg` not found | install ffmpeg and put it on `PATH` — it does the frame and mux work |
| Voice comes out in the wrong language | pass `--lang ar` / `--lang en`; `auto` only detects speech, not silent images |
| Script is read straight off the captions | no API key set — add one under **⚙ API key**, or use `--caption` |
| Captions are empty | local models missing — run `--install-models` |
| Text does not fit the frame | lower `--sub-size`, raise `--sub-margin-v`, or change `--aspect` |

More in [docs/troubleshooting.md](docs/troubleshooting.md).

## Credits

Built on [BLIP](https://huggingface.co/Salesforce/blip-image-captioning-base),
[Whisper](https://github.com/openai/whisper) via
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[edge-tts](https://github.com/rany2/edge-tts), [Google Gemini](https://ai.google.dev/),
[ffmpeg](https://ffmpeg.org/), [PyInstaller](https://pyinstaller.org/) and
[Inno Setup](https://jrsoftware.org/isinfo.php).

<sub>Reel Studio is not affiliated with any of the projects above.</sub>
