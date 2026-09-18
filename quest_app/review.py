"""Submission and review: the only path to verified completion.

Everything here exists to keep one boundary intact. A participant assembles evidence and
asks for review. A reviewer decides. Nothing a participant does, and nothing a validator
returns, can produce `verified` or verified XP (ADR-011).

The submission record is what makes "has this changed since I reviewed it?" answerable. It
captures the evidence hash at the moment of submission, so a reviewer opening the page later
is told plainly whether they are looking at what was submitted.

**Provenance limitation, stated because it must be visible.** Release one identifies a
reviewer by the display name in the review record and by Git history. It does not use
cryptographic signing, so a participant with write access to their own repository could
author a review record naming someone else. What the application *can* do, and does, is
refuse every internally inconsistent claim: a review that does not match the attempt, an
approval with no verification statement, a `verified` state with no approval behind it. The
remaining gap is social and is documented rather than papered over.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from quest_app.config import AppConfig
from quest_app.evidence import evidence_hash, scan_evidence
from quest_app.models import AttemptState, Decision, Quest
from quest_app.progress import Attempt, ParticipantState, ReviewDecision
from quest_app.store import ProgressStore, append_audit, atomic_write_text

SUBMISSION_FILENAME = "submission.yaml"
REVIEW_FILENAME = "review.yaml"


class ReviewError(RuntimeError):
    """A review that cannot be recorded, with a reason a reviewer can act on."""


@dataclass(frozen=True, slots=True)
class SubmissionRecord:
    submission_id: str
    quest_id: str
    quest_version: int
    attempt_id: str
    content_hash: str
    evidence_hash: str
    submitted_at: str
    submitted_by: str
    secret_scan_clean: bool
    validation_result_ids: tuple[str, ...] = ()
    note: str | None = None
    reproduction: str | None = None

    def to_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": 1,
            "submission_id": self.submission_id,
            "quest_id": self.quest_id,
            "quest_version": self.quest_version,
            "attempt_id": self.attempt_id,
            "content_hash": self.content_hash,
            "evidence_hash": self.evidence_hash,
            "submitted_at": self.submitted_at,
            "submitted_by": self.submitted_by,
            "secret_scan_clean": self.secret_scan_clean,
        }
        if self.validation_result_ids:
            document["validation_result_ids"] = list(self.validation_result_ids)
        if self.note:
            document["note"] = self.note
        if self.reproduction:
            document["reproduction"] = self.reproduction
        return document


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def readiness_problems(
    quest: Quest, attempt: Attempt, participant: ParticipantState, config: AppConfig
) -> list[str]:
    """Everything standing between this attempt and a reviewable submission.

    Returned as a list rather than raised one at a time, because a participant should see
    all of it at once rather than discovering it in sequence.
    """
    problems: list[str] = []
    if attempt.recorded_state not in (AttemptState.EVIDENCE_READY, AttemptState.LOCALLY_VALIDATED):
        problems.append(
            f"The attempt is {attempt.recorded_state.value!r}; mark the evidence ready first."
        )

    findings = scan_evidence(config, attempt.evidence_path)
    if findings:
        problems.append(
            f"Something secret-like is in the evidence ({findings[0].path}:{findings[0].line})."
        )

    if evidence_hash(config, attempt.evidence_path) is None:
        problems.append("The evidence directory is missing.")

    results = participant.results_for(attempt)
    latest = {result.validator_id: result for result in results}
    for validator_id in quest.validators:
        result = latest.get(validator_id)
        if result is None:
            # An advisory, not a blocker: policy may permit submitting with a validator
            # unrun, and the reviewer sees that it was not run.
            problems.append(f"advisory: {validator_id} has not been run.")
        elif not result.qualifies:
            problems.append(
                f"advisory: {validator_id} last returned {result.outcome.replace('_', ' ')}."
            )
    return problems


def blocking(problems: list[str]) -> list[str]:
    return [problem for problem in problems if not problem.startswith("advisory:")]


def create_submission(
    config: AppConfig,
    store: ProgressStore,
    *,
    quest: Quest,
    attempt: Attempt,
    participant: ParticipantState,
    schemas: Any,
    note: str | None = None,
) -> SubmissionRecord:
    """Record a submission and move the attempt to `submitted`."""
    from quest_app.store import no_guard, transition_attempt

    problems = readiness_problems(quest, attempt, participant, config)
    if blocking(problems):
        raise ReviewError("; ".join(blocking(problems)))

    digest = evidence_hash(config, attempt.evidence_path)
    if digest is None:
        raise ReviewError("The evidence directory could not be hashed.")

    record = SubmissionRecord(
        submission_id=f"submission-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}",
        quest_id=quest.id,
        quest_version=quest.version,
        attempt_id=attempt.attempt_id,
        content_hash=quest.content_hash,
        evidence_hash=digest,
        submitted_at=_now(),
        submitted_by=participant.progress.display_name,
        secret_scan_clean=True,
        validation_result_ids=tuple(result.run_id for result in participant.results_for(attempt)),
        note=note,
    )

    directory = config.resolve_participant_path(attempt.evidence_path)
    _write_yaml(directory / SUBMISSION_FILENAME, record.to_document(), schemas, "submission")

    transition_attempt(
        store, quest_id=quest.id, action="submit-for-review", schemas=schemas, guard=no_guard
    )
    _record_submission_id(store, quest.id, record.submission_id, schemas)
    append_audit(config, f"Submitted {quest.id} for review as {record.submission_id}.")
    return record


def _record_submission_id(
    store: ProgressStore, quest_id: str, submission_id: str, schemas: Any
) -> None:
    data = store.read()
    attempts = [a for a in data["attempts"] if a["quest_id"] == quest_id]
    attempt = max(attempts, key=lambda a: (a["updated_at"], a["attempt_id"]))
    attempt["submission_id"] = submission_id
    store.write(data, schemas)


def record_decision(
    config: AppConfig,
    store: ProgressStore,
    *,
    quest: Quest,
    attempt: Attempt,
    participant: ParticipantState,
    decision: str,
    reviewer_name: str,
    verification_statement: str | None,
    findings: list[dict[str, str]],
    schemas: Any,
    acknowledge_changed_evidence: bool = False,
) -> ReviewDecision:
    """Record a reviewer's decision, refusing every incomplete or inconsistent form.

    The guards are the product requirement. An approval without a statement is a formality
    wearing the clothes of a judgment; a needs-changes without a finding tells a participant
    nothing; and approving evidence that changed since submission approves something the
    reviewer has not seen.
    """
    if decision not in {member.value for member in Decision}:
        allowed = ", ".join(member.value for member in Decision)
        raise ReviewError(f"{decision!r} is not a decision. Use one of: {allowed}.")

    if attempt.recorded_state is not AttemptState.SUBMITTED:
        raise ReviewError(
            f"Only a submitted attempt can be decided; this one is "
            f"{attempt.recorded_state.value!r}."
        )

    if decision == Decision.APPROVED:
        if not verification_statement or len(verification_statement.strip()) < 20:
            raise ReviewError(
                "Approval requires a verification statement saying what you checked and how."
            )
        if evidence_changed(config, attempt) and not acknowledge_changed_evidence:
            raise ReviewError(
                "The evidence has changed since it was submitted. Re-read it and acknowledge "
                "the change before approving."
            )
    elif not findings:
        raise ReviewError(
            f"{decision.replace('_', ' ').capitalize()} requires at least one finding, so the "
            "participant knows what to do."
        )

    digest = evidence_hash(config, attempt.evidence_path) or "sha256:" + "0" * 64
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    document = {
        "schema_version": 1,
        "review_id": f"review-{stamp}-{secrets.token_hex(3)}",
        "quest_id": quest.id,
        "quest_version": quest.version,
        "attempt_id": attempt.attempt_id,
        "evidence_hash": digest,
        "reviewer": {"display_name": reviewer_name},
        "reviewed_at": _now(),
        "decision": decision,
        "findings": findings,
    }
    if verification_statement:
        document["verification_statement"] = verification_statement.strip()
    results = participant.results_for(attempt)
    if results:
        document["validation_result_ids"] = [result.run_id for result in results]

    directory = config.resolve_participant_path(attempt.evidence_path)
    _write_yaml(directory / REVIEW_FILENAME, document, schemas, "review")

    _apply_decision(store, quest.id, str(document["review_id"]), decision, schemas)
    append_audit(config, f"Review of {quest.id}: {decision} by {reviewer_name}.")

    from quest_app.progress import ReviewFinding

    return ReviewDecision(
        review_id=str(document["review_id"]),
        quest_id=quest.id,
        quest_version=quest.version,
        attempt_id=attempt.attempt_id,
        evidence_hash=digest,
        reviewer_display_name=reviewer_name,
        reviewed_at=str(document["reviewed_at"]),
        decision=decision,
        findings=tuple(
            ReviewFinding(
                id=finding["id"],
                severity=finding["severity"],
                summary=finding["summary"],
                evidence=finding["evidence"],
                required_change=finding.get("required_change"),
            )
            for finding in findings
        ),
        source=f"{attempt.evidence_path}/{REVIEW_FILENAME}",
        verification_statement=verification_statement,
    )


def _apply_decision(
    store: ProgressStore, quest_id: str, review_id: str, decision: str, schemas: Any
) -> None:
    """Move the attempt to the state the decision implies.

    This is the one place a `verified` state is ever written, and it writes it only as the
    consequence of an approval it has just validated.
    """
    data = store.read()
    attempts = [a for a in data["attempts"] if a["quest_id"] == quest_id]
    attempt = max(attempts, key=lambda a: (a["updated_at"], a["attempt_id"]))
    attempt["review_id"] = review_id
    attempt["state"] = {
        "approved": AttemptState.VERIFIED.value,
        "needs_changes": AttemptState.NEEDS_CHANGES.value,
        "rejected": AttemptState.NEEDS_CHANGES.value,
    }[decision]
    attempt["updated_at"] = _now()
    data["updated_at"] = attempt["updated_at"]
    store.write(data, schemas)


def evidence_changed(config: AppConfig, attempt: Attempt) -> bool:
    """Whether the evidence differs from what the submission recorded."""
    submission = read_submission(config, attempt)
    if submission is None:
        return False
    current = evidence_hash(config, attempt.evidence_path)
    return current is not None and current != submission.get("evidence_hash")


def read_submission(config: AppConfig, attempt: Attempt) -> dict[str, Any] | None:
    from quest_app.yaml_loader import strict_safe_load

    try:
        path = config.resolve_participant_path(attempt.evidence_path) / SUBMISSION_FILENAME
    except ValueError:
        return None
    if not path.exists():
        return None
    data = strict_safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def review_history(config: AppConfig, attempt: Attempt) -> list[dict[str, Any]]:
    """Every review recorded for this attempt, oldest first.

    Release one keeps the current decision in `review.yaml` and archives superseded ones
    beside it, so a participant can see that a reviewer changed their mind rather than only
    the outcome.
    """
    from quest_app.yaml_loader import strict_safe_load

    try:
        directory = config.resolve_participant_path(attempt.evidence_path)
    except ValueError:
        return []
    history: list[dict[str, Any]] = []
    for path in sorted(directory.glob("review*.yaml")):
        data = strict_safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            history.append(data)
    return sorted(history, key=lambda item: str(item.get("reviewed_at", "")))


def _write_yaml(path: Path, document: dict[str, Any], schemas: Any, schema_name: str) -> None:
    """Validate against the published schema before writing, never after."""
    from quest_app.errors import ProblemReport

    report = ProblemReport()
    if not schemas.validate(schema_name, document, path.name, report):
        raise ReviewError(
            "The record would not validate: "
            + "; ".join(problem.public_message for problem in report.errors[:3])
        )
    # A superseded decision is archived rather than overwritten, so history survives.
    if path.exists() and schema_name == "review":
        archive = path.with_name(
            f"review-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.yaml"
        )
        archive.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    atomic_write_text(path, yaml.safe_dump(document, sort_keys=False, allow_unicode=True))


def submission_instructions(quest_id: str, attempt_id: str, branch: str | None) -> str:
    """What the participant does next, in their own terminal.

    The application never pushes, never opens a pull request and never merges. Those are
    claims on the participant's behalf about work being finished, and they are the
    participant's to make.
    """
    branch_name = branch or f"evidence/{quest_id}"
    return (
        f"git switch -c {branch_name}\n"
        f"git add participant/evidence/{quest_id}/{attempt_id} participant/progress.yaml\n"
        f'git commit -m "Evidence for {quest_id} ({attempt_id})"\n'
        f"git push -u origin {branch_name}\n"
        "gh pr create --fill   # or open the pull request in your browser"
    )
