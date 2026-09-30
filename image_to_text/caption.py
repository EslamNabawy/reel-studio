import argparse
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent / ".env")

BASE_MODEL = "Salesforce/blip-image-captioning-base"
VQA_MODEL = "Salesforce/blip-vqa-capfilt-large"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_model(name: str):
    print(f"Loading {name} (first run downloads it)...")
    processor = BlipProcessor.from_pretrained(name)
    model = BlipForConditionalGeneration.from_pretrained(name)
    return processor, model


def describe(processor, model, image: Image.Image, question: str | None) -> str:
    if question:
        inputs = processor(image, question, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=40)
    else:
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=60)
    return processor.decode(out[0], skip_special_tokens=True)


def translate_arabic(text: str) -> str:
    import os

    from google import genai

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return "(no GOOGLE_API_KEY - skipped translation)"
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=f"Translate this image description to Arabic. Reply with translation only:\n\n{text}",
    )
    return resp.text or ""


def collect_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    sys.exit(f"Not found: {path}")


def main():
    ap = argparse.ArgumentParser(description="BLIP image-to-text")
    ap.add_argument("path", help="image file or folder")
    ap.add_argument("-q", "--question", help="ask specific question (VQA mode)")
    ap.add_argument("--ar", action="store_true", help="also translate result to Arabic")
    ap.add_argument("--out", help="save results to CSV file")
    args = ap.parse_args()

    images = collect_images(Path(args.path))
    if not images:
        sys.exit("No images found.")

    model_name = VQA_MODEL if args.question else BASE_MODEL
    processor, model = load_model(model_name)

    results = []
    for img_path in images:
        try:
            image = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"{img_path.name}: ERROR {e}")
            continue
        text = describe(processor, model, image, args.question)
        line = f"{img_path.name}: {text}"
        if args.ar:
            ar = translate_arabic(text)
            print(f"{img_path.name}: {text}")
            print(f"  -> {ar}")
        else:
            print(line)
        results.append((img_path.name, text))

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["image", "description"])
            w.writerows(results)
        print(f"saved {len(results)} rows -> {args.out}")


if __name__ == "__main__":
    main()
