#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-delta-sync quest.

Puts one bug at a time into participant/skills/trello-delta-sync/sync.py,
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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-delta-sync")
TARGET = os.path.join(SKILL, "sync.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The activity is not read: only the cross-check of card fields finds changes (criterion 1)",
     '            newest, named = (activity[-1] if activity else None), cards_named(activity)',
     '            newest, named = (activity[-1] if activity else None), {}'),
    ("B. The activity is asked for from the beginning, not since the cursor (criterion 1)",
     'dict(params, since=cursor["action_id"])', 'dict(params)'),
    ("C. Every card is fetched, not only those with new activity (criterion 1)",
     '            for card_id in sorted(set(named) | set(silent) | set(missing)):',
     '            for card_id in sorted(set(named) | set(silent) | set(missing) | on_board):'),
    ("D. A change with no activity entry is not looked for: the cross-check is off (criteria 1 and 7)",
     '            silent = sorted(row["id"] for row in listing if row["id"] not in named and',
     '            silent = sorted(row["id"] for row in [] if row["id"] not in named and'),
    ("E. A card's list is not updated when it moves (criterion 2)",
     'KEPT = ("short_link", "name", "list_id", "closed",', 'KEPT = ("short_link", "name", "closed",'),
    ("F. A move is not recognised in the activity (criterion 2)",
     '    if kind == "updateCard" and "idList" in old:', '    if kind == "updateCard" and "idlist" in old:'),
    ("G. An archived card is not flagged as archived (criterion 3)",
     'words.append("ARCHIVED in Trello. Flagged, and kept with its notes" if card["closed"] else "restored from the archive")',
     'words.append("restored from the archive")'),
    ("H. An archived card stays in its list in cards.md (criterion 3)",
     '    archived = lambda c: c["closed"] or lists.get(c["list_id"], {}).get("closed", False)',
     '    archived = lambda c: lists.get(c["list_id"], {}).get("closed", False)'),
    ("I. Archived cards are not asked for in the listing, so an archived card looks gone (criterion 3)",
     '{"filter": "all", "fields": "dateLastActivity"}', '{"filter": "visible", "fields": "dateLastActivity"}'),
    ("J. The cursor is written before the cards are fetched (criterion 4)",
     '        lists = read_lists(client, board["id"])',
     '        lists = read_lists(client, board["id"])\n'
     '        if newest is not None and not whole:\n'
     '            state["cursor"] = {"action_id": newest["id"], "action_date": str(newest.get("date", "")), "taken_from": CURSOR_SOURCE}\n'
     '            write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\\n", out_dir)'),
    ("K. A card that cannot be fetched is skipped and the sync carries on (criteria 4 and 5)",
     '    if status != 200 or not isinstance(body, dict) or body.get("id") != card_id:\n        raise Stop(',
     '    if status != 200 or not isinstance(body, dict) or body.get("id") != card_id:\n        return "gone", "skipped"\n        raise Stop('),
    ("L. The cursor is taken from this machine's clock (criterion 4)",
     'state["cursor"] = {"action_id": newest["id"], "action_date": str(newest.get("date", "")), "taken_from": CURSOR_SOURCE}',
     'state["cursor"] = {"action_id": newest["id"], "action_date": now, "taken_from": CURSOR_SOURCE}'),
    ("M. The cursor is set to the oldest new entry, not the newest (criteria 4 and 5)",
     '            newest, named = (activity[-1] if activity else None), cards_named(activity)',
     '            newest, named = (activity[0] if activity else None), cards_named(activity)'),
    ("N. A rate-limited sync is treated as finished (criterion 4)",
     '    except RateLimited:\n        say("INCOMPLETE', '    except Stop:\n        say("INCOMPLETE'),
    ("O. The first page of activity is taken for all of it (criterion 5)",
     '        if len(page) < page_size:\n            return rows', '        if page is not None:\n            return rows'),
    ("P. Entries at or before the cursor are not dropped (criterion 1)",
     'fresh = sorted((row for row in rows if row["id"] > cursor["action_id"]), key=lambda row: row["id"])',
     'fresh = sorted(rows, key=lambda row: row["id"])'),
    ("Q. Reading a notes file adds a line to it (criterion 6)",
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()',
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()\n'
     '                with open(path, "a") as f:\n                    f.write("\\n")'),
    ("R. Writing in the notes folder is no longer refused (criterion 6)",
     '    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:', '    if False:'),
    ("S. The digest leaves out which list a card is in (criterion 7)",
     'cards = {card_id: {field: card[field] for field in KEPT}', 'cards = {card_id: {field: card[field] for field in KEPT if field != "list_id"}'),
    ("T. The digest depends on when the sync ran (criterion 7)",
     'text = json.dumps({"lists": state["lists"], "cards": cards}, sort_keys=True, ensure_ascii=False)',
     'text = json.dumps({"lists": state["lists"], "cards": cards, "at": state["last_successful_sync"]}, sort_keys=True, ensure_ascii=False)'),
    ("U. A card's labels are not kept (criterion 7)",
     '"labels": sorted(str(l.get("name") or l.get("color") or "") for l in row.get("labels") or [] if isinstance(l, dict)),',
     '"labels": [str(l.get("id")) for l in row.get("labels") or [] if isinstance(l, dict)][:0],'),
    ("V. A deleted card is removed from the local copy (the first stretch goal)",
     '            state["cards"][card_id].update(status="gone", gone_reason=why, gone_since=now)\n            counts["gone"].append(card_id)',
     '            counts["gone"].append(card_id)\n    for card_id in counts["gone"]:\n        state["cards"].pop(card_id)'),
    ("W. A card moved to another board is kept as if still here (the first stretch goal)",
     '    if body.get("idBoard") != board_id:', '    if False:'),
    ("X. A card that vanishes with no activity entry is not noticed (the first stretch goal)",
     '            missing = sorted((held - on_board) - set(named))', '            missing = []'),
    ("Y. A failed sync makes the cursor look fresh (the second stretch goal)",
     '    notes_before = notes_checksums(out_dir)\n    state = load_state(out_dir)',
     '    notes_before = notes_checksums(out_dir)\n    state = load_state(out_dir)\n    if state is not None:\n'
     '        state["last_successful_sync"] = now\n'
     '        write_text(os.path.join(out_dir, "state.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\\n", out_dir)'),
    ("Z. STALE is never said (the second stretch goal)",
     '    if since is not None and since > stale_hours:', '    if since is not None and since > stale_hours * 1000:'),
    ("AA. Text from an activity entry is printed (card text is text)",
     '    return {"createCard": "created", "copyCard": "created as a copy", "commentCard": "commented on",',
     '    if kind == "commentCard":\n        return "commented: %s" % data.get("text")\n'
     '    return {"createCard": "created", "copyCard": "created as a copy", "commentCard": "commented on",'),
    ("AB. The key and token are put in the address (safety)",
     '    url = "https://%s/1%s" % (API_HOST, path)', '    url = "https://%s/1%s?key=%s&token=%s" % (API_HOST, path, key, token)'),
    ("AC. The request is not a GET (safety)", 'method="GET"', 'method="POST"'),
    ("AD. A folder holding made-up cards may be synced from live Trello (safety)",
     '    if state is not None and state["source"] != source:', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync? trello-delta-sync, attempt trello-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-delta-sync/sync.py, every test was run, and the",
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
