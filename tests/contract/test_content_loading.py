"""Loading and normalizing the real curriculum.

These run against `content/` itself, so a change that breaks the shipped package fails here
before it reaches a participant.
"""

from __future__ import annotations

from pathlib import Path

from quest_app.config import AppConfig
from quest_app.content_loader import (
    load_content,
    orphaned_list_items,
    parse_acceptance_criteria,
    parse_sections,
)
from quest_app.errors import ProblemReport
from quest_app.markdown_render import render_markdown
from quest_app.pipeline import load_world


def test_the_shipped_package_is_publishable(
    repo_root: Path, fixture_participant_root: Path
) -> None:
    config = AppConfig.for_repo(repo_root, participant_root=fixture_participant_root)
    report = ProblemReport()
    world = load_world(config, report)

    assert world is not None, report.to_text()
    assert report.errors == []
    assert len(world.content.quests) == 3
    assert len(world.content.regions) == 8


def test_warnings_do_not_stop_a_build(repo_root: Path, fixture_participant_root: Path) -> None:
    """Empty regions and unreachable badges are exactly what ARCHITECTURE.md calls warnings.

    Curriculum is published incrementally: a build that failed on a region with no quests yet
    would block every author until the whole backlog existed.
    """
    config = AppConfig.for_repo(repo_root, participant_root=fixture_participant_root)
    report = ProblemReport()
    world = load_world(config, report)

    assert world is not None
    codes = {p.code for p in report.warnings}
    assert "semantic.empty_region" in codes
    assert "semantic.badge_unreachable" in codes
    assert report.ok


def test_every_quest_normalizes_completely(repo_root: Path) -> None:
    config = AppConfig.for_repo(repo_root)
    report = ProblemReport()
    bundle = load_content(config, report)

    assert bundle is not None
    for quest in bundle.quests.values():
        assert quest.acceptance_criteria, f"{quest.id} has no criteria"
        assert quest.required_proof, f"{quest.id} has no required proof"
        assert quest.content_hash.startswith("sha256:")
        assert quest.source.startswith("content/quests/")
        assert quest.level_label
        # Criterion IDs are positional and dense: ac-1..ac-n with no gaps (ADR-016).
        assert [c.id for c in quest.acceptance_criteria] == [
            f"ac-{n}" for n in range(1, len(quest.acceptance_criteria) + 1)
        ]


def test_quest_ordering_is_total_and_stable(repo_root: Path) -> None:
    """Two builds must agree, so the sort can never fall back on dictionary order."""
    config = AppConfig.for_repo(repo_root)
    first = load_content(config, ProblemReport())
    second = load_content(config, ProblemReport())

    assert first is not None and second is not None
    assert [q.id for q in first.ordered_quests()] == [q.id for q in second.ordered_quests()]
    assert [r.id for r in first.ordered_regions()] == [r.id for r in second.ordered_regions()]
    assert first.content_hash == second.content_hash


def test_content_hash_changes_when_content_changes(content_repo: Path) -> None:
    config = AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")
    before = load_content(config, ProblemReport())
    quest_file = content_repo / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest_file.write_text(
        quest_file.read_text().replace("## Mission", "## Mission\n\nExtra sentence.")
    )
    after = load_content(config, ProblemReport())

    assert before is not None and after is not None
    assert before.content_hash != after.content_hash


class TestBodyParsing:
    """Structure is read from the Markdown token stream, not from line regexes.

    Every case below is one the Stage 2 audit broke in the regex version (H2, H3, M3, M4).
    """

    def test_sections_split_on_level_two_headings(self) -> None:
        body = "# Title\n\nIgnored.\n\n## Mission\n\nDo the thing.\n\n## Hints\n\nA hint.\n"
        sections = parse_sections(body)
        assert set(sections) == {"mission", "hints"}
        assert sections["mission"][1] == "Do the thing."

    def test_unrecognised_heading_is_kept_under_a_prefixed_slug(self) -> None:
        """An author's heading must never vanish, and must never impersonate a canonical one."""
        sections = parse_sections("## Mission\n\nx\n\n## Field Notes\n\ny\n")
        assert "custom-field-notes" in sections
        assert sections["custom-field-notes"][0] == "Field Notes"

    def test_a_near_miss_heading_cannot_satisfy_the_canonical_one(self) -> None:
        """`## Mission!` slugged to `mission` and passed the required-heading check."""
        sections = parse_sections("## Mission!\n\nx\n")
        assert "mission" not in sections
        assert "custom-mission" in sections

    def test_a_heading_inside_a_code_fence_is_not_a_heading(self) -> None:
        body = "## Mission\n\n```\n## Acceptance criteria\n\n1. fake\n```\n\n## Hints\n\nh\n"
        sections = parse_sections(body)
        assert set(sections) == {"mission", "hints"}
        assert "## Acceptance criteria" in sections["mission"][1]

    def test_criteria_ids_are_positional(self) -> None:
        criteria, ordered, empty = parse_acceptance_criteria("1. First thing\n2. Second thing\n")
        assert ordered is True
        assert empty is False
        assert [(c.id, c.number, c.text) for c in criteria] == [
            ("ac-1", 1, "First thing"),
            ("ac-2", 2, "Second thing"),
        ]

    def test_a_nested_sub_detail_is_not_a_criterion(self) -> None:
        """This is the defect ADR-016 exists to prevent: `ac-2` must not become a sub-point."""
        criteria, _, _ = parse_acceptance_criteria("1. one\n   1. sub a\n   2. sub b\n2. two\n")
        assert [c.text for c in criteria] == ["one", "two"]

    def test_a_multi_line_criterion_keeps_its_continuation(self) -> None:
        """The continuation was dropped from the model, the page and the hash."""
        criteria, _, _ = parse_acceptance_criteria("1. one that continues\n   onto a second line\n")
        assert criteria[0].text == "one that continues onto a second line"

    def test_editing_a_continuation_line_changes_the_hash(self) -> None:
        first, _, _ = parse_acceptance_criteria("1. one\n   and a tail\n")
        second, _, _ = parse_acceptance_criteria("1. one\n   and a different tail\n")
        assert first[0].id == second[0].id
        assert first[0].text_hash != second[0].text_hash

    def test_numbers_inside_a_code_fence_are_not_criteria(self) -> None:
        criteria, _, _ = parse_acceptance_criteria(
            "1. one\n\n   ```\n   1. not a criterion\n   ```\n2. two\n"
        )
        assert [c.text for c in criteria] == ["one", "two"]

    def test_an_indented_code_block_is_not_a_list(self) -> None:
        criteria, _, _ = parse_acceptance_criteria("    1. indented\n")
        assert criteria == []

    def test_an_empty_item_is_reported_rather_than_renumbering(self) -> None:
        """An empty item shifted every later identifier by one, silently."""
        criteria, _, empty = parse_acceptance_criteria("1.\n2. two\n")
        assert empty is True
        assert [c.text for c in criteria] == ["two"]

    def test_a_bullet_list_is_recognised_as_unnumbered(self) -> None:
        _, ordered, _ = parse_acceptance_criteria("- alpha\n- beta\n")
        assert ordered is False

    def test_items_outside_the_first_list_are_counted(self) -> None:
        """A paragraph between items starts a second list the author did not intend."""
        assert orphaned_list_items("1. one\n\nA paragraph.\n\n2. two\n3. three\n") >= 1
        assert orphaned_list_items("1. one\n2. two\n") == 0

    def test_criterion_text_hash_changes_with_wording(self) -> None:
        """A stable ID over changed text is what makes a stale reviewer finding detectable."""
        first, _, _ = parse_acceptance_criteria("1. The build succeeds\n")
        second, _, _ = parse_acceptance_criteria("1. The build succeeds quickly\n")
        assert first[0].id == second[0].id
        assert first[0].text_hash != second[0].text_hash


class TestMarkdownSafety:
    def test_script_tags_are_escaped(self) -> None:
        assert "<script>" not in render_markdown("<script>alert(1)</script>")

    def test_raw_html_becomes_inert_text(self) -> None:
        """Raw HTML is escaped, not stripped.

        The word `onerror` still appears — as literal text inside an escaped `&lt;img`, where
        it is content an author typed rather than an attribute a browser will act on. The
        assertion is therefore about the tag, not the substring.
        """
        rendered = render_markdown('<img src=x onerror="alert(1)">')
        assert "<img" not in rendered
        assert "&lt;img" in rendered

    def test_script_urls_never_become_links(self) -> None:
        """markdown-it rejects this destination outright, so no link is produced at all."""
        rendered = render_markdown("[x](javascript:alert(1))")
        assert "<a" not in rendered
        assert "javascript:" in rendered, "it survives as inert text, which is the point"

    def test_data_urls_never_become_links(self) -> None:
        rendered = render_markdown("[x](data:text/html;base64,PHNjcmlwdD4=)")
        assert "<a" not in rendered

    def test_a_scheme_the_parser_accepts_is_still_stripped_by_the_allowlist(self) -> None:
        """The previous two tests never exercise nh3, because markdown-it refuses first.

        `ftp:` is a destination markdown-it does accept, so this is the test that actually
        proves the URL-scheme allowlist is doing something.
        """
        rendered = render_markdown("[x](ftp://example.com/a)")
        assert "<a" in rendered
        assert "ftp://" not in rendered
        assert "href" not in rendered

    def test_external_links_carry_noopener(self) -> None:
        rendered = render_markdown("[docs](https://example.com)")
        assert 'rel="noopener noreferrer"' in rendered
        assert 'target="_blank"' in rendered

    def test_images_are_not_allowed(self) -> None:
        """A remote image is a network request the security policy does not permit by default."""
        assert "<img" not in render_markdown("![alt](https://example.com/x.png)")
