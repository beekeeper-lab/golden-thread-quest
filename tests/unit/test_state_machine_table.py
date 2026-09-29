"""The whole participant transition table, pinned (round 17 F2).

Every other test exercises a path through the table. Allowing `needs_changes → submitted`
or `verified → withdraw` passed all of them, because no test asked what a state may *not*
do. This asks every state and every action.
"""

from __future__ import annotations

import pytest
from quest_app.models import AttemptState as S
from quest_app.state_machine import BY_ACTION, TRANSITIONS, allowed_actions

EXPECTED: dict[str, tuple[frozenset[S] | None, S]] = {
    "start-quest": (None, S.IN_PROGRESS),
    "resume-quest": (frozenset({S.NEEDS_CHANGES}), S.IN_PROGRESS),
    "mark-evidence-ready": (frozenset({S.IN_PROGRESS}), S.EVIDENCE_READY),
    "reopen-evidence": (frozenset({S.EVIDENCE_READY, S.LOCALLY_VALIDATED}), S.IN_PROGRESS),
    "mark-locally-validated": (frozenset({S.EVIDENCE_READY}), S.LOCALLY_VALIDATED),
    "submit-for-review": (frozenset({S.EVIDENCE_READY, S.LOCALLY_VALIDATED}), S.SUBMITTED),
    "withdraw-submission": (frozenset({S.SUBMITTED}), S.IN_PROGRESS),
}


def test_the_table_is_exactly_the_documented_one() -> None:
    assert {t.action: (t.source, t.target) for t in TRANSITIONS} == EXPECTED
    assert set(BY_ACTION) == set(EXPECTED)


def test_no_participant_action_reaches_a_reviewer_only_state() -> None:
    assert not {t.target for t in TRANSITIONS} & {S.VERIFIED, S.NEEDS_CHANGES}


@pytest.mark.parametrize("state", [None, *S])
def test_every_state_offers_exactly_its_actions(state: S | None) -> None:
    expected = {
        action
        for action, (source, _) in EXPECTED.items()
        if (source is None and state is None) or (source is not None and state in source)
    }
    assert {t.action for t in allowed_actions(state)} == expected
