"""The reviewer confirms the decision they are actually recording.

The confirmation was one sentence — "Approving produces verified completion and verified XP"
— shown for every decision, so a reviewer requesting changes was asked to confirm producing
verified XP. The server-side gate stays; only the words change with the decision.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from quest_app.actions import ActionRunner
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.state_machine import CONFIRMATIONS, DECISION_CONFIRMATIONS, confirmation_for
from quest_app.view_models import online_service_view

QUEST = "jira-read-assigned-stories"


def _fingerprint(root: Path) -> tuple[str, ...]:
    return tuple(
        f"{path.relative_to(root)}:{path.stat().st_size}:{path.stat().st_mtime_ns}"
        for path in sorted(root.rglob("*"))
        if path.is_file()
    )


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


@pytest.mark.parametrize("denial", ["no", "false", "0", "off", "", None, "  ", 0, [], {}, "deny"])
def test_a_denial_shaped_or_unrecognised_confirm_value_writes_nothing(
    config: AppConfig, denial: Any
) -> None:
    """Round 14 T2. `_is_confirmed` checks a payload against an explicit allowlist, not
    `bool(value)` — under the weaker check every one of these, being a non-empty or
    otherwise unrecognised value, would have counted as confirmation for the one action
    that produces verified completion and verified XP (ADR-033). The whole participant
    tree is fingerprinted, not just `progress.yaml`, so a `review.yaml` written before some
    later guard also refused would still be caught.
    """
    runner = ActionRunner(config, SchemaSet(config.schemas_root), lambda: None)
    before = _fingerprint(config.participant_root)

    with pytest.raises(ValueError, match="confirm it"):
        runner.perform(
            "record-review",
            {
                "quest_id": QUEST,
                "decision": "approved",
                "reviewer_name": "Real Reviewer",
                "verification_statement": "Checked every declared proof file by hand.",
                "confirm": denial,
            },
        )

    assert _fingerprint(config.participant_root) == before


@pytest.mark.parametrize(
    "accepted", ["yes", "on", "true", "1", "confirm", "confirmed", "YES", True]
)
def test_every_allowlisted_confirm_value_passes_the_gate(config: AppConfig, accepted: Any) -> None:
    """The other half of the allowlist: none of these may be refused *for lacking
    confirmation* — `record_decision`'s own guards, further in, still apply beyond this
    point (there is no submission yet here, so it refuses for that instead)."""

    def load() -> Any:
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        return world

    runner = ActionRunner(config, SchemaSet(config.schemas_root), load)
    with pytest.raises(ValueError) as excinfo:
        runner.perform(
            "record-review", {"quest_id": QUEST, "decision": "approved", "confirm": accepted}
        )
    assert "confirm it" not in str(excinfo.value)


def _submitted_review_page(config: AppConfig) -> str:
    """A real `create_submission` call, not a hand-edited `state: submitted` (E4): since
    that check, a `submitted` attempt with no `submission.yaml` is a load error."""
    from quest_app.review import create_submission
    from quest_app.store import ProgressStore

    setup_report = ProblemReport()
    world = load_world(config, setup_report)
    assert world is not None, setup_report.to_text()
    create_submission(
        config,
        ProgressStore(config),
        quest=world.content.quests[QUEST],
        attempt=world.participant.progress.attempt_for(QUEST),
        participant=world.participant,
        schemas=SchemaSet(config.schemas_root),
    )

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
