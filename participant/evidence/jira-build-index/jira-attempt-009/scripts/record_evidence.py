#!/usr/bin/env python3
"""Records logs/index-run.txt for the jira-build-index quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Only local files are used: no Jira is
contacted, and every record is made up.

Parts 1 to 3 run on the records in the repository,
participant/context/jira/stories/, and write the catalog in the repository.
Parts 4 to 6 add and spoil records, so they run on a copy in a temporary
folder, shown in the log as COPY, and leave the repository's records alone.

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
INDEX = "participant/skills/jira-build-index/index.py"
MAKE = REL + "/scripts/make_records.py"
RECORDS = "participant/context/jira/stories"
CATALOG = "participant/context/jira/catalog.md"
ADA = "5b10a0000000000000000ada"


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


def main():
    os.chdir(ROOT)
    log = Log()
    log.out("Building the catalog, changing the records, and looking things up: jira-build-index, attempt jira-attempt-009")
    log.out("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.")
    log.out("Only local files are read. No Jira is contacted. Every record is made up, so nothing is redacted.")

    log.part("PART 1. The index built twice from the same records (criterion 5).\n"
             "The records are the %d files in %s/. Any catalog already there is removed first." % (len(os.listdir(RECORDS)), RECORDS))
    for name in ("catalog.md", "catalog.json"):
        if os.path.exists("participant/context/jira/" + name):
            os.remove("participant/context/jira/" + name)
    code1, text1 = log.command(INDEX, "build")
    first = {name: sha("participant/context/jira/" + name) for name in ("catalog.md", "catalog.json")}
    stamp = os.stat(CATALOG).st_mtime_ns
    log.out("")
    log.out("The same command again:")
    code2, text2 = log.command(INDEX, "build")
    second = {name: sha("participant/context/jira/" + name) for name in first}
    log.out("")
    log.check("the first build wrote both files and the second found both unchanged",
              code1 == 0 and code2 == 0 and text1.count(": WRITTEN") + text1.count(":   WRITTEN") == 2 and text2.count("UNCHANGED, not rewritten") == 2)
    log.check("the SHA-256 of catalog.md is the same after both builds: %s" % first["catalog.md"], first == second)
    log.check("the second build did not rewrite catalog.md (its modified time has not moved)", os.stat(CATALOG).st_mtime_ns == stamp)
    log.check("13 files were found and 13 accounted for: 13 indexed, 0 repeats, 0 not indexed (criterion 2)",
              "accounted for: 13 of 13" in text1 and "indexed, one row each:               13" in text1)
    with open(CATALOG, encoding="utf-8") as f:
        catalog = f.read()
    rows = [line for line in catalog.split("## Stories")[1].split("## By status")[0].split("\n") if re.match(r"\| \d+ \|", line)]
    ids = [row.split("|")[1].strip() for row in rows]
    log.check("counted separately by this script: catalog.md has 13 story rows, with 13 different ids, for 13 record files",
              len(rows) == 13 and len(set(ids)) == 13 and len([n for n in os.listdir(RECORDS) if n.endswith(".md")]) == 13)
    log.check("two of the committed records have a gap, and both are reported (criterion 4)",
              "GAP  id 20009 (20009.md): no status" in text1 and "GAP  id 20010 (20010.md): no assignee" in text1)

    log.part("PART 2. The catalog's header (criteria 1 and 7). The first eight lines of %s:" % CATALOG)
    head = catalog.split("\n")[:8]
    log.lines += ["-" * 78] + head + ["-" * 78]
    log.check("it says the file is generated and must not be edited by hand", "This file is generated. Do not edit it by hand." in head[2])
    log.check("it says the records, not the catalog, are the source of truth", "are the source of truth, not this catalog" in head[3])
    code, text = log.command(INDEX, "check")
    log.check("the check confirms the catalog is exactly what the generator writes from the records", code == 0)

    log.part("PART 3. Lookups from the index (criterion 3).")
    log.out("By key. OPS-4 is a story that was moved to another project, so its key is not like the others:")
    code, text = log.command(INDEX, "lookup", "--key", "OPS-4")
    log.check("one story found, issue id 20011", code == 0 and "Found: 1 of 13 stories." in text and "id 20011  key OPS-4" in text)
    log.out("")
    log.out("By status:")
    code, text = log.command(INDEX, "lookup", "--status", "In Review")
    log.check("two stories found, ids 20005 and 20011", code == 0 and "Found: 2 of 13" in text and "id 20005" in text and "id 20011" in text)
    log.out("")
    log.out("By assignee. Assignees are account ids, because the records hold no names:")
    code, text = log.command(INDEX, "lookup", "--assignee", ADA)
    log.check("four stories found for that account id", code == 0 and "Found: 4 of 13" in text)
    log.out("")
    log.out("By assignee, the stories with nobody assigned:")
    code, text = log.command(INDEX, "lookup", "--assignee", "unassigned")
    log.check("two stories found, ids 20004 and 20012", code == 0 and "Found: 2 of 13" in text and "id 20004" in text and "id 20012" in text)
    log.out("")
    log.out("By words in the title (a stretch goal):")
    code, text = log.command(INDEX, "lookup", "--text", "friday export")
    log.check("one story found, id 20004", code == 0 and "Found: 1 of 13" in text and "id 20004" in text)
    log.out("")
    log.out("A lookup that finds nothing:")
    code, text = log.command(INDEX, "lookup", "--key", "DEMO-99")
    log.check("nothing found, exit code 1", code == 1 and "Found: 0 of 13" in text)

    with tempfile.TemporaryDirectory() as tmp:
        log.copy = tmp
        records, out = os.path.join(tmp, "stories"), tmp
        shutil.copytree(RECORDS, records)
        where = ["--records", records, "--out", out]

        log.part("PART 4. Adding a record, with no hand edit of the catalog (criterion 6).\n"
                 "From here on the records are a copy of the 13, in a temporary folder shown as COPY.")
        code, text = log.command(INDEX, "build", *where)
        before = sha(os.path.join(out, "catalog.md"))
        log.check("the copy builds to the same catalog.md as the repository's records", before == first["catalog.md"])
        log.out("")
        log.out("A new record is made by the approved story reader, story id 20013:")
        log.command(MAKE, "--set", "added", "--out", records)
        log.out("")
        log.out("Before any rebuild, the check and a lookup. The catalog is now stale:")
        code_check, text_check = log.command(INDEX, "check", *where)
        code_look, text_look = log.command(INDEX, "lookup", *where, "--key", "DEMO-13")
        log.check("the check fails, and the lookup gives no answer from the stale catalog (criterion 7)",
                  code_check == 1 and "CHECK FAILED" in text_check and code_look == 1 and "No answer is given" in text_look)
        log.out("")
        log.out("The build command, and nothing else:")
        code, text = log.command(INDEX, "build", *where)
        after = sha(os.path.join(out, "catalog.md"))
        with open(os.path.join(out, "catalog.md"), encoding="utf-8") as f:
            copy_catalog = f.read()
        log.check("14 files found and 14 indexed, and catalog.md was rewritten with a different SHA-256",
                  "accounted for: 14 of 14" in text and "catalog.md:   REWRITTEN" in text and after != before)
        log.check("the new story has a row: | 20013 | DEMO-13 | Alert when the Friday export is late | To Do |",
                  "| 20013 | DEMO-13 | Alert when the Friday export is late | To Do |" in copy_catalog)
        code, text = log.command(INDEX, "lookup", *where, "--key", "DEMO-13")
        log.check("the lookup now finds it", code == 0 and "id 20013  key DEMO-13" in text)

        log.part("PART 5. A record with missing fields, reported as a gap (criterion 4).\n"
                 "Story id 20014 is saved by the reader from a Jira answer with an empty title and no update time:")
        log.command(MAKE, "--set", "gap", "--out", records)
        code, text = log.command(INDEX, "build", *where)
        with open(os.path.join(out, "catalog.md"), encoding="utf-8") as f:
            copy_catalog = f.read()
        log.check("the build reports the gap: id 20014, no title, no last update", "GAP  id 20014 (20014.md): no title, no last update" in text)
        log.check("the story is still indexed, 15 of 15, with (missing) in its row",
                  "accounted for: 15 of 15" in text and "| 20014 | DEMO-14 | (missing) | In Progress |" in copy_catalog)
        log.out("The Gaps section of the rebuilt catalog:")
        log.lines += ["-" * 78] + copy_catalog.split("## Gaps\n")[1].split("\n## Files that repeat")[0].strip("\n").split("\n") + ["-" * 78]
        log.check("it lists three stories: 20009, 20010 and 20014", copy_catalog.split("## Gaps\n")[1].split("\n## ")[0].count("\n- ") == 3)

        log.part("PART 6. Files that cannot be indexed, and a hand edit (criteria 1, 2 and 7).\n"
                 "Two files are put in the copy: notes.md, which is not a record, and OPS-4-saved-again.md, a second\n"
                 "copy of story 20011.")
        with open(os.path.join(records, "notes.md"), "w", encoding="utf-8") as f:
            f.write("# Notes\n\nSomebody's notes, left in the records folder.\n")
        shutil.copy(os.path.join(records, "20011.md"), os.path.join(records, "OPS-4-saved-again.md"))
        code, text = log.command(INDEX, "build", *where)
        log.check("17 files found: 15 indexed, 1 repeat, 1 not indexed, 17 accounted for. Nothing is dropped without a word",
                  "accounted for: 17 of 17" in text and "REPEAT  OPS-4-saved-again.md holds id 20011, already indexed from 20011.md" in text
                  and "NOT INDEXED  notes.md:" in text)
        log.out("")
        log.out("Now the catalog is edited by hand: in catalog.md, story 20001's status is changed from Done to To Do.")
        path = os.path.join(out, "catalog.md")
        with open(path, encoding="utf-8") as f:
            good = f.read()
        edited = good.replace("| 20001 | DEMO-1 | Set up the intake form | Done |", "| 20001 | DEMO-1 | Set up the intake form | To Do |")
        with open(path, "w", encoding="utf-8") as f:
            f.write(edited)
        code_check, text_check = log.command(INDEX, "check", *where)
        code, text = log.command(INDEX, "build", *where)
        with open(path, encoding="utf-8") as f:
            rebuilt = f.read()
        log.check("the hand edit was made, and the check found it", edited != good and code_check == 1 and "CHECK FAILED: catalog.md is not" in text_check)
        log.check("the next build put back what the records say: Done", rebuilt == good and "catalog.md:   REWRITTEN" in text)
        log.copy = None

    log.part("AFTERWARDS. The repository's records and catalog were not touched by parts 4 to 6.")
    code, text = log.command(INDEX, "check")
    log.check("the repository's catalog still matches its 13 records, with the SHA-256 from part 1",
              code == 0 and sha(CATALOG) == first["catalog.md"] and len(os.listdir(RECORDS)) == 13)

    log.out("")
    log.out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(log.problems) if log.problems else "ALL CHECKS PASSED."))
    with open(os.path.join(REL, "logs", "index-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print("index-run.txt: %s" % log.lines[-1])
    return 1 if log.problems else 0


if __name__ == "__main__":
    sys.exit(main())
