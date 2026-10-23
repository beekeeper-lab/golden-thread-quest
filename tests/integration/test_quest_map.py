"""The built Quest Map: a drawing for the eye, and the same facts in text for everything else."""

from __future__ import annotations

import re
from pathlib import Path

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world

FIXED_TIME = "2026-09-16T00:00:00+00:00"


def built_map(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, built_at=FIXED_TIME)
    return (config.generated_root / "map" / "index.html").read_text()


def region_ids(root: Path) -> list[str]:
    return sorted(p.stem for p in (root / "content" / "regions").glob("*.yaml"))


def test_every_region_has_a_text_label_with_its_count_and_a_dialog(config: AppConfig) -> None:
    page = built_map(config)
    for region in region_ids(config.repo_root):
        pattern = (
            rf'<a class="map-label[^"]*" href="[^"]*/regions/{region}/"'
            rf' data-region-dialog="map-dialog-{region}" title="[^"]+">'
            r'\s*<span class="map-label-name">([^<]+)</span>'
            r'\s*<span class="map-label-count">(\d+) of (\d+) verified</span>'
        )
        label = re.search(pattern, page)
        assert label, f"{region} has no label link with a count"
        assert int(label.group(2)) <= int(label.group(3))
        assert f'<dialog class="region-dialog" id="map-dialog-{region}"' in page


def test_the_drawing_is_hidden_from_assistive_technology_and_the_labels_are_not(
    config: AppConfig,
) -> None:
    page = built_map(config)
    hidden = page.index('<g aria-hidden="true"')
    first_label = page.index("<foreignObject")
    assert 'class="land-link"' in page[hidden:first_label]
    assert "map-label" not in page[hidden:first_label], (
        "a label must not be inside the hidden group"
    )
    assert page.count('class="land-link"') == page.count('<a class="map-label ')
    # The scenery is decoration, so it sits inside the hidden group.
    for decoration in (
        "continent-land",
        "map-river",
        "map-trail",
        "map-sea-name",
        "decor-mountain",
    ):
        assert decoration in page[hidden:first_label], decoration


def test_the_map_page_uses_no_style_attribute_because_the_policy_blocks_it(
    config: AppConfig,
) -> None:
    assert " style=" not in built_map(config)


def test_the_regions_are_still_available_as_a_list(config: AppConfig) -> None:
    page = built_map(config)
    assert "Show the regions as a list" in page
    assert page.count('class="card accent-') >= 2 * len(region_ids(config.repo_root))


def test_each_region_carries_the_terrain_its_content_names(config: AppConfig) -> None:
    page = built_map(config)
    for region in region_ids(config.repo_root):
        text = (config.repo_root / "content" / "regions" / f"{region}.yaml").read_text()
        terrain = re.search(r"^terrain: (\w+)$", text, re.M)
        expected = terrain.group(1) if terrain else "plain"
        assert f'<use href="#terrain-{expected}"' in page


def test_a_region_that_names_no_terrain_is_drawn_as_plain_land(config: AppConfig) -> None:
    path = config.repo_root / "content" / "regions" / "base-camp.yaml"
    path.write_text(re.sub(r"^terrain: \w+\n", "", path.read_text(), flags=re.M))
    assert "terrain:" not in path.read_text()
    assert '<use href="#terrain-plain"' in built_map(config)
