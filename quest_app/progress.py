"""Participant state: what the participant recorded, and what can be trusted about it.

`participant/progress.yaml` is written by the participant. It is theirs, it is in their Git
history, and they can edit it in any text editor. That is the point of a local-first,
repository-native design — and it is also why nothing here treats the file as authoritative
about anything a participant is not allowed to decide.

Specifically: a `verified` state and any verified XP are re-derived from review records, not
read from this file. An attempt that claims `verified` without a matching approval is an
integrity error, not a state (ADR-011).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from quest_app.config import AppConfig
from quest_app.errors import ContentProblem, ProblemReport, Severity
from quest_app.models import AttemptState

PROGRESS_FILENAME = "progress.yaml"
REVIEW_FILENAME = "review.yaml"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    id: str
    severity: str
    summary: str
    evidence: str
    required_change: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    review_id: str
    quest_id: str
    quest_version: int
    attempt_id: str
    evidence_hash: str
    reviewer_display_name: str
    reviewed_at: str
    decision: str
    findings: tuple[ReviewFinding, ...]
    source: str
    verification_statement: str | None = None
    validation_result_ids: tuple[str, ...] = ()
    reviewer_identity_reference: str | None = None

    @property
    def is_approval(self) -> bool:
        return self.decision == "approved"


@dataclass(frozen=True, slots=True)
class CheckResult:
    id: str
    outcome: str
    summary: str
    severity: str | None = None
    evidence: str | None = None
    suggested_action: str | None = None
    artifact: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    run_id: str
    validator_id: str
    validator_version: int
    quest_id: str
    attempt_id: str
    started_at: str
    completed_at: str
    duration_ms: int
    outcome: str
    checks: tuple[CheckResult, ...]
    redaction_applied: bool
    source: str
    environment: dict[str, Any] = field(default_factory=dict)
    output_excerpt: str | None = None
    output_truncated: bool = False
    result_path: str | None = None

    @property
    def qualifies(self) -> bool:
        """Whether this run counts towards `locally_validated`.

        `warning` qualifies: `VALIDATOR-CONTRACT.md` defines it as "core checks passed but
        material advisories remain", which is a pass with something to read. Everything else
        — fail, environment failure, inconclusive, interrupted — does not, and notably
        `inconclusive` is not treated as a pass, because "we could not tell" is not evidence.
        """
        return self.outcome in ("pass", "warning")


@dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: str
    quest_id: str
    quest_version: int
    content_hash: str
    recorded_state: AttemptState
    started_at: str
    updated_at: str
    evidence_path: str
    validation_result_ids: tuple[str, ...] = ()
    submission_id: str | None = None
    review_id: str | None = None


@dataclass(frozen=True, slots=True)
class ParticipantProgress:
    schema_version: int
    participant_id: str
    display_name: str
    selected_track: str
    attempts: tuple[Attempt, ...]
    source: str
    focus_tags: tuple[str, ...] = ()
    session_capacity_minutes: int | None = None
    updated_at: str | None = None

    def attempt_for(self, quest_id: str) -> Attempt | None:
        """The most recently updated attempt for a quest.

        The schema permits several, because a participant may retry after `needs_changes`.
        Sorting by `updated_at` then `attempt_id` keeps the answer stable when two records
        share a timestamp.
        """
        candidates = [a for a in self.attempts if a.quest_id == quest_id]
        if not candidates:
            return None
        return max(candidates, key=lambda a: (a.updated_at, a.attempt_id))


@dataclass(frozen=True, slots=True)
class ParticipantState:
    """Everything read from the participant's tree, already cross-checked."""

    progress: ParticipantProgress
    reviews: dict[str, ReviewDecision]
    validations: dict[str, tuple[ValidationResult, ...]]

    def latest_review_for(self, attempt: Attempt) -> ReviewDecision | None:
        review = self.reviews.get(attempt.review_id) if attempt.review_id else None
        if review is None or review.attempt_id != attempt.attempt_id:
            return None
        return review

    def results_for(self, attempt: Attempt) -> tuple[ValidationResult, ...]:
        return self.validations.get(attempt.attempt_id, ())


def load_participant_state(
    config: AppConfig, schemas: Any, report: ProblemReport
) -> ParticipantState | None:
    """Read progress, then every review and validation record its attempts point at.

    Records are read from inside the attempt's own evidence directory. Nothing scans the
    whole participant tree, so a stray file somewhere else can never become a review.
    """
    from quest_app.content_loader import read_yaml

    progress_path = config.participant_root / PROGRESS_FILENAME
    if not progress_path.exists():
        report.add(
            ContentProblem(
                code="progress.missing",
                severity=Severity.ERROR,
                public_message="No participant progress file was found.",
                source=f"participant/{PROGRESS_FILENAME}",
                expected="participant/progress.yaml",
                suggestion="Start a quest, or copy the starter file from the setup guide.",
            )
        )
        return None

    relative = f"participant/{PROGRESS_FILENAME}"
    data = read_yaml(progress_path, config, report)
    if data is None:
        return None
    if not schemas.validate("progress", data, relative, report):
        return None

    progress = _build_progress(data, relative)
    reviews: dict[str, ReviewDecision] = {}
    validations: dict[str, list[ValidationResult]] = {}

    for attempt in progress.attempts:
        try:
            evidence_dir = config.resolve_participant_path(attempt.evidence_path)
        except ValueError as exc:
            report.add(
                ContentProblem.build(
                    code="progress.unsafe_evidence_path",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} has an evidence path that is not allowed."
                    ),
                    source=relative,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].evidence_path",
                    expected=(
                        "a path under participant/evidence/ with no parent-directory segments"
                    ),
                    # Never `str(exc)`: the resolver's message quotes the offending path,
                    # which for an absolute one would put it in front of a browser.
                    received=type(exc).__name__,
                )
            )
            continue
        if not evidence_dir.exists():
            report.add(
                ContentProblem.build(
                    code="progress.missing_evidence_directory",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} points at an evidence directory that is "
                        "not there."
                    ),
                    source=relative,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].evidence_path",
                    received=attempt.evidence_path,
                    suggestion="Restore the directory, or remove the attempt.",
                )
            )
            continue

        review_path = evidence_dir / REVIEW_FILENAME
        if review_path.exists():
            review = _load_review(review_path, config, schemas, report)
            if review is not None:
                reviews[review.review_id] = review
        # The submission and the superseded reviews are read by the reviewer's page and the
        # participant's history, so they are checked here too. Otherwise a file left broken by
        # a merge conflict passed `validate` and then stopped `build` with a traceback.
        records = [(evidence_dir / "submission.yaml", "submission")]
        records += [(path, "review") for path in sorted(evidence_dir.glob("review-*.yaml"))]
        for record_path, schema_name in records:
            if record_path.exists():
                data = read_yaml(record_path, config, report)
                if data is not None:
                    schemas.validate(schema_name, data, config.relative(record_path), report)

        for result_path in sorted((evidence_dir / "validation").glob("*.json")):
            result = _load_validation(result_path, config, schemas, report)
            if result is None:
                continue
            # Filed by the directory it was found in, never by the attempt_id inside it. A
            # record that disagrees with its own location is reported rather than quietly
            # re-filed: that is the path a forged local validation would take, and under
            # ADR-017 these records are what `locally_validated` is derived from
            # (Stage 2 audit M5).
            if result.attempt_id != attempt.attempt_id or result.quest_id != attempt.quest_id:
                report.add(
                    ContentProblem.build(
                        code="validation.record_in_wrong_place",
                        severity=Severity.ERROR,
                        public_message=(
                            "A validation result claims to belong to a different attempt "
                            "from the one whose evidence directory holds it."
                        ),
                        source=result.source,
                        entity_id=result.run_id,
                        field_path="attempt_id",
                        expected=f"attempt {attempt.attempt_id!r} of quest {attempt.quest_id!r}",
                        received=f"attempt {result.attempt_id!r} of quest {result.quest_id!r}",
                        suggestion="Move the file to the attempt it belongs to, or delete it.",
                    )
                )
                continue
            validations.setdefault(attempt.attempt_id, []).append(result)

    _check_integrity(progress, reviews, relative, report, config)

    return ParticipantState(
        progress=progress,
        reviews=reviews,
        validations={
            k: tuple(sorted(v, key=lambda r: (r.completed_at, r.run_id)))
            for k, v in validations.items()
        },
    )


def _build_progress(data: dict[str, Any], relative: str) -> ParticipantProgress:
    participant = data["participant"]
    attempts = tuple(
        Attempt(
            attempt_id=str(a["attempt_id"]),
            quest_id=str(a["quest_id"]),
            quest_version=int(a["quest_version"]),
            content_hash=str(a["content_hash"]),
            recorded_state=AttemptState(a["state"]),
            started_at=str(a["started_at"]),
            updated_at=str(a["updated_at"]),
            evidence_path=str(a["evidence_path"]),
            validation_result_ids=tuple(a.get("validation_result_ids", [])),
            submission_id=a.get("submission_id"),
            review_id=a.get("review_id"),
        )
        for a in data["attempts"]
    )
    return ParticipantProgress(
        schema_version=int(data["schema_version"]),
        participant_id=str(participant["id"]),
        display_name=str(participant["display_name"]),
        selected_track=str(data["selected_track"]),
        attempts=attempts,
        source=relative,
        focus_tags=tuple(data.get("focus_tags", [])),
        session_capacity_minutes=data.get("session_capacity_minutes"),
        updated_at=data.get("updated_at"),
    )


def _load_review(
    path: Path, config: AppConfig, schemas: Any, report: ProblemReport
) -> ReviewDecision | None:
    from quest_app.content_loader import read_yaml

    relative = config.relative(path)
    data = read_yaml(path, config, report)
    if data is None or not schemas.validate("review", data, relative, report):
        return None
    reviewer = data["reviewer"]
    return ReviewDecision(
        review_id=str(data["review_id"]),
        quest_id=str(data["quest_id"]),
        quest_version=int(data["quest_version"]),
        attempt_id=str(data["attempt_id"]),
        evidence_hash=str(data["evidence_hash"]),
        reviewer_display_name=str(reviewer["display_name"]),
        reviewed_at=str(data["reviewed_at"]),
        decision=str(data["decision"]),
        findings=tuple(
            ReviewFinding(
                id=str(f["id"]),
                severity=str(f["severity"]),
                summary=str(f["summary"]),
                evidence=str(f["evidence"]),
                required_change=f.get("required_change"),
            )
            for f in data["findings"]
        ),
        source=relative,
        verification_statement=data.get("verification_statement"),
        validation_result_ids=tuple(data.get("validation_result_ids", [])),
        reviewer_identity_reference=reviewer.get("identity_reference"),
    )


def _load_validation(
    path: Path, config: AppConfig, schemas: Any, report: ProblemReport
) -> ValidationResult | None:
    relative = config.relative(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.add(
            ContentProblem.build(
                code="validation.invalid_json",
                severity=Severity.ERROR,
                public_message="A validation result file is not valid JSON.",
                source=relative,
                line=exc.lineno,
                column=exc.colno,
                received=exc.msg,
            )
        )
        return None
    except (OSError, UnicodeDecodeError) as exc:
        # Never str(exc): it embeds an absolute path (Stage 2 audit H5).
        detail = exc.strerror if isinstance(exc, OSError) else exc.reason
        report.add(
            ContentProblem.build(
                code="validation.unreadable",
                severity=Severity.ERROR,
                public_message="A validation result file could not be read.",
                source=relative,
                received=detail or "unknown error",
            )
        )
        return None
    if not isinstance(data, dict):
        return None
    # A warning, not an error. This is one file inside a participant's own evidence. A
    # malformed one should say so and be ignored, not stop the whole site from loading and
    # then blame the curriculum for a file the participant's own tooling wrote.
    scratch = ProblemReport()
    if not schemas.validate("validation-result", data, relative, scratch):
        report.add(
            ContentProblem.build(
                code="validation.unusable_result",
                severity=Severity.WARNING,
                public_message=(
                    "A validation result could not be read and has been ignored. Delete it "
                    "and run the check again."
                ),
                source=relative,
                received="; ".join(problem.public_message for problem in scratch.errors[:2]),
            )
        )
        return None
    return ValidationResult(
        run_id=str(data["run_id"]),
        validator_id=str(data["validator_id"]),
        validator_version=int(data["validator_version"]),
        quest_id=str(data["quest_id"]),
        attempt_id=str(data["attempt_id"]),
        started_at=str(data["started_at"]),
        completed_at=str(data["completed_at"]),
        duration_ms=int(data["duration_ms"]),
        outcome=str(data["outcome"]),
        checks=tuple(
            CheckResult(
                id=str(c["id"]),
                outcome=str(c["outcome"]),
                summary=str(c["summary"]),
                severity=c.get("severity"),
                evidence=c.get("evidence"),
                suggested_action=c.get("suggested_action"),
                artifact=c.get("artifact"),
            )
            for c in data["checks"]
        ),
        redaction_applied=bool(data["redaction_applied"]),
        source=relative,
        environment=data.get("environment", {}),
        output_excerpt=data.get("output_excerpt"),
        output_truncated=bool(data.get("output_truncated", False)),
        result_path=data.get("result_path"),
    )


def _check_stale_approval(
    attempt: Attempt,
    review: ReviewDecision,
    config: AppConfig,
    relative: str,
    report: ProblemReport,
) -> None:
    """Warn when the evidence differs from what the reviewer approved.

    `record_decision` compares hashes at the moment of the decision, which says nothing
    about what happens afterwards. Without this, rewriting `PROOF.md` on an approved
    attempt kept `verified` and its XP with no signal at all — and so did editing the
    review's own `evidence_hash`.

    A warning, not an error: `CONTENT-MODEL.md` keeps verified attempts verified unless a
    documented policy revokes them. The job here is to make it visible.
    """
    from quest_app.evidence import evidence_hash

    current = evidence_hash(config, attempt.evidence_path)
    if current is None or current == review.evidence_hash:
        return
    report.add(
        ContentProblem.build(
            code="progress.evidence_changed_since_approval",
            severity=Severity.WARNING,
            public_message=(
                f"The evidence for attempt {attempt.attempt_id!r} has changed since it was "
                "approved, so the approval may no longer describe it."
            ),
            source=relative,
            entity_id=attempt.attempt_id,
            field_path="attempts[].evidence_path",
            expected=review.evidence_hash,
            received=current,
            suggestion=(
                "The approval stands until a reviewer revokes it. Ask for re-review if the "
                "change was material."
            ),
        )
    )


def _check_integrity(
    progress: ParticipantProgress,
    reviews: dict[str, ReviewDecision],
    relative: str,
    report: ProblemReport,
    config: AppConfig | None = None,
) -> None:
    """The rules that stop a participant record claiming authority it does not have."""
    seen_attempt_ids: set[str] = set()
    for attempt in progress.attempts:
        if attempt.attempt_id in seen_attempt_ids:
            report.add(
                ContentProblem(
                    code="progress.duplicate_attempt_id",
                    severity=Severity.ERROR,
                    public_message=f"Attempt ID {attempt.attempt_id!r} is used more than once.",
                    source=relative,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].attempt_id",
                    expected="a unique attempt ID",
                )
            )
        seen_attempt_ids.add(attempt.attempt_id)

        if _timestamps_out_of_order(attempt.started_at, attempt.updated_at):
            report.add(
                ContentProblem.build(
                    code="progress.timestamps_out_of_order",
                    severity=Severity.WARNING,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} was updated before it was started."
                    ),
                    source=relative,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].updated_at",
                    received=attempt.updated_at,
                )
            )

        if attempt.recorded_state is not AttemptState.VERIFIED:
            continue

        # A verified state is only ever the shadow of an approval. Everything below is the
        # check that the approval actually exists and actually belongs to this attempt.
        review = reviews.get(attempt.review_id) if attempt.review_id else None
        if attempt.review_id is None:
            problem = "the attempt is marked verified but names no review"
        elif review is None:
            problem = (
                f"review {attempt.review_id!r} was not found in the attempt's evidence directory"
            )
        elif review.attempt_id != attempt.attempt_id:
            problem = (
                f"review {review.review_id!r} approves attempt {review.attempt_id!r}, not this one"
            )
        elif not review.is_approval:
            problem = f"review {review.review_id!r} records {review.decision!r}, not an approval"
        elif not review.verification_statement:
            problem = f"review {review.review_id!r} approves without a verification statement"
        elif review.quest_version != attempt.quest_version:
            problem = (
                f"review {review.review_id!r} approves version {review.quest_version} of the "
                f"quest, but this attempt is on version {attempt.quest_version}"
            )
        elif review.quest_id != attempt.quest_id:
            problem = (
                f"review {review.review_id!r} is for quest {review.quest_id!r}, not "
                f"{attempt.quest_id!r}"
            )
        else:
            # The approval is consistent. Whether it still describes the evidence is a
            # separate question, and one nothing asked before this.
            if config is not None:
                _check_stale_approval(attempt, review, config, relative, report)
            continue

        report.add(
            ContentProblem(
                code="progress.unverified_verified_state",
                severity=Severity.ERROR,
                public_message=(
                    f"Attempt {attempt.attempt_id!r} claims verified completion, but {problem}."
                ),
                source=relative,
                entity_id=attempt.attempt_id,
                field_path="attempts[].state",
                expected="a matching approved review with a verification statement",
                suggestion=(
                    "Only a reviewer approval produces verified completion and verified XP. "
                    "Set the state back to 'submitted' and ask for review."
                ),
            )
        )


def _timestamps_out_of_order(started: str, updated: str) -> bool:
    try:
        return datetime.fromisoformat(updated) < datetime.fromisoformat(started)
    except ValueError:
        return False
