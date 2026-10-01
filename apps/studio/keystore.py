"""Where the Gemini key lives, shared by the GUI and the CLI.

The key is stored per-user under the user profile, never inside the app folder.
That keeps secrets out of portable bundles: copy or share the built app and the
key does not travel with it.

No Tk and no third-party imports, so both ``gui.py`` and ``voiceover.py`` can use
this module.
"""
import os
from pathlib import Path

KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
ENV_FILE = ".env"

# Populated by the apps at import time; only used to find and clean up a key
# that an older build wrote next to the executable.
APP_DIR: Path | None = None


def set_app_dir(path: Path) -> None:
    global APP_DIR
    APP_DIR = Path(path)


def key_store_dir() -> Path:
    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / "Reel"
    return Path.home() / ".reel"


def key_store_path() -> Path:
    return key_store_dir() / ENV_FILE


def read_env_file(path: Path) -> dict:
    out: dict[str, str] = {}
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def first_key(env: dict) -> str:
    return next((env[n] for n in KEY_NAMES if env.get(n)), "")


def migrate_legacy_key(app_dir: Path | None = None) -> None:
    """Move a key written beside the exe (older builds) into the user profile.

    Best effort. On success the legacy file is deleted so a portable copy stops
    carrying a secret. If anything fails the legacy path remains a valid read
    fallback, so this never loses a key.
    """
    base = Path(app_dir) if app_dir else APP_DIR
    if base is None:
        return
    legacy = base / ENV_FILE
    if not legacy.exists():
        return
    found = first_key(read_env_file(legacy))
    if not found:
        return
    try:
        target = key_store_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(f"GEMINI_API_KEY={found}\n", encoding="utf-8")
        if first_key(read_env_file(target)) == found:
            legacy.unlink()
    except Exception:
        pass


def delete_legacy_key(app_dir: Path) -> None:
    """Remove a key file sitting next to the executable."""
    try:
        legacy = Path(app_dir) / ENV_FILE
        if legacy.exists():
            legacy.unlink()
    except Exception:
        pass


def candidate_paths(app_dir: Path | None = None) -> list[Path]:
    """Every place a key may live, most specific first."""
    base = Path(app_dir) if app_dir else APP_DIR
    paths = [key_store_path()]
    if base is not None:
        paths.append(base / ENV_FILE)
        paths.append(base.parent / ENV_FILE)
    return paths
