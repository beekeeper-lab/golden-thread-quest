"""The numbers the project claims about itself must be the numbers it produces.

An external audit found the README, the release notes and the user guide all quoting a
test count that was five short, because each was hand-maintained. For a product whose
whole argument is that claims must be backed by evidence, a stale claim about its own
evidence is the wrong kind of defect. This makes the documents fail when they drift.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Every place a suite size is asserted in prose, and the pytest marker expression the
# number is supposed to describe. The user guide is deliberately absent: it now says what
# `make check` does without quoting a total, which is one fewer number to drift.
CLAIMS = [
    (Path("README.md"), r"(\d+) under `make check`", "not ui"),
    (Path("README.md"), r"(\d+) driving a real browser", "ui"),
    (Path("docs/RELEASE-NOTES.md"), r"(\d+) under `make check`", "not ui"),
    (Path("docs/RELEASE-NOTES.md"), r"plus (\d+) browser-driven", "ui"),
]


def collected(marker: str) -> int:
    """How many tests pytest actually collects for a marker expression."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-p", "no:cacheprovider", "-m", marker],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest prints either "N tests collected" or "N/M tests collected (K deselected)".
    match = re.search(r"(\d+)(?:/\d+)?\s+tests? collected", result.stdout)
    if match is None:
        # Collection can fail outright rather than report zero, which is what happens in a
        # virtualenv without the browser extra installed. Treat that as "none here" and let
        # the caller decide; asserting would turn a missing optional dependency into a
        # documentation failure.
        return 0
    return int(match.group(1))


@pytest.mark.slow
@pytest.mark.parametrize(("document", "pattern", "marker"), CLAIMS)
def test_documented_test_counts_are_true(document: Path, pattern: str, marker: str) -> None:
    text = (ROOT / document).read_text()
    found = re.search(pattern, text)
    assert found, f"{document} no longer states a count matching {pattern!r}"
    claimed = int(found.group(1))
    actual = collected(marker)
    if actual == 0 and marker == "ui":
        pytest.skip("browser tests are not installed here; make setup-ui installs them")
    assert claimed == actual, (
        f"{document} claims {claimed} tests for -m {marker!r}, but pytest collects "
        f"{actual}. This usually means content was added or removed (a new quest's "
        "parametrized tests count too) rather than a test file changing. Update the "
        f"'Tests' row in {document} to the number `make check` just printed, or explain "
        "the difference. docs/CONTENT-AUTHORING-GUIDE.md's 'Add a quest' checklist names "
        "every document this test and test_the_readme_states_the_curriculum_it_actually_has "
        "check."
    )


# --- Which diagram each page ships -------------------------------------------------

GUIDE = Path("docs/USER-GUIDE.md")
IMAGE_PLAN = Path("IMAGE-PLAN.md")
_GUIDE_IMAGE = re.compile(r"!\[[^\]]*\]\(media/(images/[^)]+)\)")
_PLAN_ROW = re.compile(r"^\|[^|]+\|\s*\**`(images?/[^`]+|[^`|]+\.png)`\**\s*\|", re.MULTILINE)


def _guide_images() -> list[str]:
    return _GUIDE_IMAGE.findall((ROOT / GUIDE).read_text())


def _planned_images() -> list[str]:
    """The files the 'Which take each page ships' table says the guide renders."""
    text = (ROOT / IMAGE_PLAN).read_text()
    table = text.split("## Which take each page ships", 1)
    assert len(table) == 2, f"{IMAGE_PLAN} no longer records which take each page ships"
    rows = re.findall(r"^\|[^|]+\|\s*`([^`]+\.png)`\s*\|", table[1], re.MULTILINE)
    return [f"images/{name}" for name in rows]


def test_every_diagram_the_guide_references_exists() -> None:
    """A broken image in the onboarding document is invisible to every other check."""
    missing = [ref for ref in _guide_images() if not (ROOT / "docs" / "media" / ref).exists()]
    assert not missing, f"{GUIDE} references files that are not on disk: {missing}"


def test_the_guide_ships_the_take_the_plan_says_it_ships() -> None:
    """Generating a correction and wiring it in are two acts, and round 2 did only the first.

    Three superseded diagrams stayed in the guide for a release because nothing compared
    the two lists. One of them put `locally validated` in the reviewer column, which is the
    opposite of the rule the image exists to state.
    """
    assert _guide_images() == _planned_images(), (
        f"{GUIDE} and the 'Which take each page ships' table in {IMAGE_PLAN} disagree. "
        "Update whichever is wrong; a correction that is generated but not referenced is "
        "not shipped."
    )


# --- What the curriculum contains --------------------------------------------------


def test_the_readme_states_the_curriculum_it_actually_has() -> None:
    """The README said "3 quests" for a release after five more were authored.

    Test counts were already enforced here; nothing enforced the counts that describe the
    content, which is the first thing a reader of the front page looks at.
    """
    counted = {
        "regions": len(list((ROOT / "content" / "regions").glob("*.yaml"))),
        "quests": len(list((ROOT / "content" / "quests").glob("*/*.md"))),
        "badges": len(list((ROOT / "content" / "badges").glob("*.yaml"))),
        "tracks": len(list((ROOT / "content" / "tracks").glob("*.yaml"))),
    }
    row = re.search(r"\| Sample curriculum \| ([^|]+) \|", (ROOT / "README.md").read_text())
    assert row, "README.md no longer states what the sample curriculum contains"
    claimed = {
        noun: int(number)
        for number, noun in re.findall(r"(\d+) (regions?|quests?|badges?|tracks?)", row.group(1))
    }
    normalised = {noun.rstrip("s") + "s": n for noun, n in claimed.items()}
    assert normalised == counted, (
        f"README.md claims {normalised}, the content tree holds {counted}. Update the "
        "'Sample curriculum' row in README.md's release-facts table to match — adding a "
        "valid quest, region, badge, or track changes this count, per "
        "docs/CONTENT-AUTHORING-GUIDE.md's 'Add a quest' checklist."
    )


def test_the_readme_says_the_project_is_a_pilot_not_a_general_release() -> None:
    """It is public and unfinished, and a reader must not have to infer the second part.

    Released to a small pilot at Gate 1 (0.2.0), which is not a release for general use.
    """
    head = (ROOT / "README.md").read_text().split("## ", 1)[0].lower()
    assert "work in progress" in head
    assert "pilot" in head
    assert "not for general use" in head


EXPECTED_WRITE_QUESTS = {
    "jira-create-story",
    "jira-create-subtask",
    "jira-add-comment",
    "jira-update-fields",
    "jira-transition-status",
    "jira-link-work",
    "jira-idempotent-create",
    "github-create-issue",
    "github-add-comment",
    "github-update-metadata",
    "github-close-reopen",
    "github-link-delivery",
    "github-idempotent-write",
    "trello-create-card",
    "trello-add-checklist-item",
    "trello-add-comment",
    "trello-move-card",
    "trello-update-card",
    "trello-idempotent-write",
}


def _quest_fronts() -> dict[str, dict]:
    import yaml

    fronts: dict[str, dict] = {}
    for quest in sorted((ROOT / "content" / "quests").rglob("*.md")):
        front = yaml.safe_load(quest.read_text().split("---", 2)[1]) or {}
        fronts[front["id"]] = front
    return fronts


def _prerequisite_closure(fronts: dict[str, dict], quest_id: str) -> set[str]:
    seen: set[str] = set()
    pending = list(fronts[quest_id].get("prerequisites") or [])
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(fronts[current].get("prerequisites") or [])
    return seen


def test_a_quest_that_writes_to_an_external_system_carries_the_stated_controls() -> None:
    """`docs/SECURITY-AND-PRIVACY.md` lists five conditions for a quest that writes.

    This test used to assert that no quest declares a write, and said that the day one did,
    the controls would have to be built. The Jira write quests are that day. The controls are
    properties of the quest's content, so what can be held is that every quest declaring an
    external write requires evidence of each one: a preview of the target and exact changes,
    duplicate and permission checks, an explicit confirmation tied to the preview, a result
    record with the external identifier and time, and rerun safety. It also has to follow
    the preview quest, keep to a sandbox, and say so in its risk note.

    A quest that declares a write and drops any of these fails here, so the invariant is
    stricter than before: it no longer assumes writes are absent, it refuses a write quest
    that is under-specified.
    """
    fronts = _quest_fronts()
    writers = {q for q, f in fronts.items() if (f.get("risk") or {}).get("external_write") is True}
    # The set of write quests is named here so that adding one is a deliberate edit to this
    # file, and so that a write quest cannot be flipped to `false` and quietly leave the
    # check: a quest tagged `write` must declare it, and every declared write must be named.
    assert writers == EXPECTED_WRITE_QUESTS, (
        f"external-write quests changed: declared {sorted(writers)}, "
        f"expected {sorted(EXPECTED_WRITE_QUESTS)}"
    )
    tagged = {q for q, f in fronts.items() if "write" in (f.get("tags") or [])}
    assert tagged == writers, (
        f"quests tagged write differ from declared writes: {sorted(tagged ^ writers)}"
    )
    for quest_id in writers:
        front = fronts[quest_id]
        text = " ".join(
            str(item.get("description", "")) for item in front["proof"].get("required", [])
        ).lower()
        body = (
            next(
                p
                for p in (ROOT / "content" / "quests").rglob("*.md")
                if f"id: {quest_id}\n" in p.read_text()
            )
            .read_text()
            .lower()
        )
        for needle, control in (
            ("preview", "a preview of the target and exact changes"),
            ("confirmation", "an explicit confirmation"),
            ("permission check", "a permission check"),
            ("duplicate", "a duplicate check or its stated limit"),
            ("timestamp", "a result record with a time"),
            ("second time", "rerun behavior"),
            ("allowlist", "a sandbox allowlist"),
        ):
            assert needle in text, f"{quest_id}: required proof does not show {control}"
        assert "sandbox" in str((front.get("risk") or {}).get("notes", "")).lower(), (
            f"{quest_id}: its risk note does not say the target is a sandbox"
        )
        assert "base-camp-write-preview" in _prerequisite_closure(fronts, quest_id), (
            f"{quest_id}: it does not follow the preview quest"
        )
        assert "sandbox" in body and "production" in body, (
            f"{quest_id}: its safety constraints do not rule out production"
        )

    import yaml

    registry = yaml.safe_load((ROOT / "validators" / "registry.yaml").read_text())
    for entry in registry["validators"]:
        assert entry["network"] == "denied", f"{entry['id']} is registered with network access"


def test_known_limitations_are_numbered_from_one_with_no_gaps() -> None:
    """Round 13, T4: the list was numbered from 0, so README's prose count of it (once
    "ten") was off by one against the eleven items actually there. Numbering from 1 keeps
    the ordinal a reader sees matching the one used to talk about an item, with no fixed
    count anywhere in README that has to be kept in step as items are added or removed.
    """
    text = (ROOT / "docs" / "RELEASE-NOTES.md").read_text()
    section = text.split("## Known limitations", 1)[1].split("\n## ", 1)[0]
    numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\.\s", section)]
    assert numbers, "docs/RELEASE-NOTES.md's Known limitations section has no numbered items"
    assert numbers == list(range(1, len(numbers) + 1)), (
        f"docs/RELEASE-NOTES.md's Known limitations are numbered {numbers}, not 1..{len(numbers)}"
    )
