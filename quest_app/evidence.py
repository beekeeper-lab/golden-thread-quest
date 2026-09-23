"""Evidence: detecting what proof exists, scanning it, and recording validation runs.

Proof detection answers one question per requirement — is this artifact there, and does it
look like what the quest asked for? It deliberately does not judge quality; that is what
validators and reviewers are for.

The secret scan is a gate rather than a report. `docs/SECURITY-AND-PRIVACY.md` requires it
before submission preparation, and the reason is asymmetric: a false positive costs a
participant a minute, and a missed credential costs them a rotation and a conversation.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from quest_app.config import AppConfig
from quest_app.hashing import hash_directory
from quest_app.models import ProofRequirement, Quest
from quest_app.progress import ValidationResult
from quest_app.secret_patterns import scan_text
from quest_app.store import write_json_atomic

SKIP_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip"})


@dataclass(frozen=True, slots=True)
class SecretFinding:
    path: str
    line: int
    description: str


def detect_proof(
    quest: Quest,
    config: AppConfig,
    evidence_path: str | None,
    results: tuple[ValidationResult, ...],
) -> dict[str, str]:
    """Current detection state per proof requirement ID.

    States are the ones `COMPONENT-CATALOG.md` C11 defines. `validated` is only ever reached
    through a qualifying validator result — detection alone never claims it.
    """
    states: dict[str, str] = {}
    latest = {result.validator_id: result for result in results}

    for item in quest.proof:
        states[item.id] = _detect_one(item, config, evidence_path, latest)
    return states


def _detect_one(
    item: ProofRequirement,
    config: AppConfig,
    evidence_path: str | None,
    latest: dict[str, ValidationResult],
) -> str:
    if item.type == "validator":
        result = latest.get(item.validator or "")
        if result is None:
            return "missing"
        if result.qualifies:
            return "validated"
        return "warning" if result.outcome in ("inconclusive", "environment_failure") else "missing"

    if item.type == "review":
        return "missing"

    if item.type == "demonstration":
        # A live demonstration cannot be detected from the filesystem, and pretending
        # otherwise would let a checkbox stand in for a person watching someone work.
        return "missing"

    if item.path is None:
        return "missing"

    try:
        target = config.resolve_participant_path(item.path)
    except ValueError:
        return "missing"

    if item.type == "directory":
        return "detected" if target.is_dir() and any(target.iterdir()) else "missing"
    if target.is_file():
        return "detected" if target.stat().st_size > 0 else "warning"

    # A file may also live inside the attempt's own evidence package.
    if evidence_path:
        try:
            package = config.resolve_participant_path(evidence_path)
        except ValueError:
            return "missing"
        for candidate in _inside_the_package(item.path, evidence_path, package):
            if candidate.is_file():
                return "detected"
    return "missing"


def _inside_the_package(item_path: str, evidence_path: str, package: Path) -> list[Path]:
    """Where an authored proof path can land inside the attempt the participant really has.

    An authored path names an attempt directory the author had to invent — every quest
    writes `attempt-001` — while `_next_attempt_id` produces `<prefix>-attempt-001`, so the
    literal path never exists. The fallback then looked only for the bare filename directly
    under the package, and every such path in the curriculum points into `logs/` or
    `screenshots/`: the very subdirectories `_create_evidence_package` creates and the
    quests tell participants to use. A participant who followed the instructions saw
    "Not detected" for a file that was sitting where they were told to put it.

    So the authored path is re-read against the real package: the part after the author's
    attempt directory is kept whole, which preserves the subdirectory the quest asked for
    rather than accepting the file anywhere.
    """
    candidates = [package / Path(item_path).name]
    quest_area = str(Path(evidence_path).parent).replace("\\", "/") + "/"
    normalized = item_path.replace("\\", "/")
    if normalized.startswith(quest_area):
        remainder = Path(normalized[len(quest_area) :]).parts
        if len(remainder) > 1:
            candidates.insert(0, package.joinpath(*remainder[1:]))
    return candidates


def scan_evidence(config: AppConfig, evidence_path: str) -> list[SecretFinding]:
    """Every secret-like value in an evidence package.

    Uses `scan_text` directly, not the repository scanner, so a participant cannot switch
    the check off by writing an allow pragma into their own evidence.
    """
    try:
        root = config.resolve_participant_path(evidence_path)
    except ValueError:
        return []
    findings: list[SecretFinding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES or path.is_symlink():
            continue
        relative = f"{evidence_path}/{path.relative_to(root).as_posix()}"
        try:
            raw = path.read_bytes()
        except OSError:
            # A file the scan cannot read is a file it cannot vouch for, so it blocks.
            findings.append(SecretFinding(relative, 1, "could not be read to check it"))
            continue
        # Decoded with replacement, not skipped: one byte that is not UTF-8 used to hide an
        # entire file, credentials included, from the scan.
        text = raw.decode("utf-8", errors="replace")
        findings.extend(
            SecretFinding(
                path=relative,
                line=match.line,
                description=match.description,
            )
            for match in scan_text(text)
        )
    return findings


def evidence_hash(config: AppConfig, evidence_path: str) -> str | None:
    """A hash over an evidence package, for detecting change after review.

    It covers the participant's *work*, not the records the application writes about that
    work. The validation directory is excluded because a re-run writes a new result with a
    new timestamp, and the submission and review records are excluded because writing them
    would otherwise change the very hash they had just recorded — which made a freshly
    submitted attempt read as "changed since submission" the moment it was submitted.
    """
    try:
        root = config.resolve_participant_path(evidence_path)
    except ValueError:
        return None
    if not root.is_dir():
        return None
    return hash_directory(
        root,
        skip_names=frozenset({"validation"}),
        skip_globs=("submission.yaml", "review.yaml", "review-*.yaml"),
    )


def new_run_id(validator_id: str) -> str:
    """A run identifier that sorts by time and cannot collide.

    Microseconds, because results are ordered by `(completed_at, run_id)` and `completed_at`
    has one-second resolution: with a seconds-only stamp, two runs in the same second were
    ordered by the random suffix, and an earlier pass could stand as the latest result over
    the fail that followed it.
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{validator_id}-{stamp}-{secrets.token_hex(3)}"


class ResultRejectedError(ValueError):
    """A validation result that would not load back. It is refused rather than written."""


def store_result(
    config: AppConfig,
    evidence_path: str,
    document: dict[str, object],
    schemas: object | None = None,
) -> str:
    """Write a validation result into the attempt's own evidence directory.

    The location is derived from the attempt, never from the document, so a record cannot
    place itself in someone else's package (Stage 2 audit M5).

    Validated before it is written, like every other write in this application. This was the
    one place that was not, and it cost an outage: a timed-out validator produced an empty
    check list, the schema forbids that, and the invalid document then made the whole site
    refuse to load — blaming the curriculum for a file in the participant's own evidence.
    """
    if schemas is not None:
        from quest_app.errors import ProblemReport

        report = ProblemReport()
        if not schemas.validate(  # type: ignore[attr-defined]
            "validation-result", document, "validation-result", report
        ):
            raise ResultRejectedError(
                "the validator produced a result that could not be stored: "
                + "; ".join(problem.public_message for problem in report.errors[:3])
            )

    directory = config.resolve_participant_path(evidence_path) / "validation"
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(document["run_id"])
    relative = f"{evidence_path}/validation/{run_id}.json"
    document["result_path"] = relative
    write_json_atomic(directory / f"{run_id}.json", document)
    return relative
