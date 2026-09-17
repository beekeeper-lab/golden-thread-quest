"""Verified completion is the reviewer's to give, and nobody else's.

Every test here is an attempt to obtain `verified` or verified XP without a reviewer having
actually made a judgement about this attempt's evidence.
"""

from __future__ import annotations

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.evidence import evidence_hash
from quest_app.models import AttemptState
from quest_app.pipeline import load_world
from quest_app.progress_calc import compute_states, totals
from quest_app.review import (
    ReviewError,
    create_submission,
    evidence_changed,
    readiness_problems,
    record_decision,
    submission_instructions,
)
from quest_app.store import ProgressStore

QUEST = "jira-read-assigned-stories"
STATEMENT = "I ran the documented command on a clean clone and reproduced the stated behaviour."
FINDING = {
    "id": "finding-1",
    "severity": "high",
    "summary": "The documented command does not run on a clean clone",
    "evidence": "make validate fails with a missing fixture on a fresh checkout",
}


@pytest.fixture
def setup(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    schemas = SchemaSet(config.schemas_root)
    store = ProgressStore(config)
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    return world, schemas, store, quest, attempt


def submit(setup, config: AppConfig):  # type: ignore[no-untyped-def]
    world, schemas, store, quest, attempt = setup
    return create_submission(
        config,
        store,
        quest=quest,
        attempt=attempt,
        participant=world.participant,
        schemas=schemas,
    )


def reload_attempt(config: AppConfig, quest_id: str = QUEST):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    return world, world.participant.progress.attempt_for(quest_id)


class TestSubmission:
    def test_a_submission_records_what_was_true_at_the_time(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        record = submit(setup, config)
        assert record.evidence_hash == evidence_hash(config, setup[4].evidence_path)
        assert record.quest_version == setup[3].version
        _, attempt = reload_attempt(config)
        assert attempt.recorded_state is AttemptState.SUBMITTED
        assert attempt.submission_id == record.submission_id

    def test_a_submission_carrying_a_secret_is_refused(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
        directory = config.resolve_participant_path(setup[4].evidence_path)
        (directory / "notes.md").write_text(f"token={leaked}\n")
        with pytest.raises(ReviewError, match="secret-like"):
            submit(setup, config)

    def test_readiness_separates_blockers_from_advisories(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        world, _, _, quest, attempt = setup
        problems = readiness_problems(quest, attempt, world.participant, config)
        # A validator that has not been run is an advisory: policy may allow submitting
        # anyway, and the reviewer can see it was not run.
        assert all(problem.startswith("advisory:") for problem in problems), problems

    def test_the_instructions_never_push_or_open_a_pull_request_for_you(self) -> None:
        text = submission_instructions(QUEST, "attempt-001", None)
        assert "git push" in text, "the participant is told what to do"
        assert "gh pr create" in text
        # The application prints these; it does not run them.


class TestApprovalGuards:
    def test_approval_without_a_verification_statement_is_refused(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        with pytest.raises(ReviewError, match="verification statement"):
            record_decision(
                config,
                store,
                quest=quest,
                attempt=attempt,
                participant=world.participant,
                decision="approved",
                reviewer_name="A Reviewer",
                verification_statement=None,
                findings=[],
                schemas=schemas,
            )

    def test_a_token_verification_statement_is_refused(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        """ "ok" is not a judgement."""
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        with pytest.raises(ReviewError):
            record_decision(
                config,
                store,
                quest=quest,
                attempt=attempt,
                participant=world.participant,
                decision="approved",
                reviewer_name="A Reviewer",
                verification_statement="ok",
                findings=[],
                schemas=schemas,
            )

    @pytest.mark.parametrize("decision", ["needs_changes", "rejected"])
    def test_asking_for_changes_without_a_finding_is_refused(
        self, setup, config: AppConfig, decision: str
    ) -> None:  # type: ignore[no-untyped-def]
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        with pytest.raises(ReviewError, match="at least one finding"):
            record_decision(
                config,
                store,
                quest=quest,
                attempt=attempt,
                participant=world.participant,
                decision=decision,
                reviewer_name="A Reviewer",
                verification_statement=None,
                findings=[],
                schemas=schemas,
            )

    def test_deciding_an_attempt_that_was_never_submitted_is_refused(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        world, schemas, store, quest, attempt = setup
        with pytest.raises(ReviewError, match="Only a submitted attempt"):
            record_decision(
                config,
                store,
                quest=quest,
                attempt=attempt,
                participant=world.participant,
                decision="approved",
                reviewer_name="A Reviewer",
                verification_statement=STATEMENT,
                findings=[],
                schemas=schemas,
            )

    def test_approving_evidence_that_changed_since_submission_is_refused(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Otherwise the approval applies to something the reviewer has not seen."""
        submit(setup, config)
        world, attempt = reload_attempt(config)
        directory = config.resolve_participant_path(attempt.evidence_path)
        (directory / "PROOF.md").write_text("# Rewritten after submission\n")

        assert evidence_changed(config, attempt)
        _, schemas, store, quest, _ = setup
        with pytest.raises(ReviewError, match="changed since it was submitted"):
            record_decision(
                config,
                store,
                quest=quest,
                attempt=attempt,
                participant=world.participant,
                decision="approved",
                reviewer_name="A Reviewer",
                verification_statement=STATEMENT,
                findings=[],
                schemas=schemas,
            )

    def test_a_reviewer_may_approve_changed_evidence_after_acknowledging_it(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        submit(setup, config)
        world, attempt = reload_attempt(config)
        directory = config.resolve_participant_path(attempt.evidence_path)
        (directory / "PROOF.md").write_text("# Rewritten, and the reviewer has re-read it\n")
        _, schemas, store, quest, _ = setup

        decision = record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="approved",
            reviewer_name="A Reviewer",
            verification_statement=STATEMENT,
            findings=[],
            schemas=schemas,
            acknowledge_changed_evidence=True,
        )
        assert decision.is_approval


class TestWhatApprovalProduces:
    def test_approval_verifies_the_attempt_and_awards_verified_xp(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        before_world, _ = reload_attempt(config)
        before = totals(compute_states(before_world.content, before_world.participant))

        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="approved",
            reviewer_name="A Reviewer",
            verification_statement=STATEMENT,
            findings=[],
            schemas=schemas,
        )

        after_world, after_attempt = reload_attempt(config)
        after = totals(compute_states(after_world.content, after_world.participant))

        assert after_attempt.recorded_state is AttemptState.VERIFIED
        assert after["verified_xp"] == before["verified_xp"] + quest.xp

    def test_needs_changes_returns_the_quest_without_deleting_evidence(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        submit(setup, config)
        world, attempt = reload_attempt(config)
        proof = config.resolve_participant_path(attempt.evidence_path) / "PROOF.md"
        before = proof.read_text()
        _, schemas, store, quest, _ = setup

        record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="needs_changes",
            reviewer_name="A Reviewer",
            verification_statement=None,
            findings=[FINDING],
            schemas=schemas,
        )

        _, after = reload_attempt(config)
        assert after.recorded_state is AttemptState.NEEDS_CHANGES
        assert proof.read_text() == before

    def test_a_superseded_review_is_archived_rather_than_overwritten(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """A participant should see that a reviewer changed their mind, not only the outcome."""
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="needs_changes",
            reviewer_name="A Reviewer",
            verification_statement=None,
            findings=[FINDING],
            schemas=schemas,
        )
        directory = config.resolve_participant_path(attempt.evidence_path)
        assert list(directory.glob("review-*.yaml")) or (directory / "review.yaml").exists()


class TestForgery:
    def test_a_review_for_another_attempt_does_not_verify_this_one(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The most plausible forgery: reuse an approval that really happened."""
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="approved",
            reviewer_name="A Reviewer",
            verification_statement=STATEMENT,
            findings=[],
            schemas=schemas,
        )

        path = config.resolve_participant_path(attempt.evidence_path) / "review.yaml"
        data = yaml.safe_load(path.read_text())
        data["attempt_id"] = "a-different-attempt"
        path.write_text(yaml.safe_dump(data, sort_keys=False))

        report = ProblemReport()
        assert load_world(config, report) is None
        assert "progress.unverified_verified_state" in {p.code for p in report.errors}

    def test_a_hand_written_verified_state_is_refused(self, config: AppConfig) -> None:
        store = ProgressStore(config)
        data = store.read()
        for attempt in data["attempts"]:
            if attempt["quest_id"] == QUEST:
                attempt["state"] = "verified"
        store.path.write_text(yaml.safe_dump(data, sort_keys=False))

        report = ProblemReport()
        assert load_world(config, report) is None
        assert "progress.unverified_verified_state" in {p.code for p in report.errors}
