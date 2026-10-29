"""A quest waiting for a review offers "Check for my review", and no other quest does."""

from __future__ import annotations

from pathlib import Path

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.view_models import offline_service_view, online_service_view
from test_cli_actions import REVIEWED, run, submitted, unlock


def _page(config: AppConfig, quest: str, *, online: bool) -> str:
    world = load_world(config, ProblemReport())
    assert world is not None
    build_site(world, service=online_service_view() if online else offline_service_view())
    return (config.generated_root / "evidence" / quest / "index.html").read_text(encoding="utf-8")


def test_a_submitted_quest_offers_the_button_and_says_nobody_needs_telling(
    content_repo: Path, tmp_path: Path
) -> None:
    participant = tmp_path / "participant"
    submitted(participant)
    config = AppConfig.for_repo(content_repo, participant_root=participant)

    html = _page(config, REVIEWED, online=True)

    assert "Check for my review" in html
    assert f"/api/action/check-for-review/{REVIEWED}/" in html
    assert "You do not need to tell anyone" in html


def test_offline_the_button_is_disabled_and_says_why(content_repo: Path, tmp_path: Path) -> None:
    participant = tmp_path / "participant"
    submitted(participant)
    config = AppConfig.for_repo(content_repo, participant_root=participant)

    html = _page(config, REVIEWED, online=False)

    assert "Check for my review" in html
    assert "gtq get-review" in html


def test_a_quest_not_yet_submitted_has_no_button(content_repo: Path, tmp_path: Path) -> None:
    participant = tmp_path / "participant"
    unlock(participant, REVIEWED)
    started = run(participant, "start-quest", "--quest", REVIEWED)
    assert started.returncode == 0, started.stderr
    config = AppConfig.for_repo(content_repo, participant_root=participant)

    assert "Check for my review" not in _page(config, REVIEWED, online=True)
