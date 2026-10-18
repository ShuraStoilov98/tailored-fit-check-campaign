"""Lightweight credential checks for local files and reachable Git history.

Print locations and pattern names only, never matching credential values.
This is a small guard against common mistakes, not a complete secret detector.
"""

import re
import subprocess
from pathlib import Path

PATTERNS = {
    "OpenAI key": rb"sk-[A-Za-z0-9_-]{20,}",
    "Google API key": rb"AIza[A-Za-z0-9_-]{30,}",
    "GitHub token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
    "AWS access key": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "private key": rb"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "Apps Script webhook": rb"https://script\.google\.com/macros/s/[A-Za-z0-9_-]{20,}/exec",
}


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def check_data(data: bytes, location: str) -> list[str]:
    return [f"{location}: possible {name}" for name, pattern in PATTERNS.items() if re.search(pattern, data)]


def check_path(path: str) -> list[str]:
    name = Path(path).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return [f"{path}: environment file must not be published"]
    return []


def main() -> int:
    findings = set()
    paths = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    for path in filter(None, paths):
        findings.update(check_path(path))
        file = Path(path)
        if file.is_file():
            findings.update(check_data(file.read_bytes(), path))

    blobs = 0
    for entry in git("rev-list", "--objects", "--all").decode().splitlines():
        oid, _, path = entry.partition(" ")
        findings.update(check_path(path))
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        blobs += 1
        findings.update(check_data(git("cat-file", "blob", oid), f"history {oid[:12]} {path}"))

    if findings:
        for finding in sorted(findings):
            print(finding)
        return 1
    print(f"No credential patterns or environment files found; checked local files and {blobs} historical blobs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
