"""Evidence: detecting what proof exists, scanning it, and recording validation runs.

Proof detection answers one question per requirement — is this artifact there, and does it
look like what the quest asked for? It deliberately does not judge quality; that is what
validators and reviewers are for.

The secret scan is a gate rather than a report. `docs/SECURITY-AND-PRIVACY.md` requires it
before submission preparation, and the reason is asymmetric: a false positive costs a
participant a minute, and a missed credential costs them a rotation and a conversation.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from quest_app.config import AppConfig
from quest_app.hashing import hash_directory, hash_file, resolves_inside
from quest_app.models import ProofRequirement, Quest
from quest_app.progress import REVIEW_ARCHIVE_GLOBS, ValidationResult
from quest_app.safe_io import (
    MAX_EVIDENCE_FILE_BYTES,
    MAX_VALIDATION_RESULT_BYTES,
    UnsafeStateFileError,
    read_bounded_bytes,
)
from quest_app.secret_patterns import scan_text
from quest_app.store import write_json_atomic

OUTSIDE_LINK_DESCRIPTION = "is a link that leads outside the evidence package"
OVERSIZE_DESCRIPTION = (
    f"is larger than the {MAX_EVIDENCE_FILE_BYTES // 1_000_000} MB the secret scan reads, "
    "so it cannot be checked"
)


def scan_kinds(findings: list[SecretFinding]) -> frozenset[str]:
    """Which kinds of problem a scan found: `secret`, `link` or `oversize`.

    The three fail the scan alike but need different words. A page that called a link or an
    unreadably large file "secret-like" sent people looking for a credential that was never
    there (round 12 C3).
    """
    kinds = {
        "link"
        if f.description == OUTSIDE_LINK_DESCRIPTION
        else "oversize"
        if f.description == OVERSIZE_DESCRIPTION
        else "secret"
        for f in findings
    }
    return frozenset(kinds)


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


def _scan_one(path: Path, relative: str, boundary: Path) -> list[SecretFinding]:
    """Apply the fixed scan rules to one filesystem entry: link check, skip list, the 2 MB
    ceiling, then decode and match.

    `boundary` is the root a link may not resolve outside of. For an evidence package that
    is the package itself; for a declared proof path that legitimately lives elsewhere in
    the tree (`participant/context/**`, `participant/skills/**`) it is `participant/` as a
    whole, since those locations are not inside any one package (round 13 C1).
    """
    # A link out of the boundary was skipped, so the scan vouched for a file it never read
    # while the build rendered whatever the link led to. It is now a finding: the scan
    # cannot clear what it may not read, and nothing renders through it.
    if not resolves_inside(path, boundary):
        return [SecretFinding(relative, 1, OUTSIDE_LINK_DESCRIPTION)]
    if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
        return []
    try:
        raw = read_bounded_bytes(path, max_bytes=MAX_EVIDENCE_FILE_BYTES)
    except UnsafeStateFileError:
        # Over the ceiling, or swapped for something that is not a file since `is_file`.
        # Either way the scan did not read it, so it cannot vouch for it: a finding that
        # blocks submission and says why, rather than a minute of pattern matching on
        # every build while the locks are held (round 12 E8).
        return [SecretFinding(relative, 1, OVERSIZE_DESCRIPTION)]
    except OSError:
        # A file the scan cannot read is a file it cannot vouch for, so it blocks.
        return [SecretFinding(relative, 1, "could not be read to check it")]
    # Decoded with replacement, not skipped: one byte that is not UTF-8 used to hide an
    # entire file, credentials included, from the scan.
    text = raw.decode("utf-8", errors="replace")
    return [
        SecretFinding(path=relative, line=match.line, description=match.description)
        for match in scan_text(text)
    ]


def scan_evidence(config: AppConfig, evidence_path: str) -> list[SecretFinding]:
    """Every secret-like value in an evidence package.

    Uses `scan_text` directly, not the repository scanner, so a participant cannot switch
    the check off by writing an allow pragma into their own evidence.

    This covers only the package. A quest's declared proof commonly names files outside it
    (`participant/context/**`, `participant/skills/**`); `scan_declared_proof` covers those
    too and is what every gate and page must call (round 13 C1).
    """
    try:
        root = config.resolve_participant_path(evidence_path)
    except ValueError:
        return []
    findings: list[SecretFinding] = []
    for path in sorted(root.rglob("*")):
        relative = f"{evidence_path}/{path.relative_to(root).as_posix()}"
        findings.extend(_scan_one(path, relative, root))
    return findings


def scan_declared_proof(config: AppConfig, quest: Quest, evidence_path: str) -> list[SecretFinding]:
    """`scan_evidence`'s findings, plus the same scan over every declared proof path outside
    the package.

    `proof_paths_outside_package` already lists exactly those paths for change detection;
    round 13 C1 found that the secret scan never looked at them, so a token planted in
    `participant/context/**` or `participant/skills/**` passed every gate and every page
    said the evidence was clean. This is the function every gate and page must call instead
    of `scan_evidence` alone.
    """
    findings = list(scan_evidence(config, evidence_path))
    boundary = config.participant_root.resolve()
    for declared in proof_paths_outside_package(quest, evidence_path):
        try:
            target = config.resolve_participant_path(declared)
        except ValueError:
            continue
        if not target.exists():
            continue
        if target.is_file():
            findings.extend(_scan_one(target, declared, boundary))
            continue
        for path in sorted(target.rglob("*")):
            relative = f"{declared}/{path.relative_to(target).as_posix()}"
            findings.extend(_scan_one(path, relative, boundary))
    return findings


def describe_scan_findings(findings: list[SecretFinding]) -> list[str]:
    """Participant-facing problem sentences, one per kind of scan finding present.

    `secret`, `link` and `oversize` all fail the same gate but are not the same problem.
    `readiness_problems` (submission) and `_require_clean_secret_scan` (mark-evidence-ready)
    used to word this differently, and the earlier of the two called a link or an oversized
    file "secret-like" (round 13 C2). Both now share this one function instead of
    duplicating the text.
    """
    problems: list[str] = []
    links = [f for f in findings if f.description == OUTSIDE_LINK_DESCRIPTION]
    oversize = [f for f in findings if f.description == OVERSIZE_DESCRIPTION]
    secret = [f for f in findings if f not in links and f not in oversize]
    if links:
        # Not a secret, and saying "secret-like" would send the participant hunting for one.
        problems.append(
            f"{links[0].path} is a link that leads outside the evidence package, so it cannot "
            "be checked or shown. Replace it with a copy of the file."
        )
    if oversize:
        # Not a secret either: a file too large for the scan to read (round 12 E8).
        problems.append(
            f"{oversize[0].path} {OVERSIZE_DESCRIPTION}. Trim it, or keep the full file out "
            "of the evidence and include only the part that shows the result."
        )
    if secret:
        problems.append(
            f"Something secret-like is in the evidence ({secret[0].path}:{secret[0].line})."
        )
    return problems


def links_outside_package(config: AppConfig, evidence_path: str) -> list[str]:
    """Every entry in the package that, once links are followed, lands outside it.

    The package is the approved root for evidence. Render, hash and scan all refuse to read
    through such an entry, and the loader reports it, so none of the three can disagree
    about what the evidence contains.
    """
    try:
        root = config.resolve_participant_path(evidence_path)
    except ValueError:
        return []
    if not root.is_dir():
        return []
    return [
        f"{evidence_path}/{path.relative_to(root).as_posix()}"
        for path in sorted(root.rglob("*"))
        if not resolves_inside(path, root)
    ]


def package_file(config: AppConfig, evidence_path: str, name: str) -> Path | None:
    """A file in the package by name, or None when it is absent or leads outside it."""
    try:
        root = config.resolve_participant_path(evidence_path)
    except ValueError:
        return None
    path = root / name
    if not resolves_inside(path, root) or not path.is_file():
        return None
    return path


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
        # Exactly the review records the loader checks (`progress.review_archive_paths`). The
        # looser `review-*.yaml` also hid a participant's own `review-notes.yaml` from it.
        skip_globs=("submission.yaml", "review.yaml", *REVIEW_ARCHIVE_GLOBS),
    )


# Proof types that name a path. The others are checked by a validator or a person.
PATH_PROOF_TYPES = frozenset({"file", "directory", "screenshot", "command-record"})
MISSING_DIGEST = "missing"
UNRESOLVABLE_DIGEST = "unresolvable"


def proof_paths_outside_package(quest: Quest, evidence_path: str) -> tuple[str, ...]:
    """The declared proof paths, required and optional, that the evidence hash cannot see.

    Every quest's proof names files outside the attempt's package — a test in
    `participant/tests/`, a document in `participant/context/` — and `evidence_hash` covers
    only the package, so editing one of them after submission or approval changed nothing
    anyone was told about. A path under the quest's own evidence area is left out: it is
    the authored `attempt-001` form that `_inside_the_package` maps into the package, which
    the evidence hash already covers.
    """
    quest_area = str(Path(evidence_path).parent).replace("\\", "/") + "/"
    paths = {
        item.path.replace("\\", "/")
        for item in quest.proof
        if item.path and item.type in PATH_PROOF_TYPES
    }
    return tuple(sorted(path for path in paths if not path.startswith(quest_area)))


def proof_file_digests(
    config: AppConfig, paths: tuple[str, ...] | list[str]
) -> list[dict[str, str]]:
    """What each proof path holds now, as `{path, digest}` records.

    Resolution goes through `resolve_participant_path`, which follows links and refuses
    anything that lands outside `participant/`, so a path that does is recorded as
    `unresolvable` and its target is never read. A path with nothing at it is `missing`,
    so a file appearing or disappearing is a change like any other.
    """
    records: list[dict[str, str]] = []
    for path in sorted(set(paths)):
        try:
            target = config.resolve_participant_path(path)
        except ValueError:
            records.append({"path": path, "digest": UNRESOLVABLE_DIGEST})
            continue
        try:
            if target.is_file():
                digest = hash_file(target)
            elif target.is_dir():
                digest = hash_directory(target)
            else:
                digest = MISSING_DIGEST
        except OSError:
            digest = UNRESOLVABLE_DIGEST
        records.append({"path": path, "digest": digest})
    return records


def changed_proof_files(config: AppConfig, recorded: object) -> list[str]:
    """The recorded proof paths whose contents differ from what was recorded.

    A record written before proof files were recorded has no such field, and that is not
    evidence of anything: it compares nothing rather than reading as changed or forged.
    """
    if not isinstance(recorded, list):
        return []
    expected = {
        str(item["path"]): str(item["digest"])
        for item in recorded
        if isinstance(item, dict) and "path" in item and "digest" in item
    }
    current = {item["path"]: item["digest"] for item in proof_file_digests(config, list(expected))}
    return [path for path, digest in sorted(expected.items()) if current.get(path) != digest]


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

    # The lexical path, walked without following a link: a `validation/` directory that is
    # a link out of the tree used to receive the result, and the loader then read it back
    # (round 12 E1). `write_json_atomic` refuses it, and every other link below the root.
    directory = config.participant_write_path(evidence_path) / "validation"
    run_id = str(document["run_id"])
    relative = f"{evidence_path}/validation/{run_id}.json"
    document["result_path"] = relative
    # The loader reads a result only up to this ceiling, so one over it would be written and
    # then ignored. Refusing it here says so while the run is still in front of the caller.
    size = len(json.dumps(document, indent=2, sort_keys=True).encode("utf-8"))
    if size > MAX_VALIDATION_RESULT_BYTES:
        raise ResultRejectedError(
            f"the validator produced a result of {size} bytes, over the "
            f"{MAX_VALIDATION_RESULT_BYTES} byte limit for a stored result"
        )
    write_json_atomic(config.participant_root, directory / f"{run_id}.json", document)
    return relative
