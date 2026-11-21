#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-create-card-preview quest.

Puts one bug at a time into participant/skills/trello-create-card-preview/preview.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes preview.py while it runs. Do not run a preview at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-create-card-preview")
TARGET = os.path.join(SKILL, "preview.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The list is not checked against the stated board (criterion 1)",
     '    if body.get("idBoard") != board["id"]:', '    if False:'),
    ("B. An archived list is accepted (criterion 1, the quest's scenario)",
     '    if body.get("closed") is not False:\n        raise Refused("the list', '    if False:\n        raise Refused("the list'),
    ("C. A board or list may be given by something other than its id (criterion 1)",
     '        if not isinstance(value, str) or not TRELLO_ID.fullmatch(value):', '        if not isinstance(value, str):'),
    ("D. The first list Trello gives is used, not the list the draft names (criterion 1, the quest's scenario)",
     'target = read_list(conn, draft["list"], board, before["lists"])', 'target = read_list(conn, before["lists"][0]["id"], board, before["lists"])'),
    ("E. The sandbox allowlist is ignored (the target)",
     '    if draft["board"] not in load_allowlist(args.allowlist):', '    if False:'),
    ("F. A label that does not exist is dropped without a word (criteria 2 and 3)",
     '        if not matches:\n', '        if not matches:\n            continue\n'),
    ("G. A label is matched without regard to letter case (criterion 2)",
     'matches = [row["id"] for row in labels if row.get("name") == name]',
     'matches = [row["id"] for row in labels if str(row.get("name")).lower() == name.lower()]'),
    ("H. Of two labels with one name, the first is used (criterion 2)",
     '        if len(matches) > 1:', '        if False:'),
    ("I. A member is not checked against the board's members (criterion 2)",
     '        if member not in on_board:', '        if False:'),
    ("J. A draft with no position gets bottom by default (criterion 5)",
     "    else:\n        raise Refused('the draft must say where",
     "    else:\n        draft[\"position\"] = \"bottom\"\n    if False:\n        raise Refused('the draft must say where"),
    ("K. The position is shown in the field list and left out of the payload (criterion 5)",
     '    put("pos", draft["position"], json.dumps(draft["position"]))', '    rows.append(("pos", json.dumps(draft["position"]), None))'),
    ("L. The payload saved for the write differs from the payload shown (criterion 5)",
     '"request": REQUEST, "payload": payload,', '"request": REQUEST, "payload": dict(payload, pos="top"),'),
    ("M. The SHA-256 shown is of the indented text, not of the bytes that would be sent (criterion 5)",
     '    digest = hashlib.sha256(body).hexdigest()', '    digest = hashlib.sha256(pretty(payload).encode("utf-8")).hexdigest()'),
    ("N. The bytes are not in a fixed order of names (criterion 5)",
     'return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")',
     'return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")'),
    ("O. The description's line breaks are lost on the way into the payload (criterion 5)",
     '        put("desc", draft["description"],', '        put("desc", " ".join(draft["description"].split()),'),
    ("P. A token that may not write is treated as ready (criterion 4)",
     '    if not may_write:', '    if False:'),
    ("Q. An observer is treated as able to add cards (criterion 4)",
     '    if role in ("admin", "normal"):', '    if role in ("admin", "normal", "observer"):'),
    ("R. When Trello does not give the token's permissions, writing is assumed (criterion 4)",
     '        reasons.append("Trello did not say what this token may do, so it is not assumed that it may write")', '        pass'),
    ("S. A token's permission for some other board counts for this one (criterion 4)",
     'row.get("idModel") in ("*", board["id"])]', 'row.get("idModel")]'),
    ("T. A likely duplicate with no decision does not hold the write back (criterion 4)",
     '        elif uncovered:', '        elif False:'),
    ("U. Any recorded decision covers any candidate (criterion 4)",
     '        uncovered = [item for item in found if item not in draft["candidates"]]', '        uncovered = [] if draft["decision"] else found'),
    ("V. The index is not compared with Trello's card count (criterion 4)",
     '    if local < in_trello:', '    if False:'),
    ("W. A preview that is not ready is saved for a write, as ready (the verdict)",
     '    if ready:\n        say("VERDICT: READY', '    if True:\n        say("VERDICT: READY'),
    ("X. The board snapshots before and after are not compared (criterion 6)",
     '    if after["shown"] != before["shown"]:', '    if False:'),
    ("Y. The snapshot leaves out the lists (criterion 6)",
     '    seen += sorted([row["id"], str(row.get("name")), str(row.get("pos")), str(row.get("closed"))] for row in lists)', '    seen += []'),
    ("Z. A citation's quoted words are not checked against the file (criterion 7)",
     '        if " ".join(source["quote"].split()) not in there:', '        if False:'),
    ("AA. Content with no citation is accepted (criterion 7)",
     '    if missing:\n        raise Refused("the draft gives no source', '    if False:\n        raise Refused("the draft gives no source'),
    ("AB. The request path holding the token is written into the list of requests (credentials)",
     'self.sent.append(("GET", PATH_SHOWN if path == self._token_path else path))', 'self.sent.append(("GET", path))'),
    ("AC. The output is not searched for the key and the token (credentials)",
     '    if any(secret and secret in piece for secret in secrets for piece in [text] + list(files.values())):', '    if False:'),
    ("AD. A due time in the past is accepted (the draft)",
     '    if draft["due"] and datetime.datetime.strptime(draft["due"], "%Y-%m-%dT%H:%M:%S.%fZ") < args.now:', '    if False:'),
    ("AE. Archived cards are counted when working out where the card would sit (where in the list)",
     'if row.get("idList") == draft["list"] and row.get("closed") is False\n', 'if row.get("idList") == draft["list"]\n'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_preview\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken preview? trello-create-card-preview, attempt trello-attempt-005",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-create-card-preview/preview.py, every test was run, and the",
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
    out += ["After the last bug was taken out: preview.py is %s it was at the start. %s"
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
