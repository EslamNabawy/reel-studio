import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICEOVER = ROOT / "apps" / "studio" / "voiceover.py"
CAPTION = ROOT / "apps" / "caption" / "caption.py"
APP = ROOT / "apps" / "studio" / "app.py"
GUI = ROOT / "apps" / "studio" / "gui.py"

failures: list[str] = []


def cli_flags(path: Path) -> set[str]:
    """All long flags the file accepts, including '-q', '--question' pairs."""
    t = path.read_text(encoding="utf-8")
    flags: set[str] = set()
    # add_argument( ... "--flag" ... ) with arbitrary whitespace/newlines
    for call in re.findall(r"add_argument\((.*?)\)\n", t, re.S):
        for name in re.findall(r'"(--?[a-zA-Z0-9-]+)"', call):
            flags.add(name)
    return flags


def router_flags(path: Path) -> set[str]:
    """Flags handled by app.py's if-chain rather than argparse."""
    t = path.read_text(encoding="utf-8")
    out: set[str] = set()
    for group in re.findall(r'args\[0\] in \(([^)]*)\)', t):
        out |= set(re.findall(r'"(--?[a-zA-Z0-9-]+)"', group))
    return out


def readme_flags() -> set[str]:
    flags: set[str] = set()
    for doc in (ROOT / "README.md", ROOT / "apps" / "studio" / "README.md",
                ROOT / "apps" / "caption" / "README.md"):
        flags |= set(re.findall(r"`(--?[a-z][a-z0-9-]+)", doc.read_text(encoding="utf-8")))
    return flags


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        failures.append(label)


def main() -> int:
    print("docs consistency")

    # 1. every documented flag must exist in the code
    real_studio = cli_flags(VOICEOVER) | router_flags(APP)
    real_caption = cli_flags(CAPTION)
    documented = readme_flags()

    for flag in sorted(documented):
        if flag in ("--all", "--recursive"):  # tool/other-file flags
            continue
        check(f"{flag} exists", flag in real_studio or flag in real_caption,
              "(documented but not implemented)")

    # 2. every real flag should be documented (-m is a documented alias for
    #    --install-models, so it is covered by that entry)
    aliases = {"-m": "--install-models"}
    for flag in sorted(real_studio):
        target = aliases.get(flag, flag)
        check(f"{flag} documented", target in documented, "(implemented but undocumented)")

    # 3. shortcuts
    gui = GUI.read_text(encoding="utf-8")
    for combo, name in re.findall(r'root\.bind\("<([^>]+)>", lambda e: self\.(\w+)\(\)\)', gui):
        pretty = {"Control-o": "Ctrl+O", "Control-Return": "Ctrl+Enter",
                  "Escape": "Esc", "Control-k": "Ctrl+K"}.get(combo, combo)
        check(f"shortcut {pretty} documented", pretty in (ROOT / "README.md").read_text(encoding="utf-8")
              or pretty in (ROOT / "apps" / "studio" / "README.md").read_text(encoding="utf-8"))

    # 4. links in markdown must resolve
    for doc in list(ROOT.glob("*.md")) + list(ROOT.glob("docs/*.md")) + \
            list(ROOT.glob("apps/*/README.md")):
        for target in re.findall(r"\]\((?!https?:)([^)#]+)", doc.read_text(encoding="utf-8")):
            resolved = (doc.parent / target).resolve()
            check(f"{doc.name} -> {target}", resolved.exists(), "(broken link)")

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print("  -", f)
        return 1
    print("docs match the code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
