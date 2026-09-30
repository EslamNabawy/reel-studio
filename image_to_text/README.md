# Image to Text

BLIP captioning + VQA over a folder of images. Results written to CSV.

## Usage

```bash
python caption.py images\                  # caption every image
python caption.py images\ --question "what is on the table?"
```

Models:

- `Salesforce/blip-image-captioning-base` — captioning
- `Salesforce/blip-vqa-capfilt-large` — question answering

First run downloads models into `hf_models/`.
