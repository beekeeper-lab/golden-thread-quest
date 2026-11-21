#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-create-card quest.

Puts one bug at a time into participant/skills/trello-create-card/create.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes create.py while it runs. Do not run the workflow at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-create-card")
TARGET = os.path.join(SKILL, "create.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A confirmation with no name is accepted (criterion 7)",
     '    if not name:', '    if False:'),
    ("B. An email address is accepted as the confirmer's name (criterion 8)",
     '    if len(name) > 60 or "@" in name or', '    if len(name) > 60 or'),
    ("C. A preview's age is not checked (criterion 7)",
     '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):', '    if False:'),
    ("D. The time limit is an hour, not the 15 minutes stated (criterion 7)",
     'LIMIT_MINUTES = 15', 'LIMIT_MINUTES = 60'),
    ("E. A change that differs from the preview is not noticed (criterion 7)",
     '    if found["digest"] != record["payload_sha256"] or sha_of(found["draft"]["path"]) != record["draft_sha256"]:', '    if False:'),
    ("F. An edited draft is accepted when its payload comes out the same (criterion 7)",
     '    if found["digest"] != record["payload_sha256"] or sha_of(found["draft"]["path"]) != record["draft_sha256"]:',
     '    if found["digest"] != record["payload_sha256"]:'),
    ("G. A saved preview that was altered is accepted (criterion 7)",
     '    if genuine != record.get("fingerprint") or genuine[:12] != code:', '    if False:'),
    ("H. The bytes sent are not the bytes that were previewed (criterion 1)",
     'status, body = conn.create(found["body"])', 'status, body = conn.create(pv.body_bytes(dict(found["payload"], pos="top")))'),
    ("I. The link file is not consulted, so a created draft can be previewed again (criterion 9)",
     '    front, _, _ = read_link(link_path)\n    if front is None:\n        return', '    front, _, _ = read_link(link_path)\n    if True:\n        return'),
    ("J. The link file is not written before the create is sent (criterion 9, the reflection)",
     '    write_link(args.link, front, found["draft"], found["payload"], before)\n', ''),
    ("K. A second create may be sent in one run (criterion 9)",
     '        if self.wrote():\n            raise Refused("a create has already been sent', '        if False:\n            raise Refused("a create has already been sent'),
    ("L. A create with no answer is sent again (criterion 9)",
     '        except (OSError, TimeoutError) as err:\n            raise NeedsLooking("the create was sent and no answer came back',
     '        except (OSError, TimeoutError) as err:\n            status, _, answer = self._post("/cards", None, body)\n            return status, answer\n            raise NeedsLooking("the create was sent and no answer came back'),
    ("M. A preview that is not ready still gets a fingerprint (criteria 4 and 5)",
     '    if not ready:', '    if False:'),
    ("N. A check that fails at confirmation does not stop the write (criterion 5)",
     '    if found["reasons"]:', '    if False:'),
    ("O. A card of the same name already on the board is not noticed (criteria 5 and 9)",
     '    if uncovered:\n        reasons.append("Trello holds', '    if False:\n        reasons.append("Trello holds'),
    ("P. The sandbox allowlist is ignored (criterion 6)",
     '    if draft["board"] not in pv.load_allowlist(args.allowlist):', '    if False:'),
    ("Q. The name is not compared on read-back (criterion 1)",
     'brief(card.get("name")), card.get("name") == payload["name"])', 'brief(card.get("name")), True)'),
    ("R. The due time is not compared on read-back (criterion 1)",
     'instant(card.get("due")) is not None and instant(card.get("due")) == instant(payload["due"]))', 'True)'),
    ("S. The list is not compared on read-back (criterion 1)",
     'str(card.get("idList")), card.get("idList") == payload["idList"])', 'str(card.get("idList")), True)'),
    ("T. The position is not compared on read-back (criterion 1)",
     '    row("pos", json.dumps(wanted), where, same,', '    row("pos", json.dumps(wanted), where, True,'),
    ("U. Labels and members are not compared on read-back (criterion 1)",
     'ids_of(card.get(field)) == ids_of(payload[field]))', 'True)'),
    ("V. The description is not compared on read-back (criterion 1)",
     'brief(card.get("desc")), card.get("desc") == payload["desc"], ", character', 'brief(card.get("desc")), True, ", character'),
    ("W. A card that reads back differently is reported as a success (criterion 1)",
     '    if not good:\n        raise NeedsLooking("the card exists as', '    if False:\n        raise NeedsLooking("the card exists as'),
    ("X. The card id Trello returned is not written to the link file (criterion 2)",
     'front.update(state=CREATED, card_id=body["id"], short_link=', 'front.update(state=CREATED, card_id=None, short_link='),
    ("Y. Reconcile links any new card on the board (the lost answer)",
     '    matching = [card for card in new if holds(card, payload)]', '    matching = new'),
    ("Z. Reconcile takes a card that was on the board before the create was sent (the lost answer)",
     '    new = [card for card in cards if card["id"] not in before]', '    new = cards'),
    ("AA. Reconcile links the first of two matching cards (the lost answer)",
     '    if len(matching) > 1:', '    if False:'),
    ("AB. Any error answer from Trello is taken to mean no card was made (the lost answer)",
     '        if new == []:', '        if True:'),
    ("AC. After Trello refuses a create, the link file is left saying one was sent (criterion 9)",
     '            os.remove(args.link)\n', '            pass\n'),
    ("AD. The result record leaves out who confirmed (criterion 8)",
     '              "Confirmed by: %s, at %s" % (front["confirmed_by"], front["confirmed_at"]),\n', ''),
    ("AE. The output and the files are not searched for the key and the token (credentials)",
     '    if any(secret and secret in piece for secret in found for piece in [text] + list(args.files.values())):', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_create\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken workflow? trello-create-card, attempt trello-attempt-006",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-create-card/create.py, every test was run, and the",
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
    out += ["After the last bug was taken out: create.py is %s it was at the start. %s"
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
