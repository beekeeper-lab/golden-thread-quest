"""Content hashes.

Two different things are hashed and they answer different questions:

* a **quest content hash** answers "is the quest this attempt was started against still the
  same quest?", so it covers the front matter and body that define the work;
* an **evidence hash** answers "has the evidence changed since it was reviewed?", so it
  covers file names and contents across an evidence directory.

Both are stable across machines and runs: sorted traversal, normalized line endings, no
timestamps, no absolute paths.
"""

from __future__ import annotations

import hashlib
import json
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

PREFIX = "sha256:"


def _digest(chunks: list[bytes]) -> str:
    hasher = hashlib.sha256()
    for chunk in chunks:
        # Length-prefix each chunk so that concatenation cannot be ambiguous: without it,
        # ("ab", "c") and ("a", "bc") would hash identically.
        hasher.update(str(len(chunk)).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(chunk)
    return PREFIX + hasher.hexdigest()


def normalize_text(text: str) -> str:
    """Line endings unified and trailing whitespace removed, so a checkout style is not a change."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def hash_bytes(data: bytes) -> str:
    return _digest([data])


def hash_text(text: str) -> str:
    return _digest([normalize_text(text).encode("utf-8")])


def hash_mapping(data: Any) -> str:
    """Hash structured data by its canonical JSON form, so key order never matters."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return _digest([canonical.encode("utf-8")])


def hash_quest(front_matter: dict[str, Any], body: str) -> str:
    """The identity of a quest's evaluable definition."""
    canonical = json.dumps(front_matter, sort_keys=True, separators=(",", ":"), default=str)
    return _digest([canonical.encode("utf-8"), normalize_text(body).encode("utf-8")])


def hash_directory(
    root: Path,
    *,
    skip_names: frozenset[str] = frozenset(),
    skip_globs: tuple[str, ...] = (),
) -> str:
    """The identity of a directory tree: sorted relative names plus file contents.

    A symbolic link that resolves inside the tree is hashed by what it points at, because
    that is what the build renders and the secret scan reads: hashing only the link text let
    a participant change the rendered proof after approval without changing the hash. A link
    that resolves outside the tree is hashed by its link text alone, so unrelated content is
    never pulled into the digest; the evidence loader reports such a link and nothing
    renders through it.
    """
    chunks: list[bytes] = []
    resolved_root = root.resolve()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if any(part in skip_names for part in parts):
            continue
        if any(fnmatch(parts[-1], pattern) for pattern in skip_globs):
            continue
        chunks.append(relative.encode("utf-8"))
        if not resolves_inside(path, resolved_root):
            link = path.readlink() if path.is_symlink() else Path("?")
            chunks.append(b"symlink-outside:" + str(link).encode("utf-8"))
        elif path.is_file():
            if path.is_symlink():
                chunks.append(b"symlink:" + str(path.readlink()).encode("utf-8"))
            chunks.append(path.read_bytes())
        else:
            chunks.append(b"dir")
    return _digest(chunks)


def resolves_inside(path: Path, root: Path) -> bool:
    """Whether `path`, with every symbolic link followed, is `root` or lies under it.

    `root` must already be resolved. A path that cannot be resolved (a link loop) is
    treated as outside, because nothing can vouch for where it leads.
    """
    try:
        target = path.resolve(strict=False)
    except (OSError, RuntimeError):
        return False
    return target == root or root in target.parents
