"""`quest validate` from the outside: exit codes, streams and machine-readable output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from quest_app.cli import main


def test_validating_the_shipped_package_succeeds(
    repo_root: Path, fixture_participant_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        [
            "validate",
            "--repo-root",
            str(repo_root),
            "--participant-root",
            str(fixture_participant_root),
        ]
    )
    authored_quests = len(list((repo_root / "content" / "quests").rglob("*.md")))

    assert exit_code == 0
    assert f"validated {authored_quests} quest(s)" in capsys.readouterr().err


def test_no_participant_file_is_not_an_error(
    content_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The curriculum is browsable before anyone starts a quest."""
    import shutil

    shutil.rmtree(content_repo / "participant")
    assert main(["validate", "--repo-root", str(content_repo)]) == 0
    capsys.readouterr()


def test_broken_content_exits_non_zero_and_writes_errors_to_stderr(
    content_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    quest = content_repo / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text("# No front matter\n")

    exit_code = main(["validate", "--repo-root", str(content_repo)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "content.missing_front_matter" not in captured.out, "errors belong on stderr"
    assert "front matter" in captured.err


def test_warnings_go_to_stdout_so_a_pipeline_can_separate_them(
    content_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A warning must never reach stderr, where a pipeline would read it as a failure.

    The warning is manufactured in a copy rather than relied on in `content/`, so closing a
    gap in the shipped curriculum cannot quietly delete this coverage.
    """
    (content_repo / "content" / "regions" / "unwritten-frontier.yaml").write_text(
        "id: unwritten-frontier\n"
        "version: 1\n"
        "title: Unwritten Frontier\n"
        "summary: A region whose quests have not been authored yet.\n"
        "order: 900\n"
        "accent: slate\n"
        "outcomes:\n"
        "  - Nothing yet, because no quest names this region.\n"
    )

    exit_code = main(["validate", "--repo-root", str(content_repo)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "contains no quests" in captured.out
    assert "contains no quests" not in captured.err


def test_json_output_is_machine_readable_and_sorted(
    repo_root: Path, fixture_participant_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(
        [
            "validate",
            "--repo-root",
            str(repo_root),
            "--participant-root",
            str(fixture_participant_root),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["ok"] is True
    assert payload["error_count"] == 0
    assert payload["warning_count"] > 0
    assert all("code" in problem for problem in payload["problems"])


def test_json_output_is_stable_between_runs(
    repo_root: Path, fixture_participant_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Output that gets diffed must not reorder itself."""
    args = [
        "validate",
        "--repo-root",
        str(repo_root),
        "--participant-root",
        str(fixture_participant_root),
        "--json",
    ]
    main(args)
    first = capsys.readouterr().out
    main(args)
    assert capsys.readouterr().out == first


def test_no_absolute_developer_path_reaches_the_output(
    content_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Problem sources are repository-relative; an absolute path would leak a home directory."""
    quest = content_repo / "content" / "quests" / "base-camp" / "repository-safety.md"
    quest.write_text("# No front matter\n")
    main(["validate", "--repo-root", str(content_repo), "--json"])
    payload = json.loads(capsys.readouterr().out)

    for problem in payload["problems"]:
        assert not problem.get("source", "").startswith("/")
        assert str(content_repo) not in json.dumps(problem)
