<div align="center">

# Reel Studio — caption CLI

**BLIP captioning and VQA over a folder of images.**

[![CI](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/EslamNabawy/reel-studio/actions/workflows/ci.yml)

[Root README](../../README.md) · [Studio app](../studio/README.md)

</div>

---

The companion CLI to [Reel Studio](../studio/README.md). It captions images with
BLIP, optionally asks a question about each one (VQA), and writes the results to
CSV. Useful on its own for dataset labelling.

## Run

From the repo root:

```bash
pip install -r apps\caption\requirements.txt

python apps\caption\caption.py images\                          # caption every image
python apps\caption\caption.py images\ --out captions.csv       # save results
python apps\caption\caption.py photo.jpg --question "what is on the table?"
python apps\caption\caption.py images\ --ar                     # add an Arabic column
```

| Flag | Effect |
| --- | --- |
| `-q`, `--question "..."` | VQA mode — ask about each image instead of captioning it |
| `--ar` | also translate each description to Arabic (needs `GEMINI_API_KEY`) |
| `--out FILE` | write results to a CSV file |

`path` may be a single image or a folder; a folder is scanned one level deep.

## Models

| Purpose | Model |
| --- | --- |
| captioning | `Salesforce/blip-image-captioning-base` |
| question answering | `Salesforce/blip-vqa-capfilt-large` |

The first run downloads them into the HuggingFace cache. Captioning uses the
smaller base model; VQA loads the larger one, so plain captioning stays quick.

## Output

```csv
image,description
test.jpg,a black cat sitting on a windowsill
```

`--ar` prints the translation to the console; the CSV still has the two columns
above.

## Requirements

`transformers` · `torch` · `Pillow` · `google-genai` · `python-dotenv`
