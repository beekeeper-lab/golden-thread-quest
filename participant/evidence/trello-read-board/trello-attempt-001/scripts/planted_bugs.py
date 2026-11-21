#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-read-board quest.

Puts one bug at a time into participant/skills/trello-read-board/sync.py, runs
every test, notes which tests fail, and takes the bug out again. At the end it
checks that sync.py is the same as when it started, byte for byte.

It changes sync.py while it runs. Do not run the skill at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and sync.py was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
SKILL = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", "skills", "trello-read-board"))
SYNC = os.path.join(SKILL, "sync.py")

# (what the bug is, the text in sync.py to replace, what to replace it with)
BUGS = [
    ("A. Cards are matched by name, not by Trello id",
     'old = held.get(card["id"])',
     'old = next((c for c in held.values() if c["name"] == card["name"]), None)'),
    ("B. Archived cards are not asked for",
     '{"filter": "all", "fields": CARD_FIELDS}', '{"filter": "visible", "fields": CARD_FIELDS}'),
    ("C. A comment already held is added again",
     '            known[comment["id"]] = dict(comment, returned=True)',
     '            known[comment["id"] + now] = dict(comment, returned=True)'),
    ("D. A card Trello stops returning is deleted from the local copy",
     '        if card_id not in returned and old.get("state") != "not_returned":',
     '        if card_id not in returned:\n            continue\n        if False:'),
    ("E. Lists are put in name order, not board order",
     'lists.sort(key=lambda item: (item["pos"], item["id"]))',
     'lists.sort(key=lambda item: (item["name"], item["id"]))'),
    ("F. Checklist items are added to the card's description",
     '            "description": str(row.get("desc", "")),',
     '            "description": str(row.get("desc", "")) + "\\nLayout agreed",'),
    ("G. Text from Trello is put in a fixed three-backtick block",
     '    fence = "`" * max(3, longest + 1)', '    fence = "```"'),
    ("H. A rate-limited run carries on and writes what it has",
     '        return 2\n    for card in cards:', '        comments = {}\n    for card in cards:'),
    ("I. The author's name is asked for with each comment",
     '"memberCreator": "false", "member": "false"}',
     '"memberCreator": "true", "memberCreator_fields": "fullName"}'),
    ("J. The skill is given a way to send a write",
     'request = urllib.request.Request(url, method="GET")',
     'request = urllib.request.Request(url, method="GET" if not params.get("_write") else "POST")'),
    ("K. A full page holding nothing new is taken as the end of the board",
     '        if not fresh:\n            # A full page', '        if not fresh:\n            return rows\n        if False:\n            # A full page'),
    ("L. A rate limit is waited on with no limit on the number of waits (stopped here at 50)",
     '            if waited == MAX_WAITS:', '            if waited == 50:'),
    ("M. The wait is a fixed 10 seconds, whatever Trello's answer says",
     '            seconds = self._wait_for(headers)', '            seconds = DEFAULT_WAIT_SECONDS'),
    ("N. The reconciliation file leaves out cards Trello did not return",
     '    missing = sorted((c for c in cards if c["state"] == "not_returned"), key=lambda c: c["id"])\n    archived',
     '    missing = []\n    archived'),
    ("O. A card that was not returned is reported again on every later run",
     'if card_id not in returned and old.get("state") != "not_returned":',
     'if card_id not in returned:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(SYNC, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync.py? trello-read-board, attempt trello-attempt-001",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-read-board/sync.py, every test was run, and",
           "the bug was taken out again. No network is used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean = not failed and last.startswith("OK")
    missed = []
    try:
        for title, old, new in BUGS:
            if good.count(old) != 1:
                out += ["PLANTED BUG " + title, "  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(SYNC, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            out += ["PLANTED BUG " + title, "  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + name for name in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(SYNC, "w", encoding="utf-8") as f:
            f.write(good)
    with open(SYNC, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: sync.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and sync.py was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % (", ".join(missed) or "see above"))]
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
