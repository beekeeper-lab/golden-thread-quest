#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the context-staleness quest.

Puts one bug at a time into participant/skills/context-freshness/answer.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes answer.py while it runs. Do not run the tool at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "context-freshness")
TARGET = os.path.join(SKILL, "answer.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. An item with no retrieval time is treated as fresh (criterion 5)",
     '    if text is None:\n        return dict(found, why="it records no retrieval time")', '    if text is None:\n        return dict(found, stale=False, why="no time recorded, so taken as new")'),
    ("B. A retrieval time that cannot be read is treated as fresh (criterion 5)",
     '    if moment is None:\n        return dict(found, why="its retrieval time cannot be read as a time in UTC")', '    if moment is None:\n        return dict(found, stale=False, why="time not understood, so taken as new")'),
    ("C. A retrieval time later than the clock is treated as fresh (criterion 5)",
     '    if moment > now:', '    if False:'),
    ("D. An item is called stale at exactly its limit, where the policy says more than (criterion 7)",
     '    if found["age"] > limits[kind]:', '    if found["age"] >= limits[kind]:'),
    ("E. Every kind is given the longest limit, 90 days (criterion 2)",
     '    if found["age"] > limits[kind]:', '    if found["age"] > limits["decision"]:'),
    ("F. The limits are fixed in the code and the policy's numbers are ignored (criteria 2 and 7)",
     '        limits[kind] = Limit(hours=int(number) * (24 if unit.startswith("day") else 1))', '        limits[kind] = Limit(hours=24)'),
    ("G. Stale items are left out of the list of context used (safety rule: do not hide stale context)",
     '        used.append(entry)\n        return entry', '        if not entry["stale"]:\n            used.append(entry)\n        return entry'),
    ("H. A stale status is stated as current (criterion 4)",
     '        if item["status"]["stale"] or not isinstance((fields or {}).get("status"), str):', '        if not isinstance((fields or {}).get("status"), str):'),
    ("I. A stale release scope still gives a confident count: the quest's scenario (criterion 4)",
     '    if scope["stale"]:\n        out += ["ANSWER: CANNOT SAY', '    if False:\n        out += ["ANSWER: CANNOT SAY'),
    ("J. The stale items are counted and not named (criterion 4)",
     '        out += ["  %s (%s): %s." % (entry["name"], entry["kind"], entry["why"]) for entry in oldest_first(stale)]', '        out += []'),
    ("K. The newest context is reported as the oldest (criterion 3)",
     'key=lambda entry: (entry["age"] is not None, -(entry["age"] or datetime.timedelta(0)).total_seconds(), entry["name"])',
     'key=lambda entry: (entry["age"] is not None, (entry["age"] or datetime.timedelta(0)).total_seconds(), entry["name"])'),
    ("L. An item of unknown age is listed last, as if it were the newest (criteria 3 and 5)",
     'key=lambda entry: (entry["age"] is not None,', 'key=lambda entry: (entry["age"] is None,'),
    ("M. The clock given with --now is ignored and the computer's clock is used (criterion 6)",
     '            now, clock_note = parse_time(args.now), "set with --now"', '            now, clock_note = (datetime.datetime.now(UTC).replace(microsecond=0) if parse_time(args.now) else None), "set with --now"'),
    ("N. A field's own retrieval time is ignored (stretch goal: per-field staleness)",
     '    if field and isinstance(own, dict) and field in own:', '    if False:'),
    ("O. A stale decision is still applied (criterion 4)",
     '            (old_decisions if decision["stale"] else set_aside)[item_id] = decision', '            set_aside[item_id] = decision'),
    ("P. Stale ownership is still used to name owners (criterion 4)",
     'if team["fields"] and not team["stale"] and isinstance', 'if team["fields"] and isinstance'),
    ("Q. A qualified answer exits as if nothing were stale (criterion 4)",
     '    print("\\n".join(out))\n    return 1 if stale else 0', '    print("\\n".join(out))\n    return 0'),
    ("R. Refresh fetches every item, not only the stale ones (stretch goal)",
     'for entry in used if entry["stale"]))\n    fresh = ', 'for entry in used))\n    fresh = '),
    ("S. Text from an item is put into the answer unquoted (safety: text is content)",
     '    return json.dumps(" ".join(str(text).split()))', '    return str(text)'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_answer\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken freshness check? context-staleness, attempt context-attempt-001",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/context-freshness/answer.py, every test was run, and the",
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
    out += ["After the last bug was taken out: answer.py is %s it was at the start. %s"
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
