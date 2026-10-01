# The pipeline

What actually happens between dropping a file and getting an MP4.

## 1. Probe

`ffprobe` reads the container and reports width, height, duration and frame rate.
Images skip this and are read with Pillow instead.

## 2. Frame sampling

Videos are sampled with `ffmpeg -vf fps=1/<interval>` into JPEGs, so a 60-second
clip at the default 2-second interval yields about 30 frames. `--max-frames`
caps that.

An image is treated as a single frame — everything downstream is identical.

## 3. Vision captions

`BLIP` (`blip-image-captioning-base`) captions each frame. Near-identical
consecutive captions are collapsed using a similarity ratio of 0.80, so a static
scene does not produce thirty copies of "a man standing in a room".

Frames are analysed in order and the captions are what the script is written
from — they are never invented.

## 4. Language detection

In `--lang auto`, `Whisper tiny` transcribes the first 30 seconds and returns
the dominant language, accepted only above 0.50 confidence. Below that it falls
back to English.

Silent clips have nothing to detect, so images and music videos should use an
explicit `--lang`.

## 5. Script

Gemini turns the ordered captions into spoken narration — a JSON array of short
sentences, returned under a JSON mime type so it parses cleanly. This is the
step that needs an API key; without one the raw captions are spoken instead.

Override it entirely with `--caption`, or see the captions verbatim with
`--raw-captions`.

## 6. Voice

`edge-tts` synthesizes each segment to its own MP3:

| Language | Default voice |
| --- | --- |
| `en` | `en-US-AndrewNeural` |
| `ar` | `ar-EG-SalmaNeural` |

Rate and pitch are passed straight through (`--rate`, `--pitch`). Available
voices: `ar-EG-SalmaNeural`, `ar-EG-ShakirNeural`, `ar-SA-HamedNeural`,
`ar-SA-ZariyahNeural`, `en-US-AndrewNeural`, `en-US-AriaNeural`,
`en-US-GuyNeural`, `en-GB-SoniaNeural`.

## 7. Assembly

1. Segments are concatenated with a 0.3 s silence gap between them.
2. Each segment is probed for its true duration, and those durations become the
   SRT timings — so subtitles are locked to the audio, not estimated.
3. Video is padded with a frozen last frame if the voice outlasts it, or padded
   with silence if the video is longer.
4. Subtitles are burned in with the `subtitles` filter and a `force_style` built
   from the font, size, outline, margin and colour.

## 8. Encode

H.264 (`libx264`) + AAC, `yuv420p` for player compatibility:

| `--quality` | CRF | Preset |
| --- | --- | --- |
| `draft` | 30 | veryfast |
| `good` | 23 | veryfast |
| `high` | 19 | medium |

Use `draft` while iterating on a long clip, `high` for the final render.

## Cost and privacy

| Step | Leaves your machine |
| --- | --- |
| frame sampling | no |
| vision captions | no |
| language detect | no |
| script writing | frames' captions → Gemini |
| voice synthesis | the script text → edge-tts |
| mux + burn | no |

The source media itself is never uploaded. Only the derived text goes to the two
cloud services — and only when the corresponding feature is in use.
