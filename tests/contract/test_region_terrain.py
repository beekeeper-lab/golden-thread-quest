"""A region names its terrain from a fixed vocabulary, and every name has a picture."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent.parent
SYMBOLS = ROOT / "templates" / "components" / "terrain_symbols.html.j2"

BASE = {
    "id": "example",
    "version": 1,
    "title": "Example Region",
    "summary": "A region used only to hold the terrain rule in place.",
    "order": 1,
    "accent": "slate",
    "outcomes": ["Demonstrate something worth a reviewer's time."],
}


def terrain_names(schemas: dict[str, dict[str, object]]) -> list[str]:
    properties = schemas["region"]["properties"]
    assert isinstance(properties, dict)
    return list(properties["terrain"]["enum"])  # type: ignore[index]


def test_every_terrain_the_schema_allows_has_a_symbol_and_no_symbol_is_unreachable(
    schemas: dict[str, dict[str, object]],
) -> None:
    drawn = set(re.findall(r'<symbol id="terrain-([a-z]+)"', SYMBOLS.read_text()))
    assert drawn == set(terrain_names(schemas))


def test_a_region_may_omit_its_terrain_and_a_known_one_is_accepted(
    schemas: dict[str, dict[str, object]],
) -> None:
    validator = Draft202012Validator(schemas["region"])
    assert list(validator.iter_errors(BASE)) == []
    for name in terrain_names(schemas):
        assert list(validator.iter_errors({**BASE, "terrain": name})) == [], name


@pytest.mark.parametrize("bad", ["volcano", "", "Mountain", 3])
def test_an_unknown_terrain_is_refused(schemas: dict[str, dict[str, object]], bad: object) -> None:
    validator = Draft202012Validator(schemas["region"])
    assert list(validator.iter_errors({**BASE, "terrain": bad})), bad
