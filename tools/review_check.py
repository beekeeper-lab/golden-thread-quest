"""Check that a pilot hand-in pull request contains participant work and nothing else.

A hand-in is one participant's evidence, so every changed path must sit under `participant/`.
A change anywhere else (the application, a quest, a workflow, `install.sh`) is not evidence
and is never something a reviewer should accept or run. Code inside `participant/` is
allowed, because quests ask participants to write scripts, but it is untrusted: the check
lists it so a reviewer reads it before running it.

Usage: python tools/review_check.py <pull-request-number>   (needs the GitHub CLI signed in)
Exit status: 0 when every path is participant work, 1 when anything is outside it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

REPO = "beekeeper-lab/golden-thread-quest"
ALLOWED_ROOT = "participant"
CODE_SUFFIXES = frozenset(
    {".py", ".sh", ".bash", ".js", ".mjs", ".ts", ".rb", ".pl", ".ps1", ".bat", ".cmd", ".exe"}
)
NEEDS_SCRUTINY = frozenset({".github", ".git", ".gitmodules", ".gitattributes"})


@dataclass
class Verdict:
    outside: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    total: int = 0

    @property
    def safe(self) -> bool:
        return not self.outside


def _inside(path: str) -> bool:
    """True only for a normal relative path whose first folder is `participant`."""
    parts = PurePosixPath(path).parts
    if not parts or parts[0] != ALLOWED_ROOT or path.startswith("/") or "\\" in path:
        return False
    return all(part not in ("..", ".") and part not in NEEDS_SCRUTINY for part in parts)


def check_files(files: list[dict[str, Any]]) -> Verdict:
    """Judge GitHub's per-file records (`filename`, `status`, optional `previous_filename`)."""
    verdict = Verdict(total=len(files))
    for record in files:
        # A rename touches two paths, and moving a file *out of* the app is as much a change
        # as moving one in.
        paths = [record["filename"], record.get("previous_filename") or record["filename"]]
        for path in dict.fromkeys(paths):
            if not _inside(path):
                verdict.outside.append(path)
        name = record["filename"]
        if PurePosixPath(name).suffix.lower() in CODE_SUFFIXES and _inside(name):
            verdict.code.append(name)
        if record.get("status") == "removed" and _inside(name):
            verdict.removed.append(name)
    return verdict


def fetch_files(number: int) -> list[dict[str, Any]]:
    # A fixed command and an integer pull request number: nothing here is untrusted input.
    result = subprocess.run(  # noqa: S603
        ["gh", "api", "--paginate", "--slurp", f"repos/{REPO}/pulls/{number}/files?per_page=100"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    return [record for page in json.loads(result.stdout) for record in page]


def report(number: int, verdict: Verdict) -> str:
    lines = [f"PR #{number}: {verdict.total} changed files"]
    if verdict.safe:
        lines.append(f"SAFE: every path is under {ALLOWED_ROOT}/")
    else:
        lines.append(
            f"NOT SAFE: {len(verdict.outside)} path(s) outside {ALLOWED_ROOT}/."
            " Do not run or approve."
        )
        lines.extend(f"  outside: {path}" for path in verdict.outside)
    if verdict.code:
        lines.append("Code the participant wrote. It is untrusted: read it before running it.")
        lines.extend(f"  code: {path}" for path in verdict.code)
    if verdict.removed:
        lines.append("Files the participant deleted:")
        lines.extend(f"  removed: {path}" for path in verdict.removed)
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print(__doc__)
        return 2
    number = int(argv[1])
    verdict = check_files(fetch_files(number))
    print(report(number, verdict))
    return 0 if verdict.safe else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
