#!/usr/bin/env python3
"""Simulated story board for the base-camp-write-preview quest.

The "external system" in this quest is one local JSON file. It stands in for a
tool such as Jira or Trello. There is no network, no account and no login.

A board file looks like this:

    {
      "system": "simulated story board",
      "board": "DEMO",
      "next_number": 6,
      "stories": [
        {"id": "DEMO-1", "title": "...", "description": "...", "status": "todo"}
      ]
    }

A story has exactly four fields: id, title, description and status. The status
is one of: todo, doing, done. The board hands out the id when a story is
created (DEMO-6, DEMO-7, ...), so a new story has no id until it is written.

This file is used two ways. The workflow imports it to read and write the
board. A person runs it to look:

    board.py init BOARD.json    make a starting board of five made-up stories
    board.py show BOARD.json    list the stories and print the board's fingerprint

The fingerprint is a code worked out from the whole board. If two fingerprints
are the same, the two boards are the same, story for story and field for
field. It is how a run shows that the board was not changed.
"""
import hashlib
import json
import os
import sys

SYSTEM = "simulated story board"
STATUSES = ("todo", "doing", "done")
STORY_FIELDS = ("id", "title", "description", "status")

STARTING_STORIES = [
    ("Export the weekly report as a file", "Let a team lead save the weekly report to their computer.", "done"),
    ("Show who changed a story last", "On each story, show the name of the last person to edit it.", "doing"),
    ("Search stories by title", "A search box that finds stories whose title holds the words typed.", "todo"),
    ("Warn before closing an unsaved story", "Ask before the page closes if there are edits not yet saved.", "todo"),
    ("Sort the board by last update", "Add a choice to list the most recently changed stories first.", "todo"),
]


class BoardError(Exception):
    """The board file cannot be trusted. The message says why."""


def check(board):
    """Raise BoardError unless the board has the expected shape."""
    if not isinstance(board, dict) or set(board) != {"system", "board", "next_number", "stories"}:
        raise BoardError("the board file does not have the four expected parts")
    if board["system"] != SYSTEM:
        raise BoardError("this is not a simulated story board")
    name = board["board"]
    if not isinstance(name, str) or not name.isascii() or not name.isalpha() or not name.isupper():
        raise BoardError("the board name is not capital letters")
    number = board["next_number"]
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise BoardError("the next story number is not a whole number from 1 up")
    if not isinstance(board["stories"], list):
        raise BoardError("the stories are not a list")
    seen = set()
    for story in board["stories"]:
        if not isinstance(story, dict) or tuple(story) != STORY_FIELDS:
            raise BoardError("a story does not have exactly id, title, description and status")
        if not all(isinstance(story[field], str) for field in STORY_FIELDS):
            raise BoardError("a story field is not text")
        prefix, _, digits = story["id"].partition("-")
        if prefix != name or not digits.isascii() or not digits.isdigit() or int(digits) >= number:
            raise BoardError("a story id does not fit this board")
        if story["id"] in seen:
            raise BoardError("two stories have the id %s" % story["id"])
        seen.add(story["id"])
        if story["status"] not in STATUSES:
            raise BoardError("story %s has a status that is not todo, doing or done" % story["id"])


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            board = json.load(f)
    except FileNotFoundError:
        raise BoardError("there is no board file at %s" % path)
    except ValueError:
        raise BoardError("the board file is not JSON")
    check(board)
    return board


def save(path, board):
    """Check the board, then write the whole file or nothing."""
    check(board)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def fingerprint(board):
    """A code that is the same for two boards only if they are the same."""
    text = json.dumps(board, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def starting_board():
    stories = [{"id": "DEMO-%d" % n, "title": title, "description": description, "status": status}
               for n, (title, description, status) in enumerate(STARTING_STORIES, 1)]
    return {"system": SYSTEM, "board": "DEMO", "next_number": len(stories) + 1, "stories": stories}


def show(path):
    board = load(path)
    print("board: %s (%s), file %s" % (board["board"], board["system"], path))
    print("stories: %d" % len(board["stories"]))
    for story in board["stories"]:
        print("  %-8s [%-5s] %s" % (story["id"], story["status"], story["title"]))
    print("board fingerprint: %s" % fingerprint(board)[:12])


def main(argv):
    if len(argv) != 3 or argv[1] not in ("init", "show"):
        print("usage: board.py init BOARD.json | board.py show BOARD.json")
        return 1
    try:
        if argv[1] == "init":
            if os.path.exists(argv[2]):
                print("refused: %s already exists, and init does not overwrite a board" % argv[2])
                return 1
            save(argv[2], starting_board())
            print("made a starting board at %s" % argv[2])
        show(argv[2])
    except BoardError as err:
        print("board error: %s" % err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
