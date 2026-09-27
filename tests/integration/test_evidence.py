"""Proof detection, the secret gate, and where a validation result is allowed to land."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.evidence import (
    detect_proof,
    evidence_hash,
    new_run_id,
    scan_evidence,
    store_result,
)
from quest_app.pipeline import load_world

EVIDENCE = "participant/evidence/base-camp-repository-safety/base-camp-attempt-001"
LEAKED = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow


@pytest.fixture
def world(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    loaded = load_world(config, report)
    assert loaded is not None, report.to_text()
    return loaded


class TestProofDetection:
    def test_a_validator_requirement_is_validated_only_by_a_qualifying_result(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        results = world.participant.results_for(attempt)

        states = detect_proof(quest, config, attempt.evidence_path, results)

        validator_items = [item for item in quest.proof if item.type == "validator"]
        for item in validator_items:
            matching = [r for r in results if r.validator_id == item.validator]
            expected_validated = any(r.qualifies for r in matching)
            assert (states[item.id] == "validated") is expected_validated

    def test_detection_never_claims_validated_without_a_result(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        quest = world.content.quests["playwright-first-independent-test"]
        states = detect_proof(quest, config, None, ())
        assert "validated" not in states.values()

    def test_a_demonstration_cannot_be_detected_from_the_filesystem(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """A checkbox must not stand in for a person watching someone work."""
        for quest in world.content.quests.values():
            states = detect_proof(quest, config, None, ())
            for item in quest.proof:
                if item.type in ("demonstration", "review"):
                    assert states[item.id] == "missing"

    def test_evidence_saved_where_the_quest_says_to_save_it_is_detected(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The quest names `attempt-001/logs/…`; the real package is `<prefix>-attempt-001`.

        Every file-proof path in the curriculum points into `logs/` or `screenshots/`, the
        subdirectories the evidence package is created with, and the authored attempt
        directory is one no attempt ever has. Detection looked for the bare filename at the
        top of the package, so following the instructions produced "Not detected".
        """
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")
        assert "/attempt-001/logs/" in item.path, "this test is about that shape of path"

        package = config.resolve_participant_path(attempt.evidence_path)
        saved = package / "logs" / Path(item.path).name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text("second run created no duplicate\n")

        states = detect_proof(quest, config, attempt.evidence_path, ())
        assert states[item.id] == "detected"

    def test_the_package_fallback_keeps_the_subdirectory_the_quest_asked_for(
        self, world, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Accepting the file anywhere under the package would be a weaker rule, not a fix."""
        quest = world.content.quests["base-camp-repository-safety"]
        attempt = world.participant.progress.attempt_for(quest.id)
        item = next(i for i in quest.proof if i.type == "command-record")

        package = config.resolve_participant_path(attempt.evidence_path)
        wrong = package / "screenshots" / Path(item.path).name
        wrong.parent.mkdir(parents=True, exist_ok=True)
        wrong.write_text("saved in the wrong place\n")

        states = detect_proof(quest, config, attempt.evidence_path, ())
        assert states[item.id] == "missing"

    def test_a_traversing_proof_path_is_never_detected(self, world, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        import dataclasses

        quest = world.content.quests["base-camp-repository-safety"]
        item = dataclasses.replace(quest.proof[0], type="file", path="../../../etc/passwd")
        hostile = dataclasses.replace(quest, proof=(item,))
        assert detect_proof(hostile, config, None, ())[item.id] == "missing"


class TestSecretScanning:
    def test_clean_evidence_produces_no_findings(self, config: AppConfig) -> None:
        assert scan_evidence(config, EVIDENCE) == []

    def test_a_planted_credential_is_found(self, config: AppConfig) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"I used token={LEAKED} to authenticate.\n")
        findings = scan_evidence(config, EVIDENCE)
        assert findings
        assert findings[0].path.endswith("notes.md")

    def test_a_finding_never_carries_the_value(self, config: AppConfig) -> None:
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"token={LEAKED}\n")
        # SecretFinding is slotted, so `asdict` rather than `__dict__`.
        import dataclasses

        rendered = json.dumps([dataclasses.asdict(f) for f in scan_evidence(config, EVIDENCE)])
        assert LEAKED not in rendered

    def test_an_allow_pragma_in_evidence_does_not_switch_the_scan_off(
        self, config: AppConfig
    ) -> None:
        """The pragma is a repository-hygiene device, not something a submission can use."""
        target = config.resolve_participant_path(EVIDENCE) / "notes.md"
        target.write_text(f"token={LEAKED}  # secret-scan: allow\n")
        assert scan_evidence(config, EVIDENCE), "evidence scanning must ignore the pragma"

    def test_a_byte_that_is_not_utf8_does_not_hide_the_file(self, config: AppConfig) -> None:
        """One Latin-1 byte made the whole file undecodable, and the scan skipped it."""
        target = config.resolve_participant_path(EVIDENCE) / "logs" / "run.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"Caf\xe9 opened\n" + f"token={LEAKED}\n".encode())
        findings = scan_evidence(config, EVIDENCE)
        assert [finding.path.rsplit("/", 1)[-1] for finding in findings] == ["run.log"]

    def test_a_file_that_cannot_be_read_blocks_rather_than_passing(self, config: AppConfig) -> None:
        if os.geteuid() == 0:
            pytest.skip("root can read a file whatever its mode")
        target = config.resolve_participant_path(EVIDENCE) / "unreadable.md"
        target.write_text("anything\n")
        target.chmod(0)
        try:
            findings = scan_evidence(config, EVIDENCE)
        finally:
            target.chmod(0o600)
        assert [finding.description for finding in findings] == ["could not be read to check it"]

    def test_a_traversing_evidence_path_scans_nothing(self, config: AppConfig) -> None:
        assert scan_evidence(config, "participant/evidence/../../etc") == []


class TestEvidenceHash:
    def test_the_hash_changes_when_the_evidence_changes(self, config: AppConfig) -> None:
        before = evidence_hash(config, EVIDENCE)
        (config.resolve_participant_path(EVIDENCE) / "PROOF.md").write_text("# Different\n")
        assert evidence_hash(config, EVIDENCE) != before

    def test_a_new_validation_run_does_not_change_the_hash(self, config: AppConfig) -> None:
        """Otherwise re-running a check would make every prior review look stale."""
        before = evidence_hash(config, EVIDENCE)
        store_result(
            config,
            EVIDENCE,
            {
                "schema_version": 1,
                "run_id": new_run_id("validate-repository-foundation"),
                "validator_id": "validate-repository-foundation",
                "validator_version": 1,
                "quest_id": "base-camp-repository-safety",
                "attempt_id": "base-camp-attempt-001",
                "started_at": "2026-09-16T10:00:00Z",
                "completed_at": "2026-09-16T10:00:01Z",
                "duration_ms": 1000,
                "outcome": "pass",
                "checks": [{"id": "c", "outcome": "pass", "summary": "ok"}],
                "redaction_applied": False,
            },
        )
        assert evidence_hash(config, EVIDENCE) == before

    def test_a_missing_directory_has_no_hash(self, config: AppConfig) -> None:
        assert evidence_hash(config, "participant/evidence/nothing/here") is None

    def test_an_unreadable_file_is_named_relatively_not_by_a_traceback(
        self, config: AppConfig
    ) -> None:
        """Round 13 E8.

        An unreadable file used to crash the hash outright with an unhandled `OSError`, and
        the traceback that reached the terminal carried this file's absolute path. It must
        instead be reported through `UnreadableFileError`, naming the file by a path relative
        to the evidence package.
        """
        from quest_app.hashing import UnreadableFileError

        if os.geteuid() == 0:
            pytest.skip("root can read a file whatever its mode")
        target = config.resolve_participant_path(EVIDENCE) / "unreadable.md"
        target.write_text("anything\n")
        target.chmod(0)
        try:
            with pytest.raises(UnreadableFileError) as raised:
                evidence_hash(config, EVIDENCE)
        finally:
            target.chmod(0o600)
        assert raised.value.relative_path == "unreadable.md"
        assert str(config.repo_root) not in str(raised.value)
        assert str(config.participant_root) not in str(raised.value)


def test_a_result_is_stored_by_its_attempt_not_by_its_own_claim(config: AppConfig) -> None:
    """The path comes from the attempt, so a record cannot file itself elsewhere."""
    stored = store_result(
        config,
        EVIDENCE,
        {
            "run_id": "probe-run",
            "attempt_id": "some-other-attempt",
            "quest_id": "jira-read-assigned-stories",
        },
    )
    assert stored.startswith(EVIDENCE)
    assert (config.resolve_participant_path(EVIDENCE) / "validation" / "probe-run.json").exists()


def test_run_ids_do_not_collide() -> None:
    assert len({new_run_id("v") for _ in range(50)}) == 50


def test_a_stored_result_path_is_participant_relative(config: AppConfig, tmp_path: Path) -> None:
    del tmp_path
    stored = store_result(config, EVIDENCE, {"run_id": "r1"})
    assert stored.startswith("participant/")
    assert not Path(stored).is_absolute()


@pytest.mark.parametrize(
    ("outcome", "counts"),
    [
        ("pass", True),
        ("warning", True),
        ("fail", False),
        ("inconclusive", False),
        ("interrupted", False),
        ("environment_failure", False),
    ],
)
def test_only_a_pass_or_a_warning_counts_towards_local_validation(
    outcome: str, counts: bool
) -> None:
    """`qualifies` is the gate for `locally_validated`, and it survived being widened.

    Adding `inconclusive` and `interrupted` to it passed the whole suite: the one test that
    touched it computed its expectation from the same property. "We could not tell" is not
    evidence, and a run that was stopped is not a run.
    """
    from quest_app.progress import ValidationResult

    result = ValidationResult(
        run_id="run-001",
        validator_id="validate-repository-foundation",
        validator_version=1,
        quest_id="base-camp-repository-safety",
        attempt_id="base-camp-attempt-001",
        started_at="2026-09-22T00:00:00+00:00",
        completed_at="2026-09-22T00:00:01+00:00",
        duration_ms=1000,
        outcome=outcome,
        checks=(),
        redaction_applied=False,
        source="participant/evidence/x/y/validation/run-001.json",
    )
    assert result.qualifies is counts
