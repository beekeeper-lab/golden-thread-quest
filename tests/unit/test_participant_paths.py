"""The shapes a participant-owned path may not take.

`PurePosixCheck` runs before anything touches disk, so what it refuses never reaches a
resolution step at all. The percent-decoding branch had no test of its own: removing it left
the suite green, because every case anyone had written also contained `..`, which the next
check catches. A path that smuggles a separator without one is the case that branch exists
for.
"""

from __future__ import annotations

import pytest
from quest_app.config import PurePosixCheck


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
