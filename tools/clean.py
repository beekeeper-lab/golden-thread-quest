"""Remove generated output — and nothing else.

`make clean` in a repository that also holds the participant's own work is the single most
dangerous convenience command here, so removal is an explicit allowlist rather than a
pattern, every target is verified to sit inside the repository, and the paths a participant
owns are refused even if they are somehow named.

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

# The only paths this script may ever remove. Documented in docs/ARCHITECTURE.md as
# machine-owned and disposable.
REMOVABLE: tuple[str, ...] = (
    "generated",
    "local-data/cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    ".coverage",
)

# Never removable, whatever else changes. A defence against a future edit to REMOVABLE.
PROTECTED: tuple[str, ...] = (
    "participant",
    "fixtures",
    "content",
    "schemas",
    "templates",
    "docs",
    "quest_app",
    "validators",
    "tests",
    "assets",
    "tools",
    ".git",
)


class UnsafeTargetError(RuntimeError):
    """A cleanup target that is outside the repository or inside protected territory."""


def resolve_target(name: str) -> Path:
    # `~` means home, not a directory literally named "~". Expanding first means a target
    # that points outside the repository is refused rather than silently reinterpreted.
    expanded = Path(name).expanduser()
    target = (expanded if expanded.is_absolute() else REPO_ROOT / expanded).resolve()
    if target == REPO_ROOT:
        raise UnsafeTargetError(f"refusing to remove the repository root via {name!r}")
    if REPO_ROOT not in target.parents:
        raise UnsafeTargetError(f"{name!r} resolves outside the repository: {target}")
    relative = target.relative_to(REPO_ROOT)
    if relative.parts and relative.parts[0] in PROTECTED:
        raise UnsafeTargetError(f"{name!r} is inside protected path {relative.parts[0]!r}")
    return target


def plan() -> list[Path]:
    """Existing removable paths, each already proven safe."""
    return [target for name in REMOVABLE if (target := resolve_target(name)).exists()]


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
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
            print(f"removed {relative}")
        else:
            print(f"would remove {relative}")
    if not args.apply:
        print("clean: dry run — pass --apply to remove", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
