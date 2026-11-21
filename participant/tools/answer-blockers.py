#!/usr/bin/env python3
"""Answers "What is blocking the release?" from saved notes, and says how old they are.

Part of the context-staleness quest. The rules are in participant/context/freshness/policy.md:
  - a note's age is the clock time minus the note's retrieval time;
  - up to its source's limit it is fresh; past the limit, up to twice the limit, it is stale;
    past twice the limit it is too old;
  - a note that can't be trusted is too old: no usable retrieval time, retrieved after the clock,
    a source not in the policy, or a required fact missing or in the wrong form;
  - a notes file that is malformed, repeats a key or a note id, or sets its own limits is refused;
  - the answer takes the worst status of any note: too old -> refuse, stale -> warn.
Every answer shows the clock used and the oldest note with its age, and a warned or refused
answer names each stale or too-old note and which notes to refresh.

The clock is never read from the computer: it must be given with --now, so the same notes and
the same clock always produce the same answer. Read-only: it writes nothing.

    .venv/bin/python participant/tools/answer-blockers.py \\
        --context participant/context/freshness/tixly-context.yaml --now "2026-10-21T15:00:00-04:00"
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

VERSION = "1.11.0"
RANK = {"fresh": 0, "stale": 1, "too old": 2}

# The freshness limits, in days, exactly as in policy.md section 1. They live here, not in the notes
# file, so whoever writes the notes can't loosen the policy. A source not listed is not trusted.
POLICY_LIMITS = {"sprint-board": 1, "bug-list": 1, "test-runs": 1, "release-plan": 7, "team-roster": 30}

# The values a note may hold, matched ignoring capitals and surrounding spaces. Anything else is not
# recognised, so the note can't be trusted -- an unknown status must never count as "not blocking".
ALLOWED = {
    ("sprint-board", "status"): ("To Do", "In Progress", "In Review", "Done"),
    ("bug-list", "status"): ("Open", "In Progress", "Fixed", "Closed"),
    ("bug-list", "severity"): ("Critical", "High", "Medium", "Low"),
}


def canonical(source: str, field: str, value: object) -> str | None:
    """The allowed spelling of value, or None if it isn't one of the allowed values."""
    if not isinstance(value, str):
        return None
    wanted = " ".join(value.split()).casefold()
    return next((v for v in ALLOWED[(source, field)] if v.casefold() == wanted), None)


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def _date(v):
    """A calendar date written as text, YYYY-MM-DD (like times, never a pre-read date object)."""
    if not (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v.strip())):
        return False
    try:
        dt.date.fromisoformat(v.strip())
        return True
    except ValueError:
        return False


# The facts each source's notes must hold. A note missing one, or holding the wrong kind of value,
# can't be relied on, so it is treated as too old (policy section 3) instead of being filled in.
REQUIRED = {
    "sprint-board": {"title": _text, "status": _text},
    "bug-list": {"title": _text, "status": _text, "severity": _text},
    # At least one test must have run: a run of 0 tests is not a pass, it's no result.
    "test-runs": {"build": lambda v: _text(v) or _count(v), "failed": _count, "total": lambda v: _count(v) and v >= 1},
    # The release name is text, as in "3.0" (quoted, so YAML doesn't read it as a number).
    "release-plan": {"release": _text, "target_date": _date},
    "team-roster": {"qa": lambda v: isinstance(v, list) and bool(v) and all(_text(x) for x in v)},
}


def problems(note: dict) -> list[str]:
    """The facts this note is missing or holds in the wrong form."""
    bad = [field for field, ok in REQUIRED.get(note["source"], {}).items() if not ok(note.get(field))]
    if note["source"] == "test-runs" and "total" in bad and note.get("total") == 0:
        bad[bad.index("total")] = "total (no tests ran)"
    bad += [f"{field} ({note.get(field)!r} is not one of: {', '.join(ALLOWED[(src, field)])})"
            for (src, field) in ALLOWED
            if src == note["source"] and field not in bad and canonical(src, field, note.get(field)) is None]
    if note["source"] == "test-runs" and not bad and note["failed"] > note["total"]:
        bad.append("failed (more than total)")
    return bad


class StrictLoader(yaml.SafeLoader):
    """yaml's safe loader, but a key repeated in the same place is an error, not silently replaced.

    Plain YAML keeps the last of two `notes:` lists, so a first list holding stale or undated notes
    would vanish and the answer could look all fresh.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError:
                raise yaml.constructor.ConstructorError(
                    None, None, "a key must be plain text, not a list or table", key_node.start_mark) from None
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"the key '{key}' appears twice", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


# YAML would otherwise read an unquoted time itself, and quietly "correct" an impossible one
# (-04:60 becomes -05:00). With its time reading switched off, every time reaches the program as
# text and gets the same strict check, quoted or not.
StrictLoader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
# ...and an explicit "!!timestamp" label is read as plain text too, so it can't route around the check.
StrictLoader.add_constructor("tag:yaml.org,2002:timestamp", yaml.SafeLoader.construct_yaml_str)

# A date and time with a time zone: YYYY-MM-DDTHH:MM[:SS[.ffffff]] then Z or +HH:MM / -HH:MM,
# the zone's hours 00-23 and minutes 00-59. The date and time ranges are checked by Python.
TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)"
)


def load_context(path: Path) -> dict:
    """The notes file, or an error message saying why it can't be used."""
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=StrictLoader)  # noqa: S506 -- a SafeLoader subclass
    except (OSError, UnicodeDecodeError) as e:
        raise ValueError(f"{path} can't be read: {e}") from None
    except yaml.YAMLError as e:
        raise ValueError(f"{path} is not valid: {e}".replace("\n", " ")) from None
    if not isinstance(data, dict) or not _text(data.get("question")):
        raise ValueError(f"{path} must have a 'question' to answer")
    if not isinstance(data.get("notes"), list):
        raise ValueError(f"{path} must have a 'notes' list")
    if "limits_days" in data and data["limits_days"] != POLICY_LIMITS:
        raise ValueError(f"{path} sets its own freshness limits; the limits come only from the policy ({POLICY_LIMITS})")
    if not data["notes"]:
        raise ValueError(f"{path} has no notes, so there is nothing to answer from")
    for n in data["notes"]:
        if not (isinstance(n, dict) and isinstance(n.get("id"), str) and n["id"].strip()
                and isinstance(n.get("source"), str) and n["source"].strip()):
            raise ValueError(f"{path}: every note needs an 'id' and a 'source' written as text (found {n!r})")
    ids = [n["id"].strip() for n in data["notes"]]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"{path}: more than one note has the id {', '.join(repeated)}, so the notes contradict or repeat each other")
    # Allowed values are stored in their standard spelling, so "open" and "Open " both count as Open.
    data["notes"] = [
        {**n, **{field: canonical(src, field, n.get(field)) or n.get(field)
                 for (src, field) in ALLOWED if src == n["source"]}}
        for n in data["notes"]
    ]
    return data


def parse_time(value: object) -> dt.datetime | None:
    """A time with its time zone, or None if it is missing, malformed or has no time zone.

    Times arrive as text whether quoted or not (YAML's own time reading is switched off, see
    StrictLoader) and must match TIMESTAMP exactly before Python reads them.
    """
    # Only text is accepted. A time already turned into a date-time by something else could have had
    # an impossible part quietly "corrected" on the way, so it is never trusted.
    if isinstance(value, str):
        text = value.strip()
        if not TIMESTAMP.fullmatch(text):
            return None
        # A trailing "Z" means UTC. Older Pythons (3.10, the project's minimum) can't read it, so
        # it is written out as +00:00 first and every version reads the same time.
        if text[-1:] in ("Z", "z"):
            text = text[:-1] + "+00:00"
        try:
            t = dt.datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    return t if t.tzinfo else None  # without a time zone the age would be a guess


def shown(t: dt.datetime) -> str:
    """MM-DD-YYYY, 12-hour time."""
    return t.strftime("%m-%d-%Y %I:%M %p").replace(" 0", " ", 1) + t.strftime(" (UTC%z)")


def age_text(delta: dt.timedelta) -> str:
    """Days, hours, minutes and seconds (with any fraction), so the age shown is the exact age the
    status uses: a note 1 day and 1 second old never shows as "1 day"."""
    days, rest = delta.days, dt.timedelta(seconds=delta.seconds, microseconds=delta.microseconds)
    hours, rest = divmod(rest, dt.timedelta(hours=1))
    minutes, rest = divmod(rest, dt.timedelta(minutes=1))
    seconds = rest.total_seconds()
    parts = []
    for n, unit in ((days, "day"), (hours, "hour"), (minutes, "minute")):
        if n:
            parts.append(f"{n} {unit}{'s' if n != 1 else ''}")
    if seconds or not parts:
        shown_s = f"{seconds:.6f}".rstrip("0").rstrip(".")
        parts.append(f"{shown_s} second{'s' if shown_s != '1' else ''}")
    return " ".join(parts)


def assess(note: dict, limits: dict, now: dt.datetime) -> dict:
    """The note's age and status under the policy."""
    limit = limits.get(note.get("source"))
    retrieved = parse_time(note.get("retrieved_at"))
    # Every reason the note can't be trusted is collected, so none is hidden behind another.
    reasons, age_problem = [], ""
    if retrieved is None:
        age_problem = "no usable retrieval time: missing, unreadable, or without a time zone"
    elif retrieved > now:
        age_problem = "retrieved after the clock time, so the clock or the note is wrong"
    if age_problem:
        reasons.append(age_problem)
    if limit is None:
        reasons.append(f"'{note.get('source')}' is not a source in the policy, so it has no freshness limit")
    else:
        bad = problems(note)
        if bad:
            reasons.append("missing or invalid: " + ", ".join(bad))
    age = now - retrieved if not age_problem else None
    if reasons:
        return {"note": note, "age": age, "limit": limit, "status": "too old",
                "why": "; ".join(reasons), "age_problem": age_problem}
    limit_td = dt.timedelta(days=limit)
    status = "fresh" if age <= limit_td else "stale" if age <= 2 * limit_td else "too old"
    return {"note": note, "age": age, "limit": limit, "status": status, "why": "", "age_problem": ""}


def blockers(notes: list[dict]) -> list[str]:
    """What the notes say is blocking the release."""
    found = []
    for n in notes:
        src = n.get("source")
        if src == "sprint-board" and n.get("status") != "Done":
            found.append(f"{n['id']} {n.get('title')} is still {n.get('status')}")
        # An unresolved bug blocks whether or not anyone has started on it: Open and In Progress both count.
        elif src == "bug-list" and n.get("status") in ("Open", "In Progress") and n.get("severity") in ("Critical", "High"):
            found.append(f"{n['id']} {n.get('title')} is {n.get('status').lower()} ({n.get('severity')})")
        elif src == "test-runs" and n.get("failed", 0) > 0:
            found.append(f"{n['id']} build {n.get('build')}: {n.get('failed')} of {n.get('total')} tests failed")
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Answer what is blocking the release, with the age of every note used.")
    ap.add_argument("--context", required=True, type=Path, help="the saved notes (YAML)")
    ap.add_argument("--now", required=True, help='the clock, with its time zone, e.g. "2026-10-21T15:00:00-04:00"')
    args = ap.parse_args(argv)

    now = parse_time(args.now)
    if now is None:
        print('REFUSED: --now must be a date and time with a time zone, e.g. "2026-10-21T15:00:00-04:00"')
        return 2
    try:
        data = load_context(args.context)
    except ValueError as e:
        print(f"REFUSED: the notes can't be trusted, so no answer is given: {e}")
        return 2
    limits, notes = POLICY_LIMITS, data["notes"]

    print(f"$ .venv/bin/python participant/tools/answer-blockers.py --context {args.context} --now {args.now}")
    print(f"# answer-blockers.py {VERSION}")
    print(f"Clock set to: {shown(now)} (from --now, not the computer's clock)")
    print(f"Question: {data['question']}")
    print()

    results = [assess(n, limits, now) for n in notes]
    print("Notes used:")
    for r in results:
        n = r["note"]
        age = age_text(r["age"]) if r["age"] is not None else "unknown"
        limit = f"limit {r['limit']} day{'s' if r['limit'] != 1 else ''}" if r["limit"] else "no limit"
        raw = n.get("retrieved_at")
        retrieved = "NOT RECORDED" if raw in (None, "") else str(raw)
        extra = f" -- {r['why']}" if r["why"] else ""
        print(f"  {n['id']:8} {n['source']:13} retrieved {retrieved:26} age {age:17} {limit:13} {r['status'].upper()}{extra}")
    print()

    dated = [r for r in results if r["age"] is not None]
    undated = [r for r in results if r["age"] is None]
    # A note without a usable age can't be called the oldest, so these are reported on their own.
    if undated:
        print("Notes with no usable age: " + "; ".join(f"{r['note']['id']} ({r['age_problem']})" for r in undated))
    if dated:
        oldest = max(dated, key=lambda r: r["age"])
        label = "Oldest dated note used" if undated else "Oldest note used"
        print(f"{label}: {oldest['note']['id']} ({oldest['note']['source']}), {age_text(oldest['age'])} old")

    worst = max(results, key=lambda r: RANK[r["status"]])["status"]
    stale = [r for r in results if r["status"] == "stale"]
    too_old = [r for r in results if r["status"] == "too old"]
    refresh = [r["note"]["id"] for r in results if r["status"] != "fresh"]

    if worst == "too old":
        print("Answer: REFUSED. These notes can't be relied on:")
        for r in too_old:
            print(f"  {r['note']['id']}: " + (r["why"] or f"{age_text(r['age'])} old, over twice its {r['limit']}-day limit"))
        for r in stale:
            print(f"  {r['note']['id']}: stale, {age_text(r['age'])} old, past its {r['limit']}-day limit")
        print(f"Your options: refresh these notes first, then ask again: {', '.join(refresh)}. Fresh notes don't need refreshing.")
        status = 2
    else:
        found = blockers(notes)
        print("Answer: " + ("; ".join(found) if found else "nothing in these notes is blocking the release") + ".")
        if worst == "stale":
            print("WARNING: this answer relies on stale notes and may be out of date:")
            for r in stale:
                print(f"  {r['note']['id']}: {age_text(r['age'])} old, past its {r['limit']}-day limit")
            print(f"Your options: use this answer with the caveats above, or refresh these notes first: "
                  f"{', '.join(refresh)}. Fresh notes don't need refreshing.")
            status = 1
        else:
            print("All notes are within their limits.")
            status = 0
    print(f"result: {['ANSWERED (all notes fresh)', 'WARNED (stale notes)', 'REFUSED (notes too old)'][status]} (exit status {status})")
    return status


if __name__ == "__main__":
    sys.exit(main())
