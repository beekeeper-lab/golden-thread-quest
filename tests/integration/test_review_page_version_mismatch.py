"""Round 12, C5: a reviewer reading a checklist built for a version the attempt was not on.

`build_proof_views` detects each required-evidence item against the *published* quest's
proof paths. When a proof path is renamed in a newer version, an attempt still on the older
one shows "Not detected" for an item it may actually have satisfied, with nothing on the
page saying the checklist and the attempt disagree on which version they mean.
"""

from __future__ import annotations

import yaml
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.view_models import offline_service_view

QUEST = "jira-read-assigned-stories"
NOTE_FRAGMENT = "a proof path that has since been renamed"


def _set_attempt_quest_version(config: AppConfig, version: int) -> None:
    progress = config.participant_root / "progress.yaml"
    data = yaml.safe_load(progress.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["quest_version"] = version
    progress.write_text(yaml.safe_dump(data, sort_keys=False))


def _review_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=offline_service_view())
    page = config.generated_root / "review" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def test_a_version_mismatch_notes_it_on_the_missing_checklist_items(
    config: AppConfig,
) -> None:
    _set_attempt_quest_version(config, 1)  # the published quest is version 2
    html = _review_page_html(config)

    assert "Not detected" in html, "the fixture's proof files genuinely are not present"
    assert NOTE_FRAGMENT in html, (
        "a version mismatch must be noted next to a missing required-evidence item"
    )


def test_no_such_note_when_the_attempt_matches_the_published_version(
    config: AppConfig,
) -> None:
    _set_attempt_quest_version(config, 2)  # matches the published quest exactly
    html = _review_page_html(config)

    assert "Not detected" in html
    assert NOTE_FRAGMENT not in html, (
        "the note is about a version mismatch that exists, not a permanent disclaimer"
    )
