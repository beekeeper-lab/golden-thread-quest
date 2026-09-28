"""Round 15 E3/E4/S1: a hash must be defined and stable across machines, not just across runs.

`quest_app.hashing` claims both in its own module docstring. These tests hold it to that for
the two ways "the same machine" turned out not to be true: a file name that is not valid
UTF-8 used to crash the hash outright, and ordinary cross-platform Git behavior (CRLF/LF
conversion, NFC/NFD file names) changed the bytes or the name of evidence that a participant
never touched.
"""

from __future__ import annotations

import os
from pathlib import Path

from quest_app.hashing import hash_directory, hash_file


def test_a_non_utf8_file_name_does_not_crash_the_hash(tmp_path: Path) -> None:
    """Round 15 E3.

    `os.walk` hands back a name straight from the filesystem; Python surrogate-escapes a byte
    that is not valid UTF-8 in the current locale, which an unzip of a Windows archive
    produces routinely. Encoding such a name with the strict default raised
    `UnicodeEncodeError` deep inside `hash_directory`, which stopped `build` and
    `record-review` with a traceback carrying an absolute path.
    """
    bad_name = os.fsdecode(b"r\xe9sum\xe9.txt")
    (tmp_path / bad_name).write_bytes(b"whatever this file holds\n")

    digest = hash_directory(tmp_path)  # must not raise

    assert digest.startswith("sha256:")
    assert hash_directory(tmp_path) == digest, "the digest must be stable across runs too"


def test_crlf_and_lf_hash_the_same(tmp_path: Path) -> None:
    """Round 15 E4.

    Git's own CRLF/LF conversion between a Windows participant and a Linux or macOS reviewer
    changes the bytes of every text file the moment either side checks it out. Hashing raw
    bytes made every such submission read as "changed since submitted".
    """
    crlf = tmp_path / "crlf.txt"
    lf = tmp_path / "lf.txt"
    crlf.write_bytes(b"line one\r\nline two\r\n")
    lf.write_bytes(b"line one\nline two\n")

    assert hash_file(crlf) == hash_file(lf)


def test_a_lone_cr_hashes_as_lf_too(tmp_path: Path) -> None:
    """Old Mac-style line endings fold to the same normal form as CRLF and LF."""
    cr = tmp_path / "cr.txt"
    lf = tmp_path / "lf.txt"
    cr.write_bytes(b"line one\rline two\r")
    lf.write_bytes(b"line one\nline two\n")

    assert hash_file(cr) == hash_file(lf)


def test_a_crlf_pair_split_across_a_read_boundary_still_normalizes(tmp_path: Path) -> None:
    """A `\\r` at the very end of a chunk must not be resolved before the next chunk's first
    byte is known to be `\\n` or something else."""
    from quest_app.safe_io import HASH_CHUNK_BYTES

    padded = tmp_path / "padded.txt"
    plain = tmp_path / "plain.txt"
    filler = b"a" * (HASH_CHUNK_BYTES - 1)
    padded.write_bytes(filler + b"\r\nend")
    plain.write_bytes(filler + b"\nend")

    assert hash_file(padded) == hash_file(plain)


def test_binary_content_is_not_normalized(tmp_path: Path) -> None:
    """A NUL byte anywhere marks content as binary, so a real CRLF/LF byte difference inside
    it is not collapsed away — collapsing it would make two different files hash the same."""
    with_cr = tmp_path / "with_cr.bin"
    without_cr = tmp_path / "without_cr.bin"
    with_cr.write_bytes(b"\x00\x01binary\r\ndata")
    without_cr.write_bytes(b"\x00\x01binary\ndata")

    assert hash_file(with_cr) != hash_file(without_cr)


def test_a_real_content_change_still_differs(tmp_path: Path) -> None:
    """Normalization must not swallow an actual edit."""
    original = tmp_path / "a.txt"
    changed = tmp_path / "b.txt"
    original.write_bytes(b"the result was pass\r\n")
    changed.write_bytes(b"the result was fail\r\n")

    assert hash_file(original) != hash_file(changed)


def test_nfc_and_nfd_file_names_hash_the_same(tmp_path: Path) -> None:
    """Round 15 S1: the same logical name, built from precomposed (NFC) or decomposed (NFD)
    Unicode code points, as macOS commonly produces. A participant's and a reviewer's
    checkouts named the same file two different ways and hashed it two different ways."""
    import unicodedata

    nfc_dir = tmp_path / "nfc"
    nfd_dir = tmp_path / "nfd"
    nfc_dir.mkdir()
    nfd_dir.mkdir()
    nfc_name = unicodedata.normalize("NFC", "café.md")
    nfd_name = unicodedata.normalize("NFD", "café.md")
    assert nfc_name != nfd_name, (
        "the two byte forms must actually differ for this test to mean anything"
    )
    (nfc_dir / nfc_name).write_text("same content")
    (nfd_dir / nfd_name).write_text("same content")

    assert hash_directory(nfc_dir) == hash_directory(nfd_dir)


def test_a_genuinely_different_name_still_differs(tmp_path: Path) -> None:
    """NFC-normalizing names must not make two different names collide."""
    one = tmp_path / "one"
    two = tmp_path / "two"
    one.mkdir()
    two.mkdir()
    (one / "a.md").write_text("x")
    (two / "b.md").write_text("x")

    assert hash_directory(one) != hash_directory(two)
