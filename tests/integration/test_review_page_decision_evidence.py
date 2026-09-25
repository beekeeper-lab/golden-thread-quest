"""Round 13, C5: the review page after a decision, not only before one.

Before a decision, "the evidence changed since it was submitted" and "acknowledge this
before approving" are the right words: the reviewer has not acted yet. Once an attempt is
decided, neither is — the reviewer already looked at *something* (which may not be what the
submission recorded, if they approved changed evidence after acknowledging it), and the page
kept comparing against the submission forever, so an approval that had already dealt with a
change still showed the change as unacknowledged and still showed the submission's hash
instead of the one the review actually recorded.
"""

from __future__ import annotations

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.review import create_submission, record_decision
from quest_app.store import ProgressStore
from quest_app.view_models import offline_service_view

QUEST = "jira-read-assigned-stories"
STATEMENT = "I ran the documented command on a clean clone and reproduced the stated behavior."


def _setup(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    schemas = SchemaSet(config.schemas_root)
    store = ProgressStore(config)
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    return world, schemas, store, quest, attempt


def _reload_attempt(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    return world, world.participant.progress.attempt_for(QUEST)


def _review_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=offline_service_view())
    page = config.generated_root / "review" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def test_still_submitted_keeps_the_pre_decision_banner(config: AppConfig) -> None:
    """Nothing changes for an attempt awaiting its first decision."""
    world, schemas, store, quest, attempt = _setup(config)
    create_submission(
        config, store, quest=quest, attempt=attempt, participant=world.participant, schemas=schemas
    )
    world, attempt = _reload_attempt(config)
    directory = config.resolve_participant_path(attempt.evidence_path)
    (directory / "PROOF.md").write_text("# Rewritten after submission\n")

    html = _review_page_html(config)
    assert "The evidence changed since it was submitted" in html
    assert "Acknowledge this before approving" in html
    assert "The evidence changed since it was approved" not in html


def test_verified_with_acknowledgement_shows_no_stale_banner(config: AppConfig) -> None:
    """An approval that already acknowledged the change describes a *current* state of fact."""
    world, schemas, store, quest, attempt = _setup(config)
    create_submission(
        config, store, quest=quest, attempt=attempt, participant=world.participant, schemas=schemas
    )
    world, attempt = _reload_attempt(config)
    directory = config.resolve_participant_path(attempt.evidence_path)
    (directory / "PROOF.md").write_text("# Rewritten, and the reviewer has re-read it\n")

    review = record_decision(
        config,
        store,
        quest=quest,
        attempt=attempt,
        participant=world.participant,
        decision="approved",
        reviewer_name="A Reviewer",
        verification_statement=STATEMENT,
        findings=[],
        schemas=schemas,
        acknowledge_changed_evidence=True,
    )

    html = _review_page_html(config)
    assert "The evidence changed since it was submitted" not in html
    assert "Acknowledge this before approving" not in html
    assert "The evidence changed since it was approved" not in html
    assert review.evidence_hash in html, "the hash shown is the one the review recorded"


def test_verified_then_edited_shows_the_approval_aware_banner(config: AppConfig) -> None:
    """Editing the evidence *after* the decision is a different fact, worded differently."""
    world, schemas, store, quest, attempt = _setup(config)
    create_submission(
        config, store, quest=quest, attempt=attempt, participant=world.participant, schemas=schemas
    )
    world, attempt = _reload_attempt(config)

    review = record_decision(
        config,
        store,
        quest=quest,
        attempt=attempt,
        participant=world.participant,
        decision="approved",
        reviewer_name="A Reviewer",
        verification_statement=STATEMENT,
        findings=[],
        schemas=schemas,
    )
    world, attempt = _reload_attempt(config)
    directory = config.resolve_participant_path(attempt.evidence_path)
    (directory / "PROOF.md").write_text("# Rewritten after the reviewer approved it\n")

    html = _review_page_html(config)
    assert "The evidence changed since it was approved" in html
    assert "The approval stands until a reviewer revokes it" in html
    assert "Acknowledge this before approving" not in html
    assert review.evidence_hash in html, (
        "the hash shown is the one the review recorded, not the stale submission hash"
    )
