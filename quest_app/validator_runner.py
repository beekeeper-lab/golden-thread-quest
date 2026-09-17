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

import importlib
import multiprocessing
import os
import signal
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
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


def _child(
    entrypoint: str, workspace: Workspace, pipe: Any
) -> None:  # pragma: no cover - subprocess
    """Run the validator in its own process group, reporting back over a pipe."""
    os.setsid()
    output = ValidatorOutput()
    try:
        _import_entrypoint(entrypoint)(workspace, output)
    except WorkspaceError as exc:
        output.fail_environment(f"the validator tried to leave its permitted paths: {exc}")
    except Exception as exc:
        output.fail_environment(f"the validator raised {type(exc).__name__}")
    pipe.send((output.checks, output.notes, output.environment_failure))
    pipe.close()


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

    started = datetime.now(UTC)
    start_monotonic = time.monotonic()

    # The environment is constructed, never inherited: a validator cannot read a credential
    # that happens to be exported in the shell that started the service.
    environment = dict(BASE_ENVIRONMENT)
    for name in definition.environment_allowlist:
        if name in os.environ:
            environment[name] = os.environ[name]

    # `forkserver`, not `fork` and not `spawn`. `fork` from the threaded service would
    # inherit locks held by other threads. `spawn` re-imports the parent's `__main__`,
    # which fails whenever the parent was not started from an importable file. `forkserver`
    # forks from a clean, single-threaded helper and inherits nothing of either problem.
    context: Any = multiprocessing.get_context(_start_method())
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(definition.entrypoint, workspace, sender))

    previous_environment = dict(os.environ)
    os.environ.clear()
    os.environ.update(environment)
    try:
        process.start()
    finally:
        os.environ.clear()
        os.environ.update(previous_environment)
    sender.close()

    checks: list[Check] = []
    notes: list[str] = []
    environment_failure: str | None = None
    interrupted = False

    if receiver.poll(definition.timeout_seconds):
        try:
            checks, notes, environment_failure = receiver.recv()
        except EOFError:
            # The child died before reporting. That is a defect in the validator or in the
            # environment, never a statement about the participant's work.
            environment_failure = "the validator exited without producing a result"
        process.join(timeout=5)
    else:
        interrupted = True
        _terminate_tree(process)

    receiver.close()
    if process.is_alive():  # pragma: no cover - only on a stubborn child
        _terminate_tree(process)

    completed = datetime.now(UTC)
    duration_ms = int((time.monotonic() - start_monotonic) * 1000)

    output = ValidatorOutput(
        checks=list(checks), notes=list(notes), environment_failure=environment_failure
    )
    if interrupted:
        outcome = "interrupted"
        output.note(
            f"The run exceeded its {definition.timeout_seconds}-second limit and was stopped."
        )
    else:
        outcome = classify(output)

    excerpt, truncated = _bounded("\n".join(output.notes), definition.max_output_bytes)
    redacted, redaction_applied = redact_text(excerpt)

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
        checks=tuple(output.checks),
        output_excerpt=redacted,
        output_truncated=truncated,
        redaction_applied=redaction_applied,
        environment={"validator_version": definition.version, "network": definition.network},
    )


def _start_method() -> str:
    """`forkserver` where it exists, `spawn` where it does not."""
    available = multiprocessing.get_all_start_methods()
    return "forkserver" if "forkserver" in available else "spawn"


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    """Cap captured output, and say so rather than quietly losing the end of it."""
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore") + "\n… output truncated …", True


def _terminate_tree(process: Any) -> None:
    """Kill the whole process group, not just the child.

    A validator that spawned something of its own would otherwise survive its own timeout,
    which is how a "stopped" run keeps writing files.
    """
    if process.pid is None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            break
        process.join(timeout=3)
        if not process.is_alive():
            return
