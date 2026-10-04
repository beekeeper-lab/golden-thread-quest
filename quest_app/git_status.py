"""Read-only Git inspection.

This module reports and advises. It never commits, pushes, merges, resets, cleans or
checks out (C19). Every call is a fixed argument list with no shell, so nothing a
participant types can become part of a command, and every command is one that cannot
modify the repository even if it were somehow given different arguments.

Committing is the participant's act. An application that silently committed someone's
evidence would be making a claim on their behalf about work being finished.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

TIMEOUT_SECONDS = 10

# Every command this module is permitted to run. Read-only by construction, and listed so a
# reviewer can check the claim in one glance rather than reading every call site.
READ_ONLY_COMMANDS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("rev-parse", "--abbrev-ref", "HEAD"),
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
        ("status", "--porcelain=v1", "--untracked-files=normal"),
        ("log", "-1", "--format=%H"),
        ("check-ignore", "-z", "--stdin"),
    }
)


@dataclass(frozen=True, slots=True)
class GitStatus:
    available: bool
    is_repository: bool = False
    branch: str | None = None
    upstream: str | None = None
    head: str | None = None
    changed: int = 0
    untracked: int = 0
    changed_paths: tuple[str, ...] = field(default_factory=tuple)
    reason: str | None = None

    @property
    def clean(self) -> bool:
        return self.changed == 0 and self.untracked == 0

    def contains_uncommitted(self, prefix: str) -> bool:
        """Whether anything under `prefix` is uncommitted — used to advise, never to act.

        Porcelain reports a whole new directory as one untracked entry ending in `/`
        (`participant/`), never one line per file below it, so a brand-new evidence package
        is `prefix` extending a shorter recorded path rather than the other way round. Only
        checking `path.startswith(prefix)` (round 14 E3) never matched that shorter entry, so
        a package Git had never seen was reported as committed — worse than the round-7 bug
        this module's docstring already describes, because it is the normal state of every
        first attempt. Checking both directions catches a new directory above `prefix`, a new
        directory at `prefix` itself, and a changed file below it.
        """
        return any(
            path.startswith(prefix) or prefix.startswith(path) for path in self.changed_paths
        )


def _run(repo_root: Path, arguments: tuple[str, ...], *, raw: bool = False) -> str | None:
    if arguments not in READ_ONLY_COMMANDS:
        raise ValueError(f"git command not on the read-only list: {arguments!r}")
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_root), *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    # `raw` for porcelain: its status field is two columns wide and the first one is often
    # a space, so stripping the output ate the first line's status and shifted its path by
    # a character. Every other command here returns one token that wants stripping.
    return result.stdout if raw else result.stdout.strip()


def inspect(repo_root: Path) -> GitStatus:
    """Current repository state, or an explanation of why it could not be read.

    A missing `git`, or a directory that is not a repository, is a normal condition and not
    an error: the curriculum is readable either way.
    """
    toplevel = _run(repo_root, ("rev-parse", "--show-toplevel"))
    if toplevel is None:
        return GitStatus(
            available=False,
            reason="Git is not available here, or this directory is not a repository.",
        )

    porcelain = (
        _run(repo_root, ("status", "--porcelain=v1", "--untracked-files=normal"), raw=True) or ""
    )
    changed: list[str] = []
    untracked = 0
    # Every path Git reports as not-yet-committed, changed or untracked alike, so
    # `contains_uncommitted` has something to match against either way (round 14 E3, below).
    paths: list[str] = []
    for line in porcelain.splitlines():
        if not line:
            continue
        # Porcelain v1 is a fixed two-character status field, a space, then the path.
        # Splitting on the first space lost the path of every unstaged change: a tracked
        # file edited but not staged is `" M path"`, whose first space is at index 0, so
        # the status letter stayed on the front of the name and `contains_uncommitted`
        # could never match it. The evidence workspace then told a participant their
        # evidence was committed when it was not, which is worse than not saying.
        name = line[3:] if len(line) > 3 else ""
        # A rename is `R  old -> new`. What is uncommitted is where the file is now.
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        path = name.strip().strip('"')
        if line.startswith("??"):
            untracked += 1
            # A brand-new package is one line, the directory itself (`participant/`), not a
            # line per file below it. Counted here and only here — the untracked count in
            # `summary_for` still means what it always meant — but the path is still recorded,
            # or a new attempt's evidence never appeared in `changed_paths` at all and every
            # first attempt was reported as already committed.
            if path:
                paths.append(path)
        elif path:
            changed.append(path)
            paths.append(path)

    return GitStatus(
        available=True,
        is_repository=True,
        branch=_run(repo_root, ("rev-parse", "--abbrev-ref", "HEAD")),
        upstream=_run(
            repo_root, ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        ),
        head=_run(repo_root, ("log", "-1", "--format=%H")),
        changed=len(changed),
        untracked=untracked,
        changed_paths=tuple(sorted(paths)),
    )


def summary_for(repo_root: Path, evidence_path: str | None) -> dict[str, object]:
    """What the evidence workspace shows, including advice the participant has to act on."""
    status = inspect(repo_root)
    if not status.available:
        return {"available": False, "reason": status.reason}
    # `evidence_path` is always a `participant/...` contract path (ADR-018), never one this
    # module resolves through the configured participant root — it has no other root to
    # resolve it against. With `GTQ_PARTICIPANT_ROOT` pointed outside the repository, the
    # evidence this names lives somewhere `git status` on `repo_root` says nothing about, and
    # every check below silently found no match for it and reported it as committed. Whether
    # the package Git actually knows about sits where the contract path says, under
    # `repo_root`, is the one thing checkable without that root.
    known = evidence_path is not None and (repo_root / evidence_path).is_dir()
    return {
        "available": True,
        "branch": status.branch,
        "upstream": status.upstream,
        "changed": status.changed,
        "untracked": status.untracked,
        "evidence_committed": (
            not status.contains_uncommitted(evidence_path) if known and evidence_path else None
        ),
        "advice": (
            "Your evidence has uncommitted changes. Commit and push it after you submit, so a "
            "reviewer sees what you did."
            if known and evidence_path and status.contains_uncommitted(evidence_path)
            else None
        ),
    }


def ignored_paths(directory: Path, relatives: Sequence[str]) -> frozenset[str]:
    """Which of `relatives` (paths under `directory`) Git ignores and would never carry.

    Phase 2A.2: an ignored file in an evidence package is never handed in, so the reviewer's
    clone does not have it. Counting it in the evidence hash made every such package read as
    "changed" on one side or the other. A tracked file is not reported even if a pattern
    matches it, because Git does carry it. Outside a repository, or if Git cannot be run,
    nothing is reported and the hash covers every file, as before.
    """
    arguments = ("check-ignore", "-z", "--stdin")
    if arguments not in READ_ONLY_COMMANDS or not relatives:
        return frozenset()
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(directory), *arguments],  # noqa: S607
            input="\0".join(relatives) + "\0",
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    # 0: some paths are ignored. 1: none are. Anything else: not a repository, or an error.
    if result.returncode != 0:
        return frozenset()
    return frozenset(path for path in result.stdout.split("\0") if path)
