"""Repository hygiene: fail the build when a secret is about to be committed.

Scans tracked text files (or explicit paths) with `quest_app.secret_patterns`. Prints
findings as `path:line:column: [pattern] description`, never the secret itself.

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
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    return scan_text(text)


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
                            "path": str(path.relative_to(REPO_ROOT)),
                            "line": m.line,
                            "column": m.column,
                            "pattern": m.pattern_id,
                            "description": m.description,
                            "excerpt": m.excerpt,
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
            rel = path.relative_to(REPO_ROOT)
            print(f"{rel}:{m.line}:{m.column}: [{m.pattern_id}] {m.description} — {m.excerpt}")
        print(f"secret-scan: {scanned} files scanned, {len(findings)} finding(s)", file=sys.stderr)

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
