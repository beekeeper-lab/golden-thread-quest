"""Proof detection, the secret gate, and where a validation result is allowed to land."""

from __future__ import annotations

import json
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
