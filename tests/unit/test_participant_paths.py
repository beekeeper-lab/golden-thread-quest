"""The shapes a participant-owned path may not take.

`PurePosixCheck` runs before anything touches disk, so what it refuses never reaches a
resolution step at all. The percent-decoding branch had no test of its own: removing it left
the suite green, because every case anyone had written also contained `..`, which the next
check catches. A path that smuggles a separator without one is the case that branch exists
for.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from quest_app.config import AppConfig, PurePosixCheck


@pytest.mark.parametrize(
    "raw",
    [
        "evidence%2F..%2Fsecret.txt",
        "evidence%2fother-quest%2fPROOF.md",
        "%2Fetc%2Fpasswd",
    ],
)
def test_a_percent_encoded_separator_is_refused(raw: str) -> None:
    with pytest.raises(ValueError, match=r"percent-encoded|parent-directory"):
        PurePosixCheck(raw).checked()


@pytest.mark.parametrize(
    "raw",
    ["evidence/base-camp/attempt-001/PROOF.md", "context/jira/assigned.json", "notes.md"],
)
def test_an_ordinary_participant_path_is_accepted(raw: str) -> None:
    assert PurePosixCheck(raw).checked() == raw


@pytest.mark.parametrize(
    "raw", ["/absolute.md", "", "a\x00b.md", "../outside.md", "evidence/../../outside.md"]
)
def test_the_other_refusals_still_hold(raw: str) -> None:
    with pytest.raises(ValueError):
        PurePosixCheck(raw).checked()


class TestTheResolutionStepItself:
    """`PurePosixCheck` is lexical. A symbolic link is not, and this is the check for it.

    `resolve_participant_path` resolves and then re-checks that the result is still inside
    the participant root. Deleting that re-check left the whole suite green: every path test
    was about the lexical stage, and the equivalent guard in `tools/clean.py` has symlink
    tests of its own while this one had none.
    """

    def _config(self, tmp_path: Path) -> AppConfig:
        participant = tmp_path / "repo" / "participant"
        participant.mkdir(parents=True)
        return AppConfig.for_repo(tmp_path / "repo", participant_root=participant)

    def test_a_link_out_of_the_participant_tree_is_refused(self, tmp_path: Path) -> None:
        config = self._config(tmp_path)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("not the participant's\n")
        (config.participant_root / "escape").symlink_to(outside, target_is_directory=True)

        with pytest.raises(ValueError, match="outside the participant root"):
            config.resolve_participant_path("participant/escape/secret.txt")

    def test_a_link_within_the_participant_tree_is_still_allowed(self, tmp_path: Path) -> None:
        """The check is about leaving the tree, not about links."""
        config = self._config(tmp_path)
        real = config.participant_root / "evidence"
        real.mkdir()
        (real / "PROOF.md").write_text("# Proof\n")
        (config.participant_root / "shortcut").symlink_to(real, target_is_directory=True)

        resolved = config.resolve_participant_path("participant/shortcut/PROOF.md")
        assert resolved == (real / "PROOF.md").resolve()
