"""Load everything, validate everything, once.

Callers — the CLI, the builder, the local service — should not each decide what order to
load content and participant state in, or which cross-checks to run. They ask for a
`LoadedWorld` and get either a consistent one or a report explaining why not.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet, load_content
from quest_app.errors import ProblemReport
from quest_app.models import ContentBundle
from quest_app.progress import ParticipantState, load_participant_state
from quest_app.semantics import (
    validate_bundle,
    validate_local_validation_claims,
    validate_progress_against_content,
)


@dataclass(frozen=True, slots=True)
class LoadedWorld:
    """Validated curriculum, plus participant state when there is any."""

    config: AppConfig
    content: ContentBundle
    participant: ParticipantState | None


def load_world(
    config: AppConfig, report: ProblemReport, *, require_participant: bool = False
) -> LoadedWorld | None:
    """Load and cross-validate content and participant state.

    Content is loaded and semantically checked first. Participant state is only read against
    valid content, because an attempt cannot be judged against a curriculum that does not
    itself make sense — every attempt would be reported as referring to an unknown quest.

    A missing participant file is normal: the curriculum is browsable before anyone starts.
    """
    content = load_content(config, report)
    if content is None:
        return None
    validate_bundle(content, report)
    # A quest naming a validator that is not registered, or not registered for it, passed
    # `validate` and `build` and only failed when a participant pressed the button.
    from quest_app.validator_registry import check_quest_references, load_registry

    registry = load_registry(config, report)
    if registry is not None:
        check_quest_references(registry, content.quests, report)

    participant: ParticipantState | None = None
    if report.ok and (_present(config.participant_root / "progress.yaml") or require_participant):
        schemas = SchemaSet(config.schemas_root)
        participant = load_participant_state(config, schemas, report)
        if participant is not None:
            validate_progress_against_content(participant.progress, content, report)
            validate_local_validation_claims(participant, content, report)

    if not report.ok:
        return None
    return LoadedWorld(config=config, content=content, participant=participant)


def _present(path: Path) -> bool:
    """There, or a link that is there even if its target is not, so the loader reports it."""
    return path.exists() or path.is_symlink()
