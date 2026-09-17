"""Build performance with a catalog larger than the pilot will ever have.

The budget exists so that a slow build is a caught regression rather than a thing people
gradually stop noticing. It is generous on purpose: the point is to catch an accidental
quadratic, not to police a few hundred milliseconds.
"""

from __future__ import annotations

import time

import pytest
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world

QUEST_COUNT = 200
BUILD_BUDGET_SECONDS = 60.0
PAGE_BUDGET_BYTES = 200_000

QUEST_TEMPLATE = """---
id: {quest_id}
version: 1
title: Synthetic Quest Number {number}
summary: A generated quest used only to measure build time with a large catalog present.
region: {region}
level: explorer
xp: 20
estimated_minutes: 45
bookend: {bookend}
tags: [generated, {tag}]
outcomes:
  - Demonstrate that a large catalog builds in reasonable time.
proof:
  required:
    - id: generated-artifact
      type: file
      description: A file the synthetic quest claims to require as its proof.
      path: participant/context/generated/{quest_id}.md
---

# Synthetic Quest Number {number}

## Mission

Exist in sufficient numbers to make the build do real work.

## Acceptance criteria

1. The quest loads without error.
2. The quest appears in every generated index.

## Required evidence

A generated artifact.
"""


@pytest.fixture
def large_catalogue(config: AppConfig) -> AppConfig:
    regions = [
        path.stem for path in sorted((config.repo_root / "content" / "regions").glob("*.yaml"))
    ]
    bookends = ["intent", "validation", "cross-bookend", "foundation"]
    target = config.repo_root / "content" / "quests" / "generated"
    target.mkdir(parents=True, exist_ok=True)
    for number in range(QUEST_COUNT):
        quest_id = f"generated-quest-{number:04d}"
        (target / f"{quest_id}.md").write_text(
            QUEST_TEMPLATE.format(
                quest_id=quest_id,
                number=number,
                region=regions[number % len(regions)],
                bookend=bookends[number % len(bookends)],
                tag=f"topic-{number % 12}",
            )
        )
    return config


@pytest.mark.slow
def test_a_large_catalogue_builds_within_budget(large_catalogue: AppConfig) -> None:
    report = ProblemReport()
    started = time.monotonic()
    world = load_world(large_catalogue, report)
    load_seconds = time.monotonic() - started

    assert world is not None, report.to_text()
    assert len(world.content.quests) >= QUEST_COUNT

    started = time.monotonic()
    result = build_site(world, built_at="2026-09-17T00:00:00+00:00")
    build_seconds = time.monotonic() - started

    total = load_seconds + build_seconds
    assert total < BUILD_BUDGET_SECONDS, (
        f"{len(world.content.quests)} quests took {total:.1f}s "
        f"(load {load_seconds:.1f}s, build {build_seconds:.1f}s)"
    )
    # Roughly two pages per quest plus the fixed screens and the tag pages.
    assert result.page_count > QUEST_COUNT * 2


# A page about one thing must not grow with the size of the catalog. A page that lists a
# collection is proportional to that collection by definition — the catalog, a tag, a
# region, the map — so the rule is about the first kind, not the second.
COLLECTION_PREFIXES = (
    "catalog",
    "tags",
    "regions",
    "map",
    "evidence/index",
    "review",
    "index.html",
)


@pytest.mark.slow
def test_a_page_about_one_thing_does_not_grow_with_the_catalogue(
    large_catalogue: AppConfig,
) -> None:
    """The invariant that matters: a quest page is the same size whatever else exists.

    A page that lists a collection is allowed to be large, because that is what it is for.
    A quest detail page that grew with the catalog would mean something was leaking the
    whole content set into every page.
    """
    report = ProblemReport()
    world = load_world(large_catalogue, report)
    assert world is not None
    build_site(world, built_at="2026-09-17T00:00:00+00:00")

    oversized = [
        (str(path.relative_to(large_catalogue.generated_root)), path.stat().st_size)
        for path in large_catalogue.generated_root.rglob("*.html")
        if path.stat().st_size > PAGE_BUDGET_BYTES
    ]
    unexpected = [entry for entry in oversized if not entry[0].startswith(COLLECTION_PREFIXES)]
    assert unexpected == [], unexpected


@pytest.mark.slow
def test_a_quest_page_stays_small_however_many_quests_exist(large_catalogue: AppConfig) -> None:
    report = ProblemReport()
    world = load_world(large_catalogue, report)
    assert world is not None
    build_site(world, built_at="2026-09-17T00:00:00+00:00")

    quest_pages = sorted((large_catalogue.generated_root / "quests").glob("*/index.html"))
    assert len(quest_pages) > QUEST_COUNT
    largest = max(path.stat().st_size for path in quest_pages)
    assert largest < 60_000, f"the largest quest page is {largest} bytes"


@pytest.mark.slow
def test_content_loading_scales_roughly_linearly(
    config: AppConfig, large_catalogue: AppConfig
) -> None:
    """A guard against an accidental quadratic in cross-document validation.

    Timing is noisy, so the assertion is deliberately loose: it catches an order-of-magnitude
    regression, not a percentage.
    """
    del config
    report = ProblemReport()
    started = time.monotonic()
    world = load_world(large_catalogue, report)
    seconds = time.monotonic() - started
    assert world is not None
    per_quest = seconds / len(world.content.quests)
    assert per_quest < 0.05, f"{per_quest * 1000:.1f}ms per quest"
