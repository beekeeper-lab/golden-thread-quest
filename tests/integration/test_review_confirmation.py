"""The reviewer confirms the decision they are actually recording.

The confirmation was one sentence — "Approving produces verified completion and verified XP"
— shown for every decision, so a reviewer requesting changes was asked to confirm producing
verified XP. The server-side gate stays; only the words change with the decision.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from quest_app.actions import ActionRunner
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.state_machine import CONFIRMATIONS, DECISION_CONFIRMATIONS, confirmation_for
from quest_app.view_models import online_service_view

QUEST = "jira-read-assigned-stories"


def test_each_decision_confirms_its_own_consequence() -> None:
    approve = confirmation_for("record-review", {"decision": "approved"})
    assert "produces verified completion" in approve
    for decision in ("needs_changes", "rejected"):
        wording = confirmation_for("record-review", {"decision": decision})
        assert "produces verified" not in wording, decision
        assert "nothing is verified" in wording


def test_the_neutral_wording_makes_the_approval_consequence_conditional() -> None:
    """Shown before a decision is chosen, and to a browser without scripting."""
    neutral = CONFIRMATIONS["record-review"]
    assert neutral.startswith("Record this decision.")
    assert "Only an approval produces verified" in neutral
    assert confirmation_for("record-review", {}) == neutral
    assert confirmation_for("record-review", {"decision": "bogus"}) == neutral


def test_the_action_layer_still_refuses_an_unconfirmed_decision_in_its_own_words(
    config: AppConfig,
) -> None:
    runner = ActionRunner(config, SchemaSet(config.schemas_root), lambda: None)
    with pytest.raises(ValueError, match="Record this request for changes"):
        runner.perform(
            "record-review", {"quest_id": QUEST, "decision": "needs_changes", "confirm": False}
        )
    with pytest.raises(ValueError, match="Record this approval"):
        runner.perform("record-review", {"quest_id": QUEST, "decision": "approved"})


def _submitted_review_page(config: AppConfig) -> str:
    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["state"] = "submitted"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=online_service_view())
    return (Path(config.generated_root) / "review" / QUEST / "index.html").read_text()


def test_the_decision_form_carries_each_decision_s_wording(config: AppConfig) -> None:
    page = _submitted_review_page(config)
    assert 'id="decision"' in page, "the decision form was not rendered"
    for decision, wording in DECISION_CONFIRMATIONS.items():
        assert f'value="{decision}" data-confirm="{wording}?"' in page, decision
    # Without scripting the label is all a reviewer reads, so it must be true for any choice.
    assert f"<span data-confirm-label>{CONFIRMATIONS['record-review']}</span>" in page
    assert "Approving produces verified completion" not in page
