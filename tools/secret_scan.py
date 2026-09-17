"""Repository hygiene: fail the build when a secret is about to be committed.

Scans tracked text files (or explicit paths) with `quest_app.secret_patterns`. Prints
findings as `path:line:column: [pattern] description`, never the secret itself.

A line ending in `# secret-scan: allow` is skipped. This is how the scanner's own test
fixtures — which must contain strings that look exactly like real credentials — live in the
repository without failing the build, and it is why the alternative of loosening `PATTERNS`
was not taken.

The pragma is deliberately implemented **here** and not in `quest_app.secret_patterns`. This
file is repository hygiene over program-owned code that a reviewer reads. Evidence scanning
and validator-output redaction call `scan_text` directly, so a participant cannot switch off
the check on their own submission by writing a comment in it.

Usage:
    python tools/secret_scan.py                  # every tracked file
    python tools/secret_scan.py path [path ...]  # specific paths
    python tools/secret_scan.py --json           # machine-readable
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quest_app.secret_patterns import SecretMatch, scan_text

REPO_ROOT = Path(__file__).resolve().parent.parent

# Binary and generated content has no reviewable text and would produce noise.
SKIP_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".mp3",
        ".mp4",
        ".webm",
        ".lock",
    }
)
SKIP_DIRS = frozenset({"generated", "local-data", ".git", "node_modules", ".venv", "__pycache__"})
MAX_BYTES = 2_000_000

# A line carrying this marker is not scanned. Kept strict — an exact substring, not a regex —
# so it cannot be triggered by accident.
ALLOW_PRAGMA = "# secret-scan: allow"


def tracked_files() -> list[Path]:
    """Files git knows about, so an untracked scratch file never fails the build."""
    # Fixed argument list, no shell, no caller-supplied values: the only variable is the
    # repository root this file already lives in. `git` is resolved from PATH deliberately,
    # so the developer's own git is used rather than a hardcoded install location.
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return sorted(p for p in REPO_ROOT.rglob("*") if p.is_file())
    return [REPO_ROOT / name for name in result.stdout.split("\0") if name]


def eligible(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.stat().st_size <= MAX_BYTES


def scan_path(path: Path) -> list[SecretMatch]:
    """Findings in one file, minus any line that carries the allow pragma."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    allowed_lines = {
        number for number, line in enumerate(text.splitlines(), start=1) if ALLOW_PRAGMA in line
    }
    return [match for match in scan_text(text) if match.line not in allowed_lines]


def display_path(path: Path) -> str:
    """A repository-relative path, or the plain path when the caller named one outside it.

    `relative_to` raises for a path outside the root, which turned `secret_scan.py /tmp/x`
    into an unhandled traceback.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "paths", nargs="*", type=Path, help="Files to scan (default: tracked files)"
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable findings")
    args = parser.parse_args(argv)

    candidates = [p.resolve() for p in args.paths] if args.paths else tracked_files()
    findings: list[tuple[Path, SecretMatch]] = []
    scanned = 0
    for path in candidates:
        if not eligible(path):
            continue
        scanned += 1
        findings.extend((path, match) for match in scan_path(path))

    if args.json:
        print(
            json.dumps(
                {
                    "scanned": scanned,
                    "findings": [
                        {
                            "path": display_path(path),
                            "line": m.line,
                            "column": m.column,
                            "pattern": m.pattern_id,
                            "description": m.description,
                        }
                        for path, m in findings
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for path, m in findings:
            location = display_path(path)
            print(f"{location}:{m.line}:{m.column}: [{m.pattern_id}] {m.description} — {m.excerpt}")
        print(f"secret-scan: {scanned} files scanned, {len(findings)} finding(s)", file=sys.stderr)

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
