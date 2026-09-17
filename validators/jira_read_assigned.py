"""Checks a Jira synchronization against a local fixture, never a live connection.

Running against real Jira would make the check depend on someone else's data and would put
a credential inside a validator. The registry gives this one a fixture set instead, chosen
from an allowlist, so the same participant work can be evaluated against a happy path,
pagination, a stale item and a duplicated comment.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace

from quest_app.validator_runner import Check

REQUIRED_FIELDS = ("key", "source_url", "status", "summary", "retrieved_at")


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    fixture_set = workspace.parameters.get("fixture_set", "happy-path")
    fixture_path = f"validators/fixtures/jira/{fixture_set}.json"
    if not workspace.exists(fixture_path):
        output.fail_environment(f"the {fixture_set!r} fixture is not installed")
        return

    expected = json.loads(workspace.read_text(fixture_path))
    produced = _load_participant_output(workspace, output)
    if produced is None:
        return

    _check_all_items_present(expected, produced, output)
    _check_normalized_fields(produced, output)
    _check_traceability(produced, output)
    _check_no_duplicates(produced, output)
    _check_raw_responses_not_committed(workspace, output)


def _load_participant_output(
    workspace: Workspace, output: ValidatorOutput
) -> list[dict[str, Any]] | None:
    candidates = workspace.iter_files("participant/context/jira", "*.json")
    if not candidates:
        output.add(
            Check(
                id="synchronized-output-exists",
                outcome="inconclusive",
                summary="No synchronized output was found to evaluate.",
                evidence="participant/context/jira contains no JSON.",
                suggested_action="Write the normalized stories there, then run this again.",
            )
        )
        return None
    try:
        data = json.loads(workspace.read_text(str(candidates[0])))
    except json.JSONDecodeError as exc:
        output.add(
            Check(
                id="synchronized-output-parses",
                outcome="fail",
                severity="high",
                summary="The synchronized output is not valid JSON.",
                evidence=f"line {exc.lineno}: {exc.msg}",
                artifact=workspace.relative(candidates[0]),
            )
        )
        return None
    items = data.get("stories") if isinstance(data, dict) else data
    if not isinstance(items, list):
        output.add(
            Check(
                id="synchronized-output-parses",
                outcome="fail",
                severity="high",
                summary="The synchronized output is not a list of stories.",
                evidence=f"found {type(items).__name__}",
            )
        )
        return None
    return [item for item in items if isinstance(item, dict)]


def _check_all_items_present(
    expected: dict[str, Any], produced: list[dict[str, Any]], output: ValidatorOutput
) -> None:
    expected_keys = {item["key"] for item in expected["stories"]}
    produced_keys = {item.get("key") for item in produced}
    missing = sorted(expected_keys - produced_keys)
    if missing:
        output.add(
            Check(
                id="pagination-handled",
                outcome="fail",
                severity="high",
                summary="Some assigned stories are missing from the output.",
                evidence=f"missing: {', '.join(missing[:8])}",
                suggested_action="Keep requesting pages until the source reports no more results.",
            )
        )
    else:
        output.add(
            Check(
                id="pagination-handled",
                outcome="pass",
                summary="Every assigned story in the fixture appears in the output.",
                evidence=f"{len(expected_keys)} story/stories accounted for.",
            )
        )


def _check_normalized_fields(produced: list[dict[str, Any]], output: ValidatorOutput) -> None:
    incomplete = [
        item.get("key", "<no key>")
        for item in produced
        if any(field not in item for field in REQUIRED_FIELDS)
    ]
    if incomplete:
        output.add(
            Check(
                id="records-are-normalized",
                outcome="fail",
                severity="medium",
                summary="Some records are missing normalized fields.",
                evidence=f"incomplete: {', '.join(map(str, incomplete[:8]))}",
                suggested_action=f"Every record needs: {', '.join(REQUIRED_FIELDS)}.",
            )
        )
    else:
        output.add(
            Check(
                id="records-are-normalized",
                outcome="pass",
                summary="Every record carries the normalized fields.",
                evidence=f"{len(produced)} record(s) checked.",
            )
        )


def _check_traceability(produced: list[dict[str, Any]], output: ValidatorOutput) -> None:
    untraceable = [
        item.get("key", "<no key>")
        for item in produced
        if not str(item.get("source_url", "")).startswith(("http://", "https://"))
    ]
    if untraceable:
        output.add(
            Check(
                id="records-trace-to-source",
                outcome="fail",
                severity="high",
                summary="Some records cannot be traced back to their source.",
                evidence=f"no usable source_url: {', '.join(map(str, untraceable[:8]))}",
                suggested_action=(
                    "The whole point of the thread is that a reader can get back to the original."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="records-trace-to-source",
                outcome="pass",
                summary="Every record links back to its source.",
                evidence="source_url present and absolute on every record.",
            )
        )


def _check_no_duplicates(produced: list[dict[str, Any]], output: ValidatorOutput) -> None:
    seen: dict[str, int] = {}
    for item in produced:
        key = str(item.get("key"))
        seen[key] = seen.get(key, 0) + 1
    duplicates = sorted(key for key, count in seen.items() if count > 1)
    if duplicates:
        output.add(
            Check(
                id="no-duplicate-records",
                outcome="fail",
                severity="medium",
                summary="The same story appears more than once.",
                evidence=f"duplicated: {', '.join(duplicates[:8])}",
                suggested_action="Reconcile by stable key so a re-run updates rather than appends.",
            )
        )
    else:
        output.add(
            Check(
                id="no-duplicate-records",
                outcome="pass",
                summary="Each story appears exactly once.",
                evidence="Re-running should update in place rather than append.",
            )
        )


def _check_raw_responses_not_committed(workspace: Workspace, output: ValidatorOutput) -> None:
    raw = [
        path
        for path in workspace.iter_files("participant/context/jira", "*.json")
        if "raw" in path.name.lower() or "response" in path.name.lower()
    ]
    if raw:
        output.add(
            Check(
                id="raw-responses-not-committed",
                outcome="warning",
                severity="medium",
                summary="Something that looks like a raw API response is in committed context.",
                evidence=", ".join(workspace.relative(path) for path in raw[:5]),
                suggested_action="Raw responses belong in the gitignored local-data directory.",
            )
        )
    else:
        output.add(
            Check(
                id="raw-responses-not-committed",
                outcome="pass",
                summary="No raw API response is in committed context.",
                evidence="Only normalized records were found.",
            )
        )
