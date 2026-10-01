"""Scan every blob in git history for leaked secrets and PII.

Usage: python tools/audit_history.py
Exit 1 if anything suspicious is found.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# High-confidence credential shapes
PATTERNS = {
    "google-api-key": r"AIza[0-9A-Za-z_\-]{35}",
    "aws-access-key": r"AKIA[0-9A-Z]{16}",
    "github-token": r"gh[pousr]_[0-9A-Za-z]{36,}",
    "slack-token": r"xox[baprs]-[0-9A-Za-z-]{10,}",
    "openai-key": r"sk-[A-Za-z0-9]{32,}",
    "private-key-block": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
    "bearer-jwt": r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
}

# Assignments that look like secrets, even with an unusual value shape
ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|credential)\b\s*[:=]\s*"
    r"[\"']?([^\s\"'#<>]{12,})[\"']?"
)

# Environment-variable style placeholders are fine
PLACEHOLDER = re.compile(
    r"(?i)^(your|my|test|dummy|example|placeholder|xxx+|changeme|<|\$\{|os\.|"
    r"none|null|true|false|\d+|tk\.|getenv|environ)"
)

PII = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "windows-user-path": re.compile(r"[A-Z]:\\\\Users\\\\[A-Za-z0-9_.\-]+"),
}


def all_blobs() -> list[tuple[str, str, str]]:
    """(sha, path, content) for every blob reachable from any ref."""
    out = []
    seen = set()
    revs = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    for line in revs:
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        sha, path = parts
        if sha in seen:
            continue
        seen.add(sha)
        kind = subprocess.run(["git", "cat-file", "-t", sha],
                              capture_output=True, text=True).stdout.strip()
        if kind != "blob":
            continue
        body = subprocess.run(["git", "cat-file", "-p", sha],
                              capture_output=True).stdout
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            continue  # binary: icon.ico, test.jpg
        if len(text) > 2_000_000:
            continue
        out.append((sha[:10], path, text))
    return out


def main() -> int:
    blobs = all_blobs()
    print(f"scanning {len(blobs)} blobs across all history\n")

    findings: list[tuple[str, str, str]] = []

    for sha, path, text in blobs:
        for name, pat in PATTERNS.items():
            for m in re.finditer(pat, text):
                findings.append((name, path, f"{sha}: {m.group(0)[:24]}…"))
        for m in ASSIGNMENT.finditer(text):
            value = m.group(2)
            if PLACEHOLDER.match(value) or value.endswith("()"):
                continue
            if value.startswith(("self.", "$", "{", "<", "tk.", "os.")):
                continue  # widget/attribute reference, not a literal credential
            if "_API_KEY" in value.upper() or "_KEY" in value.upper():
                continue
            if value.startswith(("./", "../", "/")) or value.endswith((".py", ".json", ".txt")):
                continue  # a path, not a secret
            if re.fullmatch(r"[A-Za-z_][\w.]*", value):
                continue  # bare identifier
            findings.append(("assigned-secret", path, f"{sha}: {m.group(1)}={value[:16]}…"))

    for sha, path, text in blobs:
        for name, pat in PII.items():
            for m in re.finditer(pat, text):
                findings.append((name, path, f"{sha}: {m.group(0)[:48]}"))

    if findings:
        print(f"POTENTIAL ISSUES ({len(findings)}):")
        for name, path, detail in findings:
            print(f"  [{name}] {path}  {detail}")
        return 1

    print("no secrets, tokens, private keys, emails or absolute user paths found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
