#!/usr/bin/env python3
"""The participant's own run of the preview on the real sandbox board. Read only. Records logs/live-preview-run.txt.

The participant starts this in their own terminal, where TRELLO_API_KEY and
TRELLO_API_TOKEN are set. This script never reads, prints or stores either:
it starts the approved card reader and the preview, which read them from the
environment. Every request either of them sends is a GET.

What it does:

  1  makes a local index of the sandbox board for the duplicate search: takes
     the card ids from the board record the trello-read-board quest saved,
     participant/context/trello/board.json, leaving out any card that record
     marks as no longer returned, has the approved card reader read each one
     into a scratch folder outside the repository, and builds the index there;
  2  previews participant/context/trello/new-card/draft-sandbox.md against
     the real board;
  3  previews the same draft with a list id that no list has, which should be
     refused.

Nothing is created: the preview has no code that writes to Trello.

The real cards' text stays in the scratch folder. The log holds what the
preview printed: the board's and lists' names and ids, card ids, counts,
fingerprints and the made-up draft. The preview prints no card name, no
member id, no key and no token. The scratch folder is shown as SCRATCH.

Run from anywhere:  python3 scripts/live_run.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
READER = "participant/skills/trello-read-card/card.py"
INDEX = "participant/skills/trello-build-index/index.py"
PREVIEW = "participant/skills/trello-create-card-preview/preview.py"
BOARD = "participant/context/trello/board.json"
BASE = "participant/context/trello/new-card"
SCRATCH = "/tmp/gtq-trello-preview"
NO_SUCH_LIST = "6afdf3910000000000000000"


def run(*args):
    done = subprocess.run([sys.executable] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return done.returncode, done.stdout.replace(SCRATCH, "SCRATCH").replace(ROOT + "/", "")


def main():
    os.chdir(ROOT)
    lines, problems = [], []

    def check(label, ok):
        lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            problems.append(label)

    for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN"):
        if not os.environ.get(name):
            print("STOPPED: %s is not set in this terminal. Nothing was contacted." % name)
            return 1
    with open(BOARD, encoding="utf-8") as f:
        board = json.load(f)
    gone = [card_id for card_id, item in board["cards"].items() if item.get("state") == "not_returned"]
    ids = [card_id for card_id in board["cards"] if card_id not in gone]
    records, state = os.path.join(SCRATCH, "boards", "sandbox"), os.path.join(SCRATCH, "state")
    shutil.rmtree(SCRATCH, ignore_errors=True)
    os.makedirs(os.path.join(records, "cards"))
    shutil.copy(BOARD, os.path.join(records, "board.json"))

    lines += ["The preview on the real sandbox board: trello-create-card-preview, attempt trello-attempt-005",
              "Recorded by scripts/live_run.py, started by the participant in their own terminal.",
              "Trello was contacted by the approved card reader and by the preview, with GET requests only. Nothing was written to Trello.",
              "The local index is in a scratch folder outside the repository, shown here as SCRATCH.", "",
              "STEP 1. A local index of the sandbox board, for the duplicate search.",
              "  The approved card reader reads each of the %d cards the board record, %s, holds as on the board%s."
              % (len(ids), BOARD, " (%d left out: marked not_returned)" % len(gone) if gone else "")]
    read_ok = 0
    for card_id in ids:
        code, _ = run(READER, "--source", "live", "--card", card_id, "--out", os.path.join(records, "cards", card_id + ".md"))
        lines.append("  card %s: reader exit code %d" % (card_id, code))
        read_ok += code == 0
    check("the reader wrote a record for all %d cards" % len(ids), read_ok == len(ids))
    if read_ok == 0:
        print("STOPPED: the reader could not read any card. Check that the key and the token are still valid.")
        return 1
    code, _ = run(INDEX, "build", "--records", records, "--out", records)
    check("the index was built beside the records: exit code %d" % code, code == 0)

    common = ["--source", "live", "--allowlist", BASE + "/sandbox-allowlist.json", "--boards", os.path.join(SCRATCH, "boards"), "--state", state]
    lines += ["", "STEP 2. The preview of %s/draft-sandbox.md against the real board." % BASE,
              "$ python3 %s --source live --draft %s/draft-sandbox.md --allowlist %s/sandbox-allowlist.json --boards SCRATCH/boards --state SCRATCH/state"
              % (PREVIEW, BASE, BASE)]
    code, text = run(PREVIEW, "--draft", BASE + "/draft-sandbox.md", *common)
    lines += ["-" * 78, text.rstrip("\n"), "-" * 78, "exit code: %d" % code]
    verdict = re.search(r"^VERDICT: (.+?)\.", text, re.M)
    saved = os.listdir(os.path.join(state, "card-previews")) if os.path.isdir(os.path.join(state, "card-previews")) else []
    check("a preview was made: %s" % (verdict.group(1) if verdict else "NO VERDICT"), code in (0, 3) and bool(verdict))
    check("the list is named by id and Trello says it belongs to the stated board", "Chosen by id. Trello says it belongs to board %s, the stated board: yes" % board["board"]["id"] in text)
    check("the exact payload is shown, with the list and the position", '"idList": "' in text and '"pos": "bottom"' in text)
    check("the permission check is shown, with Trello's own answers", "PERMISSION CHECK, asked of Trello" in text and "the token's own permissions" in text)
    check("the duplicate result is shown", "DUPLICATE SEARCH:" in text and "Result: " in text)
    snaps = re.findall(r"Snapshot of the board in Trello (?:before|after) the preview: +(.+)", text)
    check("the board snapshot is the same before and after: %s" % (snaps[0] if snaps else "?"), len(snaps) == 2 and snaps[0] == snaps[1])
    sent = re.findall(r"^  (\w+) /", text, re.M)
    check("all %d requests the preview sent were GET" % len(sent), bool(sent) and set(sent) == {"GET"})
    check("the request that holds the token is listed without it", "GET /tokens/[the token]" in text)
    check("the output was searched for the key and the token", "searched for the API key and the token: neither found" in text)
    check("a preview was saved for a later write only if the verdict is READY: %d saved" % len(saved), len(saved) == (1 if code == 0 else 0))

    lines += ["", "STEP 3. The same draft with a list id that no list has, %s. It should be refused." % NO_SUCH_LIST]
    with open(BASE + "/draft-sandbox.md", encoding="utf-8") as f:
        draft = f.read()
    wrong = os.path.join(SCRATCH, "draft-no-such-list.md")
    with open(wrong, "w", encoding="utf-8") as f:
        f.write(draft.replace('list: "%s"' % re.search(r'^list: "(\w+)"', draft, re.M).group(1), 'list: "%s"' % NO_SUCH_LIST)
                .replace(": sources/notes.md", ": %s/%s/sources/notes.md" % (ROOT, BASE)))
    code, text = run(PREVIEW, "--draft", wrong, *common)
    lines += ["-" * 78, text.rstrip("\n"), "-" * 78, "exit code: %d" % code]
    check("the preview was refused: exit code 1", code == 1 and text.startswith("REFUSED: "))
    check("the reason is about the list", "the list %s" % NO_SUCH_LIST in text)
    check("no payload was shown", "idList" not in text)

    count = sum(1 for x in lines if re.match(r"  (ok  |FAIL) ", x))
    lines += ["", "RESULT OF THE REAL RUN: %s" % ("ALL CHECKS PASSED. %d checks." % count if not problems else "%d OF %d CHECKS FAILED." % (len(problems), count))]
    text = "\n".join(lines) + "\n"
    if any(os.environ[name] in text for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN")):
        print("STOPPED: the key or the token was found in the log, so the log was not saved.")
        return 1
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "live-preview-run.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(lines[-1])
    for problem in problems:
        print("  FAILED: " + problem)
    print("Log saved: logs/live-preview-run.txt in the attempt folder. The real cards' text stayed in %s." % SCRATCH)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
