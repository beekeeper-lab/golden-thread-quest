"""The loopback service's defenses, each one exercised rather than assumed.

A localhost service is reachable by every program and every page on the machine, so each of
these is a real attack surface and not a formality.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.serve import MAX_BODY_BYTES, UnsafeBindError, assert_loopback, create_server


@pytest.fixture
def service(config: AppConfig) -> Iterator[tuple[str, str]]:
    """A running service on an ephemeral loopback port, torn down after the test."""
    bound = AppConfig.for_repo(
        config.repo_root, participant_root=config.participant_root, service_port=0
    )
    # The service serves what a build produced, so a fixture that never builds would test
    # a 404 rather than the static-file defenses.
    report = ProblemReport()
    world = load_world(bound, report)
    assert world is not None, report.to_text()
    build_site(world)

    server, state = create_server(bound)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", state.token
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def post(
    base: str,
    payload: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
    raw: bytes | None = None,
    content_type: str = "application/json",
) -> tuple[int, dict[str, Any]]:
    data = raw if raw is not None else json.dumps(payload or {}).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed loopback URL built in this test
        f"{base}/api/action",
        data=data,
        method="POST",
        headers={"Content-Type": content_type, **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def post_form(
    base: str, path: str, fields: dict[str, str], *, headers: dict[str, str] | None = None
) -> tuple[int, bytes]:
    """The no-JavaScript route, which the JSON helper above never reaches.

    Every allowlist and token test here posted to `/api/action`, so the form route carried
    the same guards with nothing asserting it.
    """
    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(  # noqa: S310 - fixed loopback URL built in this test
        f"{base}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def raw_get(base: str, path: str) -> int:
    """GET without letting the client library tidy the path first.

    `urllib` normalises `/../x` away before the request is sent, so all four traversal
    cases below arrived at the service as ordinary paths and passed even with the
    containment check removed. Over a socket, `GET /../pyproject.toml` on that same mutant
    returned 200 and the file. The control was right; the test never reached it.
    """
    import socket

    host, port = base.removeprefix("http://").split(":")
    request = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    with socket.create_connection((host, int(port)), timeout=10) as sock:
        sock.sendall(request.encode())
        first = b""
        while b"\r\n" not in first:
            chunk = sock.recv(4096)
            if not chunk:
                break
            first += chunk
    return int(first.split(b" ")[1])


def get(base: str, path: str) -> int:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=10) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)


class TestBinding:
    """The difference between 127.0.0.1 and 0.0.0.0 is a tool versus a network service."""

    @pytest.mark.parametrize(
        "host",
        ["0.0.0.0", "192.168.1.10", "example.com", "::"],  # noqa: S104 - refusing these is the test
    )
    def test_a_non_loopback_address_is_refused(self, host: str) -> None:
        with pytest.raises(UnsafeBindError):
            assert_loopback(host)

    @pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
    def test_loopback_is_accepted(self, host: str) -> None:
        assert assert_loopback(host) is None


class TestARebuildWhileServing:
    """A second process rebuilding the site must not disable the pages being served."""

    def test_the_probe_tells_a_running_service_from_a_dead_port(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        from quest_app.serve import is_service_running

        base, _ = service
        port = int(base.rsplit(":", 1)[1])
        running = AppConfig.for_repo(
            config.repo_root, participant_root=config.participant_root, service_port=port
        )
        # Port 9 is discard: reachable as a concept, never answering as this application.
        dead = AppConfig.for_repo(
            config.repo_root, participant_root=config.participant_root, service_port=9
        )

        assert is_service_running(running) is True
        assert is_service_running(dead) is False

    def test_a_build_while_serving_keeps_the_controls_alive(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        """`quest-app action` built with the offline view whatever was happening.

        One command from a second terminal replaced every served page with a copy saying the
        service was not running and disabling every control, and only restarting the server
        undid it.
        """
        from quest_app.view_models import offline_service_view, online_service_view

        _, _ = service  # the fixture's value is the running server, not its address
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()

        def pages_that_can_act() -> int:
            return sum(
                'method="post"' in page.read_text().lower()
                for page in config.generated_root.rglob("index.html")
            )

        build_site(world, service=offline_service_view())
        offline = pages_that_can_act()

        build_site(world, service=online_service_view())
        online = pages_that_can_act()

        assert offline == 0, "the offline view is exactly what the fix has to avoid producing"
        assert online > 0, "a page built while the service runs must still be able to act"


class TestTheFormRoute:
    """The route a participant with JavaScript disabled uses, guarded like the JSON one."""

    def test_an_action_outside_the_allowlist_is_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post_form(
            base, "/api/action/delete-everything/base-camp-repository-safety", {"token": token}
        )
        assert status == 400

    @pytest.mark.parametrize("header", ["Origin", "Referer"])
    def test_a_cross_origin_form_post_is_refused(
        self, service: tuple[str, str], header: str
    ) -> None:
        """`TestCrossOrigin` covers `/api/action` only.

        Round 4 found the form route carrying guards nothing asserted, and round 5 found
        its origin check in the same state: removing it left the whole suite green. The
        token still stands behind it, so this is depth rather than an open door.
        """
        base, token = service
        status, _ = post_form(
            base,
            "/api/action/rebuild/base-camp-repository-safety",
            {"token": token},
            headers={header: "https://evil.example"},
        )
        assert status == 403

    def test_a_wrong_token_is_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post_form(
            base, "/api/action/start-quest/base-camp-repository-safety", {"token": "x" * len(token)}
        )
        assert status == 403

    def test_a_locked_quest_is_refused(self, service: tuple[str, str]) -> None:
        """The same rule the CLI enforces, from the other caller of the shared action layer.

        Prerequisites were computed for display and enforced nowhere, so the browser greyed
        out Start while both POST routes performed it.
        """
        base, token = service
        status, body = post_form(
            base, "/api/action/start-quest/scrum-standup-digest", {"token": token}
        )

        # The form route answers a refusal the way a page does: a redirect carrying the
        # problem, not a status code only a script would read.
        assert status == 200
        assert b"locked until a reviewer has verified" in body


class TestRequestToken:
    def test_a_state_change_without_a_token_is_refused(self, service: tuple[str, str]) -> None:
        base, _ = service
        status, body = post(base, {"action": "rebuild"})
        assert status == 403
        assert body["ok"] is False

    def test_a_wrong_token_is_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post(base, {"action": "rebuild", "token": "x" * len(token)})
        assert status == 403

    def test_a_token_that_is_not_ascii_is_refused_rather_than_fatal(
        self, service: tuple[str, str]
    ) -> None:
        """A wrong token built out of the letter x cannot catch this.

        `secrets.compare_digest` raises on a `str` carrying a non-ASCII character, inside the
        handler, so one such token took the endpoint down with no HTTP response and a
        traceback holding absolute paths.
        """
        base, token = service
        status, _ = post(base, {"action": "rebuild", "token": "é" * len(token)})
        assert status == 403
        status, _ = post(base, {"action": "rebuild", "token": token})
        assert status == 200, "the service is still answering"

    def test_the_correct_token_is_accepted(self, service: tuple[str, str]) -> None:
        base, token = service
        status, body = post(base, {"action": "rebuild", "token": token})
        assert status == 200
        assert body["ok"] is True

    def test_reading_does_not_require_a_token(self, service: tuple[str, str]) -> None:
        """Health and Git status change nothing, so they are readable without one."""
        base, _ = service
        assert get(base, "/api/health") == 200
        assert get(base, "/api/git-status") == 200


class TestCrossOrigin:
    @pytest.mark.parametrize("header", ["Origin", "Referer"])
    def test_a_cross_origin_state_change_is_refused(
        self, service: tuple[str, str], header: str
    ) -> None:
        """A page on another site must not be able to post here from your browser."""
        base, token = service
        status, _ = post(
            base, {"action": "rebuild", "token": token}, headers={header: "https://evil.example"}
        )
        assert status == 403

    def test_a_same_origin_request_is_accepted(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post(base, {"action": "rebuild", "token": token}, headers={"Origin": base})
        assert status == 200


class TestRequestShape:
    def test_a_non_json_content_type_is_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post(base, {"action": "rebuild", "token": token}, content_type="text/plain")
        assert status == 415

    def test_an_oversized_body_is_refused_before_it_is_read(self, service: tuple[str, str]) -> None:
        base, _ = service
        payload = b'{"a":"' + b"x" * (MAX_BODY_BYTES + 1000) + b'"}'
        status, _ = post(base, raw=payload)
        assert status == 413

    def test_a_malformed_body_is_refused(self, service: tuple[str, str]) -> None:
        base, _ = service
        assert post(base, raw=b"not json")[0] == 400

    def test_an_empty_body_is_refused(self, service: tuple[str, str]) -> None:
        base, _ = service
        assert post(base, raw=b"")[0] == 400

    def test_a_json_array_is_refused(self, service: tuple[str, str]) -> None:
        base, _ = service
        assert post(base, raw=b"[1,2,3]")[0] == 400


class TestActionAllowlist:
    @pytest.mark.parametrize(
        "action",
        ["rm -rf /", "eval", "../../etc/passwd", "start-quest; rm -rf /", "", "__import__"],
    )
    def test_an_action_outside_the_allowlist_is_refused(
        self, service: tuple[str, str], action: str
    ) -> None:
        base, token = service
        status, _ = post(base, {"action": action, "token": token})
        assert status == 400

    @pytest.mark.parametrize(
        "quest_id",
        ["../../etc/passwd", "/etc/passwd", "..%2f..%2fetc", "no-such-quest", "", "$(whoami)"],
    )
    def test_a_quest_id_is_matched_against_loaded_content(
        self, service: tuple[str, str], quest_id: str
    ) -> None:
        """No path crosses the boundary: an ID either names loaded content or it is refused."""
        base, token = service
        status, _ = post(base, {"action": "start-quest", "quest_id": quest_id, "token": token})
        assert status == 400


class TestStaticServing:
    @pytest.mark.parametrize(
        "path",
        [
            "/../../etc/passwd",
            "/..%2f..%2fetc%2fpasswd",
            "/../pyproject.toml",
            "/%2e%2e/%2e%2e/etc/passwd",
        ],
    )
    def test_traversal_out_of_the_generated_site_is_refused(
        self, service: tuple[str, str], path: str
    ) -> None:
        base, _ = service
        assert get(base, path) in (403, 404)
        assert raw_get(base, path) in (403, 404), (
            "the same path unnormalised, which is the only form that reaches the check"
        )

    def test_traversal_to_a_file_that_exists_outside_is_refused(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        """The parametrised cases above reach for files that do not exist in a test tree.

        403 and 404 are both acceptable answers there, so they pass whether the containment
        check runs or not. This one plants a real file one level above the output and sends
        the request over a socket, because `urllib` normalises the `..` away before it
        reaches the service. Removing the check turns this into 200 and the file's contents.
        """
        planted = config.repo_root / "planted-secret.txt"
        planted.write_text("not for the browser\n", encoding="utf-8")
        base, _ = service
        assert raw_get(base, "/../planted-secret.txt") == 403

    def test_a_symlink_planted_in_the_output_cannot_escape(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        """Resolving before checking is what makes a planted link land in the same refusal."""
        outside = config.repo_root / "pyproject.toml"
        outside.write_text("[project]\nname='x'\n")
        link = config.generated_root / "escape.toml"
        link.symlink_to(outside)
        base, _ = service
        assert get(base, "/escape.toml") == 403

    def test_the_generated_site_is_served(self, service: tuple[str, str]) -> None:
        base, _ = service
        assert get(base, "/") == 200
        assert get(base, "/map/") == 200

    def test_a_missing_page_says_so(self, service: tuple[str, str]) -> None:
        base, _ = service
        assert get(base, "/no/such/page/") == 404


class TestResponseHeaders:
    def test_every_response_carries_the_security_headers(self, service: tuple[str, str]) -> None:
        base, _ = service
        with urllib.request.urlopen(f"{base}/api/health", timeout=10) as response:  # noqa: S310
            headers = dict(response.headers)
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "no-referrer"
        assert "default-src 'none'" in headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]


def test_the_token_is_never_written_to_disk(service: tuple[str, str], config: AppConfig) -> None:
    """A token in a file is a token any process on the machine can read."""
    base, token = service
    del base
    for path in config.repo_root.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".yaml", ".md", ".html", ".log"}:
            assert token not in path.read_text(errors="ignore"), f"token leaked into {path.name}"


def test_no_absolute_path_appears_in_an_error_response(
    service: tuple[str, str], config: AppConfig
) -> None:
    base, token = service
    _, body = post(base, {"action": "start-quest", "quest_id": "no-such-quest", "token": token})
    assert str(config.repo_root) not in json.dumps(body)


def test_a_service_error_names_no_internal_detail(service: tuple[str, str]) -> None:
    base, _ = service
    _, body = post(base, raw=b"not json")
    assert "Traceback" not in json.dumps(body)


class TestFindingTheRunningService:
    """`quest-app action` rebuilds the site, and the pages it writes say whether state can
    change from them. It asks whether a service is running first — at the configured port,
    which is 8765 unless something told it otherwise, and nothing told it otherwise.

    `serve --port` is an advertised flag and `action` has no matching one, so round 4's fix
    for "one CLI action disabled every control on every served page" held only for a service
    on the default port. On any other port the probe found nothing, concluded the service was
    down, and published exactly the dead page it existed to prevent.
    """

    def test_the_probe_asks_at_the_port_the_service_actually_bound(
        self, service: tuple[str, str], config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Asserted on the URL the probe requests, not on what answers it.

        Asserting "the service was found" passes for the wrong reason on a machine where
        anything at all is listening on 8765, which is exactly the default this defect is
        about. The address asked for is the behaviour.
        """
        import urllib.request

        from quest_app.serve import PORT_FILENAME, is_service_running

        base, _ = service
        bound = int(base.rsplit(":", 1)[1])
        assert bound != config.service_port, "the fixture must not sit on the default port"

        port_file = config.local_data_root / PORT_FILENAME
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(f"{bound}\n", encoding="utf-8")

        asked: list[str] = []
        real = urllib.request.urlopen

        def record(url: Any, *args: Any, **kwargs: Any) -> Any:
            asked.append(url if isinstance(url, str) else url.full_url)
            return real(url, *args, **kwargs)

        monkeypatch.setattr(urllib.request, "urlopen", record)
        found = is_service_running(config)

        assert asked == [f"http://{config.service_host}:{bound}/"], (
            f"the probe asked at {asked}, not at the port the service bound"
        )
        assert found, "and the service answers there"

    def test_a_stale_port_file_is_not_believed(self, config: AppConfig) -> None:
        """The file is a hint. The header is the authority."""
        from quest_app.serve import PORT_FILENAME, is_service_running, running_service_port

        port_file = config.local_data_root / PORT_FILENAME
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text("9\n", encoding="utf-8")
        assert running_service_port(config) == 9
        assert not is_service_running(config)

        port_file.write_text("not a port\n", encoding="utf-8")
        assert running_service_port(config) == config.service_port, "unreadable falls back"
