"""A hand-in pull request may change participant work and nothing else."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from review_check import check_files


def _file(name: str, status: str = "added", previous: str = "") -> dict[str, str]:
    record: dict[str, str] = {"filename": name, "status": status}
    if previous:
        record["previous_filename"] = previous
    return record


def test_evidence_only_is_safe() -> None:
    verdict = check_files(
        [_file("participant/progress.yaml", "modified"), _file("participant/evidence/x/PROOF.md")]
    )
    assert verdict.safe
    assert verdict.total == 2


@pytest.mark.parametrize(
    "path",
    [
        "quest_app/actions.py",
        "content/quests/base-camp/x.md",
        "install.sh",
        ".github/workflows/ci.yml",
        "participantx/file.md",
        "participant/../quest_app/cli.py",
        "/participant/file.md",
        "participant/.github/workflows/x.yml",
        "participant/.git/config",
        "participant\\evidence",
    ],
)
def test_anything_outside_participant_is_not_safe(path: str) -> None:
    assert check_files([_file("participant/ok.md"), _file(path)]).outside == [path]


def test_moving_a_file_out_of_the_app_counts() -> None:
    verdict = check_files([_file("participant/x.md", "renamed", previous="quest_app/cli.py")])
    assert verdict.outside == ["quest_app/cli.py"]


def test_participant_code_is_listed_not_failed() -> None:
    verdict = check_files([_file("participant/skills/a/sync.py"), _file("participant/notes.md")])
    assert verdict.safe
    assert verdict.code == ["participant/skills/a/sync.py"]


def test_deletions_inside_participant_are_listed() -> None:
    assert check_files([_file("participant/old.md", "removed")]).removed == ["participant/old.md"]
