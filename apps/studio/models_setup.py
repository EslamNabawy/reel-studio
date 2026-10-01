"""Model manager: check, download and verify the local AI models.

Used by the GUI (Models card) and the CLI (`app.py --install-models`).
Downloads go through huggingface_hub so they land in the same cache layout the
app already reads at runtime.
"""
import os
import sys
import threading
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    BASE = Path(sys.executable).resolve().parent
    os.environ.setdefault("HF_HOME", str(BASE / "models"))
else:
    BASE = Path(__file__).resolve().parent

CACHE = BASE / "models" / "hub"

MODELS = [
    {
        "repo": "Salesforce/blip-image-captioning-base",
        "dir": "models--Salesforce--blip-image-captioning-base",
        "label": "Vision captions (BLIP)",
        "files": ["config.json", "preprocessor_config.json", "pytorch_model.bin"],
        "min_bytes": 400_000_000,
    },
    {
        "repo": "Systran/faster-whisper-tiny",
        "dir": "models--Systran--faster-whisper-tiny",
        "label": "Language detect (Whisper tiny)",
        "files": ["config.json", "model.bin"],
        "min_bytes": 20_000_000,
    },
]


def _snapshot_dir(spec) -> Path:
    return CACHE / spec["dir"] / "snapshots"


def status() -> list[dict]:
    """Per-model: installed bool, size on disk, missing files."""
    out = []
    for spec in MODELS:
        root = CACHE / spec["dir"]
        missing = []
        found_any = False
        total = 0
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    total += p.stat().st_size
            snaps = list(_snapshot_dir(spec).glob("*"))
            for snap in snaps:
                if not snap.is_dir():
                    continue
                have = {f.name for f in snap.iterdir()}
                for f in spec["files"]:
                    if f in have:
                        found_any = True
                    else:
                        missing.append(f)
            if not snaps:
                missing = list(spec["files"])
        else:
            missing = list(spec["files"])
        out.append({
            "label": spec["label"],
            "repo": spec["repo"],
            "dir": str(root),
            "size_mb": round(total / 1e6, 1),
            "missing": missing,
            "installed": found_any and not missing,
        })
    return out


def all_installed() -> bool:
    return all(m["installed"] for m in status())


def _total_expected() -> int:
    return sum(m["min_bytes"] for m in MODELS)


def install(progress=None, log=None) -> list[str]:
    """Download any missing model. Returns list of messages.

    progress(done_bytes, total_bytes) and log(text) are optional callbacks so the
    GUI can render a bar without this module depending on Tk.
    """
    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        return [f"huggingface_hub unavailable: {e}"]

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    CACHE.mkdir(parents=True, exist_ok=True)

    msgs = []
    st = status()
    todo = [m for m in st if not m["installed"]]
    done_bytes = sum(m["size_mb"] * 1e6 for m in st if m["installed"])
    total_bytes = _total_expected()

    for m in todo:
        spec = next(s for s in MODELS if s["repo"] == m["repo"])
        if log:
            log(f"downloading {m['repo']} …")
        try:
            snapshot_download(
                repo_id=spec["repo"],
                cache_dir=str(CACHE),
                allow_patterns=["*.json", "*.txt", "*.bin", "*.model",
                                "*.safetensors", "*.tiktoken", "*tokenizer*"],
            )
        except Exception as e:
            msgs.append(f"{spec['repo']}: {e}")
            continue
        after = next(s for s in status() if s["repo"] == m["repo"])
        if after["installed"]:
            done_bytes += after["size_mb"] * 1e6
            msgs.append(f"{spec['repo']} installed ({after['size_mb']:.0f} MB)")
            if log:
                log(f"{spec['repo']} ready ({after['size_mb']:.0f} MB)")
        else:
            msgs.append(f"{spec['repo']} incomplete, missing: "
                        f"{', '.join(after['missing'])}")
        if progress:
            progress(min(done_bytes, total_bytes), total_bytes)

    still = [m for m in status() if not m["installed"]]
    if not still:
        msgs.append("all models ready — the app now runs fully offline")
    elif not msgs:
        msgs.append("nothing to do")
    return msgs


def install_async(progress=None, log=None, done=None) -> threading.Thread:
    def runner():
        msgs = install(progress=progress, log=log)
        if done:
            done(msgs)
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print(f"model cache: {CACHE}")
    for m in status():
        state = "OK " if m["installed"] else "MISSING"
        print(f"  {state}  {m['label']:<32} {m['size_mb']:>8.1f} MB"
              + (f"  missing: {', '.join(m['missing'])}" if m["missing"] else ""))
    if "--install" in sys.argv:
        print()
        for line in install(log=lambda s: print("  " + s)):
            print(line)
