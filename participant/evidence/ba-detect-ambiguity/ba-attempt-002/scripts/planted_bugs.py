#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-detect-ambiguity quest.

Puts one bug at a time into participant/skills/requirements-review/check.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes check.py while it runs. Do not run the checker at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "requirements-review")
TARGET = os.path.join(SKILL, "check.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A finding may name any type, or none (criterion 1)",
     '        if kind not in TYPES:', '        if False:'),
    ("B. A finding that is not a contradiction may name two requirements (criterion 1)",
     '        elif len(named) > 1:', '        elif False:'),
    ("C. Quoted words are not looked for in the requirement (criterion 2)",
     '                elif target in requirements and squeeze(words) not in requirements[target]:', '                elif False:'),
    ("D. Quoted words are matched without regard to capital letters, so a near miss passes (criterion 2)",
     'squeeze(words) not in requirements[target]:', 'squeeze(words).lower() not in requirements[target].lower():'),
    ("E. A finding may name a requirement that does not exist (criterion 2)",
     '            if req not in requirements:\n                problems.append((2, "%s names %s', '            if False:\n                problems.append((2, "%s names %s'),
    ("F. Only the first line of a requirement is read, so words on its second line are not found (criterion 2)",
     '        elif current:\n            found[current] += " " + line.strip()', '        elif current:\n            pass'),
    ("G. What a tester could not decide, and what goes wrong, need not be said (criterion 3)",
     '            if len(lines.get(label, "")) < 15:', '            if False:'),
    ("H. A contradiction may name one requirement (criterion 4)",
     '            if len(set(named)) != 2:', '            if False:'),
    ("I. A contradiction need not quote both requirements (criterion 4)",
     '                if req not in finding["words"]:', '                if False:'),
    ("J. A requirement with no finding and no place in the unflagged list goes unnoticed (criterion 5)",
     '        if req not in flagged and req not in left:', '        if False:'),
    ("K. A requirement may have a finding and be listed as unflagged as well (criterion 5)",
     '        if req in flagged and req in left:', '        if False:'),
    ("L. A requirement may be listed as unflagged with no reason (criterion 5)",
     '            if len(reason) < 20:', '            if False:'),
    ("M. A finding need not ask a question (criterion 6)",
     '        if not question.rstrip().endswith("?"):', '        if False:'),
    ("N. A finding may offer wording in place of a question (criterion 6)",
     '            if phrase in said:', '            if False:'),
    ("O. A finding may be about a person and not the words (safety rule)",
     '        if re.search(r"\\b(the author|the writer|whoever wrote)\\b", said):', '        if False:'),
    ("P. The definitions need not be in the findings file (criterion 7)",
     '        if not re.search(r"\\*\\*%s\\b" % word, lower):', '        if False:'),
    ("Q. The definitions may be given in any order (criterion 7)",
     '    if all(position >= 0 for position in order) and order != sorted(order):', '    if False:'),
    ("R. A review that breaks its rules still exits as accepted",
     '        print("RESULT: NOT ACCEPTED.")\n        return 1', '        print("RESULT: NOT ACCEPTED.")\n        return 0'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_check\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken checker? ba-detect-ambiguity, attempt ba-attempt-002",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/requirements-review/check.py, every test was run, and the",
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
    out += ["After the last bug was taken out: check.py is %s it was at the start. %s"
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
