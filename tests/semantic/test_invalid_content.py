"""Every rule that must reject content, and the reason it must give.

A validator that says "invalid" is not useful to a curriculum author. Each test asserts the
problem code *and* that the message points at the file, the field, and where feasible the
correction — which is what `docs/CONTENT-MODEL.md` asks for.

Invalid content is produced by mutating a copy of the real tree, so `content/` itself never
contains a deliberately broken document.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.content_loader import load_content
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world

QUEST = "content/quests/base-camp/repository-safety.md"
OTHER_QUEST = "content/quests/jira-jungle/read-assigned-stories.md"


def codes(report: ProblemReport) -> set[str]:
    return {p.code for p in report.problems}


def problem(report: ProblemReport, code: str) -> object:
    matches = [p for p in report.problems if p.code == code]
    assert matches, f"expected {code}, got {sorted(codes(report))}"
    return matches[0]


def edit_front_matter(repo: Path, relative: str, **changes: object) -> None:
    path = repo / relative
    text = path.read_text()
    _, front, body = text.split("---\n", 2)
    data = yaml.safe_load(front)
    for key, value in changes.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    path.write_text("---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n" + body)


def load(config: AppConfig, report: ProblemReport) -> object:
    return load_world(config, report)


class TestParsing:
    def test_missing_front_matter_names_the_file_and_line(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        (config.repo_root / QUEST).write_text("# Just a title\n\nNo front matter here.\n")
        load(config, report)
        found = problem(report, "content.missing_front_matter")
        assert found.source == QUEST  # type: ignore[attr-defined]
        assert found.line == 1  # type: ignore[attr-defined]

    def test_invalid_yaml_reports_a_line(self, config: AppConfig, report: ProblemReport) -> None:
        path = config.repo_root / "content" / "regions" / "base-camp.yaml"
        path.write_text("id: base-camp\ntitle: [unclosed\n")
        load(config, report)
        found = problem(report, "content.invalid_yaml")
        assert found.line is not None  # type: ignore[attr-defined]

    def test_empty_file_is_rejected(self, config: AppConfig, report: ProblemReport) -> None:
        (config.repo_root / "content" / "regions" / "base-camp.yaml").write_text("")
        load(config, report)
        assert "content.empty" in codes(report)


class TestSchemaViolations:
    def test_missing_required_field_names_the_rule(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(config.repo_root, QUEST, summary=None)
        load(config, report)
        found = problem(report, "schema.quest.required")
        assert "summary" in str(found.expected)  # type: ignore[attr-defined]

    def test_unknown_field_is_rejected_not_ignored(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """A typo in a field name must fail, not silently do nothing."""
        edit_front_matter(config.repo_root, QUEST, estimated_minute=30)
        load(config, report)
        assert "schema.quest.additionalProperties" in codes(report)

    def test_bad_enum_value_lists_the_allowed_values(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(config.repo_root, QUEST, level="expert")
        load(config, report)
        found = problem(report, "schema.quest.enum")
        assert "scout" in str(found.expected)  # type: ignore[attr-defined]

    def test_id_pattern_is_enforced(self, config: AppConfig, report: ProblemReport) -> None:
        edit_front_matter(config.repo_root, QUEST, id="Base_Camp Repo")
        load(config, report)
        assert "schema.quest.pattern" in codes(report)

    def test_reported_value_is_summarised_not_dumped(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(config.repo_root, QUEST, summary="x" * 400)
        load(config, report)
        found = problem(report, "schema.quest.maxLength")
        assert len(str(found.received)) < 200  # type: ignore[attr-defined]


class TestBodyRules:
    def test_missing_canonical_heading_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / QUEST
        path.write_text(path.read_text().replace("## Acceptance criteria", "## Some Other Heading"))
        load(config, report)
        assert "content.quest.missing_section" in codes(report)

    def test_acceptance_criteria_with_no_list_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / QUEST
        text = path.read_text()
        start = text.index("## Acceptance criteria")
        end = text.index("##", start + 5)
        path.write_text(
            text[:start] + "## Acceptance criteria\n\nJust a paragraph.\n\n" + text[end:]
        )
        load(config, report)
        assert "content.quest.no_acceptance_criteria" in codes(report)


class TestCrossReferences:
    def test_unknown_region_suggests_a_close_match(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(config.repo_root, QUEST, region="base-camps")
        load(config, report)
        found = problem(report, "semantic.unknown_region")
        assert "base-camp" in str(found.suggestion)  # type: ignore[attr-defined]

    def test_unknown_prerequisite_suggests_a_close_match(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(
            config.repo_root, OTHER_QUEST, prerequisites=["base-camp-repository-safty"]
        )
        load(config, report)
        found = problem(report, "semantic.unknown_prerequisite")
        assert "base-camp-repository-safety" in str(found.suggestion)  # type: ignore[attr-defined]

    def test_duplicate_stable_id_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        source = config.repo_root / "content" / "regions" / "base-camp.yaml"
        (source.parent / "base-camp-copy.yaml").write_text(source.read_text())
        load(config, report)
        found = problem(report, "content.duplicate_id")
        assert "base-camp" in str(found.suggestion)  # type: ignore[attr-defined]

    def test_two_headings_that_collide_on_one_key_are_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """`## Mission` and `## MISSION` are one key, and the second overwrote the first.

        The guard compared exact title strings while `parse_sections` keys on the casefolded
        title, so the build succeeded, said nothing, and the quest page showed the second
        block where the author's Mission should have been.
        """
        path = config.repo_root / QUEST
        path.write_text(path.read_text() + "\n\n## MISSION\n\nA second block.\n")
        load(config, report)
        found = problem(report, "content.quest.duplicate_heading")
        assert "MISSION" in str(found.received)  # type: ignore[attr-defined]

    def test_self_prerequisite_is_rejected(self, config: AppConfig, report: ProblemReport) -> None:
        edit_front_matter(config.repo_root, QUEST, prerequisites=["base-camp-repository-safety"])
        load(config, report)
        assert "semantic.self_prerequisite" in codes(report)

    def test_prerequisite_cycle_reports_the_whole_path(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """An author with a large catalog needs the loop, not the news that one exists."""
        edit_front_matter(config.repo_root, QUEST, prerequisites=["jira-read-assigned-stories"])
        edit_front_matter(
            config.repo_root, OTHER_QUEST, prerequisites=["base-camp-repository-safety"]
        )
        load(config, report)
        found = problem(report, "semantic.prerequisite_cycle")
        assert "base-camp-repository-safety" in found.public_message  # type: ignore[attr-defined]
        assert "jira-read-assigned-stories" in found.public_message  # type: ignore[attr-defined]

    def test_proof_naming_an_undeclared_validator_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(config.repo_root, QUEST, validators=[])
        load(config, report)
        assert "semantic.proof_validator_not_declared" in codes(report)


class TestBadgesAndTracks:
    def test_badge_naming_an_unknown_quest_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / "content" / "badges" / "jira-ranger.yaml"
        data = yaml.safe_load(path.read_text())
        data["criteria"]["all_quests"] = ["no-such-quest"]
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        load(config, report)
        assert "semantic.badge_unknown_quest" in codes(report)

    def test_automatic_badge_may_not_carry_a_reviewer_statement(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        """The interface must say truthfully which authority awarded a badge."""
        path = config.repo_root / "content" / "badges" / "context-scout.yaml"
        data = yaml.safe_load(path.read_text())
        data["award_type"] = "automatic"
        data["criteria"]["reviewer_statement"] = "The reviewer confirms the participant did well."
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        load(config, report)
        assert "semantic.badge_automatic_with_reviewer_statement" in codes(report)

    def test_track_promising_a_balance_it_cannot_meet_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / "content" / "tracks" / "golden-thread-foundations.yaml"
        data = yaml.safe_load(path.read_text())
        data["balance"]["validation_minimum"] = 5
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        load(config, report)
        assert "semantic.track_balance_unmet" in codes(report)

    def test_unknown_default_track_is_rejected(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / "content" / "site.yaml"
        data = yaml.safe_load(path.read_text())
        data["default_track"] = "no-such-track"
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        load(config, report)
        assert "semantic.unknown_default_track" in codes(report)


class TestVersioning:
    def test_content_from_a_newer_application_is_refused(
        self, config: AppConfig, report: ProblemReport
    ) -> None:
        path = config.repo_root / "content" / "site.yaml"
        data = yaml.safe_load(path.read_text())
        data["schema_version"] = 99
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        load_content(config, report)
        assert "content.unsupported_schema_version" in codes(report)


@pytest.mark.parametrize(
    "unsafe",
    [
        "participant/evidence/../../../etc/passwd",
        "participant/evidence/..%2f..%2fetc",
        "participant/../secrets",
        "participant/evidence/./../../outside",
    ],
)
def test_traversal_in_an_evidence_path_is_refused(config: AppConfig, unsafe: str) -> None:
    """The schema blocks the literal form; the resolver is the layer that must not be fooled.

    The percent-encoded case matters because a participant path will be round-tripped
    through a URL the moment the local service exists.
    """
    with pytest.raises(ValueError, match=r"parent-directory|percent-encoded|outside"):
        config.resolve_participant_path(unsafe)


def test_absolute_participant_path_is_refused(config: AppConfig) -> None:
    with pytest.raises(ValueError, match="must start with"):
        config.resolve_participant_path("/etc/passwd")


def test_path_outside_the_participant_root_is_refused(config: AppConfig) -> None:
    with pytest.raises(ValueError, match="must start with"):
        config.resolve_participant_path("content/site.yaml")


def test_a_legitimate_evidence_path_resolves_inside_the_root(config: AppConfig) -> None:
    resolved = config.resolve_participant_path("participant/evidence/quest-id/attempt-001")
    assert config.participant_root in resolved.parents


class TestValidatorReferences:
    """`check_quest_references` existed and nothing called it, so a quest could name a
    validator that did not exist and only the participant pressing the button found out."""

    def test_a_quest_naming_an_unregistered_validator_is_refused(
        self, content_repo: Path, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(content_repo, QUEST, validators=["no-such-validator"])
        assert load(config, report) is None
        assert problem(report, "validator.unknown")

    def test_a_validator_registered_for_another_quest_is_refused(
        self, content_repo: Path, config: AppConfig, report: ProblemReport
    ) -> None:
        edit_front_matter(content_repo, QUEST, validators=["validate-jira-read-assigned"])
        assert load(config, report) is None
        assert problem(report, "validator.not_permitted_for_quest")

    @pytest.mark.parametrize("raw", [b"validators: [unclosed\n", b"validators: caf\xe9\n"])
    def test_a_registry_that_does_not_parse_is_a_reported_problem(
        self, content_repo: Path, config: AppConfig, report: ProblemReport, raw: bytes
    ) -> None:
        (content_repo / "validators" / "registry.yaml").write_bytes(raw)
        assert load(config, report) is None
        assert any(p.source == "validators/registry.yaml" for p in report.errors), codes(report)
