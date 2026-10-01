import sys


def main() -> None:
    args = sys.argv[1:]

    if args and args[0] in ("--install-models", "-m"):
        import models_setup

        print(f"model cache: {models_setup.CACHE}")
        for m in models_setup.status():
            state = "OK     " if m["installed"] else "MISSING"
            print(f"  {state}  {m['label']:<32} {m['size_mb']:>8.1f} MB"
                  + (f"  missing: {', '.join(m['missing'])}" if m["missing"] else ""))
        if not models_setup.all_installed():
            print("\ndownloading missing models (about 1 GB)…")
            for line in models_setup.install(log=lambda s: print("  " + s)):
                print(line)
        return

    if args and args[0] in ("--models",):
        import models_setup

        print(f"model cache: {models_setup.CACHE}")
        for m in models_setup.status():
            state = "OK     " if m["installed"] else "MISSING"
            print(f"  {state}  {m['label']:<32} {m['size_mb']:>8.1f} MB"
                  + (f"  missing: {', '.join(m['missing'])}" if m["missing"] else ""))
        return

    if args:
        import voiceover

        voiceover.main()
    else:
        import gui

        gui.main()


if __name__ == "__main__":
    main()
