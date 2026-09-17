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
from datetime import UTC, datetime
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
            inside = config.resolve_participant_path(evidence_path) / Path(item.path).name
        except ValueError:
            return "missing"
        if inside.is_file():
            return "detected"
    return "missing"


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
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(
            SecretFinding(
                path=f"{evidence_path}/{path.relative_to(root).as_posix()}",
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
    """A run identifier that sorts by time and cannot collide."""
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{validator_id}-{stamp}-{secrets.token_hex(3)}"


def store_result(config: AppConfig, evidence_path: str, document: dict[str, object]) -> str:
    """Write a validation result into the attempt's own evidence directory.

    The location is derived from the attempt, never from the document, so a record cannot
    place itself in someone else's package (Stage 2 audit M5).
    """
    directory = config.resolve_participant_path(evidence_path) / "validation"
    directory.mkdir(parents=True, exist_ok=True)
    run_id = str(document["run_id"])
    relative = f"{evidence_path}/validation/{run_id}.json"
    document["result_path"] = relative
    write_json_atomic(directory / f"{run_id}.json", document)
    return relative
