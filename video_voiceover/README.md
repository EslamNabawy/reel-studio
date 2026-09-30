# Video VoiceOver

Desktop app that adds AI voice-over and burned subtitles to videos and images.
Images become a short video: still frame + voice + subtitles.

## Run from source

```bash
python app.py            # GUI
python app.py file.mp4   # CLI
```

CLI examples:

```bash
python app.py myvideo.mp4
python app.py photo.jpg --lang ar
python app.py videos_folder\ --interval 1 --voice ar-EG-ShakirNeural
```

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
