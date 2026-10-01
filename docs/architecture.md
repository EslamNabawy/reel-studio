# Architecture

How Reel Studio is put together, and why.

## Process model

The app is two processes, not one.

```
┌─ GUI process ────────────────┐        ┌─ worker process ──────────────┐
│  Tk main loop                │        │  apps/studio/voiceover.py     │
│  widgets, preview, drag-drop │ ─────► │  ffmpeg · BLIP · Whisper      │
│  queue.Queue ◄───────────────┘ stdout│  Gemini · edge-tts             │
└──────────────────────────────┘        └────────────────────────────────┘
```

`gui.py` never imports the engine. It builds a command line, spawns
`app.py`/`voiceover.py` as a subprocess, streams stdout line by line into a
`queue.Queue`, and drains that queue on the main loop with `after()`. Three
things fall out of that split:

- the UI never blocks on a multi-minute render;
- the engine is importable and testable without a display;
- cancelling is just `proc.terminate()`.

## Threading rules

| Thread | May do | Must not |
| --- | --- | --- |
| main loop | touch any widget | block on a subprocess |
| worker | `Popen`, read stdout, `queue.put` | touch a widget |

`gui.py:_poll` is the only consumer. It also parses streamed lines against
`STAGES` to drive the progress strip.

## The pipeline

`voiceover.py:main()` walks one media item at a time (a file, or every video and
image in a folder):

```
1. media_info        ffprobe → width, height, duration, fps
2. target_size       aspect + height → output frame (even dims, capped at 3840)
3. detect_language   Whisper tiny on the first 30s (auto mode, videos only)
4. extract_frames    ffmpeg fps=1/interval      (videos)
5. caption_frames    BLIP per frame, de-duplicated by similarity ≥ 0.80
6. build_narration   Gemini rewrites captions into a spoken script
7. tts               edge-tts, one file per segment
8. concat_audio      ffmpeg concat + silence gaps between segments
9. make_srt          timings from real audio durations, not estimates
10. mux / mux_image  ffmpeg: pad or extend video to fit audio, burn subtitles
```

Two details that matter for output quality:

**Timings come from the rendered audio.** `segment_times()` calls `ffprobe` on
each synthesised segment, so subtitles cannot drift from the voice.

**Images and videos take different render paths.** `mux_image` builds a
`zoompan` filter chain for Ken Burns motion; `mux` handles real footage. Both
share the subtitle and audio-mux logic.

## Frame engine

`image_filter()` composes a filter graph from fit mode:

| fit | chain |
| --- | --- |
| `cover` | scale up → `zoompan` (optional) → crop to the frame at the focal point |
| `contain` | scale up → `zoompan` (optional) → letterbox onto black |
| `blur` | split → blurred cover backdrop + scaled foreground, overlaid |

The source is scaled to ~1.15× the output before `zoompan` so motion has pixels
to travel through. Focal point `--fx` / `--fy` anchors the crop and the pan.

## Theme and widgets

`gui.py` holds a `C` token dict and a small widget kit — `Hover`, `Chip`,
`Segmented`, `Card`, `Field`, `Slider`, `ScrollPane`, plus `RoundedSurface`,
which paints a rounded rectangle on a canvas because Tk has no native one.
Cards and the drop zone are `RoundedSurface`s; children go in `.inner`.

Every colour is a token. If you add a UI element, use a token rather than a hex
literal, or the theme stops being themeable.

## Local models

`models_setup.py` reports and downloads the two local models into
`apps/studio/models/hub`, sharing one cache between the GUI, the CLI and the
frozen build (`HF_HOME`). `--models` prints status; `--install-models`
downloads.

The app is built to work without them: it degrades to raw captions rather than
failing.

## Secrets

The Gemini key is read from `.env` beside the exe, falling back to the repo-root
`.env`. `build.ps1` deletes any `.env` from the bundle and copies
`.env.example` in its place, so a build can never ship a key.

## Tests

- `tests/test_studio.py` — engine logic: image detection, frame-size maths,
  subtitle style strings, SRT timing format, filter-chain construction, parser
  defaults. No models, no network, no ffmpeg.
- `tools/gui_smoke.py` — builds the real window offscreen, walks every section
  in every media mode, fires every layout callback, asserts shapes painted and
  the argument build, and traps `report_callback_exception` so a broken Tk
  handler fails the run.

That split is deliberate: fast pure-logic tests for the engine, one structural
test for the UI.
