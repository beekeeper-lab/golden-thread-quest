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

import contextlib
import json
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from quest_app.config import SUPPORTED_SCHEMA_VERSION, AppConfig
from quest_app.models import AttemptState
from quest_app.safe_io import (
    UnsafeStateFileError,
    UnsafeWriteTargetError,
    append_to_regular_file,
    atomic_write,
    ensure_directory,
    open_lock_file,
    read_bounded_text,
)
from quest_app.state_machine import TransitionError, check
from quest_app.yaml_loader import DeepNestingError, strict_safe_load

PROGRESS_FILENAME = "progress.yaml"
# Never read as data and safe to delete; it exists only while a change is in flight.
LOCK_FILENAME = ".progress.lock"
AUDIT_FILENAME = "ACTIVITY.md"
EVIDENCE_TEMPLATE_DIRECTORIES = ("validation", "screenshots", "logs")


class StoreError(RuntimeError):
    """A write that could not be performed, with a participant-facing reason."""


def atomic_write_text(root: Path, path: Path, text: str) -> None:
    """Replace `path` with `text`, or leave it exactly as it was.

    `root` is the participant root and `path` a location under it, unresolved. The write is
    `safe_io.atomic_write`: same-directory temporary file, fsync, rename, and no link or
    special file followed anywhere between `root` and `path` (round 12 E1). A refusal is a
    `StoreError`, the exception every caller of a participant write already answers.
    """
    atomic_write_bytes(root, path, text.encode("utf-8"))


def atomic_write_bytes(root: Path, path: Path, data: bytes) -> None:
    """`atomic_write_text`, for callers restoring exact original bytes.

    A failed migration restores what was on disk before it ran. Text round-tripped through
    `read_text`/`write_text` turns CRLF line endings into LF, so a restore that is meant to
    put back exactly what was there before instead rewrites it — a participant sees their
    untouched file has changed anyway. Bytes in, bytes out, has no line ending to normalize.
    """
    try:
        atomic_write(root, path, data)
    except UnsafeWriteTargetError as exc:
        raise StoreError(str(exc)) from exc


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

        The lock is advisory and POSIX-only, and **not being able to lock is never a reason
        to refuse the work**. Round 4 wrote that intent in this docstring and delivered it
        only for a missing `fcntl` module. Round 5 found the two cases that actually happen:
        a `.progress.lock` the participant cannot open, and a filesystem that answers
        `ENOLCK` because it has no lock manager, which is what an NFS or 9p home directory
        does. Both raised out of here, ahead of every guard, and the CLI printed a traceback
        carrying absolute paths. Both now fall through to an unlocked change, which is
        exactly what this application did before the lock existed. If the directory is
        genuinely unwritable, the write says so in its own words.
        """
        try:
            import fcntl
        except ImportError:  # pragma: no cover - POSIX everywhere this is tested
            yield
            return

        # Round 5 deleted this file and the directory around it when an action was refused
        # before writing anything, so that a refusal left no trace. Round 6 showed what that
        # costs: a second process holding `flock` on that inode keeps a lock on an orphan,
        # the next process creates a fresh file and enters immediately, and two writers are
        # in the critical section at once — the lost update this lock exists to prevent.
        # A refused first action now leaves one hidden, ignored file in a directory the
        # participant owns. That is the cheaper of the two.
        try:
            # Never through a link or into a FIFO (round 12 E1); either is an `OSError` here.
            handle = os.fdopen(open_lock_file(self.lock_path), "a+", encoding="utf-8")
        except OSError:
            yield
            return

        try:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                # Correct but indistinguishable from a hang: `run-validator` holds this
                # across a validator subprocess, which registry.yaml allows 120 seconds.
                print(
                    "Another change is in progress; waiting for it to finish.",
                    file=sys.stderr,
                )
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                except OSError:
                    yield
                    return
            except OSError:
                yield
                return
            try:
                yield
            finally:
                with contextlib.suppress(OSError):  # unlocking a lock we hold
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            raise StoreError(
                "No participant progress file exists yet. Start a quest to create one."
            )
        # `make validate` reports every one of these through `content_loader.read_text`
        # without a traceback (round 10, then E7). Every other reader of this file —
        # every CLI action, `make migrate` — went through `strict_safe_load` directly, with
        # none of that: a merge conflict's markers, a symlink to a device, or a file over the
        # size ceiling raised straight out of here (E2). This is now the same bounded read,
        # translated into `StoreError`, the exception every caller of `.read()` already
        # expects.
        try:
            text = read_bounded_text(self.path, encoding="utf-8")
        except UnsafeStateFileError as exc:
            raise StoreError(f"The participant progress file is not safe to read: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise StoreError("The participant progress file is not valid UTF-8 text.") from exc
        except OSError as exc:
            raise StoreError(
                f"The participant progress file could not be read: "
                f"{exc.strerror or 'unknown error'}."
            ) from exc
        try:
            data = strict_safe_load(text)
        except DeepNestingError as exc:
            raise StoreError("The participant progress file nests too deeply to parse.") from exc
        except yaml.YAMLError as exc:
            raise StoreError(
                "The participant progress file could not be parsed as YAML. If a merge is in "
                "progress, resolve the conflict (or `git merge --abort`) before trying again."
            ) from exc
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
        atomic_write_text(
            self.config.participant_root,
            self.path,
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        )

    def initialise(
        self, participant_id: str, display_name: str, track_id: str, schemas: Any
    ) -> None:
        if self.path.exists():
            return
        self.write(
            {
                "schema_version": SUPPORTED_SCHEMA_VERSION,
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
    root = store.config.participant_root
    directory = store.config.participant_write_path(evidence_path)
    _create_evidence_package(root, directory, quest_id=quest_id, attempt_id=attempt_id)

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


def _create_evidence_package(
    root: Path, directory: Path, *, quest_id: str, attempt_id: str
) -> None:
    """The standard evidence package, created from a template, never overwriting anything.

    Every directory is created through `ensure_participant_directory`, which refuses a link
    anywhere below the participant root, and each template file is written only when nothing
    at all is at its name — `lexists`, so a dangling link counts as something and the atomic
    write that follows refuses it rather than a later one writing through it.
    """
    for name in EVIDENCE_TEMPLATE_DIRECTORIES:
        ensure_participant_directory(root, directory / name)

    proof = directory / "PROOF.md"
    if not os.path.lexists(proof):
        atomic_write_text(
            root,
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
    if not os.path.lexists(manifest):
        atomic_write_text(
            root,
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

    **When `ACTIVITY.md` is unusable** — a link, a FIFO, a directory, a device — the line is
    skipped and a warning goes to stderr; the change it describes stands (ADR-042). By the time
    this runs the change is already in `progress.yaml`, so refusing the action here would tell
    the participant it had failed while their file said it had happened, and undoing it would
    need a second write the same broken tree could refuse. Round 12 found the old append
    following the link out of the tree, and blocking forever on a FIFO while both the
    progress lock and the service lock were held. Every open here is `O_NOFOLLOW` and
    `O_NONBLOCK`, so it returns at once, and the locks are released as normal.
    """
    root = config.participant_root
    path = root / AUDIT_FILENAME
    line = f"- `{_now()}` {message}\n"
    try:
        try:
            append_to_regular_file(root, path, line.encode("utf-8"))
        except FileNotFoundError:
            atomic_write(
                root,
                path,
                (
                    "# Activity\n\nEvery change this application made to your files, "
                    "newest last.\n\n" + line
                ).encode("utf-8"),
            )
    except UnsafeWriteTargetError as exc:
        print(f"The activity line was not written: {exc}", file=sys.stderr)
    except OSError:
        return


def write_json_atomic(root: Path, path: Path, payload: Any) -> None:
    atomic_write_text(root, path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def ensure_participant_directory(root: Path, directory: Path) -> None:
    """Create `directory` and every parent below `root`, refusing a link anywhere on the way."""
    try:
        ensure_directory(root, directory)
    except UnsafeWriteTargetError as exc:
        raise StoreError(str(exc)) from exc
