"""The pilot workflows keep the trust boundary the specification describes (ADR-045, ADR-046)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
PRECHECK = yaml.safe_load((WORKFLOWS / "pilot-precheck.yml").read_text())
REVIEW = yaml.safe_load((WORKFLOWS / "pilot-ai-review.yml").read_text())


def _on(workflow: dict[Any, Any]) -> dict[str, Any]:
    # PyYAML reads the bare key `on` as the boolean True.
    return workflow.get("on") or workflow[True]


def _steps(workflow: dict[Any, Any]) -> list[dict[str, Any]]:
    return [step for job in workflow["jobs"].values() for step in job["steps"]]


def test_no_job_holds_both_the_model_key_and_the_bot_token() -> None:
    for name, job in REVIEW["jobs"].items():
        text = json.dumps(job)
        assert not ("secrets.ANTHROPIC_API_KEY" in text and "secrets.PILOT_BOT_TOKEN" in text), name


def test_the_review_job_cannot_write_and_the_apply_job_has_no_model_key() -> None:
    review, apply = REVIEW["jobs"]["review"], REVIEW["jobs"]["apply"]
    assert "secrets.ANTHROPIC_API_KEY" in json.dumps(review)
    assert set(review["permissions"].values()) <= {"read"}
    assert "ANTHROPIC" not in json.dumps(apply)
    assert "PILOT_BOT_TOKEN" in json.dumps(apply)


@pytest.mark.parametrize("workflow", [PRECHECK, REVIEW])
def test_no_job_checks_out_or_runs_the_pull_request(workflow: dict[Any, Any]) -> None:
    for step in _steps(workflow):
        if str(step.get("uses", "")).startswith("actions/checkout"):
            assert set(step.get("with", {})) <= {"persist-credentials", "fetch-depth"}, step
        for field in ("run", "with", "env"):
            text = json.dumps(step.get(field, ""))
            assert "head.sha" not in text and "head.ref" not in text, step
            assert "pull_request.title" not in text and "pull_request.body" not in text, step


def test_the_precheck_runs_from_the_base_repository_and_only_for_pilot_branches() -> None:
    assert "pull_request_target" in _on(PRECHECK)
    condition = PRECHECK["jobs"]["precheck"]["if"]
    assert "startsWith(github.event.pull_request.head.ref, 'pilot/')" in condition


def test_the_workflow_reviewer_is_a_manual_fallback_the_forge_timer_does_the_sweep() -> None:
    triggers = _on(REVIEW)
    assert set(triggers) == {"workflow_dispatch"}
    assert "pilot-ai-review" not in json.dumps(PRECHECK)
    assert "actions" not in PRECHECK["permissions"]


def test_the_mode_defaults_to_shadow_and_can_be_turned_off() -> None:
    assert "'shadow'" in REVIEW["env"]["MODE"]
    assert "!= 'off'" in REVIEW["jobs"]["select"]["if"]


def test_shell_steps_only_interpolate_numbers_and_hashes_from_the_matrix() -> None:
    for step in _steps(REVIEW):
        run = step.get("run", "")
        for part in run.split("${{")[1:]:
            expression = part.split("}}")[0].strip()
            assert expression in {"matrix.pr", "steps.fetch.outputs.sha"}, expression
