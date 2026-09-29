"""Content hashes.

Two different things are hashed and they answer different questions:

* a **quest content hash** answers "is the quest this attempt was started against still the
  same quest?", so it covers the front matter and body that define the work;
* an **evidence hash** answers "has the evidence changed since it was reviewed?", so it
  covers file names and contents across an evidence directory.

Both are stable across machines and runs: sorted traversal, normalized line endings, no
timestamps, no absolute paths.

Round 15 (E4/S1): "stable across machines" was not true for evidence content or names. Git's
own CRLF/LF conversion between a Windows participant and a Linux or macOS reviewer changed
the bytes of every text file the moment either side checked it out, and NFC/NFD differences
in a file name (produced by, among others, macOS) hashed the same logical name two different
ways. A file is now hashed by its normalized text when it looks like text — no NUL byte in
it, checked in full rather than guessed from a prefix — and a name is NFC-normalized before
it is hashed. A package hashed before this change reads as changed once; ADR-031 says what a
reviewer does about that.

Round 16 (E10): "looks like text" was "holds no NUL byte anywhere", which folded every `\r`
byte to `\n` even in content that was never text at all. A NUL-free UTF-16 file with no ASCII
in it (a CJK-only document, encoded the way Windows commonly writes one) is exactly such a
case: one of a character's two bytes can itself be `\r`, and folding it changed the character
without moving the hash — the edit that mattered was invisible to it. Text now also has to
decode as UTF-8, not merely have no NUL byte in it; see `_text_shape`.

Round 17 A-E14: that stopped folding cp1252/Latin-1 text, which Git converts all the same.
Content that is not UTF-8 is now folded exactly when Git's own `core.autocrlf` would convert
it — no NUL, no lone `\r`, Git's printable ratio — and only its `\r\n` pairs. Round 17 A-E15:
a directory symbolic link inside the package is hashed by its link text, as a file link is.
"""

from __future__ import annotations

import codecs
import errno
import hashlib
import json
import os
import stat
import unicodedata
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

    Round 15 E4: text content is hashed with every `\\r\\n` and lone `\\r` folded to `\\n`
    first, the way `normalize_text` already does for a quest's body, so a checkout's line
    endings are not a change. Round 16 E10: a file counts as text when it holds no NUL byte
    *and* decodes as UTF-8, which is read in full to decide (round 12 E8 is why that read is
    still streamed rather than buffered) — a screenshot, a zip, a UTF-16/32 export, or any
    other binary or non-UTF-8 format fails one of those checks within its first few bytes in
    practice, so this rarely costs such a file more than the one pass it always took.
    Round 17 A-E14: content that is not UTF-8 is also text when Git itself would convert its
    line endings (no NUL, no lone `\\r`, Git's printable ratio); see `_text_shape`.
    Normalizing changes a file's byte length, so the length prefix cannot come from `fstat`
    for a text file the way it does for a binary one; it is computed in the same pass that
    checks it, before anything is fed to `hasher`.
    """
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    try:
        with os.fdopen(os.open(path, flags), "rb") as stream:
            status = os.fstat(stream.fileno())
            if not stat.S_ISREG(status.st_mode):
                raise OSError(errno.EINVAL, "not an ordinary file")
            size = status.st_size
            is_text, normalized_size = _text_shape(stream, size)
            stream.seek(0)
            if is_text:
                hasher.update(str(normalized_size).encode("ascii"))
                hasher.update(b"\0")
                _feed_normalized(hasher, stream, size)
            else:
                hasher.update(str(size).encode("ascii"))
                hasher.update(b"\0")
                _feed_raw(hasher, stream, size)
    except OSError as exc:
        if isinstance(exc, UnreadableFileError):
            raise
        # `path` is absolute here; `hash_directory` relabels it relative to the root it is
        # hashing before this ever reaches a caller (round 13 E8).
        raise UnreadableFileError(str(path), exc) from exc


def _feed_raw(hasher: Any, stream: Any, size: int) -> None:
    """Hash `stream`'s first `size` bytes exactly as they are, a chunk at a time."""
    remaining = size
    while remaining:
        block = stream.read(min(HASH_CHUNK_BYTES, remaining))
        if not block:
            raise OSError(errno.EIO, "the file changed while it was being hashed")
        hasher.update(block)
        remaining -= len(block)


# Round 17 A-E14: the bytes Git's own text heuristic (`gather_stats` in Git's `convert.c`)
# counts as non-printable: control bytes other than backspace, tab, form feed and escape
# (`\n` and `\r` are counted separately), and DEL.
_NONPRINTABLE = tuple(
    bytes([byte]) for byte in (*range(1, 32), 127) if byte not in (8, 9, 10, 12, 13, 27)
)


def _text_shape(stream: Any, size: int) -> tuple[bool, int]:
    """Whether `stream`'s first `size` bytes are text to fold line endings in, and their
    length once every `\\r\\n` pair collapses to one `\\n` (a lone `\\r` keeps the byte
    count the same).

    Content is text when it holds no NUL byte and either

    * decodes as UTF-8 (strict), in which case every `\\r\\n` and lone `\\r` folds to
      `\\n` exactly as before; or
    * does not decode as UTF-8 but is what Git itself converts: no lone `\\r`, and Git's
      printable-to-non-printable ratio says text (round 17 A-E14). Such content has only
      `\\r\\n` pairs to fold, so the one folding pass serves both cases.

    Round 16 E10: "text" used to mean only "holds no NUL byte anywhere", which folds every
    `\\r` byte to `\\n` even in content that is not text at all. A NUL-free UTF-16 file with
    no ASCII in it (a CJK-only document, encoded the way Windows commonly writes one) is
    exactly such a case: one of a character's own two bytes can be `\\r` without being a line
    ending, and folding it changed 不 into 上 without moving the hash. Round 16 answered that
    by folding only UTF-8.

    Round 17 A-E14: that also stopped folding every other 8-bit text encoding, while Git's
    `core.autocrlf` converts a cp1252 or Latin-1 file exactly as it converts a UTF-8 one — so
    a Windows participant's `caf\\xe9\\r\\n` log read as "changed since approval" on a Linux
    reviewer's `caf\\xe9\\n` checkout. Git's rule (`convert_is_binary`, applied to the whole
    file) is: a NUL byte, a lone `\\r`, or more than one non-printable byte per 128 printable
    ones means binary, and binary is never converted; otherwise only `\\r\\n` pairs change,
    never a lone `\\r`. Folding exactly that transformation, under exactly that condition,
    is what makes the hash invariant under Git's conversion and nothing more. It keeps round
    16's case apart: 不's UTF-16 bytes `0D 4E` hold a lone `\\r`, which Git treats as binary
    and which is therefore hashed as it sits. A UTF-16 file whose bytes happen to form
    `0D 0A` across two code units, and nowhere form a lone `\\r`, is folded — but that is the
    very file Git would rewrite on commit, so hashing the two forms alike is what keeps the
    Windows working copy and the committed file in agreement, not a collision the hash invents.

    A NUL byte ends the read the moment it is seen, and so does a lone `\\r` once the content
    is known not to be UTF-8: content that will not be normalized needs no transformed
    length, and the caller re-reads it raw from the start. A `\\r` at the very end of a chunk
    is not decided yet — the next chunk might open with the `\\n` that makes it a pair — so
    it is carried into the count made from that chunk instead of this one.
    """
    decoder = codecs.getincrementaldecoder("utf-8")()
    is_utf8 = True
    consumed = 0
    crlf_pairs = 0
    carriage_returns = 0
    line_feeds = 0
    nonprintable = 0
    trailing_cr = False
    last_byte = b""
    while consumed < size:
        block = stream.read(min(HASH_CHUNK_BYTES, size - consumed))
        if not block:
            raise OSError(errno.EIO, "the file changed while it was being hashed")
        consumed += len(block)
        if b"\0" in block:
            return False, 0
        if is_utf8:
            try:
                decoder.decode(block)
            except UnicodeDecodeError:
                is_utf8 = False
        if trailing_cr and block[:1] == b"\n":
            crlf_pairs += 1
        crlf_pairs += block.count(b"\r\n")
        carriage_returns += block.count(b"\r")
        line_feeds += block.count(b"\n")
        nonprintable += sum(block.count(byte) for byte in _NONPRINTABLE)
        trailing_cr = block[-1:] == b"\r"
        last_byte = block[-1:]
        lone_crs = carriage_returns - crlf_pairs - (1 if trailing_cr else 0)
        if not is_utf8 and lone_crs:
            return False, 0
    if is_utf8:
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            is_utf8 = False
    if is_utf8:
        return True, size - crlf_pairs
    if carriage_returns != crlf_pairs:
        # A lone `\r` at end of file: Git calls that binary too.
        return False, 0
    if last_byte == b"\x1a":
        # Git does not count a trailing DOS end-of-file marker as non-printable.
        nonprintable -= 1
    # Git counts a pair's `\n` with its `\r`, and neither as printable.
    printable = size - carriage_returns - line_feeds - nonprintable
    if (printable >> 7) < nonprintable:
        return False, 0
    return True, size - crlf_pairs


def _feed_normalized(hasher: Any, stream: Any, size: int) -> None:
    """Hash `stream`'s first `size` bytes with every `\\r\\n` and lone `\\r` folded to `\\n`.

    A chunk ending in a bare `\\r` holds it back rather than resolving it immediately: the
    byte after it, in the next chunk, decides whether it was half of a pair or a lone `\\r`
    on its own, and `_text_shape` already counted it the same way.
    """
    consumed = 0
    pending = b""
    while consumed < size:
        block = stream.read(min(HASH_CHUNK_BYTES, size - consumed))
        if not block:
            raise OSError(errno.EIO, "the file changed while it was being hashed")
        consumed += len(block)
        block = pending + block
        if block.endswith(b"\r") and consumed < size:
            pending = b"\r"
            block = block[:-1]
        else:
            pending = b""
        hasher.update(block.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    if pending:
        # A lone `\r` at end of file, never followed by anything: it is not part of a pair.
        hasher.update(b"\n")


def normalize_text(text: str) -> str:
    """Line endings unified and trailing whitespace removed, so a checkout style is not a change."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip() + "\n"


def hash_bytes(data: bytes) -> str:
    return _digest([data])


def hash_file(path: Path) -> str:
    """`hash_bytes(path.read_bytes())`, streamed, so the file is never held in memory.

    Text content is normalized first (round 15 E4): see `_update_with_file`.
    """
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


def _encode_name(name: str) -> bytes:
    """A path or link-text component, hashed losslessly and the same way on every machine.

    Round 15 E3: `os.walk` hands back a name straight from the filesystem, surrogate-escaped
    by Python when a byte in it is not valid UTF-8 in the current locale — an unzip of a
    Windows archive is one ordinary way to get one. Encoding it back with the strict default
    raised `UnicodeEncodeError` deep inside the hash, which stopped `build` and
    `record-review` with a traceback carrying an absolute path, while `validate` had nothing
    to say about it. `errors="surrogateescape"` round-trips exactly the bytes `os.walk`
    round-tripped in, so the digest is defined and stable for a name like this instead of
    failing to exist at all.

    Round 15 S1: the same string can be built from precomposed or decomposed Unicode code
    points for what a person reads as identical text (NFC vs. NFD — macOS commonly produces
    the latter), so a participant's and a reviewer's checkouts named the same file two
    different ways and hashed it two different ways. NFC-normalizing first makes the two
    agree.
    """
    return unicodedata.normalize("NFC", name).encode("utf-8", errors="surrogateescape")


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
    # `rglob` walks with `os.scandir` underneath and quietly drops a directory it cannot
    # list — it neither raises nor yields anything for what is behind it — so a directory
    # `chmod 000`'d after being populated used to vanish from the hash instead of failing it
    # (round 14 E5). `os.walk(onerror=...)` is used instead so that failure is caught rather
    # than swallowed; the first one found (by name, for a stable error across runs) is what
    # is raised, in the same `UnreadableFileError` shape as an unreadable file already gets.
    walk_errors: list[OSError] = []
    entries: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, onerror=walk_errors.append):
        current = Path(dirpath)
        if current == root:
            # A `skip_names` directory is never part of the hash (round 13 E6), so it must
            # not be able to fail one either: pruned here, `os.walk` never descends into it
            # and an unreadable one raises nothing.
            dirnames[:] = [name for name in dirnames if name not in skip_names]
        for name in (*dirnames, *filenames):
            entries.append(current / name)
    if walk_errors:
        failing = min(walk_errors, key=lambda exc: exc.filename or "")
        raise UnreadableFileError(
            _relative_to_root(Path(failing.filename), resolved_root) if failing.filename else ".",
            failing,
        ) from failing
    entries.sort(key=lambda p: p.relative_to(root).as_posix())
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
        chunks.append(_encode_name(relative))
        if not resolves_inside(path, resolved_root):
            link = path.readlink() if path.is_symlink() else Path("?")
            chunks.append(b"symlink-outside:" + _encode_name(str(link)))
        elif path.is_file():
            if path.is_symlink():
                chunks.append(b"symlink:" + _encode_name(str(path.readlink())))
            chunks.append(path)
        else:
            if path.is_symlink():
                # Round 17 A-E15: a directory link inside the package is not descended (the walk
                # does not follow links), so what it shows is already hashed under its target's
                # own name — but *which* directory it shows was not hashed at all, and
                # retargeting `logs -> a/` to `logs -> b/` left the digest unchanged. Its link
                # text is hashed, the same as a file link's.
                chunks.append(b"symlink:" + _encode_name(str(path.readlink())))
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
