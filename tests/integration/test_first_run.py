"""A participant who has never done anything must be able to start.

The first version could not: `start_attempt` read the progress file before doing anything,
and the only documented way to create that file was to start a quest. Every test passed
because every fixture copied a participant directory that already had one — which is exactly
the state the defect hid behind.
"""

from __future__ import annotations

import json
import shutil
import threading
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.serve import create_server
from quest_app.store import ProgressStore, start_attempt
from quest_app.view_models import online_service_view

QUEST = "base-camp-repository-safety"


@pytest.fixture
def empty_participant(content_repo: Path) -> AppConfig:
    """The real content tree, and a participant directory with nothing in it at all."""
    shutil.rmtree(content_repo / "participant")
    (content_repo / "participant").mkdir()
    return AppConfig.for_repo(
        content_repo, participant_root=content_repo / "participant", service_port=0
    )


def test_content_loads_with_no_participant_at_all(empty_participant: AppConfig) -> None:
    report = ProblemReport()
    world = load_world(empty_participant, report)
    assert world is not None, report.to_text()
    assert world.participant is None


def test_the_site_builds_with_no_participant_at_all(empty_participant: AppConfig) -> None:
    report = ProblemReport()
    world = load_world(empty_participant, report)
    assert world is not None
    result = build_site(world, built_at="2026-09-17T00:00:00+00:00")
    assert result.page_count > 0
    home = (empty_participant.generated_root / "index.html").read_text()
    assert "Start at" in home, "a new participant is told where to begin"


def test_starting_a_quest_creates_the_progress_file(empty_participant: AppConfig) -> None:
    """The circular refusal: starting was the only way to create the file it required."""
    report = ProblemReport()
    world = load_world(empty_participant, report)
    assert world is not None
    store = ProgressStore(empty_participant)
    assert not store.path.exists()

    quest = world.content.quests[QUEST]
    attempt_id = start_attempt(
        store,
        quest_id=QUEST,
        quest_version=quest.version,
        content_hash=quest.content_hash,
        schemas=SchemaSet(empty_participant.schemas_root),
        display_name="A New Participant",
        track_id=world.content.site.default_track,
    )

    assert store.path.exists()
    data = yaml.safe_load(store.path.read_text())
    assert data["participant"]["display_name"] == "A New Participant"
    assert data["attempts"][0]["attempt_id"] == attempt_id
    assert (
        empty_participant.participant_root / "evidence" / QUEST / attempt_id / "PROOF.md"
    ).is_file()


def test_the_new_state_loads_cleanly(empty_participant: AppConfig) -> None:
    report = ProblemReport()
    world = load_world(empty_participant, report)
    assert world is not None
    quest = world.content.quests[QUEST]
    start_attempt(
        ProgressStore(empty_participant),
        quest_id=QUEST,
        quest_version=quest.version,
        content_hash=quest.content_hash,
        schemas=SchemaSet(empty_participant.schemas_root),
        track_id=world.content.site.default_track,
    )
    fresh = ProblemReport()
    reloaded = load_world(empty_participant, fresh)
    assert reloaded is not None, fresh.to_text()
    assert reloaded.participant is not None


@pytest.fixture
def first_run_service(empty_participant: AppConfig) -> Iterator[tuple[str, str, AppConfig]]:
    report = ProblemReport()
    world = load_world(empty_participant, report)
    assert world is not None, report.to_text()
    build_site(world, service=online_service_view())
    server, state = create_server(empty_participant)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", state.token, empty_participant
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.slow
def test_the_very_first_action_through_the_service_succeeds(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    """End to end from nothing: the exact path a pilot participant takes on day one."""
    base, token, config = first_run_service
    request = urllib.request.Request(  # noqa: S310 - fixed loopback URL
        f"{base}/api/action",
        data=json.dumps(
            {"action": "start-quest", "quest_id": QUEST, "token": token, "confirm": True}
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        body = json.loads(response.read())

    assert body["ok"] is True, body
    assert body["state"] == "in_progress"
    assert (config.participant_root / "progress.yaml").exists()


@pytest.mark.slow
def test_the_served_page_carries_a_live_form_with_the_token(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    """The token reaches the form without ever being written to a file."""
    base, token, config = first_run_service
    with urllib.request.urlopen(f"{base}/quests/{QUEST}/", timeout=20) as response:  # noqa: S310
        html = response.read().decode()

    assert "<form" in html
    assert token in html, "the placeholder is substituted as the page is served"
    assert "__GTQ_REQUEST_TOKEN__" not in html

    on_disk = (config.generated_root / "quests" / QUEST / "index.html").read_text()
    assert token not in on_disk, "the token must never be written to disk"
    assert "__GTQ_REQUEST_TOKEN__" in on_disk


@pytest.mark.slow
def test_a_form_submission_performs_the_action(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    """The no-JavaScript path: an ordinary form post, not a hand-crafted JSON request."""
    import urllib.error
    from urllib.parse import urlencode

    base, token, config = first_run_service
    request = urllib.request.Request(  # noqa: S310
        f"{base}/api/action/start-quest/{QUEST}/",
        data=urlencode({"token": token, "confirm": "yes"}).encode(),
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{base}/quests/{QUEST}/",
        },
    )
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler)
    try:
        opener.open(request, timeout=20)
    except urllib.error.HTTPError as error:  # pragma: no cover - a redirect loop would land here
        assert error.code in (303, 200), error.code

    data = yaml.safe_load((config.participant_root / "progress.yaml").read_text())
    assert any(attempt["quest_id"] == QUEST for attempt in data["attempts"])


@pytest.mark.slow
def test_a_form_without_the_token_is_refused(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    import urllib.error
    from urllib.parse import urlencode

    base, _, config = first_run_service
    request = urllib.request.Request(  # noqa: S310
        f"{base}/api/action/start-quest/{QUEST}/",
        data=urlencode({"token": "x" * 43}).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=20)  # noqa: S310
    assert error.value.code == 403
    assert not (config.participant_root / "progress.yaml").exists()


@pytest.mark.slow
def test_a_refused_action_says_so_on_the_page(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    """A refusal that nothing renders is worse than no refusal at all.

    The service redirected with `?problem=…` and nothing read it. With a token in PROOF.md,
    `mark-evidence-ready` was refused and the page the participant landed on still showed
    the previous build's panel saying the scan had found nothing.
    """
    from urllib.parse import urlencode

    base, token, config = first_run_service
    urllib.request.urlopen(  # noqa: S310
        urllib.request.Request(  # noqa: S310 - a fixed loopback URL built in this test
            f"{base}/api/action",
            data=json.dumps(
                {"action": "start-quest", "quest_id": QUEST, "token": token, "confirm": True}
            ).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        ),
        timeout=20,
    )

    data = yaml.safe_load((config.participant_root / "progress.yaml").read_text())
    evidence = data["attempts"][0]["evidence_path"]
    leaked = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow
    (config.resolve_participant_path(evidence) / "PROOF.md").write_text(f"token={leaked}\n")

    opener = urllib.request.build_opener()
    response = opener.open(
        urllib.request.Request(  # noqa: S310
            f"{base}/api/action/mark-evidence-ready/{QUEST}/",
            data=urlencode({"token": token, "confirm": "yes"}).encode(),
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": f"{base}/evidence/{QUEST}/",
            },
        ),
        timeout=30,
    )
    landed = response.read().decode()

    assert "That did not happen" in landed, "the refusal was not shown to the participant"
    assert "secret-like" in landed
    assert "found nothing secret-like" not in landed, (
        "the page still reassured the participant while a token sat in their evidence"
    )
    assert leaked not in landed, (
        "neither the refusal nor the PROOF.md preview may reproduce the value"
    )


@pytest.mark.slow
def test_an_unwritable_participant_directory_returns_a_real_response(
    first_run_service: tuple[str, str, AppConfig],
) -> None:
    """An OSError used to close the connection with no status and no body at all."""
    import urllib.error

    base, token, config = first_run_service
    mode = config.participant_root.stat().st_mode
    # Read and execute, no write: the shape of a synced or NAS-backed directory that has
    # gone read-only, which is the realistic version of this failure.
    config.participant_root.chmod(0o555)
    try:
        request = urllib.request.Request(  # noqa: S310
            f"{base}/api/action",
            data=json.dumps(
                {"action": "start-quest", "quest_id": QUEST, "token": token, "confirm": True}
            ).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
                body = json.loads(response.read())
                status = response.status
        except urllib.error.HTTPError as error:
            body = json.loads(error.read())
            status = error.code
    finally:
        config.participant_root.chmod(mode)

    assert status in (409, 500), status
    assert body["ok"] is False
    assert str(config.participant_root) not in json.dumps(body), "no absolute path in the reason"
