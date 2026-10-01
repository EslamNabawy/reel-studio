# Troubleshooting

## Setup

### `ffmpeg` is not recognized
Frame extraction, muxing and subtitle burn-in all need ffmpeg on `PATH`.

```powershell
winget install Gyan.FFmpeg
# or: choco install ffmpeg
ffmpeg -version   # must print a version
```

Restart Reel afterwards — the app shells out to `ffmpeg` and `ffprobe`, it does
not bundle them in a source run.

### `No module named 'torch'` / `transformers`
Install the app's dependencies, not just the entry point:

```bash
pip install -r apps\studio\requirements.txt
```

On a laptop, prefer the CPU build of torch — it is far smaller:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### `google-genai not installed`
The key check needs it: `pip install google-genai`.

## Models

### Captions are empty, or language is always English
The local models are missing. Check and install:

```bash
python apps\studio\app.py --models
python apps\studio\app.py --install-models
```

Expect roughly 1 GB. They land in `apps/studio/models/hub` and are shared by the
GUI, the CLI and a frozen build.

If a model shows `incomplete, missing: …`, delete that folder from
`models/hub` and re-run `--install-models`.

## Output quality

### The script is read verbatim off the captions
No Gemini key is set, so the app falls back to raw BLIP captions. Add one under
**⚙ API key**, put it in `.env`, or bypass the model with `--caption "…"`.

### The voice speaks the wrong language
`--lang auto` only detects *speech*, so a silent clip always resolves to English.
For an image, or a video whose audio is music, set it explicitly:

```bash
python apps\studio\app.py photo.jpg --lang ar
```

Also check the voice: `ar-*` voices read Arabic, `en-*` voices read English.

### Speech is too fast or too slow

```bash
--rate -15%     # slower
--rate +20%     # faster
```

The same slider is live in the GUI.

### Subtitles are cut off at the edges

```bash
--sub-size 16        # smaller type
--sub-margin-v 48    # lift off the bottom edge
--aspect 9:16        # give the text a taller frame
```

Arabic burns correctly provided the system has an Arabic-capable font;
`--sub-font` accepts any installed font name.

### Subtitles drift out of sync
The app times subtitles from the rendered audio, so drift means the render was
cut short. Use `--quality high` and avoid `--keep`-less interrupted runs.

### The image is cropped wrong
`--fit contain` keeps the whole image (letterboxed), `--fit blur` puts it over a
blurred backdrop. In Fill mode, click the preview to set the focal point, or set
it precisely:

```bash
--fx 0.3 --fy 0.7
```

## App

### The window looks cramped
Minimum size is 1080×720. Resize or move it to a larger display — the layout is
two columns and needs the width.

### Nothing happens when I press Generate
Check the Activity log at the bottom left. Common causes: no media selected, the
file path no longer exists, or the local models are missing. The stage strip
shows which stage it reached.

### The preview is blank
`preview needs Pillow` means Pillow is not installed in the interpreter running
the app. Images with no embedded preview, and videos without ffmpeg, also show
the empty state.

### The models card says "models_setup.py missing"
The file was moved or deleted. It must sit next to `app.py`.

### Cancel does nothing immediately
Reel asks the subprocess to terminate. ffmpeg usually stops at the next frame;
give it a moment before pressing again.

## Build

### `pyinstaller` is not recognized
`pip install pyinstaller`.

### `iscc` is not recognized
Install Inno Setup 6, or add it to `PATH`. The build writes
`dist\VideoVoiceOver\` first; the installer needs that to exist.

### The build is huge
Expected — torch and transformers are bundled. Roughly 350–400 MB for the
installer.

### The build fails on a locked file
A previous build may still be running. `build.ps1` stops stray
`VideoVoiceOver*` processes; if it still fails, close Explorer windows pointed
inside `dist\`.

## Still stuck

Open an issue with the version, your Windows build, the output of
`python apps\studio\app.py --models`, and the Activity log from the failing run.
