#!/usr/bin/env python3
"""Records one local edit for the jira-detect-conflicts quest.

A local edit is a change a person makes to a story's field on their own
machine. It is never written into Jira's copy. It goes into a separate file,
local-edits.json, together with the Jira value it was based on.

    local_edit.py --copy jira-copy.json --edits local-edits.json \
                  --story FIX-3 --field estimate --value 5 --by participant

What it does:

  1. Reads Jira's copy (reading only) and finds the field's present value
     and the time Jira last changed it. That pair is the base.
  2. If this field has no local edit yet, it writes a new one holding the
     base, the local value, the time of the edit and who made it.
  3. If this field already has a local edit, it keeps the base exactly as
     first recorded and replaces only the local value, time and name. The
     base says where the person started from, and a second edit does not
     change where they started.

It never writes to Jira's copy and it contacts nothing.

--value is read as JSON when it can be (5 is a number, null is empty) and as
text otherwise. --at sets the time of the edit, for repeatable tests. Without
it the machine's clock is used.

Exit codes: 0 recorded; 1 refused, with the reason, and nothing written.
"""
import argparse
import datetime
import json
import os
import sys

FIELDS = ("summary", "status", "priority", "estimate", "due_date")


def main():
    parser = argparse.ArgumentParser(description="Record one local edit with its base value.")
    parser.add_argument("--copy", required=True, help="Jira's copy, read only")
    parser.add_argument("--edits", required=True, help="the local edits file, created if absent")
    parser.add_argument("--story", required=True)
    parser.add_argument("--field", required=True, choices=FIELDS)
    parser.add_argument("--value", required=True)
    parser.add_argument("--by", required=True)
    parser.add_argument("--at")
    args = parser.parse_args()

    if os.path.abspath(args.copy) == os.path.abspath(args.edits):
        print("local_edit: refused: the edits file and Jira's copy must be different files")
        return 1
    try:
        with open(args.copy, encoding="utf-8") as f:  # reading only
            stories = json.load(f)["stories"]
        cell = stories[args.story][args.field]
        base = {"value": cell["value"], "changed_at": cell["changed_at"]}
    except FileNotFoundError:
        print("local_edit: refused: there is no Jira copy at %s" % args.copy)
        return 1
    except (ValueError, KeyError, TypeError):
        # No base can be read, so no edit is recorded. An edit without a base could never be judged.
        print("local_edit: refused: Jira's copy has no %s for story %s, so there is no base to record"
              % (args.field, args.story))
        return 1

    try:
        value = json.loads(args.value)
    except ValueError:
        value = args.value
    if isinstance(value, (dict, list)):
        print("local_edit: refused: a field value is text, a number or empty")
        return 1
    when = args.at or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    data = {"what": "Edits made locally since the last sync, each with the Jira value it was based on.", "edits": []}
    if os.path.exists(args.edits):
        try:
            with open(args.edits, encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data["edits"], list)
        except (ValueError, KeyError, TypeError, AssertionError):
            print("local_edit: refused: %s cannot be read as a local edits file" % args.edits)
            return 1

    local = {"value": value, "edited_at": when, "edited_by": args.by}
    for edit in data["edits"]:
        if edit.get("story") == args.story and edit.get("field") == args.field:
            edit["local"] = local  # the base is left exactly as first recorded
            print("local_edit: %s %s edited again. Local value is now %s. Base kept as first recorded: %s (%s)"
                  % (args.story, args.field, json.dumps(value), json.dumps(edit["base"]["value"]),
                     edit["base"]["changed_at"]))
            break
    else:
        data["edits"].append({"story": args.story, "field": args.field, "base": base, "local": local})
        print("local_edit: %s %s recorded. Local value %s. Base %s (%s), read from Jira's copy"
              % (args.story, args.field, json.dumps(value), json.dumps(base["value"]), base["changed_at"]))

    tmp = args.edits + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, args.edits)
    return 0


if __name__ == "__main__":
    sys.exit(main())
