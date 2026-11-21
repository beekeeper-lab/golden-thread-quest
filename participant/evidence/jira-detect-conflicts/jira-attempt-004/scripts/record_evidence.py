#!/usr/bin/env python3
"""Records logs/conflict-run.txt for the jira-detect-conflicts quest.

It does five things, in order, and writes down what it sees:

  1. takes a SHA-256 checksum of each fixture file
  2. runs detect.py twice, saving each report in work/
  3. compares the two reports with each other, and with the committed
     participant/context/jira/conflicts/report.md
  4. checks each case in the fixture against the result fixture.md says it
     should give
  5. takes the checksums again and compares them with step 1

Nothing here contacts Jira. The fixture is synthetic, so nothing is redacted.

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
REL_ATTEMPT = os.path.relpath(ATTEMPT, ROOT)
FIXTURE = "participant/context/jira/conflicts/fixture"
REPORT = "participant/context/jira/conflicts/report.md"
FILES = ("jira-copy.json", "local-edits.json", "jira-now.json")

# What fixture.md says each case should give. Kept here by hand, apart from detect.py.
EXPECTED = {
    ("FIX-1", "estimate"): "local",
    ("FIX-2", "status"): "jira",
    ("FIX-2", "due_date"): "local",
    ("FIX-3", "estimate"): "conflict",
    ("FIX-3", "priority"): "local",
    ("FIX-4", "priority"): "agreement",
    ("FIX-5", "summary"): "conflict",
    ("FIX-5", "due_date"): "jira",
    ("FIX-7", "estimate"): "uncomparable",
}
EXPECTED_UNCHANGED = 22
NAMES = {"conflict": "conflict", "agreement": "agreement", "local": "changed only locally",
         "jira": "changed only in Jira", "uncomparable": "cannot be compared"}


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    os.chdir(ROOT)
    os.makedirs(os.path.join(REL_ATTEMPT, "work"), exist_ok=True)
    os.makedirs(os.path.join(REL_ATTEMPT, "logs"), exist_ok=True)
    lines = []
    problems = []

    def out(text=""):
        lines.append(text)

    def check(label, ok):
        out("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            problems.append(label)

    def checksums():
        sums = {name: sha(os.path.join(FIXTURE, name)) for name in FILES}
        for name in FILES:
            out("  %s  %s/%s" % (sums[name], FIXTURE, name))
        return sums

    out("Conflict detection run: jira-detect-conflicts, attempt jira-attempt-004")
    out("Recorded by scripts/record_evidence.py. Paths are from the repository root.")
    out("The fixture is synthetic and no Jira site is contacted, so nothing here needed redacting.")
    out("")
    out("The three files:")
    out("  local-edits.json  the local file: edits made locally, each with its base value")
    out("  jira-copy.json    the Jira copy: Jira's values as stored at the last sync")
    out("  jira-now.json     what Jira returns now")

    out("")
    out("=" * 78)
    out("1. SHA-256 checksums of the fixture files, before any run")
    before = checksums()

    reports = []
    for number in (1, 2):
        target = "%s/work/report-run-%d.md" % (REL_ATTEMPT, number)
        command = [sys.executable, os.path.join(REL_ATTEMPT, "scripts", "detect.py"),
                   "--fixture", FIXTURE, "--out", target]
        out("")
        out("=" * 78)
        out("2.%d Detection run %d" % (number, number))
        out("$ python3 %s/scripts/detect.py --fixture %s --out %s" % (REL_ATTEMPT, FIXTURE, target))
        done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out(done.stdout.rstrip("\n"))
        out("(exit code %d: 2 means at least one conflict was found)" % done.returncode)
        check("run %d ended with exit code 2" % number, done.returncode == 2)
        reports.append(target)
        if number == 1:
            out("")
            out("The report from run 1, in full:")
            out("-" * 78)
            with open(target, encoding="utf-8") as f:
                out(f.read().rstrip("\n"))
            out("-" * 78)

    out("")
    out("=" * 78)
    out("3. Are the reports identical?")
    for path in reports + [REPORT]:
        out("  %s  %s" % (sha(path), path))
    check("the report from run 1 and the report from run 2 are byte for byte the same",
          sha(reports[0]) == sha(reports[1]))
    check("both are the same as the committed %s" % REPORT, sha(reports[0]) == sha(REPORT))

    out("")
    out("=" * 78)
    out("4. Each case, against the result fixture.md says it should give")
    sys.path.insert(0, HERE)
    import detect  # noqa: E402
    data = {name: detect.read_json(os.path.join(FIXTURE, name))[0] for name in FILES}
    found, unchanged = detect.detect(detect.check_stories(data["jira-copy.json"], "jira-copy.json"),
                                     detect.check_edits(data["local-edits.json"], "local-edits.json"),
                                     detect.check_stories(data["jira-now.json"], "jira-now.json"))
    got = {(row["story"], row["field"]): kind for kind, rows in found.items() for row in rows}
    for place, kind in EXPECTED.items():
        check("%s %-9s expected: %-22s reported: %s"
              % (place[0], place[1], NAMES[kind], NAMES.get(got.get(place), "nothing")), got.get(place) == kind)
    check("nothing is reported that fixture.md does not list (%d reported, %d listed)" % (len(got), len(EXPECTED)),
          set(got) == set(EXPECTED))
    check("FIX-6, which nobody touched, is in no list", not any(place[0] == "FIX-6" for place in got))
    check("fields compared and unchanged: expected %d, reported %d" % (EXPECTED_UNCHANGED, unchanged),
          unchanged == EXPECTED_UNCHANGED)

    out("")
    out("=" * 78)
    out("5. SHA-256 checksums of the fixture files, after both runs")
    after = checksums()
    out("")
    for name in FILES:
        check("%s is unchanged" % name, before[name] == after[name])
    names_now = sorted(os.listdir(FIXTURE))
    check("the fixture folder still holds exactly these three files (found: %s)" % ", ".join(names_now),
          names_now == sorted(FILES))

    out("")
    if problems:
        out("RESULT: %d CHECK(S) FAILED" % len(problems))
        for label in problems:
            out("  - " + label)
    else:
        out("RESULT: ALL CHECKS PASSED. Two runs gave the same report, every case came out as fixture.md")
        out("says, and neither the local file nor the Jira copy was altered.")

    text = "\n".join(lines) + "\n"
    with open(os.path.join(REL_ATTEMPT, "logs", "conflict-run.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print("wrote %s/logs/conflict-run.txt: %s" % (REL_ATTEMPT, lines[-2] if not problems else lines[-1 - len(problems)]))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
