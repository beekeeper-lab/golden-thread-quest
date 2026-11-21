#!/usr/bin/env python3
"""Preview-then-confirm writer for the base-camp-write-preview quest.

Makes changes to a simulated story board (see board.py), which is one local
JSON file. The rules it follows are in participant/context/write-preview-rules.md.

    writer.py preview --board BOARD.json --change CHANGE.json

Shows everything the change file would write, saves that preview beside the
board, and stops. It never writes to the board.

A change file names the board and lists the changes:

    {
      "board": "DEMO",
      "changes": [
        {"action": "create",
         "fields": {"title": "...", "description": "...", "status": "todo"}},
        {"action": "update", "id": "DEMO-3",
         "fields": {"title": "..."}}
      ]
    }

A create gives all three fields. An update gives only the fields it changes.

    writer.py confirm --board BOARD.json --change CHANGE.json \
                      --fingerprint CODE --confirmed-by "Your name"

Writes the changes of one preview, named by its fingerprint. Before writing it
works the change out again from the change file and the board as they are
now, and refuses unless that is exactly what the preview showed. It also
refuses a preview that is older than 15 minutes, one that has been used, and
one whose saved record has been altered.

There is no option that writes without a fingerprint. --pretend-minutes-later N
is for tests: it moves the workflow's idea of "now" forward by N minutes, so
it can make a preview look older. It cannot make one look newer.

Previews are saved in BOARD.json.previews/, one file each, named by fingerprint.
Each write leaves a record in BOARD.json.written/, also named by fingerprint.

Exit codes: 0 done; 1 refused, with the reason. A refusal writes nothing.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board as boards  # noqa: E402

LIMIT_MINUTES = 15
WRITABLE = ("title", "description", "status")
SECRET_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey", "credential", "auth")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"


class Refused(Exception):
    """Nothing is done. The message is the reason, in plain words."""


# ---------------------------------------------------------------- reading


def no_repeats(pairs):
    names = [name for name, _ in pairs]
    for name in names:
        if names.count(name) > 1:
            raise Refused("the change file gives the name '%s' twice in one place" % name)
    return dict(pairs)


def read_change_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=no_repeats)
    except FileNotFoundError:
        raise Refused("there is no change file at %s" % path)
    except ValueError:
        raise Refused("the change file is not JSON")


def check_fields(fields, where):
    """The fields of one change: known names, text values, nothing secret."""
    if not isinstance(fields, dict) or not fields:
        raise Refused("%s has no fields to write" % where)
    for name, value in fields.items():
        if any(word in name.lower() for word in SECRET_WORDS):
            raise Refused("%s has a field named like a secret ('%s'). A preview must not hold a "
                          "credential, so no preview is made" % (where, name))
        if name not in WRITABLE:
            raise Refused("%s has a field the board does not have: '%s'" % (where, name))
        if not isinstance(value, str):
            raise Refused("%s: the value of '%s' is not text" % (where, name))
        if name != "description" and "\n" in value:
            raise Refused("%s: the value of '%s' has a line break" % (where, name))
        if any(ord(ch) < 32 and ch != "\n" for ch in value) or "\x7f" in value:
            raise Refused("%s: the value of '%s' has a character that cannot be shown" % (where, name))
        if name == "title" and not value.strip():
            raise Refused("%s: the title is empty" % where)
        if name == "status" and value not in boards.STATUSES:
            raise Refused("%s: the status is not todo, doing or done" % where)


def build_proposal(change, board):
    """Turn a change file into the full list of what would be written.

    This is the one place that decides what a change means. The preview shows
    its result, and nothing else is ever written.
    """
    if not isinstance(change, dict) or set(change) != {"board", "changes"}:
        raise Refused("the change file must have exactly 'board' and 'changes'")
    if change["board"] != board["board"]:
        raise Refused("the change file is for board '%s' but this board is '%s'"
                      % (change["board"], board["board"]))
    if not isinstance(change["changes"], list) or not change["changes"]:
        raise Refused("the change file lists no changes")
    by_id = {story["id"]: story for story in board["stories"]}
    next_number = board["next_number"]
    updated = set()
    steps = []
    for position, item in enumerate(change["changes"], 1):
        where = "change %d" % position
        if not isinstance(item, dict) or item.get("action") not in ("create", "update"):
            raise Refused("%s: the action must be 'create' or 'update'" % where)
        if item["action"] == "create":
            if set(item) != {"action", "fields"}:
                raise Refused("%s: a create has exactly 'action' and 'fields'" % where)
            check_fields(item["fields"], where)
            if set(item["fields"]) != set(WRITABLE):
                raise Refused("%s: a create must give title, description and status" % where)
            steps.append({"action": "create", "id": "%s-%d" % (board["board"], next_number),
                          "fields": {name: item["fields"][name] for name in WRITABLE}})
            next_number += 1
        else:
            if set(item) != {"action", "id", "fields"}:
                raise Refused("%s: an update has exactly 'action', 'id' and 'fields'" % where)
            story = by_id.get(item["id"]) if isinstance(item["id"], str) else None
            if story is None:
                raise Refused("%s: there is no story with that id on the board" % where)
            if item["id"] in updated:
                raise Refused("%s: story %s is updated twice in one change file" % (where, item["id"]))
            updated.add(item["id"])
            check_fields(item["fields"], where)
            fields = {}
            for name in WRITABLE:
                if name in item["fields"]:
                    if item["fields"][name] == story[name]:
                        raise Refused("%s: the %s given for %s is what it already is"
                                      % (where, name, item["id"]))
                    fields[name] = {"now": story[name], "after": item["fields"][name]}
            steps.append({"action": "update", "id": item["id"], "title_now": story["title"], "fields": fields})
    return {"board": board["board"], "stories_now": len(board["stories"]), "steps": steps}


# ---------------------------------------------------------------- fingerprint


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fingerprint_of(proposal, board_fingerprint, made_at):
    """One code for: these changes, against this board, previewed at this time."""
    text = canonical({"proposal": proposal, "board_fingerprint": board_fingerprint, "made_at": made_at})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short(fingerprint):
    return fingerprint[:12]


# ---------------------------------------------------------------- showing


def plural(count, one, many):
    return "%d %s" % (count, one if count == 1 else many)


def show_value(label, value, indent):
    """Print a value whole. A value of several lines keeps every line."""
    lines = value.split("\n")
    print("%s%s%s" % (indent, label, lines[0]))
    for line in lines[1:]:
        print("%s%s%s" % (indent, " " * len(label), line))


def render(proposal, board_path):
    steps = proposal["steps"]
    creates = sum(1 for step in steps if step["action"] == "create")
    updates = len(steps) - creates
    kinds = []
    if creates:
        kinds.append(plural(creates, "new story", "new stories"))
    if updates:
        kinds.append(plural(updates, "story updated", "stories updated"))
    print("%s to board %s (%s, file %s):"
          % (plural(len(steps), "change", "changes"), proposal["board"], boards.SYSTEM, board_path))
    print("  %s." % ", ".join(kinds))
    print("  Of the %s on the board now, %d %s left alone."
          % (plural(proposal["stories_now"], "story", "stories"), proposal["stories_now"] - updates,
             "is" if proposal["stories_now"] - updates == 1 else "are"))
    for number, step in enumerate(steps, 1):
        print("")
        if step["action"] == "create":
            print("Change %d of %d: CREATE a new story" % (number, len(steps)))
            print("    The board will give it the id %s." % step["id"])
            for name in WRITABLE:
                show_value("%-13s" % (name + ":"), step["fields"][name], "    ")
        else:
            print('Change %d of %d: UPDATE story %s ("%s")' % (number, len(steps), step["id"], step["title_now"]))
            for name, value in step["fields"].items():
                show_value("%-13snow:    " % (name + ":"), value["now"], "    ")
                show_value("%-13safter:  " % "", value["after"], "    ")
            kept = [name for name in WRITABLE if name not in step["fields"]]
            if kept:
                print("    Not changed: %s." % ", ".join(kept))


# ---------------------------------------------------------------- commands


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def previews_dir(board_path):
    return board_path + ".previews"


def cmd_preview(args):
    board = boards.load(args.board)
    proposal = build_proposal(read_change_file(args.change), board)
    made = now_utc()
    expires = made + datetime.timedelta(minutes=LIMIT_MINUTES)
    made_at = made.strftime(TIME_FORMAT)
    board_fingerprint = boards.fingerprint(board)
    fingerprint = fingerprint_of(proposal, board_fingerprint, made_at)

    os.makedirs(previews_dir(args.board), exist_ok=True)
    record_path = os.path.join(previews_dir(args.board), short(fingerprint) + ".json")
    if os.path.exists(record_path):
        raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": fingerprint, "made_at": made_at, "expires_at": expires.strftime(TIME_FORMAT),
                   "board_fingerprint": board_fingerprint, "proposal": proposal, "state": "open"},
                  f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("PREVIEW. Nothing has been written.")
    print("")
    render(proposal, args.board)
    print("")
    print("Fingerprint of this preview: %s" % short(fingerprint))
    print("Made:    %s" % made_at)
    print("Expires: %s (%d minutes after it was made)" % (expires.strftime(TIME_FORMAT), LIMIT_MINUTES))
    print("")
    print("Nothing has been written. The board is as it was.")
    print("To make these changes, a person who has read this preview confirms it by its fingerprint.")
    return 0


def describe_difference(shown, now, board_changed):
    """Say in plain words how the change now differs from the preview."""
    lines = []
    if board_changed:
        lines.append("the board has changed since the preview was made")
    if len(shown["steps"]) != len(now["steps"]):
        lines.append("the preview showed %s, the change file now has %d"
                     % (plural(len(shown["steps"]), "change", "changes"), len(now["steps"])))
    for number, (a, b) in enumerate(zip(shown["steps"], now["steps"]), 1):
        if (a["action"], a["id"]) != (b["action"], b["id"]):
            lines.append("change %d was %s %s in the preview and is now %s %s"
                         % (number, a["action"].upper(), a["id"], b["action"].upper(), b["id"]))
        else:
            names = [name for name in WRITABLE if a["fields"].get(name) != b["fields"].get(name)]
            if names:
                lines.append("change %d (%s %s): %s differs from the preview"
                             % (number, a["action"].upper(), a["id"], ", ".join(names)))
    return lines


def read_preview_record(board_path, code):
    path = os.path.join(previews_dir(board_path), code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        made = datetime.datetime.strptime(record["made_at"], TIME_FORMAT)
        genuine = fingerprint_of(record["proposal"], record["board_fingerprint"], record["made_at"])
        state = record["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s for this board. "
                      "Make a preview, read it, and confirm that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    # The fingerprint is worked out from the record's contents. If the record
    # was edited after it was made, the two no longer agree.
    if genuine != record.get("fingerprint") or short(genuine) != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, record, made, state


def cmd_confirm(args):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("a confirmation must name the fingerprint of the preview it approves. "
                      "There is no way to confirm without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name or any(ord(ch) < 32 for ch in name):
        raise Refused("a confirmation must give the name of the person confirming")

    record_path, record, made, state = read_preview_record(args.board, code)
    written_path = os.path.join(args.board + ".written", code + ".json")
    if state != "open" or os.path.exists(written_path):
        raise Refused("the preview %s has already been confirmed and written. "
                      "A fingerprint is used once" % code)

    now = now_utc()
    if args.pretend_minutes_later:
        print("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
        now += datetime.timedelta(minutes=args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview has expired. It was made %d minutes ago and the limit is %d. "
                      "Make a new preview and read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    # Work the change out again, from the change file and the board as they are now.
    board = boards.load(args.board)
    before = boards.fingerprint(board)
    try:
        proposal = build_proposal(read_change_file(args.change), board)
    except Refused as problem:
        raise Refused("the change is not the one that was previewed: it can no longer be made at all "
                      "(%s). Make a new preview and read it" % problem)
    differences = describe_difference(record["proposal"], proposal, before != record["board_fingerprint"])
    if differences or proposal != record["proposal"]:
        raise Refused("the change is not the one that was previewed: %s. "
                      "Make a new preview and read it" % ("; ".join(differences) or "it differs"))

    # Everything matches. Write exactly the steps the preview showed.
    by_id = {story["id"]: story for story in board["stories"]}
    done = []
    for step in proposal["steps"]:
        if step["action"] == "create":
            assert step["id"] == "%s-%d" % (board["board"], board["next_number"])
            board["stories"].append({"id": step["id"], **step["fields"]})
            board["next_number"] += 1
            done.append("CREATED %s  (title, description, status)" % step["id"])
        else:
            for field, value in step["fields"].items():
                by_id[step["id"]][field] = value["after"]
            done.append("UPDATED %s  (%s)" % (step["id"], ", ".join(step["fields"])))
    boards.save(args.board, board)
    after = boards.fingerprint(board)

    confirmed_at = now_utc().strftime(TIME_FORMAT)
    os.makedirs(args.board + ".written", exist_ok=True)
    with open(written_path, "w", encoding="utf-8") as f:
        json.dump({"fingerprint": record["fingerprint"], "confirmed_by": name, "confirmed_at": confirmed_at,
                   "preview_made_at": record["made_at"], "board_fingerprint_before": before,
                   "board_fingerprint_after": after, "written": proposal["steps"]},
                  f, indent=2, ensure_ascii=False)
        f.write("\n")
    record["state"] = "written"
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print("CONFIRMED. The change file and the board were checked against preview %s, and they match." % code)
    print("")
    print("WRITTEN to board %s (%s, file %s): %s."
          % (board["board"], boards.SYSTEM, args.board, plural(len(done), "change", "changes")))
    for number, line in enumerate(done, 1):
        print("  %d. %s" % (number, line))
    print("")
    print("Confirmed by: %s (the name given with the confirmation)" % name)
    print("Confirmed at: %s" % confirmed_at)
    print("Preview:      %s, made %s" % (code, record["made_at"]))
    print("Record of this write: %s" % written_path)
    return 0


def minutes_forward(text):
    """The test clock only goes forward: a whole number of minutes, 0 or more."""
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number of minutes, 0 or more")
    return int(text)


def main():
    parser = argparse.ArgumentParser(description="Preview, then confirm, a change to the simulated story board.")
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview", help="show what a change file would write, and stop")
    preview.add_argument("--board", required=True)
    preview.add_argument("--change", required=True)
    confirm = commands.add_parser("confirm", help="write the changes of one preview, named by its fingerprint")
    confirm.add_argument("--board", required=True)
    confirm.add_argument("--change", required=True)
    confirm.add_argument("--fingerprint")
    confirm.add_argument("--confirmed-by")
    confirm.add_argument("--pretend-minutes-later", type=minutes_forward, default=0,
                         metavar="N", help="tests only: move 'now' forward by N minutes")
    args = parser.parse_args()
    try:
        return cmd_confirm(args) if args.command == "confirm" else cmd_preview(args)
    except Refused as refusal:
        print("REFUSED: %s." % refusal)
    except boards.BoardError as err:
        print("REFUSED: the board cannot be used: %s." % err)
    print("Nothing has been written.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
