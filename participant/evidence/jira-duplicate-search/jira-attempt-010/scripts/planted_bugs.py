#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-duplicate-search quest.

Puts one bug at a time into participant/skills/jira-duplicate-search/search.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes search.py while it runs. Do not run a search at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, "participant", "skills", "jira-duplicate-search")
TARGET = os.path.join(SKILL, "search.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A matching title is enough to report a duplicate (criterion 3)",
     '    if len(matched) < MIN_SIGNALS:', '    if len(matched) < 1:'),
    ("B. Two matched signals are enough to report a duplicate (criteria 1 and 3)",
     'MIN_SIGNALS = 3', 'MIN_SIGNALS = 2'),
    ("C. Only the title is compared (criteria 1 and 4)",
     '    matched = [name for name, _ in WEIGHTS if signals[name][0] is True]', '    matched = [name for name in ("title",) if signals[name][0] is True]'),
    ("D. The description is never compared, so a duplicate under another title scores lower (criterion 4)",
     '        signals["description"] = (len(shared) >= 4 and share >= 0.5,', '        signals["description"] = (False,'),
    ("E. Any shared word makes two descriptions match (criterion 3)",
     '        signals["description"] = (len(shared) >= 4 and share >= 0.5,', '        signals["description"] = (len(shared) >= 1,'),
    ("F. A field that cannot be compared is counted as a match (criterion 2)",
     '    matched = [name for name, _ in WEIGHTS if signals[name][0] is True]', '    matched = [name for name, _ in WEIGHTS if signals[name][0] is not False]'),
    ("G. Every signal is worth one point, so the trust ranking is lost (criterion 2)",
     '    score = sum(points for name, points in WEIGHTS if name in matched)', '    score = len(matched)'),
    ("H. Medium starts at 6 points where it should start at 5 (criterion 2)",
     'LEVELS = (("high", 8), ("medium", 5), ("low", 0))', 'LEVELS = (("high", 8), ("medium", 6), ("low", 0))'),
    ("I. A finished story is recommended for merging (criterion 6)",
     '        advice = "link" if finished else "merge"', '        advice = "merge"'),
    ("J. A low-confidence candidate is recommended for linking (criterion 6)",
     '        advice = "link" if level == "medium" else "proceed"', '        advice = "link"'),
    ("K. No match is reported as an empty result with no statement (criterion 5)",
     '        out += ["RESULT: NONE. No story in the catalog matches this proposal on three or more signals."]', '        out += [""]'),
    ("L. The statement that a person decides is left out (criterion 6)",
     '"This is a recommendation. A person decides whether to merge, link or proceed. The search has created,",', '"This is the decision. The search has created,",'),
    ("M. A stale catalog is searched anyway (criterion 7)",
     '    if index.matches(folder, files):', '    if False:'),
    ("N. The search rebuilds a stale catalog itself (criterion 7)",
     '    if index.matches(folder, files):', '    if index.matches(folder, files) and index.cmd_build(records, folder) != 0:'),
    ("O. The report may be written over the catalog (criterion 7)",
     '                os.path.basename(args.report) in ("catalog.md", "catalog.json"):', '                False:'),
    ("P. The weakest candidate is listed first (criterion 2)",
     '    candidates.sort(key=lambda c: (-c["score"], int(c["entry"]["id"])))', '    candidates.sort(key=lambda c: (c["score"], int(c["entry"]["id"])))'),
    ("Q. A parent is matched on part of its key, so RPT-1 matches RPT-10 (criterion 2)",
     'proposal["parent"].lower() == (story["parent_key"] or "").lower()', '(story["parent_key"] or "").lower().startswith(proposal["parent"].lower())'),
    ("R. Stop words are compared like any other word (criterion 3)",
     '        if len(word) >= 3 and word not in STOP_WORDS:', '        if len(word) >= 1:'),
    ("S. A title in the report is not escaped (safety rule: untrusted text)",
     '    esc = md\n', '    esc = str\n'),
    ("T. The story's description is printed with the candidate (safety rule: untrusted text)",
     '                "  title: %s" % quote(entry["title"] or ""),', '                "  title: %s" % quote(entry["title"] or ""), "  says: %s" % c["story"]["description"],'),
    ("U. The age of a candidate is counted from the wrong end (stretch goal)",
     '    days = (today - datetime.date.fromisoformat(day)).days', '    days = (datetime.date.fromisoformat(day) - today).days'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_search\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken search? jira-duplicate-search, attempt jira-attempt-010",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-duplicate-search/search.py, every test was run, and the",
           "bug was taken out again. Only local files are used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: search.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
