#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-build-index quest.

Puts one bug at a time into participant/skills/jira-build-index/index.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes index.py while it runs. Do not build the catalog at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "jira-build-index")
TARGET = os.path.join(SKILL, "index.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A record with a gap is left out of the catalog (criteria 2 and 4)",
     '        else:\n            rows[found["id"]] = found', '        elif not found["gaps"]:\n            rows[found["id"]] = found'),
    ("B. A file that is not a record is skipped without a word (criterion 2)",
     '            skipped.append({"file": name, "reason": found})', '            pass'),
    ("C. A second file with the same issue id replaces the first, unreported (criterion 2)",
     '        elif found["id"] in rows:', '        elif False:'),
    ("D. A file in some other format is indexed as a story (criterion 2)",
     '    if front.get("format") != FORMAT:', '    if False:'),
    ("E. Every file in the folder is read as a record, whatever its kind (criterion 2)",
     'if name.endswith(".md") and os.path.isfile(os.path.join(records, name)))', 'if os.path.isfile(os.path.join(records, name)))'),
    ("F. Rows are ordered by issue id as text, so 10 comes before 9 (criterion 5)",
     'sorted(rows, key=int)', 'sorted(rows)'),
    ("G. The catalog records when it was built (criterion 5)",
     '           "> Rebuild: `%s`" % REBUILD,', '           "> Rebuild: `%s`" % REBUILD, "> Built at %s" % datetime.datetime.now().isoformat(),'),
    ("H. An unchanged catalog is rewritten on every build (criterion 5)",
     '        if on_disk(out, name) == files[name]:', '        if False:'),
    ("I. A story with no assignee in Jira is reported as a gap (criterion 4)",
     '    elif front["assignee"] is None:\n        assignee = UNASSIGNED', '    elif front["assignee"] is None:\n        assignee = None\n        gaps.append("assignee")'),
    ("J. A missing status is filled in with a guess (criterion 4)",
     '    if status is None:\n        gaps.append("status")', '    if status is None:\n        status = "To Do"'),
    ("K. The count of stories with a gap is always shown as none (criterion 4)",
     '"| Stories with a gap | %d |" % sum(1 for entry in entries if entry["gaps"]),', '"| Stories with a gap | %d |" % 0,'),
    ("L. A lookup answers from a catalog that no longer matches the records (criterion 7)",
     '    if cmd_check(records, out, quiet=True) != 0:', '    if False:'),
    ("M. The check looks at catalog.md only, so an edited catalog.json passes (criteria 1 and 7)",
     '    return [name for name in sorted(files) if on_disk(out, name) != files[name]]', '    return [name for name in ["catalog.md"] if on_disk(out, name) != files[name]]'),
    ("N. The fingerprint covers file names only, so a changed record goes unseen (criteria 6 and 7)",
     '        digest.update(("%s %s\\n" % (file_hash, name)).encode("utf-8"))', '        digest.update(name.encode("utf-8"))'),
    ("O. The header no longer says the records are the source of truth (criterion 7)",
     'are the source of truth, not this catalog. To learn what a story holds,', 'are indexed here. To learn what a story holds,'),
    ("P. A lookup by key also matches part of a key (criterion 3)",
     '(e["key"] or "").lower() == args.key.lower()', 'args.key.lower() in (e["key"] or "").lower()'),
    ("Q. A lookup by status needs the exact capital letters (criterion 3)",
     '(e["status"] or MISSING).lower() == args.status.lower()', '(e["status"] or MISSING) == args.status'),
    ("R. A lookup by assignee matches every story (criterion 3)",
     '(e["assignee"] or MISSING) == args.assignee]', '(e["assignee"] or MISSING)]'),
    ("S. A title search matches any one word where it should need all (stretch goal)",
     'all(w in (e["title"] or "").lower() for w in words)', 'any(w in (e["title"] or "").lower() for w in words)'),
    ("T. A pipe character in a title is not escaped, so it splits the table (safety rule: untrusted text)",
     '    for ch in "\\\\`*_[]|#~":', '    for ch in "\\\\`*_[]#~":'),
    ("U. A line break in a title is kept, so a title can add lines to the catalog (safety rule: untrusted text)",
     '    text = " ".join(str(text).split())', '    text = str(text)'),
    ("V. Angle brackets in a title are not escaped (safety rule: untrusted text)",
     '.replace("<", "&lt;")', ''),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_index\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken generator? jira-build-index, attempt jira-attempt-009",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-build-index/index.py, every test was run, and the",
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
    out += ["After the last bug was taken out: index.py is %s it was at the start. %s"
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
