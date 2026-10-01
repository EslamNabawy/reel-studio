"""Print the CLI + GUI surface (used to keep docs accurate)."""
import re
from pathlib import Path

t = Path("apps/studio/voiceover.py").read_text(encoding="utf-8")
seg = t[t.index("def build_parser"):t.index("def main()")]
print("=== CLI flags ===")
for line in seg.splitlines():
    g = re.search(r'add_argument_group\("([^"]+)"\)', line)
    if g:
        print(f"[{g.group(1)}]")
    a = re.search(r'add_argument\(\s*"(--?[a-z0-9-]+)"', line)
    if a:
        print("   ", a.group(1))

g = Path("apps/studio/gui.py").read_text(encoding="utf-8")
print("\n=== GUI shortcuts ===")
for m in re.finditer(r'root\.bind\("<([^>]+)>", lambda e: self\.(\w+)\(\)\)', g):
    print("   ", m.group(1), "->", m.group(2))
print("\n=== voices ===")
for v in re.findall(r'"([a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural)', g):
    print("   ", v)
print("\n=== pipeline stages ===")
for s in re.findall(r'\),\s*\n?\s*"([A-Za-z][A-Za-z ]+)"\)', g):
    print("   ", s)
