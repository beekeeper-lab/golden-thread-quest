"""What a validator may write, and what the result document can actually hold.

The registry declared a capture size, the result schema declared a smaller field, and
nothing reconciled the two: a validator that passed and said too much had its entire run
refused with a message about a rejected document.
"""

from __future__ import annotations

import json
from pathlib import Path

from quest_app.validator_runner import EXCERPT_LIMIT, TRUNCATION_SUFFIX, _bounded

ROOT = Path(__file__).resolve().parent.parent.parent
RESULT_SCHEMA = ROOT / "schemas" / "validation-result.schema.json"
REGISTRY_SCHEMA = ROOT / "schemas" / "validator-registry.schema.json"


def test_the_excerpt_limit_is_the_one_the_result_schema_enforces() -> None:
    schema = json.loads(RESULT_SCHEMA.read_text())
    assert schema["properties"]["output_excerpt"]["maxLength"] == EXCERPT_LIMIT


def test_no_validator_may_be_registered_above_what_a_result_can_hold() -> None:
    """A declared number nothing can honour is the same defect as no number at all."""
    schema = json.loads(REGISTRY_SCHEMA.read_text())
    entry = schema["$defs"]["validator"]["properties"]["max_output_bytes"]
    assert entry["maximum"] == EXCERPT_LIMIT


def test_a_truncated_excerpt_counts_its_own_notice() -> None:
    """The notice used to be appended after truncating, putting the excerpt over the cap."""
    text, truncated = _bounded("x" * (EXCERPT_LIMIT * 2), EXCERPT_LIMIT)
    assert truncated
    assert len(text.encode("utf-8")) <= EXCERPT_LIMIT
    assert text.endswith(TRUNCATION_SUFFIX)


def test_an_excerpt_that_fits_is_returned_whole() -> None:
    text, truncated = _bounded("still short", EXCERPT_LIMIT)
    assert not truncated
    assert text == "still short"
