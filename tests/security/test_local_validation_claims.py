"""`locally_validated` is a claim about validator results, so the results decide it at load.

The transition guard refuses the state without qualifying results, but `progress.yaml` is the
participant's own file. Writing `state: locally_validated` into it by hand loaded cleanly and
was shown under the registered validator's authority, as though the checks had passed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world

QUEST = "jira-read-assigned-stories"
CODE = "progress.unvalidated_locally_validated_state"
NEW_VALIDATOR_CODE = "progress.locally_validated_missing_new_validator"
QUEST_CONTENT_PATH = "content/quests/jira-jungle/read-assigned-stories.md"
REGISTRY_PATH = "validators/registry.yaml"


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


def _add_validator_in_a_newer_quest_version(config: AppConfig, new_validator: str) -> None:
    """Simulate an upstream curriculum update that requires one more validator.

    The quest's declared version moves past the attempt's `quest_version`, and the new
    validator is registered to run for it — everything a legitimate upstream change does,
    with no forgery involved.
    """
    quest_path = config.repo_root / QUEST_CONTENT_PATH
    text = quest_path.read_text()
    current = int(re.search(r"(?m)^version: (\d+)$", text).group(1).strip())
    text = re.sub(r"(?m)^version: \d+$", f"version: {current + 1}", text, count=1)
    text = text.replace(
        "validators:\n  - validate-jira-read-assigned\n",
        f"validators:\n  - validate-jira-read-assigned\n  - {new_validator}\n",
        1,
    )
    quest_path.write_text(text)

    registry_path = config.repo_root / REGISTRY_PATH
    registry = yaml.safe_load(registry_path.read_text())
    for entry in registry["validators"]:
        if entry["id"] == new_validator:
            entry["quest_ids"].append(QUEST)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False))


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


def test_a_validator_added_after_the_attempts_version_is_a_warning_not_a_load_error(
    config: AppConfig,
) -> None:
    """ADR-017 (amended round 12, E5).

    An upstream update that adds a validator must not turn a legitimate `locally_validated`
    attempt into a load error: this application keeps no record of what a quest required at
    an earlier version, so a validator missing here may simply not have existed yet. The
    attempt still has a qualifying result from the validator it did run, which is what
    keeps this from being a wholesale forgery.
    """
    _set_state(config, "locally_validated")
    _add_validator_in_a_newer_quest_version(config, "validate-playwright-quality")

    report = ProblemReport()
    world = load_world(config, report)

    assert world is not None, report.to_text()
    assert CODE not in {p.code for p in report.problems}, report.to_text()
    warnings = [p for p in report.warnings if p.code == NEW_VALIDATOR_CODE]
    assert len(warnings) == 1, report.to_text()
    assert "validate-playwright-quality" in warnings[0].public_message
    assert "validate-playwright-quality" in (warnings[0].suggestion or "")


def test_a_version_mismatch_with_no_qualifying_result_at_all_is_still_refused(
    config: AppConfig,
) -> None:
    """The version mismatch alone does not excuse it.

    An attempt that never produced a single qualifying result is indistinguishable from the
    forgery this whole check exists to catch, whatever quest version it claims.
    """
    for path in _results(config).glob("*.json"):
        path.unlink()
    _set_state(config, "locally_validated")
    _add_validator_in_a_newer_quest_version(config, "validate-playwright-quality")

    report = ProblemReport()
    assert load_world(config, report) is None
    assert CODE in {p.code for p in report.errors}


def _set_attempt_quest_version(config: AppConfig, version: int) -> None:
    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["quest_version"] = version
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def test_a_hand_lowered_version_does_not_excuse_a_missing_validator(config: AppConfig) -> None:
    """Round 13 E7.

    Lowering `quest_version` by hand, with the quest's text untouched, used to earn the same
    excuse a genuine upstream update earns: "this may predate the validator". It should not,
    because `content_hash` still names the *current* text of the quest — nothing about what
    this attempt validated against actually changed, only the number claiming it did.

    `passed` has to be non-empty for the excuse to even be considered (round 12 E5's own
    guard), so this attempt keeps a qualifying result — from a validator the quest does not
    even declare, so it proves nothing about `validate-jira-read-assigned`, which stays
    missing throughout.
    """
    original = next(iter(_results(config).glob("*.json")))
    stray = json.loads(original.read_text())
    stray["result_path"] = stray["result_path"].replace(original.stem, "stray-run-001")
    stray.update(run_id="stray-run-001", validator_id="validate-something-else", outcome="pass")
    (_results(config) / "stray-run-001.json").write_text(json.dumps(stray))
    original.unlink()
    _set_state(config, "locally_validated")
    _set_attempt_quest_version(config, 1)  # the published quest is version 2; content untouched

    report = ProblemReport()
    assert load_world(config, report) is None, "content_hash matches the current version"
    assert CODE in {p.code for p in report.errors}
    assert NEW_VALIDATOR_CODE not in {p.code for p in report.problems}


def test_a_genuinely_older_version_still_gets_the_warning(config: AppConfig) -> None:
    """The legitimate case E7 must not break: content actually changed, so the excuse holds."""
    _set_state(config, "locally_validated")
    _add_validator_in_a_newer_quest_version(config, "validate-playwright-quality")

    report = ProblemReport()
    world = load_world(config, report)

    assert world is not None, report.to_text()
    assert CODE not in {p.code for p in report.problems}
    assert NEW_VALIDATOR_CODE in {p.code for p in report.warnings}
