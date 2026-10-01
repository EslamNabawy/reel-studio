# Reel Studio docs

| Document | What is in it |
| --- | --- |
| [architecture.md](architecture.md) | Process model, threading rules, the pipeline, the frame engine, the theme, tests |
| [pipeline.md](pipeline.md) | Step by step: probe → frames → captions → script → voice → mux → encode |
| [troubleshooting.md](troubleshooting.md) | ffmpeg, models, language, subtitles, app and build problems |

Elsewhere:

- [Root README](../README.md) — install, features, CLI
- [Studio app](../apps/studio/README.md) — the desktop app
- [Caption CLI](../apps/caption/README.md) — image captioning
- [CONTRIBUTING.md](../CONTRIBUTING.md) — dev setup and the checks CI runs
- [CHANGELOG.md](../CHANGELOG.md) — what changed in each release

## Local vs cloud

Worth knowing before you use it: the source media never leaves your machine.
Frame sampling, vision captions and language detection are local. Only two steps
use a network, and only when the feature is in use — the script rewrite
(captions → Gemini) and the voice synthesis (script → edge-tts). See
[pipeline.md](pipeline.md#cost-and-privacy).
