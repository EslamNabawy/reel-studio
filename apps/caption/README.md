# Caption (`apps/caption`)

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)

BLIP captioning + VQA over a folder of images. Results written to CSV.

## Usage

From the repo root:

```bash
pip install -r apps\caption\requirements.txt
python apps\caption\caption.py <images>                  # caption every image
python apps\caption\caption.py <images> --question "what is on the table?"
python apps\caption\caption.py <images> --ar --out captions.csv
```

| Flag | Effect |
| --- | --- |
| `--question "..."` | Ask about each image (VQA mode) instead of captioning |
| `--ar` | Add Arabic translation column (needs `GEMINI_API_KEY`) |
| `--out FILE` | Save results to CSV |

Models:

- `Salesforce/blip-image-captioning-base` — captioning
- `Salesforce/blip-vqa-capfilt-large` — question answering

First run downloads models into the HuggingFace cache.

Back to [root README](../../README.md) · [Releases](https://github.com/EslamNabawy/reel-studio/releases).
