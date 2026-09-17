"""Content hashes.

Two different things are hashed and they answer different questions:

* a **quest content hash** answers "is the quest this attempt was started against still the
  same quest?", so it covers the front matter and body that define the work;
* an **evidence hash** answers "has the evidence changed since it was reviewed?", so it
  covers file names and contents across an evidence directory.

Both are stable across machines and runs: sorted traversal, normalised line endings, no
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

    Symbolic links are hashed as their target string rather than followed, so a link that
    points outside the tree cannot silently pull unrelated content into the digest.
    """
    chunks: list[bytes] = []
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        if any(part in skip_names for part in parts):
            continue
        if any(fnmatch(parts[-1], pattern) for pattern in skip_globs):
            continue
        chunks.append(relative.encode("utf-8"))
        if path.is_symlink():
            chunks.append(b"symlink:" + str(path.readlink()).encode("utf-8"))
        elif path.is_file():
            chunks.append(path.read_bytes())
        else:
            chunks.append(b"dir")
    return _digest(chunks)
