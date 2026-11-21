#!/usr/bin/env python3
"""Builds an index of one Trello board from the local card records, and looks cards up in it.

    index.py build   [--records FOLDER] [--out FOLDER]
    index.py check   [--records FOLDER] [--out FOLDER]
    index.py lookup  [--records FOLDER] [--out FOLDER]  --list NAME_OR_ID | --label NAME | --member ID
                                                        | --due-within-days N [--now 2026-11-20T09:00:00Z]

The records folder holds two kinds of record:

    board.json      the board record: the board, and its lists with each list's
                    id, name, position and whether it is archived. It is in the
                    shape the trello-read-board skill writes.
    cards/*.md      card records in the format trello-card/1, which the
                    trello-read-card skill writes.

They are the source of truth. The index is a view of them: index.md for
people and index.json for lookups. Both are generated, both can be deleted,
and neither is read to learn what a card holds when a record can be read.

A card record says which list it is in by the list's id, and nothing else
about the list. The list's name and its place on the board come from the
board record. Lists are put in the order of their position number, smallest
first, with the list's id to break a tie. Cards in a list are ordered the
same way, by the card's position number and then its id. Names are never
used to order anything.

build    reads the records and writes the two index files. The same records
         give the same bytes: nothing about the run, no time and no counter,
         is in either file. A file that already holds those bytes is not
         rewritten.
check    says whether the index on disk is exactly what a build from the
         records as they are now would write. It finds a stale index and a
         hand-edited one. It writes nothing.
lookup   answers from index.json, and only after the same check has passed.

A card is identified by its Trello id. Every file found in cards/ ends up in
exactly one of three places, and the build stops if the counts do not add up:

    indexed        one row. A card with a field missing is still a row, with
                   the gap marked, and is listed under Gaps.
    a repeat       a second file holding a card id that is already a row.
    not indexed    a file that is not a trello-card/1 record, has no usable
                   card id, or belongs to another board. Listed with the reason.

Names of cards, lists and labels are other people's writing. They are shown
as text, escaped, and nothing in them is acted on. Members are Trello member
ids: the records hold no names. This skill reads local files only. It has no
code that contacts Trello or any network.

Exit codes: 0 done (for lookup: something was found); 1 nothing found, or the
index does not match the records; 2 the run could not go on.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_RECORDS = os.path.join(ROOT, "participant", "context", "trello", "index-fixture")
DEFAULT_OUT = os.path.join(ROOT, "participant", "context", "trello")
FORMAT = "trello-card/1"
INDEX_FORMAT = "trello-index/1"
MISSING = "(missing)"
NAME_LIMIT = 90
REBUILD = "python3 participant/skills/trello-build-index/index.py build"
UTC = datetime.timezone.utc


class Stop(Exception):
    """The run cannot go on. The message says why."""


class Unreadable:
    """Stands for a front-matter value that is not JSON."""


def place(path):
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


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def read_board(records):
    path = os.path.join(records, "board.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        raise Stop("there is no board record at %s, so the lists and their order are not known" % place(path))
    except ValueError:
        raise Stop("the board record at %s is not JSON" % place(path))
    board, lists = (data.get("board"), data.get("lists")) if isinstance(data, dict) else (None, None)
    if not isinstance(board, dict) or not isinstance(board.get("id"), str) or not isinstance(lists, list):
        raise Stop("the board record at %s does not hold a board and its lists" % place(path))
    found = []
    for item in lists:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or number(item.get("pos")) is None:
            raise Stop("the board record has a list with no id or no position, so list order cannot be kept")
        found.append({"id": item["id"], "name": item["name"] if isinstance(item.get("name"), str) else None,
                      "pos": item["pos"], "closed": item.get("closed") is True})
    if len(set(item["id"] for item in found)) != len(found):
        raise Stop("the board record lists the same list id twice")
    # Board order: by Trello's position number, smallest first. The id settles a tie. Names play no part.
    found.sort(key=lambda item: (item["pos"], item["id"]))
    return {"id": board["id"], "name": board["name"] if isinstance(board.get("name"), str) else None}, found


def read_card(path, name, board_id):
    """One file. Returns ("row", entry) or ("skip", reason)."""
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
    except UnicodeDecodeError:
        return "skip", "it is not UTF-8 text"
    except OSError:
        return "skip", "it could not be read"
    front = front_matter(text)
    if front is None:
        return "skip", "it has no front matter, so it is not a card record"
    if front.get("format") != FORMAT:
        return "skip", "its format is not %s" % FORMAT
    card_id = front.get("id")
    if not (isinstance(card_id, str) and card_id.isascii() and card_id.isalnum() and len(card_id) <= 32):
        return "skip", "it has no usable card id, so the card cannot be identified"
    if isinstance(front.get("idBoard"), str) and front["idBoard"] != board_id:
        return "skip", "it belongs to another board, %s" % front["idBoard"][:32]

    gaps = []

    def text_of(key, label):
        value = front.get(key)
        if isinstance(value, str) and value.strip():
            return value
        gaps.append(label)
        return None
    title = text_of("name", "name")
    list_id = text_of("idList", "list")
    pos = number(front.get("pos"))
    if pos is None:
        gaps.append("position")
    closed = front.get("closed") if isinstance(front.get("closed"), bool) else None
    if closed is None:
        gaps.append("closed state")
    labels = None
    if isinstance(front.get("labels"), list):
        labels = [{"id": item.get("id") if isinstance(item.get("id"), str) else None,
                   "name": item.get("name") if isinstance(item.get("name"), str) else "",
                   "color": item.get("color") if isinstance(item.get("color"), str) else None}
                  for item in front["labels"] if isinstance(item, dict)]
    else:
        gaps.append("labels")
    members = None
    if isinstance(front.get("idMembers"), list) and all(isinstance(m, str) for m in front["idMembers"]):
        members = list(front["idMembers"])
    else:
        gaps.append("members")
    if "due" not in front or not (front["due"] is None or isinstance(front["due"], str)):
        due, due_known = None, False
        gaps.append("due date")
    else:
        due, due_known = front["due"], True
    if "idBoard" not in front:
        gaps.append("board")
    return "row", {"id": card_id, "short_link": front.get("shortLink") if isinstance(front.get("shortLink"), str) else None,
                   "name": title, "list_id": list_id, "pos": pos, "closed": closed, "labels": labels, "members": members,
                   "due": due, "due_known": due_known, "due_complete": front.get("dueComplete") is True, "file": name, "gaps": gaps}


def scan(records):
    """Everything the index is made from."""
    board, lists = read_board(records)
    folder = os.path.join(records, "cards")
    if not os.path.isdir(folder):
        raise Stop("there is no cards folder at %s" % place(folder))
    names = sorted(name for name in os.listdir(folder) if name.endswith(".md") and os.path.isfile(os.path.join(folder, name)))
    digest = hashlib.sha256()
    with open(os.path.join(records, "board.json"), "rb") as f:
        digest.update(("%s board.json\n" % hashlib.sha256(f.read()).hexdigest()).encode("utf-8"))
    rows, repeats, skipped = {}, [], []
    for name in names:
        path = os.path.join(folder, name)
        with open(path, "rb") as f:
            digest.update(("%s cards/%s\n" % (hashlib.sha256(f.read()).hexdigest(), name)).encode("utf-8"))
        kind, found = read_card(path, name, board["id"])
        if kind == "skip":
            skipped.append({"file": name, "reason": found})
        elif found["id"] in rows:
            repeats.append({"id": found["id"], "file": name, "kept": rows[found["id"]]["file"]})
        else:
            rows[found["id"]] = found
    known = {item["id"] for item in lists}
    for entry in rows.values():
        if entry["list_id"] is not None and entry["list_id"] not in known:
            entry["gaps"].append("list in the board record")
    # Cards in list order: open before archived, then by position number, then by id. A card with no position goes last.
    cards = sorted(rows.values(), key=lambda e: (e["closed"] is True, e["pos"] is None, e["pos"] or 0, e["id"]))
    counts = {"files": len(names), "indexed": len(cards), "repeats": len(repeats), "not_indexed": len(skipped)}
    if counts["indexed"] + counts["repeats"] + counts["not_indexed"] != counts["files"]:
        raise Stop("%d files were found and %d were accounted for, so a card would have been lost"
                   % (counts["files"], counts["indexed"] + counts["repeats"] + counts["not_indexed"]))
    return {"format": INDEX_FORMAT, "records_fingerprint": digest.hexdigest(), "board": board, "lists": lists, "counts": counts,
            "cards": cards, "repeats": repeats, "not_indexed": skipped}


# ---------------------------------------------------------------- writing the index


def escape(text):
    """Text from a record, made safe to sit in a Markdown table cell or a heading as plain text."""
    text = " ".join(str(text).split())
    if len(text) > NAME_LIMIT:
        text = text[:NAME_LIMIT - 1].rstrip() + "…"
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for ch in "\\`*_[]|#~":
        text = text.replace(ch, "\\" + ch)
    return text


def cell(value):
    return MISSING if value is None else escape(value)


def label_text(label):
    return "%s (%s)" % (escape(label["name"]) if label["name"] else "no name", escape(label["color"]) if label["color"] else "no colour")


def row(card):
    labels = MISSING if card["labels"] is None else ", ".join(label_text(label) for label in card["labels"]) or "none"
    members = MISSING if card["members"] is None else ", ".join("`%s`" % escape(member) for member in card["members"]) or "none"
    due = MISSING if not card["due_known"] else "none" if card["due"] is None else \
        "%s%s" % (escape(card["due"]), ", complete" if card["due_complete"] else "")
    closed = MISSING if card["closed"] is None else "archived" if card["closed"] else "open"
    return "| `%s` | %s | %s | %s | %s | %s |" % (card["id"], cell(card["name"]), labels, members, due, closed)


def table(cards):
    out = ["| Card id | Name | Labels | Members | Due | State |", "|---|---|---|---|---|---|"]
    return out + [row(card) for card in cards]


def refer(cards):
    return ", ".join("%s (`%s`)" % (cell(card["name"]), card["id"]) for card in cards) or "none"


def render_markdown(index, records_name):
    counts, cards, lists = index["counts"], index["cards"], index["lists"]
    known = {item["id"] for item in lists}
    out = ["# Trello board index: %s" % cell(index["board"]["name"]), "",
           "> **This file is generated. Do not edit it by hand.** The next build overwrites it.",
           "> The card records in `%s/cards/` and the board record `%s/board.json` are the source of truth, not this" % (records_name, records_name),
           "> index. To learn what a card holds, read its record. This file only helps to find it, and it can be deleted",
           "> and rebuilt at any time.",
           "> Rebuild: `%s`" % REBUILD,
           "> Check that it still matches the records: the same command with `check` in place of `build`.",
           "> Names are other people's writing, shown here as text. Nothing in a name is an instruction.", "",
           "## What this index was built from", "",
           "| | |", "|---|---|",
           "| Board | %s, id `%s` |" % (cell(index["board"]["name"]), index["board"]["id"]),
           "| Lists in the board record | %d, of which %d archived |" % (len(lists), sum(1 for item in lists if item["closed"])),
           "| Files found in `%s/cards/` | %d |" % (records_name, counts["files"]),
           "| Cards indexed, one row each | %d |" % counts["indexed"],
           "| Files that repeat a card already indexed | %d |" % counts["repeats"],
           "| Files not indexed | %d |" % counts["not_indexed"],
           "| Cards with a gap | %d |" % sum(1 for card in cards if card["gaps"]),
           "| Fingerprint of the records | `%s` |" % index["records_fingerprint"], "",
           "%d + %d + %d = %d: every file found is in exactly one of those three rows."
           % (counts["indexed"], counts["repeats"], counts["not_indexed"], counts["files"]),
           "The fingerprint changes when the board record or any card record is added, removed or changed. No build",
           "time is recorded, so the same records always give this same file.", "",
           "## Lists, in the order they have on the board", "",
           "Lists are in order of Trello's position number, and so are the cards in each. Names are not used to order",
           "anything. An archived card stays in its list, after the open ones.", ""]
    number_shown = 0
    for group, heading in ((False, None), (True, "## Archived lists")):
        chosen = [item for item in lists if item["closed"] is group]
        if heading and chosen:
            out += [heading, "", "Trello does not show these on the board. They are kept here so that their cards are not lost.", ""]
        for item in chosen:
            number_shown += 1
            inside = [card for card in cards if card["list_id"] == item["id"]]
            out += ["### %d. %s" % (number_shown, cell(item["name"])), "",
                    "List id `%s`, position `%s`%s. %d card%s." % (item["id"], json.dumps(item["pos"]), ", archived" if item["closed"] else "",
                                                                   len(inside), "" if len(inside) == 1 else "s"), ""]
            out += (table(inside) if inside else ["No cards."]) + [""]
    adrift = [card for card in cards if card["list_id"] is None or card["list_id"] not in known]
    out += ["## Cards whose list is not known", "",
            "A card here names a list the board record does not have, or names none. Its row is here and nowhere else.", ""]
    if adrift:
        out += ["| Card id | Name | Labels | Members | Due | State | List id in the record |", "|---|---|---|---|---|---|---|"]
        out += [row(card) + " %s |" % ("`%s`" % escape(card["list_id"]) if card["list_id"] else MISSING) for card in adrift]
    else:
        out += ["None."]
    out += ["", "## By label", ""]
    labels = {}
    for card in cards:
        for label in card["labels"] or []:
            labels.setdefault((label["name"], label["color"] or ""), []).append(card)
    out += ["- **%s** (%d): %s" % (label_text({"name": key[0], "color": key[1] or None}), len(found), refer(found))
            for key, found in sorted(labels.items())] or ["No card has a label."]
    out += ["- **no label** (%d): %s" % (len(found), refer(found)) for found in [[card for card in cards if card["labels"] == []]] if found]
    out += ["", "## By member", "", "Members are Trello member ids. The records hold no names.", ""]
    members = {}
    for card in cards:
        for member in card["members"] or []:
            members.setdefault(member, []).append(card)
    out += ["- **`%s`** (%d): %s" % (escape(member), len(found), refer(found)) for member, found in sorted(members.items())] or ["No card has a member."]
    out += ["- **no member** (%d): %s" % (len(found), refer(found)) for found in [[card for card in cards if card["members"] == []]] if found]
    out += ["", "## Gaps", "", "A card listed here has its row above, with `%s` where its record has no value." % MISSING,
            "\"none\" is not a gap: it means the record says the card has no label, no member or no due date.", ""]
    out += ["- %s (`%s`), record `cards/%s`: no %s" % (cell(card["name"]), card["id"], card["file"], ", no ".join(card["gaps"]))
            for card in cards if card["gaps"]] or ["None."]
    out += ["", "## Files that repeat a card", ""]
    out += ["- `cards/%s` holds card id `%s`, which is already indexed from `cards/%s`. One of the two should be removed."
            % (item["file"], item["id"], item["kept"]) for item in index["repeats"]] or ["None."]
    out += ["", "## Files not indexed", ""]
    out += ["- `cards/%s`: %s." % (item["file"].replace("`", "'"), escape(item["reason"])) for item in index["not_indexed"]] or ["None."]
    return "\n".join(out) + "\n"


def render(index, records_name):
    """Both index files as bytes. This is the only place that decides what they hold."""
    markdown = render_markdown(index, records_name)
    rows = len(re.findall(r"^\| `[0-9A-Za-z]+` \|", markdown.split("\n## By label\n")[0], re.M))
    if rows != index["counts"]["indexed"]:
        raise Stop("%d cards were indexed and the index has %d rows" % (index["counts"]["indexed"], rows))
    data = dict(index, note="Generated. The card records and the board record are the source of truth. Do not edit by hand.")
    return {"index.md": markdown.encode("utf-8"),
            "index.json": (json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")}


def on_disk(out, name):
    try:
        with open(os.path.join(out, name), "rb") as f:
            return f.read()
    except OSError:
        return None


def matches(out, files):
    """Which index files on disk are not what a build would write now."""
    return [name for name in sorted(files) if on_disk(out, name) != files[name]]


# ---------------------------------------------------------------- the commands


def cmd_build(records, out):
    index = scan(records)
    files = render(index, os.path.basename(os.path.normpath(records)))
    counts = index["counts"]
    print("BOARD INDEX BUILD. Reads local files only.")
    print("Records folder: %s" % place(records))
    print("Board: %s, id %s. Lists in board order: %s." % (json.dumps(index["board"]["name"]), index["board"]["id"],
                                                          ", ".join("%s%s" % (json.dumps(item["name"]), " (archived)" if item["closed"] else "") for item in index["lists"])))
    print("Files found in cards/: %d" % counts["files"])
    print("  indexed, one row each:               %d" % counts["indexed"])
    print("  repeating a card already indexed:    %d" % counts["repeats"])
    print("  not indexed:                         %d" % counts["not_indexed"])
    print("  accounted for: %d of %d" % (counts["indexed"] + counts["repeats"] + counts["not_indexed"], counts["files"]))
    gaps = [card for card in index["cards"] if card["gaps"]]
    print("Cards with a gap: %d" % len(gaps))
    for card in gaps:
        print("  GAP  card %s (cards/%s): no %s" % (card["id"], card["file"], ", no ".join(card["gaps"])))
    for item in index["repeats"]:
        print("  REPEAT  cards/%s holds card %s, already indexed from cards/%s" % (item["file"], item["id"], item["kept"]))
    for item in index["not_indexed"]:
        print("  NOT INDEXED  cards/%s: %s" % (item["file"], item["reason"]))
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
        print("%-11s %s, %d bytes, SHA-256 %s" % (name + ":", state, len(files[name]), hashlib.sha256(files[name]).hexdigest()))
    return 0


def cmd_check(records, out, quiet=False):
    files = render(scan(records), os.path.basename(os.path.normpath(records)))
    wrong = matches(out, files)
    if not wrong:
        if not quiet:
            print("CHECK: index.md and index.json are exactly what a build from the records would write now.")
        return 0
    print("CHECK FAILED: %s %s not what a build from the records would write now."
          % (" and ".join(wrong), "is" if len(wrong) == 1 else "are"))
    print("Either a record was added, removed or changed since the last build, or the index was edited by hand.")
    print("The records are the source of truth. Rebuild: %s" % REBUILD)
    return 1


def parse_time(text):
    if not isinstance(text, str):
        return None
    for form in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.datetime.strptime(text, form).replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


def age_of(path):
    seconds = max(0, int(datetime.datetime.now().timestamp() - os.path.getmtime(path)))
    for size, word in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= size:
            return "%d %s%s" % (seconds // size, word, "" if seconds // size == 1 else "s")
    return "under a minute"


def cmd_lookup(records, out, args):
    if cmd_check(records, out, quiet=True) != 0:
        print("No answer is given from an index that does not match the records.")
        return 1
    with open(os.path.join(out, "index.json"), encoding="utf-8") as f:
        index = json.load(f)
    cards, lists = index["cards"], index["lists"]
    names = {item["id"]: item["name"] for item in lists}
    if args.list is not None:
        wanted = [item["id"] for item in lists if args.list == item["id"] or (item["name"] or "").lower() == args.list.lower()]
        what, found = "list %s" % json.dumps(args.list), [card for card in cards if card["list_id"] in wanted]
        if not wanted:
            print("LOOKUP by %s: the board record has no list with that name or id." % what)
            return 1
    elif args.label is not None:
        what = "label %s" % json.dumps(args.label)
        found = [card for card in cards if any(label["name"].lower() == args.label.lower() for label in card["labels"] or [])]
    elif args.member is not None:
        what, found = "member %s" % json.dumps(args.member), [card for card in cards if args.member in (card["members"] or [])]
    else:
        now = parse_time(args.now) if args.now else datetime.datetime.now(UTC).replace(microsecond=0)
        if now is None:
            raise Stop("--now must be a time in UTC written like 2026-11-20T09:00:00Z")
        end = now + datetime.timedelta(days=args.due_within_days)
        what = "due from %s to %s (%d days), not yet complete, not archived" % (now.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ"), args.due_within_days)
        found = sorted((card for card in cards if parse_time(card["due"]) and now <= parse_time(card["due"]) <= end
                        and not card["due_complete"] and card["closed"] is not True), key=lambda card: (card["due"], card["id"]))
        if not args.now:
            what += ", counted from the computer's clock"
    print("LOOKUP by %s, answered from index.json." % what)
    print("The index matches the records as they are now. It was last written %s ago, by this machine's clock."
          % age_of(os.path.join(out, "index.json")))
    print("Found: %d of %d cards." % (len(found), len(cards)))
    for card in found:
        print("  card %s  list %s  state %s  due %s" % (card["id"], json.dumps(names.get(card["list_id"], "not known")),
                                                      MISSING if card["closed"] is None else "archived" if card["closed"] else "open",
                                                      MISSING if not card["due_known"] else card["due"] or "none"))
        print("      name: %s" % (json.dumps(card["name"]) if card["name"] else MISSING))
        print("      labels: %s   members: %s" % (MISSING if card["labels"] is None else ", ".join(json.dumps(l["name"]) for l in card["labels"]) or "none",
                                                 MISSING if card["members"] is None else ", ".join(card["members"]) or "none"))
        print("      record: cards/%s%s" % (card["file"], "   GAP: no %s" % ", no ".join(card["gaps"]) if card["gaps"] else ""))
    if found:
        print("Names are quoted text from the records. For what a card holds, read its record.")
    return 0 if found else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build, check and look things up in the index of one Trello board's local records.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check", "lookup"):
        sub = commands.add_parser(name)
        sub.add_argument("--records", default=DEFAULT_RECORDS, help="the folder holding board.json and cards/")
        sub.add_argument("--out", default=DEFAULT_OUT, help="the folder the index files are in")
        if name == "lookup":
            how = sub.add_mutually_exclusive_group(required=True)
            how.add_argument("--list", help="a list's name or id")
            how.add_argument("--label", help="a label's name")
            how.add_argument("--member", help="a Trello member id")
            how.add_argument("--due-within-days", type=int, metavar="N", help="cards due in the next N days")
            sub.add_argument("--now", help="the clock value for --due-within-days, in UTC, like 2026-11-20T09:00:00Z")
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
