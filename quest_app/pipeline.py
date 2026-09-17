"""Load everything, validate everything, once.

Callers — the CLI, the builder, the local service — should not each decide what order to
load content and participant state in, or which cross-checks to run. They ask for a
`LoadedWorld` and get either a consistent one or a report explaining why not.
"""

from __future__ import annotations

from dataclasses import dataclass

from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet, load_content
from quest_app.errors import ProblemReport
from quest_app.models import ContentBundle
from quest_app.progress import ParticipantState, load_participant_state
from quest_app.semantics import validate_bundle, validate_progress_against_content


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

    participant: ParticipantState | None = None
    if report.ok and ((config.participant_root / "progress.yaml").exists() or require_participant):
        schemas = SchemaSet(config.schemas_root)
        participant = load_participant_state(config, schemas, report)
        if participant is not None:
            validate_progress_against_content(participant.progress, content, report)

    if not report.ok:
        return None
    return LoadedWorld(config=config, content=content, participant=participant)
