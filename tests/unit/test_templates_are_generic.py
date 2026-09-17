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

# Region IDs are structural: they name accent slots and nothing else. Everything else that
# identifies a specific piece of curriculum is forbidden.
ALLOWED_SUBSTRINGS = {"base-camp", "jira-jungle", "playwright-labyrinth"}


def content_identifiers(repo_root: Path) -> set[str]:
    """Every name a maintainer could write in `content/` that must not appear in UI code.

    The first version of this collected quest IDs, quest titles and badge titles only. The
    Stage 3 audit found a region title hard-coded in a template and pointed out that this
    test could not see it: region titles, track titles and site fields were never read, so
    planting `Golden Thread Foundations` in a template passed the suite. Anything an author
    can type is now in scope.
    """
    identifiers: set[str] = set()

    for path in (repo_root / "content" / "quests").rglob("*.md"):
        front = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.S)
        if front:
            data = yaml.safe_load(front.group(1))
            identifiers.update({data["id"], data["title"], data["summary"]})
            # `tools` is deliberately excluded: those are generic technology names like
            # "Git" and "Markdown", which appear legitimately in prose and in module names.
            # Treating them as curriculum identifiers would make this guard unusable, and a
            # guard people disable protects nothing.

    for directory, fields in (
        ("regions", ("title", "short_title", "summary")),
        ("badges", ("title", "summary")),
        ("tracks", ("title", "summary")),
    ):
        for path in (repo_root / "content" / directory).glob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            identifiers.update(str(data[field]) for field in fields if data.get(field))

    site = yaml.safe_load((repo_root / "content" / "site.yaml").read_text())
    # `title`, `curriculum` and `tagline` are the program's own identity and appear in the
    # shell by design, so they come from the view model rather than being literals. The
    # default track is a stable ID a template must never name.
    identifiers.add(str(site["default_track"]))

    return {
        value for value in identifiers if value not in ALLOWED_SUBSTRINGS and _is_distinctive(value)
    }


def _is_distinctive(value: str) -> bool:
    """Whether a name identifies curriculum rather than a technology.

    A single bare word such as `GitHub` is a product name that appears legitimately in
    security-pattern descriptions and module docstrings; treating it as a curriculum
    identifier would produce false positives that make maintainers disable the check, and a
    check people disable protects nothing. A stable ID (hyphenated) or a multi-word title is
    curriculum-specific and stays in scope.
    """
    return " " in value or "-" in value


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


def test_the_guard_would_catch_a_planted_violation(repo_root: Path, tmp_path: Path) -> None:
    """The test that guards the rule has to be able to see a violation of it.

    A guard nobody has watched fail is a guard nobody knows works. This plants each kind of
    identifier into a file and asserts the collector finds it — region and track titles
    included, because those are the two the first version was blind to.
    """
    identifiers = content_identifiers(repo_root)
    for expected in ("Base Camp", "Golden Thread Foundations", "golden-thread-foundations"):
        assert expected in identifiers, f"{expected!r} is invisible to this guard"

    planted = tmp_path / "planted.html.j2"
    planted.write_text("<h1>Base Camp</h1>")
    offenders = [name for name in identifiers if name in planted.read_text()]
    assert offenders, "a planted region title must be detectable"
