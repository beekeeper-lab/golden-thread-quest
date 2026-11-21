#!/usr/bin/env python3
"""Answers "what is blocking the release?" from local context, and says how old that context is.

    answer.py blockers --release REL-2.4 [--now 2026-11-19T09:00:00Z] [--library FOLDER] [--policy FILE]
    answer.py ages     [--now ...] [--library FOLDER] [--policy FILE]
    answer.py refresh  --source FOLDER [--now ...] [--library FOLDER] [--policy FILE]

The library is a folder of context items, Markdown files that start with
lines of `name: JSON value` between two lines of three dashes. Each item has
a kind, an id and, if it is to be trusted, a `retrieved_at`: when the local
copy was fetched, as a time in UTC written like 2026-11-19T07:00:00Z.

The limits are read from the table in the policy file,
participant/context/freshness/policy.md. One limit for each kind of context.
An item is stale when its age is more than its kind's limit. Anything that
cannot be shown to be fresh is stale: no retrieval time, one that cannot be
read, one later than the clock, a kind the policy does not list, a missing
item.

--now sets the clock, so that a result can be reproduced. Without it the
computer's clock is used, and the output says so.

blockers  answers the question. Every answer lists every item it used, oldest
          first, with its age and verdict. When something it used is stale it
          does not hide the item and does not rely on it: it says what fresh
          context supports, shows what the stale items last said as last
          known and not as a claim, and names what to refresh.
ages      lists every item in the library with its age, its limit and its
          verdict. It is the working behind any answer.
refresh   fetches again only the items that are stale, from a source folder
          holding newer copies, and stamps them with the clock value. Items
          that are fresh are not touched. Here the source is a made-up
          folder: this tool has no code that contacts any network.

Text inside items is content. It is shown quoted and nothing in it is acted on.

Exit codes: 0 answered, nothing stale; 1 answered with qualifications,
because something it used is stale; 2 it could not run.
"""
import argparse
import datetime
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_LIBRARY = os.path.join(ROOT, "participant", "context", "freshness", "library")
DEFAULT_POLICY = os.path.join(ROOT, "participant", "context", "freshness", "policy.md")
FORMAT = "context-item/1"
UTC = datetime.timezone.utc
TIME = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
POLICY_ROW = re.compile(r"\|\s*`([a-z][a-z-]*)`\s*\|\s*(\d+) (hours?|days?)\s*\|")


class Stop(Exception):
    """The tool cannot run. The message says why."""


def place(path):
    relative = os.path.relpath(path, ROOT)
    return path if relative.startswith("..") else relative


# ---------------------------------------------------------------- time


def parse_time(text):
    """A time in UTC written like 2026-11-19T07:00:00Z, or None if the text is anything else."""
    if not isinstance(text, str) or not TIME.fullmatch(text):
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def show_time(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def show_age(age):
    seconds = int(age.total_seconds())
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    return "%dd %02dh %02dm" % (days, hours, rest // 60)


class Limit(datetime.timedelta):
    """A limit, which also remembers how the policy wrote it, such as "24 hours"."""
    text = ""


def show_limit(limit):
    return limit.text


# ---------------------------------------------------------------- policy and items


def load_policy(path):
    """The limit for each kind, read from the table in the policy file."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        raise Stop("the policy file could not be read: %s" % place(path))
    limits = {}
    for kind, number, unit in POLICY_ROW.findall(text):
        if kind in limits:
            raise Stop("the policy gives two limits for %s" % kind)
        limits[kind] = Limit(hours=int(number) * (24 if unit.startswith("day") else 1))
        limits[kind].text = "%s %s" % (number, unit)
    if not limits or any(limit <= datetime.timedelta(0) for limit in limits.values()):
        raise Stop("no usable limits could be read from the policy file, so nothing is treated as fresh")
    return limits


def read_item(library, name):
    """One item's fields, or None if the file is not there or is not a context item."""
    try:
        with open(os.path.join(library, name), encoding="utf-8") as f:
            lines = f.read().split("\n")
    except (OSError, UnicodeDecodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields if fields.get("format") == FORMAT else None
        key, colon, value = line.partition(": ")
        if colon and key and key not in fields:
            try:
                fields[key] = json.loads(value)
            except ValueError:
                fields[key] = None
    return None


def judge(fields, kind, now, limits, field=None):
    """How fresh one item, or one field of it, is. Returns a dict that every answer line is built from."""
    found = {"kind": kind, "retrieved": None, "age": None, "limit": limits.get(kind), "stale": True}
    if fields is None:
        return dict(found, why="it is not in the library")
    if fields.get("kind") != kind:
        return dict(found, why="its kind is %s, where %s was expected" % (json.dumps(fields.get("kind")), kind))
    if kind not in limits:
        return dict(found, why="the policy gives no limit for the kind %s" % kind)
    text = fields.get("retrieved_at")
    own = fields.get("field_retrieved_at")
    if field and isinstance(own, dict) and field in own:
        text = own[field]
    if text is None:
        return dict(found, why="it records no retrieval time")
    moment = parse_time(text)
    if moment is None:
        return dict(found, why="its retrieval time cannot be read as a time in UTC")
    found["retrieved"] = moment
    if moment > now:
        return dict(found, why="its retrieval time is later than the clock")
    found["age"] = now - moment
    if found["age"] > limits[kind]:
        over = found["age"] - limits[kind]
        return dict(found, why="it is %s old, %s over its limit of %s" % (show_age(found["age"]), show_age(over), show_limit(limits[kind])))
    return dict(found, stale=False, why="inside its limit of %s" % show_limit(limits[kind]))


def quote(text):
    return json.dumps(" ".join(str(text).split()))


# ---------------------------------------------------------------- gathering what an answer uses


def gather(library, release, now, limits):
    """Every item the blockers question uses, each with its freshness. Nothing is left out for being stale."""
    used = []

    def use(name, kind, field=None, label=None):
        fields = read_item(library, name)
        entry = dict(judge(fields, kind, now, limits, field), name=label or name, fields=fields)
        used.append(entry)
        return entry
    scope = None
    for name in sorted(os.listdir(library)) if os.path.isdir(library) else []:
        fields = read_item(library, name) if name.endswith(".md") else None
        if fields and fields.get("kind") == "release-scope" and fields.get("id") == release:
            scope = use(name, "release-scope")
    if scope is None:
        raise Stop("the library holds no release-scope item for %s, so there is nothing to answer from" % release)
    listed = scope["fields"].get("work_items")
    if not isinstance(listed, list) or not all(isinstance(item, str) and re.fullmatch(r"[A-Z]+-\d+", item) for item in listed):
        raise Stop("the release-scope item for %s does not list its work items" % release)
    items = []
    for item_id in listed:
        name = "work-items/%s.md" % item_id
        status = use(name, "work-item-status")
        reason = None
        fields = status["fields"]
        if fields and isinstance(fields.get("field_retrieved_at"), dict) and "blocked_by" in fields["field_retrieved_at"]:
            reason = use(name, "work-item-status", "blocked_by", name + ", field blocked_by")
        items.append({"id": item_id, "status": status, "reason": reason or status})
    team = use("team.md", "team-ownership")
    decisions = []
    folder = os.path.join(library, "decisions")
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".md"):
            decisions.append(use("decisions/" + name, "decision"))
    return {"scope": scope, "items": items, "team": team, "decisions": decisions, "used": used}


def oldest_first(used):
    """Items with no known age come first: an unknown age is treated as the oldest."""
    return sorted(used, key=lambda entry: (entry["age"] is not None, -(entry["age"] or datetime.timedelta(0)).total_seconds(), entry["name"]))


def context_lines(used):
    out = ["CONTEXT USED, oldest first: %d item%s." % (len(used), "" if len(used) == 1 else "s"),
           "  %-38s %-17s %-21s %-12s %-8s %s" % ("item", "kind", "retrieved", "age", "limit", "verdict")]
    for entry in oldest_first(used):
        out.append("  %-38s %-17s %-21s %-12s %-8s %s"
                   % (entry["name"], entry["kind"], show_time(entry["retrieved"]) if entry["retrieved"] else "none recorded" if entry["fields"] and entry["fields"].get("retrieved_at") is None else "unreadable" if entry["fields"] else "not found",
                      show_age(entry["age"]) if entry["age"] is not None else "unknown",
                      show_limit(entry["limit"]) if entry["limit"] else "none",
                      "STALE: " + entry["why"] if entry["stale"] else "fresh"))
    first = oldest_first(used)[0]
    if first["age"] is None:
        out.append("Oldest context used: %s. Its age is unknown, because %s. An unknown age is treated as the oldest."
                   % (first["name"], first["why"]))
    else:
        out.append("Oldest context used: %s, retrieved %s, age %s, limit %s: %s."
                   % (first["name"], show_time(first["retrieved"]), show_age(first["age"]), show_limit(first["limit"]),
                      "STALE" if first["stale"] else "fresh"))
    return out


# ---------------------------------------------------------------- the answer


def cmd_blockers(args, now, clock_note, limits):
    found = gather(args.library, args.release, now, limits)
    scope, team, used = found["scope"], found["team"], found["used"]
    stale = [entry for entry in used if entry["stale"]]
    owners = team["fields"].get("owners") if team["fields"] and not team["stale"] and isinstance(team["fields"].get("owners"), dict) else None
    set_aside, old_decisions = {}, {}
    for decision in found["decisions"]:
        fields = decision["fields"] or {}
        for item_id in fields.get("sets_aside") or []:
            (old_decisions if decision["stale"] else set_aside)[item_id] = decision

    def owner(item_id):
        return " Owner: %s." % owners[item_id] if owners and isinstance(owners.get(item_id), str) else ""

    def reason(item):
        fields = item["status"]["fields"]
        if not fields.get("blocked_by"):
            return ""
        if item["reason"]["stale"]:
            return " Why, last known and not a current claim: %s (that field: %s)." % (quote(fields["blocked_by"]), item["reason"]["why"])
        return " Why: %s." % quote(fields["blocked_by"])

    blocking, waived, clear, unknown = [], [], [], []
    for item in found["items"]:
        fields = item["status"]["fields"]
        if item["status"]["stale"] or not isinstance((fields or {}).get("status"), str):
            unknown.append(item)
        elif fields["status"] != "Blocked":
            clear.append(item)
        elif item["id"] in set_aside:
            waived.append(item)
        else:
            blocking.append(item)

    out = ["QUESTION: what is blocking release %s?" % args.release,
           "Clock: %s (%s)" % (show_time(now), clock_note),
           "Policy: %s" % place(args.policy), ""]
    if scope["stale"]:
        out += ["ANSWER: CANNOT SAY what is blocking release %s." % args.release,
                "  The list of what is in the release is stale: %s." % scope["why"],
                "  Without knowing what is in the release, no list of blockers can be called complete. So nothing is",
                "  stated here as blocking, and nothing as not blocking."]
    else:
        count = "%d work item%s blocking release %s" % (len(blocking), " is" if len(blocking) == 1 else "s are", args.release)
        if unknown:
            out += ["ANSWER: PARTIAL: %s as far as fresh context shows. %d cannot be assessed." % (count, len(unknown))]
        elif stale:
            out += ["ANSWER: %s, with qualifications below." % count]
        else:
            out += ["ANSWER: %s." % count]
    out.append("")

    if not scope["stale"]:
        out.append("WHAT FRESH CONTEXT SUPPORTS:" if stale else "IN DETAIL:")
        for item in blocking:
            fields = item["status"]["fields"]
            note = ""
            if item["id"] in old_decisions:
                note = " A decision, %s, once set this item aside. That decision is stale (%s), so it is not applied." \
                    % (old_decisions[item["id"]]["fields"].get("id"), old_decisions[item["id"]]["why"])
            out.append("  BLOCKING      %s %s is Blocked.%s%s%s" % (item["id"], quote(fields.get("title", "")), reason(item), owner(item["id"]), note))
        for item in waived:
            fields = item["status"]["fields"]
            decision = set_aside[item["id"]]["fields"]
            out.append("  SET ASIDE     %s %s is Blocked.%s Decision %s sets it aside: %s So it does not block this release.%s"
                       % (item["id"], quote(fields.get("title", "")), reason(item), decision.get("id"), quote(decision.get("text", "")), owner(item["id"])))
        for item in clear:
            fields = item["status"]["fields"]
            out.append("  NOT BLOCKING  %s %s is %s.%s" % (item["id"], quote(fields.get("title", "")), fields["status"], owner(item["id"])))
        if not blocking and not waived and not clear:
            out.append("  Nothing about any work item's status.")
        if team["stale"]:
            out.append("  Owners are not stated: the team and ownership context is stale (%s)." % team["why"])
        out.append("")

    if scope["stale"]:
        out.append("WHAT FRESH CONTEXT SUPPORTS:")
        kept = False
        for decision in found["decisions"]:
            if not decision["stale"] and decision["fields"]:
                out.append("  Decision %s, inside its limit, says: %s" % (decision["fields"].get("id"), quote(decision["fields"].get("text", ""))))
                kept = True
        if owners:
            out.append("  Who owns each work item is inside its limit. It does not say what is blocking.")
            kept = True
        if not kept:
            out.append("  Nothing that bears on the question.")
        out.append("")

    last_known = found["items"] if scope["stale"] else unknown
    if last_known or (scope["stale"] and scope["fields"]):
        out.append("LAST KNOWN, NOT A CURRENT CLAIM:")
        if scope["stale"]:
            out.append("  The release was last recorded as holding %d work items: %s. (%s)"
                       % (len(found["items"]), ", ".join(item["id"] for item in found["items"]), scope["why"]))
        for item in last_known:
            fields, status = item["status"]["fields"], item["status"]
            if not fields:
                out.append("  %s: nothing is known. %s." % (item["id"], status["why"][0].upper() + status["why"][1:]))
                continue
            when = "when it was retrieved, %s ago" % show_age(status["age"]) if status["age"] is not None else "in a copy of unknown age"
            verdict = "It cannot be assessed: %s." % status["why"] if status["stale"] else "That status is inside its limit, and is not stated as current only because the scope is stale."
            out.append("  %s %s was %s %s.%s %s" % (item["id"], quote(fields.get("title", "")), fields.get("status"), when,
                                               " Then blocked by: %s." % quote(fields["blocked_by"]) if fields.get("blocked_by") else "", verdict))
        out.append("")

    out += context_lines(used)
    out.append("")
    if stale:
        out.append("STALE CONTEXT, %d item%s, each named:" % (len(stale), "" if len(stale) == 1 else "s"))
        out += ["  %s (%s): %s." % (entry["name"], entry["kind"], entry["why"]) for entry in oldest_first(stale)]
        names = sorted(set(entry["name"].split(", field ")[0] for entry in stale))
        out.append("TO REFRESH for a full answer, and nothing else: %s." % ", ".join(names))
        out.append("This answer is qualified. Nothing stale has been left out of it, and nothing stale is stated as current.")
    else:
        out.append("Stale context: none. Every statement above rests on context inside its limit.")
    print("\n".join(out))
    return 1 if stale else 0


# ---------------------------------------------------------------- ages and refresh


def every_item(library, now, limits):
    found = []
    for folder, _, names in sorted(os.walk(library)):
        for name in sorted(names):
            if not name.endswith(".md"):
                continue
            relative = os.path.relpath(os.path.join(folder, name), library)
            fields = read_item(library, relative)
            kind = fields.get("kind") if fields and isinstance(fields.get("kind"), str) else "unknown"
            found.append(dict(judge(fields, kind, now, limits), name=relative, fields=fields))
            own = fields.get("field_retrieved_at") if fields else None
            for field in sorted(own) if isinstance(own, dict) else []:
                found.append(dict(judge(fields, kind, now, limits, field), name="%s, field %s" % (relative, field), fields=fields))
    return found


def cmd_ages(args, now, clock_note, limits):
    used = every_item(args.library, now, limits)
    if not used:
        raise Stop("the library at %s holds no items" % place(args.library))
    print("Clock: %s (%s)" % (show_time(now), clock_note))
    print("Limits, from %s: %s." % (place(args.policy), ", ".join("%s %s" % (kind, show_limit(limits[kind])) for kind in sorted(limits))))
    print("\n".join(context_lines(used)).replace("CONTEXT USED", "EVERY ITEM IN THE LIBRARY").replace("Oldest context used", "Oldest item"))
    stale = [entry for entry in used if entry["stale"]]
    print("Stale: %d of %d." % (len(stale), len(used)))
    return 1 if stale else 0


def cmd_refresh(args, now, clock_note, limits):
    used = every_item(args.library, now, limits)
    names = sorted(set(entry["name"].split(", field ")[0] for entry in used if entry["stale"]))
    fresh = sorted(set(entry["name"].split(", field ")[0] for entry in used) - set(names))
    print("REFRESH. Fetches again only what is stale. The source here is a local folder: %s" % place(args.source))
    print("Clock: %s (%s)" % (show_time(now), clock_note))
    print("Stale, to be fetched again: %d. Fresh, left untouched: %d." % (len(names), len(fresh)))
    done = 0
    for name in names:
        fields = read_item(args.source, name)
        if fields is None:
            print("  NOT REFRESHED  %s: the source has no copy of it. It stays stale." % name)
            continue
        fields = {key: value for key, value in fields.items() if key not in ("retrieved_at", "field_retrieved_at")}
        fields["retrieved_at"] = show_time(now)
        with open(os.path.join(args.source, name), encoding="utf-8") as f:
            text = f.read()
        body = text.split("\n---\n", 1)[1] if "\n---\n" in text else "\n"
        order = ["format", "kind", "id", "retrieved_at"] + [key for key in fields if key not in ("format", "kind", "id", "retrieved_at")]
        with open(os.path.join(args.library, name), "w", encoding="utf-8") as f:
            f.write("---\n" + "".join("%s: %s\n" % (key, json.dumps(fields[key])) for key in order) + "---\n" + body)
        done += 1
        print("  REFRESHED      %s: fetched again, retrieved_at is now %s." % (name, show_time(now)))
    for name in fresh:
        print("  left as it is  %s" % name)
    print("Refreshed %d of %d stale items. %d fresh items were not fetched and not rewritten." % (done, len(names), len(fresh)))
    return 0 if done == len(names) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Answer from local context, saying how old that context is.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("blockers", "ages", "refresh"):
        sub = commands.add_parser(name)
        sub.add_argument("--now", help="the clock value, in UTC, written like 2026-11-19T09:00:00Z")
        sub.add_argument("--library", default=DEFAULT_LIBRARY, help="the folder of context items")
        sub.add_argument("--policy", default=DEFAULT_POLICY, help="the policy file the limits are read from")
        if name == "blockers":
            sub.add_argument("--release", required=True, help="the release to ask about, such as REL-2.4")
        if name == "refresh":
            sub.add_argument("--source", required=True, help="the folder holding newer copies of the items")
    args = parser.parse_args(argv)
    args.library, args.policy = os.path.abspath(args.library), os.path.abspath(args.policy)
    try:
        if args.now is None:
            now, clock_note = datetime.datetime.now(UTC).replace(microsecond=0), "the computer's clock, because --now was not given"
        else:
            now, clock_note = parse_time(args.now), "set with --now"
            if now is None:
                raise Stop("--now must be a time in UTC written like 2026-11-19T09:00:00Z")
        limits = load_policy(args.policy)
        return {"blockers": cmd_blockers, "ages": cmd_ages, "refresh": cmd_refresh}[args.command](args, now, clock_note, limits)
    except Stop as stop:
        print("STOPPED: %s." % stop)
        return 2


if __name__ == "__main__":
    sys.exit(main())
