"""Browser-driven checks: the things only a real engine can answer.

The Stage 3 audit could not run a browser and flagged two questions as needing one — whether
the Content Security Policy blocks the site's own stylesheet when a page is opened from
disk, and whether catalog filtering actually works. Both are settled here.
"""

from __future__ import annotations

import os
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import ClassVar

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
            # In CI a missing browser is a broken job, not a reason to pass quietly: a
            # suite that skips itself is one nobody notices has stopped running.
            message = f"no usable Chromium: {str(exc).splitlines()[0]}"
            if os.environ.get("CI"):
                raise RuntimeError(message) from exc
            pytest.skip(message)
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
        """Home to a quest to its evidence workspace, with the keyboard only.

        The first version called `.click()` — a mouse click — and stopped at the region page
        despite a docstring promising the evidence workspace. Every step here is a real key
        press, and the journey ends where the docstring says it does.
        """
        page = page_for(browser, f"{served}/")

        for route, name in (
            ("/catalog/", "Catalog"),
            ("/quests/", "Synchronize"),
            ("/evidence/jira-read-assigned-stories/", "evidence workspace"),
        ):
            target = page.get_by_role("link", name=name).first
            target.focus()
            assert target.evaluate("el => el === document.activeElement"), name
            target.press("Enter")
            page.wait_for_load_state("load")
            assert route in page.url, f"keyboard navigation did not reach {route}"

        assert page.get_by_role("heading", level=1).first.is_visible()
        page.close()


AXE = Path(__file__).resolve().parents[2] / "vendor" / "axe.min.js"

# The rule set the product is held to. `docs/ACCESSIBILITY-AND-DESIGN.md` targets WCAG 2.2
# AA, and axe's tags are the closest expression of that.
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]

AUDITED_PAGES = [
    "/",
    "/map/",
    "/catalog/",
    "/regions/base-camp/",
    "/quests/jira-read-assigned-stories/",
    "/evidence/",
    "/evidence/jira-read-assigned-stories/",
    "/passport/",
    "/health/",
    "/review/",
    "/tags/jira/",
]


def axe_violations(page: object, tags: list[str] | None = None) -> list[dict[str, object]]:
    """Serious and critical axe violations on the current page."""
    page.add_script_tag(path=str(AXE))  # type: ignore[attr-defined]
    result = page.evaluate(  # type: ignore[attr-defined]
        "async (tags) => await axe.run(document, {runOnly: {type: 'tag', values: tags}})",
        tags or AXE_TAGS,
    )
    return [
        violation
        for violation in result["violations"]
        if violation["impact"] in ("serious", "critical")
    ]


@pytest.mark.parametrize("route", AUDITED_PAGES)
def test_no_serious_accessibility_violation(browser: object, served: str, route: str) -> None:
    """The plan's requirement, as a check rather than an intention.

    Only serious and critical impacts fail the build. Minor and moderate findings are worth
    reading but are judgement calls, and a suite that fails on all of them is a suite people
    learn to ignore.

    The context bypasses the Content Security Policy because axe is injected as an inline
    script and the policy — correctly — refuses one. That the injection had to be worked
    around is itself evidence the policy is doing its job; `TestStylesActuallyApply` checks
    the policy with it enforced.
    """
    context = browser.new_context(bypass_csp=True)  # type: ignore[attr-defined]
    page = context.new_page()
    page.goto(f"{served}{route}", wait_until="load")
    violations = axe_violations(page)
    page.close()
    context.close()
    assert violations == [], [
        f"{v['id']}: {v['help']} ({len(v['nodes'])} node(s))" for v in violations
    ]


class TestResponsive:
    """The viewports `docs/ACCESSIBILITY-AND-DESIGN.md` names for visual acceptance."""

    VIEWPORTS: ClassVar[dict[str, tuple[int, int]]] = {
        "desktop": (1440, 900),
        "laptop": (1280, 720),
        "tablet": (768, 1024),
        "phone": (390, 844),
    }

    @pytest.mark.parametrize("name", list(VIEWPORTS))
    def test_no_horizontal_scrolling(self, browser: object, served: str, name: str) -> None:
        """Every audited page, not a hand-picked four.

        The first version checked home, catalogue, one quest and the passport. The evidence
        workspace overflowed by 179px at phone width and nothing saw it, because it was not
        on the list. The list is now the same one the accessibility audit uses.
        """
        width, height = self.VIEWPORTS[name]
        context = browser.new_context(viewport={"width": width, "height": height})  # type: ignore[attr-defined]
        page = context.new_page()
        try:
            for route in AUDITED_PAGES:
                page.goto(f"{served}{route}", wait_until="load")
                overflow = page.evaluate(
                    "document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                assert overflow <= 1, f"{route} scrolls horizontally by {overflow}px at {name}"
        finally:
            page.close()
            context.close()

    @pytest.mark.parametrize("route", AUDITED_PAGES)
    def test_usable_at_two_hundred_percent_zoom(
        self, browser: object, served: str, route: str
    ) -> None:
        """Doubling the scale factor halves the effective viewport, which is what 200% means.

        Every audited page, for the same reason as above: checking only the catalogue is how
        a 246px overflow on the evidence workspace went unnoticed.
        """
        context = browser.new_context(viewport={"width": 720, "height": 450})  # type: ignore[attr-defined]
        page = context.new_page()
        try:
            page.goto(f"{served}{route}", wait_until="load")
            page.evaluate("document.body.style.zoom = '2'")
            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            assert overflow <= 1, f"{route} scrolls horizontally by {overflow}px at 200% zoom"
        finally:
            page.close()
            context.close()

    def test_a_scrollable_table_can_be_reached_by_keyboard(
        self, browser: object, served: str
    ) -> None:
        """A scroll container a keyboard user cannot focus is not an alternative to stacking."""
        page = page_for(browser, f"{served}/health/")
        containers = page.eval_on_selector_all(
            ".table-scroll",
            "nodes => nodes.map(n => ({tab: n.getAttribute('tabindex'), "
            "label: n.getAttribute('aria-label')}))",
        )
        page.close()
        assert containers
        for container in containers:
            assert container["tab"] == "0", container
            assert container["label"], container

    def test_the_primary_action_is_reachable_on_a_phone(self, browser: object, served: str) -> None:
        context = browser.new_context(viewport={"width": 390, "height": 844})  # type: ignore[attr-defined]
        page = context.new_page()
        try:
            page.goto(f"{served}/quests/jira-read-assigned-stories/", wait_until="load")
            action = page.locator(".button").first
            assert action.is_visible()
            box = action.bounding_box()
            assert box is not None and box["width"] <= 390
        finally:
            page.close()
            context.close()


def test_no_essential_action_requires_hover(browser: object, served: str) -> None:
    """Hover-only information is unreachable on a touch screen and to a keyboard."""
    page = page_for(browser, f"{served}/catalog/")
    hidden = page.evaluate(
        """() => Array.from(document.querySelectorAll('a, button'))
              .filter(el => {
                const s = getComputedStyle(el);
                return s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0';
              })
              .filter(el => !el.hasAttribute('hidden'))
              .map(el => el.textContent.trim().slice(0, 40))"""
    )
    page.close()
    assert hidden == [], hidden
