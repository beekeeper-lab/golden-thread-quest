"""Every quest state renders, and the states the plan names by hand are exercised.

The shipped fixture only ever occupies `verified` and `evidence_ready`. Four of the eight
states appeared in the map legend and nowhere else, and no test put a real quest into one —
which is the same shape as the defects the final audit found hiding in unoccupied states.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.models import QuestState
from quest_app.pipeline import load_world
from quest_app.view_models import offline_service_view, online_service_view

QUEST = "jira-read-assigned-stories"
LOCKED_QUEST = "playwright-first-independent-test"


def rebuild(config: AppConfig, *, online: bool = False) -> Path:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(
        world,
        built_at="2026-09-17T00:00:00+00:00",
        service=online_service_view() if online else offline_service_view(),
    )
    return config.generated_root


def set_state(config: AppConfig, quest_id: str, state: str) -> None:
    path = config.participant_root / "progress.yaml"
    data = yaml.safe_load(path.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == quest_id:
            attempt["state"] = state
            if state != "verified":
                attempt.pop("review_id", None)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


@pytest.mark.parametrize(
    "state",
    ["in_progress", "evidence_ready", "locally_validated", "submitted", "needs_changes"],
)
def test_every_storable_state_renders_on_the_map(config: AppConfig, state: str) -> None:
    set_state(config, QUEST, state)
    root = rebuild(config)

    catalog = (root / "catalog" / "index.html").read_text()
    from quest_app.models import STATE_LABELS

    label = STATE_LABELS[QuestState(state)]
    assert f'data-state="{state}"' in catalog, f"{state} does not reach the catalog"
    assert label in catalog, f"{state} renders no readable label"


def test_the_legend_names_every_state(config: AppConfig) -> None:
    from quest_app.models import STATE_LABELS

    html = (rebuild(config) / "map" / "index.html").read_text()
    for state, label in STATE_LABELS.items():
        assert label in html, f"the legend omits {state}"


class TestLocked:
    def test_a_locked_quest_shows_its_unmet_prerequisites(self, config: AppConfig) -> None:
        quest = (
            config.repo_root
            / "content"
            / "quests"
            / "playwright-labyrinth"
            / "first-independent-test.md"
        )
        _, front, body = quest.read_text().split("---\n", 2)
        data = yaml.safe_load(front)
        data["prerequisites"] = [QUEST]
        quest.write_text("---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body)
        # The prerequisite is started but not verified, so the dependent quest stays locked.
        set_state(config, QUEST, "in_progress")

        html = (rebuild(config) / "quests" / LOCKED_QUEST / "index.html").read_text()

        assert "This quest is locked" in html
        assert "Before you start" in html
        assert "Verify this quest first" in html
        assert 'class="button" disabled' in html, "a locked quest must not offer a live start"


class TestNeedsChanges:
    def test_it_says_the_evidence_is_preserved(self, config: AppConfig) -> None:
        """A participant reading this has just been told their work was not accepted."""
        set_state(config, QUEST, "needs_changes")
        html = (rebuild(config) / "quests" / QUEST / "index.html").read_text()
        assert "Needs changes" in html
        assert "evidence is preserved" in html.lower()


class TestFailedValidation:
    def test_a_failing_run_is_shown_without_calling_the_quest_failed(
        self, config: AppConfig
    ) -> None:
        import json

        evidence = config.participant_root / "evidence" / QUEST / "jira-attempt-001" / "validation"
        source = next(evidence.glob("*.json"))
        document = json.loads(source.read_text())
        document["outcome"] = "fail"
        document["run_id"] = "failing-run-001"
        for check in document["checks"]:
            check["outcome"] = "fail"
            check["severity"] = "high"
        (evidence / "failing-run-001.json").write_text(json.dumps(document, indent=2))

        root = rebuild(config)
        result = (
            root / "evidence" / QUEST / "validation" / "failing-run-001" / "index.html"
        ).read_text()

        assert "Failed" in result
        assert "your evidence is preserved" in result.lower()
        assert "quest failed" not in result.lower()

    def test_the_evidence_page_does_not_treat_a_failure_as_a_verdict(
        self, config: AppConfig
    ) -> None:
        html = (rebuild(config) / "evidence" / QUEST / "index.html").read_text()
        assert "A failing check is never a failed quest" in html


class TestServiceUnavailable:
    def test_an_offline_page_disables_controls_and_says_why(self, config: AppConfig) -> None:
        html = (rebuild(config) / "evidence" / QUEST / "index.html").read_text()
        assert "Working offline" in html
        assert "Start the local service" in html
        assert "<form" not in html, "an offline page must not offer a control that would fail"

    def test_an_online_page_offers_the_controls(self, config: AppConfig) -> None:
        html = (rebuild(config, online=True) / "evidence" / QUEST / "index.html").read_text()
        assert "Working offline" not in html
        assert "<form" in html

    def test_content_stays_browsable_either_way(self, config: AppConfig) -> None:
        """The curriculum is readable whether or not anything can change."""
        offline = (rebuild(config) / "quests" / QUEST / "index.html").read_text()
        online = (rebuild(config, online=True) / "quests" / QUEST / "index.html").read_text()
        for html in (offline, online):
            assert "How this is judged" in html
            assert "Required evidence" in html


def test_no_participant_at_all_renders_every_page(content_repo: Path) -> None:
    shutil.rmtree(content_repo / "participant")
    (content_repo / "participant").mkdir()
    config = AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")
    root = rebuild(config)
    for relative in ("index.html", "map/index.html", "catalog/index.html", "passport/index.html"):
        assert (root / relative).exists()
    assert "Start at" in (root / "index.html").read_text()
