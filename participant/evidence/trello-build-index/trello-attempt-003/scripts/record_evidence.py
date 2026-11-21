#!/usr/bin/env python3
"""Records logs/index-run.txt for the trello-build-index quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Only local files are used: no Trello is
contacted, and every board, list, card and member is made up.

Parts 1 to 3 run on the records in the repository,
participant/context/trello/index-fixture/, and write the index in the
repository. Parts 4 to 7 add and spoil records, so they run on a copy in a
temporary folder, shown in the log as COPY, and leave the repository's
records alone.

This script counts for itself. It does not take the generator's word for how
many cards there are or how many rows it wrote: it lists the record files,
reads the card id out of each, and reads the rows out of index.md.

If logs/live-index-run.txt exists (the participant's own run on the real
sandbox board's records), it is copied unchanged to the end of the log.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
INDEX = "participant/skills/trello-build-index/index.py"
MAKE = REL + "/scripts/make_fixture.py"
RECORDS = "participant/context/trello/index-fixture"
OUT = "participant/context/trello"
BO = "5f0000000000000000000002"
NOW = "2026-11-20T09:00:00Z"


def card(n):
    return "72c%021d" % n


class Log:
    def __init__(self):
        self.lines, self.problems, self.copy = [], [], None

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.copy, "COPY") if self.copy else text

    def command(self, script, *args):
        self.out("$ python3 %s %s" % (script, self.tidy(" ".join('"%s"' % a if " " in a else a for a in args))))
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text = self.tidy(done.stdout.rstrip("\n"))
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def record_ids(records):
    """This script's own count: the card id written in each file of cards/."""
    found = []
    for name in sorted(os.listdir(os.path.join(records, "cards"))):
        match = re.search(r'^id: "(\w+)"$', read(os.path.join(records, "cards", name)), re.M)
        found.append(match.group(1) if match else None)
    return found


def row_ids(out):
    """This script's own count: the card id at the start of each card row of index.md, above the views by label."""
    return re.findall(r"^\| `(\w+)` \|", read(os.path.join(out, "index.md")).split("\n## By label\n")[0], re.M)


def rows_under(out, heading):
    text = read(os.path.join(out, "index.md")).split("\n%s\n" % heading)[1]
    return re.findall(r"^\| `(\w+)` \|", re.split(r"\n##+ ", text)[0], re.M)


def found(text):
    return re.findall(r"^  card (\w+)", text, re.M)


def main():
    os.chdir(ROOT)
    log = Log()
    log.out("Building the board index, changing the records, and looking things up: trello-build-index, attempt trello-attempt-003")
    log.out("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.")
    log.out("Only local files are read. No Trello is contacted. Every board, list, card and member in parts 1 to 7 is made up,")
    log.out("so nothing is redacted. The card records were written by the card reader approved in the trello-read-card quest.")

    files = record_ids(RECORDS)
    log.part("PART 1. The index built twice from the same records.\n"
             "The records are %s/board.json and the %d files in %s/cards/. Any index already there is removed first."
             % (RECORDS, len(files), RECORDS))
    for name in ("index.md", "index.json"):
        if os.path.exists(os.path.join(OUT, name)):
            os.remove(os.path.join(OUT, name))
    code1, text1 = log.command(INDEX, "build")
    first = {name: sha(os.path.join(OUT, name)) for name in ("index.md", "index.json")}
    stamp = os.stat(os.path.join(OUT, "index.md")).st_mtime_ns
    log.out("")
    log.out("The same command again:")
    code2, text2 = log.command(INDEX, "build")
    second = {name: sha(os.path.join(OUT, name)) for name in first}
    log.out("")
    log.check("the first build wrote both files and the second found both unchanged",
              code1 == 0 and code2 == 0 and len(re.findall(r"^index\.\w+: +WRITTEN", text1, re.M)) == 2 and text2.count("UNCHANGED, not rewritten") == 2)
    log.check("the SHA-256 of index.md is the same after both builds: %s" % first["index.md"], first == second)
    log.check("the second build did not rewrite index.md (its modified time has not moved)", os.stat(os.path.join(OUT, "index.md")).st_mtime_ns == stamp)
    log.out("")
    log.out("Counted by this script, not by the generator:")
    rows = row_ids(OUT)
    log.out("  record files in %s/cards/: %d, holding %d different card ids" % (RECORDS, len(files), len(set(files))))
    log.out("  card rows in %s/index.md:  %d, holding %d different card ids" % (OUT, len(rows), len(set(rows))))
    log.check("the row count equals the record count: %d rows, %d records" % (len(rows), len(files)), len(rows) == len(files) == 12)
    log.check("no card is repeated: the %d rows hold %d different card ids" % (len(rows), len(set(rows))), len(set(rows)) == len(rows))
    log.check("the card ids in the rows are exactly the card ids in the record files", sorted(rows) == sorted(files) and None not in files)
    log.check("the generator's own counts agree: 12 found, 12 indexed, 0 repeats, 0 not indexed",
              "accounted for: 12 of 12" in text1 and "indexed, one row each:               12" in text1)
    index = read(os.path.join(OUT, "index.md"))
    log.out("")
    log.out("The start of %s/index.md, as written:" % OUT)
    log.out("-" * 78)
    log.out(index.split("\n### 2. ")[0].rstrip("\n"))
    log.out("-" * 78)
    head = index.split("## What this index was built from")[0]
    log.check("the header says the file is generated, that the records are the source of truth, and which records it was built from",
              "This file is generated. Do not edit it by hand." in head and "are the source of truth, not this" in head
              and "`index-fixture/cards/`" in head and "`index-fixture/board.json`" in head
              and re.search(r"\| Fingerprint of the records \| `[0-9a-f]{64}` \|", index) is not None)
    log.check("no date or time of the build is in the index", re.search(r"(built|generated|written) (at|on) \d", index.lower()) is None)

    log.part("PART 2. Board order.\n"
             "By name the open lists would sort Doing, Done, In review, To do. Their position numbers are 1000 for To do,\n"
             "2000 for Doing, 3000 for In review and 4000 for Done. The archived list Abandoned is at 2500.")
    headings = re.findall(r"^(##+ .+)$", index.split("## Lists, in the order")[1].split("## By label")[0], re.M)
    for line in headings:
        log.out("  " + line)
    log.check("the lists are in position order: To do, Doing, In review, Done",
              headings[:4] == ["### 1. To do", "### 2. Doing", "### 3. In review", "### 4. Done"])
    log.check("the archived list comes after them, under its own heading, and keeps its card",
              headings[4:6] == ["## Archived lists", "### 5. Abandoned"] and rows_under(OUT, "### 5. Abandoned") == [card(9)])
    log.check("To do holds its cards by position, 100 then 300, although by name the second sorts first; its archived card is last",
              rows_under(OUT, "### 1. To do") == [card(2), card(1), card(3)])
    log.check("Doing holds 100, then 200, then the card whose record has no position",
              rows_under(OUT, "### 2. Doing") == [card(5), card(4), card(11)])
    log.check("In review holds 100, 150, 200", rows_under(OUT, "### 3. In review") == [card(6), card(13), card(7)])
    log.check("the card on a list the board record does not have is in its own section, and has one row in all",
              rows_under(OUT, "## Cards whose list is not known") == [card(10)] and rows.count(card(10)) == 1)
    log.check("the card whose name is worded as an instruction is one row in Doing, and the other lists still hold their cards",
              rows.count(card(5)) == 1 and rows_under(OUT, "### 4. Done") == [card(8)])
    awkward = [line for line in index.split("\n") if line.startswith("| `%s`" % card(2))][0]
    log.check("the card name full of table characters is one row of six cells", len(re.findall(r"(?<!\\)\|", awkward)) == 7)

    log.part("PART 3. Lookups, answered from the index.")
    code, text = log.command(INDEX, "lookup", "--list", "In review")
    log.check("by list: the three cards of In review, in board order", code == 0 and found(text) == [card(6), card(13), card(7)])
    log.out("")
    code, text = log.command(INDEX, "lookup", "--label", "bug")
    log.check("by label: the three cards labelled bug", code == 0 and sorted(found(text)) == [card(2), card(5), card(10)])
    log.out("")
    code, text = log.command(INDEX, "lookup", "--member", BO)
    log.check("by member: the four cards that member is on", code == 0 and sorted(found(text)) == [card(2), card(4), card(8), card(13)])
    log.out("")
    log.out("Stretch goal: cards due in the next seven days, counted from a clock value given on the command line.")
    code, text = log.command(INDEX, "lookup", "--due-within-days", "7", "--now", NOW)
    log.check("two cards are due from 20 to 27 November 09:00; the one due at 12:00 on the 27th, the one already complete "
              "and the one due in December are left out", code == 0 and found(text) == [card(4), card(1)])
    log.check("each lookup says the index matches the records and how long ago it was written", "It was last written" in text)
    log.out("")
    code, text = log.command(INDEX, "lookup", "--label", "no-such-label")
    log.check("a label no card has finds nothing and ends with exit code 1", code == 1 and found(text) == [] and "Found: 0 of 12" in text)
    log.out("")
    code, text = log.command(INDEX, "check")
    log.check("the check passes on the index just built", code == 0)

    with tempfile.TemporaryDirectory() as tmp:
        log.copy = os.path.realpath(tmp)
        records, out = os.path.join(log.copy, "index-fixture"), os.path.join(log.copy, "out")
        shutil.copytree(RECORDS, records)
        where = ["--records", records, "--out", out]

        log.part("PART 4. A card is added.\n"
                 "The records are copied to a temporary folder, COPY, and the index is built there.")
        code, text = log.command(INDEX, "build", *where)
        before = read(os.path.join(out, "index.md"))
        log.check("the copy gives the same index.md as the repository's records, byte for byte", sha(os.path.join(out, "index.md")) == first["index.md"])
        log.out("")
        log.out("The approved card reader writes one more record:")
        log.command(MAKE, "--set", "added", "--out", records)
        log.out("")
        log.out("Before any rebuild:")
        code, text = log.command(INDEX, "check", *where)
        log.check("the check says the index no longer matches the records", code == 1 and "CHECK FAILED" in text)
        log.out("")
        code, text = log.command(INDEX, "lookup", "--list", "Doing", *where)
        log.check("a lookup refuses to answer from the stale index and names no card", code == 1 and found(text) == [] and "No answer is given" in text)
        log.out("")
        log.out("Rebuilt:")
        code, text = log.command(INDEX, "build", *where)
        files, rows = record_ids(records), row_ids(out)
        log.out("")
        log.out("Counted by this script: %d record files, %d card rows, %d different card ids in the rows." % (len(files), len(rows), len(set(rows))))
        log.check("13 records, 13 rows, no card repeated, the same ids", len(files) == 13 and sorted(rows) == sorted(files) and len(set(rows)) == 13)
        log.check("the new card is in Doing between the cards at 200 and at no position: its position is 250",
                  rows_under(out, "### 2. Doing") == [card(5), card(4), card(14), card(11)])
        after = read(os.path.join(out, "index.md"))
        old_rows = [line for line in before.split("\n## By label\n")[0].split("\n") if line.startswith("| `")]
        log.check("every row of the earlier index is in the new one, unchanged", all(line in after.split("\n") for line in old_rows))
        code, text = log.command(INDEX, "lookup", "--due-within-days", "7", "--now", NOW, *where)
        log.check("the new card, due on the 25th, is now among the cards due in seven days", found(text) == [card(4), card(1), card(14)])

        log.part("PART 5. A card with missing fields.\n"
                 "The reader is handed a card with no due date field, no labels field and no closed field, and writes its record.")
        log.command(MAKE, "--set", "gap", "--out", records)
        log.out("")
        code, text = log.command(INDEX, "build", *where)
        after = read(os.path.join(out, "index.md"))
        line = [x for x in after.split("\n") if x.startswith("| `%s`" % card(15))]
        log.out("")
        log.out("Its row in index.md:")
        log.out("  " + (line[0] if line else "NO ROW"))
        log.out("The Gaps section of index.md:")
        for x in after.split("\n## Gaps\n")[1].split("\n## ")[0].strip().split("\n"):
            log.out("  " + x)
        log.check("the card has its row, in Done, after the card at position 100", rows_under(out, "### 4. Done") == [card(8), card(15)])
        log.check("the row shows (missing) three times: labels, due date and state", len(line) == 1 and line[0].count("(missing)") == 3)
        log.check("the build reports the gap by card id and field",
                  "GAP  card %s (cards/%s.md): no closed state, no labels, no due date" % (card(15), card(15)) in text)
        log.check("three cards with a gap are reported and listed", "Cards with a gap: 3" in text and "| Cards with a gap | 3 |" in after)
        log.check("a card whose record says it has no due date is not listed as a gap: card 7 says none",
                  card(7) not in after.split("\n## Gaps\n")[1].split("\n## ")[0])
        files, rows = record_ids(records), row_ids(out)
        log.check("14 records, 14 rows, no card repeated", len(files) == 14 and sorted(rows) == sorted(files) and len(set(rows)) == 14)

        log.part("PART 6. Files that must not become rows.\n"
                 "Three files are put in COPY/index-fixture/cards/: a second copy of one card's record, a card of another board\n"
                 "written by the reader, and a file of notes that is not a record.")
        shutil.copy(os.path.join(records, "cards", card(1) + ".md"), os.path.join(records, "cards", "copy-of-card-1.md"))
        log.command(MAKE, "--set", "stray", "--out", records)
        with open(os.path.join(records, "cards", "notes.md"), "w", encoding="utf-8") as f:
            f.write("# Notes\n\nNot a card record.\n")
        log.out("")
        code, text = log.command(INDEX, "build", *where)
        names, rows = os.listdir(os.path.join(records, "cards")), row_ids(out)
        log.out("")
        log.out("Counted by this script: %d files in cards/, %d card rows, %d different card ids in the rows." % (len(names), len(rows), len(set(rows))))
        log.check("17 files: 14 rows, 1 repeat, 2 not indexed, and 14 + 1 + 2 = 17",
                  len(names) == 17 and len(rows) == 14 and "accounted for: 17 of 17" in text and "14 + 1 + 2 = 17" in read(os.path.join(out, "index.md")))
        log.check("no card is repeated: card 1 still has one row", len(set(rows)) == 14 and rows.count(card(1)) == 1)
        log.check("the repeat and both files not indexed are named, each with the reason",
                  "REPEAT  cards/copy-of-card-1.md" in text and "NOT INDEXED  cards/notes.md: it has no front matter" in text
                  and "NOT INDEXED  cards/%s.md: it belongs to another board" % card(12) in text)

        log.part("PART 7. The index edited by hand.\n"
                 "In COPY/out/index.md the card \"Add dark mode\" is moved, by hand, from open to archived.")
        path = os.path.join(out, "index.md")
        good = read(path)
        line = [x for x in good.split("\n") if x.startswith("| `%s`" % card(4))][0]
        with open(path, "w", encoding="utf-8") as f:
            f.write(good.replace(line, line[:-len("open |")] + "archived |"))
        log.check("the file was changed", read(path) != good)
        code, text = log.command(INDEX, "check", *where)
        log.check("the check finds it and names index.md", code == 1 and "index.md is not what" in text)
        log.out("")
        code, text = log.command(INDEX, "build", *where)
        log.check("a build puts back what the records say", code == 0 and read(path) == good and "REWRITTEN" in text)
        log.copy = None

    log.part("AFTERWARDS")
    files = record_ids(RECORDS)
    log.check("the repository's records were not touched by parts 4 to 7: %d files" % len(files), len(files) == 12)
    log.check("the repository's index.md is still the one built in part 1", sha(os.path.join(OUT, "index.md")) == first["index.md"])
    code = subprocess.run([sys.executable, INDEX, "check"], stdout=subprocess.PIPE, text=True).returncode
    log.check("and the check on it still passes", code == 0)

    checks = sum(1 for line in log.lines if re.match(r"  (ok  |FAIL) ", line))
    log.out("")
    log.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % checks if not log.problems else "%d OF %d CHECKS FAILED." % (len(log.problems), checks)))
    live = os.path.join(ATTEMPT, "logs", "live-index-run.txt")
    if os.path.exists(live):
        log.part("THE SAME ON THE REAL SANDBOX BOARD'S RECORDS.\n"
                 "What follows is logs/live-index-run.txt, copied unchanged. The participant ran it. It is not part of the checks above.")
        log.out(read(live).rstrip("\n"))
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "index-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print([line for line in log.lines if line.startswith("RESULT:")][0])
    for problem in log.problems:
        print("  FAILED: " + problem)
    return 0 if not log.problems else 1


if __name__ == "__main__":
    sys.exit(main())
