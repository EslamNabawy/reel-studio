# Video VoiceOver

Desktop app that adds AI voice-over and burned subtitles to videos and images.
Images become a short video: still frame + voice + subtitles, with real framing
control (aspect, fit, focal point, Ken Burns motion).

## Run from source

```bash
python app.py            # GUI
python app.py file.mp4   # CLI
```

CLI examples:

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

## Build exe

```powershell
.\build.ps1
```

Output lands in `dist\VideoVoiceOver\`:

- `VideoVoiceOver.exe` — GUI, no console
- `VideoVoiceOver_CLI.exe` — command line

## Stack

`edge-tts` (speech) · `faster-whisper` (transcription) · `BLIP` (image captioning) · `ffmpeg` (mux + subtitle burn-in, must be on PATH) · PyInstaller (packaging).

`build/`, `dist/`, `hf_models/`, `output/` are git-ignored.
