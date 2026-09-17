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

from quest_app.config import APPLICATION_VERSION, AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import LoadedWorld, load_world

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
        if not args.json:
            _summarize(report, world)
            print(
                "nothing was generated; the previous output, if any, is untouched",
                file=sys.stderr,
            )
        return EXIT_CONTENT_ERROR
    result = build_site(world)
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
    for note in (*warnings, *result.notes):
        print(f"[note] {note}")

    if result.safe_to_proceed:
        print("\nRun these yourself. This command never merges anything:\n")
        print(result.instructions)
        return EXIT_OK
    print("\nNot safe to update yet. Fix the items above first.", file=sys.stderr)
    return EXIT_CONTENT_ERROR


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

    update = subparsers.add_parser(
        "update", help="Check whether it is safe to take upstream curriculum changes"
    )
    _common_arguments(update)
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
