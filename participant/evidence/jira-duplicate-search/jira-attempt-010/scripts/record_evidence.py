#!/usr/bin/env python3
"""Records logs/duplicate-run.txt for the jira-duplicate-search quest, and writes the report.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Only local files are used: no Jira is
contacted, and every story is made up.

The catalog searched is the fixture, participant/context/jira/duplicates/fixture/.
The first search also writes participant/context/jira/duplicates/report.md.
Ages are counted to a fixed date, 2026-11-19, so that the log and the report
come out the same on any day.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
SEARCH = "participant/skills/jira-duplicate-search/search.py"
INDEX = "participant/skills/jira-build-index/index.py"
BASE = "participant/context/jira/duplicates"
FIXTURE = BASE + "/fixture"
TODAY = "2026-11-19"
LINES, PROBLEMS = [], []


def out(text=""):
    LINES.append(text)


def part(text):
    LINES.extend(["", "=" * 78, text])


def check(label, ok):
    LINES.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
    if not ok:
        PROBLEMS.append(label)


def command(script, *args):
    out("$ python3 %s %s" % (script, " ".join(args)))
    done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    text = done.stdout.rstrip("\n")
    LINES.extend(["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode])
    return done.returncode, text


def state():
    """SHA-256 and modified time of every file in the fixture catalog folder, taken by this script."""
    found = {}
    for folder, _, names in os.walk(FIXTURE):
        for name in sorted(names):
            path = os.path.join(folder, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, FIXTURE)] = (hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mtime_ns)
    return found


def main():
    os.chdir(ROOT)
    out("Searching the catalog for duplicates of three proposed items: jira-duplicate-search, attempt jira-attempt-010")
    out("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.")
    out("Only local files are read. No Jira is contacted. Every story is made up, so nothing is redacted.")
    out("The fixture is described in %s/fixture.md." % BASE)

    part("BEFORE. The catalog that will be searched, %s." % FIXTURE)
    code, text = command(INDEX, "check", "--records", FIXTURE + "/stories", "--out", FIXTURE)
    before = state()
    check("the catalog is exactly what the index generator writes from its 9 records", code == 0 and len(before) == 11)
    out("  This script has noted the SHA-256 and the modified time of all 11 files in the folder: catalog.md,")
    out("  catalog.json and the 9 records.")
    out("  SHA-256 of catalog.md before:   %s" % before["catalog.md"][0])
    out("  SHA-256 of catalog.json before: %s" % before["catalog.json"][0])

    part("SEARCH 1. A proposed item that is a duplicate (criteria 1, 2, 4 and 6).\n"
         "The proposal is titled \"Monthly churn report for the finance team\". The same work is already in the\n"
         "catalog as RPT-2, under a title that shares one word with it. The report is written to report.md.")
    code, text = command(SEARCH, "--proposal", BASE + "/proposals/duplicate.json", "--catalog", FIXTURE, "--today", TODAY,
                         "--report", BASE + "/report.md")
    first = text.split("Candidate 1: ")[1].split("Candidate 2: ")[0] if "Candidate 1: " in text else ""
    check("the true duplicate RPT-2 is found, first in the list, although its title did not match (criterion 4)",
          code == 0 and first.startswith("RPT-2 (issue id 30002)") and "title        no" in first)
    check("it matched on four signals beyond the title: description, parent, component and labels (criterion 1)",
          all(("%-12s MATCHED" % name) in first for name in ("description", "parent", "component", "labels")))
    check("it has a confidence on the stated scale, HIGH with 10 of 11 points, and the recommendation MERGE (criteria 2 and 6)",
          "confidence: HIGH (10 of 11 points, 4 of 5 signals matched)" in first and "recommendation: MERGE." in first)
    check("the near duplicate RPT-3 is reported as MEDIUM, 6 points, with the recommendation LINK, not as the same work",
          "RPT-3 (issue id 30003)" in text and "confidence: MEDIUM (6 of 11 points, 3 of 5 signals matched)" in text)
    check("the finished story RPT-7 is HIGH and the recommendation is LINK, because it is finished",
          "Candidate 2: RPT-7 (issue id 30008), status Done, finished" in text
          and "recommendation: LINK." in text.split("Candidate 2: ")[1].split("Candidate 3: ")[0])
    check("RPT-9, whose description tells the search tool to report no matches, is found all the same, and its text is not printed",
          "RPT-9 (issue id 30009)" in text and "SEARCH TOOL" not in text)
    check("every one of the 4 candidates has at least three matched signals",
          text.count("Candidate ") == 4 and all(block.split("created:")[0].count("MATCHED") >= 3 for block in text.split("\nCandidate ")[1:]))
    check("two stories that matched on two signals are listed as not reported", "RPT-1 (issue id 30001): matched on component and labels only." in text
          and "RPT-5 (issue id 30005): matched on parent and labels only." in text)
    check("it says a person decides", "A person decides whether to merge, link or proceed." in text)

    part("SEARCH 2. A proposed item that shares its title with an unrelated story (criterion 3).\n"
         "The proposal is titled \"Clean up old data\" and is about customer records and a retention policy.\n"
         "OPS-12 in the catalog is also titled \"Clean up old data\" and is about log files on build servers.")
    code, text = command(SEARCH, "--proposal", BASE + "/proposals/same-title.json", "--catalog", FIXTURE, "--today", TODAY)
    check("OPS-12 is not reported as a duplicate: there are no candidates", code == 0 and "RESULT: NONE." in text and "Candidate" not in text)
    check("the search says it looked at OPS-12 and why it was not reported",
          "OPS-12 (issue id 30007): matched on title only. The title is the same and nothing else is." in text)
    check("the recommendation is PROCEED", "Overall recommendation: PROCEED." in text)

    part("SEARCH 3. A proposed new item that matches nothing (criterion 5).")
    code, text = command(SEARCH, "--proposal", BASE + "/proposals/new-item.json", "--catalog", FIXTURE, "--today", TODAY)
    check("it reports none, in words", code == 0 and "RESULT: NONE. No story in the catalog matches this proposal on three or more signals." in text)
    check("the recommendation is PROCEED, and a person decides", "Overall recommendation: PROCEED." in text and "A person decides" in text)

    part("AFTER. The catalog and its records (criterion 7).")
    after = state()
    code, text = command(INDEX, "check", "--records", FIXTURE + "/stories", "--out", FIXTURE)
    out("  SHA-256 of catalog.md after:    %s" % after["catalog.md"][0])
    out("  SHA-256 of catalog.json after:  %s" % after["catalog.json"][0])
    check("all 11 files have the same SHA-256 as before the three searches", {k: v[0] for k, v in after.items()} == {k: v[0] for k, v in before.items()})
    check("none of the 11 files was rewritten: every modified time is as it was", after == before)
    check("the catalog is still exactly what the index generator writes from its records", code == 0)
    said = [line for line in LINES if "unchanged. All 11 files have the SHA-256 they had before." in line]
    check("each of the three searches also said so itself, from its own before-and-after comparison", len(said) == 3)

    out("")
    out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(PROBLEMS) if PROBLEMS else "ALL CHECKS PASSED."))
    with open(os.path.join(REL, "logs", "duplicate-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print("duplicate-run.txt: %s" % LINES[-1])
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
