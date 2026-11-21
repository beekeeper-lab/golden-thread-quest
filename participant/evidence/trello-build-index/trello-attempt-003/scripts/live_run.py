#!/usr/bin/env python3
"""The participant's own run on the real sandbox board. Read only. Records logs/live-index-run.txt.

The participant starts this in their own terminal, where TRELLO_API_KEY and
TRELLO_API_TOKEN are set. This script never reads, prints or stores either:
it starts the approved card reader, which reads them from the environment.

What it does:

  1  takes the card ids of the sandbox board from the board record the
     trello-read-board quest saved, participant/context/trello/board.json,
     leaving out any card that record marks as no longer returned by Trello;
  2  has the approved card reader (participant/skills/trello-read-card/card.py,
     --source live) read each card from Trello, with GET requests only, into
     a scratch folder outside the repository;
  3  copies the board record beside them and builds the index there;
  4  counts record files and index rows for itself, runs the check, and runs
     one lookup for each list.

The real cards' text stays in the scratch folder. The log holds counts, list
names, card ids and fingerprints only: no card names, no member ids, no
address and no credential. The scratch folder is shown as SCRATCH.

Run from anywhere:  python3 scripts/live_run.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
READER = "participant/skills/trello-read-card/card.py"
INDEX = "participant/skills/trello-build-index/index.py"
BOARD = "participant/context/trello/board.json"
SCRATCH = "/tmp/gtq-trello-index"


def run(*args):
    done = subprocess.run([sys.executable] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return done.returncode, done.stdout


def main():
    os.chdir(ROOT)
    lines, problems = [], []

    def check(label, ok):
        lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            problems.append(label)

    for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN"):
        if not os.environ.get(name):
            print("STOPPED: %s is not set in this terminal. Nothing was contacted." % name)
            return 1
    with open(BOARD, encoding="utf-8") as f:
        board = json.load(f)
    gone = [card_id for card_id, item in board["cards"].items() if item.get("state") == "not_returned"]
    ids = [card_id for card_id in board["cards"] if card_id not in gone]
    records, out = os.path.join(SCRATCH, "sandbox-board"), os.path.join(SCRATCH, "out")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(os.path.join(records, "cards"))
    shutil.copy(BOARD, os.path.join(records, "board.json"))

    lines += ["The index built from the real sandbox board's records: trello-build-index, attempt trello-attempt-003",
              "Recorded by scripts/live_run.py, started by the participant in their own terminal.",
              "Trello was contacted by the approved card reader only, with GET requests only. Nothing was written to Trello.",
              "The records and the index are in a scratch folder outside the repository, shown here as SCRATCH.",
              "This log holds counts, list names, card ids and fingerprints. Card names and member ids are left out.", "",
              "STEP 1. The approved card reader reads each of the %d cards the board record, %s, holds as on the board." % (len(ids), BOARD)]
    lines += ["  Left out: card %s. The board record marks it not_returned: Trello stopped returning it for this board on an" % card_id for card_id in gone]
    if gone:
        lines += ["  earlier sync. The first run of this script asked for it anyway and the reader stopped (exit code 1). That run",
                  "  is kept as logs/live-index-run-first.txt."]
    read_ok = 0
    for card_id in ids:
        code, text = run(READER, "--source", "live", "--card", card_id, "--out", os.path.join(records, "cards", card_id + ".md"))
        status = re.search(r"\b(?:status|HTTP) (\d{3})\b", text)
        lines.append("  card %s: reader exit code %d%s" % (card_id, code, ", %s" % status.group(0) if status else ""))
        read_ok += code == 0
    check("the reader wrote a record for all %d cards" % len(ids), read_ok == len(ids))
    if read_ok == 0:
        print("STOPPED: the reader could not read any card. Its last output, with nothing secret in it by design:")
        print(text[-600:])
        return 1

    lines += ["", "STEP 2. The index is built from SCRATCH/sandbox-board.",
              "$ python3 %s build --records SCRATCH/sandbox-board --out SCRATCH/out" % INDEX]
    code, text = run(INDEX, "build", "--records", records, "--out", out)
    kept = [x for x in text.replace(SCRATCH, "SCRATCH").split("\n")
            if re.match(r"(BOARD INDEX|Records folder|Files found|  indexed|  repeating|  not indexed|  accounted|Cards with a gap|Fingerprint|index\.)", x)]
    lines += ["-" * 78] + kept + ["-" * 78, "exit code: %d (lines naming a board, a card or a gap's file are left out of this log)" % code]
    files = sorted(os.listdir(os.path.join(records, "cards")))
    with open(os.path.join(out, "index.md"), encoding="utf-8") as f:
        index = f.read()
    rows = re.findall(r"^\| `(\w+)` \|", index.split("\n## By label\n")[0], re.M)
    lines += ["", "Counted by this script, not by the generator:",
              "  record files in SCRATCH/sandbox-board/cards/: %d" % len(files),
              "  card rows in SCRATCH/out/index.md:            %d, holding %d different card ids" % (len(rows), len(set(rows)))]
    check("the row count equals the record count: %d rows, %d records" % (len(rows), len(files)), len(rows) == len(files) > 0)
    check("no card is repeated", len(set(rows)) == len(rows))
    check("the card ids in the rows are exactly the card ids the records are named by", sorted(rows) == [name[:-3] for name in files])

    lines += ["", "STEP 3. Board order. The board record gives these positions: %s."
              % ", ".join("%s %s" % (item["name"], item["pos"]) for item in board["lists"])]
    headings = re.findall(r"^### \d+\. (.+)$", index, re.M)
    expected = [item["name"] for item in sorted(board["lists"], key=lambda item: (item["closed"], item["pos"], item["id"]))]
    lines.append("  list headings in index.md, in order: %s" % ", ".join(headings))
    check("the lists are in position order, which is not their order by name", headings == expected and headings != sorted(headings))

    lines += ["", "STEP 4. One lookup for each list, and the check."]
    total = 0
    for item in board["lists"]:
        code, text = run(INDEX, "lookup", "--list", item["name"], "--records", records, "--out", out)
        found = re.findall(r"^  card (\w+)", text, re.M)
        total += len(found)
        lines.append("  lookup --list %s: exit code %d, %d card(s): %s" % (json.dumps(item["name"]), code, len(found), ", ".join(found) or "none"))
    check("the four lookups together return every card once: %d of %d" % (total, len(rows)), total == len(rows))
    code, text = run(INDEX, "check", "--records", records, "--out", out)
    lines.append("  check: exit code %d" % code)
    check("the check passes on the index just built", code == 0)
    code2, _ = run(INDEX, "build", "--records", records, "--out", out)
    code2, text2 = code2, _
    check("a second build finds both files unchanged", text2.count("UNCHANGED, not rewritten") == 2)

    count = sum(1 for x in lines if re.match(r"  (ok  |FAIL) ", x))
    lines += ["", "RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not problems else "%d OF %d CHECKS FAILED." % (len(problems), count))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "live-index-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[-1])
    for problem in problems:
        print("  FAILED: " + problem)
    print("Log saved: logs/live-index-run.txt in the attempt folder. The real cards' text stayed in %s." % SCRATCH)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
