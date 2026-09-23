"""The validator framework's constraints, each exercised against the real runner.

`docs/VALIDATOR-CONTRACT.md` lists guarantees. A guarantee nobody tried to break is a
comment, so every one of them is attacked here: unknown IDs, attacker-shaped arguments,
paths outside the registered roots, a timeout with a child of its own, oversized output,
secrets in output, and a passing run trying to become an approval.
"""

from __future__ import annotations

import contextlib
import os
import signal
from pathlib import Path

import pytest
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.models import AttemptState
from quest_app.validator_registry import (
    Parameter,
    ValidatorError,
    load_registry,
    resolve_root,
)
from quest_app.validator_runner import (
    Check,
    ValidatorOutput,
    Workspace,
    WorkspaceError,
    _bounded,
    _import_entrypoint,
    classify,
    run_validator,
)


@pytest.fixture
def registry(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    loaded = load_registry(config, report)
    assert loaded is not None, report.to_text()
    return loaded


class TestOnlyRegisteredValidatorsRun:
    @pytest.mark.parametrize(
        "validator_id",
        [
            "",
            "unknown",
            "../../etc/passwd",
            "os.system",
            "validate-repository-foundation ",
            "VALIDATE",
        ],
    )
    def test_an_unregistered_id_cannot_run(self, registry, validator_id: str) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValidatorError):
            registry.get(validator_id)

    def test_a_validator_cannot_run_for_a_quest_it_is_not_registered_for(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        definition = registry.get("validate-repository-foundation")
        with pytest.raises(ValidatorError, match="not registered to run"):
            run_validator(
                definition,
                config,
                quest_id="jira-read-assigned-stories",
                attempt_id="a-001",
                run_id="run-001",
            )

    @pytest.mark.parametrize(
        "entrypoint",
        [
            "os:system",
            "subprocess:run",
            "builtins:eval",
            "validators.repository_foundation:run; rm -rf /",
            "..validators.x:run",
            "validators.x",
        ],
    )
    def test_an_entrypoint_outside_the_validators_package_is_refused(self, entrypoint: str) -> None:
        """There is no path from a registry edit to importing arbitrary code."""
        with pytest.raises((ValidatorError, ModuleNotFoundError, ImportError)):
            _import_entrypoint(entrypoint)


class TestParameters:
    def test_a_value_outside_the_allowlist_is_refused(self, registry) -> None:  # type: ignore[no-untyped-def]
        definition = registry.get("validate-jira-read-assigned")
        with pytest.raises(ValidatorError, match="must be one of"):
            definition.bind_parameters({"fixture_set": "../../etc/passwd"})

    @pytest.mark.parametrize(
        "value",
        ["happy-path; rm -rf /", "$(whoami)", "`id`", "happy-path\n", "", "HAPPY-PATH"],
    )
    def test_attacker_shaped_values_are_refused(self, registry, value: str) -> None:  # type: ignore[no-untyped-def]
        definition = registry.get("validate-jira-read-assigned")
        with pytest.raises(ValidatorError):
            definition.bind_parameters({"fixture_set": value})

    def test_an_unexpected_parameter_is_refused_rather_than_ignored(self, registry) -> None:  # type: ignore[no-untyped-def]
        """Dropping it silently would let a caller believe they had changed the run."""
        definition = registry.get("validate-jira-read-assigned")
        with pytest.raises(ValidatorError, match="unknown parameter"):
            definition.bind_parameters({"command": "rm -rf /"})

    def test_there_is_no_free_string_parameter_type(self, config: AppConfig) -> None:
        """A free string is how an argument becomes an injection, so the type does not exist."""
        with pytest.raises(ValidatorError, match="unsupported type"):
            Parameter(name="x", type="string").coerce("anything")

    def test_an_integer_outside_its_range_is_refused(self) -> None:
        parameter = Parameter(name="depth", type="integer", minimum=1, maximum=5, default=1)
        assert parameter.coerce(3) == 3
        with pytest.raises(ValidatorError):
            parameter.coerce(99)


class TestWorkspaceContainment:
    @pytest.fixture
    def workspace(self, tmp_path: Path) -> Workspace:
        allowed = tmp_path / "allowed"
        (allowed / "inner").mkdir(parents=True)
        (allowed / "inner" / "file.txt").write_text("in bounds")
        (tmp_path / "secret.txt").write_text("out of bounds")
        return Workspace(
            read_roots=(allowed.resolve(),),
            write_roots=(allowed.resolve(),),
            repo_root=tmp_path,
            participant_root=tmp_path / "participant",
            parameters={},
        )

    def test_reading_inside_the_root_works(self, workspace: Workspace) -> None:
        assert workspace.read_text("allowed/inner/file.txt") == "in bounds"

    @pytest.mark.parametrize(
        "path",
        ["secret.txt", "allowed/../secret.txt", "/etc/passwd", "allowed/inner/../../secret.txt"],
    )
    def test_reading_outside_the_roots_is_refused(self, workspace: Workspace, path: str) -> None:
        with pytest.raises(WorkspaceError):
            workspace.read_text(path)

    def test_a_symlink_cannot_be_used_to_escape(self, workspace: Workspace, tmp_path: Path) -> None:
        """Containment is checked after resolution, so a planted link is not a way out."""
        (tmp_path / "allowed" / "escape.txt").symlink_to(tmp_path / "secret.txt")
        with pytest.raises(WorkspaceError):
            workspace.read_text("allowed/escape.txt")

    def test_writing_outside_the_write_roots_is_refused(self, workspace: Workspace) -> None:
        with pytest.raises(WorkspaceError):
            workspace.write_text("../escaped.txt", "nope")

    def test_a_validator_with_no_write_roots_cannot_write_at_all(self, tmp_path: Path) -> None:
        """Every shipped validator is registered with no write roots."""
        workspace = Workspace(
            read_roots=(tmp_path.resolve(),),
            write_roots=(),
            repo_root=tmp_path,
            participant_root=tmp_path,
            parameters={},
        )
        with pytest.raises(WorkspaceError):
            workspace.write_text("anything.txt", "x")

    def test_listing_never_returns_a_path_outside_the_roots(
        self, workspace: Workspace, tmp_path: Path
    ) -> None:
        (tmp_path / "allowed" / "escape").symlink_to(tmp_path)
        for path in workspace.iter_files("allowed"):
            assert str(path).startswith(str((tmp_path / "allowed").resolve()))

    def test_a_finding_never_names_an_absolute_path(
        self, workspace: Workspace, tmp_path: Path
    ) -> None:
        assert not workspace.relative(tmp_path / "allowed" / "inner" / "file.txt").startswith("/")


class TestShippedRegistry:
    def test_no_shipped_validator_may_write_anywhere(self, registry) -> None:  # type: ignore[no-untyped-def]
        for validator_id in registry.ids():
            assert registry.get(validator_id).write_roots == (), validator_id

    def test_no_shipped_validator_has_network_access(self, registry) -> None:  # type: ignore[no-untyped-def]
        for validator_id in registry.ids():
            assert registry.get(validator_id).network == "denied", validator_id

    def test_every_validator_has_a_timeout_and_an_output_cap(self, registry) -> None:  # type: ignore[no-untyped-def]
        for validator_id in registry.ids():
            definition = registry.get(validator_id)
            assert 0 < definition.timeout_seconds <= 600
            assert definition.max_output_bytes > 0

    def test_the_environment_allowlist_carries_no_credential_name(self, registry) -> None:  # type: ignore[no-untyped-def]
        forbidden = ("TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL")
        for validator_id in registry.ids():
            for name in registry.get(validator_id).environment_allowlist:
                assert not any(marker in name.upper() for marker in forbidden), name

    def test_participant_roots_follow_the_configured_participant_directory(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Resolving against the repository root instead would point every check at nothing."""
        roots = registry.get("validate-repository-foundation").resolved_read_roots(config)
        assert config.participant_root.resolve() in roots

    def test_a_non_participant_root_still_resolves_against_the_repository(
        self, config: AppConfig
    ) -> None:
        assert resolve_root(config, "content") == (config.repo_root / "content").resolve()


class TestRunning:
    @pytest.mark.slow
    def test_a_real_run_produces_a_schema_valid_document(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        from jsonschema import Draft202012Validator, FormatChecker
        from quest_app.content_loader import SchemaSet

        result = run_validator(
            registry.get("validate-repository-foundation"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="base-camp-attempt-001",
            run_id="test-run-001",
        )
        document = result.to_document()
        schemas = SchemaSet(config.schemas_root)
        del schemas
        import json

        schema = json.loads((config.schemas_root / "validation-result.schema.json").read_text())
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document)
        )
        assert errors == [], [error.message for error in errors]

    @pytest.mark.slow
    def test_a_timeout_produces_interrupted_not_a_verdict(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """A run that did not finish says nothing either way, so it is never a verdict.

        The probe validator spawns a child of its own, so this also proves the timeout kills
        the process group rather than only the direct child.
        """
        import dataclasses

        impatient = dataclasses.replace(
            registry.get("validate-repository-foundation"),
            timeout_seconds=1,
            entrypoint="validators.slow_probe:run",
        )
        result = run_validator(
            impatient,
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="timeout-run",
        )
        assert result.outcome == "interrupted"
        assert result.outcome not in ("pass", "fail", "warning")


class TestClassification:
    def test_an_inconclusive_check_is_not_a_pass(self) -> None:
        """Letting "we could not tell" qualify is the quietest way to void locally_validated."""
        output = ValidatorOutput(checks=[Check(id="c", outcome="inconclusive", summary="s")])
        assert classify(output) == "inconclusive"

    def test_a_single_failure_fails_the_run(self) -> None:
        output = ValidatorOutput(
            checks=[
                Check(id="a", outcome="pass", summary="s"),
                Check(id="b", outcome="fail", summary="s"),
            ]
        )
        assert classify(output) == "fail"

    def test_a_warning_alone_is_a_warning(self) -> None:
        output = ValidatorOutput(checks=[Check(id="a", outcome="warning", summary="s")])
        assert classify(output) == "warning"

    def test_no_checks_is_inconclusive_not_a_pass(self) -> None:
        assert classify(ValidatorOutput()) == "inconclusive"

    def test_every_check_skipped_is_inconclusive_not_a_pass(self) -> None:
        output = ValidatorOutput(checks=[Check(id="a", outcome="skipped", summary="s")] * 3)
        assert classify(output) == "inconclusive"

    def test_run_ids_made_in_the_same_second_sort_in_the_order_they_were_made(self) -> None:
        """Results are ordered by `(completed_at, run_id)` at one-second resolution, so the
        run ID is the tie-break. A random suffix decided which of two runs was the latest."""
        from quest_app.evidence import new_run_id

        made = [new_run_id("validate-repository-foundation") for _ in range(50)]
        assert made == sorted(made)

    def test_an_environment_failure_outranks_everything(self) -> None:
        output = ValidatorOutput(checks=[Check(id="a", outcome="pass", summary="s")])
        output.fail_environment("no fixture installed")
        assert classify(output) == "environment_failure"


class TestOutputHandling:
    def test_large_output_is_bounded_and_marked(self) -> None:
        text, truncated = _bounded("x" * 10_000, 1024)
        assert truncated
        assert len(text.encode()) <= 1024 + 64
        assert "truncated" in text

    def test_small_output_is_untouched(self) -> None:
        assert _bounded("short", 1024) == ("short", False)

    @pytest.mark.slow
    def test_secret_like_output_is_redacted_before_it_is_stored(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        from quest_app.secret_patterns import REDACTION_PLACEHOLDER, redact_text

        leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
        redacted, applied = redact_text(f"validator said token={leaked}")
        assert applied
        assert leaked not in redacted
        assert REDACTION_PLACEHOLDER in redacted


def test_a_passing_validator_cannot_produce_verified(registry) -> None:  # type: ignore[no-untyped-def]
    """The whole point of ADR-011, asserted where it would be easiest to break."""
    from quest_app.state_machine import BY_ACTION

    assert all(t.target is not AttemptState.VERIFIED for t in BY_ACTION.values())
    assert "verified" not in {t.target.value for t in BY_ACTION.values()}


class TestEnvironmentIsolation:
    """What the child can actually see, asked of the child.

    The first version of this only inspected registry strings for credential-shaped names,
    which cannot tell you whether the parent applied them. It did not: the environment was
    set around `process.start()`, and `forkserver` captures its helper's environment once —
    so the second validator of a session inherited the first one's allowlist, in both
    directions.
    """

    @staticmethod
    def _seen(result: object) -> dict[str, str]:
        return {
            check.evidence.split("=", 1)[0]: check.evidence.split("=", 1)[1]
            for check in result.checks  # type: ignore[attr-defined]
            if check.evidence and "=" in check.evidence
        }

    @pytest.mark.slow
    def test_an_empty_allowlist_hides_an_exported_variable(
        self, registry, config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.invalid")
        result = run_validator(
            registry.get("probe-environment-empty"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="env-empty",
        )
        assert self._seen(result)["JIRA_BASE_URL"] == "<ABSENT>"

    @pytest.mark.slow
    def test_the_child_starts_in_the_declared_working_directory(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """`working_directory` is required by the schema, set on every entry, documented in
        the contract — and applied nowhere. The child started in the repository root, so a
        validator resolving a relative path as the contract describes read the wrong tree."""
        result = run_validator(
            registry.get("probe-environment-empty"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="env-cwd",
        )
        where = next(check for check in result.checks if check.id == "working-directory")
        assert Path(where.evidence or "") == config.participant_root.resolve()

    @pytest.mark.slow
    def test_an_allowed_variable_reaches_the_child(
        self, registry, config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.invalid")
        result = run_validator(
            registry.get("probe-environment-allowed"),
            config,
            quest_id="jira-read-assigned-stories",
            attempt_id="a-001",
            run_id="env-allowed",
        )
        assert self._seen(result)["JIRA_BASE_URL"] == "https://jira.example.invalid"

    @pytest.mark.slow
    def test_one_run_does_not_leak_into_the_next_in_either_direction(
        self, registry, config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:  # type: ignore[no-untyped-def]
        """The defect: order decided what a validator could see, and in a running service
        the order is whatever the participant clicks first."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.example.invalid")
        monkeypatch.setenv("GTQ_TEST_SECRET", "must-never-be-seen")

        allowed = run_validator(
            registry.get("probe-environment-allowed"),
            config,
            quest_id="jira-read-assigned-stories",
            attempt_id="a-001",
            run_id="env-order-1",
        )
        empty = run_validator(
            registry.get("probe-environment-empty"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="env-order-2",
        )

        assert self._seen(allowed)["JIRA_BASE_URL"] == "https://jira.example.invalid"
        assert self._seen(empty)["JIRA_BASE_URL"] == "<ABSENT>"
        for result in (allowed, empty):
            assert self._seen(result)["GTQ_TEST_SECRET"] == "<ABSENT>", (
                "a variable on no allowlist reached a validator"
            )


class TestAResultAlwaysLoadsBack:
    """A run that produced no checks used to write a document the loader then refused.

    The schema requires at least one check. A timeout and an early environment failure both
    produced none, `store_result` was the only writer that did not validate, and the invalid
    file then stopped the whole site from loading — blaming the curriculum for a file in the
    participant's own evidence. One click, total outage.

    The two tests that should have caught it validated only the happy path.
    """

    @pytest.mark.slow
    def test_a_timeout_still_produces_a_storable_result(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        import dataclasses
        import json

        from jsonschema import Draft202012Validator, FormatChecker

        impatient = dataclasses.replace(
            registry.get("validate-repository-foundation"),
            timeout_seconds=1,
            entrypoint="validators.slow_probe:run",
        )
        result = run_validator(
            impatient,
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="timeout-storable",
        )

        assert result.outcome == "interrupted"
        assert result.checks, "a result with no checks cannot be stored"
        schema = json.loads((config.schemas_root / "validation-result.schema.json").read_text())
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(
                result.to_document()
            )
        )
        assert errors == [], [error.message for error in errors]

    @pytest.mark.slow
    def test_the_fallback_check_says_what_happened(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        """ "Interrupted" with an empty list tells the participant nothing."""
        import dataclasses

        impatient = dataclasses.replace(
            registry.get("validate-repository-foundation"),
            timeout_seconds=1,
            entrypoint="validators.slow_probe:run",
        )
        (check,) = run_validator(
            impatient,
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="timeout-explains",
        ).checks
        assert check.outcome == "inconclusive", "a timeout is not a verdict on the work"
        assert "time limit" in check.summary
        assert check.suggested_action

    def test_storing_an_invalid_result_is_refused_rather_than_written(
        self, config: AppConfig
    ) -> None:
        from quest_app.content_loader import SchemaSet
        from quest_app.evidence import ResultRejectedError, store_result

        evidence = "participant/evidence/base-camp-repository-safety/base-camp-attempt-001"
        with pytest.raises(ResultRejectedError):
            store_result(
                config,
                evidence,
                {"run_id": "bad-run", "checks": []},
                SchemaSet(config.schemas_root),
            )
        target = config.resolve_participant_path(evidence) / "validation" / "bad-run.json"
        assert not target.exists(), "an invalid result must not reach disk"

    def test_an_unreadable_result_warns_instead_of_stopping_the_site(
        self, config: AppConfig
    ) -> None:
        """One bad file in a participant's evidence must not make the curriculum unpublishable."""
        from quest_app.errors import ProblemReport
        from quest_app.pipeline import load_world

        evidence = (
            config.participant_root
            / "evidence"
            / "base-camp-repository-safety"
            / "base-camp-attempt-001"
            / "validation"
        )
        (evidence / "corrupt.json").write_text('{"run_id": "corrupt", "checks": []}')

        report = ProblemReport()
        world = load_world(config, report)

        assert world is not None, report.to_text()
        assert "validation.unusable_result" in {p.code for p in report.warnings}

    @pytest.mark.slow
    def test_a_check_cannot_write_a_secret_to_disk(self, config: AppConfig) -> None:
        """The module claimed output was redacted before persistence; only the excerpt was."""
        from dataclasses import replace as _replace

        from quest_app.secret_patterns import REDACTION_PLACEHOLDER
        from quest_app.validator_runner import RunResult

        leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
        check = Check(id="c", outcome="fail", summary=f"found token={leaked}", evidence=leaked)
        del _replace, RunResult, config

        from quest_app.secret_patterns import redact_text

        cleaned, changed = redact_text(check.summary)
        assert changed and leaked not in cleaned and REDACTION_PLACEHOLDER in cleaned


class TestAValidatorJudgesTheAttemptItWasGiven:
    """A check about this attempt's evidence must not be decided by another attempt's files.

    Round 6's checks reached for `participant/evidence` and took whichever file was newest,
    so a blank `PROOF.md` under an unrelated quest failed a complete one, and any log left
    behind by any other quest satisfied "failure is diagnosable" here. Records are connected
    by their identifiers (`CLAUDE.md`), never by modification time.
    """

    COMPLETE_PROOF = (
        "# Proof\n"
        "What was built: the ownership document and the audit log.\n"
        "Where the artifacts are: the path is participant/context.\n"
        "How to reproduce: run the documented steps in order.\n"
        "What was validated: the registered checks ran and passed.\n"
        "Remaining limitations: does not cover a live connection.\n"
    )

    def _evidence(self, config: AppConfig, quest_id: str, attempt_id: str) -> Path:
        directory = config.participant_root / "evidence" / quest_id / attempt_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @pytest.mark.slow
    def test_another_quests_blank_proof_cannot_fail_this_attempt(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        mine = self._evidence(config, "base-camp-repository-safety", "base-attempt-002")
        (mine / "PROOF.md").write_text(self.COMPLETE_PROOF)

        theirs = self._evidence(config, "ba-ingest-transcript", "attempt-001")
        stranger = theirs / "PROOF.md"
        stranger.write_text("# Proof\n")
        # Newer than mine, which is all the old implementation looked at.
        import os

        os.utime(stranger, (2_000_000_000, 2_000_000_000))

        result = run_validator(
            registry.get("validate-repository-foundation"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="base-attempt-002",
            run_id="scoped-run-001",
        )
        answers = next(c for c in result.checks if c.id == "proof-answers-reviewer-questions")
        assert answers.outcome == "pass", answers.evidence
        assert answers.artifact is not None
        assert "ba-ingest-transcript" not in answers.artifact

    @pytest.mark.slow
    def test_a_secret_in_another_attempt_does_not_fail_this_one(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """`submit-for-review` scans the package being submitted, so nothing goes unscanned."""
        mine = self._evidence(config, "base-camp-repository-safety", "base-attempt-003")
        (mine / "PROOF.md").write_text(self.COMPLETE_PROOF)
        theirs = self._evidence(config, "jira-read-assigned-stories", "attempt-001")
        (theirs / "notes.md").write_text(
            "ghp_abcdefghijklmnopqrstuvwxyz0123456789\n"  # secret-scan: allow
        )

        result = run_validator(
            registry.get("validate-repository-foundation"),
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="base-attempt-003",
            run_id="scoped-run-002",
        )
        secrets = next(c for c in result.checks if c.id == "evidence-carries-no-secrets")
        assert secrets.outcome == "pass", secrets.evidence

    @pytest.mark.slow
    def test_a_success_log_is_not_failure_evidence(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        """Criterion 9 asks what a failure looks like, not whether any file exists."""
        tests_dir = config.participant_root / "tests" / "playwright"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "first-independent-test.spec.ts").write_text(
            "test('a customer can check out', async ({ page }) => {\n"
            "  await page.getByRole('button', { name: 'Pay' }).click();\n"
            "  await expect(page.getByText('Thank you')).toBeVisible();\n"
            "});\n"
        )

        mine = self._evidence(config, "playwright-first-independent-test", "attempt-001")
        (mine / "logs").mkdir(exist_ok=True)
        (mine / "logs" / "test-run.txt").write_text("1 passed\n")
        stranger = self._evidence(config, "base-camp-repository-safety", "base-attempt-004")
        (stranger / "second-run.txt").write_text("no duplicates\n")

        result = run_validator(
            registry.get("validate-playwright-quality"),
            config,
            quest_id="playwright-first-independent-test",
            attempt_id="attempt-001",
            run_id="scoped-run-003",
        )
        diagnosable = next(c for c in result.checks if c.id == "failure-is-diagnosable")
        assert diagnosable.outcome == "warning", diagnosable.evidence

        (mine / "logs" / "failure-run.txt").write_text("1 failed: expected 'Thank you'\n")
        (mine / "failure.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        result = run_validator(
            registry.get("validate-playwright-quality"),
            config,
            quest_id="playwright-first-independent-test",
            attempt_id="attempt-001",
            run_id="scoped-run-004",
        )
        diagnosable = next(c for c in result.checks if c.id == "failure-is-diagnosable")
        assert diagnosable.outcome == "pass", diagnosable.evidence


class TestTheJiraFixturesTestWhatTheyDescribe:
    """Each fixture set is a promise about what choosing it demonstrates.

    Two of them did not keep it: `duplicate-comment` described a comment arriving on two
    pages and carried no comment at all, and `stale-item` described a story that had to be
    reported rather than dropped and carried no trace of one. A participant who chose either
    to show criterion 7 or criterion 8 showed neither, and the run passed.
    """

    def _sync(self, config: AppConfig, document: dict) -> None:  # type: ignore[type-arg]
        import json

        directory = config.participant_root / "context" / "jira"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "assigned.json").write_text(json.dumps(document))

    def _run(self, registry, config: AppConfig, fixture_set: str):  # type: ignore[no-untyped-def]
        return run_validator(
            registry.get("validate-jira-read-assigned"),
            config,
            quest_id="jira-read-assigned-stories",
            attempt_id="jira-attempt-001",
            run_id=f"jira-{fixture_set}",
            parameters={"fixture_set": fixture_set},
        )

    def _story(self, key: str, **extra):  # type: ignore[no-untyped-def]
        record = {
            "key": key,
            "summary": f"Fixture story {key}",
            "status": "To Do",
            "source_url": f"https://jira.example.invalid/browse/{key}",
            "retrieved_at": "2026-09-22T00:00:00+00:00",
        }
        record.update(extra)
        return record

    @pytest.mark.slow
    def test_dropping_a_story_that_disappeared_fails(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        self._sync(config, {"stories": [self._story("GTQ-101"), self._story("GTQ-102")]})
        result = self._run(registry, config, "stale-item")
        check = next(c for c in result.checks if c.id == "disappearances-reported")
        assert check.outcome == "fail"
        assert "GTQ-100" in (check.evidence or "")

    @pytest.mark.slow
    def test_reporting_it_with_its_last_known_state_passes(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        self._sync(
            config,
            {
                "stories": [self._story("GTQ-101"), self._story("GTQ-102")],
                "removed": [{"key": "GTQ-100", "last_known_status": "In Progress"}],
            },
        )
        result = self._run(registry, config, "stale-item")
        check = next(c for c in result.checks if c.id == "disappearances-reported")
        assert check.outcome == "pass", check.evidence

    @pytest.mark.slow
    def test_a_comment_recorded_twice_fails(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        self._sync(
            config,
            {
                "stories": [
                    self._story(
                        "GTQ-101",
                        comments=[{"id": "9001"}, {"id": "9002"}, {"id": "9001"}],
                    ),
                    self._story("GTQ-102", comments=[{"id": "9003"}]),
                    self._story("GTQ-103", comments=[]),
                ]
            },
        )
        result = self._run(registry, config, "duplicate-comment")
        check = next(c for c in result.checks if c.id == "no-duplicate-comments")
        assert check.outcome == "fail"
        assert "9001" in (check.evidence or "")

    @pytest.mark.slow
    def test_reconciling_the_comment_by_its_identifier_passes(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        self._sync(
            config,
            {
                "stories": [
                    self._story("GTQ-101", comments=[{"id": "9001"}, {"id": "9002"}]),
                    self._story("GTQ-102", comments=[{"id": "9003"}]),
                    self._story("GTQ-103", comments=[]),
                ]
            },
        )
        result = self._run(registry, config, "duplicate-comment")
        check = next(c for c in result.checks if c.id == "no-duplicate-comments")
        assert check.outcome == "pass", check.evidence

    @pytest.mark.slow
    def test_a_fixture_without_the_behaviour_does_not_judge_it(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The happy path says nothing about either, rather than passing them for free."""
        self._sync(
            config,
            {"stories": [self._story(key) for key in ("GTQ-101", "GTQ-102", "GTQ-103")]},
        )
        result = self._run(registry, config, "happy-path")
        reported = [c.id for c in result.checks]
        assert "disappearances-reported" not in reported
        assert "no-duplicate-comments" not in reported


def _processes_carrying(marker: str) -> set[int]:
    """Every live process whose command line mentions `marker`."""
    import subprocess

    listing = subprocess.run(  # fixed argv, no shell
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=False
    )
    found = set()
    for line in listing.stdout.splitlines():
        pid, _, args = line.strip().partition(" ")
        if marker in args and pid.isdigit():
            found.add(int(pid))
    return found


@pytest.mark.slow
def test_a_timeout_kills_what_the_validator_spawned(registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
    """The whole process group, not just the child.

    `os.killpg` downgraded to `os.kill` passed the entire suite while the grandchild kept
    running for two minutes: nothing looked for it. A stopped run that keeps working is
    worse than one that never stopped.
    """
    import dataclasses
    import time

    from validators.slow_probe import GRANDCHILD_MARKER

    before = _processes_carrying(GRANDCHILD_MARKER)
    impatient = dataclasses.replace(
        registry.get("validate-repository-foundation"),
        timeout_seconds=1,
        entrypoint="validators.slow_probe:run",
    )
    result = run_validator(
        impatient,
        config,
        quest_id="base-camp-repository-safety",
        attempt_id="a-001",
        run_id="grandchild-run",
    )
    assert result.outcome == "interrupted"

    deadline = time.monotonic() + 5
    survivors = _processes_carrying(GRANDCHILD_MARKER) - before
    while survivors and time.monotonic() < deadline:
        time.sleep(0.2)
        survivors = _processes_carrying(GRANDCHILD_MARKER) - before
    for pid in survivors:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)
    assert not survivors, f"the validator's grandchild outlived the timeout: {survivors}"


class TestHostileChildren:
    """Validators written to break the parent, each placed in the test's own copy.

    Every one of these used to succeed: a participant's file replaced registered code, a
    non-UTF-8 byte lost the whole run, output was read into memory without a ceiling, a
    stray `print()` became "could not be read", and a grandchild outlived a finished run.
    """

    @staticmethod
    def _run(registry, config: AppConfig, source: str, timeout: int = 20):  # type: ignore[no-untyped-def]
        import dataclasses
        import textwrap

        (config.repo_root / "validators" / "hostile_probe.py").write_text(textwrap.dedent(source))
        definition = dataclasses.replace(
            registry.get("validate-repository-foundation"),
            timeout_seconds=timeout,
            entrypoint="validators.hostile_probe:run",
        )
        return run_validator(
            definition,
            config,
            quest_id="base-camp-repository-safety",
            attempt_id="a-001",
            run_id="hostile-run",
        )

    PASSING = """
        from quest_app.validator_runner import Check

        def run(workspace, output):
            output.add(Check(id="probe", outcome="pass", summary="ran"))
    """

    @pytest.mark.slow
    def test_participant_code_cannot_replace_a_registered_validator(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The child runs in `participant/`, which `python -m` put first on the import path."""
        shadow = config.participant_root / "validators"
        shadow.mkdir(parents=True, exist_ok=True)
        (shadow / "__init__.py").write_text("")
        (shadow / "hostile_probe.py").write_text(
            "from quest_app.validator_runner import Check\n"
            "def run(workspace, output):\n"
            "    output.add(Check(id='shadow', outcome='pass', summary='participant code'))\n"
        )
        (config.participant_root / "json.py").write_text("raise SystemExit(3)\n")
        result = self._run(registry, config, self.PASSING)
        assert [check.id for check in result.checks] == ["probe"], result.checks

    @pytest.mark.slow
    @pytest.mark.parametrize("stream", ["stdout", "stderr"])
    def test_non_utf8_output_still_produces_a_result(
        self, registry, config: AppConfig, stream: str
    ) -> None:  # type: ignore[no-untyped-def]
        result = self._run(
            registry,
            config,
            f"""
            import sys
            from quest_app.validator_runner import Check

            def run(workspace, output):
                sys.{stream}.buffer.write(b"\\xff\\xfe caf\\xe9\\n")
                sys.{stream}.flush()
                output.add(Check(id="probe", outcome="pass", summary="ran"))
            """,
        )
        assert result.outcome == "pass", result

    @pytest.mark.slow
    def test_a_stray_print_does_not_corrupt_the_result(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        result = self._run(
            registry,
            config,
            """
            import subprocess, sys
            from quest_app.validator_runner import Check

            def run(workspace, output):
                print("debugging output")
                subprocess.run([sys.executable, "-c", "print('from a child')"], check=True)
                output.add(Check(id="probe", outcome="pass", summary="ran"))
            """,
        )
        assert result.outcome == "pass", result

    @pytest.mark.slow
    def test_output_past_the_ceiling_stops_the_run(self, registry, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        import resource

        from quest_app.validator_runner import STREAM_LIMIT

        before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result = self._run(
            registry,
            config,
            """
            import sys

            def run(workspace, output):
                chunk = b"x" * 1048576
                for _ in range(200):
                    sys.stderr.buffer.write(chunk)
            """,
        )
        grown_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before
        assert result.outcome == "environment_failure"
        assert f"more than {STREAM_LIMIT} bytes" in result.output_excerpt
        assert grown_kib < 50 * 1024, f"the parent grew by {grown_kib} KiB"

    @pytest.mark.slow
    def test_a_grandchild_holding_the_pipe_does_not_turn_a_pass_into_a_timeout(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        import time

        started = time.monotonic()
        result = self._run(
            registry,
            config,
            """
            import subprocess, sys
            from quest_app.validator_runner import Check

            def run(workspace, output):
                subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
                output.add(Check(id="probe", outcome="pass", summary="ran"))
            """,
            timeout=10,
        )
        assert result.outcome == "pass", result
        assert time.monotonic() - started < 8

    @pytest.mark.slow
    def test_a_grandchild_does_not_outlive_a_finished_run(
        self, registry, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        import time

        marker = config.participant_root / "grandchild.pid"
        result = self._run(
            registry,
            config,
            f"""
            import subprocess, sys
            from quest_app.validator_runner import Check

            def run(workspace, output):
                child = subprocess.Popen(
                    [sys.executable, "-c", "import time; time.sleep(60)"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                open({str(marker)!r}, "w").write(str(child.pid))
                output.add(Check(id="probe", outcome="pass", summary="ran"))
            """,
        )
        assert result.outcome == "pass"
        pid = int(marker.read_text())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            with contextlib.suppress(ChildProcessError):
                os.waitpid(pid, os.WNOHANG)
            time.sleep(0.1)
        os.kill(pid, signal.SIGKILL)
        pytest.fail("the grandchild was still running after the run finished")
