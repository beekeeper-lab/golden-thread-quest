"""Writing participant-owned files, safely.

Everything here writes inside `participant/` and nowhere else. Three properties matter:

* **atomic** — a write either happens completely or not at all, so an interrupted save
  cannot leave a participant with a half-written progress file and no way back;
* **validated before and after** — the file is parsed and schema-checked before it is
  replaced, because writing something the loader will later refuse would lock a participant
  out of their own work;
* **auditable** — every mutation appends a line the participant can read, because an
  application that edits your files should be able to tell you what it did.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from quest_app.config import AppConfig
from quest_app.models import AttemptState
from quest_app.state_machine import TransitionError, check
from quest_app.yaml_loader import strict_safe_load

PROGRESS_FILENAME = "progress.yaml"
# Never read as data and safe to delete; it exists only while a change is in flight.
LOCK_FILENAME = ".progress.lock"
AUDIT_FILENAME = "ACTIVITY.md"
EVIDENCE_TEMPLATE_DIRECTORIES = ("validation", "screenshots", "logs")


class StoreError(RuntimeError):
    """A write that could not be performed, with a participant-facing reason."""


def atomic_write_text(path: Path, text: str) -> None:
    """Replace `path` with `text`, or leave it exactly as it was.

    The temporary file is created in the same directory so the final `os.replace` is a
    same-filesystem rename, which is atomic. Writing to a temporary directory and moving
    across filesystems is not, and that is the case that loses data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            # fsync before the rename: without it a crash can leave the rename durable and
            # the contents not, which is the one failure mode atomic writing exists to stop.
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


@dataclass(frozen=True, slots=True)
class ProgressStore:
    """Read-modify-write access to `participant/progress.yaml`."""

    config: AppConfig

    @property
    def path(self) -> Path:
        return self.config.participant_root / PROGRESS_FILENAME

    @property
    def lock_path(self) -> Path:
        return self.config.participant_root / LOCK_FILENAME

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Hold an exclusive lock on this participant's progress for the whole change.

        Every mutation here is a read, a decision, and a write. The service held a lock
        across that sequence, but only within its own process, and since the CLI action
        layer landed a second process can do the same sequence at the same time. Four
        concurrent `quest-app action start-quest` calls each read the same file, each
        decided they were first, and three attempts and four activity lines survived.

        The lock is advisory and POSIX-only. On a platform without `fcntl` the block still
        runs: a local-first application must not refuse to work because it cannot lock, and
        the atomic replace in `atomic_write_text` still keeps the file readable.
        """
        try:
            import fcntl
        except ImportError:  # pragma: no cover - POSIX everywhere this is tested
            yield
            return

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            raise StoreError(
                "No participant progress file exists yet. Start a quest to create one."
            )
        data = strict_safe_load(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise StoreError("The participant progress file is not a mapping of fields.")
        return data

    def write(self, data: dict[str, Any], schemas: Any) -> None:
        """Validate, then replace atomically. Never the other way round."""
        from quest_app.errors import ProblemReport

        report = ProblemReport()
        if not schemas.validate("progress", data, f"participant/{PROGRESS_FILENAME}", report):
            raise StoreError(
                "The change would produce a progress file this application cannot read: "
                + "; ".join(problem.public_message for problem in report.errors[:3])
            )
        atomic_write_text(self.path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    def initialise(
        self, participant_id: str, display_name: str, track_id: str, schemas: Any
    ) -> None:
        if self.path.exists():
            return
        self.write(
            {
                "schema_version": 1,
                "participant": {"id": participant_id, "display_name": display_name},
                "selected_track": track_id,
                "attempts": [],
                "updated_at": _now(),
            },
            schemas,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def start_attempt(
    store: ProgressStore,
    *,
    quest_id: str,
    quest_version: int,
    content_hash: str,
    schemas: Any,
    participant_id: str = "participant",
    display_name: str = "Participant",
    track_id: str | None = None,
) -> str:
    """Create an attempt and its evidence package. Returns the attempt ID.

    Creates the progress file first if there is none. The first version required the file
    to exist and offered starting a quest as the only way to create it, so a new
    participant met a circular refusal on their very first action.
    """
    if not store.path.exists():
        store.initialise(participant_id, display_name, track_id or "", schemas)
    data = store.read()
    existing = [a for a in data["attempts"] if a["quest_id"] == quest_id]
    current = AttemptState(existing[-1]["state"]) if existing else None
    try:
        check("start-quest", current)
    except TransitionError as exc:
        raise StoreError(str(exc)) from exc

    attempt_id = _next_attempt_id(quest_id, data["attempts"])
    evidence_path = f"participant/evidence/{quest_id}/{attempt_id}"
    directory = store.config.resolve_participant_path(evidence_path)
    _create_evidence_package(directory, quest_id=quest_id, attempt_id=attempt_id)

    now = _now()
    data["attempts"].append(
        {
            "attempt_id": attempt_id,
            "quest_id": quest_id,
            "quest_version": quest_version,
            "content_hash": content_hash,
            "state": AttemptState.IN_PROGRESS.value,
            "started_at": now,
            "updated_at": now,
            "evidence_path": evidence_path,
        }
    )
    data["updated_at"] = now
    store.write(data, schemas)
    append_audit(store.config, f"Started {quest_id} as attempt {attempt_id}.")
    return attempt_id


def no_guard(action: str) -> None:
    """The explicit "this transition needs no extra condition" guard.

    A named function rather than a default of `None`, so a caller that has no extra condition
    says so and a caller that forgot cannot silently skip one.
    """
    del action


def transition_attempt(
    store: ProgressStore,
    *,
    quest_id: str,
    action: str,
    schemas: Any,
    guard: Callable[[str], None],
) -> AttemptState:
    """Apply one allowed transition to the latest attempt for `quest_id`.

    `guard` is called with the action before anything is written, for the conditions the
    transition table cannot express — notably that `locally_validated` needs qualifying
    validator results. It is **required**, not optional: the first version defaulted it to
    `None`, so the invariant this docstring claimed did not actually exist and a caller could
    reach `locally_validated` with no validation results at all. `no_guard` exists for the
    callers that genuinely have nothing to add, and naming it makes that a visible choice.
    """
    data = store.read()
    attempts = [a for a in data["attempts"] if a["quest_id"] == quest_id]
    if not attempts:
        raise StoreError(f"There is no attempt for {quest_id!r} to change.")
    attempt = max(attempts, key=lambda a: (a["updated_at"], a["attempt_id"]))
    current = AttemptState(attempt["state"])
    try:
        transition = check(action, current)
    except TransitionError as exc:
        raise StoreError(str(exc)) from exc
    guard(action)

    attempt["state"] = transition.target.value
    attempt["updated_at"] = _now()
    data["updated_at"] = attempt["updated_at"]
    store.write(data, schemas)
    append_audit(
        store.config,
        f"{quest_id}: {current.value} → {transition.target.value} ({transition.description})",
    )
    return transition.target


def _next_attempt_id(quest_id: str, attempts: list[dict[str, Any]]) -> str:
    """A stable, readable attempt ID that cannot collide with an existing one."""
    prefix = quest_id.split("-")[0]
    used = {a["attempt_id"] for a in attempts}
    for number in range(1, 1000):
        candidate = f"{prefix}-attempt-{number:03d}"
        if candidate not in used:
            return candidate
    raise StoreError("Too many attempts for one quest.")


def _create_evidence_package(directory: Path, *, quest_id: str, attempt_id: str) -> None:
    """The standard evidence package, created from a template, never overwriting anything."""
    directory.mkdir(parents=True, exist_ok=True)
    for name in EVIDENCE_TEMPLATE_DIRECTORIES:
        (directory / name).mkdir(exist_ok=True)

    proof = directory / "PROOF.md"
    if not proof.exists():
        atomic_write_text(
            proof,
            f"""# Proof · {quest_id}

Attempt: `{attempt_id}`

## What was built

<!-- What exists now that did not before? -->

## Where the important artifacts are

<!-- Repository-relative paths. A reviewer should not have to hunt. -->

## How to reproduce the behavior

<!-- Exact commands, from a clean clone where possible. -->

## What was tested or validated

<!-- Which validators ran, and what they established. -->

## Remaining limitations

<!-- What this does not do, and what you would do next. -->

## Sensitive values

<!-- Confirm that no secret, token, customer name or private ticket content is here. -->
""",
        )

    manifest = directory / "manifest.yaml"
    if not manifest.exists():
        atomic_write_text(
            manifest,
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "quest_id": quest_id,
                    "attempt_id": attempt_id,
                    "created_at": _now(),
                    "artifacts": [],
                },
                sort_keys=False,
            ),
        )


def append_audit(config: AppConfig, message: str) -> None:
    """Append one participant-visible line about a change this application made.

    Ordinary Markdown in the participant's own tree, so it is readable, diffable and theirs.
    Failing to write it must never fail the operation it describes — losing the work would
    be a worse outcome than losing the note.
    """
    path = config.participant_root / AUDIT_FILENAME
    line = f"- `{_now()}` {message}\n"
    try:
        if not path.exists():
            atomic_write_text(
                path,
                "# Activity\n\nEvery change this application made to your files, newest last.\n\n"
                + line,
            )
        else:
            with path.open("a", encoding="utf-8") as stream:
                stream.write(line)
    except OSError:
        return


def write_json_atomic(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
