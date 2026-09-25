"""The application's own roots: `generated/`, its siblings, and `local-data/` (round 13).

E1: `AppConfig` resolved the generated root through links and a build renamed and deleted
it, so a committed `generated -> ..` link, or `GTQ_GENERATED_ROOT` pointed at an existing
folder, deleted that folder. E2: the build error page, the service port file and the build
lock followed links under `local-data/` and beside `generated/`. E4: `serve --port` dropped
the generated and local-data roots. E5: participant state records were read through links
leading out of the tree. Every test here puts a sentinel outside the clone and checks that
it survives untouched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from quest_app.build import UnsafeOutputRootError, _exclusive_output, build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.safe_io import UnsafeWriteTargetError
from quest_app.store import ProgressStore, StoreError

ROOT = Path(__file__).resolve().parent.parent.parent
SENTINEL_TEXT = "the participant's own file, which no build may touch\n"
VERIFIED = "evidence/base-camp-repository-safety/base-camp-attempt-001"
READY = "evidence/jira-read-assigned-stories/jira-attempt-001"


def _clone(destination: Path) -> Path:
    """The same private copy `content_repo` makes, at a place of the test's choosing."""
    for name in ("content", "schemas", "templates", "assets", "validators", "quest_app"):
        shutil.copytree(
            ROOT / name, destination / name, ignore=shutil.ignore_patterns("__pycache__")
        )
    shutil.copy2(ROOT / ".gitignore", destination / ".gitignore")
    shutil.copytree(ROOT / "fixtures" / "participant", destination / "participant")
    return destination


def _sentinel(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    sentinel = directory / "sentinel.txt"
    sentinel.write_text(SENTINEL_TEXT)
    return sentinel


def _world(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    return world


# ---------------------------------------------------------------------------------- E1


def test_a_committed_generated_link_to_the_parent_is_refused_and_deletes_nothing(
    tmp_path: Path,
) -> None:
    """`generated -> ..` resolved to the directory holding the clone, which the build renamed
    to `.previous` and deleted, clone and all."""
    outer = tmp_path / "outer"
    clone = _clone(outer / "clone")
    sentinel = _sentinel(outer)
    (clone / "generated").symlink_to("..")
    config = AppConfig.for_repo(clone, participant_root=clone / "participant")

    with pytest.raises(UnsafeOutputRootError, match="symbolic link"):
        build_site(_world(config))

    assert sentinel.read_text() == SENTINEL_TEXT
    assert (clone / "content").is_dir()
    assert (clone / "generated").is_symlink()
    assert not (outer.parent / "outer.previous").exists()


def test_a_committed_generated_link_to_a_folder_outside_is_refused(tmp_path: Path) -> None:
    clone = _clone(tmp_path / "clone")
    outside = tmp_path / "outside"
    sentinel = _sentinel(outside)
    (clone / "generated").symlink_to(outside)
    config = AppConfig.for_repo(clone, participant_root=clone / "participant")

    with pytest.raises(UnsafeOutputRootError, match="symbolic link"):
        build_site(_world(config))

    assert sentinel.read_text() == SENTINEL_TEXT
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.txt"]


@pytest.mark.parametrize("sibling", [".building", ".previous"])
def test_a_link_at_a_sibling_of_the_generated_root_is_refused(
    content_repo: Path, tmp_path: Path, sibling: str
) -> None:
    outside = tmp_path / "outside"
    sentinel = _sentinel(outside)
    (content_repo / f"generated{sibling}").symlink_to(outside)
    config = AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")

    with pytest.raises(UnsafeOutputRootError, match="symbolic link"):
        build_site(_world(config))
    assert sentinel.read_text() == SENTINEL_TEXT


def test_generated_root_from_the_environment_pointing_at_an_existing_folder_is_refused(
    tmp_path: Path,
) -> None:
    """`GTQ_GENERATED_ROOT` at a folder the participant already had: the CLI build deleted it.

    Run as the CLI, as a participant would. Local data is pointed away from the repository
    as well, so nothing here can write to the repository's own roots.
    """
    existing = tmp_path / "my-notes"
    sentinel = _sentinel(existing)
    environment = {
        **os.environ,
        "GTQ_GENERATED_ROOT": str(existing),
        "GTQ_LOCAL_DATA_ROOT": str(tmp_path / "local-data"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "build",
            "--participant-root",
            str(ROOT / "fixtures" / "participant"),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode != 0, result.stderr
    assert "was not written by this application" in result.stderr, result.stderr
    assert "Traceback" not in result.stderr
    assert sentinel.read_text() == SENTINEL_TEXT
    assert sorted(path.name for path in existing.iterdir()) == ["sentinel.txt"]
    assert not (tmp_path / "my-notes.previous").exists()


def test_a_generated_root_from_the_environment_that_is_new_or_ours_builds(
    content_repo: Path, tmp_path: Path
) -> None:
    """The refusal is narrow: a new directory, an empty one, and our own output all build."""
    for name in ("new", "empty"):
        target = tmp_path / "out" / name
        if name == "empty":
            target.mkdir(parents=True)
        config = AppConfig.for_repo(
            content_repo, participant_root=content_repo / "participant", generated_root=target
        )
        build_site(_world(config))
        build_site(_world(config))  # the second build replaces our own first one
        assert (target / "index.html").is_file()
        assert (target / ".golden-thread-output").is_file()


@pytest.mark.parametrize(
    "where",
    ["repository", "repository_parent", "content", "participant", "inside_participant"],
)
def test_a_generated_root_overlapping_a_source_folder_is_refused(
    content_repo: Path, where: str
) -> None:
    targets = {
        "repository": content_repo,
        "repository_parent": content_repo.parent,
        "content": content_repo / "content",
        "participant": content_repo / "participant",
        "inside_participant": content_repo / "participant" / "site",
    }
    config = AppConfig.for_repo(
        content_repo,
        participant_root=content_repo / "participant",
        generated_root=targets[where],
    )
    before = sorted(str(path) for path in content_repo.rglob("*"))

    with pytest.raises(UnsafeOutputRootError, match="Refusing to build"):
        build_site(_world(config))
    assert sorted(str(path) for path in content_repo.rglob("*")) == before


def test_a_staging_directory_this_application_did_not_write_is_not_deleted(
    content_repo: Path,
) -> None:
    staging = content_repo / "generated.building"
    sentinel = _sentinel(staging)
    config = AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")

    with pytest.raises(UnsafeOutputRootError, match="not written by this application"):
        build_site(_world(config))
    assert sentinel.read_text() == SENTINEL_TEXT


def test_the_cli_build_refuses_a_linked_generated_root_without_a_traceback(
    content_repo: Path, tmp_path: Path
) -> None:
    from quest_app.cli import main

    outside = tmp_path / "outside"
    sentinel = _sentinel(outside)
    (content_repo / "generated").symlink_to(outside)
    code = main(
        [
            "build",
            "--repo-root",
            str(content_repo),
            "--participant-root",
            str(content_repo / "participant"),
        ]
    )
    assert code != 0
    assert sentinel.read_text() == SENTINEL_TEXT


# ---------------------------------------------------------------------------------- E2


@pytest.mark.parametrize("level", ["local-data", "build-errors", "index.html"])
def test_the_build_error_page_is_never_written_through_a_link(
    config: AppConfig, tmp_path: Path, level: str
) -> None:
    from quest_app.build import render_error_page

    outside = tmp_path / "outside"
    sentinel = _sentinel(outside)
    local_data = config.local_data_root
    if level == "local-data":
        local_data.symlink_to(outside)
    elif level == "build-errors":
        local_data.mkdir()
        (local_data / "build-errors").symlink_to(outside)
    else:
        (local_data / "build-errors").mkdir(parents=True)
        (local_data / "build-errors" / "index.html").symlink_to(sentinel)

    with pytest.raises(UnsafeWriteTargetError, match="link"):
        render_error_page(config, ProblemReport())

    assert sentinel.read_text() == SENTINEL_TEXT
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.txt"]


def test_the_error_page_still_writes_to_an_ordinary_local_data(config: AppConfig) -> None:
    from quest_app.build import render_error_page

    page = render_error_page(config, ProblemReport())
    assert page == config.local_data_root / "build-errors" / "index.html"
    assert "This content was not published" in page.read_text()


@pytest.mark.parametrize("level", ["local-data", "service-ports", "entry"])
def test_the_service_port_file_is_never_written_through_a_link(
    config: AppConfig, tmp_path: Path, level: str
) -> None:
    from quest_app.serve import claim_port_file

    outside = tmp_path / "outside"
    sentinel = _sentinel(outside)
    local_data = config.local_data_root
    if level == "local-data":
        local_data.symlink_to(outside)
    elif level == "service-ports":
        local_data.mkdir()
        (local_data / "service-ports").symlink_to(outside)
    else:
        (local_data / "service-ports").mkdir(parents=True)
        (local_data / "service-ports" / "8799").symlink_to(sentinel)

    assert claim_port_file(config, 8799) is None
    assert sentinel.read_text() == SENTINEL_TEXT
    assert sorted(path.name for path in outside.iterdir()) == ["sentinel.txt"]


def test_the_service_port_file_is_written_to_an_ordinary_local_data(config: AppConfig) -> None:
    from quest_app.serve import claim_port_file

    claimed = claim_port_file(config, 8799)
    assert claimed is not None
    assert claimed.read_text() == "8799\n"


def test_stale_port_pruning_never_deletes_through_a_linked_ports_directory(
    config: AppConfig, tmp_path: Path
) -> None:
    """The probe deletes an entry whose port refuses a connection. Through a link, that was
    a file outside the clone whose contents happened to be a number."""
    import socket

    from quest_app.serve import is_service_running

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = probe.getsockname()[1]
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "notes"
    victim.write_text(f"{free_port}\n")
    config.local_data_root.mkdir()
    (config.local_data_root / "service-ports").symlink_to(outside)

    is_service_running(config)
    assert victim.read_text() == f"{free_port}\n"


def test_the_build_lock_is_never_created_through_a_link(config: AppConfig, tmp_path: Path) -> None:
    """`generated.lock` opened with `a+` created or appended to whatever a link named."""
    planted = tmp_path / "outside" / "planted"
    planted.parent.mkdir()
    lock = config.generated_root.with_name("generated.lock")
    lock.symlink_to(planted)

    with _exclusive_output(config):
        pass
    assert not planted.exists()

    with pytest.raises(UnsafeOutputRootError, match="build lock"):
        build_site(_world(config))
    assert not planted.exists()


# ---------------------------------------------------------------------------------- E4


def test_the_service_and_a_cli_action_agree_on_every_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`serve --port` rebuilt its configuration from the participant root alone."""
    import quest_app.serve as serve_module
    from quest_app.cli import _config_from_args, build_parser

    monkeypatch.setenv("GTQ_GENERATED_ROOT", str(tmp_path / "generated"))
    monkeypatch.setenv("GTQ_LOCAL_DATA_ROOT", str(tmp_path / "local-data"))
    participant = str(ROOT / "fixtures" / "participant")
    cli_config = _config_from_args(
        build_parser().parse_args(["action", "rebuild", "--participant-root", participant])
    )

    seen: list[AppConfig] = []

    def capture(config: AppConfig, report: ProblemReport) -> None:
        seen.append(config)
        return None  # "content does not validate": the service stops before binding

    monkeypatch.setattr(serve_module, "load_world", capture)
    serve_module.run_service(cli_config, port=0)

    (service_config,) = seen
    for field in ("repo_root", "participant_root", "generated_root", "local_data_root"):
        assert getattr(service_config, field) == getattr(cli_config, field), field
    assert service_config.generated_root == tmp_path / "generated"
    assert service_config.local_data_root == tmp_path / "local-data"
    assert service_config.service_port == 0


# ---------------------------------------------------------------------------------- E5

SECRET_KEY = "outside_only_key_name_7f3a"


def _outside_record(tmp_path: Path) -> Path:
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    record = outside / "record.yaml"
    record.write_text(f"{SECRET_KEY}: the contents of a file outside the tree\n")
    return record


@pytest.mark.parametrize(
    "relative",
    [
        "progress.yaml",
        f"{VERIFIED}/review.yaml",
        f"{VERIFIED}/submission.yaml",
        f"{VERIFIED}/review-20260101000000.yaml",
        f"{READY}/submission.yaml",
    ],
)
def test_a_state_record_that_is_a_link_is_a_load_error_that_reads_nothing(
    config: AppConfig, tmp_path: Path, relative: str
) -> None:
    record = _outside_record(tmp_path)
    target = config.participant_root / relative
    target.unlink(missing_ok=True)
    target.symlink_to(record)

    report = ProblemReport()
    assert load_world(config, report) is None
    text = report.to_text()
    assert SECRET_KEY not in text
    assert any(
        problem.source.endswith(Path(relative).name) and "symbolic link" in problem.public_message
        for problem in report.errors
    ), text


def test_a_review_record_that_is_a_link_is_left_out_of_the_history(
    config: AppConfig, tmp_path: Path
) -> None:
    from quest_app.progress import load_participant_state
    from quest_app.review import DamagedRecordError, _read_record, review_history

    state = load_participant_state(config, SchemaSet(config.schemas_root), ProblemReport())
    assert state is not None
    attempt = state.progress.attempt_for("base-camp-repository-safety")
    assert attempt is not None
    archive = config.participant_root / VERIFIED / "review-20260101000000.yaml"
    archive.symlink_to(_outside_record(tmp_path))

    assert all(SECRET_KEY not in item for item in review_history(config, attempt))
    with pytest.raises(DamagedRecordError) as refused:
        _read_record(config, archive)
    assert SECRET_KEY not in str(refused.value)


def test_the_progress_store_refuses_a_linked_progress_file(
    config: AppConfig, tmp_path: Path
) -> None:
    progress = config.participant_root / "progress.yaml"
    moved = tmp_path / "outside" / "progress.yaml"
    moved.parent.mkdir()
    shutil.move(progress, moved)
    progress.symlink_to(moved)

    with pytest.raises(StoreError, match="symbolic link"):
        ProgressStore(config).read()
