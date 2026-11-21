#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-read-assigned-cards quest.

Puts one bug at a time into participant/skills/trello-read-assigned-cards/sync.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes sync.py while it runs. Do not run a sync at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-read-assigned-cards")
TARGET = os.path.join(SKILL, "sync.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The member is written into the skill instead of read from the connection (criterion 1)",
     '    return body["id"]', '    return "5f0000000000000000000001"'),
    ("B. Only open boards are asked for, so a closed board is never searched (criteria 2 and 4)",
     '"/members/me/boards", {"filter": "all"', '"/members/me/boards", {"filter": "open"'),
    ("C. Only the first board is searched (criterion 2)",
     '        for board in boards:', '        for board in boards[:1]:'),
    ("D. Other members' cards are kept as the member's (criterion 2)",
     '        if member_id not in members:', '        if False:'),
    ("E. Reading stops after the first page (criterion 3)",
     '        if len(page) < page_size:', '        if page is not None:'),
    ("F. The next page is never asked for: `before` is not sent (criterion 3)",
     'params["before"] = min(seen)', 'params["before_"] = min(seen)'),
    ("G. A full page with nothing new is taken as the end (criterion 3)",
     '        if not fresh:', '        if not fresh:\n            return rows, pages'),
    ("H. What was found is not compared with Trello's own list of the member's cards (criterion 3)",
     '    if missed:', '    if False:'),
    ("I. The saved count is not counted from the index: heading rows are counted as cards (criterion 3)",
     ' and not line.startswith("| Card |"):', ':'),
    ("J. Archived cards are not asked for (criterion 4)",
     '{"filter": "all", "fields": CARD_FIELDS}', '{"filter": "visible", "fields": CARD_FIELDS}'),
    ("K. A card in an archived list counts as open (criterion 4)",
     '("list", in_list.get("closed"))', '("list", False)'),
    ("L. A card on a closed board counts as open (criterion 4)",
     '("board", board["closed"])', '("board", False)'),
    ("M. Archived cards are listed and counted with the open ones (criterion 4)",
     'is_open = order(c for c in mine if not c["archived_by"])', 'is_open = order(c for c in mine)'),
    ("N. A renamed card is counted as a new card (criterion 5)",
     '        if old is None:\n            changes["new"]', '        if old is None or old.get("name") != record["name"]:\n            changes["new"]'),
    ("O. The time a card was first seen is replaced at every sync (criterion 5)",
     'first_seen=old["first_seen"] if old else now', 'first_seen=now'),
    ("P. A card no longer assigned is deleted from the memory (criterion 6)",
     '    state.update(boards=searched, restricted=restricted, last_successful_sync=now)',
     '    state.update(boards=searched, restricted=restricted, last_successful_sync=now)\n'
     '    state["cards"] = {k: v for k, v in state["cards"].items() if v["status"] == "assigned"}'),
    ("Q. A card no longer assigned is left out of the index (criterion 6)",
     'gone = order(c for c in cards if c["status"] != "assigned")', 'gone = []'),
    ("R. A card that is still the member's, on a board not searched, is called reassigned (criterion 6)",
     '    if member_id in others:', '    if False:'),
    ("S. A deleted card is not recognised (criterion 6)",
     '    if status == 404:', '    if status == 4040:'),
    ("T. A card assigned again stays flagged (criterion 6)",
     'record = dict(card, status="assigned",', 'record = dict(card, status=old["status"] if old else "assigned",'),
    ("U. Reading a notes file adds a line to it (criterion 7)",
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()',
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()\n'
     '                with open(path, "a") as f:\n                    f.write("\\n")'),
    ("V. Writing in the notes folder is no longer refused (criterion 7)",
     '    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:', '    if False:'),
    ("W. A folder holding another member's cards is synced into (criterion 1)",
     '    if state.get("member_id") != member_id:', '    if False:'),
    ("X. A folder holding made-up cards may be synced from live Trello (safety)",
     '    if state.get("source") != source:', '    if False:'),
    ("Y. The key and token are put in the address (safety)",
     '    url = "https://%s/1%s" % (API_HOST, path)', '    url = "https://%s/1%s?key=%s&token=%s" % (API_HOST, path, key, token)'),
    ("Z. The request is not a GET (safety)",
     'method="GET"', 'method="POST"'),
    ("AA. A vertical bar in a card name is not escaped in the index (card text is text)",
     '.replace("|", "\\\\|")', ''),
    ("AB. A restricted search does not say so in the index (criterion 2)",
     '(len(state["boards"]), state.get("restricted") or "")', '(len(state["boards"]), "")'),
    ("AC. A card that is only the member's is listed as shared (the first stretch goal)",
     'others = lambda c: len([m for m in c["member_ids"] if m != me])', 'others = lambda c: len(c["member_ids"])'),
    ("AD. Archived cards are listed as quiet (the second stretch goal)",
     'quiet = [c for c in is_open if', 'quiet = [c for c in mine if'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync? trello-read-assigned-cards, attempt trello-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-read-assigned-cards/sync.py, every test was run, and the",
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
    out += ["After the last bug was taken out: sync.py is %s it was at the start. %s"
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
