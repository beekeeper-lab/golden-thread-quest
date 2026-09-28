"""`ActionRunner._is_confirmed` — the ADR-033 choke point every caller confirms through.

Round 14 T2: the explicit allowlist match (`value.strip().lower() in {"yes", "on", "true",
"1", "confirm", "confirmed"}`) had no test of its own. Collapsing it to `bool(value)` passed
the whole suite: every payload sent anywhere in the tree is Python's `True`, `False`, or the
literal string `"yes"`, so nothing ever sent a denial-shaped string (`"no"`, `"false"`, `"0"`,
`"off"`) or an arbitrary non-allowlisted one to check it is refused. Under `bool(value)`, any
of those would have counted as confirmation for `record-review` — the action that produces
verified completion and verified XP.
"""

from __future__ import annotations

from typing import Any

import pytest
from quest_app.actions import _is_confirmed

REFUSED: tuple[Any, ...] = (
    "no",
    "false",
    "0",
    "off",
    "",
    None,
    "  ",
    0,
    0.0,
    [],
    {},
    "deny",
    "nope",
    False,
)

ACCEPTED: tuple[Any, ...] = (
    "yes",
    "on",
    "true",
    "1",
    "confirm",
    "confirmed",
    "YES",
    " Confirmed ",
    True,
)


@pytest.mark.parametrize("value", REFUSED)
def test_a_denial_or_unrecognised_value_is_not_confirmation(value: Any) -> None:
    assert _is_confirmed({"confirm": value}) is False


@pytest.mark.parametrize("value", ACCEPTED)
def test_an_allowlisted_value_is_confirmation(value: Any) -> None:
    assert _is_confirmed({"confirm": value}) is True


def test_a_missing_confirm_key_is_not_confirmation() -> None:
    assert _is_confirmed({}) is False
