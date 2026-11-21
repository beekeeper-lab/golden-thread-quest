#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-build-index quest.

Puts one bug at a time into participant/skills/trello-build-index/index.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes index.py while it runs. Do not build the index at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-build-index")
TARGET = os.path.join(SKILL, "index.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A card with a gap is left out of the index (every card once; gaps)",
     '        else:\n            rows[found["id"]] = found', '        elif not found["gaps"]:\n            rows[found["id"]] = found'),
    ("B. A file that is not a card record is skipped without a word (every card once)",
     '            skipped.append({"file": name, "reason": found})', '            pass'),
    ("C. A second file with the same card id replaces the first, unreported (no card repeated)",
     '        elif found["id"] in rows:', '        elif False:'),
    ("D. A card of another board is indexed on this one (every card once)",
     'if isinstance(front.get("idBoard"), str) and front["idBoard"] != board_id:', 'if False:'),
    ("E. A file in some other format is indexed as a card",
     '    if front.get("format") != FORMAT:', '    if False:'),
    ("F. Lists are ordered by name (list order)",
     'found.sort(key=lambda item: (item["pos"], item["id"]))', 'found.sort(key=lambda item: (item["name"] or "", item["id"]))'),
    ("G. Lists are left in the order the board record happens to hold them (list order)",
     'found.sort(key=lambda item: (item["pos"], item["id"]))', 'pass'),
    ("H. Cards in a list are ordered by id, not position (card order)",
     'e["pos"] is None, e["pos"] or 0, e["id"]))', 'e["id"]))'),
    ("I. Card positions are compared as text, so 100.5 comes before 20 (card order)",
     'e["pos"] is None, e["pos"] or 0, e["id"]))', 'e["pos"] is None, str(e["pos"] or 0), e["id"]))'),
    ("J. An archived card is dropped from its list (archived cards)",
     '            inside = [card for card in cards if card["list_id"] == item["id"]]',
     '            inside = [card for card in cards if card["list_id"] == item["id"] and not card["closed"]]'),
    ("K. Archived lists are left out, and their cards with them (archived lists)",
     '    for group, heading in ((False, None), (True, "## Archived lists")):', '    for group, heading in ((False, None),):'),
    ("L. A card whose list the board does not have gets no row (every card once)",
     '        out += [row(card) + " %s |" % ("`%s`" % escape(card["list_id"]) if card["list_id"] else MISSING) for card in adrift]', '        pass'),
    ("M. The check that rows equal cards indexed is switched off (row count equals record count)",
     '    if rows != index["counts"]["indexed"]:', '    if False:'),
    ("N. The index records when it was built (same records, same bytes)",
     '           "> Rebuild: `%s`" % REBUILD,', '           "> Rebuild: `%s`" % REBUILD, "> Built at %s" % datetime.datetime.now().isoformat(),'),
    ("O. An unchanged index is rewritten on every build (same records, same bytes)",
     '        if on_disk(out, name) == files[name]:', '        if False:'),
    ("P. A card with no due date is reported as a gap (gaps)",
     '    if "due" not in front or not (front["due"] is None or isinstance(front["due"], str)):',
     '    if not isinstance(front.get("due"), str):'),
    ("Q. A missing closed state is filled in as open (gaps)",
     '    if closed is None:\n        gaps.append("closed state")', '    if closed is None:\n        closed = False'),
    ("R. Missing members are shown as none, not as missing (gaps)",
     '    else:\n        gaps.append("members")', '    else:\n        members = []'),
    ("S. The count of cards with a gap is always shown as none (gaps)",
     '"| Cards with a gap | %d |" % sum(1 for card in cards if card["gaps"]),', '"| Cards with a gap | %d |" % 0,'),
    ("T. A lookup answers from an index that no longer matches the records (stale index)",
     '    if cmd_check(records, out, quiet=True) != 0:', '    if False:'),
    ("U. The check looks at index.md only, so an edited index.json passes (stale index)",
     '    return [name for name in sorted(files) if on_disk(out, name) != files[name]]', '    return [name for name in ["index.md"] if on_disk(out, name) != files[name]]'),
    ("V. The fingerprint leaves out the board record (stale index)",
     '        digest.update(("%s board.json\\n" % hashlib.sha256(f.read()).hexdigest()).encode("utf-8"))', '        pass'),
    ("W. The header no longer says the records are the source of truth (header)",
     'are the source of truth, not this" % (records_name, records_name),', 'are indexed in this" % (records_name, records_name),'),
    ("X. A lookup by list also matches part of a list name (lookup)",
     '(item["name"] or "").lower() == args.list.lower()]', 'args.list.lower() in (item["name"] or "").lower()]'),
    ("Y. A lookup by label also matches part of a label name (lookup)",
     'any(label["name"].lower() == args.label.lower() for label', 'any(args.label.lower() in label["name"].lower() for label'),
    ("Z. A lookup by member matches every card that has a member (lookup)",
     '[card for card in cards if args.member in (card["members"] or [])]', '[card for card in cards if card["members"]]'),
    ("AA. The due lookup counts cards already complete (due in the next seven days)",
     '                        and not card["due_complete"] and card["closed"] is not True)', '                        and card["closed"] is not True)'),
    ("AB. The due lookup counts cards that are already overdue (due in the next seven days)",
     'if parse_time(card["due"]) and now <= parse_time(card["due"]) <= end', 'if parse_time(card["due"]) and parse_time(card["due"]) <= end'),
    ("AC. The due lookup ignores the clock value it is given (due in the next seven days)",
     '        now = parse_time(args.now) if args.now else datetime.datetime.now(UTC).replace(microsecond=0)',
     '        now = datetime.datetime.now(UTC).replace(microsecond=0)'),
    ("AD. A vertical bar in a card name is not escaped, so the name can split a table row (names are text)",
     '    for ch in "\\\\`*_[]|#~":', '    for ch in "\\\\`*_[]#~":'),
    ("AE. A line break in a name is kept, so a name can start a heading (names are text)",
     '    text = " ".join(str(text).split())', '    text = str(text)'),
    ("AF. A list name is written into its heading unescaped (names are text)",
     '            out += ["### %d. %s" % (number_shown, cell(item["name"])), "",', '            out += ["### %d. %s" % (number_shown, item["name"]), "",'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_index\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken generator? trello-build-index, attempt trello-attempt-003",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-build-index/index.py, every test was run, and the",
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
