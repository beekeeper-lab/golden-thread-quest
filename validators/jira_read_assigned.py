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
    loaded = _load_participant_output(workspace, output)
    if loaded is None:
        return
    document, produced = loaded

    _check_all_items_present(expected, produced, output)
    _check_normalized_fields(produced, output)
    _check_traceability(produced, output)
    _check_no_duplicates(produced, output)
    _check_disappearances_reported(expected, document, produced, output)
    _check_comments_not_duplicated(expected, produced, output)
    _check_raw_responses_not_committed(workspace, output)


def _load_participant_output(
    workspace: Workspace, output: ValidatorOutput
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """The participant's synchronized output: the whole document, and its story records.

    The document matters as well as the list, because a story that disappeared between runs
    is reported outside the list of stories that are still assigned.
    """
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
    records = [item for item in items if isinstance(item, dict)]
    return (data if isinstance(data, dict) else {}), records


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
                summary="Every record carries the fields this check requires.",
                evidence=(
                    f"{len(produced)} record(s) carry {', '.join(REQUIRED_FIELDS)}. The "
                    "optional fields criterion 4 names are for the reviewer to judge."
                ),
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


REMOVAL_FIELDS = ("removed", "reported_removed", "no_longer_assigned", "disappeared")
"""Top-level lists in which a participant may report the items that went away."""

REMOVAL_FLAGS = ("removed", "unassigned", "disappeared", "no_longer_assigned", "gone")
REMOVAL_WORDS = (
    "removed",
    "unassigned",
    "no longer assigned",
    "not assigned",
    "gone",
    "deleted",
    "inaccessible",
)


def _says_no_longer_assigned(record: dict[str, Any] | None) -> bool:
    """Whether a record kept in the list says the item is no longer assigned.

    Criterion 8 is about reporting a disappearance, not about the record surviving. Keeping
    the story in the list exactly as it was is what a synchronization that never noticed
    produces, so presence alone cannot be the evidence that it was noticed.
    """
    if not record:
        return False
    for key in ("assigned", "still_assigned", "is_assigned", "active"):
        value = record.get(key)
        if isinstance(value, bool) and not value:
            return True
    for key in REMOVAL_FLAGS:
        value = record.get(key)
        if value not in (None, False, "", [], {}):
            return True
    for key in ("status", "state", "sync_status", "assignment", "note", "notes"):
        value = record.get(key)
        if isinstance(value, str) and any(word in value.lower() for word in REMOVAL_WORDS):
            return True
    return False


def _check_disappearances_reported(
    expected: dict[str, Any],
    document: dict[str, Any],
    produced: list[dict[str, Any]],
    output: ValidatorOutput,
) -> None:
    """Criterion 8: an item that was assigned before and is gone now is reported, not dropped.

    Only the fixtures that carry `previously_assigned` exercise this. Until round 7 the
    `stale-item` fixture described a reassigned story and contained no trace of one, so a
    participant who chose it to demonstrate this behaviour demonstrated nothing: the only
    check that ran asked whether the two remaining stories were present.
    """
    gone = [str(item["key"]) for item in expected.get("previously_assigned", [])]
    if not gone:
        return

    reported_elsewhere = {
        str(entry.get("key") if isinstance(entry, dict) else entry)
        for field in REMOVAL_FIELDS
        for entry in (document.get(field) or [])
    }
    kept = {str(item.get("key")): item for item in produced}
    unreported = sorted(
        key
        for key in gone
        if key not in reported_elsewhere and not _says_no_longer_assigned(kept.get(key))
    )

    if unreported:
        output.add(
            Check(
                id="disappearances-reported",
                outcome="fail",
                severity="high",
                summary="A story that was assigned on the previous run vanished without a word.",
                evidence=f"not reported: {', '.join(unreported[:8])}",
                suggested_action=(
                    "Keep the record with its last known state and say it is no longer assigned: "
                    "mark the record itself (`assigned: false`, a removal timestamp, or a status "
                    f"naming it removed), or list it under one of {', '.join(REMOVAL_FIELDS)}. "
                    "Deleting it silently is how a thread goes cold."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="disappearances-reported",
                outcome="pass",
                summary="Every story that disappeared between runs is still reported.",
                evidence=f"{len(gone)} disappearance(s) accounted for.",
            )
        )


def _check_comments_not_duplicated(
    expected: dict[str, Any], produced: list[dict[str, Any]], output: ValidatorOutput
) -> None:
    """Criterion 7: a comment delivered twice is recorded once.

    Only the fixtures whose stories carry comments exercise this. The `duplicate-comment`
    fixture named the behaviour in its description and carried no comment at all, and the
    only duplicate check in this validator reconciles stories by key, which cannot see a
    comment at all.
    """
    if not any(story.get("comments") for story in expected.get("stories", [])):
        return

    offenders: list[str] = []
    counted = 0
    for item in produced:
        comments = item.get("comments")
        if not isinstance(comments, list):
            continue
        seen: dict[str, int] = {}
        for comment in comments:
            identifier = str(comment.get("id") if isinstance(comment, dict) else comment)
            seen[identifier] = seen.get(identifier, 0) + 1
            counted += 1
        repeated = sorted(identifier for identifier, count in seen.items() if count > 1)
        if repeated:
            offenders.append(f"{item.get('key')}: {', '.join(repeated[:3])}")

    if offenders:
        output.add(
            Check(
                id="no-duplicate-comments",
                outcome="fail",
                severity="medium",
                summary="The same comment is recorded more than once.",
                evidence="; ".join(offenders[:5]),
                suggested_action=(
                    "Reconcile comments by their own identifier. Appending what each page "
                    "returns duplicates whatever both pages return."
                ),
            )
        )
    elif counted:
        output.add(
            Check(
                id="no-duplicate-comments",
                outcome="pass",
                summary="Each comment is recorded exactly once.",
                evidence=f"{counted} comment(s) checked by identifier.",
            )
        )
    else:
        output.add(
            Check(
                id="no-duplicate-comments",
                outcome="inconclusive",
                summary="No comments were recorded, so duplication could not be judged.",
                evidence="This fixture delivers the same comment on two pages.",
                suggested_action="Record each story's comments, then run this again.",
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
