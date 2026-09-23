"""`locally_validated` is a claim about validator results, so the results decide it at load.

The transition guard refuses the state without qualifying results, but `progress.yaml` is the
participant's own file. Writing `state: locally_validated` into it by hand loaded cleanly and
was shown under the registered validator's authority, as though the checks had passed.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world

QUEST = "jira-read-assigned-stories"
CODE = "progress.unvalidated_locally_validated_state"


def _set_state(config: AppConfig, state: str) -> None:
    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["state"] = state
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def _results(config: AppConfig) -> Path:
    return config.participant_root / "evidence" / QUEST / "jira-attempt-001" / "validation"


def _set_outcomes(config: AppConfig, outcome: str) -> None:
    for path in _results(config).glob("*.json"):
        data = json.loads(path.read_text())
        data["outcome"] = outcome
        path.write_text(json.dumps(data))


def test_a_hand_written_local_validation_with_no_results_is_refused(config: AppConfig) -> None:
    for path in _results(config).glob("*.json"):
        path.unlink()
    _set_state(config, "locally_validated")

    report = ProblemReport()
    assert load_world(config, report) is None
    problems = [p for p in report.errors if p.code == CODE]
    assert len(problems) == 1
    assert "validate-jira-read-assigned" in problems[0].public_message


def test_a_hand_written_local_validation_over_failing_results_is_refused(
    config: AppConfig,
) -> None:
    _set_outcomes(config, "fail")
    _set_state(config, "locally_validated")

    report = ProblemReport()
    assert load_world(config, report) is None
    assert CODE in {p.code for p in report.errors}


def test_a_local_validation_backed_by_a_qualifying_result_loads(config: AppConfig) -> None:
    _set_state(config, "locally_validated")

    report = ProblemReport()
    assert load_world(config, report) is not None, report.to_text()
    assert CODE not in {p.code for p in report.problems}


def test_a_failing_rerun_after_local_validation_is_not_a_forgery(config: AppConfig) -> None:
    """ADR-017: a failing run leaves the attempt where it was, so the site must still load."""
    _set_state(config, "locally_validated")
    passing = next(iter(sorted(_results(config).glob("*.json"))))
    data = json.loads(passing.read_text())
    data.update(
        run_id="validate-jira-read-assigned-20990101000000000000-abcdef",
        completed_at="2099-01-01T00:00:00Z",
        outcome="fail",
    )
    data["result_path"] = data["result_path"].replace(passing.stem, data["run_id"])
    (_results(config) / f"{data['run_id']}.json").write_text(json.dumps(data))

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    assert CODE not in {p.code for p in report.problems}
    attempt = world.participant.progress.attempt_for(QUEST)
    assert world.participant.results_for(attempt)[-1].outcome == "fail", "the rerun is latest"


def test_other_states_are_not_judged_by_this_rule(config: AppConfig) -> None:
    """Submission is allowed straight from evidence_ready, so no later state implies it."""
    for path in _results(config).glob("*.json"):
        path.unlink()
    _set_state(config, "submitted")

    report = ProblemReport()
    load_world(config, report)
    assert CODE not in {p.code for p in report.problems}
