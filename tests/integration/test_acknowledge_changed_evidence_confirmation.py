"""Round 15 E8: `acknowledge_changed_evidence` is parsed the same strict way `confirm` is.

`bool(payload.get("acknowledge_changed_evidence"))` (`actions.py`) and
`bool(fields.get("acknowledge_changed_evidence"))` (`serve.py`) both treated the string
`"false"` as true — Python's `bool("false")` is `True`, same as `bool("anything")`. A JSON
caller that explicitly said it had *not* re-read changed evidence
(`"acknowledge_changed_evidence": "false"`) had that denial read as an acknowledgement, and
an approval of evidence the reviewer never re-read went through anyway (ADR-033's whole
point). Both now go through `quest_app.actions.is_affirmed`, the same allowlist `confirm`
already used, reused rather than duplicated.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from quest_app.actions import ActionRunner
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.store import StoreError

QUEST = "jira-read-assigned-stories"
STATEMENT = "I re-read the assigned-issue export and matched it against every criterion."

# The same shapes round 14 T2 established for `confirm` (test_review_confirmation.py):
# denial words, falsy-but-not-`False` values, and values that mean nothing at all.
DENIALS: tuple[Any, ...] = (
    "false",
    "no",
    "0",
    "off",
    "",
    None,
    "  ",
    0,
    [],
    {},
    "deny",
    False,
)
ACCEPTED: tuple[Any, ...] = ("yes", "on", "true", "1", "confirm", "confirmed", "YES", True)


def _submit_then_edit_a_proof_file(config: AppConfig) -> None:
    """Submit the quest, then edit its evidence — the state `acknowledge_changed_evidence`
    exists to gate an approval of."""
    from quest_app.review import create_submission
    from quest_app.store import ProgressStore

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    create_submission(
        config,
        ProgressStore(config),
        quest=world.content.quests[QUEST],
        attempt=world.participant.progress.attempt_for(QUEST),
        participant=world.participant,
        schemas=SchemaSet(config.schemas_root),
    )
    proof = next((config.participant_root / "evidence" / QUEST).glob("*/PROOF.md"))
    proof.write_text(proof.read_text() + "\nEdited after submitting.\n", encoding="utf-8")


def _state_of(config: AppConfig, quest: str = QUEST) -> str:
    data = yaml.safe_load((config.participant_root / "progress.yaml").read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == quest:
            return str(attempt["state"])
    raise AssertionError(f"{quest} has no recorded attempt")


def _runner(config: AppConfig) -> ActionRunner:
    def load() -> Any:
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        return world

    return ActionRunner(config, SchemaSet(config.schemas_root), load)


@pytest.mark.parametrize("denial", DENIALS)
def test_a_denial_shaped_acknowledgement_does_not_approve_changed_evidence(
    config: AppConfig, denial: Any
) -> None:
    _submit_then_edit_a_proof_file(config)

    with pytest.raises(StoreError, match="changed"):
        _runner(config).perform(
            "record-review",
            {
                "quest_id": QUEST,
                "decision": "approved",
                "reviewer_name": "Real Reviewer",
                "verification_statement": STATEMENT,
                "confirm": True,
                "acknowledge_changed_evidence": denial,
            },
        )

    assert _state_of(config) == "submitted", "a denied acknowledgement must not verify anything"


@pytest.mark.parametrize("accepted", ACCEPTED)
def test_an_allowlisted_acknowledgement_still_lets_the_approval_through(
    config: AppConfig, accepted: Any
) -> None:
    """The other half: none of these may be refused *for the acknowledgement*."""
    _submit_then_edit_a_proof_file(config)

    _runner(config).perform(
        "record-review",
        {
            "quest_id": QUEST,
            "decision": "approved",
            "reviewer_name": "Real Reviewer",
            "verification_statement": STATEMENT,
            "confirm": True,
            "acknowledge_changed_evidence": accepted,
        },
    )

    assert _state_of(config) == "verified"


def test_a_missing_acknowledgement_key_is_not_an_acknowledgement(config: AppConfig) -> None:
    _submit_then_edit_a_proof_file(config)

    with pytest.raises(StoreError, match="changed"):
        _runner(config).perform(
            "record-review",
            {
                "quest_id": QUEST,
                "decision": "approved",
                "reviewer_name": "Real Reviewer",
                "verification_statement": STATEMENT,
                "confirm": True,
            },
        )

    assert _state_of(config) == "submitted"
