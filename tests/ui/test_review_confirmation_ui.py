"""The reviewer's confirmation follows the decision they choose, in a real browser."""

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
from quest_app.state_machine import CONFIRMATIONS, DECISION_CONFIRMATIONS  # noqa: E402
from quest_app.view_models import online_service_view  # noqa: E402

pytestmark = pytest.mark.ui

QUEST = "jira-read-assigned-stories"
SYSTEM_BROWSERS = (
    "/usr/bin/chromium",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
)


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    repo_root = Path(__file__).resolve().parents[2]
    tmp = tmp_path_factory.mktemp("review-confirmation")
    for name in ("content", "schemas", "templates", "assets", "validators"):
        shutil.copytree(repo_root / name, tmp / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo_root / "fixtures" / "participant", tmp / "participant")
    progress = tmp / "participant" / "progress.yaml"
    data = yaml.safe_load(progress.read_text())
    for attempt in data["attempts"]:
        if attempt["quest_id"] == QUEST:
            attempt["state"] = "submitted"
    progress.write_text(yaml.safe_dump(data, sort_keys=False))
    config = AppConfig.for_repo(tmp, participant_root=tmp / "participant", service_port=0)
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, service=online_service_view())

    server, _ = create_server(config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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


def test_the_confirmation_follows_the_chosen_decision(browser: object, served: str) -> None:
    page = browser.new_page()  # type: ignore[attr-defined]
    page.goto(f"{served}/review/{QUEST}/", wait_until="load")
    label = page.locator("[data-confirm-label]")
    form = page.locator("form[data-confirm]")
    assert label.inner_text().strip() == CONFIRMATIONS["record-review"]

    for decision, wording in DECISION_CONFIRMATIONS.items():
        page.select_option("#decision", decision)
        assert label.inner_text().strip() == wording, decision
        assert form.get_attribute("data-confirm") == f"{wording}?", decision

    # The dialog shows the chosen decision's words. Dismissed, so nothing is recorded.
    page.select_option("#decision", "needs_changes")
    shown: list[str] = []

    def dismiss(dialog: object) -> None:
        shown.append(dialog.message)  # type: ignore[attr-defined]
        dialog.dismiss()  # type: ignore[attr-defined]

    page.on("dialog", dismiss)
    page.fill("#reviewer_name", "A Reviewer")
    page.check("#confirm-decision")
    page.click("button[type=submit]")
    assert shown == [f"{DECISION_CONFIRMATIONS['needs_changes']}?"]
    page.close()
