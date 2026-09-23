"""Command line entry points.

Each command is a thin shell over the same pipeline, and every one of them prints problems
in the same shape, because an author who learns to read one error message has learned to
read all of them.

`build` and `serve` are registered by their own stages — the generator and the local action
service — so the command list always describes what actually exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from quest_app.actions import CONFIRMATIONS, MUTATING_ACTIONS, ActionRunner
from quest_app.config import APPLICATION_VERSION, AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport, filesystem_message
from quest_app.models import Decision
from quest_app.pipeline import LoadedWorld, load_world
from quest_app.store import StoreError
from quest_app.view_models import offline_service_view, online_service_view

EXIT_OK = 0
EXIT_CONTENT_ERROR = 1
EXIT_USAGE = 2


def _config_from_args(args: argparse.Namespace) -> AppConfig:
    repo_root = Path(args.repo_root).resolve() if args.repo_root else None
    config = AppConfig.from_environment(repo_root)
    if args.participant_root:
        config = AppConfig.for_repo(
            config.repo_root,
            participant_root=Path(args.participant_root),
            service_host=config.service_host,
            service_port=config.service_port,
        )
    return config


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo-root", help="Repository root (default: the installed package's repository)"
    )
    parser.add_argument(
        "--participant-root",
        help="Where participant-owned files live (default: <repo>/participant)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")


def _report_problems(report: ProblemReport, as_json: bool) -> None:
    """Warnings go to stdout, errors to stderr, so a pipeline can separate them."""
    if as_json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return
    for problem in report.sorted_problems():
        stream = sys.stderr if problem.severity.stops_the_build else sys.stdout
        print(problem.to_text(), file=stream)


def _summarize(report: ProblemReport, world: LoadedWorld | None) -> None:
    errors, warnings = len(report.errors), len(report.warnings)
    if world is not None:
        content = world.content
        print(
            f"validated {len(content.quests)} quest(s), {len(content.regions)} region(s), "
            f"{len(content.badges)} badge(s), {len(content.tracks)} track(s)"
            f" — {warnings} warning(s)",
            file=sys.stderr,
        )
    else:
        print(
            f"content is not publishable: {errors} error(s), {warnings} warning(s)", file=sys.stderr
        )


def validate_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    report = ProblemReport()
    world = load_world(config, report)
    _report_problems(report, args.json)
    if not args.json:
        _summarize(report, world)
    return EXIT_OK if world is not None else EXIT_CONTENT_ERROR


def build_command(args: argparse.Namespace) -> int:
    """Generate the site, or refuse and leave the last good one in place."""
    from quest_app.build import build_site

    config = _config_from_args(args)
    report = ProblemReport()
    world = load_world(config, report)
    _report_problems(report, args.json)
    if world is None:
        from quest_app.build import render_error_page

        page = render_error_page(config, report)
        if not args.json:
            _summarize(report, world)
            print(
                "nothing was generated; the previous output, if any, is untouched",
                file=sys.stderr,
            )
            print(f"the same errors as a page: {config.relative(page)}", file=sys.stderr)
        return EXIT_CONTENT_ERROR
    # `make build` while a service is running had the same effect as an action did: the
    # served pages were replaced with copies saying nothing could change state.
    from quest_app.serve import is_service_running

    result = build_site(
        world, service=online_service_view() if is_service_running(config) else None
    )
    if not args.json:
        print(
            f"built {result.page_count} page(s) into {config.relative(config.generated_root)}",
            file=sys.stderr,
        )
        _summarize(report, world)
    return EXIT_OK


def serve_command(args: argparse.Namespace) -> int:
    from quest_app.serve import run_service

    return run_service(_config_from_args(args), host=args.host, port=args.port)


def update_command(args: argparse.Namespace) -> int:
    """Report whether an update is safe, and print the commands. It runs no merge."""
    from quest_app.update import migration_report, preflight

    config = _config_from_args(args)
    if args.migrate:
        from quest_app.update import apply_migrations

        applied, problems = apply_migrations(config)
        for problem in problems:
            print(problem, file=sys.stderr)
        for step in applied:
            print(f"[migrated] {step}")
        if not applied and not problems:
            print("Your progress file is already on the current schema.")
        return EXIT_CONTENT_ERROR if problems else EXIT_OK

    result = preflight(config)
    steps, warnings = migration_report(config)

    if args.json:
        print(
            json.dumps(
                {
                    "safe_to_proceed": result.safe_to_proceed,
                    "findings": [
                        {
                            "id": finding.id,
                            "status": finding.status,
                            "summary": finding.summary,
                            "remediation": finding.remediation,
                        }
                        for finding in result.findings
                    ],
                    "migration_steps": steps,
                    "warnings": [*warnings, *result.notes],
                    "instructions": result.instructions,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return EXIT_OK if result.safe_to_proceed else EXIT_CONTENT_ERROR

    for finding in result.findings:
        print(f"[{finding.status}] {finding.summary}")
        if finding.remediation:
            print(f"    fix: {finding.remediation}")
    for step in steps:
        print(f"[migration] {step}")
    if steps:
        print("    apply: make migrate   (after the merge, with your work committed)")
    for note in (*warnings, *result.notes):
        print(f"[note] {note}")

    if result.safe_to_proceed:
        print("\nRun these yourself. This command never merges anything:\n")
        print(result.instructions)
        return EXIT_OK
    print("\nNot safe to update yet. Fix the items above first.", file=sys.stderr)
    return EXIT_CONTENT_ERROR


def action_command(args: argparse.Namespace) -> int:
    """Perform one quest action without a browser.

    The browser is not available everywhere a participant works. An agent sandbox, a
    remote shell and CI all have a filesystem and no way to reach a loopback server, and
    on those surfaces this is the only path to changing state. It runs the same
    `ActionRunner` the HTTP service runs, so every guard applies identically: the secret
    scan still blocks marking evidence ready, a validation run is still not a transition,
    and nothing here can produce verified completion.
    """
    if args.list:
        for name in sorted(MUTATING_ACTIONS):
            print(name)
        return EXIT_OK

    if not args.name:
        print("Name an action, or pass --list to see them.", file=sys.stderr)
        return EXIT_CONTENT_ERROR
    if args.name not in MUTATING_ACTIONS:
        print(f"{args.name!r} is not an action this application performs.", file=sys.stderr)
        print("Run with --list to see them.", file=sys.stderr)
        return EXIT_CONTENT_ERROR
    if args.name != "rebuild" and not args.quest:
        print(f"{args.name} needs --quest.", file=sys.stderr)
        return EXIT_CONTENT_ERROR

    config = _config_from_args(args)

    def load() -> LoadedWorld:
        report = ProblemReport()
        world = load_world(config, report)
        if world is None:
            _report_problems(report, as_json=False)
            raise ValueError("Content did not validate, so nothing was changed.")
        return world

    payload: dict[str, object] = {
        "action": args.name,
        "quest_id": args.quest,
        # The same confirmation the browser form carries. `ActionRunner` refuses the
        # actions that need one, so this surface cannot be the quiet way around the gate.
        "confirm": bool(args.confirm),
    }
    if args.validator:
        payload["validator_id"] = args.validator
    if args.decision:
        payload["decision"] = args.decision
        payload["reviewer_name"] = args.reviewer
        payload["verification_statement"] = args.statement or ""
        payload["acknowledge_changed_evidence"] = args.acknowledge_changed_evidence
        # A malformed finding used to be dropped in silence, which left a reviewer holding
        # a refusal that named the wrong problem: "requires at least one finding" when they
        # had typed one, mis-shaped.
        malformed = [part for part in args.finding if part.count(":") < 2]
        if malformed:
            print(
                f"--finding needs severity:summary:evidence; {malformed[0]!r} has too few fields.",
                file=sys.stderr,
            )
            return EXIT_USAGE
        payload["findings"] = [
            {
                "id": f"finding-{index + 1}",
                "severity": severity,
                "summary": summary,
                "evidence": evidence,
            }
            for index, (severity, summary, evidence) in enumerate(
                part.split(":", 2) for part in args.finding
            )
        ]

    # An action rebuilds the site, and the page it writes says whether state can be changed
    # from it. Assuming "offline" here meant one CLI action from a second terminal disabled
    # every control on the pages a running service was serving, with no way back but a
    # restart. Ask, rather than assume.
    from quest_app.serve import is_service_running

    service_view = online_service_view if is_service_running(config) else offline_service_view
    runner = ActionRunner(config, SchemaSet(config.schemas_root), load, service=service_view)
    try:
        result = runner.perform(args.name, payload)
    except (StoreError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_CONTENT_ERROR
    except OSError as exc:
        # The service has said this since it was written. The CLI said it with a traceback
        # and an absolute path until round 5, which is the surface Cowork participants use.
        print(filesystem_message(exc), file=sys.stderr)
        return EXIT_CONTENT_ERROR
    except Exception as exc:  # the CLI is a surface, not a stack trace
        # Both write paths in the service answer every failure. This one answered three
        # kinds and let the rest out as a traceback with absolute paths in it.
        print(f"{args.name} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_CONTENT_ERROR

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        state = result.get("state")
        print(f"{args.name}: ok" + (f" — now {state}" if state else ""))
        for advisory in result.get("advisories") or ():
            # Printed, not raised: it did not stop the submission and must not read as if
            # it had. Saying nothing is what left the participant to hear it from a reviewer.
            print(f"advisory: {advisory}")
        if result.get("next"):
            print(f"next: {result['next']}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quest", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=APPLICATION_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate content and participant state")
    _common_arguments(validate)
    validate.set_defaults(func=validate_command)

    build = subparsers.add_parser("build", help="Generate the site into generated/")
    _common_arguments(build)
    build.set_defaults(func=build_command)

    serve = subparsers.add_parser("serve", help="Build, then run the loopback action service")
    _common_arguments(serve)
    serve.add_argument("--host", default=None, help="Bind address (loopback only)")
    serve.add_argument("--port", type=int, default=None)
    serve.set_defaults(func=serve_command)

    action = subparsers.add_parser(
        "action", help="Perform a quest action without a browser (Cowork, SSH, CI)"
    )
    _common_arguments(action)
    action.add_argument("name", nargs="?", help="Action to perform; --list shows them all")
    action.add_argument("--list", action="store_true", help="List the actions and exit")
    action.add_argument("--quest", help="Quest ID the action applies to")
    action.add_argument("--validator", help="Validator ID, for run-validator")
    action.add_argument(
        "--decision",
        choices=[member.value for member in Decision],
        help="For record-review; the same three values the browser form posts",
    )
    action.add_argument("--reviewer", default="Reviewer", help="Reviewer name, for record-review")
    action.add_argument("--statement", help="Verification statement, required to approve")
    action.add_argument(
        "--finding",
        action="append",
        default=[],
        help="severity:summary:evidence — repeatable; at least one to request changes",
    )
    action.add_argument(
        "--acknowledge-changed-evidence",
        action="store_true",
        help="Approve although the evidence changed after submission; the browser form has "
        "the same checkbox and approval is refused without it",
    )
    action.add_argument(
        "--confirm",
        action="store_true",
        help="Say you mean it. Required for the actions the browser form confirms: "
        + ", ".join(sorted(CONFIRMATIONS)),
    )
    action.set_defaults(func=action_command)

    update = subparsers.add_parser(
        "update", help="Check whether it is safe to take upstream curriculum changes"
    )
    _common_arguments(update)
    update.add_argument(
        "--migrate",
        action="store_true",
        help="Move participant/progress.yaml to the current schema, validating before and after",
    )
    update.set_defaults(func=update_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result: int = args.func(args)
    return result


def validate_main() -> int:
    return main(["validate", *sys.argv[1:]])


def build_main() -> int:
    return main(["build", *sys.argv[1:]])


def serve_main() -> int:
    return main(["serve", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
