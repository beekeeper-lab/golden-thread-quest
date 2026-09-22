"""The local action service.

It exists only to do the things a static page cannot safely do: record a state change, create
an evidence package, read Git status, run a registered validator, rebuild. Everything it is
*not* allowed to do is enforced here rather than assumed, because a localhost service is
still reachable by every program and every page on the machine.

The shape of the defense, in the order a request meets it:

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

import contextlib
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
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from quest_app.actions import CONFIRMATIONS, MUTATING_ACTIONS, ActionRunner
from quest_app.build import build_site
from quest_app.config import APPLICATION_VERSION, AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport, filesystem_message
from quest_app.git_status import summary_for
from quest_app.pipeline import load_world
from quest_app.state_machine import allowed_actions
from quest_app.store import StoreError
from quest_app.view_models import online_service_view

MAX_BODY_BYTES = 64 * 1024
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
# Replaced in served HTML so a form can carry the token without it ever being written to a
# file. A page built by `quest build` keeps the placeholder, and the service refuses it.
TOKEN_PLACEHOLDER = "__GTQ_REQUEST_TOKEN__"  # noqa: S105 - a marker to replace, not a secret
# Where a refusal message is rendered into a served page. Substituted at request time from
# the `problem` query parameter, so it works with no JavaScript and survives a redirect.
# It is an HTML comment so that a statically built page opened from disk shows nothing rather
# than the literal marker; the whole comment is replaced, not just the text inside it.
FLASH_PLACEHOLDER = "<!--__GTQ_FLASH__-->"
LOOPBACK_ADDRESSES = frozenset({"127.0.0.1", "::1", "localhost"})
JSON_CONTENT_TYPE = "application/json"

# Every action the service will perform. A request naming anything else is refused before
# any state is read, and the list is the complete surface of what this process can change.


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


def _unexpected_message(error: Exception) -> str:
    """What to say about a failure this application did not anticipate.

    The type and nothing else. A traceback carries absolute paths, and this text is shown to
    a participant. The change, if there was one, is already on disk: an unexpected failure
    in the rebuild that follows is not a reason to say nothing at all, which is what
    happened before — no status, no body, and a closed connection.
    """
    return (
        f"Something unexpected went wrong ({type(error).__name__}). Any change you made was "
        "recorded; run `quest-app build` to rebuild the site."
    )


def _is_loopback(address: str) -> bool:
    import ipaddress

    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


SERVICE_HEADER = "X-Quest-App"


PORTS_DIRNAME = "service-ports"
PORT_FILE_MAX_BYTES = 16


def running_service_ports(config: AppConfig) -> list[int]:
    """Every port a service of this repository is currently claiming, then the default.

    One file per bound port, named by the port, written when a service binds and removed
    when it stops. Round 5 kept a single `service-port` file, which a repository hosting two
    services overwrote and either service's shutdown deleted for both: stopping the second
    one left the first serving pages while the CLI went back to probing 8765 and republished
    every page with its controls dead, which is the defect the file was added to fix.

    Each file is a hint, never an authority: the probe still requires this application's own
    response header, so a stale entry pointing at a port something else now holds is refused
    like any other stranger. The read is bounded because the only valid content is a handful
    of digits, and a `service-ports` entry symlinked at `/dev/zero` otherwise hangs the
    reader forever.
    """
    return [port for port, _ in _port_entries(config)]


def _port_entries(config: AppConfig) -> list[tuple[int, Path | None]]:
    """Each claimed port and the file that claims it; the default port claims nothing."""
    entries: list[tuple[int, Path | None]] = []
    directory = config.local_data_root / PORTS_DIRNAME
    try:
        listing = sorted(directory.iterdir())
    except OSError:
        listing = []
    for entry in listing:
        try:
            with entry.open("r", encoding="utf-8") as handle:
                port = int(handle.read(PORT_FILE_MAX_BYTES).strip())
        except (OSError, ValueError):
            continue
        if 1 <= port <= 65535:
            entries.append((port, entry))
    if config.service_port not in [port for port, _ in entries]:
        entries.append((config.service_port, None))
    return entries


def running_service_port(config: AppConfig) -> int:
    """The first port worth asking at. Kept for callers that want one number."""
    return running_service_ports(config)[0]


def is_service_running(config: AppConfig) -> bool:
    """Whether a service of this application is answering on the configured address.

    `quest-app action` built the site with the offline view whatever else was happening, so
    one command from a second terminal replaced every served page with a copy saying the
    service was down and disabling every control on it. Nothing in the application could
    undo that; only restarting the server could.

    The probe asks for a page and looks for this application's own header, because a bare
    TCP connect would call whatever else happened to hold the port a running service.

    It asks at the port the running service actually bound, not the configured default.
    `serve --port` is an advertised flag and `quest-app action` has no matching one, so
    round 4's fix held only for a service on 8765: on any other port the probe found
    nothing, decided the service was down, and published exactly the dead page it existed
    to prevent.
    """
    import urllib.error
    import urllib.request

    for port, entry in _port_entries(config):
        url = f"http://{config.service_host}:{port}/"
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.headers.get(SERVICE_HEADER):
                    return True
        except urllib.error.HTTPError as error:
            if error.headers.get(SERVICE_HEADER):
                return True
        except OSError as error:
            # Nothing is listening there. A service killed outright never ran its own
            # cleanup, and its entry otherwise stayed forever, costing every later probe a
            # timeout. Only a refusal prunes: a timeout might be a slow service.
            # `urlopen` wraps the refusal in a `URLError`, so the cause is what to read.
            refused = isinstance(error, ConnectionRefusedError) or isinstance(
                getattr(error, "reason", None), ConnectionRefusedError
            )
            if entry is not None and refused:
                with contextlib.suppress(OSError):
                    entry.unlink(missing_ok=True)
            continue
    return False


def _token_matches(supplied: str, expected: str) -> bool:
    """Compare a caller-supplied token in constant time, whatever bytes it contains.

    `secrets.compare_digest` raises on a `str` holding a non-ASCII character, and the raise
    happens inside the request handler, so a single `token=\u00e9` took the endpoint down
    without an HTTP response and printed a traceback carrying absolute paths. The wrong-token
    test missed it because it built its wrong token out of the letter x. Encoding both sides
    first keeps the comparison constant-time and makes a non-ASCII token an ordinary refusal.
    """
    return secrets.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))


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
        # Also the signature `is_service_running` probes for. A bare TCP connect would call
        # anything holding the port this application.
        self.send_header(SERVICE_HEADER, APPLICATION_VERSION)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        )

    def _refuse(self, status: HTTPStatus, reason: str) -> None:
        # Refusals happen before the declared body is read — wrong content type, bad length,
        # a cross-origin header, a wrong token — and HTTP/1.1 keeps the connection open, so
        # the unread bytes were parsed as the next request, with every header chosen by the
        # sender. That is a way past the origin check for anyone who can get one ordinary
        # POST through. The connection ends with the refusal instead.
        self.close_connection = True
        self._send(status, {"ok": False, "error": reason})

    # ---------------------------------------------------------------- checks

    def _host_is_acceptable(self) -> bool:
        """Reject a request that reached this port under someone else's name.

        Every page this service serves carries the run's request token, and until round 7
        any request reaching the port was served one, whatever `Host` it claimed. A page at
        a name that resolves to 127.0.0.1 — DNS rebinding — is same-origin to the browser,
        so it could read a page here and take the token out of it. The token is what
        authorizes every change, so handing it to a stranger is the whole game.
        """
        host = (self.headers.get("Host") or "").strip()
        if not host:
            # HTTP/1.0 clients and raw sockets send none. The token still gates every change.
            return True
        name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
        name = name.strip("[]").lower()
        if name in {"localhost", "127.0.0.1", "::1", self.state.config.service_host.lower()}:
            return True
        return _is_loopback(name)

    def _body_is_absent(self) -> bool:
        """Whether this request declared no body. A GET that declares one is refused.

        An unread body is read as the next request on a kept-alive connection, with every
        header chosen by the sender. Round 6 closed that on refusals by ending the
        connection; a GET carrying a declared body walked straight through it.
        """
        declared = self.headers.get("Content-Length")
        if self.headers.get("Transfer-Encoding"):
            return False
        if declared is None:
            return True
        try:
            return int(declared) == 0
        except ValueError:
            return False

    def _origin_is_acceptable(self) -> bool:
        """Reject a cross-origin state-changing request.

        Checked for `Origin` and `Referer` both, because a browser sends one or the other
        depending on the request. A missing header is accepted: a command-line client sends
        neither, and the token is what actually authorizes the request.
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
        if not self._host_is_acceptable():
            self._refuse(HTTPStatus.FORBIDDEN, "This service answers on the loopback name only.")
            return
        if not self._body_is_absent():
            self._refuse(HTTPStatus.BAD_REQUEST, "A GET request may not carry a body.")
            return
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
        if not self._host_is_acceptable():
            self._refuse(HTTPStatus.FORBIDDEN, "This service answers on the loopback name only.")
            return
        path = urlparse(self.path).path
        if path.startswith("/api/action/"):
            self._handle_form_action(path)
            return
        if path != "/api/action":
            self._refuse(HTTPStatus.NOT_FOUND, "There is no such endpoint.")
            return
        if not self._origin_is_acceptable():
            self._refuse(HTTPStatus.FORBIDDEN, "Cross-origin requests are refused.")
            return
        payload = self._read_json_body()
        if payload is None:
            return
        token = payload.get("token")
        if not isinstance(token, str) or not _token_matches(token, self.state.token):
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
            except OSError as exc:
                self._refuse(HTTPStatus.INTERNAL_SERVER_ERROR, _filesystem_message(exc))
            except Exception as exc:  # the last line before no response at all
                self._refuse(HTTPStatus.INTERNAL_SERVER_ERROR, _unexpected_message(exc))

    def _handle_form_action(self, path: str) -> None:
        """An ordinary HTML form submission, so the UI works with no JavaScript.

        The path carries only IDs, which are resolved against loaded content exactly as a
        JSON request's are. The token arrives as a hidden field the service itself
        substituted into the page it served.
        """
        if not self._origin_is_acceptable():
            self._refuse(HTTPStatus.FORBIDDEN, "Cross-origin requests are refused.")
            return
        parts = [segment for segment in path[len("/api/action/") :].split("/") if segment]
        if not 2 <= len(parts) <= 3:
            self._refuse(HTTPStatus.NOT_FOUND, "There is no such action.")
            return

        fields = self._read_form_body()
        if fields is None:
            return
        token = fields.get("token", [""])[0]
        if not _token_matches(token, self.state.token):
            self._refuse(
                HTTPStatus.FORBIDDEN,
                "This page was not served by the running application. Reload it and try again.",
            )
            return

        action, quest_id = parts[0], parts[1]
        if action not in MUTATING_ACTIONS:
            self._refuse(HTTPStatus.BAD_REQUEST, "That is not an action this application performs.")
            return

        payload: dict[str, Any] = {"action": action, "quest_id": quest_id}
        if len(parts) == 3:
            payload["validator_id"] = parts[2]
        try:
            payload.update(self._review_fields(fields))
        except ValueError as exc:
            # Reading the form is part of the request, so a refusal here is a refusal, not
            # an unanswered connection.
            self._redirect_back(str(exc))
            return

        payload["confirm"] = fields.get("confirm", [""])[0]
        if action in CONFIRMATIONS and not payload["confirm"]:
            # C21 is rendered as a required checkbox, which is the browser's rule and not
            # this service's. The action layer refuses it too (ADR-033); this branch exists
            # so the refusal reaches the participant as a message on the page they came
            # from rather than as a JSON error body.
            self._redirect_back(f"{CONFIRMATIONS[action]} — confirm it, then try again.")
            return

        with self.state.lock:
            try:
                result = self._perform(action, payload)
            except (StoreError, ValueError) as exc:
                self._redirect_back(str(exc))
                return
            except OSError as exc:
                # A read-only participant directory or a full disk. Without this the
                # connection closed with no status and no body, and a traceback containing
                # absolute paths went to stderr.
                self._redirect_back(_filesystem_message(exc))
                return
            except Exception as exc:  # the last line before no response at all
                # Anything else — a broken template, a malformed validator payload — used to
                # escape the handler: no status, no body, a traceback carrying absolute
                # paths on stderr, and the participant's change already on disk.
                self._redirect_back(_unexpected_message(exc))
                return
        # The one place this application reports a partial success. The form surface
        # discarded it, so a rebuild that failed after a change landed was invisible to
        # everyone not reading JSON.
        advisories = [str(item) for item in (result.get("advisories") or ())]
        self._redirect_back(None, notice=" ".join(advisories) or None)

    @staticmethod
    def _review_fields(fields: dict[str, list[str]]) -> dict[str, Any]:
        """Reviewer form fields, with empty findings dropped rather than submitted blank."""
        severities = fields.get("finding_severity", [])
        summaries = fields.get("finding_summary", [])
        evidence = fields.get("finding_evidence", [])
        findings = []
        for index, (severity, summary, observed) in enumerate(
            zip(severities, summaries, evidence, strict=False)
        ):
            if not (severity or summary or observed):
                # An untouched row of the form. Nothing was meant by it.
                continue
            if not (severity and summary and observed):
                # A half-filled one was dropped silently, and the refusal that followed said
                # "needs changes requires at least one finding" — which named the wrong
                # problem to a reviewer who had just written one. The CLI already says this.
                missing = [
                    name
                    for name, value in (
                        ("a severity", severity),
                        ("a summary", summary),
                        ("evidence", observed),
                    )
                    if not value
                ]
                raise ValueError(
                    f"Finding {index + 1} is missing {' and '.join(missing)}. "
                    "A finding a participant cannot act on is not a finding."
                )
            findings.append(
                {
                    "id": f"finding-{index + 1}",
                    "severity": severity,
                    "summary": summary,
                    "evidence": observed,
                }
            )
        extra: dict[str, Any] = {}
        if "decision" in fields:
            extra["decision"] = fields["decision"][0]
            extra["reviewer_name"] = fields.get("reviewer_name", ["Reviewer"])[0]
            extra["verification_statement"] = fields.get("verification_statement", [""])[0]
            extra["findings"] = findings
            extra["acknowledge_changed_evidence"] = bool(fields.get("acknowledge_changed_evidence"))
        return extra

    def _read_form_body(self) -> dict[str, list[str]] | None:
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if content_type != FORM_CONTENT_TYPE:
            self._refuse(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Send a form submission.")
            return None
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            self._refuse(HTTPStatus.BAD_REQUEST, "A valid Content-Length is required.")
            return None
        if not 0 < length <= MAX_BODY_BYTES:
            self._refuse(HTTPStatus.BAD_REQUEST, "The request body is empty or too large.")
            return None
        from urllib.parse import parse_qs

        return parse_qs(
            self.rfile.read(length).decode("utf-8", errors="replace"), keep_blank_values=True
        )

    def _flash_html(self, path: str) -> str:
        """The refusal message for this request, as escaped HTML, or nothing.

        Read from the `problem` query parameter the redirect set. Escaped here rather than
        trusted, because it is substituted into the page after Jinja has finished with it and
        a refusal message can quote a value the participant supplied.
        """
        from html import escape
        from urllib.parse import parse_qs, urlparse

        del path
        query = parse_qs(urlparse(self.path).query)
        message = (query.get("problem") or [""])[0].strip()
        if message:
            return (
                '<div class="alert alert-error" role="status">'
                f"<p><strong>That did not happen.</strong> {escape(message[:400])}</p>"
                "</div>"
            )
        notice = (query.get("notice") or [""])[0].strip()
        if notice:
            return (
                '<div class="alert alert-warning" role="status">'
                f"<p><strong>Recorded, with something to know.</strong> {escape(notice[:400])}</p>"
                "</div>"
            )
        return ""

    def _redirect_back(self, message: str | None, notice: str | None = None) -> None:
        """Return the browser to the page it came from, which the rebuild has refreshed.

        `message` is a refusal: nothing happened. `notice` is an advisory: the change
        happened and there is something to know about it.
        """
        target = self.headers.get("Referer") or "/"
        parsed = urlparse(target)
        location = parsed.path or "/"
        if message:
            # Rebuild before redirecting, so the page the participant lands on describes the
            # state as it actually is. Without this a refused evidence-ready still showed the
            # previous build's "no secrets found" panel beside the refusal.
            with contextlib.suppress(StoreError, OSError):
                build_site(self._load(), service=online_service_view())
        if message:
            from urllib.parse import quote

            location = f"{location}?problem={quote(message[:300])}"
        elif notice:
            from urllib.parse import quote

            location = f"{location}?notice={quote(notice[:300])}"
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self._security_headers()
        self.end_headers()

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
        """Delegate to the shared runner, so HTTP is one caller of the action layer."""
        return ActionRunner(self.state.config, self.state.schemas, self._load).perform(
            action, payload
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
            # The actions this service performs, and the two paths it answers a GET on.
            # `READ_ACTIONS` was reported here as though `actions` were an endpoint of its
            # own, which it has never been.
            "actions": sorted(MUTATING_ACTIONS),
            "read_endpoints": ["/api/git-status", "/api/health"],
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
        if content_type == "text/html":
            # Substituted as the page is served, so the token reaches a form without ever
            # being written to a file.
            body = body.replace(TOKEN_PLACEHOLDER.encode(), self.state.token.encode())
            body = body.replace(FLASH_PLACEHOLDER.encode(), self._flash_html(path).encode())
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
    build_site(world, service=online_service_view())

    try:
        server, _ = create_server(config)
    except UnsafeBindError as exc:
        print(f"refusing to start: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        # `serve --port` exists so two people can run two services, and typing a port that
        # is already taken printed a socketserver traceback.
        reason = exc.strerror or type(exc).__name__
        print(
            f"cannot listen on {config.service_host}:{config.service_port}: {reason}. "
            "Choose another port with --port.",
            file=sys.stderr,
        )
        return 2

    bound = int(server.server_address[1])
    port_file = config.local_data_root / PORTS_DIRNAME / str(bound)
    try:
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(f"{bound}\n", encoding="utf-8")
    except OSError:
        # A CLI action in a second terminal will then assume the default port. Worth a
        # degraded probe, never worth refusing to serve.
        port_file = None  # type: ignore[assignment]

    address = f"http://{config.service_host}:{bound}/"
    print(f"Golden Thread Quest is at {address}", file=sys.stderr)
    # Deliberately not printed. The pages this run serves already carry it, substituted as
    # they are served, so nobody needs to read it — and printing it put it into any log a
    # participant redirected the service into, which is the one place it could reach disk.
    print(
        "Pages served by this run carry a request token; it is not printed or stored.",
        file=sys.stderr,
    )
    print("Stop with Ctrl-C.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
    finally:
        server.server_close()
        if port_file is not None:
            with contextlib.suppress(OSError):
                port_file.unlink(missing_ok=True)
    return 0


def _filesystem_message(error: OSError) -> str:
    """Both surfaces say the same thing; the words live in `quest_app.errors`."""
    return filesystem_message(error)


def describe_actions(current: Any) -> list[dict[str, str]]:
    return [
        {"action": transition.action, "description": transition.description}
        for transition in allowed_actions(current)
    ]
