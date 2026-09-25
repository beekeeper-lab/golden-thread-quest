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

Writing into `participant/` has the matching rule, and lives here for the same reason. Round
12 found that the activity line was appended through a symlink to wherever it led, blocked
forever on a FIFO named `ACTIVITY.md` while both locks were held, and that validation results
were written into a `validation/` directory that was itself a link out of the tree. Every
write below `participant/` now goes through `atomic_write` or `append_to_regular_file`, which
walk from the participant root one component at a time with `O_NOFOLLOW`, refuse any
component that is a link or not a directory, refuse a target that exists and is not a regular
file, and never open anything in a way that can block. Walking by directory descriptor rather
than re-checking a path string means a directory swapped for a link between the check and the
write is refused too.
"""

from __future__ import annotations

import contextlib
import errno
import os
import secrets
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# Far above any file this application writes (a few hundred fields), and far below the sizes
# that made reading one hang or exhaust memory. Matches tools/secret_scan.py's MAX_BYTES, the
# repository's other ceiling for "how big can a file we did not author be".
MAX_STATE_BYTES = 2_000_000

# A validation result is larger than a state file can be. The runner keeps at most 1 MiB of a
# validator's output (`validator_runner.STREAM_LIMIT`), and `json.dumps` escapes a non-ASCII
# character as `\uXXXX`, up to six bytes for each byte captured. Eight megabytes holds the
# largest result the runner can produce with room to spare; anything bigger was not written
# by it. `evidence.store_result` refuses to write a result over this, so the loader never
# meets one it wrote itself.
MAX_VALIDATION_RESULT_BYTES = 8_000_000

# The largest evidence file the secret scan reads. A 135 MB log made every build take about a
# minute, holding the locks, because the scan ran its patterns over all of it. The patterns
# cover about 4 MB a second, so this keeps one file under half a second. A bigger text file is
# a scan finding, which blocks submission and says why, because a file the scan did not read
# is a file it cannot vouch for. Matches the two ceilings above.
MAX_EVIDENCE_FILE_BYTES = 2_000_000

# Chunk size for streaming a file through a hash, so no file is ever held whole in memory.
HASH_CHUNK_BYTES = 1024 * 1024


class UnsafeStateFileError(RuntimeError):
    """A path that is not a small, ordinary file where one was expected.

    Raised for a FIFO, a device, a directory, or anything else `Path.is_file()` refuses —
    before a single byte is read — and for an ordinary file over `max_bytes`, checked by
    `stat` before the read that would have paid for it.
    """


class UnsafeWriteTargetError(RuntimeError):
    """A write inside `participant/` that would have gone through a link or special file.

    The message names the path relative to the participant root and never an absolute one,
    so it is safe to show in a browser or a terminal.
    """


def read_bounded_bytes(
    path: Path, *, max_bytes: int = MAX_STATE_BYTES, follow_symlinks: bool = True
) -> bytes:
    """The bytes of `path`, or `UnsafeStateFileError` if it is not a small, ordinary file.

    `Path.is_file()` follows a symlink and asks about the target, so a symlink to a character
    device such as `/dev/zero` or to a FIFO fails here, before anything is opened. The file is
    then opened with `O_NONBLOCK`, so a path swapped for a FIFO after that check cannot hang
    the open, and the descriptor is checked again with `fstat`: what is read is what was
    checked. The size check also runs before the read, and at most `max_bytes + 1` bytes are
    read, so a file that grows after the check is refused rather than read whole.

    `follow_symlinks=False` refuses a symlink outright, for files this application writes
    itself and therefore never writes as links.
    """
    if not follow_symlinks and path.is_symlink():
        raise UnsafeStateFileError(f"{path.name} is a symbolic link.")
    if not path.is_file():
        raise UnsafeStateFileError(f"{path.name} is not an ordinary file.")
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    if not follow_symlinks:
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise UnsafeStateFileError(f"{path.name} is a symbolic link.") from exc
        raise
    with os.fdopen(descriptor, "rb") as stream:
        status = os.fstat(stream.fileno())
        if not stat.S_ISREG(status.st_mode):
            raise UnsafeStateFileError(f"{path.name} is not an ordinary file.")
        if status.st_size > max_bytes:
            raise UnsafeStateFileError(
                f"{path.name} is {status.st_size} bytes, over the {max_bytes} byte limit."
            )
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise UnsafeStateFileError(f"{path.name} is over the {max_bytes} byte limit.")
    return data


def read_bounded_text(
    path: Path,
    *,
    max_bytes: int = MAX_STATE_BYTES,
    encoding: str = "utf-8-sig",
    follow_symlinks: bool = True,
) -> str:
    """`read_bounded_bytes`, decoded. Raises `UnsafeStateFileError` or `UnicodeDecodeError`."""
    return read_bounded_bytes(path, max_bytes=max_bytes, follow_symlinks=follow_symlinks).decode(
        encoding
    )


def _label(root: Path, path: Path) -> str:
    try:
        return "participant/" + path.relative_to(root).as_posix()
    except ValueError:
        return path.name


@contextmanager
def _participant_directory(root: Path, directory: Path, *, create: bool) -> Iterator[int]:
    """A descriptor for `directory`, reached from `root` without following a single link.

    `root` itself is trusted: it is the configured participant root, and a participant may
    keep it anywhere. Every component below it must be a real directory. With `create`, a
    missing component is made, and then opened like any other, so a component created by
    someone else in the meantime is still checked.
    """
    try:
        relative = directory.relative_to(root)
    except ValueError as exc:
        raise UnsafeWriteTargetError(
            f"{directory.name} is not inside the participant directory."
        ) from exc
    if create:
        root.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(root, flags)
    try:
        walked = root
        for part in relative.parts:
            walked = walked / part
            if create:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(part, mode=0o777, dir_fd=descriptor)
            try:
                child = os.open(part, flags | os.O_NOFOLLOW, dir_fd=descriptor)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise UnsafeWriteTargetError(
                        f"{_label(root, walked)} is a link or not a directory, so nothing is "
                        "written through it. Replace it with an ordinary directory."
                    ) from exc
                raise
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


def ensure_directory(root: Path, directory: Path) -> None:
    """Create `directory` and every missing parent below `root`, refusing a link on the way."""
    with _participant_directory(root, directory, create=True):
        pass


def open_lock_file(path: Path) -> int:
    """A descriptor for a lock file directly in a trusted directory, never through a link.

    `O_NOFOLLOW` keeps `O_CREAT` from creating the lock wherever a planted link points, and
    `O_NONBLOCK` keeps a FIFO from hanging the open; the `fstat` refuses anything that is
    not a regular file. Raises `OSError` either way, which the lock's caller already treats
    as "run unlocked" (ADR-036).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags, 0o600)
    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise OSError(errno.EINVAL, "the lock file is not an ordinary file")
    return descriptor


def _refuse_unless_regular(root: Path, path: Path, directory: int) -> None:
    """Refuse an existing `path` that is anything but a regular file. Absent is fine."""
    try:
        status = os.lstat(path.name, dir_fd=directory)
    except FileNotFoundError:
        return
    if not stat.S_ISREG(status.st_mode):
        raise UnsafeWriteTargetError(
            f"{_label(root, path)} is a link or special file, not an ordinary file, so it was "
            "not written. Replace it with an ordinary file, or remove it."
        )


def atomic_write(root: Path, path: Path, data: bytes) -> None:
    """Replace `path` with `data`, or leave it exactly as it was; never through a link.

    `path` is the lexical location under `root` — not one with links resolved, which would
    hide the very link this refuses. The temporary file is created in the same directory with
    `O_EXCL | O_NOFOLLOW`, so the final rename is a same-filesystem rename and atomic, and it
    is fsynced before the rename, so a crash cannot leave the rename durable and the contents
    not. `os.replace` on a name replaces that name, never what a link at it points to, but a
    link or special file at the target is refused anyway rather than silently replaced: it is
    not something this application put there.
    """
    with _participant_directory(root, path.parent, create=True) as directory:
        _refuse_unless_regular(root, path, directory)
        temporary = f".{path.name}.{secrets.token_hex(6)}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=directory)
            raise


def append_to_regular_file(root: Path, path: Path, data: bytes) -> None:
    """Append `data` to an existing regular file at `path`, never through a link.

    Opened with `O_NOFOLLOW | O_NONBLOCK`: a link is refused by the open itself, and a FIFO
    either refuses the open (no reader) or opens without waiting, and is then refused by the
    `fstat` that follows. Nothing here can block. Raises `FileNotFoundError` when there is no
    file yet, so the caller decides what a new one starts with.
    """
    with _participant_directory(root, path.parent, create=False) as directory:
        flags = (
            os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
        )
        try:
            descriptor = os.open(path.name, flags, dir_fd=directory)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENXIO, errno.EISDIR):
                raise UnsafeWriteTargetError(
                    f"{_label(root, path)} is a link or special file, not an ordinary file, "
                    "so nothing was appended to it."
                ) from exc
            raise
        with os.fdopen(descriptor, "wb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise UnsafeWriteTargetError(
                    f"{_label(root, path)} is a special file, not an ordinary file, so nothing "
                    "was appended to it."
                )
            stream.write(data)
