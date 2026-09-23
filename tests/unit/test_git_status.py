"""`git_status` reports and advises. It must never act.

The traceability document claimed this was covered by the update tests; it was not — nothing
imported the module at all. C19 states the rule, so here it is as a check.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from quest_app.git_status import READ_ONLY_COMMANDS, _run, inspect, summary_for

MUTATING = {
    "commit",
    "push",
    "pull",
    "merge",
    "rebase",
    "reset",
    "checkout",
    "switch",
    "clean",
    "rm",
    "mv",
    "restore",
    "cherry-pick",
    "revert",
    "stash",
    "gc",
    "prune",
}


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        },
    )


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "tracked.txt").write_text("committed\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "initial")
    return tmp_path


class TestItCannotAct:
    def test_no_permitted_command_can_change_anything(self) -> None:
        for command in READ_ONLY_COMMANDS:
            assert not MUTATING & set(command), command

    @pytest.mark.parametrize(
        "command",
        [
            ("commit", "-m", "x"),
            ("push",),
            ("merge", "main"),
            ("reset", "--hard"),
            ("clean", "-fd"),
        ],
    )
    def test_asking_for_a_mutating_command_raises(
        self, repository: Path, command: tuple[str, ...]
    ) -> None:
        with pytest.raises(ValueError, match="read-only list"):
            _run(repository, command)


class TestWhatItReports:
    def test_a_clean_repository(self, repository: Path) -> None:
        status = inspect(repository)
        assert status.available and status.is_repository
        assert status.branch == "main"
        assert status.clean

    def test_changed_and_untracked_files_are_counted_separately(self, repository: Path) -> None:
        (repository / "tracked.txt").write_text("modified\n")
        (repository / "new.txt").write_text("untracked\n")
        status = inspect(repository)
        assert status.changed == 1
        assert status.untracked == 1
        assert not status.clean

    def test_a_directory_that_is_not_a_repository_is_a_normal_condition(
        self, tmp_path: Path
    ) -> None:
        """The curriculum is readable either way, so this is not an error."""
        status = inspect(tmp_path / "not-a-repo")
        assert not status.available
        assert status.reason

    def test_it_advises_when_evidence_is_uncommitted(self, repository: Path) -> None:
        evidence = repository / "participant" / "evidence" / "q" / "a-001"
        evidence.mkdir(parents=True)
        (evidence / "PROOF.md").write_text("# Proof\n")
        _git(repository, "add", "-A")
        (evidence / "PROOF.md").write_text("# Proof, edited\n")

        summary = summary_for(repository, "participant/evidence/q/a-001")

        assert summary["available"] is True
        assert summary["evidence_committed"] is False
        assert "commit" in str(summary["advice"]).lower()

    def test_it_advises_when_evidence_is_edited_and_never_staged(self, repository: Path) -> None:
        """The commonest case: edit a file, do not `git add`, open the evidence workspace.

        Porcelain writes `" M path"` for it. The parser split on the first space, so the
        status letter stayed on the front of the path, no prefix ever matched, and the page
        printed "yes" under "evidence committed" for evidence that was not committed.
        """
        evidence = repository / "participant" / "evidence" / "q" / "a-001"
        evidence.mkdir(parents=True)
        (evidence / "PROOF.md").write_text("# Proof\n")
        _git(repository, "add", "-A")
        _git(repository, "commit", "-m", "evidence")
        (evidence / "PROOF.md").write_text("# Proof, edited and never staged\n")

        summary = summary_for(repository, "participant/evidence/q/a-001")

        assert summary["evidence_committed"] is False, summary
        assert "commit" in str(summary["advice"]).lower()

    def test_it_says_nothing_about_evidence_when_not_asked(self, repository: Path) -> None:
        assert summary_for(repository, None)["evidence_committed"] is None

    def test_the_summary_carries_no_absolute_path(self, repository: Path) -> None:
        assert str(repository) not in str(summary_for(repository, None))
