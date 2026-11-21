#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-duplicate-search quest.

Puts one bug at a time into participant/skills/trello-duplicate-search/search.py,
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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-duplicate-search")
TARGET = os.path.join(SKILL, "search.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The name counts as one of the three signals (criteria 1 and 4)",
     '    beyond = [name for name, _ in BEYOND_NAME if signals[name][0] is True]',
     '    beyond = [name for name, _ in WEIGHTS if signals[name][0] is True]'),
    ("B. Two signals beyond the name are enough (criterion 1)",
     'MIN_SIGNALS = 3', 'MIN_SIGNALS = 2'),
    ("C. A card with a name alike is always reported (criterion 4)",
     '    if len(beyond) < MIN_SIGNALS:', '    if len(beyond) < MIN_SIGNALS and "name" not in matched:'),
    ("D. A card is reported only if its name is alike too, so a different name hides a duplicate (criterion 5)",
     '    if len(beyond) < MIN_SIGNALS:', '    if len(beyond) < MIN_SIGNALS or "name" not in matched:'),
    ("E. Only the board the card would go on is searched (criterion 3)",
     '        for entry in board["cards"]:', '        for entry in (board["cards"] if board["id"] == proposal["board"] else []):'),
    ("F. Only the first board folder is read (criterion 3)",
     '    for name in names:\n        path = os.path.join(folder, name)', '    for name in names[:1]:\n        path = os.path.join(folder, name)'),
    ("G. Labels are compared with letter case, so Finance and finance differ (signals)",
     '    return set(item.strip().lower() for item in items if item.strip())', '    return set(item.strip() for item in items if item.strip())'),
    ("H. A signal that cannot be compared is counted as a match (signals)",
     '        signals[which] = (None, "cannot compare', '        signals[which] = (True, "cannot compare'),
    ("I. Due dates up to thirty days apart match (signals)", 'DUE_DAYS = 3', 'DUE_DAYS = 30'),
    ("J. One shared word makes the descriptions match (signals)",
     'len(shared) >= 4 and share >= 0.5', 'len(shared) >= 1'),
    ("K. One alike checklist item makes the checklists match (signals)",
     'same >= 2 and same * 2 >= len(short)', 'same >= 1'),
    ("L. Any member on either card counts as a shared member (signals)",
     'shared = sorted(set(proposal["members"]) & set(entry["members"]))', 'shared = sorted(set(proposal["members"]) | set(entry["members"]))'),
    ("M. A stale index is searched anyway (criterion 7, and the stale check)",
     '        if index.matches(path, files):', '        if False and index.matches(path, files):'),
    ("N. The search rebuilds a stale index itself, so it changes the index (criterion 7)",
     '            files = index.render(index.scan(path), name)\n',
     '            files = index.render(index.scan(path), name)\n            for n in files:\n                open(os.path.join(path, n), "wb").write(files[n])\n'),
    ("O. Archive-as-duplicate is never recommended (criterion 7)",
     '    elif same_board and level == "high":', '    elif False:'),
    ("P. Archive-as-duplicate is recommended for a card on another team's board (criterion 7)",
     '    elif same_board and level == "high":', '    elif level == "high":'),
    ("Q. An archived or complete card is treated as open (recommendation)",
     '    if finished:\n        advice = "proceed"', '    if False:\n        advice = "proceed"'),
    ("R. A card marked complete is not seen as finished (recommendation)",
     'else "marked complete" if entry["due_complete"] else None)', 'else None)'),
    ("S. High confidence starts at 8 points, not 10 (criterion 2, the scale)",
     'LEVELS = (("high", 10), ("medium", 7), ("low", 0))', 'LEVELS = (("high", 8), ("medium", 7), ("low", 0))'),
    ("T. The overall recommendation is the least cautious one (criterion 7)",
     'overall = min((c["advice"] for c in candidates), key=ADVICE.index)', 'overall = max((c["advice"] for c in candidates), key=ADVICE.index)'),
    ("U. A card that matched on one signal is put among the candidates (criteria 4 and 6)",
     '            if level:\n                candidates.append(found)', '            if level or matched:\n                candidates.append(found)'),
    ("V. The report may be written over an index (criterion 7)",
     '        if args.report and os.path.commonpath(', '        if False and os.path.commonpath('),
    ("W. With no decision given, the search writes its own recommendation as the decision (criterion 7)",
     'markdown_for(proposal, result, args.decision, args.decision_note)', 'markdown_for(proposal, result, args.decision or result["overall"], args.decision_note)'),
    ("X. A vertical bar in a card name is not escaped in the report (card text is text)",
     '    for ch in "\\\\`*_[]|#~":', '    for ch in "\\\\`*_[]#~":'),
    ("Y. A proposal may hold names the search does not know (proposals)",
     '    if not isinstance(data, dict) or not set(data) <= allowed:', '    if not isinstance(data, dict):'),
    ("Z. The board the card would go on need not be one of those searched (criterion 3)",
     '    if proposal["board"] not in [board["id"] for board in boards]:', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_search\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken search? trello-duplicate-search, attempt trello-attempt-004",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-duplicate-search/search.py, every test was run, and the",
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
