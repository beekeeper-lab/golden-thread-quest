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

import errno
import hashlib
import json
import os
import stat
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from quest_app.safe_io import HASH_CHUNK_BYTES

PREFIX = "sha256:"


class UnreadableFileError(OSError):
    """A file could not be read while hashing it: permission denied, or it changed mid-read.

    Carries a path relative to the tree being hashed, never an absolute one (round 13 E8):
    an unhandled `OSError` from deep inside a hash used to reach a participant or reviewer
    as a traceback with the local filesystem layout in it. A subclass of `OSError` so any
    caller that already catches that keeps working unchanged.
    """

    def __init__(self, relative_path: str, cause: BaseException | None = None) -> None:
        reason = getattr(cause, "strerror", None) or (str(cause) if cause else "could not be read")
        errno_value = getattr(cause, "errno", None)
        if errno_value is not None:
            super().__init__(errno_value, reason)
        else:
            super().__init__(reason)
        self.relative_path = relative_path


def _digest(chunks: list[bytes | Path]) -> str:
    """SHA-256 over length-prefixed chunks. A `Path` chunk is a file, streamed.

    Length-prefix each chunk so that concatenation cannot be ambiguous: without it,
    ("ab", "c") and ("a", "bc") would hash identically. A file is hashed exactly as its bytes
    would be, so a digest recorded before files were streamed still matches.
    """
    hasher = hashlib.sha256()
    for chunk in chunks:
        if isinstance(chunk, Path):
            _update_with_file(hasher, chunk)
            continue
        hasher.update(str(len(chunk)).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(chunk)
    return PREFIX + hasher.hexdigest()


def _update_with_file(hasher: Any, path: Path) -> None:
    """Feed one file to `hasher` as a length-prefixed chunk, a megabyte at a time.

    `hash_directory` used to hold every file of a package in memory at once, so a large log
    cost its size in memory on every build (round 12 E8). The length prefix comes from
    `fstat` on the open descriptor; a file that shrinks while it is read raises `OSError`
    rather than producing a digest of something that never existed. Opened `O_NONBLOCK` and
    refused unless regular, so nothing swapped in after the caller's check can block.
    """
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        with os.fdopen(os.open(path, flags), "rb") as stream:
            status = os.fstat(stream.fileno())
            if not stat.S_ISREG(status.st_mode):
                raise OSError(errno.EINVAL, "not an ordinary file")
            remaining = status.st_size
            hasher.update(str(remaining).encode("ascii"))
            hasher.update(b"\0")
            while remaining:
                block = stream.read(min(HASH_CHUNK_BYTES, remaining))
                if not block:
                    raise OSError(errno.EIO, "the file changed while it was being hashed")
                hasher.update(block)
                remaining -= len(block)
    except OSError as exc:
        if isinstance(exc, UnreadableFileError):
            raise
        # `path` is absolute here; `hash_directory` relabels it relative to the root it is
        # hashing before this ever reaches a caller (round 13 E8).
        raise UnreadableFileError(str(path), exc) from exc


def normalize_text(text: str) -> str:
    """Line endings unified and trailing whitespace removed, so a checkout style is not a change."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def hash_bytes(data: bytes) -> str:
    return _digest([data])


def hash_file(path: Path) -> str:
    """`hash_bytes(path.read_bytes())`, streamed, so the file is never held in memory."""
    return _digest([path])


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
    chunks: list[bytes | Path] = []
    resolved_root = root.resolve()
    try:
        entries = sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix())
    except OSError as exc:
        raise UnreadableFileError(
            _relative_to_root(Path(exc.filename), resolved_root) if exc.filename else ".", exc
        ) from exc
    for path in entries:
        relative = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
        # Only a *top-level* name is skipped (round 13 E6): `parts[0]` is the first path
        # segment under `root`, so a folder named `validation` skips itself and everything
        # under it, but a folder named `validation` nested somewhere else does not, and a
        # participant's own nested `logs/validation/x.txt` or `some/dir/review.yaml` is
        # ordinary content the hash must see. `skip_names` and the review-record globs in
        # `skip_globs` both name only records the application itself writes at the top of
        # the package (ADR-031); anything with the same name deeper in a participant's own
        # tree is their content, not the application's bookkeeping.
        if parts[0] in skip_names:
            continue
        if len(parts) == 1 and any(fnmatch(parts[-1], pattern) for pattern in skip_globs):
            continue
        chunks.append(relative.encode("utf-8"))
        if not resolves_inside(path, resolved_root):
            link = path.readlink() if path.is_symlink() else Path("?")
            chunks.append(b"symlink-outside:" + str(link).encode("utf-8"))
        elif path.is_file():
            if path.is_symlink():
                chunks.append(b"symlink:" + str(path.readlink()).encode("utf-8"))
            chunks.append(path)
        else:
            chunks.append(b"dir")
    try:
        return _digest(chunks)
    except UnreadableFileError as exc:
        raise UnreadableFileError(
            _relative_to_root(Path(exc.relative_path), resolved_root), exc.__cause__ or exc
        ) from exc


def _relative_to_root(path: Path, resolved_root: Path) -> str:
    """`path` named relative to `resolved_root`, or by its own name if it is not under it.

    Never returns an absolute path: this is what keeps a filesystem layout out of an error
    a participant or reviewer ends up reading (round 13 E8).
    """
    try:
        return path.resolve(strict=False).relative_to(resolved_root).as_posix()
    except ValueError:
        return path.name


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
