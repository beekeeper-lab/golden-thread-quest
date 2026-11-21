#!/usr/bin/env python3
"""Records the logs for the base-camp-write-preview quest.

    logs/preview.txt     a preview that stops, and the board unchanged after it
    logs/confirmed.txt   the same preview confirmed, and the board after it
    logs/refused.txt     confirmations that are refused, and the board unchanged
    logs/within-limit.txt  one preview refused at 16 minutes and confirmed at 14

The four logs are one sequence against one board, work/board.json. The work
folder is emptied first, so everything in it comes from this recording.

Each command is shown on a line starting with "$", followed by exactly what
it printed. Lines starting with "#" are notes written by this script.

Run from the attempt folder:  python3 scripts/record_evidence.py
"""
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
BOARD = "work/board.json"
NAME = "Beau Brown"


class Log:
    def __init__(self, name, title):
        self.file = open(os.path.join("logs", name), "w", encoding="utf-8")
        self.note(title)
        self.note("base-camp-write-preview, attempt base-attempt-006. Recorded by scripts/record_evidence.py.")
        self.note("The board is a simulated one: the local file %s. No real system is contacted." % BOARD)

    def write(self, text=""):
        self.file.write(text + "\n")

    def note(self, text):
        self.write("# " + text)

    def run(self, *command):
        """Run one command, write it and what it printed, and return what it printed."""
        shown = " ".join('"%s"' % part if " " in part else part for part in command)
        self.write("")
        self.write("$ " + shown)
        done = subprocess.run([sys.executable if command[0].endswith(".py") else command[0]] + list(command[
            0 if command[0].endswith(".py") else 1:]), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.write(done.stdout.rstrip("\n"))
        self.write("(exit code %d)" % done.returncode)
        return done.stdout

    def board_fingerprint(self):
        out = self.run("scripts/board.py", "show", BOARD)
        return re.search(r"board fingerprint: (\w+)", out).group(1)

    def compare(self, before, after, expect_same):
        same = before == after
        self.write("")
        self.note("Board fingerprint before: %s   after: %s" % (before, after))
        self.note("The board is %s." % ("UNCHANGED" if same else "CHANGED"))
        if same != expect_same:
            self.note("THIS IS NOT WHAT WAS EXPECTED.")
            print("unexpected result in %s" % self.file.name)

    def section(self, text):
        self.write("")
        self.write("=" * 78)
        self.note(text)


def preview(log, change):
    out = log.run("scripts/writer.py", "preview", "--board", BOARD, "--change", change)
    return re.search(r"Fingerprint of this preview: (\w+)", out).group(1)


def confirm(log, change, fingerprint, *extra):
    return log.run("scripts/writer.py", "confirm", "--board", BOARD, "--change", change,
                   "--fingerprint", fingerprint, "--confirmed-by", NAME, *extra)


def main():
    os.chdir(ATTEMPT)
    shutil.rmtree("work", ignore_errors=True)
    os.makedirs("work")
    os.makedirs("logs", exist_ok=True)

    # ------------------------------------------------------------ preview.txt
    log = Log("preview.txt", "A preview that stops, then a check that the board is unchanged.")
    log.section("1. Make a starting board and look at it.")
    log.run("scripts/board.py", "init", BOARD)
    log.run("cp", "scripts/sample/follow-ups.json", "work/change-a.json")
    start = log.board_fingerprint()
    log.section("2. Preview the change. This is the whole run: it shows the preview and stops.")
    code_a = preview(log, "work/change-a.json")
    log.section("3. Look at the board again.")
    log.compare(start, log.board_fingerprint(), expect_same=True)
    log.section("4. Try to write without confirming a preview. Each attempt is refused.")
    log.note("With no fingerprint:")
    log.run("scripts/writer.py", "confirm", "--board", BOARD, "--change", "work/change-a.json",
            "--confirmed-by", NAME)
    log.note("With --yes, on each command:")
    log.run("scripts/writer.py", "preview", "--board", BOARD, "--change", "work/change-a.json", "--yes")
    log.run("scripts/writer.py", "confirm", "--board", BOARD, "--change", "work/change-a.json",
            "--confirmed-by", NAME, "--yes")
    log.note("With a fingerprint that no preview has:")
    confirm(log, "work/change-a.json", "0123456789ab")
    log.compare(start, log.board_fingerprint(), expect_same=True)
    log.section("5. A change with a field named like a credential. No preview is made or saved.")
    log.run("ls", BOARD + ".previews")
    log.run("scripts/writer.py", "preview", "--board", BOARD, "--change", "scripts/sample/with-auth-field.json")
    log.run("ls", BOARD + ".previews")
    log.note("The folder of saved previews holds the same one file before and after.")
    log.file.close()

    # ---------------------------------------------------------- confirmed.txt
    log = Log("confirmed.txt", "The preview from logs/preview.txt confirmed, and the board after it.")
    log.section("1. The board before. It is as logs/preview.txt left it.")
    before = log.board_fingerprint()
    log.section("2. Confirm preview %s, the one shown in logs/preview.txt." % code_a)
    confirm(log, "work/change-a.json", code_a)
    log.section("3. The board after. Compare with the preview: DEMO-6 and DEMO-7 are new, DEMO-3 is now doing.")
    after = log.board_fingerprint()
    log.compare(before, after, expect_same=False)
    log.section("4. The record the write left behind.")
    log.run("cat", "%s.written/%s.json" % (BOARD, code_a))
    log.section("5. Confirm the same preview a second time. It is refused, and the board does not change again.")
    confirm(log, "work/change-a.json", code_a)
    log.compare(after, log.board_fingerprint(), expect_same=True)
    log.file.close()

    # ------------------------------------------------------------ refused.txt
    log = Log("refused.txt", "Confirmations that are refused, with no change made by any of them.")
    log.note("The board starts as logs/confirmed.txt left it. A second change file is used:")
    log.note("two updates, to DEMO-4 and DEMO-5.")

    log.section("REFUSAL 1. The change differs from the one previewed.")
    log.run("cp", "scripts/sample/tidy-up.json", "work/change-b.json")
    before = log.board_fingerprint()
    code = preview(log, "work/change-b.json")
    log.note("After the preview, the change file is replaced by one that differs in a single word:")
    log.note("DEMO-5's new status is done where the preview said doing.")
    log.run("cp", "scripts/sample/tidy-up-edited.json", "work/change-b.json")
    log.run("diff", "scripts/sample/tidy-up.json", "work/change-b.json")
    log.note("Confirm the fingerprint of the preview that was read:")
    confirm(log, "work/change-b.json", code)
    log.compare(before, log.board_fingerprint(), expect_same=True)

    log.section("REFUSAL 2. The preview is older than the time limit of 15 minutes.")
    log.run("cp", "scripts/sample/tidy-up.json", "work/change-b.json")
    log.note("(The script waits a second here. This is the same change against the same board as the")
    log.note("preview in refusal 1. Made in the same second it would get the same fingerprint, and the")
    log.note("workflow refuses to make a second preview with a fingerprint that is already in use.)")
    time.sleep(1.1)
    code = preview(log, "work/change-b.json")
    log.note("The change file and the board are exactly as previewed. Only the time differs.")
    log.note("--pretend-minutes-later moves the workflow's clock forward. It cannot move it back.")
    confirm(log, "work/change-b.json", code, "--pretend-minutes-later", "16")
    log.compare(before, log.board_fingerprint(), expect_same=True)

    log.section("REFUSAL 3 (not asked for by the quest). The board was changed by someone else after the preview.")
    log.run("cp", "scripts/sample/one-more.json", "work/change-c.json")
    code = preview(log, "work/change-c.json")
    log.note("Stand-in for another person editing the board: one story's title is changed by hand.")
    with open(BOARD, encoding="utf-8") as f:
        text = f.read()
    assert text.count("Export the weekly report as a file") == 1
    with open(BOARD, "w", encoding="utf-8") as f:
        f.write(text.replace("Export the weekly report as a file", "Export the weekly report as a PDF file"))
    moved = log.board_fingerprint()
    confirm(log, "work/change-c.json", code)
    log.compare(moved, log.board_fingerprint(), expect_same=True)

    log.section("REFUSAL 4 (not asked for by the quest). The saved preview was edited to look newer.")
    log.note("The board is put back as it was when the preview in refusal 3 was made, so that preview")
    log.note("would otherwise be good. Then the time in its saved file is moved a year ahead by hand.")
    with open(BOARD, "w", encoding="utf-8") as f:
        f.write(text)
    before = log.board_fingerprint()
    saved = "%s.previews/%s.json" % (BOARD, code)
    with open(saved, encoding="utf-8") as f:
        record = f.read()
    assert record.count('"made_at": "2026-') == 1
    with open(saved, "w", encoding="utf-8") as f:
        f.write(record.replace('"made_at": "2026-', '"made_at": "2027-'))
    log.run("grep", "made_at", saved)
    confirm(log, "work/change-c.json", code)
    log.compare(before, log.board_fingerprint(), expect_same=True)
    log.file.close()

    # ------------------------------------------------------- within-limit.txt
    log = Log("within-limit.txt", "One preview refused at 16 minutes and confirmed at 14.")
    log.note("This shows that the expiry refusal in logs/refused.txt was for age and nothing else.")
    log.note("The board starts as logs/refused.txt left it. This log does end with a write.")
    log.section("1. Preview the two updates to DEMO-4 and DEMO-5.")
    time.sleep(1.1)
    before = log.board_fingerprint()
    code = preview(log, "work/change-b.json")
    log.section("2. Confirm it 16 minutes on: refused, and the board is unchanged.")
    confirm(log, "work/change-b.json", code, "--pretend-minutes-later", "16")
    log.compare(before, log.board_fingerprint(), expect_same=True)
    log.section("3. Confirm the same preview 14 minutes on: inside the limit, so it is written.")
    confirm(log, "work/change-b.json", code, "--pretend-minutes-later", "14")
    log.compare(before, log.board_fingerprint(), expect_same=False)
    log.file.close()
    print("wrote logs/preview.txt, logs/confirmed.txt, logs/refused.txt, logs/within-limit.txt")


if __name__ == "__main__":
    main()
