#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the ba-search-existing-work quest.

Puts one bug at a time into participant/skills/ba-search-existing-work/search.py,
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
SKILL = os.path.join(ROOT, "participant", "skills", "ba-search-existing-work")
TARGET = os.path.join(SKILL, "search.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The same description is a duplicate with nothing to back it up (criterion 3)",
     '    if said_the_same and backed_up:', '    if said_the_same:'),
    ("B. Enough points make a duplicate, whatever the descriptions say (criterion 3)",
     '    if said_the_same and backed_up:', '    if score >= 7:'),
    ("C. Any two signals make an item related, a title and a label included (criteria 3 and 4)",
     '    elif said_the_same or (len(matched) >= 2 and backed_up):', '    elif said_the_same or len(matched) >= 2:'),
    ("D. One signal makes an item related, so a title alone is a match (criterion 4)",
     '    elif said_the_same or (len(matched) >= 2 and backed_up):', '    elif said_the_same or len(matched) >= 1:'),
    ("E. When nothing matches, the closest items are returned as related (criterion 4)",
     '        elif matched:\n            dismissed.append(found)',
     '        elif matched:\n            matches.append(dict(found, kind="related", level="low", advice="link"))'),
    ("F. The same description with nothing else in common is dropped without a word (criterion 3)",
     '    elif said_the_same or (len(matched) >= 2 and backed_up):', '    elif len(matched) >= 2 and backed_up:'),
    ("G. One shared word makes the descriptions match (criterion 1)",
     'signals["description"] = (len(shared) >= 4 and share >= threshold,', 'signals["description"] = (len(shared) >= 1,'),
    ("H. The threshold given on the command line is not used (the first stretch goal)",
     '            result = search(proposal, items, threshold)', '            result = search(proposal, items)'),
    ("I. The same document counts as the same source, whatever the item (criterion 1)",
     'signals["source"] = (bool(shared), "the same item', 'signals["source"] = (bool(documents), "the same item'),
    ("J. Components are compared with letter case (criterion 1)",
     'same = proposal["component"].lower() == item["component"].lower()', 'same = proposal["component"] == item["component"]'),
    ("K. A signal that cannot be compared is counted as a match (criterion 2)",
     '        signals[which] = (None, "cannot compare', '        signals[which] = (True, "cannot compare'),
    ("L. A finished duplicate is recommended for merging (criterion 5)",
     'advice = "merge" if kind == "duplicate" and level == "high" and not finished else "link"',
     'advice = "merge" if kind == "duplicate" and level == "high" else "link"'),
    ("M. A duplicate of medium strength is recommended for merging (criterion 5)",
     'advice = "merge" if kind == "duplicate" and level == "high" and not finished else "link"',
     'advice = "merge" if kind == "duplicate" and not finished else "link"'),
    ("N. A related item is recommended for merging (criteria 3 and 5)",
     'advice = "merge" if kind == "duplicate" and level == "high" and not finished else "link"',
     'advice = "merge" if not finished else "link"'),
    ("O. High strength starts at 8 points, not 9 (criterion 2)",
     'LEVELS = (("high", 9), ("medium", 5), ("low", 0))', 'LEVELS = (("high", 8), ("medium", 5), ("low", 0))'),
    ("P. The overall recommendation is the least cautious one (criterion 5)",
     'overall = min((m["advice"] for m in matches), key=ADVICE.index)', 'overall = max((m["advice"] for m in matches), key=ADVICE.index)'),
    ("Q. A cancelled item is treated as still open (criterion 5)",
     'FINISHED = ("done", "closed", "cancelled", "resolved")', 'FINISHED = ("done", "closed", "resolved")'),
    ("R. Two catalog items with one id are both read (the catalog)",
     '        if item_id in seen:', '        if False:'),
    ("S. A catalog section that cannot be read is skipped without a word (the catalog)",
     'or not title.strip():\n            raise Stop(', 'or not title.strip():\n            continue\n            raise Stop('),
    ("T. A line in a description that looks like a field is read as one (catalog text is text)",
     '            elif line.strip() and not found:\n                break', '            elif line.strip() and not found:\n                pass'),
    ("U. An item with no status is read as open (the catalog)",
     '        if not item.get("status"):', '        if False:'),
    ("V. The report may be written over the catalog (criterion 6)",
     '        if args.report and os.path.exists(args.report) and os.path.samefile(args.report, catalog):', '        if False:'),
    ("W. With no decision given, the search writes its own recommendation as the decision (criterion 5)",
     'markdown_for(proposal, result, catalog, args.decision, args.decision_note)', 'markdown_for(proposal, result, catalog, args.decision or result["overall"], args.decision_note)'),
    ("X. A vertical bar in a catalog title is not escaped in the report (catalog text is text)",
     '    for ch in "\\\\`*_[]|#~":', '    for ch in "\\\\`*_[]#~":'),
    ("Y. A proposal may hold names the search does not know (proposals)",
     '    if not isinstance(data, dict) or not set(data) <= allowed:', '    if not isinstance(data, dict):'),
    ("Z. In the related map an item is compared with itself (the second stretch goal)",
     '        if proposal.get("id") and item["id"] == proposal["id"]:', '        if False:'),
    ("AA. The related map lists items with a single match as having several (the second stretch goal)",
     'several = {key: value for key, value in found.items() if len(value) >= 2}', 'several = {key: value for key, value in found.items() if len(value) >= 1}'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_search\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken search? ba-search-existing-work, attempt ba-attempt-003",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/ba-search-existing-work/search.py, every test was run, and the",
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
