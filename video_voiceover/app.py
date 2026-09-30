import sys


def main() -> None:
    if len(sys.argv) > 1:
        import voiceover

        voiceover.main()
    else:
        import gui

        gui.main()


if __name__ == "__main__":
    main()
