"""Verified completion is the reviewer's to give, and nobody else's.

Every test here is an attempt to obtain `verified` or verified XP without a reviewer having
actually made a judgment about this attempt's evidence.
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
STATEMENT = "I ran the documented command on a clean clone and reproduced the stated behavior."
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
        """ "ok" is not a judgment.

        Both `record_decision`'s own length check and the schema's `minLength: 20` would
        catch this string, so asserting only `ReviewError` would still pass with the Python
        guard deleted. Matching the guard's own wording proves it is that check, not the
        schema, doing the refusing.
        """
        submit(setup, config)
        world, attempt = reload_attempt(config)
        _, schemas, store, quest, _ = setup
        with pytest.raises(ReviewError, match="verification statement saying what you checked"):
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
        first = (directory / "review.yaml").read_text()
        assert "needs_changes" in first

        # The second decision is the one that supersedes. Until round 7 this test recorded
        # only one, and asserted `archive or review.yaml exists` — an `or` whose right side
        # is always true, so deleting the archiving code outright left the suite green.
        from quest_app.store import transition_attempt

        for action in ("resume-quest", "mark-evidence-ready"):
            transition_attempt(
                store, quest_id=QUEST, action=action, schemas=schemas, guard=lambda _action: None
            )
        world, attempt = reload_attempt(config)
        create_submission(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            schemas=schemas,
        )
        world, attempt = reload_attempt(config)
        record_decision(
            config,
            store,
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            decision="approved",
            reviewer_name="A Reviewer",
            verification_statement="I read the evidence and it does what it claims.",
            findings=[],
            schemas=schemas,
        )
        archived = list(directory.glob("review-*.yaml"))
        assert archived, "the superseded decision was overwritten"
        assert "needs_changes" in archived[0].read_text()
        assert "approved" in (directory / "review.yaml").read_text()


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


class TestEvidenceChangedAfterApproval:
    """An approval describes the evidence that existed when it was made.

    Both of these kept `verified` and its XP with no signal at all: the only hash comparison
    happened inside `record_decision`, which says nothing about what happens afterwards.
    """

    def approve(self, setup, config: AppConfig):  # type: ignore[no-untyped-def]
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
        return reload_attempt(config)[1]

    def test_rewriting_the_evidence_after_approval_is_surfaced(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        attempt = self.approve(setup, config)
        proof = config.resolve_participant_path(attempt.evidence_path) / "PROOF.md"
        proof.write_text("# Rewritten after the reviewer approved it\n")

        report = ProblemReport()
        world = load_world(config, report)

        assert world is not None, report.to_text()
        assert "progress.evidence_changed_since_approval" in {p.code for p in report.warnings}

    def test_editing_the_reviews_own_hash_is_surfaced(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        attempt = self.approve(setup, config)
        path = config.resolve_participant_path(attempt.evidence_path) / "review.yaml"
        data = yaml.safe_load(path.read_text())
        data["evidence_hash"] = "sha256:" + "0" * 64
        path.write_text(yaml.safe_dump(data, sort_keys=False))

        report = ProblemReport()
        world = load_world(config, report)

        assert world is not None, report.to_text()
        assert "progress.evidence_changed_since_approval" in {p.code for p in report.warnings}

    def test_untouched_evidence_produces_no_warning(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        self.approve(setup, config)
        report = ProblemReport()
        assert load_world(config, report) is not None
        assert "progress.evidence_changed_since_approval" not in {p.code for p in report.problems}

    def test_the_approval_still_stands(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        """A warning, not a revocation: CONTENT-MODEL.md keeps verified attempts verified."""
        attempt = self.approve(setup, config)
        proof = config.resolve_participant_path(attempt.evidence_path) / "PROOF.md"
        proof.write_text("# Rewritten\n")

        report = ProblemReport()
        world = load_world(config, report)

        assert world is not None
        assert report.ok, "a changed evidence package must not break the build"
        _, after = reload_attempt(config)
        assert after.recorded_state is AttemptState.VERIFIED


def test_an_approval_for_a_different_quest_version_does_not_verify(
    setup, config: AppConfig
) -> None:  # type: ignore[no-untyped-def]
    """An approval of a version that was never attempted must not confer verified XP.

    The integrity check compared review to attempt, review to quest, the decision and the
    statement — and never the version. Setting `quest_version: 99` left the attempt verified
    with no warning at all.
    """
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
    data["quest_version"] = 99
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    report = ProblemReport()
    assert load_world(config, report) is None
    assert "progress.unverified_verified_state" in {p.code for p in report.errors}


def test_the_transition_guard_cannot_be_omitted() -> None:
    """`locally_validated` needs qualifying results, and the guard is how that is enforced.

    It used to default to `None`, so the invariant its own docstring claimed did not exist:
    a caller could reach `locally_validated` with no validation results on disk.
    """
    import inspect

    from quest_app.store import transition_attempt

    guard = inspect.signature(transition_attempt).parameters["guard"]
    assert guard.default is inspect.Parameter.empty, "the guard must be required"


class TestTheParticipantIsToldWhy:
    """A decision the participant cannot read is not a decision they can act on."""

    def test_needs_changes_findings_reach_the_participant_s_own_pages(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """The reason lived in `review.yaml` and on the reviewer's page, nowhere else.

        The participant was told "a reviewer asked for corrections" and had to open a YAML
        file in their own repository to find out what the corrections were.
        """
        from quest_app.build import build_site

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

        report = ProblemReport()
        rebuilt = load_world(config, report)
        assert rebuilt is not None, report.to_text()
        build_site(rebuilt, built_at="2026-09-16T00:00:00+00:00")

        for relative in (
            f"quests/{QUEST}/index.html",
            f"evidence/{QUEST}/index.html",
        ):
            page = (config.generated_root / relative).read_text()
            assert FINDING["summary"] in page, f"{relative} does not say what is wrong"
            assert FINDING["evidence"] in page, f"{relative} does not say what was observed"
            assert FINDING["severity"] in page, f"{relative} does not say how serious it is"


def test_an_attempt_started_before_a_version_bump_can_still_be_approved(
    content_repo, config: AppConfig
) -> None:  # type: ignore[no-untyped-def]
    """An update that bumps a quest leaves in-progress attempts on the version they started.

    Submission and review recorded the current content version rather than the attempt's,
    so the integrity check then read the reviewer's own approval as a forgery and refused to
    load the participant's state at all.
    """
    quest_file = content_repo / "content" / "quests" / "jira-jungle" / "read-assigned-stories.md"
    import re

    text = quest_file.read_text()
    started_on = int(re.search(r"\nversion: (\d+)\n", text).group(1))  # type: ignore[union-attr]
    quest_file.write_text(
        text.replace(f"\nversion: {started_on}\n", f"\nversion: {started_on + 1}\n", 1)
    )

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    schemas = SchemaSet(config.schemas_root)
    store = ProgressStore(config)
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    assert (quest.version, attempt.quest_version) == (started_on + 1, started_on)

    record = submit((world, schemas, store, quest, attempt), config)
    assert record.quest_version == started_on
    world, attempt = reload_attempt(config)
    decision = record_decision(
        config,
        store,
        quest=world.content.quests[QUEST],
        attempt=attempt,
        participant=world.participant,
        decision="approved",
        reviewer_name="A Reviewer",
        verification_statement=STATEMENT,
        findings=[],
        schemas=schemas,
    )
    assert decision.quest_version == started_on

    _, after = reload_attempt(config)
    assert after.recorded_state is AttemptState.VERIFIED


class TestProofOutsideThePackage:
    """Declared proof that lives outside the evidence package is covered too.

    Every quest's required proof names files outside the attempt's package — this one a
    skill in `participant/skills/` and an index in `participant/context/` — and the evidence
    hash covered only the package. Rewriting any of them after submission or after approval
    changed nothing the reviewer was told about.
    """

    SKILL = "participant/skills/jira-read-assigned/SKILL.md"
    OUTSIDE = (
        "participant/context/jira/assigned/index.md",
        "participant/context/jira/assigned/stories.json",
        SKILL,
    )

    def write_proof(self, config: AppConfig) -> None:
        for path in self.OUTSIDE:
            target = config.resolve_participant_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"as submitted: {path}\n")

    def edit_skill(self, config: AppConfig) -> None:
        config.resolve_participant_path(self.SKILL).write_text("rewritten after the fact\n")

    def approve(self, config: AppConfig, **extra):  # type: ignore[no-untyped-def]
        world, attempt = reload_attempt(config)
        return record_decision(
            config,
            ProgressStore(config),
            quest=world.content.quests[QUEST],
            attempt=attempt,
            participant=world.participant,
            decision="approved",
            reviewer_name="A Reviewer",
            verification_statement=STATEMENT,
            findings=[],
            schemas=SchemaSet(config.schemas_root),
            **extra,
        )

    def strip_proof_files(self, config: AppConfig, name: str) -> None:
        _, attempt = reload_attempt(config)
        path = config.resolve_participant_path(attempt.evidence_path) / name
        data = yaml.safe_load(path.read_text())
        del data["proof_files"]
        path.write_text(yaml.safe_dump(data, sort_keys=False))

    def test_the_submission_records_every_declared_path_outside_the_package(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        self.write_proof(config)
        record = submit(setup, config)
        assert record.proof_files is not None
        # The screenshot is authored under the quest's own evidence area, which is the
        # package, so the evidence hash already covers it.
        assert tuple(item["path"] for item in record.proof_files) == self.OUTSIDE
        assert all(item["digest"].startswith("sha256:") for item in record.proof_files)

    def test_editing_proof_outside_the_package_after_submission_needs_acknowledgement(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        self.write_proof(config)
        submit(setup, config)
        self.edit_skill(config)

        _, attempt = reload_attempt(config)
        assert evidence_changed(config, attempt)
        with pytest.raises(ReviewError, match="changed since it was submitted") as raised:
            self.approve(config)
        assert self.SKILL in str(raised.value), "the reviewer is told what to re-read"
        assert self.approve(config, acknowledge_changed_evidence=True).is_approval

    def test_a_proof_file_created_after_submission_is_a_change(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        submit(setup, config)
        self.write_proof(config)
        _, attempt = reload_attempt(config)
        assert evidence_changed(config, attempt)

    def test_the_review_page_names_the_changed_proof(self, setup, config: AppConfig) -> None:  # type: ignore[no-untyped-def]
        from quest_app.build import build_site
        from quest_app.view_models import offline_service_view

        self.write_proof(config)
        submit(setup, config)
        self.edit_skill(config)
        world, _ = reload_attempt(config)
        build_site(world, service=offline_service_view())
        page = (config.generated_root / "review" / QUEST / "index.html").read_text()
        assert "changed since it was submitted" in page
        assert self.SKILL in page

    def test_editing_proof_outside_the_package_after_approval_is_surfaced(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        self.write_proof(config)
        submit(setup, config)
        decision = self.approve(config)
        assert decision.proof_files is not None and len(decision.proof_files) == 3

        report = ProblemReport()
        assert load_world(config, report) is not None
        assert "progress.proof_changed_since_approval" not in {p.code for p in report.problems}

        self.edit_skill(config)
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        stale = [p for p in report.warnings if p.code == "progress.proof_changed_since_approval"]
        assert len(stale) == 1 and self.SKILL in stale[0].public_message
        _, after = reload_attempt(config)
        assert after.recorded_state is AttemptState.VERIFIED, "a warning, not a revocation"

    def test_records_from_before_proof_files_were_recorded_still_load_clean(
        self, setup, config: AppConfig
    ) -> None:  # type: ignore[no-untyped-def]
        """Compared only when present: an old record is neither changed nor forged."""
        self.write_proof(config)
        submit(setup, config)
        self.strip_proof_files(config, "submission.yaml")
        self.edit_skill(config)

        _, attempt = reload_attempt(config)
        assert not evidence_changed(config, attempt)
        self.approve(config)
        self.strip_proof_files(config, "review.yaml")
        self.edit_skill(config)

        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        assert report.ok, report.to_text()
        codes = {p.code for p in report.problems}
        assert not codes & {
            "progress.proof_changed_since_approval",
            "progress.evidence_changed_since_approval",
            "progress.unverified_verified_state",
        }
        _, after = reload_attempt(config)
        assert after.recorded_state is AttemptState.VERIFIED

    def test_a_proof_path_that_leads_out_of_participant_is_never_read(
        self, config: AppConfig, tmp_path
    ) -> None:  # type: ignore[no-untyped-def]
        from quest_app.evidence import proof_file_digests

        outside = tmp_path / "elsewhere.txt"
        outside.write_text("not the participant's\n")
        link = config.resolve_participant_path(self.SKILL)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(outside)
        digests = proof_file_digests(config, [self.SKILL, "participant/../escape"])
        assert {item["digest"] for item in digests} == {"unresolvable"}
