"""Structural accessibility of the generated HTML.

These parse the output rather than drive a browser, so they run everywhere and fast. They
cover the failures that are structural and therefore permanent — a skipped heading level, a
control with no label, a table with no headers, a skip link pointing at nothing — which is
most of what goes wrong and all of what a template can get wrong once and then repeat on
every page.

Browser-driven behavior (focus management, keyboard flows, live regions, axe) is in
`test_participant_flows.py`, which needs Playwright.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world


@pytest.fixture(scope="module")
def generated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One build, reused by every test in this module."""
    import shutil

    repo_root = Path(__file__).resolve().parents[2]
    tmp = tmp_path_factory.mktemp("site")
    for name in ("content", "schemas", "templates", "assets", "validators"):
        shutil.copytree(repo_root / name, tmp / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(repo_root / "fixtures" / "participant", tmp / "participant")
    config = AppConfig.for_repo(tmp, participant_root=tmp / "participant")

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, built_at="2026-09-16T00:00:00+00:00")
    return config.generated_root


def pages(root: Path) -> list[Path]:
    return sorted(root.rglob("*.html"))


class Collector(HTMLParser):
    """Enough of a parse to answer structural questions, with no dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str]] = []
        self.ids: set[str] = set()
        self.labels_for: set[str] = set()
        self.controls: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.landmarks: list[str] = []
        self.tables = 0
        self.table_headers = 0
        self.images: list[dict[str, str]] = []
        self._heading: int | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: (value or "") for key, value in attrs}
        if identifier := attributes.get("id"):
            self.ids.add(identifier)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = int(tag[1])
            self._text = []
        elif tag == "label":
            if target := attributes.get("for"):
                self.labels_for.add(target)
        elif tag in {"input", "select", "textarea"}:
            if attributes.get("type") not in {"hidden", "submit", "reset", "button"}:
                self.controls.append({"tag": tag, **attributes})
        elif tag == "a":
            self.links.append(attributes)
        elif tag in {"main", "nav", "header", "footer", "aside"}:
            self.landmarks.append(tag)
        elif tag == "table":
            self.tables += 1
        elif tag == "th":
            self.table_headers += 1
        elif tag == "img":
            self.images.append(attributes)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._heading is not None:
            self.headings.append((self._heading, "".join(self._text).strip()))
            self._heading = None

    def handle_data(self, data: str) -> None:
        if self._heading is not None:
            self._text.append(data)


def parse(path: Path) -> Collector:
    collector = Collector()
    collector.feed(path.read_text())
    return collector


def test_every_page_has_exactly_one_first_level_heading(generated: Path) -> None:
    for page in pages(generated):
        levels = [level for level, _ in parse(page).headings]
        assert levels.count(1) == 1, f"{page.relative_to(generated)} has {levels.count(1)} h1"


def test_heading_levels_never_skip(generated: Path) -> None:
    """A skipped level is what turns a heading outline into a guess for a screen reader."""
    for page in pages(generated):
        previous = 0
        for level, text in parse(page).headings:
            assert level <= previous + 1, (
                f"{page.relative_to(generated)} jumps from h{previous} to h{level} at {text!r}"
            )
            previous = level


def test_every_page_has_the_expected_landmarks(generated: Path) -> None:
    for page in pages(generated):
        landmarks = parse(page).landmarks
        assert "main" in landmarks, f"{page.relative_to(generated)} has no main landmark"
        assert "nav" in landmarks, f"{page.relative_to(generated)} has no navigation"
        assert "footer" in landmarks


def test_the_skip_link_points_at_something_that_exists(generated: Path) -> None:
    for page in pages(generated):
        collector = parse(page)
        skip = next((link for link in collector.links if "skip" in (link.get("class") or "")), None)
        assert skip is not None, f"{page.relative_to(generated)} has no skip link"
        target = (skip.get("href") or "").lstrip("#")
        assert target in collector.ids, (
            f"{page.relative_to(generated)} skip link targets {target!r}"
        )


def test_the_skip_target_can_receive_focus(generated: Path) -> None:
    """A skip link that moves focus nowhere is worse than none: it looks like it worked."""
    html = (generated / "index.html").read_text()
    assert re.search(r'<main[^>]*id="main"[^>]*tabindex="-1"', html)


def test_the_current_page_is_marked_programmatically(generated: Path) -> None:
    for page in pages(generated):
        html = page.read_text()
        assert 'aria-current="page"' in html, f"{page.relative_to(generated)} marks no current page"


def test_every_form_control_has_a_label(generated: Path) -> None:
    for page in pages(generated):
        collector = parse(page)
        for control in collector.controls:
            identifier = control.get("id")
            labeled = (
                (identifier and identifier in collector.labels_for)
                or control.get("aria-label")
                or control.get("aria-labelledby")
            )
            assert labeled, f"{page.relative_to(generated)}: unlabelled {control['tag']}"


def test_every_table_has_header_cells(generated: Path) -> None:
    for page in pages(generated):
        collector = parse(page)
        if collector.tables:
            assert collector.table_headers >= collector.tables, page.relative_to(generated)


def test_no_remote_resource_is_referenced(generated: Path) -> None:
    """No remote script, style, font or image: the security policy forbids it by default."""
    for page in pages(generated):
        html = page.read_text()
        remote = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
        assert remote == [], f"{page.relative_to(generated)} loads {remote}"


def test_external_links_carry_noopener(generated: Path) -> None:
    for page in pages(generated):
        for link in parse(page).links:
            href = link.get("href", "")
            if href.startswith(("http://", "https://")):
                assert "noopener" in link.get("rel", ""), f"{page.relative_to(generated)}: {href}"


def test_status_is_never_communicated_by_colour_alone(generated: Path) -> None:
    """Every state chip carries its label as text; the CSS adds a glyph on top."""
    html = (generated / "map" / "index.html").read_text()
    for label in ("Locked", "Available", "In progress", "Verified", "Needs changes"):
        assert label in html, f"the legend does not name {label!r}"


def test_the_stylesheet_never_removes_a_focus_outline_without_replacing_it(
    generated: Path,
) -> None:
    css = (generated / "assets" / "css" / "app.css").read_text()
    for block in re.findall(r"[^{}]*\{[^}]*outline:\s*none[^}]*\}", css):
        assert "box-shadow" in block, f"focus removed with no replacement: {block[:80]}"


def test_reduced_motion_is_respected(generated: Path) -> None:
    css = (generated / "assets" / "css" / "tokens.css").read_text()
    assert "prefers-reduced-motion" in css


def test_the_content_security_policy_is_restrictive(generated: Path) -> None:
    html = (generated / "index.html").read_text()
    policy = re.search(r'Content-Security-Policy" content="([^"]+)"', html)
    assert policy
    directives = policy.group(1)
    assert "default-src 'none'" in directives
    assert "unsafe-inline" not in directives
    assert "unsafe-eval" not in directives
    # `frame-ancestors` belongs in the header only: a browser ignores it in a meta element
    # and logs an error. The service's header is asserted in tests/security/test_service.py.
    assert "frame-ancestors" not in directives


def test_the_referrer_meta_tag_is_same_origin(generated: Path) -> None:
    """T6 (round 13): the header is asserted in `tests/security/test_service.py`, but a page
    opened straight from disk has no server to send it — only this meta copy protects that
    case (round 12, C1), and nothing asserted it was actually there.
    """
    for page in pages(generated):
        html = page.read_text()
        assert re.search(r'<meta\s+name="referrer"\s+content="same-origin">', html), (
            f"{page.relative_to(generated)} has no same-origin referrer meta tag"
        )


def test_no_inline_script_or_style_would_be_blocked_by_that_policy(generated: Path) -> None:
    """A policy with no 'unsafe-inline' means an inline handler silently does nothing."""
    for page in pages(generated):
        html = page.read_text()
        assert not re.search(r"<script(?![^>]*\ssrc=)[^>]*>\s*\S", html), page.relative_to(
            generated
        )
        assert not re.search(r"\son(?:click|load|error|submit)=", html), page.relative_to(generated)


def test_the_claimed_and_verified_distinction_appears_wherever_progress_does(
    generated: Path,
) -> None:
    for relative in ("index.html", "passport/index.html"):
        html = (generated / relative).read_text()
        assert "Claimed" in html and "Verified" in html, relative
