#!/usr/bin/env python3
"""Records logs/base-recorded.txt for the jira-detect-conflicts quest.

Shows local_edit.py capturing the base value at the moment of a local edit.
It works on a copy of the fixture's jira-copy.json in work/base-demo/, so the
fixture itself is not touched.

Run from anywhere:  python3 scripts/record_base.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
FIXTURE = "participant/context/jira/conflicts/fixture"
DEMO = REL + "/work/base-demo"


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    os.chdir(ROOT)
    shutil.rmtree(DEMO, ignore_errors=True)
    os.makedirs(DEMO)
    shutil.copy(FIXTURE + "/jira-copy.json", DEMO + "/jira-copy.json")
    copy, edits = DEMO + "/jira-copy.json", DEMO + "/local-edits.json"
    lines, problems = [], []

    def out(text=""):
        lines.append(text)

    def check(label, ok):
        out("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            problems.append(label)

    def edit(*args):
        shown = " ".join("'%s'" % a if (" " in a or '"' in a) else a for a in args)
        out("$ local_edit.py --copy %s --edits %s %s" % (copy, edits, shown))
        done = subprocess.run([sys.executable, REL + "/scripts/local_edit.py", "--copy", copy, "--edits", edits]
                              + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out(done.stdout.rstrip("\n"))
        out("(exit code %d)" % done.returncode)
        return done.returncode

    out("Recording the base value: jira-detect-conflicts, attempt jira-attempt-004")
    out("Recorded by scripts/record_base.py. Paths are from the repository root. Synthetic data only.")
    out("")
    out("=" * 78)
    out("1. A copy of the fixture's jira-copy.json is the only input. Its checksum before:")
    before = sha(copy)
    out("  %s  %s" % (before, copy))

    out("")
    out("=" * 78)
    out("2. Make the fixture's seven local edits again, one command each.")
    out("   No base is given on any command line. The tool reads it from Jira's copy.")
    with open(FIXTURE + "/local-edits.json", encoding="utf-8") as f:
        wanted = json.load(f)["edits"]
    for e in wanted:
        edit("--story", e["story"], "--field", e["field"], "--value", json.dumps(e["local"]["value"]),
             "--by", e["local"]["edited_by"], "--at", e["local"]["edited_at"])
    with open(edits, encoding="utf-8") as f:
        made = json.load(f)["edits"]
    out("")
    check("the seven edits the tool recorded are the same as the fixture's local-edits.json, bases included",
          made == wanted)
    check("every recorded edit has a base value and a base time",
          all("value" in e["base"] and e["base"].get("changed_at") for e in made))

    out("")
    out("=" * 78)
    out("3. Edit a field a second time. The local value changes. The base does not.")
    edit("--story", "FIX-3", "--field", "estimate", "--value", "4", "--by", "participant",
         "--at", "2026-11-05T17:00:00Z")
    with open(edits, encoding="utf-8") as f:
        again = [e for e in json.load(f)["edits"] if (e["story"], e["field"]) == ("FIX-3", "estimate")][0]
    out(json.dumps(again, indent=2))
    check("the local value is now 4", again["local"]["value"] == 4)
    check("the base is still 8, as first recorded", again["base"] == {"value": 8, "changed_at": "2026-11-02T09:00:00Z"})

    out("")
    out("=" * 78)
    out("4. An edit that has no base to record is refused.")
    code = edit("--story", "FIX-99", "--field", "estimate", "--value", "5", "--by", "participant")
    check("a story that is not in Jira's copy: refused", code == 1)
    out("$ (the edits file given as the same file as Jira's copy)")
    done = subprocess.run([sys.executable, REL + "/scripts/local_edit.py", "--copy", copy, "--edits", copy,
                           "--story", "FIX-1", "--field", "estimate", "--value", "5", "--by", "participant"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out(done.stdout.rstrip("\n"))
    check("writing local edits into Jira's copy: refused", done.returncode == 1)
    with open(edits, encoding="utf-8") as f:
        check("the edits file still holds seven edits", len(json.load(f)["edits"]) == 7)

    out("")
    out("=" * 78)
    out("5. Jira's copy after all of the above:")
    out("  %s  %s" % (sha(copy), copy))
    check("Jira's copy is unchanged: no local edit was written into it", sha(copy) == before)
    check("the fixture's own jira-copy.json is the same file, untouched", sha(FIXTURE + "/jira-copy.json") == before)

    out("")
    out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(problems) if problems else
                        "ALL CHECKS PASSED. The base is read from Jira's copy when an edit is made, and kept."))
    with open(REL + "/logs/base-recorded.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[-1])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
