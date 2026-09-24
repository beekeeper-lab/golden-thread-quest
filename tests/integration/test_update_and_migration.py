"""Receiving upstream curriculum without losing participant work.

The promise this repository makes is that a participant can take improvements and keep
everything they wrote. These are the tests that hold it.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path

import pytest
from quest_app.config import SUPPORTED_SCHEMA_VERSION, AppConfig
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

    @pytest.mark.parametrize(
        "schema_version",
        ["abc", [1], {"nested": True}],
        ids=["string", "list", "mapping"],
    )
    def test_a_non_integer_schema_version_is_a_migration_error_not_a_traceback(
        self, schema_version: object
    ) -> None:
        """`migrate()` called `int(data.get("schema_version", 0))` unguarded (E2). A
        `schema_version` written as a string, a list or a mapping — all of which a hostile
        or merely broken `progress.yaml` can carry, and which `validate` already reports
        cleanly — raised `ValueError`/`TypeError` straight out of `migrate()` and into a CLI
        traceback instead of the `MigrationError` every caller already handles.
        """
        with pytest.raises(MigrationError, match="not a whole number"):
            migrate({"schema_version": schema_version, "attempts": []})


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

    def test_the_instructions_name_make_migrate_after_validate_content(self) -> None:
        """The printed sequence used to end at `make validate-content` and never name
        `make migrate`, so after a merge the stale-progress-schema notes went unmentioned
        until the participant found `make migrate` some other way."""
        text = update_instructions("backup/x", "main")
        assert text.index("make validate-content") < text.index("make migrate")

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
    def test_the_preflight_names_one_branch(
        self, config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The name is built from the clock, and it was built twice.

        A preflight that straddled a second boundary reported one branch in
        `proposed_backup_branch` and told the participant to create another in `instructions`.
        Forcing a different name per call turns that once-a-second race into an assertion.
        """
        from quest_app import update as update_module

        names = iter(["backup/pre-update-first", "backup/pre-update-second"])
        monkeypatch.setattr(update_module, "backup_branch_name", lambda: next(names))
        _init_repo(config.repo_root, commit=True)
        result = preflight(config)

        assert result.proposed_backup_branch, "the preflight found no repository to report on"
        assert result.proposed_backup_branch in result.instructions


def _git_commands(instructions: str) -> list[list[str]]:
    """The `git` lines a participant would copy out of `update_instructions()`.

    Strips the trailing `# comment` off each line and drops anything that is not a `git`
    invocation (the printed recipe also names `make validate-content`, which this fixture's
    stripped-down repository copy cannot run).
    """
    commands = []
    for line in instructions.splitlines():
        line = re.split(r"\s+#", line, maxsplit=1)[0].strip()
        if line.startswith("git "):
            commands.append(shlex.split(line)[1:])
    return commands


@pytest.mark.slow
def test_participant_files_survive_an_upstream_style_update(
    config: AppConfig, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """The promise, end to end, driven by the application's own preflight and the exact
    commands `update_instructions()` prints — not a hand-rolled Git sequence that would
    still pass with `quest_app/update.py` gutted.

    A real repository, a real second remote standing in for upstream, program-owned content
    changed there, and the merge performed by running the printed recipe verbatim.
    """
    _init_repo(config.repo_root, commit=True)

    # A real 'upstream' remote, so `preflight()` reports the repository as safe to update
    # from and the instructions it prints are the ones this test then runs.
    upstream = tmp_path_factory.mktemp("upstream") / "origin.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(config.repo_root), str(upstream)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(config.repo_root), "remote", "add", "upstream", str(upstream)],
        check=True,
        capture_output=True,
    )

    result = preflight(config)
    assert result.safe_to_proceed, [
        finding.summary for finding in result.findings if finding.blocks
    ]
    assert result.proposed_backup_branch is not None

    evidence = config.participant_root / "evidence" / "base-camp-repository-safety"
    proof = next(evidence.rglob("PROOF.md"))
    before = proof.read_text()
    progress_before = (config.participant_root / "progress.yaml").read_text()

    # Upstream publishes a change to program-owned content, through a second clone —
    # nothing here touches the participant's own working copy directly.
    upstream_work = tmp_path_factory.mktemp("upstream-work") / "clone"
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(upstream_work)], check=True, capture_output=True
    )
    quest = upstream_work / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text(quest.read_text().replace("## Mission", "## Mission\n\nA new sentence."))
    subprocess.run(["git", "-C", str(upstream_work), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(upstream_work), "commit", "-q", "-m", "upstream change"],
        check=True,
        capture_output=True,
        env=_git_env(),
    )
    subprocess.run(
        ["git", "-C", str(upstream_work), "push", "-q", "origin", "HEAD:main"],
        check=True,
        capture_output=True,
        env=_git_env(),
    )

    # Run exactly the commands `update_instructions()` printed for the participant to
    # copy and paste — the real update path, not a paraphrase of it.
    commands = _git_commands(result.instructions)
    assert commands, "update_instructions() printed no git commands to run"
    for command in commands:
        subprocess.run(
            ["git", "-C", str(config.repo_root), *command],
            check=True,
            capture_output=True,
            env=_git_env(),
        )

    # The update actually happened...
    quest_now = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
    assert "A new sentence." in quest_now.read_text()
    # ...and the participant's own files were not touched by any of it.
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


class TestSchemaVersionAtLoad:
    """`config.SUPPORTED_SCHEMA_VERSION` said a newer file is refused. It was loaded, and the
    next action rewrote it in the old shape. No command applied a migration at all."""

    @staticmethod
    def _declare(config: AppConfig, version: int) -> None:
        import yaml

        path = config.participant_root / "progress.yaml"
        data = yaml.safe_load(path.read_text())
        data["schema_version"] = version
        path.write_text(yaml.safe_dump(data, sort_keys=False))

    def test_a_file_from_a_newer_application_is_refused(self, config: AppConfig) -> None:
        from quest_app.errors import ProblemReport
        from quest_app.pipeline import load_world

        self._declare(config, 7)
        report = ProblemReport()
        assert load_world(config, report) is None
        assert "progress.newer_schema" in {p.code for p in report.errors}

    def test_an_older_file_is_refused_until_migrated_and_then_loads(
        self, config: AppConfig
    ) -> None:
        import yaml
        from quest_app.errors import ProblemReport
        from quest_app.pipeline import load_world
        from quest_app.update import apply_migrations

        self._declare(config, 0)
        report = ProblemReport()
        assert load_world(config, report) is None
        assert "progress.needs_migration" in {p.code for p in report.errors}

        applied, problems = apply_migrations(config)
        assert problems == []
        assert applied and applied[0].startswith("0 → 1")
        assert (
            yaml.safe_load((config.participant_root / "progress.yaml").read_text())[
                "schema_version"
            ]
            == SUPPORTED_SCHEMA_VERSION
        )
        assert load_world(config, ProblemReport()) is not None

    def test_a_migration_that_leaves_state_unloadable_is_rolled_back(
        self, config: AppConfig
    ) -> None:
        from quest_app.update import apply_migrations

        self._declare(config, 0)
        path = config.participant_root / "progress.yaml"
        before = path.read_text()
        # Valid against the schema, but the attempt now points at a quest that does not exist.
        broken = before.replace("quest_id: jira-read-assigned-stories", "quest_id: no-such-quest")
        path.write_text(broken)
        applied, problems = apply_migrations(config)
        assert applied == []
        assert "restored" in problems[0]
        assert path.read_text() == broken


def test_a_merge_in_progress_is_named_and_committing_everything_is_not_advised(
    config: AppConfig,
) -> None:
    root = config.repo_root
    _init_repo(root, commit=True)
    git = ["git", "-C", str(root)]
    target = root / "content" / "README-conflict.txt"
    target.write_text("base\n")
    subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-qm", "base"], check=True, capture_output=True, env=_git_env())
    subprocess.run([*git, "switch", "-qc", "upstream-side"], check=True, capture_output=True)
    target.write_text("theirs\n")
    subprocess.run(
        [*git, "commit", "-qam", "theirs"], check=True, capture_output=True, env=_git_env()
    )
    subprocess.run([*git, "switch", "-q", "main"], check=True, capture_output=True)
    target.write_text("ours\n")
    subprocess.run(
        [*git, "commit", "-qam", "ours"], check=True, capture_output=True, env=_git_env()
    )
    merged = subprocess.run([*git, "merge", "upstream-side"], capture_output=True, env=_git_env())
    assert merged.returncode != 0, "the fixture needs a real conflict"

    result = preflight(config)
    merge = next(f for f in result.findings if f.id == "merge-in-progress")
    assert merge.blocks
    assert "git merge --abort" in (merge.remediation or "")
    assert not any("git add -A" in (f.remediation or "") for f in result.findings)


def _conflict_progress_yaml(root: Path) -> None:
    """Leave `participant/progress.yaml` mid-merge, holding real conflict markers.

    Conflict markers are not valid YAML, so this is what `store.read()` used to raise
    `yaml.YAMLError` on straight out of `migration_report`/`apply_migrations` (E2), before
    `preflight`'s own `merge-in-progress` finding — computed from Git, never from this
    file's content — ever printed a word.
    """
    _init_repo(root, commit=True)
    git = ["git", "-C", str(root)]
    progress = root / "participant" / "progress.yaml"
    subprocess.run([*git, "switch", "-qc", "upstream-side"], check=True, capture_output=True)
    progress.write_text(progress.read_text().replace("Alex Rivera", "Upstream Rivera"))
    subprocess.run(
        [*git, "commit", "-qam", "theirs"], check=True, capture_output=True, env=_git_env()
    )
    subprocess.run([*git, "switch", "-q", "main"], check=True, capture_output=True)
    progress.write_text(progress.read_text().replace("Alex Rivera", "Local Rivera"))
    subprocess.run(
        [*git, "commit", "-qam", "ours"], check=True, capture_output=True, env=_git_env()
    )
    merged = subprocess.run([*git, "merge", "upstream-side"], capture_output=True, env=_git_env())
    assert merged.returncode != 0, "the fixture needs a real conflict"
    assert "<<<<<<<" in progress.read_text(), "the fixture needs conflict markers in the file"


class TestUpdateCommandOnHostileProgressFiles:
    """`update.py` read `progress.yaml` through `ProgressStore.read()`'s raw
    `strict_safe_load`, with none of the exception handling `content_loader.read_text` gives
    `validate` — so every one of these shapes, which `validate` already reports as one clean
    line, raised straight through `migration_report`/`apply_migrations` and into a CLI
    traceback carrying absolute paths (E2)."""

    def test_a_merge_in_progress_produces_no_traceback_from_update_check(
        self, config: AppConfig, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import quest_app.update as update_module
        from quest_app.cli import main

        _conflict_progress_yaml(config.repo_root)

        def _must_not_be_called(*_args: object, **_kwargs: object) -> None:
            raise AssertionError(
                "migration_report must not run while progress.yaml may hold conflict markers"
            )

        monkeypatch.setattr(update_module, "migration_report", _must_not_be_called)

        exit_code = main(["update", "--repo-root", str(config.repo_root)])
        out = capsys.readouterr()

        assert "Traceback" not in out.err
        assert exit_code != 0
        assert "merge is in progress" in (out.out + out.err).lower()

    def test_a_merge_in_progress_produces_no_traceback_from_update_migrate(
        self, config: AppConfig, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quest_app.cli import main

        _conflict_progress_yaml(config.repo_root)

        exit_code = main(["update", "--migrate", "--repo-root", str(config.repo_root)])
        out = capsys.readouterr()

        assert "Traceback" not in out.err
        assert exit_code != 0
        assert "merge is in progress" in (out.out + out.err).lower()

    @pytest.mark.parametrize(
        "make_hostile",
        [
            lambda p: p.write_text(
                p.read_text().replace("schema_version: 1", "schema_version: abc")
            ),
            lambda p: p.write_text(
                p.read_text().replace("schema_version: 1", "schema_version: [1]")
            ),
            lambda p: p.write_text("schema_version: 1\nattempts: [\n"),
            lambda p: p.write_bytes(
                b'schema_version: 1\nparticipant: {id: x, display_name: "\xff\xfe"}\n'
            ),
            lambda p: (p.unlink(), p.symlink_to("/etc/passwd")),
            lambda p: (p.unlink(), p.mkdir()),
        ],
        ids=[
            "non_integer_schema_version",
            "list_schema_version",
            "malformed_yaml",
            "non_utf8",
            "symlink_outside_participant",
            "directory",
        ],
    )
    def test_migration_report_and_apply_migrations_do_not_raise(
        self, config: AppConfig, make_hostile: object
    ) -> None:
        from quest_app.update import apply_migrations, migration_report

        path = config.participant_root / "progress.yaml"
        make_hostile(path)  # type: ignore[operator]

        migration_report(config)  # must not raise
        apply_migrations(config)  # must not raise

    def test_update_check_on_these_files_prints_no_traceback(
        self, config: AppConfig, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quest_app.cli import main

        path = config.participant_root / "progress.yaml"
        path.write_text("schema_version: 1\nattempts: [\n")

        main(["update", "--repo-root", str(config.repo_root)])
        assert "Traceback" not in capsys.readouterr().err

    def test_update_migrate_on_these_files_prints_no_traceback(
        self, config: AppConfig, capsys: pytest.CaptureFixture[str]
    ) -> None:
        from quest_app.cli import main

        path = config.participant_root / "progress.yaml"
        path.write_text("schema_version: 1\nattempts: [\n")

        main(["update", "--migrate", "--repo-root", str(config.repo_root)])
        assert "Traceback" not in capsys.readouterr().err


def test_apply_migrations_takes_the_progress_lock(tmp_path: Path) -> None:
    """`make migrate` (`apply_migrations`) reads, decides and writes `progress.yaml` the same
    shape every action does, but did not take `participant/.progress.lock` across it (E8):
    a concurrent holder of the lock did not make it wait, so it could run its read-modify-
    write interleaved with an action's. Wrapping it in `store.exclusive()` makes it wait like
    everything else that touches this file — observable here the same way
    `test_waiting_for_another_change_says_so` observes an action waiting: the message
    `store.exclusive()` prints only while it is blocked on the lock.
    """
    import sys

    from quest_app.config import AppConfig
    from quest_app.content_loader import SchemaSet
    from quest_app.store import ProgressStore

    repo_root = Path(__file__).resolve().parents[2]
    participant = tmp_path / "participant"
    config = AppConfig.for_repo(repo_root, participant_root=participant)
    store = ProgressStore(config)
    store.initialise(
        "p", "Participant", "golden-thread-foundations", SchemaSet(config.schemas_root)
    )
    # A pending migration to apply, so `apply_migrations` actually writes.
    path = participant / "progress.yaml"
    path.write_text(path.read_text().replace("schema_version: 1\n", "", 1))

    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import fcntl,sys,time\n"
            "h=open(sys.argv[1],'a+')\n"
            "fcntl.flock(h.fileno(), fcntl.LOCK_EX)\n"
            "print('held', flush=True)\n"
            "time.sleep(2)\n",
            str(store.lock_path),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "held"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "quest_app.cli",
                "update",
                "--migrate",
                "--repo-root",
                str(repo_root),
                "--participant-root",
                str(participant),
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        holder.wait(timeout=30)

    assert "Another change is in progress" in result.stderr
    assert result.returncode == 0, result.stderr
    assert "[migrated]" in result.stdout


def test_a_failed_migration_restores_original_bytes_including_crlf(config: AppConfig) -> None:
    """The restore after a failed migration used `read_text`/`write_text` (E9), which
    normalizes CRLF line endings to LF on the way through — a participant whose editor uses
    CRLF would see their untouched file "restored" with different bytes. Restoring through
    `atomic_write_bytes` puts back exactly what was read, line endings included.
    """
    import yaml
    from quest_app.update import apply_migrations

    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    data["schema_version"] = 0
    for attempt in data["attempts"]:
        if attempt["quest_id"] == "jira-read-assigned-stories":
            attempt["quest_id"] = "no-such-quest"  # valid against the schema, refuses to load
    text = "# a participant's own comment, which a text round-trip also keeps\n" + yaml.safe_dump(
        data, sort_keys=False
    )
    original_bytes = text.replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(original_bytes)

    applied, problems = apply_migrations(config)

    assert applied == []
    assert "restored" in problems[0]
    restored = path.read_bytes()
    assert restored == original_bytes
    assert b"\r\n" in restored
    assert b"a participant's own comment" in restored
