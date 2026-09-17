"""Templates and rendering code must contain no quest-specific content.

This is the mechanical half of "a maintainer can add a quest without editing UI code". The
other half — that a new quest actually appears everywhere — is asserted in
`tests/integration/test_build.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

SEARCH_ROOTS = ("templates", "assets", "quest_app")

# Region ids are structural: they name accent slots and nothing else. Everything else that
# identifies a specific piece of curriculum is forbidden.
ALLOWED_SUBSTRINGS = {"base-camp", "jira-jungle", "playwright-labyrinth"}


def content_identifiers(repo_root: Path) -> set[str]:
    identifiers: set[str] = set()
    for path in (repo_root / "content" / "quests").rglob("*.md"):
        front = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
        if front:
            data = yaml.safe_load(front.group(1))
            identifiers.add(data["id"])
            identifiers.add(data["title"])
    for path in (repo_root / "content" / "badges").glob("*.yaml"):
        identifiers.add(yaml.safe_load(path.read_text())["title"])
    return {value for value in identifiers if value not in ALLOWED_SUBSTRINGS}


@pytest.mark.parametrize("directory", SEARCH_ROOTS)
def test_no_quest_specific_string_appears_in_ui_code(repo_root: Path, directory: str) -> None:
    identifiers = content_identifiers(repo_root)
    offenders: list[str] = []
    for path in sorted((repo_root / directory).rglob("*")):
        if not path.is_file() or path.suffix not in {".j2", ".css", ".js", ".py"}:
            continue
        text = path.read_text()
        for identifier in identifiers:
            if identifier in text:
                offenders.append(f"{path.relative_to(repo_root)} contains {identifier!r}")
    assert offenders == [], "\n".join(offenders)


def test_every_region_accent_has_a_style(repo_root: Path) -> None:
    """A region naming an accent with no rule would render with no accent and no error."""
    css = (repo_root / "assets" / "css" / "app.css").read_text()
    schema = (repo_root / "schemas" / "region.schema.json").read_text()
    accents = re.search(r'"accent":\s*\{[^}]*"enum":\s*\[([^\]]+)\]', schema, re.S)
    assert accents
    for accent in re.findall(r'"([a-z]+)"', accents.group(1)):
        assert f".accent-{accent}" in css, f"no style for accent {accent!r}"


def test_every_quest_state_has_a_style(repo_root: Path) -> None:
    css = (repo_root / "assets" / "css" / "app.css").read_text()
    from quest_app.models import QuestState

    for state in QuestState:
        assert f".state-{state.value}" in css, f"no style for state {state.value!r}"
