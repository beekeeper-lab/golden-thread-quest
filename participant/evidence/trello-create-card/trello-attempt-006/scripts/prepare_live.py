#!/usr/bin/env python3
"""Makes a local index of the real sandbox board, for the duplicate search of the real preview. Read only.

The participant starts this in their own terminal, where TRELLO_API_KEY and
TRELLO_API_TOKEN are set. This script never reads, prints or stores either:
it starts the approved card reader, which reads them from the environment
and sends GET requests only.

It takes the card ids from the board record the trello-read-board quest
saved, participant/context/trello/board.json, leaving out any card that
record marks as no longer returned, has the approved card reader read each
one into a scratch folder outside the repository, /tmp/gtq-trello-create, and
builds the index there with the approved index generator.

The real cards' text stays in the scratch folder. This script prints counts
and card ids only, and saves nothing in the repository.

Run from anywhere:  python3 scripts/prepare_live.py
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
READER = "participant/skills/trello-read-card/card.py"
INDEX = "participant/skills/trello-build-index/index.py"
BOARD = "participant/context/trello/board.json"
SCRATCH = "/tmp/gtq-trello-create"


def main():
    os.chdir(ROOT)
    for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN"):
        if not os.environ.get(name):
            print("STOPPED: %s is not set in this terminal. Nothing was contacted." % name)
            return 1
    with open(BOARD, encoding="utf-8") as f:
        board = json.load(f)
    ids = [card_id for card_id, item in board["cards"].items() if item.get("state") != "not_returned"]
    records = os.path.join(SCRATCH, "boards", "sandbox")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(os.path.join(records, "cards"))
    shutil.copy(BOARD, os.path.join(records, "board.json"))
    read = 0
    for card_id in ids:
        done = subprocess.run([sys.executable, READER, "--source", "live", "--card", card_id, "--out", os.path.join(records, "cards", card_id + ".md")],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("card %s: reader exit code %d" % (card_id, done.returncode))
        read += done.returncode == 0
    built = subprocess.run([sys.executable, INDEX, "build", "--records", records, "--out", records], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = read == len(ids) and built.returncode == 0
    print("RESULT: %s. %d of %d cards read with GET requests only. The index is in %s/boards." % ("READY" if ok else "NOT READY", read, len(ids), SCRATCH))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
