"""Round 12, C1: a real browser form submission has to actually work.

Every previous UI test either inspected markup or dismissed the confirmation dialog, so
none of them exercised the path a participant or reviewer actually uses: fill the form,
accept the dialog, submit, and have the state on disk change. `Referrer-Policy:
no-referrer` made Chromium send `Origin: null` on a same-origin form POST, which
`_origin_is_acceptable` refused as cross-origin — every action form failed in a real
browser, and nothing here would have caught it.

These tests drive Chromium end to end and read the participant's files afterward. A
cross-origin (or `Origin: null`) POST staying refused is covered in
`tests/security/test_service.py`; this file is about the accepted path.
"""

from __future__ import annotations

import os
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

import yaml  # noqa: E402
from quest_app.build import build_site  # noqa: E402
from quest_app.config import AppConfig  # noqa: E402
from quest_app.errors import ProblemReport  # noqa: E402
from quest_app.pipeline import load_world  # noqa: E402
from quest_app.serve import create_server  # noqa: E402
from quest_app.view_models import online_service_view  # noqa: E402

pytestmark = pytest.mark.ui

SYSTEM_BROWSERS = (
    "/usr/bin/chromium",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
)

START_QUEST = "trello-read-board"
REVIEW_QUEST = "jira-read-assigned-stories"


def _prepared_repo(tmp_path: Path, *, submit_review_quest: bool = False) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    for name in ("content", "schemas", "templates", "assets", "validators"):
        shutil.copytree(
            repo_root / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__")
        )
    shutil.copytree(repo_root / "fixtures" / "participant", tmp_path / "participant")
    if submit_review_quest:
        # A real `create_submission` call, not a hand-edited `state: submitted`: a submitted
        # attempt with no `submission.yaml` behind it is a load error (round 12 E4).
        from quest_app.config import AppConfig
        from quest_app.content_loader import SchemaSet
        from quest_app.errors import ProblemReport
        from quest_app.pipeline import load_world
        from quest_app.review import create_submission
        from quest_app.store import ProgressStore

        config = AppConfig.for_repo(tmp_path, participant_root=tmp_path / "participant")
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        create_submission(
            config,
            ProgressStore(config),
            quest=world.content.quests[REVIEW_QUEST],
            attempt=world.participant.progress.attempt_for(REVIEW_QUEST),
            participant=world.participant,
            schemas=SchemaSet(config.schemas_root),
        )
    return tmp_path


def _serve(tmp_path: Path) -> tuple[object, str]:
    config = AppConfig.for_repo(tmp_path, participant_root=tmp_path / "participant", service_port=0)
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=online_service_view())

    server, _ = create_server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def _stop(server: object) -> None:
    server.shutdown()  # type: ignore[attr-defined]
    server.server_close()  # type: ignore[attr-defined]


@pytest.fixture(scope="module")
def browser() -> Iterator[object]:
    from playwright.sync_api import Error, sync_playwright

    executable = next((path for path in SYSTEM_BROWSERS if Path(path).exists()), None)
    with sync_playwright() as driver:
        try:
            instance = driver.chromium.launch(executable_path=executable)
        except Error as exc:  # pragma: no cover - environment without any Chromium
            message = f"no usable Chromium: {str(exc).splitlines()[0]}"
            if os.environ.get("CI"):
                raise RuntimeError(message) from exc
            pytest.skip(message)
        try:
            yield instance
        finally:
            instance.close()


def test_start_quest_form_submission_changes_state_on_disk(browser: object, tmp_path: Path) -> None:
    """The primary action on an unlocked, not-yet-started quest actually starts it.

    Chromium sends the real `Origin` for this same-origin POST only because the referrer
    policy stopped stripping it to `null`; a revert of that fix makes this dialog-accepting
    submission come back refused, with the participant's progress file untouched.
    """
    repo_root = _prepared_repo(tmp_path)
    progress_path = repo_root / "participant" / "progress.yaml"
    before = yaml.safe_load(progress_path.read_text())
    assert all(a["quest_id"] != START_QUEST for a in before["attempts"])

    server, base = _serve(repo_root)
    try:
        page = browser.new_page()  # type: ignore[attr-defined]
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"{base}/quests/{START_QUEST}/", wait_until="load")

        checkbox = page.locator("#confirm-start-quest")
        assert checkbox.count() == 1, "the quest must be unlocked and not yet started"
        checkbox.check()
        with page.expect_navigation(wait_until="load"):
            page.click("button[type=submit]")

        # A refusal redirects back with `?problem=`; success carries none.
        assert "problem=" not in page.url
        page.close()
    finally:
        _stop(server)

    after = yaml.safe_load(progress_path.read_text())
    attempts = [a for a in after["attempts"] if a["quest_id"] == START_QUEST]
    assert len(attempts) == 1, "the form submission must have created exactly one attempt"
    assert attempts[0]["state"] == "in_progress"


def test_record_review_form_submission_changes_state_on_disk(
    browser: object, tmp_path: Path
) -> None:
    """A reviewer's real, dialog-accepted submission actually records the decision.

    Uses `needs_changes`, which only requires a name and one finding — not the twenty
    character verification statement `approved` demands — so the test stays about the
    form-submission path this finding is about, not the decision's own validation rules.
    """
    repo_root = _prepared_repo(tmp_path, submit_review_quest=True)
    progress_path = repo_root / "participant" / "progress.yaml"
    before = yaml.safe_load(progress_path.read_text())
    (before_attempt,) = [a for a in before["attempts"] if a["quest_id"] == REVIEW_QUEST]
    assert before_attempt["state"] == "submitted"

    server, base = _serve(repo_root)
    try:
        page = browser.new_page()  # type: ignore[attr-defined]
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"{base}/review/{REVIEW_QUEST}/", wait_until="load")

        page.fill("#reviewer_name", "A Reviewer")
        page.select_option("#decision", "needs_changes")
        page.select_option("#finding-severity-0", "medium")
        page.fill("#finding-summary-0", "The evidence is missing the screenshot.")
        page.fill("#finding-evidence-0", "No file under evidence/screenshots/.")
        page.check("#confirm-decision")
        with page.expect_navigation(wait_until="load"):
            page.click("button[type=submit]")

        assert "problem=" not in page.url
        page.close()
    finally:
        _stop(server)

    after = yaml.safe_load(progress_path.read_text())
    (after_attempt,) = [a for a in after["attempts"] if a["quest_id"] == REVIEW_QUEST]
    assert after_attempt["state"] == "needs_changes"

    evidence_dir = repo_root / after_attempt["evidence_path"]
    review_file = evidence_dir / "review.yaml"
    assert review_file.is_file(), "the review record must have been written to disk"
    review = yaml.safe_load(review_file.read_text())
    assert review["decision"] == "needs_changes"
    assert review["reviewer"]["display_name"] == "A Reviewer"
