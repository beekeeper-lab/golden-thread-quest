"""Participant-state migrations.

A participant's `progress.yaml` is theirs and lives in their Git history. When the program
changes the shape of that file, the migration has to be reversible in practice: it validates
before, validates after, and if anything goes wrong the original is still on disk unchanged.

Two rules shape every migration here.

* **Never migrate an in-progress attempt's quest version.** A participant working against
  version 2 of a quest keeps working against version 2 until they choose otherwise. Silently
  advancing it would change the acceptance criteria under someone mid-task.
* **Never drop a field you do not understand.** An unknown key is carried forward. The
  alternative — dropping it — quietly destroys data written by a newer version of the
  application that a participant may go back to.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quest_app.config import SUPPORTED_SCHEMA_VERSION


class MigrationError(RuntimeError):
    """A migration that cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class Migration:
    from_version: int
    to_version: int
    description: str
    apply: Callable[[dict[str, Any]], dict[str, Any]]


def _identity(data: dict[str, Any]) -> dict[str, Any]:
    """The no-op step for version 1.

    Release one ships schema version 1, so there is nothing to migrate yet. The machinery
    exists now rather than later because the first real migration is exactly the wrong
    moment to be designing the safety around it.
    """
    return data


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        from_version=0,
        to_version=1,
        description="Adopt schema version 1 (no change to existing fields).",
        apply=_identity,
    ),
)


def plan(current_version: int, target_version: int = SUPPORTED_SCHEMA_VERSION) -> list[Migration]:
    """The ordered steps from `current_version` to `target_version`."""
    if current_version > target_version:
        raise MigrationError(
            f"This state was written by a newer version of the application "
            f"(schema {current_version}, this build understands {target_version}). "
            "Update the application rather than downgrading your work."
        )
    steps: list[Migration] = []
    version = current_version
    while version < target_version:
        step = next((m for m in MIGRATIONS if m.from_version == version), None)
        if step is None:
            raise MigrationError(
                f"No migration is defined from schema version {version} to {version + 1}."
            )
        steps.append(step)
        version = step.to_version
    return steps


def migrate(
    data: dict[str, Any], *, target_version: int = SUPPORTED_SCHEMA_VERSION
) -> tuple[dict[str, Any], list[str]]:
    """Apply every step in order, returning the new state and what was done.

    The input is not mutated: a caller holding the original can always put it back.
    """
    raw_version = data.get("schema_version", 0)
    try:
        current = int(raw_version)
    except (TypeError, ValueError) as exc:
        # `progress.py`'s schema-version check is this lenient on purpose, deferring to the
        # JSON Schema error that follows for the precise complaint. There is no schema check
        # here — this is the one place a bad value reaches an unguarded `int()` instead — so
        # the sentence has to say what is wrong itself, not raise past this function's own
        # caller as a `ValueError`/`TypeError` neither expects.
        raise MigrationError(
            f"schema_version is {raw_version!r}, which is not a whole number. Run "
            "`make validate-content` for the exact problem, then fix progress.yaml by hand."
        ) from exc
    steps = plan(current, target_version)
    if not steps:
        return dict(data), []

    migrated = dict(data)
    applied: list[str] = []
    for step in steps:
        before = dict(migrated)
        migrated = step.apply(dict(migrated))
        migrated["schema_version"] = step.to_version
        _check_nothing_was_lost(before, migrated, step)
        applied.append(f"{step.from_version} → {step.to_version}: {step.description}")
    return migrated, applied


def _check_nothing_was_lost(before: dict[str, Any], after: dict[str, Any], step: Migration) -> None:
    """Refuse a migration that dropped an attempt or a top-level field.

    A migration is code, and code has bugs. This is the guard that turns a data-losing bug
    into a refusal instead of a participant discovering months later that two quests
    vanished from their record.
    """
    lost_keys = sorted(set(before) - set(after) - {"schema_version"})
    if lost_keys:
        raise MigrationError(
            f"migration {step.from_version}→{step.to_version} dropped field(s): "
            + ", ".join(lost_keys)
        )
    before_attempts = {a.get("attempt_id") for a in before.get("attempts", [])}
    after_attempts = {a.get("attempt_id") for a in after.get("attempts", [])}
    lost_attempts = sorted(str(a) for a in before_attempts - after_attempts)
    if lost_attempts:
        raise MigrationError(
            f"migration {step.from_version}→{step.to_version} dropped attempt(s): "
            + ", ".join(lost_attempts)
        )


def attempts_on_older_quest_versions(
    data: dict[str, Any], quest_versions: dict[str, int]
) -> list[dict[str, Any]]:
    """In-progress attempts whose quest has moved on.

    These are reported, never rewritten. The participant decides whether to move to the new
    version, because the acceptance criteria they are working against may have changed.
    """
    finished = {"verified"}
    return [
        attempt
        for attempt in data.get("attempts", [])
        if attempt.get("state") not in finished
        and attempt.get("quest_version", 0) < quest_versions.get(attempt.get("quest_id", ""), 0)
    ]
