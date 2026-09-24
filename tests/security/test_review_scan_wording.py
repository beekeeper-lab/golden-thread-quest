"""Round 12, C3: a link out of the package is not the same problem as a secret.

`build.py` used to reduce the secret scan to a single boolean, so a review page whose only
scan finding was a link leading outside the evidence package said "The scan found something
secret-like... rotated" — sending a reviewer looking for a credential that was never there.
A link finding and a secret finding are different failures and need different wording; both
still tell the reviewer not to approve.
"""

from __future__ import annotations

from pathlib import Path

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.view_models import online_service_view

QUEST = "jira-read-assigned-stories"
LINK_TEXT = (
    "The scan found a link in the evidence that leads outside the package, so it could not "
    "be checked or shown. That is not a secret finding"
)
SECRET_TEXT = (
    "The scan found something secret-like. Do not approve until it is removed and the "
    "value rotated."
)


def _review_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=online_service_view())
    page = config.generated_root / "review" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def _package(config: AppConfig) -> Path:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    attempt = world.participant.progress.attempt_for(QUEST)
    return config.resolve_participant_path(attempt.evidence_path)


def test_a_link_out_of_the_package_gets_its_own_message(config: AppConfig, tmp_path: Path) -> None:
    package = _package(config)
    outside = tmp_path / "outside.txt"
    outside.write_text("nothing secret here\n")
    (package / "escape-link.txt").symlink_to(outside)

    html = _review_page_html(config)
    assert LINK_TEXT in html, "a link finding must say it is a link, not a secret"
    assert SECRET_TEXT not in html, "a link finding must not use the secret-finding wording"
    # Still tells the reviewer not to approve, whichever message is shown.
    assert "do not approve" in html.lower()


def test_an_actual_secret_keeps_the_existing_message(config: AppConfig) -> None:
    package = _package(config)
    leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
    (package / "leaked-notes.md").write_text(f"token={leaked}\n")

    html = _review_page_html(config)
    assert SECRET_TEXT in html, "an actual secret finding must keep the existing wording"
    assert LINK_TEXT not in html
