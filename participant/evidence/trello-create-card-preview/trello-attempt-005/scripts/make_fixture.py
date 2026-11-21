#!/usr/bin/env python3
"""Makes the local side of the card-creation preview fixture. No network.

    make_fixture.py [--out FOLDER]

FOLDER is participant/context/trello/new-card unless --out says otherwise. It gets:

    fixture/boards/platform-team/   board.json, cards/ and the index of that board
    fixture/boards/support-team/    the same for the second board
    refused/                        five drafts, each the main draft with one thing wrong
    not-ready/duplicate.md          a draft that duplicates a card on the support board
    decided/duplicate.md            the same draft with a person's decision recorded

The boards are a local copy of the made-up Trello in
participant/skills/trello-create-card-preview/fake_trello.py. Each card
record is written by the card reader approved in the trello-read-card quest,
reading the fake as it would read Trello. Each index is built by the
generator approved in the trello-build-index quest. Neither is changed.

The drafts in refused/ are made from draft.md, which is written by hand, by
changing one line each. draft.md, sources/notes.md and
sandbox-allowlist.json are not made by this script and are not touched.

Every board, list, card, label and member here is invented.
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-read-card"))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-build-index"))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-create-card-preview"))
import card  # noqa: E402
import index  # noqa: E402
import fake_trello as fake  # noqa: E402

FOLDERS = {fake.PLATFORM: "platform-team", fake.SUPPORT: "support-team"}

# (file, what is wrong, the line of draft.md to replace, what to replace it with)
REFUSED = [
    ("list-on-another-board.md", "the list is on the support board, not the stated board",
     'list: "%s"' % fake.TO_DO, 'list: "%s"' % fake.INBOX),
    ("missing-list.md", "no list has this id",
     'list: "%s"' % fake.TO_DO, 'list: "%s"' % fake.lid(99)),
    ("archived-list.md", "the list is the archived one, which is first by position",
     'list: "%s"' % fake.TO_DO, 'list: "%s"' % fake.OLD_IDEAS),
    ("unknown-label.md", "the board has no label named urgent",
     'labels: ["feature"]', 'labels: ["feature", "urgent"]'),
    ("member-not-on-board.md", "this member is not on the board",
     'members: ["%s"]' % fake.BO, 'members: ["%s"]' % fake.DEE),
]

DUPLICATE = """---
format: "trello-card-draft/1"
board: "%(board)s"
list: "%(list)s"
position: "top"
name: "Export the customer list as CSV"
labels: ["export"]
members: ["%(bo)s"]
due: "2026-12-04T17:00:00.000Z"
%(decision)s---

# Card draft: Export the customer list as CSV

For the made-up platform team board, list "To do". The made-up support team board already holds a card for this
work under another name. Every board, list, label and member here is invented.

## Description

Admins keep asking support for their customer list. Add an Export button on the customers page that downloads the customer list as a CSV file with the account name, plan and signup date columns. Stream the download so large accounts do not time out.

## Sources

- name: ../sources/notes.md line 16: "export the customer list as CSV"
- description: ../sources/notes.md lines 17-18: "admins keep asking support for their customer list"
- description: ../sources/notes.md line 18: "an Export button on the customers page that downloads the customer list as a CSV file"
- labels: ../sources/notes.md line 19: "Label it export"
- members: ../sources/notes.md line 19: "member %(bo)s"
- due: ../sources/notes.md line 19: "Friday 4 December 2026"
"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    parser = argparse.ArgumentParser(description="Make the local boards and the variant drafts of the preview fixture.")
    parser.add_argument("--out", default=os.path.join(ROOT, "participant", "context", "trello", "new-card"))
    out = os.path.abspath(parser.parse_args().out)
    trello = fake.FakeTrello()
    for name in ("fixture", "refused", "not-ready", "decided"):
        shutil.rmtree(os.path.join(out, name), ignore_errors=True)
    for board_id, folder_name in FOLDERS.items():
        board = trello.boards[board_id]
        folder = os.path.join(out, "fixture", "boards", folder_name)
        os.makedirs(os.path.join(folder, "cards"))
        with open(os.path.join(folder, "board.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "source": "fixture", "board": {"id": board["id"], "name": board["name"],
                                                                   "short_link": board["shortLink"], "closed": False},
                       "lists": board["lists"]}, f, indent=2)
            f.write("\n")
        for row in board["cards"]:
            del card.LINES[:]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    card.run(trello.get, row["id"], os.path.join(folder, "cards", row["id"] + ".md"))
            except card.Stop as stop:
                print("STOPPED on %s: %s" % (row["id"], stop))
                return 1
        with contextlib.redirect_stdout(io.StringIO()):
            code = index.main(["build", "--records", folder, "--out", folder])
        if code != 0:
            print("STOPPED: the index of %s could not be built" % folder_name)
            return 1
        print("fixture/boards/%s/  board.json, %d card records read from the fake Trello by the approved card reader, index.md and index.json"
              % (folder_name, len(board["cards"])))
    if any(method != "GET" for method, _, _ in trello.requests):
        print("STOPPED: something other than a GET was sent to the fake")
        return 1

    with open(os.path.join(out, "draft.md"), encoding="utf-8") as f:
        draft = f.read()
    for name, wrong, old, new in REFUSED:
        if draft.count(old) != 1:
            print("STOPPED: draft.md does not hold the line %s once" % old)
            return 1
        text = draft.replace(old, new).replace(": sources/notes.md", ": ../sources/notes.md")
        text = text.replace("\n# Card draft:", "\n> Made from draft.md by scripts/make_fixture.py with one line changed: %s.\n\n# Card draft:" % wrong)
        write(os.path.join(out, "refused", name), text)
    print("refused/  %d drafts, each draft.md with one line changed" % len(REFUSED))
    fields = {"board": fake.PLATFORM, "list": fake.TO_DO, "bo": fake.BO}
    write(os.path.join(out, "not-ready", "duplicate.md"), DUPLICATE % dict(fields, decision=""))
    write(os.path.join(out, "decided", "duplicate.md"),
          DUPLICATE % dict(fields, decision='duplicate_decision: "link"\nduplicate_candidates: ["%s"]\n' % fake.cid(201)))
    print("not-ready/duplicate.md and decided/duplicate.md  the same card, without and with a person's decision")
    return 0


if __name__ == "__main__":
    sys.exit(main())
