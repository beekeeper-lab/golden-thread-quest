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
import importlib
import json
import os
import signal
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

    def _is_readable(self, item: Path) -> bool:
        try:
            self._contained(item, self.read_roots, "reading")
        except WorkspaceError:
            return False
        return True

    def write_text(self, path: str, text: str) -> None:
        target = self._contained(Path(path), self.write_roots, "writing")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

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
    return "pass"


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
) -> RunResult:
    """Run one registered validator under every registered constraint."""
    if not definition.may_run_for(quest_id):
        raise ValidatorError(f"{definition.id!r} is not registered to run for {quest_id!r}.")

    bound = definition.bind_parameters(parameters)
    workspace = Workspace(
        read_roots=definition.resolved_read_roots(config),
        write_roots=definition.resolved_write_roots(config),
        repo_root=config.repo_root,
        participant_root=config.participant_root,
        parameters=bound,
    )

    started = datetime.now(timezone.utc)
    start_monotonic = time.monotonic()

    # The environment is constructed, never inherited: a validator cannot read a credential
    # that happens to be exported in the shell that started the service.
    environment = dict(BASE_ENVIRONMENT)
    for name in definition.environment_allowlist:
        if name in os.environ:
            environment[name] = os.environ[name]

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
            "parameters": bound,
        }
    )

    checks: list[Check] = []
    notes: list[str] = []
    environment_failure: str | None = None
    interrupted = False

    # `start_new_session` puts the child in its own process group, so a timeout kills
    # anything it spawned rather than only the child itself.
    process = subprocess.Popen(
        [sys.executable, "-m", "quest_app.validator_child"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(config.repo_root),
        env=environment,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(specification, timeout=definition.timeout_seconds)
    except subprocess.TimeoutExpired:
        interrupted = True
        _terminate_tree(process)
        stdout, stderr = "", ""
    else:
        if process.returncode != 0 or not stdout.strip():
            environment_failure = (
                f"it exited with status {process.returncode} and produced no result"
            )
        else:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                environment_failure = "the validator produced output that could not be read"
            else:
                checks = [Check(**entry) for entry in payload["checks"]]
                notes = list(payload["notes"])
                environment_failure = payload["environment_failure"]
        if stderr.strip():
            notes.append(_redact_stderr(stderr))
            if environment_failure:
                # On a failure the first line of stderr is usually the cause, and it is far
                # more useful than the line count. Redacted like any other captured output.
                notes.append(f"Its last message was: {stderr.strip().splitlines()[-1][:300]}")

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

    excerpt, truncated = _bounded("\n".join(output.notes), definition.max_output_bytes)
    redacted, redaction_applied = redact_text(excerpt)

    # Every free-text field a check carries, not only the captured output. The docstring at
    # the top of this module promised this and only the excerpt had it, so a check quoting a
    # token wrote it to disk verbatim.
    checks_out: list[Check] = []
    for check in output.checks:
        fields = {}
        for name in ("summary", "evidence", "suggested_action", "artifact"):
            value = getattr(check, name)
            if isinstance(value, str):
                cleaned, changed = redact_text(value)
                fields[name] = cleaned
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
        output_excerpt=redacted,
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


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    """Cap captured output, and say so rather than quietly losing the end of it."""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n… output truncated …", True


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    """Kill the whole process group, not just the child.

    A validator that spawned something of its own would otherwise survive its own timeout,
    which is how a "stopped" run keeps writing files.
    """
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            break
        try:
            process.wait(timeout=3)
            return
        except subprocess.TimeoutExpired:
            continue
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        process.kill()
        process.wait(timeout=3)
