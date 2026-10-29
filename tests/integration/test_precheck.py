"""The pull request pre-check says what a participant should do, and never approves anything."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_cli_actions import REVIEWED, ROOT, STATEMENT, run, submitted

sys.path.insert(0, str(ROOT / "tools"))

import precheck


def _files(participant: Path) -> list[dict[str, str]]:
    return [
        {"filename": "participant/" + p.relative_to(participant).as_posix(), "status": "added"}
        for p in participant.rglob("*")
        if p.is_file()
    ]


@pytest.fixture
def participant(tmp_path: Path) -> Path:
    return tmp_path / "participant"


def test_a_complete_submission_is_ready_for_review(participant: Path) -> None:
    submitted(participant)
    result = precheck.check(ROOT, participant, _files(participant))
    assert result.status == precheck.READY
    assert result.label == "gtq:ready-for-review"


def test_a_ready_comment_does_not_claim_a_decision_for_the_submitted_quest(
    participant: Path,
) -> None:
    submitted(participant)
    result = precheck.check(ROOT, participant, _files(participant))
    comment = precheck.render_comment(result)
    assert precheck.MARKER in comment
    title = result.checked[0].title
    (line,) = [line for line in comment.splitlines() if title in line]
    assert "all required files are in place" in line
    assert "verified" not in line.lower() and "approved" not in line.lower()
    assert "not a review" in comment


def test_a_missing_required_file_needs_fixes_and_names_it(participant: Path) -> None:
    submitted(participant)
    evidence = next((participant / "evidence" / REVIEWED).iterdir())
    victim = next(
        p
        for p in sorted(evidence.rglob("*"))
        if p.is_file()
        and p.name != "submission.yaml"
        and p.suffix in {".txt", ".md"}
        and p.name != "PROOF.md"
    )
    name = victim.name
    victim.unlink()
    result = precheck.check(ROOT, participant, _files(participant))
    assert result.status == precheck.NEEDS_FIXES
    assert any(name in problem for item in result.checked for problem in item.problems)


def test_a_secret_in_the_evidence_needs_fixes_without_repeating_it(participant: Path) -> None:
    submitted(participant)
    evidence = next((participant / "evidence" / REVIEWED).iterdir())
    secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    (evidence / "notes.md").write_text(f"token = {secret}\n", encoding="utf-8")
    result = precheck.check(ROOT, participant, _files(participant))
    assert result.status == precheck.NEEDS_FIXES
    assert secret not in precheck.render_comment(result)


def test_a_file_outside_participant_is_refused_without_reading_anything(
    participant: Path,
) -> None:
    submitted(participant)
    files = [*_files(participant), {"filename": "quest_app/cli.py", "status": "modified"}]
    result = precheck.check(ROOT, participant, files)
    assert result.status == precheck.NEEDS_FIXES
    assert "quest_app/cli.py" in result.problems[0]
    assert result.checked == []


def test_a_broken_progress_file_is_a_plain_message_not_a_crash(participant: Path) -> None:
    submitted(participant)
    (participant / "progress.yaml").write_text("attempts: [unclosed\n", encoding="utf-8")
    result = precheck.check(ROOT, participant, _files(participant))
    assert result.status == precheck.NEEDS_FIXES
    assert "Traceback" not in precheck.render_comment(result)


def test_a_decision_produces_one_new_comment_for_the_newest_review(participant: Path) -> None:
    submitted(participant)
    recorded = run(
        participant, "record-review", "--quest", REVIEWED, "--decision", "approved",
        "--reviewer", "A Reviewer", "--statement", STATEMENT,
    )  # fmt: skip
    assert recorded.returncode == 0, recorded.stderr
    result = precheck.check(ROOT, participant, _files(participant))
    assert result.status == precheck.REVIEWED
    comments = precheck.render_review_ready(result)
    assert len(comments) == 1
    review_id, body = comments[0]
    assert precheck.REVIEW_MARKER.format(review_id=review_id) in body
    assert "Check for my review" in body


def test_needs_changes_points_at_the_findings_in_the_app(participant: Path) -> None:
    submitted(participant)
    recorded = run(
        participant, "record-review", "--quest", REVIEWED, "--decision", "needs_changes",
        "--reviewer", "A Reviewer", "--finding", "high:Second run is missing:only one run in logs",
    )  # fmt: skip
    assert recorded.returncode == 0, recorded.stderr
    result = precheck.check(ROOT, participant, _files(participant))
    ((_, body),) = precheck.render_review_ready(result)
    assert "1 finding" in body
    assert "Resume after review" in body


def test_a_decision_is_not_announced_unless_reviews_are_trusted(participant: Path) -> None:
    """A review record is a file the participant can write too, so it proves nothing alone."""
    submitted(participant)
    recorded = run(
        participant, "record-review", "--quest", REVIEWED, "--decision", "approved",
        "--reviewer", "A Reviewer", "--statement", STATEMENT,
    )  # fmt: skip
    assert recorded.returncode == 0, recorded.stderr
    result = precheck.check(ROOT, participant, _files(participant), trust_reviews=False)
    assert result.decisions == []
    assert precheck.render_review_ready(result) == []
    assert result.label != "gtq:reviewed"


def test_text_from_the_pull_request_cannot_mention_or_link_in_the_comment(
    participant: Path,
) -> None:
    submitted(participant)
    files = [{"filename": "x`[click](http://evil)@some-team/y", "status": "added"}]
    comment = precheck.render_comment(precheck.check(ROOT, participant, files))
    assert "@some-team" not in comment
    assert "](http" not in comment
