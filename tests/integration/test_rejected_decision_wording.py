"""Round 13, C6: `rejected` and `needs_changes` produce the same state and badge.

Nothing told a rejected participant that. The evidence page's copy of the reviewer's
findings (`reviewer_findings_panel`) now says so when the recorded decision is `rejected`.
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
FINDING = {
    "id": "finding-1",
    "severity": "high",
    "summary": "The documented command does not run on a clean clone",
    "evidence": "make validate fails with a missing fixture on a fresh checkout",
}


def _reject(config: AppConfig) -> None:
    schemas = SchemaSet(config.schemas_root)
    store = ProgressStore(config)

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    create_submission(
        config,
        store,
        quest=quest,
        attempt=attempt,
        participant=world.participant,
        schemas=schemas,
    )

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    record_decision(
        config,
        store,
        quest=quest,
        attempt=attempt,
        participant=world.participant,
        decision="rejected",
        reviewer_name="A Reviewer",
        verification_statement=None,
        findings=[FINDING],
        schemas=schemas,
    )


def _evidence_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=offline_service_view())
    page = config.generated_root / "evidence" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def test_a_rejected_decision_says_it_lands_in_needs_changes(config: AppConfig) -> None:
    _reject(config)
    html = _evidence_page_html(config)
    assert "same needs-changes state" in html, (
        "the evidence page does not explain that a rejected decision is the same state "
        "as needs_changes"
    )
