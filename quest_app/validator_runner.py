"""Running a registered validator, under every constraint the contract names.

The guarantees, and how each one is actually obtained:

* **no shell** — the validator is a Python callable named in the registry, imported by an
  exact allowlisted module path. There is no argument string anywhere, so there is nothing
  for a metacharacter to escape from;
* **explicit roots** — the validator receives a `Workspace` whose `read` and `write` methods
  canonicalise a path and re-check it inside the registered roots *after* symlinks are
  followed. It never receives a bare path;
* **constructed environment** — `os.environ` is not inherited. The child's environment is
  built from the registry's allowlist plus a minimal `PATH`;
* **timeout with process-tree cleanup** — the run happens in a child process in its own
  process group, and a timeout kills the group, not just the child;
* **bounded output** — captured output is truncated at the registered limit and marked;
* **redaction before persistence** — output passes through the same detectors the repository
  scanner uses before it is written or displayed.

An interrupted run produces an `interrupted` result. It never produces a pass or a fail,
because "we did not finish" is not evidence either way.
"""

from __future__ import annotations

import contextlib
import errno
import importlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quest_app.config import AppConfig
from quest_app.secret_patterns import redact_text
from quest_app.validator_registry import ValidatorDefinition, ValidatorError

# The only modules a registry entry may name. The schema already constrains the shape;
# this constrains the package, so a future registry edit cannot import something else.
ALLOWED_ENTRYPOINT_PACKAGE = "validators"

# A minimal environment. Anything a validator needs beyond this is named in its allowlist.
BASE_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}

OUTCOMES = ("pass", "fail", "warning", "environment_failure", "inconclusive", "interrupted")

# `output_excerpt` is capped at this in `schemas/validation-result.schema.json`, and a result
# that breaks the schema is refused whole — so a chatty validator that passed had its entire
# run thrown away with a message about a rejected document. The registry let an author
# declare five times this and nothing reconciled the two numbers.
# `tests/unit/test_validator_limits.py` fails if the schema and this constant drift apart.
EXCERPT_LIMIT = 20000

# Nothing bounded the list. Twenty thousand checks produced a 9.7 MB result document that
# every later page render read back in full.
MAX_CHECKS = 200

# `$defs.check`'s `outcome` enum in `schemas/validation-result.schema.json`. Deliberately
# separate from `OUTCOMES` above, which is the *run's* outcome: a single check cannot be
# `environment_failure` or `interrupted` — those describe why the whole run could not
# reach a verdict, not what one check found. A validator's process only promises JSON; it
# does not promise a value from this set, and `outcome="passed"` (not `pass`) or
# `outcome=None` used to fall through `classify()`'s set-membership checks and read as a
# pass (round 12, E6).
CHECK_OUTCOMES = ("pass", "fail", "warning", "skipped", "inconclusive")

# `$defs.id` in the same schema, which every check's `id` must match, exactly like a
# validator or quest ID does everywhere else in this application.
CHECK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CHECK_ID_MAX_LENGTH = 120

# `$defs.check`'s `maxLength` for each free-text field. Nothing enforced these before round
# 12's E6: a field over its limit did not shrink the check, it broke the document — the
# same failure mode `EXCERPT_LIMIT` exists to prevent for `output_excerpt`, and
# `evidence.store_result` refuses to write a document that does not fit, a passing run
# included.
CHECK_FIELD_LIMITS = {
    "summary": 500,
    "evidence": 4000,
    "suggested_action": 1000,
    "artifact": 300,
}


class WorkspaceError(RuntimeError):
    """A path a validator asked for that is outside the roots it was registered with."""


@dataclass(frozen=True, slots=True)
class Check:
    """One thing a validator established. `evidence` is what it actually observed."""

    id: str
    outcome: str
    summary: str
    severity: str | None = None
    evidence: str | None = None
    suggested_action: str | None = None
    artifact: str | None = None


@dataclass(slots=True)
class ValidatorOutput:
    """What a validator returns. It classifies its own checks; the runner classifies the run."""

    checks: list[Check] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    environment_failure: str | None = None

    def add(self, check: Check) -> None:
        self.checks.append(check)

    def note(self, text: str) -> None:
        self.notes.append(text)

    def fail_environment(self, reason: str) -> None:
        """Say that the validator could not evaluate the work, rather than that it failed."""
        self.environment_failure = reason


@dataclass(frozen=True, slots=True)
class Workspace:
    """The only way a validator touches the filesystem.

    Every call canonicalises and then re-checks containment, so a symbolic link planted
    inside a read root cannot be used to read outside it.
    """

    read_roots: tuple[Path, ...]
    write_roots: tuple[Path, ...]
    repo_root: Path
    participant_root: Path
    parameters: dict[str, Any]
    evidence_root: Path | None = None
    """The evidence package of the attempt being validated, when there is one.

    Without it a validator has no way to tell one attempt's evidence from another's, and
    round 6's checks reached for `participant/evidence` and judged whichever file was
    newest: a blank `PROOF.md` under an unrelated quest failed a complete one, and a log
    left behind by any other quest satisfied "failure is diagnosable" for this one. Records
    are connected by their identifiers, never by modification time.
    """

    def _contained(self, path: Path, roots: tuple[Path, ...], what: str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            # A validator writes `participant/...`, which is the contract path, not
            # necessarily the location. It follows the configured participant root, exactly
            # as every other participant path does (ADR-018).
            parts = candidate.parts
            if parts and parts[0] == "participant":
                candidate = self.participant_root.joinpath(*parts[1:])
            else:
                candidate = self.repo_root / candidate
        resolved = candidate.resolve()
        for root in roots:
            if resolved == root or root in resolved.parents:
                return resolved
        raise WorkspaceError(f"{what} is not permitted outside the registered roots")

    def exists(self, path: str) -> bool:
        try:
            return self._contained(Path(path), self.read_roots, "reading").exists()
        except WorkspaceError:
            return False

    def read_text(self, path: str, *, limit: int = 1_000_000) -> str:
        target = self._contained(Path(path), self.read_roots, "reading")
        if not target.is_file():
            raise WorkspaceError("no such file inside the registered read roots")
        return target.read_text(encoding="utf-8", errors="replace")[:limit]

    def iter_files(self, path: str, pattern: str = "*") -> list[Path]:
        root = self._contained(Path(path), self.read_roots, "reading")
        if not root.is_dir():
            return []
        return sorted(
            item for item in root.rglob(pattern) if item.is_file() and self._is_readable(item)
        )

    def attempt_files(self, pattern: str = "*") -> list[Path]:
        """Every readable file inside the evidence package of the attempt under validation.

        A check about this attempt's evidence uses this rather than `iter_files`, so its
        verdict cannot be decided by a file belonging to another quest or another attempt.
        """
        if self.evidence_root is None:
            return []
        try:
            root = self._contained(self.evidence_root, self.read_roots, "reading")
        except WorkspaceError:
            return []
        if not root.is_dir():
            return []
        return sorted(
            item for item in root.rglob(pattern) if item.is_file() and self._is_readable(item)
        )

    def _is_readable(self, item: Path) -> bool:
        try:
            self._contained(item, self.read_roots, "reading")
        except WorkspaceError:
            return False
        return True

    def write_text(self, path: str, text: str) -> None:
        target = self._contained(Path(path), self.write_roots, "writing")
        target.parent.mkdir(parents=True, exist_ok=True)
        # `_contained` resolved every link, so what is left to refuse is a special file at
        # the resolved name: a FIFO there blocked the validator until its timeout (round 12
        # E1). Never blocks, never truncates anything but a regular file.
        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
        try:
            descriptor = os.open(target, flags, 0o666)
        except OSError as exc:
            if exc.errno not in (errno.ELOOP, errno.ENXIO, errno.EISDIR):
                raise
            raise WorkspaceError("writing is only permitted to an ordinary file") from exc
        with os.fdopen(descriptor, "wb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise WorkspaceError("writing is only permitted to an ordinary file")
            stream.truncate(0)
            stream.write(text.encode("utf-8"))

    def relative(self, path: Path) -> str:
        """A label for a finding: repository-relative, or participant-relative, never absolute."""
        for root, prefix in ((self.repo_root, ""), (self.participant_root, "participant/")):
            try:
                return prefix + path.relative_to(root).as_posix()
            except ValueError:
                continue
        return path.name


@dataclass(frozen=True, slots=True)
class RunResult:
    """One completed run, ready to be written as a validation-result document."""

    run_id: str
    validator_id: str
    validator_version: int
    quest_id: str
    attempt_id: str
    started_at: str
    completed_at: str
    duration_ms: int
    outcome: str
    checks: tuple[Check, ...]
    output_excerpt: str
    output_truncated: bool
    redaction_applied: bool
    environment: dict[str, Any]

    def to_document(self, result_path: str | None = None) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema_version": 1,
            "run_id": self.run_id,
            "validator_id": self.validator_id,
            "validator_version": self.validator_version,
            "quest_id": self.quest_id,
            "attempt_id": self.attempt_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "outcome": self.outcome,
            "environment": self.environment,
            "checks": [
                {key: value for key, value in asdict(check).items() if value is not None}
                for check in self.checks
            ],
            "redaction_applied": self.redaction_applied,
        }
        if self.output_excerpt:
            document["output_excerpt"] = self.output_excerpt
            document["output_truncated"] = self.output_truncated
        if result_path:
            document["result_path"] = result_path
        return document


def classify(output: ValidatorOutput) -> str:
    """Turn a validator's checks into one outcome for the run.

    `inconclusive` is deliberately not a pass: "we could not tell" is not evidence, and
    letting it qualify would be the quietest possible way to make `locally_validated`
    meaningless.
    """
    if output.environment_failure:
        return "environment_failure"
    if not output.checks:
        return "inconclusive"
    outcomes = {check.outcome for check in output.checks}
    if "fail" in outcomes:
        return "fail"
    if "inconclusive" in outcomes:
        return "inconclusive"
    if "warning" in outcomes:
        return "warning"
    if outcomes <= {"skipped"}:
        # Every check stood aside, so nothing was checked. That is not evidence either.
        return "inconclusive"
    return "pass"


def _apply_check_limit(checks: list[Check]) -> list[Check]:
    """Cap a run's checks at `MAX_CHECKS`, and say how many were dropped.

    `quest_app.validator_child` applies this before it serializes its result, so a
    validator that reports far more than the schema allows never produces a document large
    enough to trip `STREAM_LIMIT` before this limit had a chance to apply. Twenty thousand
    checks made a document past the 1 MiB ceiling on either stream, and the run was thrown
    away whole as `environment_failure` — the truncation this function exists for was
    never reached.

    Applied again here for whatever else reaches the runner. Doing it twice is harmless: a
    list already at or under the cap is returned unchanged, and one that already ends with
    this exact marker — because the child already applied it — is recognised and left
    alone rather than truncated a second time.
    """
    if len(checks) <= MAX_CHECKS:
        return checks
    if len(checks) == MAX_CHECKS + 1 and checks[-1].id == "checks-truncated":
        return checks
    dropped = len(checks) - MAX_CHECKS
    limited = checks[:MAX_CHECKS]
    limited.append(
        Check(
            id="checks-truncated",
            outcome="warning",
            summary=f"{dropped} further check(s) were dropped; this run reported too many.",
            severity="medium",
            suggested_action="A validator that reports this much detail should summarize it.",
        )
    )
    return limited


def _sanitize_checks(raw_checks: Any) -> tuple[list[Check], bool]:
    """Turn what a validator's process reported into checks that fit the schema.

    The process only promises to speak JSON on its result channel; nothing enforces that
    what is inside is the shape `docs/VALIDATOR-CONTRACT.md` describes. Before round 12's
    E6, `Check(**entry)` trusted every entry outright: an `id` that did not match the
    schema's pattern, an `outcome` outside its enum (`"passed"`, `None`, anything else a
    hostile or merely buggy validator wrote), or a check missing its required `summary`
    reached `classify()` unchanged, which read an unrecognised outcome as a pass and made
    `store_result` refuse the whole document for one bad entry — a passing run's verdict
    thrown away with it.

    Each entry here is checked against exactly the constraints the schema states. One that
    fails is not patched; it is replaced outright with a check of our own that says a
    check was malformed and why, so nothing the validator claimed for it survives.

    Returns the sanitized checks and whether any entry needed replacing. A validator that
    broke its own contract this way has a defect in itself, not in the participant's
    work — the same principle already applied to a nonzero exit and an uncaught exception
    — so the caller forces the run's outcome to `environment_failure` rather than letting
    a replaced check's own (necessarily non-`pass`) outcome decide it through `classify()`.
    """
    if not isinstance(raw_checks, list):
        return [], bool(raw_checks)
    checks: list[Check] = []
    any_malformed = False
    for index, entry in enumerate(raw_checks):
        check, valid = _sanitize_check(entry, index)
        checks.append(check)
        any_malformed = any_malformed or not valid
    return checks, any_malformed


def _sanitize_check(entry: Any, index: int) -> tuple[Check, bool]:
    """One raw entry from the child, validated against `$defs.check`'s id and outcome.

    Field lengths are handled later, uniformly for every check regardless of validity,
    alongside redaction (see `run_validator`) — truncation is not a reason to discard a
    check, only a missing summary or a value outside the id/outcome constraints is.
    """
    check_id = entry.get("id") if isinstance(entry, dict) else None
    outcome = entry.get("outcome") if isinstance(entry, dict) else None
    summary = entry.get("summary") if isinstance(entry, dict) else None
    valid = (
        isinstance(entry, dict)
        and isinstance(check_id, str)
        and len(check_id) <= CHECK_ID_MAX_LENGTH
        and CHECK_ID_PATTERN.match(check_id) is not None
        and isinstance(outcome, str)
        and outcome in CHECK_OUTCOMES
        and isinstance(summary, str)
        and summary != ""
    )
    if not valid:
        evidence = (
            f"It reported id={check_id!r}, outcome={outcome!r}."
            if isinstance(entry, dict)
            else f"Entry {index + 1} of the reported checks was not a check object."
        )
        return (
            Check(
                id=f"malformed-check-{index + 1}",
                # Not `fail`: that would blame the participant's work for a defect in the
                # validator. Not `pass` or `skipped`: `classify()` must never read this as
                # a verdict. `inconclusive` is the closest schema-legal value to "we could
                # not tell what this was" — `run_validator` also forces the run's own
                # outcome to `environment_failure` so this is never mistaken for the
                # ordinary "insufficient evidence" case a validator reports on purpose.
                outcome="inconclusive",
                severity="information",
                summary="A check this validator reported did not fit the result schema.",
                evidence=evidence,
                suggested_action=(
                    "This is a defect in the validator, not in your work; report it so the "
                    "check can be fixed."
                ),
            ),
            False,
        )
    fields: dict[str, Any] = {"id": check_id, "outcome": outcome}
    for name in ("summary", "evidence", "suggested_action", "artifact"):
        value = entry.get(name)
        fields[name] = value if isinstance(value, str) else None
    severity = entry.get("severity")
    fields["severity"] = severity if isinstance(severity, str) else None
    return Check(**fields), True


def _import_entrypoint(entrypoint: str) -> Any:
    module_path, _, attribute = entrypoint.partition(":")
    if not module_path.startswith(f"{ALLOWED_ENTRYPOINT_PACKAGE}.") or not attribute:
        raise ValidatorError(f"{entrypoint!r} is not an allowed validator entrypoint.")
    module = importlib.import_module(module_path)
    function = getattr(module, attribute, None)
    if function is None or not callable(function):
        raise ValidatorError(f"{entrypoint!r} does not name a callable.")
    return function


def run_validator(
    definition: ValidatorDefinition,
    config: AppConfig,
    *,
    quest_id: str,
    attempt_id: str,
    run_id: str,
    parameters: dict[str, Any] | None = None,
    evidence_path: str | None = None,
) -> RunResult:
    """Run one registered validator under every registered constraint."""
    if not definition.may_run_for(quest_id):
        raise ValidatorError(f"{definition.id!r} is not registered to run for {quest_id!r}.")

    bound = definition.bind_parameters(parameters)
    # The attempt's own evidence package. The caller passes the path the attempt recorded;
    # the default is the one `store.start_attempt` builds from the same two identifiers.
    declared_evidence = evidence_path or f"participant/evidence/{quest_id}/{attempt_id}"
    try:
        evidence_root: Path | None = config.resolve_participant_path(declared_evidence)
    except ValueError:
        evidence_root = None
    workspace = Workspace(
        read_roots=definition.resolved_read_roots(config),
        write_roots=definition.resolved_write_roots(config),
        repo_root=config.repo_root,
        participant_root=config.participant_root,
        parameters=bound,
        evidence_root=evidence_root,
    )

    started = datetime.now(timezone.utc)
    start_monotonic = time.monotonic()

    # The environment is constructed, never inherited: a validator cannot read a credential
    # that happens to be exported in the shell that started the service.
    environment = dict(BASE_ENVIRONMENT)
    for name in definition.environment_allowlist:
        if name in os.environ:
            environment[name] = os.environ[name]
    # The child runs in the validator's declared working directory, which is usually
    # participant-owned. `python -m` would put that directory first on the import path, so
    # a participant's `validators/` package or `json.py` would replace the registered code.
    # `CHILD_BOOTSTRAP` puts the repository there instead, and `-s` drops the user's site
    # directory; nothing else is on the path.

    # A fresh interpreter started as a subprocess, not a `multiprocessing` child of any
    # start method. `fork` from the threaded service would inherit locks held by other
    # threads, and `spawn` re-imports the parent's `__main__`, which fails whenever the
    # parent was not started from an importable file. A plain `-m quest_app.validator_child`
    # inherits neither problem, and the specification below is everything it is told.
    #
    # The comment this replaces described `forkserver` and survived the change to a
    # subprocess, so a reader checking how a validator is isolated was told the wrong
    # mechanism by the one comment written to explain it.
    specification = json.dumps(
        {
            "entrypoint": definition.entrypoint,
            "read_roots": [str(path) for path in workspace.read_roots],
            "write_roots": [str(path) for path in workspace.write_roots],
            "repo_root": str(workspace.repo_root),
            "participant_root": str(workspace.participant_root),
            "evidence_root": str(evidence_root) if evidence_root is not None else None,
            "parameters": bound,
        }
    )

    checks: list[Check] = []
    notes: list[str] = []
    environment_failure: str | None = None
    interrupted = False
    # One flag for the whole document, matching the schema's single `redaction_applied`
    # property. Set as soon as any field is redacted, wherever that happens below —
    # the stderr summary line, the excerpt, or a check's own text.
    redaction_applied = False

    # `start_new_session` puts the child in its own process group, so a timeout kills
    # anything it spawned rather than only the child itself.
    # `working_directory` is required by the registry schema, set on every entry, and
    # published in the validator contract — and until round 8 nothing applied it: the child
    # started in the repository root, so a validator following the contract resolved its
    # relative paths against the wrong tree.
    working_directory = definition.resolved_working_directory(config)
    if not working_directory.is_dir():
        # A participant who has run nothing yet has no participant directory. Creating it
        # is what the first action does in any case, and refusing to start the check is a
        # worse answer than starting it in an empty directory.
        working_directory.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-s", "-c", CHILD_BOOTSTRAP, str(config.repo_root)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(working_directory),
        env=environment,
        start_new_session=True,
    )
    # `start_new_session=True` calls `setsid()` before exec, which makes the child both a
    # new session leader and the leader of a new process group whose id equals its own pid.
    # Capturing that now, rather than reaching for `os.getpgid(process.pid)` later, is what
    # lets every kill below still find the group after the child itself has been reaped —
    # `getpgid` raises `ProcessLookupError` at exactly that point.
    pgid = process.pid
    captured = _collect(process, pgid, specification.encode("utf-8"), definition.timeout_seconds)
    stdout = captured.stdout.decode("utf-8", errors="replace")
    stderr = captured.stderr.decode("utf-8", errors="replace")
    if captured.timed_out:
        interrupted = True
        stdout, stderr = "", ""
    elif captured.overflowed:
        environment_failure = f"it wrote more than {STREAM_LIMIT} bytes of output and was stopped"
    else:
        # A nonzero exit is normally trusted over anything printed (`docs/VALIDATOR-
        # CONTRACT.md`: "exit status is not separable from the result"), *except* when we
        # are the ones who produced it: `captured.result_closed_early` means the child had
        # already written its result and returned — `validator_child.main()` closes the
        # result channel as its very last act before `return 0` — and something it left
        # running (round 12 E11: a non-daemon thread) kept the OS process alive past that
        # point. The signal-based return code that follows describes our own cleanup, not
        # a judgment the validator made about itself, so it must not discard a result that
        # was already complete.
        exit_is_self_reported = not captured.result_closed_early
        if (process.returncode != 0 and exit_is_self_reported) or not stdout.strip():
            environment_failure = (
                f"it exited with status {process.returncode} and produced no result"
            )
        else:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                environment_failure = "the validator produced output that could not be read"
            else:
                raw_checks = payload.get("checks") if isinstance(payload, dict) else None
                checks, checks_malformed = _sanitize_checks(raw_checks)
                raw_notes = payload.get("notes") if isinstance(payload, dict) else None
                notes = (
                    [note for note in raw_notes if isinstance(note, str)]
                    if isinstance(raw_notes, list)
                    else []
                )
                reported_failure = (
                    payload.get("environment_failure") if isinstance(payload, dict) else None
                )
                environment_failure = (
                    reported_failure if isinstance(reported_failure, str) else None
                )
                if checks_malformed and environment_failure is None:
                    # A defect in the validator's own output, not a fact about the
                    # participant's work — the same reasoning that already applies to an
                    # uncaught exception or a nonzero exit (round 12, E6).
                    environment_failure = (
                        "it reported a check outside its contract (an invalid outcome or id)"
                    )
                if not exit_is_self_reported:
                    notes.append(
                        "The validator's process did not exit on its own after writing its "
                        "result; the runner terminated it."
                    )
    if stderr.strip():
        notes.append(_redact_stderr(stderr))
        if environment_failure:
            # On a failure the first line of stderr is usually the cause, and it is far
            # more useful than the line count. Redacted before it is cut to length, never
            # after: truncating first can sever a secret-shaped token at the boundary, and
            # the half that survives no longer matches any detector's pattern (round 12,
            # E7). `_redact_paths` never reproduces a path verbatim for the same reason
            # `validator_child._safe_reason` scrubs one from an exception's message.
            last_line = stderr.strip().splitlines()[-1]
            scrubbed, line_redacted = redact_text(last_line)
            scrubbed = _redact_paths(scrubbed)
            bounded_line, _ = _bounded(scrubbed, 300, suffix=CHECK_TRUNCATION_SUFFIX)
            notes.append(f"Its last message was: {bounded_line}")
            redaction_applied = redaction_applied or line_redacted

    completed = datetime.now(timezone.utc)
    duration_ms = int((time.monotonic() - start_monotonic) * 1000)

    output = ValidatorOutput(
        checks=list(checks), notes=list(notes), environment_failure=environment_failure
    )
    if environment_failure:
        # Without this the outcome said "could not run" and the excerpt was empty, so the
        # participant was told a verdict with no cause.
        output.note(f"The validator could not run: {environment_failure}")

    if interrupted:
        outcome = "interrupted"
        output.note(
            f"The run exceeded its {definition.timeout_seconds}-second limit and was stopped."
        )
    else:
        outcome = classify(output)

    # A result always carries at least one check. The schema requires it, and more
    # importantly a run that says nothing is useless to the participant: "interrupted" with
    # an empty list gives them no idea what happened or what to do.
    if not output.checks:
        output.checks.append(_explaining_check(outcome, definition, environment_failure))

    output.checks = _apply_check_limit(output.checks)
    # Redacted before it is cut to the excerpt limit, never after: the previous order
    # truncated first, and a secret-shaped token cut in half at that boundary no longer
    # matches any detector's pattern, so it was stored in clear (round 12, E7). Redacting
    # the complete, untruncated text first means there is nothing left to sever by the
    # time truncation runs.
    joined_notes = "\n".join(output.notes)
    redacted_notes, notes_redacted = redact_text(joined_notes)
    redaction_applied = redaction_applied or notes_redacted
    excerpt, truncated = _bounded(redacted_notes, min(definition.max_output_bytes, EXCERPT_LIMIT))

    # Every free-text field a check carries, not only the captured output — redacted
    # first and truncated to its own schema `maxLength` second, for the same reason as
    # the excerpt above. Before round 12's E6 these fields were redacted but never
    # truncated at all: a check whose `summary`, `evidence`, `suggested_action` or
    # `artifact` field ran past its schema limit broke the document exactly like an
    # over-length `output_excerpt` did, and `evidence.store_result` refuses to write a
    # document that does not fit — a passing run's verdict thrown away with it.
    checks_out: list[Check] = []
    for check in output.checks:
        fields: dict[str, Any] = {}
        for name, limit in CHECK_FIELD_LIMITS.items():
            value = getattr(check, name)
            if not isinstance(value, str):
                continue
            cleaned, changed = redact_text(value)
            bounded_value, _ = _bounded(cleaned, limit, suffix=CHECK_TRUNCATION_SUFFIX)
            fields[name] = bounded_value
            redaction_applied = redaction_applied or changed
        checks_out.append(replace(check, **fields))

    return RunResult(
        run_id=run_id,
        validator_id=definition.id,
        validator_version=definition.version,
        quest_id=quest_id,
        attempt_id=attempt_id,
        started_at=started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        completed_at=completed.isoformat(timespec="seconds").replace("+00:00", "Z"),
        duration_ms=duration_ms,
        outcome=outcome,
        checks=tuple(checks_out),
        output_excerpt=excerpt,
        output_truncated=truncated,
        redaction_applied=redaction_applied,
        environment={"validator_version": definition.version, "network": definition.network},
    )


def _explaining_check(outcome: str, definition: ValidatorDefinition, reason: str | None) -> Check:
    """The one check a run that produced none still has to carry.

    It is the difference between a participant seeing "Interrupted" with nothing underneath
    and seeing what stopped, why, and what to do about it.
    """
    if outcome == "interrupted":
        return Check(
            id="validator-did-not-finish",
            outcome="inconclusive",
            severity="information",
            summary=f"{definition.display_name} did not finish within its time limit.",
            evidence=f"It was stopped after {definition.timeout_seconds} seconds.",
            suggested_action=(
                "This says nothing about your work either way. Run it again; if it keeps "
                "timing out, say so in your evidence and a reviewer can take it into account."
            ),
        )
    return Check(
        id="validator-could-not-run",
        outcome="inconclusive",
        severity="information",
        summary=f"{definition.display_name} could not evaluate your work.",
        evidence=reason or "No reason was reported.",
        suggested_action=(
            "This is a problem with the check or the environment, not with what you built."
        ),
    )


def _redact_stderr(text: str) -> str:
    """A child's stderr, summarized. Never reproduced: it may carry absolute paths."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return f"The validator wrote {len(lines)} line(s) to standard error."


_PATH_LIKE = re.compile(r"(?:/[^/\s'\"]+){2,}/?")


def _redact_paths(text: str) -> str:
    """Replace anything path-shaped, the same rule `validator_child._safe_reason` applies
    to an exception's message before it is written into a document a reviewer reads.
    """
    return _PATH_LIKE.sub("<path>", text)


TRUNCATION_SUFFIX = "\n… output truncated …"

# Used for a single-line field cut to a schema `maxLength` — a check's `summary`,
# `evidence`, `suggested_action` or `artifact`, or the one-line stderr excerpt appended on
# a failure. Shorter and inline, unlike `TRUNCATION_SUFFIX`, which is written for the much
# larger captured-output excerpt and starts with its own newline.
CHECK_TRUNCATION_SUFFIX = " …[truncated]"

# The ceiling on either stream of a child. Output is read as it arrives and the run is
# stopped when it passes this, so a validator cannot make the parent hold its output in
# memory. The result is a few kilobytes of JSON; a megabyte is far more than any needs.
STREAM_LIMIT = 1024 * 1024

# How the child starts. `-c` rather than `-m`, so the import path's first entry is ours to
# replace: the repository, never the working directory the validator runs in.
CHILD_BOOTSTRAP = (
    "import sys, runpy; sys.path[0] = sys.argv.pop(1); "
    "runpy.run_module('quest_app.validator_child', run_name='__main__', alter_sys=True)"
)


@dataclass
class _Captured:
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    overflowed: bool = False
    result_closed_early: bool = False
    """The child's result channel (its stdout) hit EOF while the OS process was still
    alive, rather than because the process itself had exited.

    `validator_child.main()` closes that channel as its very last act before returning, so
    this is a stronger completion signal than `process.poll()`: a non-daemon thread the
    validator left running can keep the process alive indefinitely past that point (round
    12, E11). When this is true, the nonzero return code `_terminate_tree` produces by
    killing the leftover process afterward describes our own cleanup, not a judgment the
    validator made about itself, and `run_validator` must not read it as a self-reported
    failure.

    Defaults `False`, the same as `docs/VALIDATOR-CONTRACT.md`'s ordinary rule that a
    nonzero exit is trusted "whatever it printed first": a code path that forgets to set
    this explicitly keeps that existing, deliberately strict behavior rather than silently
    granting every unrecognised case the E11 exemption.
    """


def _collect(process: subprocess.Popen[bytes], pgid: int, data: bytes, timeout: float) -> _Captured:
    """Feed the child its specification and read both streams under a byte ceiling.

    `communicate()` read everything into memory before any limit applied, and waited for the
    pipes to close rather than for the child to exit, so a grandchild holding a pipe open
    turned a finished pass into a timeout. Here the child's exit ends the run: whatever it
    left behind in its process group is killed, and what is already in the pipes is read.
    """
    import selectors

    assert process.stdin is not None and process.stdout is not None
    assert process.stderr is not None
    try:
        process.stdin.write(data)
        process.stdin.close()
    except (BrokenPipeError, OSError):
        pass

    buffers = {process.stdout: bytearray(), process.stderr: bytearray()}
    deadline = time.monotonic() + timeout
    captured = _Captured(b"", b"")
    with selectors.DefaultSelector() as selector:
        for stream in buffers:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
        exited_at: float | None = None
        # When the child's result channel (its stdout) closes before `process.poll()`
        # says the OS process has exited, this is when that happened — not yet treated
        # as an exit on its own, only a candidate for one, because the ordinary case
        # is this exact order: `validator_child.main()` closes its one reference to that
        # pipe a Python statement or two before the interpreter actually finishes tearing
        # down, so the parent routinely sees EOF a scheduler tick before `poll()` returns
        # non-`None` for a process that was going to exit on its own regardless. Reading
        # every EOF here as "something is stuck" made every ordinary run report one.
        stdout_closed_at: float | None = None
        while selector.get_map():
            now = time.monotonic()
            if exited_at is None and process.poll() is not None:
                exited_at = now
                # The child is done; anything it started is not part of the run.
                _kill_group(pgid)
            if exited_at is None and stdout_closed_at is not None and now - stdout_closed_at > 1:
                # A full second past the result channel closing with the process still
                # not reaped is long enough that this is not the ordinary scheduling gap
                # above: something the validator left running — round 12 E11's non-daemon
                # thread — is holding the interpreter open. Treat it like a self-reported
                # exit for cleanup (kill now, do not wait out the rest of the timeout for
                # a run whose result is already in hand), but record that we, not the
                # validator, ended it: the return code `_terminate_tree` is about to
                # produce describes our cleanup, not a verdict the validator passed on
                # itself.
                exited_at = now
                captured.result_closed_early = True
                _kill_group(pgid)
            if exited_at is not None and now - exited_at > 1:
                break
            if exited_at is None and now >= deadline:
                captured.timed_out = True
                break
            for key, _ in selector.select(timeout=0.1):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    if key.fileobj is process.stdout and stdout_closed_at is None:
                        stdout_closed_at = now
                    continue
                buffer = buffers[key.fileobj]  # type: ignore[index]
                buffer.extend(chunk)
                if len(buffer) > STREAM_LIMIT:
                    captured.overflowed = True
            if captured.overflowed:
                break
    _terminate_tree(process, pgid)
    for stream in buffers:
        with contextlib.suppress(OSError):
            stream.close()
    captured.stdout = bytes(buffers[process.stdout][:STREAM_LIMIT])
    captured.stderr = bytes(buffers[process.stderr][:STREAM_LIMIT])
    return captured


def _kill_group(pgid: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGKILL)


def _bounded(text: str, limit: int, suffix: str = TRUNCATION_SUFFIX) -> tuple[str, bool]:
    """Cap `text`, and say so rather than quietly losing the end of it.

    The notice is counted inside the budget. It used to be appended after truncating to
    the limit, so a validator registered at exactly the schema's cap produced an excerpt
    over it by the length of the notice, and the result was refused for being too long.

    `suffix` defaults to the multi-line marker used for the large captured-output
    excerpt; callers bounding a single-line schema field pass `CHECK_TRUNCATION_SUFFIX`
    instead. Callers are also expected to redact `text` before calling this, never after:
    cutting first can sever a secret-shaped token at the boundary, and the half that
    survives no longer matches any detector's pattern (round 12, E7).
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    room = max(limit - len(suffix.encode("utf-8")), 0)
    return encoded[:room].decode("utf-8", errors="ignore") + suffix, True


def _terminate_tree(process: subprocess.Popen[bytes], pgid: int) -> None:
    """Kill the whole process group, not just the child.

    A validator that spawned something of its own would otherwise survive its own timeout,
    which is how a "stopped" run keeps writing files. SIGTERM goes to the group first, so
    anything willing to clean up on its own gets the chance; then, always — regardless of
    whether the direct child has already exited — SIGKILL goes to the same group.

    "Always" is the fix: the previous version returned the moment `process.wait()` reaped
    the direct child, which is exactly what happens when the child dies of its own SIGTERM
    while a grandchild in the same group ignores it and keeps running. The SIGKILL that
    would have reached that grandchild was never sent, so it outlived the run.

    `pgid` is the id captured at spawn time, never `os.getpgid(process.pid)`: that call
    raises `ProcessLookupError` once the child has already been reaped, which is routinely
    true by the time this runs.
    """
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=3)
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGKILL)
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        process.wait(timeout=3)
