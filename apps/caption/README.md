# Caption (`apps/caption`)

BLIP captioning + VQA over a folder of images. Results written to CSV.

## Usage

From the repo root:

```bash
pip install -r apps\caption\requirements.txt
python apps\caption\caption.py <images>                  # caption every image
python apps\caption\caption.py <images> --question "what is on the table?"
```

Models:

- `Salesforce/blip-image-captioning-base` — captioning
- `Salesforce/blip-vqa-capfilt-large` — question answering

First run downloads models into `hf_models/`.
