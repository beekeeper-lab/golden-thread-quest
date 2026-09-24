"""Reading a file the application did not write, with a bound on what "read" means.

Round 10 gave `content/` discovery a rule for this: only a regular file inside the content
tree is read, because a symlink to `/dev/zero` was read until the process ran out of memory
and a FIFO hung `validate` indefinitely (`content_loader.discover`). Participant state —
`progress.yaml`, `review.yaml`, `submission.yaml` — is read from the same untrusted place, a
participant's own repository that a reviewer checks out and runs this application against,
through call sites `discover()` never touches: a fixed path, opened directly. Those had
neither check, and neither did a size ceiling: an 18 MB `progress.yaml` took `validate` past
two minutes.

This is the one place both checks live, so every reader of an untrusted, fixed-path file uses
it rather than re-deriving the rule.
"""

from __future__ import annotations

from pathlib import Path

# Far above any file this application writes (a few hundred fields), and far below the sizes
# that made reading one hang or exhaust memory. Matches tools/secret_scan.py's MAX_BYTES, the
# repository's other ceiling for "how big can a file we did not author be".
MAX_STATE_BYTES = 2_000_000


class UnsafeStateFileError(RuntimeError):
    """A path that is not a small, ordinary file where one was expected.

    Raised for a FIFO, a device, a directory, or anything else `Path.is_file()` refuses —
    before a single byte is read — and for an ordinary file over `max_bytes`, checked by
    `stat` before the read that would have paid for it.
    """


def read_bounded_bytes(path: Path, *, max_bytes: int = MAX_STATE_BYTES) -> bytes:
    """The bytes of `path`, or `UnsafeStateFileError` if it is not a small, ordinary file.

    `Path.is_file()` follows a symlink and asks about the target, so a symlink to a character
    device such as `/dev/zero` or to a FIFO fails here, before anything is read. A symlink to
    an oversized regular file passes this check and is caught by the size check that follows,
    which also runs before the read: a `stat` never pays for the bytes a bad file would cost.
    """
    if not path.is_file():
        raise UnsafeStateFileError(f"{path.name} is not an ordinary file.")
    size = path.stat().st_size
    if size > max_bytes:
        raise UnsafeStateFileError(f"{path.name} is {size} bytes, over the {max_bytes} byte limit.")
    return path.read_bytes()


def read_bounded_text(
    path: Path, *, max_bytes: int = MAX_STATE_BYTES, encoding: str = "utf-8-sig"
) -> str:
    """`read_bounded_bytes`, decoded. Raises `UnsafeStateFileError` or `UnicodeDecodeError`."""
    return read_bounded_bytes(path, max_bytes=max_bytes).decode(encoding)
