"""Round 12, C4: `locally_validated` and a later failing run of the same validator.

ADR-017 says a validation run never changes state — `locally_validated` is earned once, and
a failing re-run leaves the attempt alone. That is correct, and this test does not touch it.
But the evidence page showed "Required automated checks passed" (the state's explanation)
right beside "Last run: fail" for the very validator that earned it, with nothing saying
those are two different moments. This checks that a note now connects them.
"""

from __future__ import annotations

import json

import yaml
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.view_models import offline_service_view

QUEST = "jira-read-assigned-stories"
VALIDATOR = "validate-jira-read-assigned"


def _mark_locally_validated_with_a_later_failure(config: AppConfig) -> None:
    progress = config.participant_root / "progress.yaml"
    data = yaml.safe_load(progress.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["state"] = "locally_validated"
    progress.write_text(yaml.safe_dump(data, sort_keys=False))

    evidence_dir = config.participant_root / "evidence" / QUEST / "jira-attempt-001" / "validation"
    result = json.loads((evidence_dir / "jira-read-assigned-run-001.json").read_text())
    result["run_id"] = "jira-read-assigned-run-002"
    result["completed_at"] = "2026-09-17T09:00:00Z"
    result["started_at"] = "2026-09-17T08:59:50Z"
    result["outcome"] = "fail"
    result["checks"] = [
        {
            "id": "pagination-complete",
            "outcome": "fail",
            "severity": "blocking",
            "summary": "Only 20 of 37 expected issue keys are present in the generated index.",
            "evidence": "The fixture server changed shape after the run that passed.",
        }
    ]
    result["result_path"] = (
        f"participant/evidence/{QUEST}/jira-attempt-001/validation/jira-read-assigned-run-002.json"
    )
    (evidence_dir / "jira-read-assigned-run-002.json").write_text(json.dumps(result))


def _evidence_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=offline_service_view())
    page = config.generated_root / "evidence" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def test_a_stale_locally_validated_state_carries_a_connecting_note(
    config: AppConfig,
) -> None:
    _mark_locally_validated_with_a_later_failure(config)
    html = _evidence_page_html(config)

    assert "Required automated checks passed" in html, (
        "ADR-017: a failing re-run must not unwind the state"
    )
    assert "fail" in html, "the latest run's outcome must still be shown"
    assert "earlier passing run" in html, (
        "a note must connect the earned state to the later failing run"
    )


def test_a_currently_qualifying_locally_validated_state_carries_no_such_note(
    config: AppConfig,
) -> None:
    """The note is about a contradiction that exists, not a permanent disclaimer."""
    progress = config.participant_root / "progress.yaml"
    data = yaml.safe_load(progress.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["state"] = "locally_validated"
    progress.write_text(yaml.safe_dump(data, sort_keys=False))

    html = _evidence_page_html(config)
    assert "Required automated checks passed" in html
    assert "earlier passing run" not in html
