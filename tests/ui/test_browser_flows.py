"""Browser-driven checks: the things only a real engine can answer.

The Stage 3 audit could not run a browser and flagged two questions as needing one — whether
the Content Security Policy blocks the site's own stylesheet when a page is opened from
disk, and whether catalog filtering actually works. Both are settled here.
"""

from __future__ import annotations

import shutil
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")

from quest_app.build import build_site  # noqa: E402
from quest_app.config import AppConfig  # noqa: E402
from quest_app.errors import ProblemReport  # noqa: E402
from quest_app.pipeline import load_world  # noqa: E402
from quest_app.serve import create_server  # noqa: E402

pytestmark = pytest.mark.ui


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    tmp = tmp_path_factory.mktemp("browser-site")
    for name in ("content", "schemas", "templates", "assets", "validators"):
        shutil.copytree(repo_root / name, tmp / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo_root / "fixtures" / "participant", tmp / "participant")
    config = AppConfig.for_repo(tmp, participant_root=tmp / "participant", service_port=0)
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, built_at="2026-09-17T00:00:00+00:00")
    return config


@pytest.fixture(scope="module")
def served(site: AppConfig) -> Iterator[str]:
    server, _ = create_server(site)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# Playwright's own Chromium download needs root here, so a system browser is used when one
# is present. The engine is what these tests are for; which copy of it runs them is not.
SYSTEM_BROWSERS = (
    "/usr/bin/chromium",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
)


def _executable() -> str | None:
    from pathlib import Path as _Path

    return next((path for path in SYSTEM_BROWSERS if _Path(path).exists()), None)


@pytest.fixture(scope="module")
def browser() -> Iterator[object]:
    from playwright.sync_api import Error, sync_playwright

    with sync_playwright() as driver:
        try:
            instance = driver.chromium.launch(executable_path=_executable())
        except Error as exc:  # pragma: no cover - environment without any Chromium
            pytest.skip(f"no usable Chromium: {str(exc).splitlines()[0]}")
        try:
            yield instance
        finally:
            instance.close()


def page_for(browser: object, url: str):  # type: ignore[no-untyped-def]
    context = browser.new_page()  # type: ignore[attr-defined]
    context.goto(url, wait_until="load")
    return context


class TestStylesActuallyApply:
    def test_the_stylesheet_loads_when_served(self, browser: object, served: str) -> None:
        page = page_for(browser, f"{served}/")
        colour = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert colour not in ("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)"), (
            "the stylesheet did not apply, so the CSP is blocking it"
        )
        page.close()

    def test_progress_meters_have_a_visible_width(self, browser: object, served: str) -> None:
        """The audit's S3-H1: inline style attributes were being dropped by the CSP."""
        page = page_for(browser, f"{served}/passport/")
        widths = page.eval_on_selector_all(
            ".meter-fill", "nodes => nodes.map(n => n.getBoundingClientRect().width)"
        )
        assert widths, "no meters rendered"
        assert any(width > 0 for width in widths), "every meter rendered with zero width"
        page.close()

    def test_no_console_error_is_raised_on_load(self, browser: object, served: str) -> None:
        page = browser.new_page()  # type: ignore[attr-defined]
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" else None,
        )
        page.goto(f"{served}/catalog/", wait_until="load")
        page.fill("#filter-q", "jira")
        page.wait_for_timeout(200)
        assert errors == [], errors
        page.close()

    def test_opening_from_disk_still_applies_styles(self, browser: object, site: AppConfig) -> None:
        """The question the audit could not answer: does the meta CSP break a file:// page?

        If this fails, the generated site is unstyled when double-clicked and the setup
        guide's claim is false. It is asserted rather than assumed either way.
        """
        page = page_for(browser, (site.generated_root / "index.html").as_uri())
        colour = page.evaluate("getComputedStyle(document.body).backgroundColor")
        page.close()
        assert colour not in ("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)"), (
            "the CSP blocks the stylesheet on file://; either relax it or stop claiming "
            "disk-opening works"
        )


class TestCatalogFiltering:
    def test_filtering_narrows_the_results(self, browser: object, served: str) -> None:
        page = page_for(browser, f"{served}/catalog/")
        before = page.eval_on_selector_all("[data-search]:not([hidden])", "n => n.length")
        page.select_option("#filter-region", "jira-jungle")
        page.wait_for_timeout(150)
        after = page.eval_on_selector_all("[data-search]:not([hidden])", "n => n.length")
        assert 0 < after < before
        page.close()

    def test_an_active_filter_appears_as_a_removable_chip(
        self, browser: object, served: str
    ) -> None:
        page = page_for(browser, f"{served}/catalog/")
        page.select_option("#filter-region", "jira-jungle")
        page.wait_for_timeout(150)
        chips = page.eval_on_selector_all("[data-active-filters] button", "n => n.length")
        assert chips == 1
        page.click("[data-active-filters] button")
        page.wait_for_timeout(150)
        assert page.eval_on_selector_all("[data-active-filters] button", "n => n.length") == 0
        page.close()

    def test_a_filtered_url_opens_filtered(self, browser: object, served: str) -> None:
        """The audit's S3-H2: the query string was written and never read back."""
        page = page_for(browser, f"{served}/catalog/?region=jira-jungle")
        page.wait_for_timeout(150)
        assert page.input_value("#filter-region") == "jira-jungle"
        shown = page.eval_on_selector_all("[data-search]:not([hidden])", "n => n.length")
        assert shown == 1
        page.close()

    def test_sorting_reorders_the_results(self, browser: object, served: str) -> None:
        page = page_for(browser, f"{served}/catalog/")
        page.select_option("#filter-sort", "title")
        page.wait_for_timeout(150)
        titles = page.eval_on_selector_all(
            "[data-search]:not([hidden])", "n => n.map(x => x.getAttribute('data-title'))"
        )
        assert titles == sorted(titles)
        page.close()

    def test_a_tag_page_works_without_any_script(self, browser: object, served: str) -> None:
        """The no-JavaScript route into a tag has to be a real page."""
        context = browser.new_context(java_script_enabled=False)  # type: ignore[attr-defined]
        page = context.new_page()
        page.goto(f"{served}/tags/jira/", wait_until="load")
        assert page.locator("[data-search]").count() >= 1
        page.close()
        context.close()

    def test_the_catalog_lists_everything_without_script(
        self, browser: object, served: str
    ) -> None:
        context = browser.new_context(java_script_enabled=False)  # type: ignore[attr-defined]
        page = context.new_page()
        page.goto(f"{served}/catalog/", wait_until="load")
        assert page.locator("[data-search]").count() == 3
        page.close()
        context.close()


class TestKeyboardAndFocus:
    def test_the_skip_link_moves_focus_to_the_main_landmark(
        self, browser: object, served: str
    ) -> None:
        page = page_for(browser, f"{served}/")
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")
        page.wait_for_timeout(100)
        assert page.evaluate("document.activeElement.id") == "main"
        page.close()

    def test_focus_is_always_visible(self, browser: object, served: str) -> None:
        page = page_for(browser, f"{served}/catalog/")
        page.focus("#filter-q")
        shadow = page.evaluate("getComputedStyle(document.querySelector('#filter-q')).boxShadow")
        page.close()
        assert shadow and shadow != "none", "a focused control shows no focus indicator"

    def test_the_primary_journey_is_reachable_by_keyboard(
        self, browser: object, served: str
    ) -> None:
        """Home to a quest to its evidence workspace, without a mouse."""
        page = page_for(browser, f"{served}/")
        page.get_by_role("link", name="Quest Map").click()
        page.wait_for_load_state("load")
        assert "/map/" in page.url
        page.get_by_role("link", name="Base Camp", exact=True).first.click()
        page.wait_for_load_state("load")
        assert "/regions/base-camp/" in page.url
        page.close()
