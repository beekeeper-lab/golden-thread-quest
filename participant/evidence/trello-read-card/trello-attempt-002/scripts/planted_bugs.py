#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the trello-read-card quest.

Puts one bug at a time into participant/skills/trello-read-card/card.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes card.py while it runs. Do not run the reader at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "trello-read-card")
TARGET = os.path.join(SKILL, "card.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. Every checklist item is drawn with an empty box: the quest's scenario (criterion 2)",
     '            box = "x" if state == "complete" else " " if state == "incomplete" else "?"', '            box = " "'),
    ("B. Every checklist item's state is saved as incomplete (criterion 2)",
     '            state = item.get("state")', '            state = "incomplete"'),
    ("C. The box is taken from the item's name when the name starts with a box (criterion 2 and 7)",
     '            box = "x" if state == "complete" else " " if state == "incomplete" else "?"',
     '            box = "x" if state == "complete" or str(item.get("name")).startswith("[x]") else " " if state == "incomplete" else "?"'),
    ("D. Checklist items are saved in the order Trello sent them, not by position (criterion 2)",
     '        items = ordered([item for item in', '        items = list([item for item in'),
    ("E. An item's other fields, such as its own due date, are dropped (criterion 1)",
     '            if extra:\n                preserved["items"][item["id"]] = extra', '            if False:\n                preserved["items"][item["id"]] = extra'),
    ("F. The due date loses its time zone (criterion 3)",
     '    out += ["%s: %s" % (name, as_json(card[name])) for name in front]',
     '    out += ["%s: %s" % (name, as_json(card[name][:19] if name == "due" and card[name] else card[name])) for name in front]'),
    ("G. The due-complete flag is saved as false whatever Trello sent (criterion 3)",
     '    card = redact(card, counts)\n', '    card = redact(card, counts)\n    card["dueComplete"] = False\n'),
    ("H. Labels lose their colour (criterion 1)",
     '    front = [name for name in CARD_FRONT if name in card]',
     '    card["labels"] = [{"id": label["id"], "name": label["name"]} for label in card.get("labels") or []]\n    front = [name for name in CARD_FRONT if name in card]'),
    ("I. The short link is written where the card's id belongs (criterion 4)",
     '"id: %s" % as_json(card["id"])]', '"id: %s" % as_json(card.get("shortLink"))]'),
    ("J. Fields the format does not know are dropped (criterion 5)",
     '    preserved = {"card": {name: card[name] for name in kept},', '    preserved = {"card": {},'),
    ("K. Unknown fields whose value is empty, false or null are dropped (criterion 5)",
     '    kept = sorted(name for name in card if name not in CARD_FRONT and name not in ("id", "desc"))',
     '    kept = sorted(name for name in card if name not in CARD_FRONT and name not in ("id", "desc") and card[name] not in (None, False, [], ""))'),
    ("L. The file records when it was made (criterion 6)",
     '    out = ["---", "format: %s" % as_json(FORMAT), "id: %s" % as_json(card["id"])]',
     '    out = ["---", "format: %s" % as_json(FORMAT), "id: %s" % as_json(card["id"]), "retrieved: %s" % as_json(__import__("time").time())]'),
    ("M. An unchanged file is rewritten on every run (criterion 6)",
     '    if existing == data_bytes:', '    if False:'),
    ("N. Comments are saved in the order Trello sent them, newest first (criteria 1 and 6)",
     '    comments = sorted(redact(data["comments"], counts), key=lambda row: (str(row.get("date")), row["id"]))', '    comments = redact(data["comments"], counts)'),
    ("O. Only the first page of comments is read (criterion 1)",
     '        if len(page) < PAGE:\n            break', '        if True:\n            break'),
    ("P. The description is written into the file without a fence (criterion 7)",
     '    out += (fenced(card["desc"]) if isinstance(card.get("desc"), str) and card["desc"] else ["(empty)"]) + [""]', '    out += [card.get("desc") or "(empty)", ""]'),
    ("Q. A fence is always three backticks, whatever the text holds (criterion 7)",
     '    fence = "`" * (longest + 1)', '    fence = "```"'),
    ("R. A comment's text is written into the file without a fence (criterion 7)",
     '        body += fenced(str(payload.get("text", ""))) + [""]', '        body += [str(payload.get("text", "")), ""]'),
    ("S. A card name with a line break is written as several lines (criterion 7)",
     '    text = " ".join(str(text).split())\n    for ch in', '    text = str(text)\n    for ch in'),
    ("T. A person is saved whole, with name and picture (criterion 7)",
     '            return {"id": value["id"]} if isinstance(value.get("id"), str) else {}', '            return value'),
    ("U. Email addresses typed into text are left in (criterion 7)",
     '        if found:\n            counts["email addresses removed from text"]', '        if False:\n            counts["email addresses removed from text"]'),
    ("V. The card's private email address is stored (criterion 7)",
     '        del card["email"]', '        pass'),
    ("W. Trello is asked to send people's details with each comment (criterion 7)",
     '"memberCreator": "false", "member": "false"}', '"memberCreator": "true", "member": "true"}'),
    ("X. The key and the token are put in the address of each request (safety rule: credentials)",
     '            url += "?" + urllib.parse.urlencode(params)', '            url += "?" + urllib.parse.urlencode(dict(params, key=key, token=token))'),
    ("Y. A file that would hold the key or the token is written anyway (criterion 7)",
     '    if any(secret and secret in text for secret in secrets):\n        raise Stop("the key or the token was found in what would have been written',
     '    if False:\n        raise Stop("the key or the token was found in what would have been written'),
    ("Z. The reader is given a way to send a write (safety rule: read only)",
     '        request = urllib.request.Request(url, method="GET")', '        request = urllib.request.Request(url, method="GET" if "_w" not in (params or {}) else "POST")'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_card\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken reader? trello-read-card, attempt trello-attempt-002",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/trello-read-card/card.py, every test was run, and the",
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
    out += ["After the last bug was taken out: card.py is %s it was at the start. %s"
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
