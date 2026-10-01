"""Verify the key store: per-user location, legacy migration, no key beside the exe.

Uses a temporary APPDATA and a fake app dir, so it never touches the real
profile or the real key.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "studio"))

FAKE = "unit-test-key-not-a-real-secret"


def main() -> int:
    import os

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        appdata = base / "appdata"
        appdata.mkdir()
        os.environ["APPDATA"] = str(appdata)

        import keystore
        keystore.set_app_dir(base / "app")
        app_dir = base / "app"
        app_dir.mkdir()

        failures = []

        def check(label, ok):
            print(f"  {'ok  ' if ok else 'FAIL'}  {label}")
            if not ok:
                failures.append(label)

        store = keystore.key_store_path()
        check("store lives under the user profile", str(appdata) in str(store))
        check("store is not beside the exe", app_dir not in store.parents)

        # 1. save round-trip
        p = keystore.key_store_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"GEMINI_API_KEY={FAKE}\n", encoding="utf-8")
        check("read back from store", keystore.first_key(keystore.read_env_file(p)) == FAKE)

        # 2. a key beside the exe gets migrated and removed
        legacy = app_dir / ".env"
        legacy.write_text(f"GOOGLE_API_KEY={FAKE}\n", encoding="utf-8")
        keystore.migrate_legacy_key(app_dir)
        check("legacy file removed after migration", not legacy.exists())
        check("migrated into the user store",
              keystore.first_key(keystore.read_env_file(keystore.key_store_path())) == FAKE)

        # 3. a non-key .env beside the exe is left alone
        harmless = app_dir / ".env"
        harmless.write_text("# nothing secret\nOTHER=1\n", encoding="utf-8")
        keystore.migrate_legacy_key(app_dir)
        check("non-key .env preserved", harmless.exists())
        harmless.unlink()

        # 4. missing files never raise
        keystore.migrate_legacy_key(app_dir / "nope")
        check("missing app dir tolerated", True)

        # 5. store read wins over legacy
        store.write_text(f"GEMINI_API_KEY={FAKE}\n", encoding="utf-8")
        legacy2 = app_dir / ".env"
        legacy2.write_text("GOOGLE_API_KEY=different\n", encoding="utf-8")
        found = next((keystore.first_key(keystore.read_env_file(p))
                      for p in keystore.candidate_paths(app_dir) if p.exists()), "")
        check("user store takes precedence", found == FAKE)
        legacy2.unlink()

        print()
        if failures:
            print(f"{len(failures)} failure(s)")
            return 1
        print("keystore ok - key never lives beside the executable")
        return 0


if __name__ == "__main__":
    sys.exit(main())
