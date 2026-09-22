"""The shipped validators, checked against work that should fail them.

A validator is a check, and a check is only worth what it can see. Each test here hands a
validator work that satisfies the words of its summary while failing the criterion behind
it, which is the shape the earlier rounds kept finding.
"""

from __future__ import annotations

import json
from pathlib import Path

from quest_app.validator_runner import ValidatorOutput, Workspace
from validators.jira_read_assigned import _check_disappearances_reported
from validators.playwright_quality import BRITTLE_SELECTORS
from validators.repository_foundation import _check_ignore_rules

STALE_FIXTURE = json.loads(Path("validators/fixtures/jira/stale-item.json").read_text())


def _workspace(root: Path) -> Workspace:
    return Workspace(
        read_roots=(root.resolve(),),
        write_roots=(),
        repo_root=root.resolve(),
        participant_root=(root / "participant").resolve(),
        parameters={},
    )


def _outcome(output: ValidatorOutput, check_id: str) -> str | None:
    for check in output.checks:
        if check.id == check_id:
            return check.outcome
    return None


class TestIgnoreRulesAreRules:
    """A .gitignore is judged by what it ignores, not by the words it contains."""

    def test_a_file_of_comments_covers_nothing(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(
            "# Note to the reviewer: generated output, local-data, .cache and tmp/ files,\n"
            "# .env files and credentials or secret material must never be committed.\n"
        )
        output = ValidatorOutput()
        _check_ignore_rules(_workspace(tmp_path), output)
        assert _outcome(output, "ignore-rules-present") == "fail"
        assert _outcome(output, "ignore-rules-cover-categories") is None

    def test_a_negation_is_not_coverage(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("generated/\n!credentials/keep.md\n.env\ntmp/\n")
        output = ValidatorOutput()
        _check_ignore_rules(_workspace(tmp_path), output)
        assert _outcome(output, "ignore-rules-cover-categories") == "fail"

    def test_real_rules_pass(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text(
            "# what this covers\ngenerated/\nlocal-data/\n.env\n*.pem\n"
        )
        output = ValidatorOutput()
        _check_ignore_rules(_workspace(tmp_path), output)
        assert _outcome(output, "ignore-rules-cover-categories") == "pass"


class TestBrittleSelectors:
    """The check exists to catch a test coupled to markup, which is usually a class name."""

    def test_a_class_or_id_locator_is_brittle(self) -> None:
        for source in (
            "page.locator('.btn-primary')",
            'page.locator("#submit-button")',
            "page.locator('.card .title')",
            "page.locator('div')",
            "frame.query_selector('div.card > span')",
        ):
            assert BRITTLE_SELECTORS.search(source), source

    def test_a_test_id_or_text_engine_is_not(self) -> None:
        for source in (
            'page.locator("[data-testid=save]")',
            "page.locator('text=Save')",
            "page.get_by_role('button', name='Save')",
        ):
            assert not BRITTLE_SELECTORS.search(source), source


class TestDisappearancesAreReported:
    """Criterion 8 is about saying an item went away, not about the record surviving."""

    def _run(self, stories: list[dict[str, object]], **document: object) -> str | None:
        output = ValidatorOutput()
        payload = {"stories": stories, **document}
        _check_disappearances_reported(STALE_FIXTURE, payload, stories, output)
        return _outcome(output, "disappearances-reported")

    def test_a_synchronization_that_never_noticed_fails(self) -> None:
        """The story is still listed as assigned, exactly as the previous run left it."""
        assert (
            self._run([{"key": "GTQ-100", "status": "In Progress", "summary": "untouched"}])
            == "fail"
        )

    def test_dropping_it_silently_fails(self) -> None:
        assert self._run([{"key": "GTQ-101", "status": "To Do"}]) == "fail"

    def test_a_record_marked_no_longer_assigned_passes(self) -> None:
        assert self._run([{"key": "GTQ-100", "status": "In Progress", "assigned": False}]) == "pass"

    def test_a_status_naming_the_removal_passes(self) -> None:
        assert self._run([{"key": "GTQ-100", "status": "removed from my queue"}]) == "pass"

    def test_a_separate_removal_list_passes(self) -> None:
        assert self._run([], removed=[{"key": "GTQ-100"}]) == "pass"
