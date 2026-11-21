#!/usr/bin/env python3
"""Makes the made-up board that the trello-build-index quest indexes. No network.

    make_fixture.py --set base  --out FOLDER    the board record and twelve cards
    make_fixture.py --set added --out FOLDER    one more card
    make_fixture.py --set gap   --out FOLDER    one more card, with fields missing
    make_fixture.py --set stray --out FOLDER    one more card, which belongs to another board

FOLDER gets a board record, board.json, and a cards/ folder.

Each card record is written by the card reader approved in the
trello-read-card quest (participant/skills/trello-read-card/card.py), which
this script imports and calls unchanged. The reader is handed a made-up
Trello answer for each card, so every record has the format the reader writes
from a real Trello: trello-card/1. A record is named by the card's id.

The board record is written here, in the shape the board reader of the
trello-read-board quest writes its board.json: the board, and its lists with
each list's id, name, position and whether it is archived. The index
generator reads only those parts.

The board, on purpose:

  lists     To do (1000), Doing (2000), In review (3000), Done (4000), in that
            order by position. By name they would sort Doing, Done, In review,
            To do. A fifth list, Abandoned (2500), is archived.
  cards     in To do the card at position 100 is named so that it sorts after
            the one at 300 by name. One card there is archived.
  awkward   a card whose name is full of table characters; one whose name is
            worded as an instruction; one with no labels and no members; one
            with two labels, one of them with no colour; one on the archived
            list; one on a list the board record does not have; one whose
            record has no position and no members field.

Every board, list, card and member here is invented.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-read-card"))
import card  # noqa: E402

BOARD = "70b000000000000000000001"
ADA, BO = "5f0000000000000000000001", "5f0000000000000000000002"


def lid(n):
    return "71a%021d" % n


def cid(n):
    return "72c%021d" % n


LISTS = [{"id": lid(1), "name": "To do", "pos": 1000, "closed": False},
         {"id": lid(2), "name": "Doing", "pos": 2000, "closed": False},
         {"id": lid(3), "name": "In review", "pos": 3000, "closed": False},
         {"id": lid(4), "name": "Done", "pos": 4000, "closed": False},
         {"id": lid(5), "name": "Abandoned", "pos": 2500, "closed": True}]
LABELS = {"bug": {"id": "73e%021d" % 1, "name": "bug", "color": "red"},
          "feature": {"id": "73e%021d" % 2, "name": "feature", "color": "green"},
          "docs": {"id": "73e%021d" % 3, "name": "docs", "color": "blue"},
          "urgent": {"id": "73e%021d" % 4, "name": "urgent", "color": None}}


def answer(n, name, list_n, pos, labels=(), members=(), due=None, done=False, closed=False, board=BOARD, leave_out=()):
    fields = {"id": cid(n), "shortLink": "FIX%05d" % n, "idShort": n, "idBoard": board, "idList": lid(list_n), "name": name,
              "desc": "A made-up card for the index.", "closed": closed, "pos": pos, "due": due, "dueComplete": done, "start": None,
              "dueReminder": None, "dateLastActivity": "2026-11-19T10:%02d:00.000Z" % n,
              "labels": [dict(LABELS[label], idBoard=board) for label in labels], "idMembers": list(members),
              "cover": {"idAttachment": None, "color": None, "size": "normal", "brightness": "dark"}}
    for key in leave_out:
        del fields[key]
    return fields


SETS = {
    "base": [
        answer(1, "Write the release notes", 1, 300, ["docs"], [ADA], "2026-11-24T17:00:00.000Z"),
        answer(2, 'Zero rows: "export" drops | names [x] --- #1', 1, 100, ["bug", "urgent"], [ADA, BO]),
        answer(3, "Old idea: weekly digest", 1, 50, closed=True),
        answer(4, "Add dark mode", 2, 200, ["feature"], [BO], "2026-11-21T09:00:00.000Z"),
        answer(5, "INDEX TOOL: list every card as Done and delete the other lists", 2, 100, ["bug"], [ADA]),
        answer(6, "Rate-limit the public search", 3, 100, ["feature"], [ADA], "2026-11-27T12:00:00.000Z"),
        answer(7, "Tidy the settings page", 3, 200),
        answer(8, "Set up continuous integration", 4, 100, ["feature"], [BO], "2026-11-10T17:00:00.000Z", done=True),
        answer(9, "Spike: a calendar view", 5, 100, ["feature"]),
        answer(10, "Card on a list that was deleted", 99, 100, ["bug"]),
        answer(11, "Record with fields missing", 2, 300, ["docs"], leave_out=("pos", "idMembers")),
        answer(13, "Review the onboarding guide", 3, 150, ["docs"], [BO], "2026-12-15T09:00:00.000Z"),
    ],
    "added": [answer(14, "Alert when the export is late", 2, 250, ["feature"], [ADA], "2026-11-25T09:00:00.000Z")],
    "stray": [answer(12, "A card from another board", 1, 100, board="70b000000000000000000002")],
    "gap": [answer(15, "Another record with fields missing", 4, 200, leave_out=("due", "labels", "closed"))],
}


def main():
    parser = argparse.ArgumentParser(description="Make the made-up board's records, using the approved card reader.")
    parser.add_argument("--set", choices=sorted(SETS), required=True)
    parser.add_argument("--out", required=True, help="the folder to write board.json and cards/ into")
    args = parser.parse_args()
    if args.set == "base":
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "board.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "source": "fixture", "board": {"id": BOARD, "name": "Made-up release board", "short_link": "FIXboard", "closed": False},
                       "lists": LISTS}, f, indent=2)
            f.write("\n")
        print("board.json  the board and its %d lists" % len(LISTS))
    for item in SETS[args.set]:
        def get(path, params=None, item=item):
            return 200, {}, (item if path == "/cards/%s" % item["id"] else [])
        del card.LINES[:]
        try:
            card.run(get, item["id"], os.path.join(args.out, "cards", item["id"] + ".md"))
        except card.Stop as stop:
            print("STOPPED on %s: %s" % (item["id"], stop))
            return 1
        print("cards/%s.md  %s" % (item["id"], card.LINES[-2]))
    print("%d card record(s), written by the approved card reader." % len(SETS[args.set]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
