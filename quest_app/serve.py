"""The local action service.

It exists only to do the things a static page cannot safely do: record a state change, create
an evidence package, read Git status, run a registered validator, rebuild. Everything it is
*not* allowed to do is enforced here rather than assumed, because a localhost service is
still reachable by every program and every page on the machine.

The shape of the defence, in the order a request meets it:

1. **Loopback only.** A non-loopback bind address is refused at startup, not warned about.
2. **Same-origin.** `Origin` and `Referer`, when present, must match the address actually
   bound. A page on another site cannot post here from your browser.
3. **Per-run token.** Every state-changing request carries a token minted at startup and
   never written to disk. A page that has not been served by this run cannot have it.
4. **Strict body.** JSON only, with a hard size cap read before the body is.
5. **Allowlisted actions.** The caller names an action ID and a quest ID from the loaded
   content. No path and no command ever crosses the boundary.

`docs/SECURITY-AND-PRIVACY.md` is the source for all of it.
"""

from __future__ import annotations

import json
import mimetypes
import secrets
import socket
import sys
import threading
from dataclasses import dataclass
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.git_status import summary_for
from quest_app.pipeline import load_world
from quest_app.state_machine import BY_ACTION, allowed_actions
from quest_app.store import ProgressStore, StoreError, start_attempt, transition_attempt

MAX_BODY_BYTES = 64 * 1024
LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1", "localhost"})
JSON_CONTENT_TYPE = "application/json"

# Every action the service will perform. A request naming anything else is refused before
# any state is read, and the list is the complete surface of what this process can change.
MUTATING_ACTIONS = frozenset(BY_ACTION) | {"rebuild", "run-validator"}
READ_ACTIONS = frozenset({"health", "git-status", "actions"})


class UnsafeBindError(RuntimeError):
    """A bind address that is not loopback."""


@dataclass(slots=True)
class ServiceState:
    """What one run of the service knows. The token lives here and nowhere else."""

    config: AppConfig
    token: str
    schemas: SchemaSet
    lock: threading.Lock
    # The port actually bound, which is not the configured one when the configuration asks
    # for 0 and the kernel chooses. Origin checking must compare against what was bound, or
    # it refuses every same-origin request.
    bound_port: int = 0


def assert_loopback(host: str) -> None:
    """Refuse to bind anywhere reachable from another machine.

    A warning would not be enough: the difference between `127.0.0.1` and `0.0.0.0` is the
    difference between a tool on your laptop and an unauthenticated service on the network
    that can write files.
    """
    if host in LOOPBACK_ADDRESSES:
        return
    try:
        resolved = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeBindError(f"{host!r} could not be resolved") from exc
    for entry in resolved:
        address = str(entry[4][0])
        if not _is_loopback(address):
            raise UnsafeBindError(
                f"{host!r} resolves to {address}, which is not loopback. "
                "This service binds to 127.0.0.1 only."
            )


def _is_loopback(address: str) -> bool:
    import ipaddress

    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


class ActionHandler(BaseHTTPRequestHandler):
    """The whole HTTP surface. Two GET routes, one POST route, and static files."""

    server_version = "GoldenThread"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def __init__(self, *args: Any, state: ServiceState, **kwargs: Any) -> None:
        self.state = state
        super().__init__(*args, **kwargs)

    # ---------------------------------------------------------------- plumbing

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - base class signature
        """One line per request, on stderr, with no query string.

        A query string can carry a filter a participant typed; it has no place in a log that
        may be pasted into an issue.
        """
        sys.stderr.write(f"{self.address_string()} {format % args}\n")

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{JSON_CONTENT_TYPE}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        )

    def _refuse(self, status: HTTPStatus, reason: str) -> None:
        self._send(status, {"ok": False, "error": reason})

    # ---------------------------------------------------------------- checks

    def _origin_is_acceptable(self) -> bool:
        """Reject a cross-origin state-changing request.

        Checked for `Origin` and `Referer` both, because a browser sends one or the other
        depending on the request. A missing header is accepted: a command-line client sends
        neither, and the token is what actually authorises the request.
        """
        port = self.state.bound_port or self.state.config.service_port
        expected = {
            f"http://{self.state.config.service_host}:{port}",
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
        }
        for header in ("Origin", "Referer"):
            value = self.headers.get(header)
            if not value:
                continue
            parsed = urlparse(value)
            if f"{parsed.scheme}://{parsed.netloc}" not in expected:
                return False
        return True

    def _read_json_body(self) -> dict[str, Any] | None:
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if content_type != JSON_CONTENT_TYPE:
            self._refuse(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send application/json.")
            return None
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._refuse(HTTPStatus.BAD_REQUEST, "A valid Content-Length is required.")
            return None
        if length <= 0:
            self._refuse(HTTPStatus.BAD_REQUEST, "An empty body is not a request.")
            return None
        if length > MAX_BODY_BYTES:
            # Checked before reading, so an oversized body is never buffered.
            self._refuse(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "The request body is too large.")
            return None
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._refuse(HTTPStatus.BAD_REQUEST, "The body is not valid JSON.")
            return None
        if not isinstance(payload, dict):
            self._refuse(HTTPStatus.BAD_REQUEST, "The body must be a JSON object.")
            return None
        return payload

    # ---------------------------------------------------------------- routes

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send(HTTPStatus.OK, self._health())
            return
        if path == "/api/git-status":
            self._send(
                HTTPStatus.OK, {"ok": True, "git": summary_for(self.state.config.repo_root, None)}
            )
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/action":
            self._refuse(HTTPStatus.NOT_FOUND, "There is no such endpoint.")
            return
        if not self._origin_is_acceptable():
            self._refuse(HTTPStatus.FORBIDDEN, "Cross-origin requests are refused.")
            return
        payload = self._read_json_body()
        if payload is None:
            return
        token = payload.get("token")
        if not isinstance(token, str) or not secrets.compare_digest(token, self.state.token):
            # Constant-time comparison: a timing difference here would leak the token one
            # character at a time to anything that can post to this port.
            self._refuse(HTTPStatus.FORBIDDEN, "A valid request token is required.")
            return

        action = payload.get("action")
        if not isinstance(action, str) or action not in MUTATING_ACTIONS:
            self._refuse(HTTPStatus.BAD_REQUEST, "That is not an action this application performs.")
            return

        with self.state.lock:
            try:
                self._send(HTTPStatus.OK, self._perform(action, payload))
            except StoreError as exc:
                self._refuse(HTTPStatus.CONFLICT, str(exc))
            except ValueError as exc:
                self._refuse(HTTPStatus.BAD_REQUEST, str(exc))

    # ---------------------------------------------------------------- work

    def _load(self) -> Any:
        report = ProblemReport()
        world = load_world(self.state.config, report)
        if world is None:
            raise StoreError(
                "The curriculum does not currently validate, so nothing can be changed: "
                + "; ".join(problem.public_message for problem in report.errors[:3])
            )
        return world

    def _perform(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        world = self._load()
        store = ProgressStore(self.state.config)

        if action == "rebuild":
            result = build_site(world)
            return {"ok": True, "action": action, "pages": result.page_count}

        quest_id = payload.get("quest_id")
        if not isinstance(quest_id, str) or quest_id not in world.content.quests:
            # A quest ID is matched against loaded content, so it can only ever name
            # something the build already knows about. No path reaches the filesystem.
            raise ValueError("That quest does not exist.")
        quest = world.content.quests[quest_id]

        if action == "run-validator":
            # Not a transition (ADR-017). It appends a result and changes nothing else.
            return self._run_validator(world, quest_id, payload)

        if action == "start-quest":
            attempt_id = start_attempt(
                store,
                quest_id=quest_id,
                quest_version=quest.version,
                content_hash=quest.content_hash,
                schemas=self.state.schemas,
            )
            state = "in_progress"
        else:
            if action == "mark-locally-validated":
                self._require_qualifying_validation(world, quest_id)
            if action in ("mark-evidence-ready", "submit-for-review"):
                self._require_clean_secret_scan(world, quest_id)
            new_state = transition_attempt(
                store, quest_id=quest_id, action=action, schemas=self.state.schemas
            )
            state = new_state.value
            attempt_id = None

        build_site(self._load())
        return {
            "ok": True,
            "action": action,
            "quest_id": quest_id,
            "state": state,
            "attempt_id": attempt_id,
        }

    def _run_validator(self, world: Any, quest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from quest_app.evidence import new_run_id, store_result
        from quest_app.validator_registry import ValidatorError, load_registry
        from quest_app.validator_runner import run_validator

        validator_id = payload.get("validator_id")
        if not isinstance(validator_id, str):
            raise ValueError("A validator ID is required.")
        quest = world.content.quests[quest_id]
        if validator_id not in quest.validators:
            # The quest decides which validators apply to it, so a caller cannot run an
            # arbitrary registered validator against arbitrary work.
            raise ValueError("That validator is not declared by this quest.")

        report = ProblemReport()
        registry = load_registry(self.state.config, report)
        if registry is None:
            raise StoreError("The validator registry could not be loaded.")

        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            raise StoreError("Start the quest before running its checks.")

        try:
            definition = registry.get(validator_id)
            result = run_validator(
                definition,
                self.state.config,
                quest_id=quest_id,
                attempt_id=attempt.attempt_id,
                run_id=new_run_id(validator_id),
                parameters=payload.get("parameters"),
            )
        except ValidatorError as exc:
            raise ValueError(str(exc)) from exc

        stored = store_result(self.state.config, attempt.evidence_path, result.to_document())
        build_site(self._load())
        return {
            "ok": True,
            "action": "run-validator",
            "quest_id": quest_id,
            "validator_id": validator_id,
            "outcome": result.outcome,
            "run_id": result.run_id,
            "result_path": stored,
            "note": "A validation run never changes quest state.",
        }

    def _require_clean_secret_scan(self, world: Any, quest_id: str) -> None:
        """Refuse to prepare a submission that carries a credential.

        The asymmetry is the argument: a false positive costs a minute, and a missed
        credential costs a rotation and an awkward conversation.
        """
        from quest_app.evidence import scan_evidence

        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            return
        findings = scan_evidence(self.state.config, attempt.evidence_path)
        if findings:
            locations = ", ".join(f"{f.path}:{f.line}" for f in findings[:3])
            raise StoreError(
                f"Something secret-like is in your evidence ({locations}). "
                "Remove it before submitting; the scan never reports the value itself."
            )

    def _require_qualifying_validation(self, world: Any, quest_id: str) -> None:
        """`locally_validated` is a claim about validator results, so the results decide.

        Without this the state would be a participant's assertion wearing a validator's
        authority, which is exactly the blurring the progress model exists to prevent.
        """
        quest = world.content.quests[quest_id]
        if not quest.validators:
            return
        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            raise StoreError("There is no attempt to validate.")
        results = participant.results_for(attempt) if participant else ()
        latest = {result.validator_id: result for result in results}
        missing = [
            validator
            for validator in quest.validators
            if validator not in latest or not latest[validator].qualifies
        ]
        if missing:
            raise StoreError(
                "These checks have not returned a qualifying result yet: " + ", ".join(missing)
            )

    def _health(self) -> dict[str, Any]:
        report = ProblemReport()
        world = load_world(self.state.config, report)
        config = self.state.config
        return {
            "ok": world is not None,
            "bound_to": f"{config.service_host}:{self.state.bound_port}",
            "loopback_only": True,
            "content_valid": world is not None,
            "errors": len(report.errors),
            "warnings": len(report.warnings),
            "participant_state": world is not None and world.participant is not None,
            "actions": sorted(MUTATING_ACTIONS | READ_ACTIONS),
        }

    # ---------------------------------------------------------------- static

    def _serve_static(self, path: str) -> None:
        """Serve the generated site, and nothing outside it.

        The requested path is decoded, joined, resolved, and then checked to be inside the
        output directory. Resolving first and checking after is what makes `..`, a symlink
        planted in `generated/`, and an encoded traversal all land in the same refusal.
        """
        root = self.state.config.generated_root.resolve()
        relative = unquote(path).lstrip("/")
        if "\x00" in relative:
            self._refuse(HTTPStatus.BAD_REQUEST, "Invalid path.")
            return
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            self._refuse(HTTPStatus.FORBIDDEN, "That path is outside the generated site.")
            return
        if candidate.is_dir():
            candidate = candidate / "index.html"
        if not candidate.is_file():
            self._refuse(HTTPStatus.NOT_FOUND, "No such page. Run a build if you expected one.")
            return

        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def create_server(config: AppConfig) -> tuple[ThreadingHTTPServer, ServiceState]:
    """Bind the service, or refuse. The token is minted here and never persisted."""
    assert_loopback(config.service_host)
    state = ServiceState(
        config=config,
        token=secrets.token_urlsafe(32),
        schemas=SchemaSet(config.schemas_root),
        lock=threading.Lock(),
    )
    handler = partial(ActionHandler, state=state)
    server = ThreadingHTTPServer((config.service_host, config.service_port), handler)
    state.bound_port = int(server.server_address[1])
    return server, state


def run_service(config: AppConfig, *, host: str | None = None, port: int | None = None) -> int:
    """Build once, then serve until interrupted."""
    from quest_app.config import AppConfig as Config

    if host or port:
        config = Config.for_repo(
            config.repo_root,
            participant_root=config.participant_root,
            service_host=host or config.service_host,
            service_port=port or config.service_port,
        )

    report = ProblemReport()
    world = load_world(config, report)
    if world is None:
        for problem in report.errors:
            print(problem.to_text(), file=sys.stderr)
        print("content does not validate, so nothing was generated", file=sys.stderr)
        return 1
    build_site(world)

    try:
        server, state = create_server(config)
    except UnsafeBindError as exc:
        print(f"refusing to start: {exc}", file=sys.stderr)
        return 2

    address = f"http://{config.service_host}:{server.server_address[1]}/"
    print(f"Golden Thread Quest is at {address}", file=sys.stderr)
    print(f"Request token for this run: {state.token}", file=sys.stderr)
    print("The token is not written to disk. Stop with Ctrl-C.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    finally:
        server.server_close()
    return 0


def describe_actions(current: Any) -> list[dict[str, str]]:
    return [
        {"action": transition.action, "description": transition.description}
        for transition in allowed_actions(current)
    ]
