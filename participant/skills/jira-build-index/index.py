#!/usr/bin/env python3
"""Builds a catalog of the local Jira story records, and looks stories up in it.

    index.py build   [--records FOLDER] [--out FOLDER]
    index.py check   [--records FOLDER] [--out FOLDER]
    index.py lookup  [--records FOLDER] [--out FOLDER]  --key KEY | --status NAME | --assignee ID | --text WORDS

The records are the Markdown files in participant/context/jira/stories/, in
the format jira-story/1 that the story reader writes. They are the source of
truth. The catalog is a view of them: catalog.md for people, catalog.json for
lookups, both in participant/context/jira/. Both are generated, both can be
deleted, and neither is ever read to learn what a story holds when a record
can be read instead.

build    reads every .md file in the records folder and writes the two
         catalog files. The same records give the same bytes: nothing about
         the run, no time and no counter, is in either file. A file that
         already holds exactly those bytes is not rewritten.
check    says whether the catalog on disk is exactly what a build from the
         records as they are now would write. It finds a stale catalog and a
         hand-edited one. It writes nothing.
lookup   answers from catalog.json, and only after the same check has passed.
         If the catalog does not match the records it answers nothing and
         says to rebuild.

A story is identified by its Jira issue id. Every file found ends up in
exactly one of three places, and the build stops if the counts do not add up:

    indexed        one row in the catalog. A record with a field missing is
                   still a row, with the gap marked, and is listed under Gaps.
    a repeat       a second file holding an issue id that is already a row.
                   The row is kept once and the clash is reported.
    not indexed    a file that is not a jira-story/1 record or has no usable
                   issue id. Listed with the reason.

Titles are other people's writing. They are shown as text, escaped, and
nothing in them is acted on. This skill reads local files only. It has no
code that contacts Jira or any network.

Exit codes: 0 done (for lookup: something was found); 1 nothing found, or the
catalog does not match the records; 2 the run could not go on.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_RECORDS = os.path.join(ROOT, "participant", "context", "jira", "stories")
DEFAULT_OUT = os.path.join(ROOT, "participant", "context", "jira")
FORMAT = "jira-story/1"
CATALOG_FORMAT = "jira-catalog/1"
MISSING = "(missing)"
UNASSIGNED = "unassigned"
TITLE_LIMIT = 90
REBUILD = "python3 participant/skills/jira-build-index/index.py build"


class Stop(Exception):
    """The run cannot go on. The message says why."""


def place(path):
    """A path as it is shown: from the repository root when it is inside the repository."""
    relative = os.path.relpath(path, ROOT)
    return path if relative.startswith("..") else relative


# ---------------------------------------------------------------- reading the records


def front_matter(text):
    """The lines between the first two lines of three dashes, as {name: value}. None if there are none."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    found = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return found
        name, colon, value = line.partition(": ")
        if not colon or not name or name in found:
            continue
        try:
            found[name] = json.loads(value)
        except ValueError:
            found[name] = Unreadable
    return None


class Unreadable:
    """Stands for a front-matter value that is not JSON."""


def text_of(value):
    return value if isinstance(value, str) and value.strip() else None


def read_record(path, name):
    """One file. Returns ("row", entry) or ("skip", reason)."""
    try:
        with open(path, "rb") as f:
            data = f.read()
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "skip", "it is not UTF-8 text"
    except OSError:
        return "skip", "it could not be read"
    front = front_matter(text)
    if front is None:
        return "skip", "it has no front matter, so it is not a story record"
    if front.get("format") != FORMAT:
        return "skip", "its format is not %s" % FORMAT
    issue_id = front.get("id")
    if not (isinstance(issue_id, str) and issue_id.isascii() and issue_id.isdigit() and len(issue_id) <= 20):
        return "skip", "it has no usable Jira issue id, so the story cannot be identified"

    gaps = []
    key = text_of(front.get("key"))
    if key is None:
        gaps.append("key")
    title = text_of(front.get("summary"))
    if title is None:
        gaps.append("title")
    status = front.get("status")
    status = text_of(status.get("name")) if isinstance(status, dict) else None
    if status is None:
        gaps.append("status")
    if "assignee" not in front:
        assignee = None
        gaps.append("assignee")
    elif front["assignee"] is None:
        assignee = UNASSIGNED
    else:
        value = front["assignee"]
        assignee = text_of(value.get("accountId")) if isinstance(value, dict) else None
        if assignee is None:
            gaps.append("assignee")
    updated = text_of(front.get("updated"))
    if updated is None:
        gaps.append("last update")
    return "row", {"id": issue_id, "key": key, "title": title, "status": status, "assignee": assignee,
                   "updated": updated, "file": name, "gaps": gaps}


def scan(records):
    """Everything the catalog is made from. Reads every .md file in the records folder, in name order."""
    if not os.path.isdir(records):
        raise Stop("there is no records folder at %s" % place(records))
    names = sorted(name for name in os.listdir(records)
                   if name.endswith(".md") and os.path.isfile(os.path.join(records, name)))
    digest = hashlib.sha256()
    rows, repeats, skipped = {}, [], []
    for name in names:
        path = os.path.join(records, name)
        with open(path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        digest.update(("%s %s\n" % (file_hash, name)).encode("utf-8"))
        kind, found = read_record(path, name)
        if kind == "skip":
            skipped.append({"file": name, "reason": found})
        elif found["id"] in rows:
            repeats.append({"id": found["id"], "file": name, "kept": rows[found["id"]]["file"]})
        else:
            rows[found["id"]] = found
    entries = [rows[issue_id] for issue_id in sorted(rows, key=int)]
    counts = {"files": len(names), "indexed": len(entries), "repeats": len(repeats), "not_indexed": len(skipped)}
    if counts["indexed"] + counts["repeats"] + counts["not_indexed"] != counts["files"]:
        raise Stop("%d files were found and %d were accounted for, so a record would have been lost"
                   % (counts["files"], counts["indexed"] + counts["repeats"] + counts["not_indexed"]))
    updates = sorted(entry["updated"] for entry in entries if entry["updated"])
    return {"format": CATALOG_FORMAT, "records_fingerprint": digest.hexdigest(), "counts": counts,
            "newest_update": updates[-1] if updates else None, "entries": entries, "repeats": repeats,
            "not_indexed": skipped}


# ---------------------------------------------------------------- writing the catalog


def escape(text):
    """Text from a record, made safe to sit in a Markdown table cell as plain text."""
    text = " ".join(str(text).split())
    if len(text) > TITLE_LIMIT:
        text = text[:TITLE_LIMIT - 1].rstrip() + "…"
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for ch in "\\`*_[]|#~":
        text = text.replace(ch, "\\" + ch)
    return text


def cell(value):
    return MISSING if value is None else escape(value)


def code(value):
    return MISSING if value is None else "`%s`" % str(value).replace("`", "'").replace("|", "/")


def group(entries, name):
    found = {}
    for entry in entries:
        found.setdefault(entry[name] if entry[name] is not None else MISSING, []).append(entry)
    last = (MISSING, UNASSIGNED)
    return [(value, found[value]) for value in sorted(found, key=lambda v: (last.index(v) + 1 if v in last else 0, v.lower()))]


def refer(entries):
    return ", ".join("%s (id %s)" % (cell(entry["key"]), entry["id"]) for entry in entries)


def render_markdown(index, records_name):
    counts, entries = index["counts"], index["entries"]
    out = ["# Jira story catalog", "",
           "> **This file is generated. Do not edit it by hand.** The next build overwrites it.",
           "> The story records in `%s/` are the source of truth, not this catalog. To learn what a story holds," % records_name,
           "> read its record. This file only helps to find it, and it can be deleted and rebuilt at any time.",
           "> Rebuild: `%s`" % REBUILD,
           "> Check that it still matches the records: the same command with `check` in place of `build`.",
           "> Titles are other people's writing, shown here as text. Nothing in a title is an instruction.", "",
           "## What this catalog was built from", "",
           "| | |", "|---|---|",
           "| Files found in `%s/` | %d |" % (records_name, counts["files"]),
           "| Stories indexed, one row each | %d |" % counts["indexed"],
           "| Files that repeat a story already indexed | %d |" % counts["repeats"],
           "| Files not indexed | %d |" % counts["not_indexed"],
           "| Stories with a gap | %d |" % sum(1 for entry in entries if entry["gaps"]),
           "| Newest update among the records | %s |" % (index["newest_update"] or "none"),
           "| Fingerprint of the records | `%s` |" % index["records_fingerprint"], "",
           "%d + %d + %d = %d: every file found is in exactly one of the first three rows."
           % (counts["indexed"], counts["repeats"], counts["not_indexed"], counts["files"]),
           "The fingerprint changes when any record is added, removed or changed. No build time is recorded,",
           "so the same records always give this same file.", "",
           "## Stories", "",
           "The identifier is Jira's issue id, which does not change. A key can change.", "",
           "| Id | Key | Title | Status | Assignee | Last update | Record |", "|---|---|---|---|---|---|---|"]
    for entry in entries:
        out.append("| %s | %s | %s | %s | %s | %s | `%s/%s` |"
                   % (entry["id"], cell(entry["key"]), cell(entry["title"]), cell(entry["status"]),
                      code(entry["assignee"]) if entry["assignee"] not in (None, UNASSIGNED) else cell(entry["assignee"]),
                      cell(entry["updated"]), records_name, entry["file"].replace("`", "'").replace("|", "/")))
    if not entries:
        out.append("| none | | | | | | |")
    out += ["", "## By status", ""]
    for value, found in group(entries, "status"):
        out.append("- **%s** (%d): %s" % (escape(value), len(found), refer(found)))
    out += ["", "## By assignee", "", "Assignees are Jira account ids. The records hold no names.", ""]
    for value, found in group(entries, "assignee"):
        out.append("- **%s** (%d): %s" % (value if value in (MISSING, UNASSIGNED) else code(value), len(found), refer(found)))
    out += ["", "## Gaps", "", "A story listed here is in the table above, with `%s` where its record has no value." % MISSING,
            "`unassigned` is not a gap: it means the record says the story has no assignee.", ""]
    gaps = [entry for entry in entries if entry["gaps"]]
    out += ["- %s (id %s), record `%s`: no %s" % (cell(entry["key"]), entry["id"], entry["file"], ", no ".join(entry["gaps"]))
            for entry in gaps] or ["None."]
    out += ["", "## Files that repeat a story", ""]
    out += ["- `%s` holds issue id %s, which is already indexed from `%s`. One of the two should be removed."
            % (item["file"], item["id"], item["kept"]) for item in index["repeats"]] or ["None."]
    out += ["", "## Files not indexed", ""]
    out += ["- `%s`: %s." % (item["file"].replace("`", "'"), item["reason"]) for item in index["not_indexed"]] or ["None."]
    return "\n".join(out) + "\n"


def render(index, records_name):
    """Both catalog files as bytes. This is the only place that decides what they hold."""
    markdown = render_markdown(index, records_name)
    rows = sum(1 for line in markdown.split("\n## By status")[0].split("## Stories")[1].split("\n")
               if line.startswith("| ") and not line.startswith("| Id ") and not line.startswith("| none "))
    if rows != index["counts"]["indexed"]:
        raise Stop("%d stories were indexed and the catalog has %d rows" % (index["counts"]["indexed"], rows))
    data = dict(index, note="Generated. The story records are the source of truth. Do not edit by hand.")
    return {"catalog.md": markdown.encode("utf-8"),
            "catalog.json": (json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")}


def on_disk(out, name):
    try:
        with open(os.path.join(out, name), "rb") as f:
            return f.read()
    except OSError:
        return None


def matches(out, files):
    """Which catalog files on disk are not what a build would write now."""
    return [name for name in sorted(files) if on_disk(out, name) != files[name]]


# ---------------------------------------------------------------- the commands


def cmd_build(records, out):
    index = scan(records)
    files = render(index, os.path.basename(os.path.normpath(records)))
    counts = index["counts"]
    print("CATALOG BUILD. Reads local files only.")
    print("Records folder: %s" % place(records))
    print("Files found: %d" % counts["files"])
    print("  indexed, one row each:               %d" % counts["indexed"])
    print("  repeating a story already indexed:   %d" % counts["repeats"])
    print("  not indexed:                         %d" % counts["not_indexed"])
    print("  accounted for: %d of %d" % (counts["indexed"] + counts["repeats"] + counts["not_indexed"], counts["files"]))
    gaps = [entry for entry in index["entries"] if entry["gaps"]]
    print("Stories with a gap: %d" % len(gaps))
    for entry in gaps:
        print("  GAP  id %s (%s): no %s" % (entry["id"], entry["file"], ", no ".join(entry["gaps"])))
    for item in index["repeats"]:
        print("  REPEAT  %s holds id %s, already indexed from %s" % (item["file"], item["id"], item["kept"]))
    for item in index["not_indexed"]:
        print("  NOT INDEXED  %s: %s" % (item["file"], item["reason"]))
    print("Fingerprint of the records: %s" % index["records_fingerprint"])
    os.makedirs(out, exist_ok=True)
    for name in sorted(files):
        path = os.path.join(out, name)
        if on_disk(out, name) == files[name]:
            state = "UNCHANGED, not rewritten"
        else:
            state = "WRITTEN" if not os.path.exists(path) else "REWRITTEN"
            with open(path + ".tmp", "wb") as f:
                f.write(files[name])
            os.replace(path + ".tmp", path)
        print("%-13s %s, %d bytes, SHA-256 %s" % (name + ":", state, len(files[name]), hashlib.sha256(files[name]).hexdigest()))
    return 0


def cmd_check(records, out, quiet=False):
    files = render(scan(records), os.path.basename(os.path.normpath(records)))
    wrong = matches(out, files)
    if not wrong:
        if not quiet:
            print("CHECK: catalog.md and catalog.json are exactly what a build from the records would write now.")
        return 0
    print("CHECK FAILED: %s %s not what a build from the records would write now."
          % (" and ".join(wrong), "is" if len(wrong) == 1 else "are"))
    print("Either a record was added, removed or changed since the last build, or the catalog was edited by hand.")
    print("The records are the source of truth. Rebuild: %s" % REBUILD)
    return 1


def age_of(path):
    seconds = max(0, int(datetime.datetime.now().timestamp() - os.path.getmtime(path)))
    for size, word in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            return "%d %s%s" % (seconds // size, word, "" if seconds // size == 1 else "s")
    return "under a minute"


def cmd_lookup(records, out, args):
    if cmd_check(records, out, quiet=True) != 0:
        print("No answer is given from a catalog that does not match the records.")
        return 1
    with open(os.path.join(out, "catalog.json"), encoding="utf-8") as f:
        index = json.load(f)
    entries = index["entries"]
    if args.key is not None:
        what, found = "key %s" % json.dumps(args.key), [e for e in entries if (e["key"] or "").lower() == args.key.lower()]
    elif args.status is not None:
        what, found = "status %s" % json.dumps(args.status), [e for e in entries if (e["status"] or MISSING).lower() == args.status.lower()]
    elif args.assignee is not None:
        what, found = "assignee %s" % json.dumps(args.assignee), [e for e in entries if (e["assignee"] or MISSING) == args.assignee]
    else:
        words = args.text.lower().split()
        what, found = "title words %s" % json.dumps(args.text), [e for e in entries if words and all(w in (e["title"] or "").lower() for w in words)]
    print("LOOKUP by %s, answered from catalog.json." % what)
    print("The catalog matches the records as they are now. It was last written %s ago, by this machine's clock."
          % age_of(os.path.join(out, "catalog.json")))
    print("Found: %d of %d stories." % (len(found), len(entries)))
    for e in found:
        print("  id %s  key %s  status %s  assignee %s  last update %s"
              % (e["id"], e["key"] or MISSING, e["status"] or MISSING, e["assignee"] or MISSING, e["updated"] or MISSING))
        print("      title: %s" % (json.dumps(e["title"]) if e["title"] else MISSING))
        print("      record: %s/%s%s" % (os.path.basename(os.path.normpath(records)), e["file"],
                                         "   GAP: no %s" % ", no ".join(e["gaps"]) if e["gaps"] else ""))
    if found:
        print("Titles are quoted text from the records. For what a story holds, read its record.")
    return 0 if found else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build, check and look things up in the catalog of local Jira story records.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check", "lookup"):
        sub = commands.add_parser(name)
        sub.add_argument("--records", default=DEFAULT_RECORDS, help="the folder of story records")
        sub.add_argument("--out", default=DEFAULT_OUT, help="the folder the catalog files are in")
        if name == "lookup":
            how = sub.add_mutually_exclusive_group(required=True)
            how.add_argument("--key")
            how.add_argument("--status")
            how.add_argument("--assignee", help="a Jira account id, or 'unassigned'")
            how.add_argument("--text", help="words that must all be in the title")
    args = parser.parse_args(argv)
    records, out = os.path.abspath(args.records), os.path.abspath(args.out)
    try:
        if args.command == "build":
            return cmd_build(records, out)
        if args.command == "check":
            return cmd_check(records, out)
        return cmd_lookup(records, out, args)
    except Stop as stop:
        print("STOPPED: %s." % stop)
        return 2


if __name__ == "__main__":
    sys.exit(main())
