"""Generating the site.

The properties asserted here are the ones the plan calls out by name: a clean build, no
broken links, determinism, a failed build that leaves the last good site alone, and — the
one that decides whether this product works at all — a new quest appearing everywhere
without a line of UI code changing.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import LoadedWorld, load_world
from quest_app.serve import FLASH_PLACEHOLDER

FIXED_TIME = "2026-09-16T00:00:00+00:00"


def build(config: AppConfig) -> tuple[LoadedWorld, int]:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    result = build_site(world, built_at=FIXED_TIME)
    return world, result.page_count


def tree_digest(root: Path) -> str:
    """A digest over a directory's *source*, ignoring compiled bytecode.

    `__pycache__` appears in the working tree and not in a fresh copy, so including it would
    make every comparison fail for a reason that has nothing to do with what changed.
    """
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        if not path.is_file() or "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        digest.update(relative.as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def internal_links(root: Path) -> list[tuple[str, str]]:
    broken: list[tuple[str, str]] = []
    for page in sorted(root.rglob("*.html")):
        for href in re.findall(r'(?:href|src)="([^"#?]+)', page.read_text()):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            target = (page.parent / href).resolve()
            if href.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                broken.append((str(page.relative_to(root)), href))
    return broken


@pytest.fixture
def built(config: AppConfig) -> AppConfig:
    build(config)
    return config


@pytest.mark.slow
def test_a_clean_build_produces_every_page(built: AppConfig) -> None:
    root = built.generated_root
    expected = [
        "index.html",
        "map/index.html",
        "catalog/index.html",
        "passport/index.html",
        "health/index.html",
        "review/index.html",
        "evidence/index.html",
        "regions/base-camp/index.html",
        "quests/base-camp-repository-safety/index.html",
        "evidence/base-camp-repository-safety/index.html",
        "build-manifest.json",
        "indexes/search.json",
    ]
    for relative in expected:
        assert (root / relative).exists(), f"missing {relative}"


@pytest.mark.slow
def test_no_broken_internal_links(built: AppConfig) -> None:
    assert internal_links(built.generated_root) == []


@pytest.mark.slow
def test_two_builds_of_the_same_inputs_are_identical(config: AppConfig) -> None:
    """A diff of `generated/` must mean content changed and nothing else."""
    build(config)
    first = tree_digest(config.generated_root)
    build(config)
    assert tree_digest(config.generated_root) == first


@pytest.mark.slow
def test_links_work_when_the_site_is_opened_from_disk(built: AppConfig) -> None:
    """No link may start with `/`, which would mean the filesystem root from a file:// page."""
    for page in sorted(built.generated_root.rglob("*.html")):
        for href in re.findall(r'(?:href|src)="([^"]+)', page.read_text()):
            assert not href.startswith("/"), f"{page.name} links to {href}"


@pytest.mark.slow
def test_broken_content_never_reaches_a_build(config: AppConfig) -> None:
    build(config)
    before = tree_digest(config.generated_root)

    quest = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text("# Broken\n\nNo front matter.\n")
    report = ProblemReport()
    world = load_world(config, report)

    assert world is None, "the broken content should not load"
    assert tree_digest(config.generated_root) == before


@pytest.mark.slow
def test_a_build_that_fails_midway_leaves_the_previous_site_intact(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The atomic swap, exercised by an actual failure rather than only by the happy path.

    The earlier version of this test asserted that broken content does not load and never
    called `build_site` at all, so the rename it was named after was never executed
    (Stage 3 audit S3-M8).
    """
    world, _ = build(config)
    before = tree_digest(config.generated_root)

    import quest_app.build as build_module

    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("disk full halfway through rendering")

    monkeypatch.setattr(build_module, "_write_indexes", explode)

    with pytest.raises(RuntimeError, match="disk full"):
        build_site(world, built_at=FIXED_TIME)

    assert tree_digest(config.generated_root) == before, "the published site was damaged"
    staging = config.generated_root.with_suffix(".building")
    assert not staging.exists() or any(staging.iterdir()), "staging left in an odd state"


@pytest.mark.slow
def test_no_developer_path_reaches_the_generated_site(built: AppConfig) -> None:
    marker = str(built.repo_root)
    for path in built.generated_root.rglob("*"):
        if path.is_file() and path.suffix in {".html", ".json"}:
            assert marker not in path.read_text(), f"{path.name} contains an absolute path"


@pytest.mark.slow
def test_core_content_survives_without_javascript(built: AppConfig) -> None:
    """Generated pages render meaningful content before any script runs."""
    cases = {
        "index.html": "Recommended next",
        "catalog/index.html": "quest(s) match",
        "map/index.html": "What the states mean",
        "quests/jira-read-assigned-stories/index.html": "How this is judged",
        "passport/index.html": "Verified XP",
    }
    for relative, expected in cases.items():
        html = (built.generated_root / relative).read_text()
        without_scripts = re.sub(r"<script.*?</script>", "", html, flags=re.S)
        assert expected in without_scripts, f"{relative} needs JavaScript to say {expected!r}"


@pytest.mark.slow
def test_claimed_and_verified_are_never_presented_as_one_total(built: AppConfig) -> None:
    """Both words appearing somewhere on the page proved nothing about either number.

    The fixture participant has one verified quest worth 20 and one unverified worth 30,
    so the two totals must differ, each must carry its own value, and neither may be shown
    as a single combined figure.
    """
    passport = (built.generated_root / "passport" / "index.html").read_text()
    totals = dict(re.findall(r"<dt>([^<]+)</dt><dd>(\d+)</dd>", passport))

    assert totals.get("Claimed XP") == "50", totals
    assert totals.get("Verified XP") == "20", totals
    assert not re.search(r"<dt>\s*(Total|XP)\s*</dt>", passport), "one total for two facts"


@pytest.mark.slow
def test_an_automated_pass_never_wears_the_reviewer_badge(built: AppConfig) -> None:
    """A machine's check and a person's approval may not carry the same badge.

    The proof row said "Validated" and wore `state-verified`, the gold tick this
    application uses nowhere else but for a reviewer's approval. The word differed; the
    colour and the tick did not, and the badge is what a reader scans.
    """
    badges: list[tuple[str, str, str]] = []
    for page in sorted(built.generated_root.rglob("*.html")):
        for state, label in re.findall(r'class="state state-(\w+)">([^<]*)<', page.read_text()):
            badges.append((page.name, state, label.strip()))

    validated = [b for b in badges if b[2] == "Validated"]
    assert validated, "no page shows a locally validated proof, so this test proves nothing"
    assert all(b[1] == "locally_validated" for b in validated), validated
    assert all(b[2] != "Validated" for b in badges if b[1] == "verified"), badges


class TestAddingContentNeedsNoCodeChange:
    """The product's central claim, asserted rather than trusted.

    A maintainer adds one Markdown file and the quest must appear in its region, the catalog,
    the filters, the search index, the relationship graph and the state index — with no
    change to Python, Jinja2, JavaScript or CSS.
    """

    @pytest.fixture
    def with_new_quest(self, config: AppConfig) -> AppConfig:
        region = config.repo_root / "content" / "quests" / "context-library"
        region.mkdir(parents=True, exist_ok=True)
        (region / "normalize-notes.md").write_text(
            """---
id: context-normalize-notes
version: 1
title: Normalize Meeting Notes Into Context
summary: Turn a raw meeting transcript into normalized local context another agent can use.
region: context-library
level: explorer
xp: 20
estimated_minutes: 45
bookend: intent
tags: [context, markdown, brand-new-tag]
outcomes:
  - Produce normalized context files another agent can consume without further cleanup.
proof:
  required:
    - id: context-files
      type: file
      description: The normalized context file produced from the transcript.
      path: participant/context/meetings/normalized.md
---

# Normalize Meeting Notes Into Context

## Mission

Turn one raw transcript into context an agent can act on.

## Acceptance criteria

1. Every decision in the transcript appears once, with its owner.
2. Ambiguities are listed separately rather than resolved silently.

## Required evidence

The normalized context file.
"""
        )
        build(config)
        return config

    def test_the_quest_page_exists(self, with_new_quest: AppConfig) -> None:
        assert (
            with_new_quest.generated_root / "quests" / "context-normalize-notes" / "index.html"
        ).exists()

    def test_it_appears_in_its_region(self, with_new_quest: AppConfig) -> None:
        region = (
            with_new_quest.generated_root / "regions" / "context-library" / "index.html"
        ).read_text()
        assert "Normalize Meeting Notes Into Context" in region
        assert "No quests here yet" not in region

    def test_it_appears_in_the_catalog(self, with_new_quest: AppConfig) -> None:
        catalog = (with_new_quest.generated_root / "catalog" / "index.html").read_text()
        assert "Normalize Meeting Notes Into Context" in catalog

    def test_its_new_tag_becomes_a_filter(self, with_new_quest: AppConfig) -> None:
        catalog = (with_new_quest.generated_root / "catalog" / "index.html").read_text()
        assert 'value="brand-new-tag"' in catalog

    def test_it_reaches_every_generated_index(self, with_new_quest: AppConfig) -> None:
        indexes = with_new_quest.generated_root / "indexes"
        search = json.loads((indexes / "search.json").read_text())
        assert any(entry["id"] == "context-normalize-notes" for entry in search)
        assert "brand-new-tag" in json.loads((indexes / "tags.json").read_text())
        assert (
            "context-normalize-notes"
            in json.loads((indexes / "regions.json").read_text())["context-library"]
        )
        assert "context-normalize-notes" in json.loads((indexes / "relationships.json").read_text())
        assert "context-normalize-notes" in json.loads((indexes / "states.json").read_text())

    def test_no_ui_file_was_touched(self, with_new_quest: AppConfig, repo_root: Path) -> None:
        """The check that gives the rest of this class its meaning.

        It used to `continue` past any directory the fixture had not copied, and the fixture
        did not copy `quest_app` — so the "no Python was changed" half of the product's
        central claim was never asserted at all. The directories are named and their presence
        is required rather than assumed.
        """
        for directory in ("quest_app", "templates", "assets"):
            copied = with_new_quest.repo_root / directory
            assert copied.exists(), f"the fixture did not copy {directory}, so nothing is checked"
            assert tree_digest(repo_root / directory) == tree_digest(copied), (
                f"adding a quest changed something in {directory}"
            )


@pytest.mark.slow
def test_the_search_index_never_contains_participant_evidence(built: AppConfig) -> None:
    """A public catalog page must not become a search index over someone's private work."""
    search = (built.generated_root / "indexes" / "search.json").read_text()
    assert "PROOF.md" not in search
    assert "participant/evidence" not in search


@pytest.mark.slow
def test_the_content_error_screen_has_a_producer(content_repo: Path) -> None:
    """U11 existed as a template nothing rendered, so it had never been exercised.

    It crashed on the first problem that had no column number the moment it was first
    rendered — which is exactly what a screen with no producer gets to hide.
    """
    from quest_app.build import render_error_page

    config = AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")
    quest = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text("# Broken, no front matter\n")

    report = ProblemReport()
    assert load_world(config, report) is None

    page = render_error_page(config, report)
    html = page.read_text()

    assert page.is_file()
    assert "content.missing_front_matter" in html
    assert "repository-safety.md" in html
    # Written outside `generated/`, because a failed build must leave the last good site
    # standing rather than replacing it with a page of errors.
    assert "local-data" in str(page)
    assert not (config.generated_root / "errors").exists()


@pytest.mark.slow
def test_every_consequential_action_confirms_without_javascript(built: AppConfig) -> None:
    """C21 was a `window.confirm` call, so with scripting off the form posted unguarded."""
    import re as _re

    for page in sorted(built.generated_root.rglob("*.html")):
        html = page.read_text()
        for form in _re.findall(r"<form[^>]*data-confirm[^>]*>.*?</form>", html, _re.S):
            # Named, not merely present: this assertion passed on the reviewer's decision
            # form because of an unrelated checkbox and a `required` on the name field.
            assert _re.search(r'type="checkbox"[^>]*name="confirm"[^>]*required', form), (
                f"{page.relative_to(built.generated_root)} confirms only in script"
            )


@pytest.mark.slow
def test_every_confirming_form_in_the_templates_carries_the_checkbox() -> None:
    """The built pages only prove it for the forms a fixture happens to render.

    The reviewer's decision form is rendered only for an attempt awaiting a decision with
    the service running, which no fixture build produces. So the test above never saw it,
    and its `data-confirm` was a script dialog and nothing else.
    """
    import re as _re

    templates = Path(__file__).resolve().parents[2] / "templates"
    checked = 0
    for template in sorted(templates.rglob("*.j2")):
        for form in _re.findall(
            r"<form[^>]*data-confirm[^>]*>.*?</form>", template.read_text(), _re.S
        ):
            checked += 1
            assert _re.search(r'type="checkbox"[^>]*name="confirm"[^>]*required', form), (
                f"{template.name} confirms only in script"
            )
    assert checked >= 2, "the confirming forms are not being found at all"


@pytest.mark.slow
def test_no_page_gives_two_regions_the_same_name(built: AppConfig) -> None:
    """Two scroll regions labelled "Table" are two things a screen reader cannot tell apart."""
    import re as _re

    for page in sorted(built.generated_root.rglob("*.html")):
        labels = _re.findall(r'role="region"[^>]*aria-label="([^"]+)"', page.read_text())
        relative = page.relative_to(built.generated_root)
        assert len(labels) == len(set(labels)), f"{relative} repeats a region label: {labels}"
        assert "Table" not in labels, f"{relative} names a region after its markup"


@pytest.mark.slow
def test_validation_findings_are_ordered_by_severity(built: AppConfig) -> None:
    from quest_app.build import _checks_by_severity
    from quest_app.progress import CheckResult, ValidationResult

    result = ValidationResult(
        run_id="r",
        validator_id="v",
        validator_version=1,
        quest_id="q",
        attempt_id="a",
        started_at="2026-09-17T00:00:00Z",
        completed_at="2026-09-17T00:00:01Z",
        duration_ms=1,
        outcome="fail",
        redaction_applied=False,
        source="s",
        checks=(
            CheckResult(id="c-low", outcome="warning", summary="s", severity="low"),
            CheckResult(id="c-blocking", outcome="fail", summary="s", severity="blocking"),
            CheckResult(id="c-medium", outcome="fail", summary="s", severity="medium"),
        ),
    )
    assert [check.id for check in _checks_by_severity(result)] == [
        "c-blocking",
        "c-medium",
        "c-low",
    ]


@pytest.mark.slow
def test_a_reviewer_page_exists_for_every_attempt(built: AppConfig) -> None:
    """The queue linked to per-quest reviewer pages that were never generated."""
    import yaml

    progress = yaml.safe_load((built.participant_root / "progress.yaml").read_text())
    for attempt in progress["attempts"]:
        page = built.generated_root / "review" / attempt["quest_id"] / "index.html"
        assert page.exists(), f"no reviewer page for {attempt['quest_id']}"
        html = page.read_text()
        assert attempt["attempt_id"] in html
        assert "Secret and redaction status" in html


@pytest.mark.slow
def test_no_broken_links_with_an_attempt_awaiting_review(config: AppConfig) -> None:
    """The link check passed only because the fixture had nothing in `submitted`.

    A real `create_submission` call is used rather than hand-editing `state: submitted`
    directly: since E4, a `submitted` attempt with no `submission.yaml` behind it is a load
    error, exactly as a hand-written `verified` is.
    """
    from quest_app.content_loader import SchemaSet
    from quest_app.review import create_submission
    from quest_app.store import ProgressStore

    quest_id = "jira-read-assigned-stories"
    setup_report = ProblemReport()
    world = load_world(config, setup_report)
    assert world is not None, setup_report.to_text()
    create_submission(
        config,
        ProgressStore(config),
        quest=world.content.quests[quest_id],
        attempt=world.participant.progress.attempt_for(quest_id),
        participant=world.participant,
        schemas=SchemaSet(config.schemas_root),
    )

    build(config)

    assert internal_links(config.generated_root) == []
    queue = (config.generated_root / "review" / "index.html").read_text()
    assert "jira-read-assigned-stories" in queue


@pytest.mark.slow
def test_a_page_built_by_the_cli_offers_no_live_action(built: AppConfig) -> None:
    """A page built without a service says so, and offers no control that would fail."""
    html = (
        built.generated_root / "evidence" / "jira-read-assigned-stories" / "index.html"
    ).read_text()
    assert "Working offline" in html
    assert "Start the local service" in html
    assert "<form" not in html, "a page with no service must offer no live control"


@pytest.mark.slow
def test_a_page_built_by_the_service_offers_live_actions(config: AppConfig) -> None:
    """The service view was a build-time constant, so every action was permanently dead."""
    from quest_app.view_models import online_service_view

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, built_at=FIXED_TIME, service=online_service_view())

    html = (
        config.generated_root / "evidence" / "jira-read-assigned-stories" / "index.html"
    ).read_text()
    assert "Working offline" not in html
    assert "<form" in html, "the generated site contained no form at all"
    assert 'name="token"' in html
    assert "__GTQ_REQUEST_TOKEN__" in html, "the placeholder is substituted at serve time"


@pytest.mark.slow
def test_a_quest_page_communicates_every_required_element(built: AppConfig) -> None:
    """SCREEN-SPECS U05 lists what a quest page must carry.

    The traceability row for this pointed at a test asserting one heading. These are the
    nine elements the specification actually names.
    """
    html = (
        built.generated_root / "quests" / "jira-read-assigned-stories" / "index.html"
    ).read_text()

    required = {
        "mission": "Mission",
        "outcomes": "What you will be able to do",
        "acceptance criteria": "How this is judged",
        "required evidence": "Required evidence",
        "safety constraints": "Safety",
        "state": "Evidence ready",
        "version": "Version",
        "experience": "XP",
        "estimate": "minutes",
    }
    missing = [name for name, marker in required.items() if marker not in html]
    assert missing == [], missing

    assert "Builder" in html or "Explorer" in html, "the difficulty level is shown"

    # Prerequisites and validators are the two the first version of this omitted. They are
    # checked on a quest that actually declares them rather than on one that does not.
    declared = (
        built.generated_root / "quests" / "playwright-first-independent-test" / "index.html"
    ).read_text()
    assert "Automated checks" in declared, "declared validators are not shown"
    assert "validate-playwright-quality".replace("-", " ") in declared.lower()


@pytest.mark.slow
def test_a_secret_in_evidence_is_redacted_from_the_generated_preview(config: AppConfig) -> None:
    """`generated/` must contain no secret, even one the participant put in their own file.

    The evidence page previews PROOF.md. They can already read their own file, but the
    generated directory can be served and is what a screenshot captures, so the guarantee
    has to hold for it as a whole.
    """
    leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
    evidence = (
        config.participant_root / "evidence" / "jira-read-assigned-stories" / "jira-attempt-001"
    )
    (evidence / "PROOF.md").write_text(f"# Proof\n\nI used token={leaked} to authenticate.\n")

    build(config)

    for page in config.generated_root.rglob("*.html"):
        assert leaked not in page.read_text(), f"{page.name} reproduces a secret"
    preview = (
        config.generated_root / "evidence" / "jira-read-assigned-stories" / "index.html"
    ).read_text()
    assert "[REDACTED]" in preview, "the preview should show that something was removed"


def test_built_pages_show_no_internal_placeholder(built: AppConfig) -> None:
    """A page opened straight from disk must not display an internal marker.

    The flash placeholder is substituted by the running service. A statically built
    page keeps it, so it has to be inert HTML rather than bare text: an external audit
    found the literal string rendering on every offline page, and the whole browser
    suite passed anyway, because every browser test reaches pages through the service
    that substitutes it. This asserts the built artifact directly.
    """
    marker = FLASH_PLACEHOLDER.strip("<!->")
    offenders = []
    for page in sorted(built.generated_root.rglob("*.html")):
        html = page.read_text()
        for match in re.finditer(re.escape(marker), html):
            opening = html.rfind("<!--", 0, match.start())
            closing = html.rfind("-->", 0, match.start())
            if opening == -1 or (closing != -1 and closing > opening):
                offenders.append(str(page.relative_to(built.generated_root)))
    assert not offenders, (
        "internal placeholder is in text position and will render to the reader: "
        + ", ".join(sorted(set(offenders)))
    )


@pytest.mark.slow
def test_source_date_epoch_makes_two_builds_byte_identical(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The documented reproducibility claim, run the way a reader runs it.

    `test_two_builds_of_the_same_inputs_are_identical` pins `built_at` itself, so it passed
    while two consecutive `make build` runs differed on every page: the footer carries the
    real clock. A reader following the release notes could not reproduce what they said.
    """
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()

    build_site(world)
    first = tree_digest(config.generated_root)
    build_site(world)
    assert tree_digest(config.generated_root) == first

    page = (config.generated_root / "index.html").read_text()
    assert "2023-11-14" in page, "the stamp should come from SOURCE_DATE_EPOCH, not the clock"


@pytest.mark.slow
def test_without_source_date_epoch_the_stamp_is_the_clock(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The override is an override, not a new default."""
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    from quest_app.build import build_stamp

    assert "2023-11-14" not in build_stamp()


@pytest.mark.slow
def test_a_file_where_the_staging_directory_goes_does_not_break_every_build(
    config: AppConfig,
) -> None:
    """Debris in the wrong shape used to end every build until someone removed it by hand.

    `rmtree` answers a file with `NotADirectoryError`, which is an `OSError`, so the action
    layer reported it as an advisory on every change and the build itself exited non-zero —
    for ever, because nothing in the application or in `make clean` removed the file.
    """
    debris = config.generated_root.with_suffix(".building")
    debris.write_text("left behind by a build that died")

    build(config)
    assert (config.generated_root / "index.html").exists()
    assert not debris.exists()


def test_make_clean_knows_about_build_debris() -> None:
    """The list is exact, so a path missing from it is a path nobody can remove."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    from clean import REMOVABLE

    assert {"generated", "generated.building", "generated.previous"} <= set(REMOVABLE)
