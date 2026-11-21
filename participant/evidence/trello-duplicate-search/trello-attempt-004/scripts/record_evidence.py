#!/usr/bin/env python3
"""Records logs/duplicate-run.txt for the trello-duplicate-search quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Only local files are used: no Trello is
contacted, and every board, list, card and member is made up.

Parts 1 to 6 run on the two made-up boards in the repository,
participant/context/trello/duplicates/boards/, and write nothing there.
Parts 7 and 8 spoil a board and remove one, so they run on a copy in a
temporary folder, shown in the log as COPY.

This script checks for itself. It takes the SHA-256 of every file in the
boards folder before the first search and after the last, rather than taking
the search's word that nothing changed.

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
SEARCH = "participant/skills/trello-duplicate-search/search.py"
INDEX = "participant/skills/trello-build-index/index.py"
BASE = "participant/context/trello/duplicates"
BOARDS = BASE + "/boards"
REPORT = BASE + "/report.md"


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


def hashes(folder):
    found = {}
    for base, _, names in os.walk(folder):
        for name in names:
            with open(os.path.join(base, name), "rb") as f:
                found[os.path.relpath(os.path.join(base, name), folder)] = hashlib.sha256(f.read()).hexdigest()
    return found


def candidates(text):
    """{card id: the lines of that candidate} from what a search printed."""
    found = {}
    for block in re.split(r"\n(?=Candidate \d+: )", text.split("\nLooked at and NOT")[0].split("\nOverall recommendation")[0])[1:]:
        found[re.match(r"Candidate \d+: card (\w+)", block).group(1)] = block
    return found


def main():
    os.chdir(ROOT)
    log = Log()
    log.out("The duplicate search across boards: trello-duplicate-search, attempt trello-attempt-004")
    log.out("Recorded by scripts/record_evidence.py. Local files only. No Trello was contacted. Every board, card and member is made up.")

    log.part("PART 1. The fixture: two boards, each with its own index, and each index matches its records.")
    folders = sorted(name for name in os.listdir(BOARDS) if os.path.isdir(os.path.join(BOARDS, name)))
    files = {name: sorted(os.listdir(os.path.join(BOARDS, name, "cards"))) for name in folders}
    for name in folders:
        log.out("  %s/cards/: %d card records" % (name, len(files[name])))
    log.check("there are at least two boards: %d" % len(folders), len(folders) >= 2)
    log.check("the true duplicate (card ...201) is on the support board, and the near duplicate (...101) and the same-name card "
              "(...103) are on the platform board",
              card(201) + ".md" in files["support-team"] and {card(101) + ".md", card(103) + ".md"} <= set(files["platform-team"]))
    for name in folders:
        code, _ = log.command(INDEX, "check", "--records", "%s/%s" % (BOARDS, name), "--out", "%s/%s" % (BOARDS, name))
        log.check("the index of %s is exactly what a build from its records would write" % name, code == 0)
    before = hashes(BOARDS)
    log.out("SHA-256 taken by this script of all %d files in %s/, before any search." % (len(before), BOARDS))

    log.part("PART 2. A proposed duplicate. The card for the same work has a different name and is on another board. (criteria 1, 2, 3, 5)")
    code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/1-duplicate-on-another-board.json")
    found = candidates(text)
    dup = found.get(card(201), "")
    log.check("the search ran: exit code 0", code == 0)
    log.check("card ...201 is reported, and is the first candidate", list(found)[:1] == [card(201)])
    log.check("it is on ANOTHER board than the one the card would go on", "on: ANOTHER board" in dup)
    log.check("its name did not match: the name line says no", bool(re.search(r"^    name +no ", dup, re.M)))
    beyond = re.findall(r"^    (description|checklist|labels|members|due date) +MATCHED", dup, re.M)
    log.check("it matched on %d signals beyond the name, which is at least three: %s" % (len(beyond), ", ".join(beyond)), len(beyond) >= 3)
    log.check("it has a confidence on the stated scale: HIGH, 12 of 13 points", "confidence: HIGH (12 of 13 points" in dup)
    log.check("its recommendation is LINK, one of the three allowed", "recommendation: LINK." in dup)
    log.check("every candidate lists all six signals and a confidence",
              all(len(re.findall(r"^    (?:description|checklist|labels|members|due date|name) ", block, re.M)) == 6
                  and re.search(r"confidence: (HIGH|MEDIUM|LOW) \(", block) for block in found.values()) and len(found) == 3)
    log.check("the near duplicate (card ...101) is reported with less confidence: MEDIUM", "confidence: MEDIUM" in found.get(card(101), ""))
    log.check("the archived earlier card (...102) is reported with PROCEED, because it is archived",
              "recommendation: PROCEED. This earlier card is archived" in found.get(card(102), ""))
    log.check("the card whose name gives orders (...105) is not a candidate: it matched on members only",
              card(105) not in found and bool(re.search(r"card %s, .*: matched on members only\." % card(105), text)))

    log.part("PART 3. A proposed card with the same name as an unrelated card. (criterion 4)")
    code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/2-same-name-unrelated.json")
    log.check("the search ran: exit code 0", code == 0)
    log.check("no candidate is reported: RESULT: NONE", "RESULT: NONE." in text and not candidates(text))
    log.check("the same-name card (...103) was looked at and not reported: its name is alike and nothing else is",
              bool(re.search(r'card %s, "Update the onboarding checklist", .*: matched on name only\. The name is alike and nothing else is\.' % card(103), text)))
    log.check("a card that matched on two signals beyond the name (...203) is not reported either",
              bool(re.search(r"card %s, .*: matched on labels and members only\." % card(203), text)))
    log.check("the overall recommendation is PROCEED", "Overall recommendation: PROCEED." in text)

    log.part("PART 4. A proposed card with no match. (criterion 6)")
    code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/3-no-match.json")
    log.check("the search ran: exit code 0", code == 0)
    log.check("it reports none, in those words: RESULT: NONE", "RESULT: NONE. No card on any board searched matches" in text)
    log.check("no candidate and no near miss is listed", not candidates(text) and "Looked at and NOT" not in text)
    log.check("all 10 cards on both boards were compared", "Cards compared: 10." in text and "Boards searched: 2" in text)
    log.check("the overall recommendation is PROCEED", "Overall recommendation: PROCEED." in text)

    log.part("PART 5. The first proposal again, for the board the duplicate is on. The board decides the recommendation. (criterion 7)")
    code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/4-duplicate-on-the-same-board.json")
    found = candidates(text)
    log.check("card ...201 is now on the SAME board, and the recommendation is ARCHIVE-AS-DUPLICATE",
              "on: the SAME board" in found.get(card(201), "") and "recommendation: ARCHIVE-AS-DUPLICATE." in found.get(card(201), ""))
    log.check("the near duplicate, now on another team's board, is LINK", "recommendation: LINK." in found.get(card(101), ""))
    words = set(re.findall(r"recommendation: ([A-Z-]+)\.", text))
    log.check("the three recommendations seen are the three allowed: %s" % ", ".join(sorted(words)),
              words == {"LINK", "ARCHIVE-AS-DUPLICATE", "PROCEED"})
    log.check("the search says a person decides", "A person decides whether to link, archive as a duplicate or proceed." in text)

    log.part("PART 6. The indexes are unchanged after the four searches. (criterion 7)")
    after = hashes(BOARDS)
    log.out("SHA-256 taken again by this script of all %d files in %s/." % (len(after), BOARDS))
    for name in folders:
        for item in ("index.md", "index.json"):
            key = os.path.join(name, item)
            log.out("  %-26s before %s" % (key, before[key]))
            log.out("  %-26s after  %s" % ("", after[key]))
    log.check("every one of the %d files has the SHA-256 it had before the first search" % len(before), after == before)
    log.check("no file was added to or removed from the boards folder", sorted(after) == sorted(before))
    for name in folders:
        code, _ = log.command(INDEX, "check", "--records", "%s/%s" % (BOARDS, name), "--out", "%s/%s" % (BOARDS, name))
        log.check("the index of %s still matches its records" % name, code == 0)

    with tempfile.TemporaryDirectory() as tmp:
        log.copy = os.path.realpath(tmp)
        copy = os.path.join(log.copy, "boards")
        shutil.copytree(BOARDS, copy)

        log.part("PART 7. On a copy: an index that no longer matches its records is not searched, and is not rebuilt by the search.")
        with open(os.path.join(copy, "support-team", "cards", card(201) + ".md"), "a", encoding="utf-8") as f:
            f.write("\nA line added to the record after the index was built.\n")
        log.out("One line was added to COPY/boards/support-team/cards/%s.md." % card(201))
        stale = hashes(copy)
        code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/1-duplicate-on-another-board.json", "--boards", copy)
        log.check("the search stopped: exit code 2", code == 2)
        log.check("it says the index does not match and that nothing was searched", "does not match its records" in text and "Nothing was searched" in text)
        log.check("it reported no candidate", "Candidate" not in text)
        log.check("the search did not rebuild the index: every file in COPY/boards is as it was", hashes(copy) == stale)
        log.command(INDEX, "build", "--records", copy + "/support-team", "--out", copy + "/support-team")
        code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/1-duplicate-on-another-board.json", "--boards", copy,
                                 "--report", os.path.join(log.copy, "report.md"))
        log.check("after a person rebuilds the index, the search runs and finds card ...201 again", code == 0 and card(201) in candidates(text))
        with open(os.path.join(log.copy, "report.md"), encoding="utf-8") as f:
            report = f.read()
        log.check("a report written with no --decision says 'Not yet decided': the search does not decide", "Not yet decided." in report and "**Decision:" not in report)

        log.part("PART 8. On a copy: without the other board, the duplicate is not found. It is found because other boards are searched. (criterion 3)")
        shutil.rmtree(os.path.join(copy, "support-team"))
        log.out("COPY/boards/support-team/ was removed. Only the platform board is left.")
        code, text = log.command(SEARCH, "--proposal", BASE + "/proposals/1-duplicate-on-another-board.json", "--boards", copy)
        log.check("the search ran on one board", code == 0 and "Boards searched: 1" in text)
        log.check("card ...201 is not among the candidates", card(201) not in candidates(text))
        log.copy = None

    log.part("AFTERWARDS. The report in the repository, %s." % REPORT)
    if os.path.exists(REPORT):
        with open(REPORT, encoding="utf-8") as f:
            report = f.read()
        parts = report.split("\n### Candidate ")[1:]
        log.out("  The report was written by the participant's own run of the search, with their decision given as --decision.")
        log.check("it holds %d candidates" % len(parts), len(parts) >= 1)
        log.check("each candidate has at least three signals beyond the name marked yes",
                  all(len(re.findall(r"^\| (?:Description|Checklist|Labels|Members|Due date) \| yes \|", part, re.M)) >= 3 for part in parts))
        log.check("each candidate has a confidence of high, medium or low, with its points out of 13",
                  all(re.search(r"\*\*Confidence: (high|medium|low)\*\* \(\d+ of 13 points", part) for part in parts))
        log.check("each recommendation is link, archive-as-duplicate or proceed",
                  all(re.search(r"\*\*Recommendation: (link|archive-as-duplicate|proceed)\.\*\*", part) for part in parts))
        decided = re.search(r"^\*\*Decision: (link|archive-as-duplicate|proceed)\.\*\*$", report, re.M)
        log.check("a person's decision is recorded: %s" % (decided.group(1) if decided else "NONE YET"), bool(decided))
        log.check("the boards folder is still as it was before the first search", hashes(BOARDS) == before)
    else:
        log.out("  There is no report yet. The participant writes it with their own run of the search, giving their decision.")
        log.check("the report exists", False)

    count = sum(1 for line in log.lines if re.match(r"  (ok  |FAIL) ", line))
    log.out()
    log.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not log.problems
                            else "%d OF %d CHECKS FAILED." % (len(log.problems), count)))
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "duplicate-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print(log.lines[-1])
    for problem in log.problems:
        print("  FAILED: " + problem)
    return 0 if not log.problems else 1


if __name__ == "__main__":
    sys.exit(main())
