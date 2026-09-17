"""`format: date-time` must actually reject a non-timestamp.

The first attempt at this fix passed a `FormatChecker` and looked correct. It was not:
`jsonschema` registers a `date-time` checker only when `rfc3339-validator` is installed, so
`started_at: "banana"` still validated. That silently defeated the out-of-order warning and
left attempt ordering comparing garbage as strings.

This test fails if the `[format]` extra is ever dropped from the dependencies.
"""

from __future__ import annotations

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.progress import load_participant_state


def test_the_date_time_format_checker_is_installed() -> None:
    from jsonschema import FormatChecker

    assert "date-time" in FormatChecker().checkers, (
        "jsonschema needs its [format] extra; without it `format: date-time` checks nothing"
    )


@pytest.mark.parametrize("value", ["banana", "2026-13-45T99:99:99Z", "16/09/2026", ""])
def test_a_non_timestamp_is_rejected(config: AppConfig, report: ProblemReport, value: str) -> None:
    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    data["attempts"][0]["started_at"] = value
    path.write_text(yaml.safe_dump(data, sort_keys=False))

    load_participant_state(config, SchemaSet(config.schemas_root), report)

    assert any(p.code.startswith("schema.progress") for p in report.errors), report.to_text()


def test_a_real_timestamp_is_accepted(config: AppConfig, report: ProblemReport) -> None:
    load_participant_state(config, SchemaSet(config.schemas_root), report)
    assert not [p for p in report.errors if p.code.startswith("schema.progress")]
