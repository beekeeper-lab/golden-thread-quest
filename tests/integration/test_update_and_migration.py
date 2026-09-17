"""Receiving upstream curriculum without losing participant work.

The promise this repository makes is that a participant can take improvements and keep
everything they wrote. These are the tests that hold it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from quest_app.config import AppConfig
from quest_app.migrations import (
    MIGRATIONS,
    Migration,
    MigrationError,
    attempts_on_older_quest_versions,
    migrate,
    plan,
)
from quest_app.update import PERMITTED_COMMANDS, backup_branch_name, preflight, update_instructions


class TestMigrationPlanning:
    def test_current_state_needs_no_migration(self) -> None:
        assert plan(1, 1) == []

    def test_state_from_a_newer_application_is_refused(self) -> None:
        """Downgrading someone's work is worse than refusing to run."""
        with pytest.raises(MigrationError, match="newer version"):
            plan(99, 1)

    def test_a_missing_step_is_refused_rather_than_skipped(self) -> None:
        with pytest.raises(MigrationError, match="No migration is defined"):
            plan(1, 5)

    def test_every_declared_migration_moves_exactly_one_version(self) -> None:
        for migration in MIGRATIONS:
            assert migration.to_version == migration.from_version + 1


class TestMigrationSafety:
    def test_migration_does_not_mutate_the_input(self) -> None:
        original = {"schema_version": 0, "attempts": [{"attempt_id": "a-1"}]}
        snapshot = {"schema_version": 0, "attempts": [{"attempt_id": "a-1"}]}
        migrate(original)
        assert original == snapshot

    def test_a_migration_that_drops_an_attempt_is_refused(self) -> None:
        """A migration is code, and code has bugs. This turns a data-losing bug into a stop."""
        destructive = Migration(
            from_version=0,
            to_version=1,
            description="drops everything",
            apply=lambda data: {**data, "attempts": []},
        )
        import quest_app.migrations as module

        original = module.MIGRATIONS
        module.MIGRATIONS = (destructive,)
        try:
            with pytest.raises(MigrationError, match="dropped attempt"):
                migrate({"schema_version": 0, "attempts": [{"attempt_id": "a-1"}]})
        finally:
            module.MIGRATIONS = original

    def test_a_migration_that_drops_a_field_is_refused(self) -> None:
        destructive = Migration(
            from_version=0,
            to_version=1,
            description="drops the participant",
            apply=lambda data: {k: v for k, v in data.items() if k != "participant"},
        )
        import quest_app.migrations as module

        original = module.MIGRATIONS
        module.MIGRATIONS = (destructive,)
        try:
            with pytest.raises(MigrationError, match="dropped field"):
                migrate({"schema_version": 0, "participant": {"id": "p"}, "attempts": []})
        finally:
            module.MIGRATIONS = original

    def test_an_unknown_field_is_carried_forward(self) -> None:
        """Dropping it would destroy data written by a newer build a participant may return to."""
        migrated, _ = migrate({"schema_version": 0, "attempts": [], "future_field": "keep me"})
        assert migrated["future_field"] == "keep me"


class TestInProgressAttempts:
    def test_an_in_progress_attempt_on_an_older_version_is_reported_not_moved(self) -> None:
        data = {
            "attempts": [
                {"attempt_id": "a-1", "quest_id": "q", "quest_version": 1, "state": "in_progress"}
            ]
        }
        stale = attempts_on_older_quest_versions(data, {"q": 2})
        assert [attempt["attempt_id"] for attempt in stale] == ["a-1"]
        # Reported only: the record itself is untouched.
        assert data["attempts"][0]["quest_version"] == 1

    def test_a_verified_attempt_is_not_reported_as_stale(self) -> None:
        """Verified work stays verified; a newer quest version does not revoke it."""
        data = {
            "attempts": [
                {"attempt_id": "a-1", "quest_id": "q", "quest_version": 1, "state": "verified"}
            ]
        }
        assert attempts_on_older_quest_versions(data, {"q": 2}) == []


class TestUpdatePreflight:
    def test_a_directory_that_is_not_a_repository_blocks(self, config: AppConfig) -> None:
        result = preflight(config)
        assert not result.safe_to_proceed
        assert any(finding.id == "repository" for finding in result.findings)

    def test_a_dirty_working_tree_blocks_with_the_command_to_fix_it(
        self, config: AppConfig
    ) -> None:
        _init_repo(config.repo_root)
        (config.repo_root / "scratch.txt").write_text("uncommitted\n")

        result = preflight(config)

        blocker = next(f for f in result.findings if f.id == "working-tree")
        assert blocker.blocks
        assert "git commit" in (blocker.remediation or "")

    def test_a_clean_tree_without_an_upstream_remote_blocks(self, config: AppConfig) -> None:
        _init_repo(config.repo_root, commit=True)
        result = preflight(config)
        upstream = next(f for f in result.findings if f.id == "upstream-remote")
        assert upstream.blocks
        assert "git remote add upstream" in (upstream.remediation or "")

    def test_the_instructions_create_a_backup_before_anything_else(self) -> None:
        text = update_instructions("backup/x", "main")
        assert text.index("git branch backup/x") < text.index("git merge")
        assert "reset --hard backup/x" in text

    def test_the_preflight_says_participant_files_are_never_replaced(
        self, config: AppConfig
    ) -> None:
        _init_repo(config.repo_root, commit=True)
        result = preflight(config)
        assert any("never replaced" in finding.summary for finding in result.findings)


class TestGitSafety:
    def test_no_permitted_command_can_change_history_or_the_working_tree(self) -> None:
        """The update helper reports and stops; it never runs the merge itself."""
        forbidden = {
            "merge",
            "rebase",
            "reset",
            "checkout",
            "switch",
            "clean",
            "push",
            "pull",
            "commit",
        }
        for command in PERMITTED_COMMANDS:
            assert not forbidden & set(command), command

    def test_asking_for_a_forbidden_command_raises(self, config: AppConfig) -> None:
        from quest_app.update import _git

        with pytest.raises(ValueError, match="not permitted"):
            _git(config.repo_root, ("merge", "upstream/main"))

    def test_backup_branch_names_do_not_collide(self) -> None:
        assert backup_branch_name().startswith("backup/pre-update-")


@pytest.mark.slow
def test_participant_files_survive_an_upstream_style_update(config: AppConfig) -> None:
    """The promise, end to end: program files change, participant files do not.

    Simulated rather than mocked — a real repository, a real commit, a real change to
    program-owned content while participant evidence sits beside it.
    """
    _init_repo(config.repo_root, commit=True)
    evidence = config.participant_root / "evidence" / "base-camp-repository-safety"
    proof = next(evidence.rglob("PROOF.md"))
    before = proof.read_text()
    progress_before = (config.participant_root / "progress.yaml").read_text()

    # An "upstream" change: program-owned content is rewritten.
    quest = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text(quest.read_text().replace("## Mission", "## Mission\n\nA new sentence."))
    subprocess.run(
        ["git", "-C", str(config.repo_root), "add", "-A"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(config.repo_root), "commit", "-m", "upstream change"],
        check=True,
        capture_output=True,
        env=_git_env(),
    )

    assert proof.read_text() == before
    assert (config.participant_root / "progress.yaml").read_text() == progress_before


def _git_env() -> dict[str, str]:
    import os

    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


def _init_repo(root: Path, *, commit: bool = False) -> None:
    subprocess.run(
        ["git", "-C", str(root), "init", "-q", "-b", "main"], check=True, capture_output=True
    )
    if commit:
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(root), "commit", "-q", "-m", "initial"],
            check=True,
            capture_output=True,
            env=_git_env(),
        )
