Video Voice-Over App
====================

Handles VIDEOS (mp4/mov/avi/mkv/webm) and IMAGES (png/jpg/jpeg/webp/bmp/gif).
Images become a short video: still image + voice-over + burned subtitles.

Double-click VideoVoiceOver.exe        -> GUI (no console)
VideoVoiceOver_CLI.exe                 -> command line version

CLI examples (run from this folder in cmd/PowerShell):
  VideoVoiceOver_CLI.exe myvideo.mp4
  VideoVoiceOver_CLI.exe photo.jpg --lang ar
  VideoVoiceOver_CLI.exe videos_folder\ --interval 1 --voice ar-EG-ShakirNeural

Options:
  --lang auto|ar|en     narration language (default auto detect;
                        images default to English unless you pass --lang)
  --interval SECONDS    seconds per frame for videos (default 2)
  --voice VOICE         edge-tts voice override, e.g. en-US-AriaNeural
  --keep                keep intermediate work files

Requirements:
  - Internet needed for TTS + Gemini narration.
    AI models (BLIP + whisper) are bundled in models\ — offline fallback
    narration uses raw captions if GOOGLE_API_KEY missing.
  - .env file next to the exe must contain:  GOOGLE_API_KEY=...

Output:  output\<name>_voiceover_<lang>.mp4   (voice-over + burned subtitles)
