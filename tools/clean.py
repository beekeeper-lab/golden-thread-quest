"""Remove generated output — and nothing else.

`make clean` in a repository that also holds a participant's own work is the most dangerous
convenience command here, so this is an allowlist in the strict sense: a target is removed
only when its repository-relative path is *exactly* an entry in `REMOVABLE`.

The earlier version resolved the path first and then screened the result against a denylist
of protected top-level names. That is not the same thing, and the Stage 1 audit broke it:
`generated` as a symlink to `prototype/` resolved to an unprotected path and `rmtree`
followed the link, and `generated/../README.md` resolved to a file the denylist never
mentioned. Both are closed below.

Usage:
    python tools/clean.py            # show what would be removed
    python tools/clean.py --apply    # remove it
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The only paths this script may ever remove, as exact repository-relative paths.
REMOVABLE: tuple[str, ...] = (
    "generated",
    "local-data/cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",
)

# A second, independent refusal. `REMOVABLE` is already exact, so nothing here should ever
# be reachable — which is the point: if a future edit adds an unsafe entry, this still
# refuses. Compared case-insensitively, because macOS filesystems are.
PROTECTED: tuple[str, ...] = (
    "participant",
    "fixtures",
    "content",
    "schemas",
    "templates",
    "prototype",
    "docs",
    "quest_app",
    "validators",
    "tests",
    "assets",
    "tools",
    ".github",
    ".git",
)


class UnsafeTargetError(RuntimeError):
    """A cleanup target that is not exactly an allowed path, or is reached through a link."""


def _contains_symlink(relative: Path) -> bool:
    """Whether any component of `relative`, walking down from the repository root, is a link.

    Checked on the *unresolved* path. A resolved path has no symlinks left in it, which is
    why resolving first and asking `is_symlink()` afterwards always answered "no".
    """
    current = REPO_ROOT
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def resolve_target(name: str) -> Path:
    """The path `name` refers to, proven safe to remove, or `UnsafeTargetError`.

    Returns the *unresolved* path, so a caller removing it unlinks a symlink rather than
    deleting whatever it points at.
    """
    expanded = Path(name).expanduser()
    if expanded.is_absolute():
        raise UnsafeTargetError(
            f"{name!r} is an absolute path; cleanup targets are repository-relative"
        )

    relative = Path(name)
    if any(part in ("..", "") for part in relative.parts):
        raise UnsafeTargetError(f"{name!r} contains a parent-directory segment")
    if relative.as_posix() not in REMOVABLE:
        raise UnsafeTargetError(f"{name!r} is not one of the removable paths")
    if any(part.casefold() in {p.casefold() for p in PROTECTED} for part in relative.parts):
        raise UnsafeTargetError(f"{name!r} names a protected path")
    if _contains_symlink(relative):
        raise UnsafeTargetError(f"{name!r} is, or is reached through, a symbolic link")

    unresolved = REPO_ROOT / relative
    # Belt and braces: even with no symlink in the path, confirm it lands inside the repo.
    if (
        REPO_ROOT not in unresolved.resolve().parents
        and unresolved.resolve() != REPO_ROOT / relative
    ):
        raise UnsafeTargetError(f"{name!r} resolves outside the repository")
    return unresolved


def plan() -> list[Path]:
    """Existing removable paths, each already proven safe. Unsafe entries are refused loudly."""
    targets: list[Path] = []
    for name in REMOVABLE:
        try:
            target = resolve_target(name)
        except UnsafeTargetError as exc:
            print(f"clean: skipping {name}: {exc}", file=sys.stderr)
            continue
        if target.exists() or target.is_symlink():
            targets.append(target)
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="Actually remove the listed paths")
    args = parser.parse_args(argv)

    targets = plan()
    if not targets:
        print("clean: nothing to remove")
        return 0
    for target in targets:
        relative = target.relative_to(REPO_ROOT)
        if args.apply:
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            print(f"removed {relative}")
        else:
            print(f"would remove {relative}")
    if not args.apply:
        print("clean: dry run — pass --apply to remove", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
