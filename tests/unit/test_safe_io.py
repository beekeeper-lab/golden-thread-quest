"""Direct unit tests for `safe_io`'s own guards, independent of any caller.

Round 14 T1: `unlink_regular_file`'s special-file refusal (the `stat.S_ISREG` check) had no
test of its own anywhere in the suite. Disabling it (`if False: raise ...`) passed the whole
suite unchanged — every existing test that exercises stale-port-file pruning plants its link
one directory level up (the `service-ports` directory itself), which a different guard
(`_participant_directory`'s `O_NOFOLLOW` on that directory component) already catches. Nothing
plants a FIFO, a directory or a symlink at the entry name itself to exercise this function's
own check.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest
from quest_app.safe_io import LOCAL_DATA, UnsafeWriteTargetError, unlink_regular_file


def _local_data(tmp_path: Path) -> Path:
    root = tmp_path / "local-data"
    (root / "service-ports").mkdir(parents=True)
    return root


def _plant(target: Path, kind: str, elsewhere: Path) -> None:
    if kind == "fifo":
        os.mkfifo(target)
    elif kind == "directory":
        target.mkdir()
    elif kind == "symlink":
        target.symlink_to(elsewhere)
    else:  # pragma: no cover - parametrize typo guard
        raise ValueError(kind)


@pytest.mark.parametrize("kind", ["fifo", "directory", "symlink"])
def test_a_special_file_at_the_entry_name_is_left_in_place(tmp_path: Path, kind: str) -> None:
    root = _local_data(tmp_path)
    target = root / "service-ports" / "8799"
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("not this application's business\n")
    _plant(target, kind, elsewhere)

    with pytest.raises(UnsafeWriteTargetError, match="link or special file"):
        unlink_regular_file(root, target, prefix=LOCAL_DATA)

    status = os.lstat(target)
    if kind == "fifo":
        assert stat.S_ISFIFO(status.st_mode)
    elif kind == "directory":
        assert stat.S_ISDIR(status.st_mode)
    else:
        assert stat.S_ISLNK(status.st_mode)
        assert target.readlink() == elsewhere
    assert elsewhere.read_text() == "not this application's business\n"


def test_an_ordinary_file_at_the_entry_name_is_removed(tmp_path: Path) -> None:
    root = _local_data(tmp_path)
    target = root / "service-ports" / "8799"
    target.write_text("8799\n")

    unlink_regular_file(root, target, prefix=LOCAL_DATA)

    assert not target.exists()


def test_an_absent_entry_is_not_an_error(tmp_path: Path) -> None:
    root = _local_data(tmp_path)
    target = root / "service-ports" / "8799"

    unlink_regular_file(root, target, prefix=LOCAL_DATA)  # does not raise


def test_atomic_write_fsyncs_the_directory_after_the_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Round 17 E9: without a directory fsync a power loss can undo the rename."""
    from quest_app import safe_io

    synced: list[bool] = []
    real_fsync = os.fsync

    def recording_fsync(fd: int) -> None:
        synced.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        real_fsync(fd)

    monkeypatch.setattr(safe_io.os, "fsync", recording_fsync)
    safe_io.atomic_write(tmp_path, tmp_path / "state.yaml", b"new\n")
    assert (tmp_path / "state.yaml").read_bytes() == b"new\n"
    assert synced == [False, True], "the file, then its directory"
