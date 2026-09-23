"""A participant record cannot grant itself authority it does not have.

`participant/progress.yaml` is the participant's own file, editable in any text editor. That
is deliberate — the work is theirs and lives in their Git history. It is also why `verified`
is re-derived from review records rather than believed, and why every one of the ways an
attempt could claim approval it does not have gets its own test here (ADR-011).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.progress import load_participant_state

VERIFIED_ATTEMPT = "base-camp-attempt-001"
EVIDENCE = "participant/evidence/base-camp-repository-safety/base-camp-attempt-001"


def progress_path(config: AppConfig) -> Path:
    return config.participant_root / "progress.yaml"


def edit_progress(config: AppConfig, mutate: object) -> None:
    path = progress_path(config)
    data = yaml.safe_load(path.read_text())
    mutate(data)  # type: ignore[operator]
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def review_path(config: AppConfig) -> Path:
    return (
        config.participant_root
        / "evidence"
        / "base-camp-repository-safety"
        / VERIFIED_ATTEMPT
        / "review.yaml"
    )


def edit_review(config: AppConfig, mutate: object) -> None:
    path = review_path(config)
    data = yaml.safe_load(path.read_text())
    mutate(data)  # type: ignore[operator]
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def load(config: AppConfig, report: ProblemReport) -> object:
    return load_participant_state(config, SchemaSet(config.schemas_root), report)


def codes(report: ProblemReport) -> set[str]:
    return {p.code for p in report.problems}


def test_the_shipped_fixture_is_consistent(config: AppConfig, report: ProblemReport) -> None:
    state = load(config, report)
    assert state is not None
    assert report.errors == [], report.to_text()


class TestForgedVerification:
    """Each of these is a different way to claim verified completion without an approval."""

    def test_verified_with_no_review_reference(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            for attempt in data["attempts"]:  # type: ignore[attr-defined]
                if attempt["attempt_id"] == VERIFIED_ATTEMPT:
                    attempt.pop("review_id", None)

        edit_progress(config, mutate)
        load(config, report)
        assert "progress.unverified_verified_state" in codes(report)

    def test_verified_naming_a_review_that_does_not_exist(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            for attempt in data["attempts"]:  # type: ignore[attr-defined]
                if attempt["attempt_id"] == VERIFIED_ATTEMPT:
                    attempt["review_id"] = "invented-review"

        edit_progress(config, mutate)
        load(config, report)
        assert "progress.unverified_verified_state" in codes(report)

    def test_approval_belonging_to_a_different_attempt(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """An approval is for one attempt. Reusing it is the most plausible forgery."""
        edit_review(config, lambda data: data.__setitem__("attempt_id", "some-other-attempt"))
        load(config, report)
        assert "progress.unverified_verified_state" in codes(report)

    def test_a_needs_changes_review_does_not_verify(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            data["decision"] = "needs_changes"
            data["findings"] = [
                {
                    "id": "finding-1",
                    "severity": "high",
                    "summary": "Evidence does not reproduce",
                    "evidence": "The documented command fails on a clean clone",
                }
            ]

        edit_review(config, mutate)
        load(config, report)
        assert "progress.unverified_verified_state" in codes(report)

    def test_approval_without_a_verification_statement(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """The statement is the reviewer saying what they checked, in their own words."""
        edit_review(config, lambda data: data.pop("verification_statement", None))
        load(config, report)
        # The schema refuses it first; either layer catching it is correct, but one must.
        assert codes(report) & {
            "progress.unverified_verified_state",
            "schema.review.required",
        }

    def test_approval_for_a_different_quest(self, config: AppConfig, report: ProblemReport) -> None:
        edit_review(config, lambda data: data.__setitem__("quest_id", "jira-read-assigned-stories"))
        load(config, report)
        assert "progress.unverified_verified_state" in codes(report)


class TestRecordIntegrity:
    def test_duplicate_attempt_ids_are_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            attempts = data["attempts"]  # type: ignore[index]
            attempts.append(dict(attempts[0]))  # type: ignore[attr-defined]

        edit_progress(config, mutate)
        load(config, report)
        assert "progress.duplicate_attempt_id" in codes(report)

    def test_missing_evidence_directory_is_reported(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        import shutil

        shutil.rmtree(config.participant_root / "evidence" / "base-camp-repository-safety")
        load(config, report)
        assert "progress.missing_evidence_directory" in codes(report)

    def test_unsafe_evidence_path_is_refused(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            data["attempts"][0]["evidence_path"] = "participant/evidence/../../escape"  # type: ignore[index]

        edit_progress(config, mutate)
        load(config, report)
        # The schema pattern refuses it, and so does the resolver. Both are load-bearing:
        # the schema protects the file, the resolver protects every path built from it.
        assert codes(report) & {"progress.unsafe_evidence_path", "schema.progress.pattern"}

    def test_attempt_for_an_unknown_quest_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            data["attempts"][0]["quest_id"] = "no-such-quest"  # type: ignore[index]

        edit_progress(config, mutate)
        load_world(config, report)
        assert "progress.unknown_quest" in codes(report)

    def test_attempt_on_a_future_quest_version_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        def mutate(data: dict[str, object]) -> None:
            data["attempts"][0]["quest_version"] = 99  # type: ignore[index]

        edit_progress(config, mutate)
        load_world(config, report)
        assert "progress.future_quest_version" in codes(report)

    def test_editing_a_verified_quest_warns_and_does_not_break_the_build(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """Editing a quest someone has already had approved must not fail the build.

        `CONTENT-MODEL.md`: previously verified attempts remain verified unless a documented
        policy revokes them. The build reports a possibly-stale approval and continues
        (ADR-028). Making this an error was the first thing tried, and this test is why it
        is not.
        """
        quest = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
        # Bumped from whatever the quest is on now. Written against the literal `version: 1`,
        # this test stopped mutating anything the day the quest reached version 2 and passed
        # by asserting warnings the fixture already carried.
        source = quest.read_text()
        current = int(re.search(r"(?m)^version: (\d+)$", source).group(1))
        quest.write_text(re.sub(r"(?m)^version: \d+$", f"version: {current + 1}", source, count=1))

        world = load_world(config, report)

        assert world is not None, report.to_text()
        warnings = {p.code for p in report.warnings}
        assert "progress.outdated_quest_version" in warnings
        assert "progress.content_hash_mismatch" in warnings

    def test_a_changed_content_hash_is_reported(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """Stored and never compared, the hash was decoration: 64 zeros validated."""

        def mutate(data: dict[str, object]) -> None:
            data["attempts"][0]["content_hash"] = "sha256:" + "0" * 64  # type: ignore[index]

        edit_progress(config, mutate)
        world = load_world(config, report)

        assert world is not None, report.to_text()
        assert "progress.content_hash_mismatch" in {p.code for p in report.warnings}

    def test_the_fixture_carries_real_content_hashes(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """A fixture with placeholder hashes cannot prove the comparison works."""
        load_world(config, report)
        assert "progress.content_hash_mismatch" not in {p.code for p in report.problems}


@pytest.mark.parametrize("state", ["submitted", "needs_changes", "locally_validated"])
def test_non_verified_states_need_no_review(
    config: AppConfig, report: ProblemReport, state: str
) -> None:
    """Only `verified` is gated. Nothing else requires a reviewer to have acted."""

    def mutate(data: dict[str, object]) -> None:
        for attempt in data["attempts"]:  # type: ignore[attr-defined]
            if attempt["attempt_id"] == VERIFIED_ATTEMPT:
                attempt["state"] = state
                attempt.pop("review_id", None)

    edit_progress(config, mutate)
    load(config, report)
    assert "progress.unverified_verified_state" not in codes(report)


class TestLocallyValidatedTellsTheTruth:
    """`locally_validated` on a quest with no validators is an assertion, not a check.

    Five of the eight quests declare no validators. The state is reachable for them — the
    guard exits early — but the interface used to label it "by registered validator" and
    explain it as "Required automated checks passed", which asserts a check that does not
    exist. The authority field is in the model precisely to stop that.
    """

    def test_a_quest_with_no_validators_is_attributed_to_the_participant(self) -> None:
        from quest_app.models import Authority, QuestState
        from quest_app.progress_calc import StateView

        view = StateView.of(QuestState.LOCALLY_VALIDATED, has_validators=False)
        assert view.authority is Authority.PARTICIPANT
        assert "no automated checks" in view.explanation
        assert "checks passed" not in view.explanation

    def test_a_quest_with_validators_still_credits_the_validators(self) -> None:
        from quest_app.models import Authority, QuestState
        from quest_app.progress_calc import StateView

        view = StateView.of(QuestState.LOCALLY_VALIDATED)
        assert view.authority is Authority.REGISTERED_VALIDATOR
        assert "checks passed" in view.explanation

    def test_the_legend_keeps_the_general_wording(self) -> None:
        """A legend describes the state itself, not any one quest."""
        from quest_app.models import Authority, QuestState
        from quest_app.view_models import build_legend

        entry = next(s for s in build_legend() if s.id is QuestState.LOCALLY_VALIDATED)
        assert entry.authority is Authority.REGISTERED_VALIDATOR

    def test_only_locally_validated_is_affected(self) -> None:
        from quest_app.models import STATE_AUTHORITY, QuestState
        from quest_app.progress_calc import StateView

        for state in QuestState:
            if state is QuestState.LOCALLY_VALIDATED:
                continue
            assert StateView.of(state, has_validators=False).authority is STATE_AUTHORITY[state]


@pytest.mark.parametrize(
    "name",
    ["submission.yaml", "review-20260910000000-abcdef.yaml"],
)
@pytest.mark.parametrize("content", ["a: [unclosed\n", "<<<<<<< HEAD\nx: 1\n=======\n"])
def test_a_broken_record_beside_the_review_is_reported_not_a_traceback(
    config: AppConfig, name: str, content: str
) -> None:
    """`validate` passed these and `build` then crashed on them while rendering the reviewer
    page, with a traceback naming absolute paths. A merge conflict leaves exactly this."""
    from quest_app.errors import ProblemReport
    from quest_app.pipeline import load_world

    directory = config.participant_root / "evidence" / "base-camp-repository-safety"
    target = directory / "base-camp-attempt-001" / name
    target.write_text(content)

    report = ProblemReport()
    assert load_world(config, report) is None
    assert any(problem.source.endswith(name) for problem in report.errors), report.to_text()
