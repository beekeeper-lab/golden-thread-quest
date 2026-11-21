#!/usr/bin/env python3
"""Conflict detection for the jira-detect-conflicts quest.

Reads three files and prints a report. It contacts nothing and changes nothing.

    jira-copy.json     Jira's copy of each story, as stored at the last sync
    local-edits.json   edits made locally since then, each with the Jira
                       value it was based on (its "base")
    jira-now.json      what Jira returns for the same stories now

For every field of every story it works out one of these:

    conflict            a local edit exists, Jira's value has moved away from
                        the base, and Jira's value is not the local value
    agreement           a local edit exists, Jira's value has moved away from
                        the base, and Jira's value is the local value
    changed locally     a local edit exists and Jira's value is still the base
    changed in Jira     no local edit, and Jira's value differs from the
                        stored copy
    cannot be compared  a local edit exists but Jira no longer returns the
                        story
    unchanged           none of the above

It never chooses between two values. A conflict is reported with the base,
local and Jira values and their times, and both values are left where they are.

The three files are opened for reading only. The report goes to standard
output, or to the file named by --out. Field values are text from other
people: they are printed as data and nothing in them is acted on.

The report has no date or time of its own and lists everything in a fixed
order, so the same three files always give the same report.

Usage: detect.py --fixture DIR [--out REPORT.md]
Exit codes: 0 no conflicts; 2 at least one conflict; 1 an input could not be used.
"""
import argparse
import hashlib
import json
import os
import sys

FIELDS = ("summary", "status", "priority", "estimate", "due_date")


class BadInput(Exception):
    pass


def read_json(path):
    try:
        with open(path, "rb") as f:  # reading only
            raw = f.read()
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except FileNotFoundError:
        raise BadInput("there is no file at %s" % path)
    except (ValueError, UnicodeDecodeError):
        raise BadInput("%s is not JSON" % path)


def check_stories(data, name):
    stories = data.get("stories") if isinstance(data, dict) else None
    if not isinstance(stories, dict):
        raise BadInput("%s has no stories" % name)
    for key, story in stories.items():
        if not isinstance(story, dict) or set(story) != set(FIELDS):
            raise BadInput("%s: story %s does not have exactly the five fields" % (name, key))
        for field in FIELDS:
            cell = story[field]
            if not isinstance(cell, dict) or "value" not in cell or not isinstance(cell.get("changed_at"), str):
                raise BadInput("%s: %s %s has no value or no time" % (name, key, field))
    return stories


def check_edits(data, name):
    edits = data.get("edits") if isinstance(data, dict) else None
    if not isinstance(edits, list):
        raise BadInput("%s has no list of edits" % name)
    seen = set()
    for edit in edits:
        ok = (isinstance(edit, dict) and isinstance(edit.get("story"), str) and edit.get("field") in FIELDS
              and isinstance(edit.get("base"), dict) and "value" in edit["base"]
              and isinstance(edit["base"].get("changed_at"), str)
              and isinstance(edit.get("local"), dict) and "value" in edit["local"]
              and isinstance(edit["local"].get("edited_at"), str))
        if not ok:
            # Criterion 1: an edit with no recorded base cannot be judged, so it is not guessed at.
            raise BadInput("%s: a local edit is missing its story, field, base or local value" % name)
        if (edit["story"], edit["field"]) in seen:
            raise BadInput("%s: two edits for %s %s" % (name, edit["story"], edit["field"]))
        seen.add((edit["story"], edit["field"]))
    return edits


def key_order(key):
    prefix, _, number = key.rpartition("-")
    return (prefix, int(number)) if number.isdigit() else (key, 0)


def detect(copy, edits, now):
    """Sort every field of every story into one of the outcomes."""
    found = {"conflict": [], "agreement": [], "local": [], "jira": [], "uncomparable": []}
    unchanged = 0
    by_place = {(edit["story"], edit["field"]): edit for edit in edits}

    for (story, field), edit in sorted(by_place.items(), key=lambda item: (key_order(item[0][0]), FIELDS.index(item[0][1]))):
        base, local = edit["base"], edit["local"]
        row = {"story": story, "field": field, "base": base, "local": local, "jira": None}
        if story not in now:
            found["uncomparable"].append(row)
            continue
        jira = now[story][field]
        row["jira"] = jira
        if local["value"] == base["value"]:
            # An "edit" that changes nothing is treated as no local edit at all.
            del by_place[(story, field)]
        elif jira["value"] == base["value"]:
            found["local"].append(row)
        elif jira["value"] == local["value"]:
            found["agreement"].append(row)
        else:
            found["conflict"].append(row)

    for story in sorted(now, key=key_order):
        for field in FIELDS:
            if (story, field) in by_place:
                continue
            jira = now[story][field]
            if story in copy and copy[story][field]["value"] == jira["value"]:
                unchanged += 1
            else:
                before = copy[story][field] if story in copy else None
                found["jira"].append({"story": story, "field": field, "base": before, "local": None, "jira": jira})
    return found, unchanged


# ---------------------------------------------------------------- the report


def shown(value):
    """A value as data: on one line, in a code span, with nothing able to break the table."""
    if value is None:
        return "(empty)"
    text = value if isinstance(value, str) else json.dumps(value)
    text = text.replace("\\", "\\\\").replace("\r", " ").replace("\n", " ").replace("|", "\\|").replace("`", "'")
    return "`%s`" % text


def who(cell, name):
    by = cell.get(name)
    return shown(by) if isinstance(by, str) else "(not recorded)"


def three_values(row):
    lines = ["| | Value | When | Who |", "|---|---|---|---|"]
    lines.append("| Base | %s | %s | |" % (shown(row["base"]["value"]), row["base"]["changed_at"]))
    lines.append("| Local | %s | %s | %s |" % (shown(row["local"]["value"]), row["local"]["edited_at"],
                                              who(row["local"], "edited_by")))
    lines.append("| Jira now | %s | %s | %s |" % (shown(row["jira"]["value"]), row["jira"]["changed_at"],
                                                 who(row["jira"], "changed_by")))
    return lines


def report(found, unchanged, sums, names):
    out = ["# Conflict report", ""]
    out += ["Made by `detect.py` from three files. It read them and changed nothing. The values below are text from",
            "the stories, shown as data. Nothing written in a value was acted on.", ""]
    out += ["| Input | SHA-256 |", "|---|---|"]
    out += ["| `%s` | `%s` |" % (name, sums[name]) for name in names]
    out += ["", "## Conflicts (%d)" % len(found["conflict"]), ""]
    if found["conflict"]:
        out += ["Each of these fields was changed locally and changed in Jira, to different values. Neither value has",
                "been written over the other. Both are kept until a person decides.", ""]
    else:
        out += ["None.", ""]
    for row in found["conflict"]:
        out += ["### %s · %s" % (row["story"], row["field"]), ""] + three_values(row) + [""]

    out += ["## Agreements (%d)" % len(found["agreement"]), "",
            "Changed on both sides to the same value. Nothing to decide.", ""]
    for row in found["agreement"]:
        out += ["### %s · %s" % (row["story"], row["field"]), ""] + three_values(row) + [""]

    out += ["## Changed only locally (%d)" % len(found["local"]), "",
            "Jira still has the base value. Not a conflict.", "",
            "| Story | Field | Base | Local | Edited at |", "|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s |" % (r["story"], r["field"], shown(r["base"]["value"]),
                                          shown(r["local"]["value"]), r["local"]["edited_at"]) for r in found["local"]]

    out += ["", "## Changed only in Jira (%d)" % len(found["jira"]), "",
            "No local edit. Not a conflict.", "",
            "| Story | Field | Stored copy | Jira now | Changed at |", "|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s |" % (r["story"], r["field"],
                                          shown(r["base"]["value"]) if r["base"] else "(story not held)",
                                          shown(r["jira"]["value"]), r["jira"]["changed_at"]) for r in found["jira"]]

    out += ["", "## Cannot be compared (%d)" % len(found["uncomparable"]), "",
            "A local edit exists, but Jira did not return the story. The local edit is kept.", "",
            "| Story | Field | Base | Local | Edited at |", "|---|---|---|---|---|"]
    out += ["| %s | %s | %s | %s | %s |" % (r["story"], r["field"], shown(r["base"]["value"]),
                                          shown(r["local"]["value"]), r["local"]["edited_at"])
            for r in found["uncomparable"]]

    counts = {}
    for row in found["conflict"]:
        counts[row["field"]] = counts.get(row["field"], 0) + 1
    out += ["", "## Conflicts by field", "", "| Field | Conflicts |", "|---|---|"]
    out += ["| %s | %d |" % (field, counts.get(field, 0)) for field in FIELDS]

    out += ["", "## Totals", "", "| | Count |", "|---|---|",
            "| Conflicts | %d |" % len(found["conflict"]),
            "| Agreements | %d |" % len(found["agreement"]),
            "| Changed only locally | %d |" % len(found["local"]),
            "| Changed only in Jira | %d |" % len(found["jira"]),
            "| Cannot be compared | %d |" % len(found["uncomparable"]),
            "| Fields compared and unchanged | %d |" % unchanged]
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Report conflicts between local edits and Jira. Reads only.")
    parser.add_argument("--fixture", required=True, help="folder holding the three JSON files")
    parser.add_argument("--out", help="write the report here instead of printing it")
    args = parser.parse_args()
    names = ("jira-copy.json", "local-edits.json", "jira-now.json")
    try:
        data, sums = {}, {}
        for name in names:
            data[name], sums[name] = read_json(os.path.join(args.fixture, name))
        copy = check_stories(data["jira-copy.json"], "jira-copy.json")
        now = check_stories(data["jira-now.json"], "jira-now.json")
        edits = check_edits(data["local-edits.json"], "local-edits.json")
    except BadInput as problem:
        print("detect: stopped, nothing reported: %s" % problem)
        return 1
    found, unchanged = detect(copy, edits, now)
    text = report(found, unchanged, sums, names)
    if args.out:
        folder = os.path.abspath(args.fixture)
        if os.path.abspath(args.out).startswith(folder + os.sep):
            print("detect: stopped: the report may not be written into the fixture folder")
            return 1
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("detect: report written to %s: %d conflict(s)" % (args.out, len(found["conflict"])))
    else:
        sys.stdout.write(text)
    return 2 if found["conflict"] else 0


if __name__ == "__main__":
    sys.exit(main())
