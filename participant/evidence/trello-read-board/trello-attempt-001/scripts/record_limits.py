#!/usr/bin/env python3
"""Records logs/rate-limit-and-paging.txt for the trello-read-board quest.

Runs the skill against fake_trello.py, made to rate-limit and to page, and
saves exactly what the skill prints, with its exit code. No network. The
waits are real: the first case takes about 30 seconds.

Each case writes into a temporary folder that is removed afterwards, so the
made-up board never lands in participant/context/trello/.

Run from anywhere:  python3 scripts/record_limits.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-read-board"))
import fake_trello  # noqa: E402
import sync  # noqa: E402

ACTIONS = "/boards/%s/actions" % fake_trello.BOARD_ID
CARDS = "/boards/%s/cards" % fake_trello.BOARD_ID
lines, problems = [], []


def out(text=""):
    lines.append(text)


def check(label, ok):
    out("  %-4s %s" % ("ok" if ok else "FAIL", label))
    if not ok:
        problems.append(label)


def snapshot(folder):
    found = {}
    for where, _, names in os.walk(folder):
        for name in names:
            with open(os.path.join(where, name), "rb") as f:
                found[os.path.relpath(os.path.join(where, name), folder)] = hashlib.sha256(f.read()).hexdigest()
    return found


def run(fake, folder, get=None, **options):
    """One run of the skill, exactly as it prints, with real waits. Returns (exit code, seconds, text)."""
    printed = io.StringIO()
    started = time.monotonic()
    with contextlib.redirect_stdout(printed):
        try:
            code = sync.run(sync.Client(get or fake.get), fake_trello.BOARD_LINK, folder, "fake", **options)
        except sync.Stop as stop:   # what sync.py's own main() prints for a Stop
            sync.say("STOPPED: %s." % stop)
            sync.say("Nothing was written.")
            code = 1
    seconds = time.monotonic() - started
    text = printed.getvalue().rstrip("\n")
    out("-" * 78)
    out(text)
    out("-" * 78)
    out("exit code: %d      time taken: %.1f seconds" % (code, seconds))
    return code, seconds, text


def main():
    out("Rate limits and paging, against the fake Trello: trello-read-board, attempt trello-attempt-001")
    out("Recorded by scripts/record_limits.py. Each block between the dashed lines is what the skill printed.")
    out("The fake is fake_trello.py. No network is used and no real board is read. The waits are real.")
    out("Real Trello never rate-limited a run and the real board never needed a second page, so this is")
    out("the only record of this behavior. It shows what the skill does with a 429 as the fake sends one.")

    with tempfile.TemporaryDirectory() as folder:
        out("")
        out("=" * 78)
        out("CASE 1. Trello answers 429 to the comments request, every time.")
        out("First an ordinary run, so that there are files from a last successful sync:")
        fake = fake_trello.FakeTrello()
        run(fake, folder, now="2026-11-19T09:00:00Z")
        before = snapshot(folder)
        out("")
        out("Then two changes are made on the fake board (a card renamed, a card deleted), the fake is set to")
        out("answer 429 to every request for comments, and the skill is run again:")
        fake.rename("Add dark mode", "Add dark theme")
        fake.delete("Remove old banner")
        fake.fail(ACTIONS, 429)
        code, seconds, text = run(fake, folder, now="2026-11-20T09:00:00Z")
        out("")
        check("the run ended INCOMPLETE and did not say it had synchronized", "INCOMPLETE" in text and "written:" not in text)
        check("exit code 2", code == 2)
        check("it listed what was retrieved before the limit", "retrieved before that: the signed-in member, the board, lists, cards, checklists" in text)
        check("it listed what was NOT retrieved: comments", "NOT retrieved: comments" in text)
        check("it waited 3 times and no more (three 10 second waits; took %.0f seconds)" % seconds,
              text.count("Wait ") == 3 and 29 <= seconds <= 36)
        check("every file from the last successful sync is unchanged (%d files, same checksums)" % len(before),
              snapshot(folder) == before)
        with open(os.path.join(folder, "board.json"), encoding="utf-8") as f:
            held = f.read()
        check("the time of the last successful sync has not moved", '"last_successful_sync": "2026-11-19T09:00:00Z"' in held)
        check("no card was marked as not returned, and the rename was not half-applied",
              '"not_returned"' not in held and "Add dark theme" not in held)

    with tempfile.TemporaryDirectory() as folder:
        out("")
        out("=" * 78)
        out("CASE 2. Trello answers 429 once, with a header saying its window is 2000 milliseconds, then answers.")
        fake = fake_trello.FakeTrello()
        fake.fail(CARDS, 429, times=1, headers={"x-rate-limit-api-token-interval-ms": "2000"})
        code, seconds, text = run(fake, folder, now="2026-11-19T09:00:00Z")
        out("")
        check("it waited once, for the 2 seconds Trello's answer gave (took %.1f seconds)" % seconds,
              "Wait 1 of 3: 2 seconds" in text and 2 <= seconds < 4)
        check("it then completed: exit code 0, 8 cards held", code == 0 and "cards held: 8" in text)
        check("the report says that it waited", "this run waited 1 time(s)" in text)

    with tempfile.TemporaryDirectory() as folder:
        out("")
        out("=" * 78)
        out("CASE 3. A first run with nothing held, limited on the cards request every time.")
        fake = fake_trello.FakeTrello()
        fake.fail(CARDS, 429, headers={"Retry-After": "1"})
        code, seconds, text = run(fake, folder)
        out("")
        check("exit code 2, and cards, checklists and comments listed as NOT retrieved",
              code == 2 and "NOT retrieved: cards, checklists, comments" in text)
        check("no file at all was written (the folder is empty)", os.listdir(folder) == [])

    with tempfile.TemporaryDirectory() as folder:
        out("")
        out("=" * 78)
        out("CASE 4. Paging. The skill is told a page holds 3, so the 8 cards need three requests,")
        out("and five more comments are added to the fake so the 7 comments need three as well.")
        fake = fake_trello.FakeTrello()
        for n in range(5):
            fake.comment("Search by title", "comment %d" % n, date="2026-11-19T10:0%d:00.000Z" % n)
        code, seconds, text = run(fake, folder, now="2026-11-19T09:00:00Z", page_size=3)
        out("")
        out("The requests the fake received for cards and for comments:")
        for path, params in fake.requests:
            if path in (CARDS, ACTIONS):
                out("  GET %s  limit=%s  before=%s" % (path.split("/")[-1], params.get("limit"), params.get("before", "(none)")))
        cards = [p for p, _ in fake.requests if p == CARDS]
        actions = [p for p, _ in fake.requests if p == ACTIONS]
        check("the 8 cards took %d requests of 3" % len(cards), len(cards) == 3)
        check("the 7 comments took %d requests of 3" % len(actions), len(actions) == 3)
        check("all 8 cards and all 7 comments were read, none twice",
              code == 0 and "read from Trello: 4 lists, 8 cards (1 archived), 1 checklists, 7 comments" in text)

    with tempfile.TemporaryDirectory() as folder:
        out("")
        out("=" * 78)
        out("CASE 5. Paging that does not advance. This fake takes no notice of `before`, so asking for older")
        out("cards returns the same page again.")
        fake = fake_trello.FakeTrello()

        def ignores_before(path, params=None):
            params = dict(params or {})
            params.pop("before", None)
            return fake.get(path, params)

        code, seconds, text = run(fake, folder, get=ignores_before, page_size=3)
        out("")
        check("the run stopped and did not treat the first page as the whole board (exit code 1)",
              code == 1 and "cannot tell whether it has them all" in text)
        check("nothing was written (the folder is empty)", os.listdir(folder) == [])

    out("")
    out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(problems) if problems else "ALL CHECKS PASSED."))
    with open(os.path.join(ATTEMPT, "logs", "rate-limit-and-paging.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[-1])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
