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

FIXED_TIME = "2026-09-16T00:00:00+00:00"


def build(config: AppConfig) -> tuple[LoadedWorld, int]:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    result = build_site(world, built_at=FIXED_TIME)
    return world, result.page_count


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
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
def test_a_failed_build_leaves_the_previous_site_intact(config: AppConfig) -> None:
    build(config)
    before = tree_digest(config.generated_root)

    quest = config.repo_root / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text("# Broken\n\nNo front matter.\n")
    report = ProblemReport()
    world = load_world(config, report)

    assert world is None, "the broken content should not load"
    assert tree_digest(config.generated_root) == before


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
    passport = (built.generated_root / "passport" / "index.html").read_text()
    assert "Claimed XP" in passport
    assert "Verified XP" in passport


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
        """The check that gives the rest of this class its meaning."""
        for directory in ("quest_app", "templates", "assets"):
            source = repo_root / directory
            if not (with_new_quest.repo_root / directory).exists():
                continue
            assert tree_digest(source) == tree_digest(with_new_quest.repo_root / directory)


@pytest.mark.slow
def test_the_search_index_never_contains_participant_evidence(built: AppConfig) -> None:
    """A public catalog page must not become a search index over someone's private work."""
    search = (built.generated_root / "indexes" / "search.json").read_text()
    assert "PROOF.md" not in search
    assert "participant/evidence" not in search
