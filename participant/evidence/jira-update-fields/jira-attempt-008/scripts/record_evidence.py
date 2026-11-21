#!/usr/bin/env python3
"""Records logs/preview.txt, confirmation.txt, stale-run.txt, rerun.txt and unsupported-field.txt.

Everything here runs against scripts/fake_jira.py, a made-up Jira. No network
is used and no real Jira is read or written. Each run is the real command,
started as a person would start it, and what it printed is written down.

The fake Jira keeps its state in a temporary folder, shown in the logs as
STATE. A new folder is used for each log except rerun.txt, which carries on
from the approved write in confirmation.txt.

Where a person has also made the same kind of run against a real Jira
sandbox, and its saved log is in logs/ under a name starting live-, that log
is copied unchanged onto the end of the matching record.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
S = REL + "/scripts"
ALLOW = S + "/fake-allowlist.json"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "The Jira here is scripts/fake_jira.py, a made-up one. No real Jira was read or written, so nothing is\n"
        "redacted: the site, the projects and the stories are invented. STATE stands for a temporary folder.")


class Log:
    def __init__(self, title, state):
        self.lines, self.problems, self.state = [title, HEAD, ""], [], state

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def command(self, script, *args):
        args = [self.state if arg == "STATE" else arg for arg in args]
        shown = " ".join('"%s"' % a if " " in a else a for a in args).replace(self.state, "STATE")
        self.out("$ python3 %s/%s %s" % (S, script, shown))
        done = subprocess.run([sys.executable, os.path.join(S, script)] + args, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True)
        text = done.stdout.rstrip("\n").replace(self.state, "STATE")
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text

    def preview(self, change, allow=ALLOW):
        code, text = self.command("update.py", "preview", "--source", "fake", "--change", "%s/changes/%s" % (S, change),
                                  "--allowlist", allow, "--state", "STATE")
        found = re.findall(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text, re.M)
        return code, text, (found[0] if found else None)

    def confirm(self, change, *more, allow=ALLOW):
        return self.command("update.py", "confirm", "--source", "fake", "--change", "%s/changes/%s" % (S, change),
                            "--allowlist", allow, "--state", "STATE", *more)

    def show(self, story="SAND-1"):
        return self.command("fake_jira.py", "show", "--state", "STATE", "--story", story)[1]

    def save(self, name, live=()):
        """`live` is a list of (what it is, log file) for runs a person made against the real sandbox."""
        self.out("")
        result = "RESULT: %s" % ("%d CHECK(S) FAILED" % len(self.problems) if self.problems else "ALL CHECKS PASSED.")
        self.out(result + (" (The checks are on the fake-Jira runs above.)" if live else ""))
        found = [(what, log) for what, log in live if os.path.exists(os.path.join(REL, "logs", log))]
        if found:
            self.lines += ["", "#" * 78, "THE SAME ON THE REAL JIRA SANDBOX",
                           "The blocks below were not made by this script. The participant ran each command in their own",
                           "terminal against their real Jira sandbox, and the updater saved its output with the site's",
                           "address replaced by a marker. They are copied here unchanged from the log files named."]
            for what, log in found:
                with open(os.path.join(REL, "logs", log), encoding="utf-8") as f:
                    self.lines += ["", what, "(copied from logs/%s)" % log, "-" * 78, f.read().strip("\n"), "-" * 78]
        with open(os.path.join(REL, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, result))
        return self.problems


START = 'labels ["onboarding"], duedate "2026-12-01", priority "Medium". Changelog entries: 0.'
DONE = 'labels ["onboarding", "q4"], duedate "2026-12-15", priority "High". Changelog entries: 1.'


def main():
    os.chdir(ROOT)
    problems = []

    # ------------------------------------------------------------ preview.txt
    with tempfile.TemporaryDirectory() as state:
        log = Log("The workflow stopping at a preview: jira-update-fields, attempt jira-attempt-008", state)
        log.part("1. What the fake Jira holds before the preview.")
        first = log.show()
        log.part("2. The preview. The change file asks for two labels, a due date and a priority.")
        code, text, fingerprint = log.preview("wanted.json")
        log.part("3. What the fake Jira holds after the preview.")
        second = log.show()
        log.out("")
        log.check("the preview shows the Jira site, the project and the story", "Jira site:  https://fixture-site.example.invalid" in text
                  and "Project:    SAND (project id 20001). On the sandbox allowlist: yes." in text and "Story:      SAND-1 (issue id 30001)" in text)
        log.check("it shows the value now and the value after for each of the three fields (criterion 1)",
                  all(part in text for part in ('labels    now:    ["onboarding"]', 'after:  ["onboarding", "q4"]', "duedate   now:    2026-12-01",
                                                "after:  2026-12-15", 'priority  now:    "Medium" (id 3)', 'after:  "High" (id 2)')))
        log.check("it records the permission check and the duplicate check, and says where Jira cannot check (criterion 5)",
                  "may edit the story (EDIT_ISSUES):     yes" in text and "Duplicate check:" in text and "Where Jira cannot check:" in text)
        log.check("it gives a fingerprint and an expiry time (criterion 7)", bool(fingerprint) and "(15 minutes after it was made)" in text)
        log.check("every request was a GET, and the preview says nothing was written (criterion 4)",
                  "Every one was a GET" in text and "PUT" not in text and text.startswith("PREVIEW. Nothing has been written."))
        snaps = re.findall(r"(?:before|after) the preview:\s+([0-9a-f]{16})", text)
        log.check("the snapshot of the story before and after the preview is the same", len(snaps) == 2 and snaps[0] == snaps[1])
        log.check("the fake Jira holds the same values, and the same number of history entries, before and after",
                  first == second and START in first)
        problems += log.save("preview.txt", [("The real preview: one label and a due date on the sandbox story.", "live-preview.txt")])

    # ------------------------------------------------------------ unsupported-field.txt
    with tempfile.TemporaryDirectory() as state:
        log = Log("Fields outside the supported list being refused: jira-update-fields, attempt jira-attempt-008", state)
        log.part("1. A change file that asks for a supported field, priority, and also for the assignee.")
        code1, text1, f1 = log.preview("unsupported-assignee.json")
        log.part("2. A change file that asks for the summary.")
        code2, text2, f2 = log.preview("unsupported-summary.json")
        log.part("3. What the fake Jira holds afterwards.")
        held = log.show()
        log.out("")
        log.check("both were refused with exit code 1, and no fingerprint was issued (criterion 2)",
                  code1 == 1 and code2 == 1 and f1 is None and f2 is None)
        log.check("each refusal names the field and the three that are supported",
                  'the field "assignee" is not supported' in text1 and 'the field "summary" is not supported' in text2
                  and "changes only labels, duedate, priority" in text1)
        log.check("a supported field in the same file was not changed either: the whole change is refused", START in held)
        problems += log.save("unsupported-field.txt")

    # ------------------------------------------------------------ confirmation.txt and rerun.txt
    with tempfile.TemporaryDirectory() as state:
        log = Log("Four refusals and the approved run: jira-update-fields, attempt jira-attempt-008", state)
        log.part("0. The preview that the rest of this record is about.")
        code, text, fingerprint = log.preview("wanted.json")
        log.check("a fingerprint was issued", code == 0 and bool(fingerprint))

        log.part("REFUSAL 1. A missing confirmation: the confirm command with no fingerprint and no name.")
        code, text = log.confirm("wanted.json")
        log.check("refused, exit code 1, nothing written", code == 1 and "no confirmation was given" in text and "Nothing has been written." in text)
        log.out("And with a fingerprint but no name of a person confirming:")
        code, text = log.confirm("wanted.json", "--fingerprint", fingerprint)
        log.check("refused, exit code 1, nothing written", code == 1 and "no confirmation was given" in text and "Nothing has been written." in text)

        log.part("REFUSAL 2. A change that differs from the preview. The fingerprint is the right one, and the\n"
                 "change file now asks for priority Highest where the preview showed High.")
        code, text = log.confirm("wanted-then-edited.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        log.check("refused, exit code 1, nothing written", code == 1 and "the change is not the one that was previewed" in text
                  and 'the preview showed "High" (id 2) and the change file now asks for "Highest" (id 1)' in text)

        log.part("REFUSAL 3. A preview older than the limit of 15 minutes. The test clock is moved 16 minutes on.")
        code, text = log.confirm("wanted.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--pretend-minutes-later", "16")
        log.check("refused, exit code 1, nothing written", code == 1 and "this preview is too old" in text and "the limit is 15" in text)

        log.part("REFUSAL 4. A project that is not on the sandbox allowlist. PROD-9 is a story this identity is\n"
                 "permitted to edit, so the allowlist is the only thing that stops it.")
        code, text, none = log.preview("not-on-allowlist.json")
        log.check("refused at the preview, exit code 1, and no fingerprint was issued, so there is nothing to confirm",
                  code == 1 and none is None and "project PROD (project id 20002)" in text and "is not on the sandbox allowlist" in text)
        log.out("The allowlist is checked again at confirmation. Here the good preview is confirmed against an allowlist")
        log.out("that no longer lists SAND:")
        code, text = log.confirm("wanted.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant",
                                 allow=S + "/fake-allowlist-without-sand.json")
        log.check("refused, exit code 1, nothing written", code == 1 and "project SAND (project id 20001)" in text and "is not on the sandbox allowlist" in text)

        log.part("After the four refusals, what the fake Jira holds.")
        held = log.show()
        prod = log.show("PROD-9")
        log.check("SAND-1 is as it was before the preview, with no history entries", START in held)
        log.check("PROD-9 is as it was, with no history entries", 'priority "Medium". Changelog entries: 0.' in prod)

        log.part("THE APPROVED RUN. The same preview, confirmed by its fingerprint, with the confirming person's\n"
                 "name, the unchanged change file, and inside the time limit. In this recording the command is\n"
                 "started by the recording script, which stands in for the person. In a real run a person types it.")
        code, text = log.confirm("wanted.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        log.check("written, exit code 0", code == 0 and "WRITTEN to Jira: one edit of story SAND-1, fields labels, duedate, priority. Jira answered 204." in text)
        log.check("the confirmation names the preview's fingerprint and who confirmed (criterion 7)",
                  ("CONFIRMATION for preview %s, given by: the participant" % fingerprint) in text)
        log.check("the confirmation and the write were in the same run", "The confirmation and the write happened in this one run of the command." in text)
        log.check("each field was read back as proposed", text.count(": as proposed") == 3)
        log.check("the result record has the issue key, the changelog entry, the project, the time and the confirmer (criterion 8)",
                  all(part in text for part in ("Issue key: SAND-1", "Identifier of what was changed: Jira changelog entry 40001",
                                                "Target project: SAND (project id 20001)", "Written at: ", "Confirmed by: the participant")))
        held = log.show()
        log.check("the fake Jira now holds the three new values, with one history entry", DONE in held)
        problems += log.save("confirmation.txt", [
            ("A real refusal: the first real preview, made before the sandbox project had been put on the allowlist.", "live-not-on-allowlist.txt"),
            ("The real approved run: the participant confirming the real preview by its fingerprint.", "live-confirmation.txt")])

        log = Log("Running the approved workflow a second time: jira-update-fields, attempt jira-attempt-008", state)
        log.out("This carries on from the approved run recorded in logs/confirmation.txt, in the same STATE folder.")
        log.out("The fingerprint of that run's preview was %s." % fingerprint)
        log.part("1. What the fake Jira holds after the approved run.")
        first = log.show()
        log.part("2. The same preview command again, with the same change file.")
        code, text, again = log.preview("wanted.json")
        log.check("it reports nothing to change, issues no fingerprint, and sent only GETs (criterion 9)",
                  code == 0 and text.startswith("NOTHING TO CHANGE.") and again is None and "Every one was a GET" in text)
        log.part("3. The same confirm command again, with the fingerprint that was already used.")
        code, text = log.confirm("wanted.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        log.check("refused, exit code 1: a fingerprint is used once", code == 1 and "A fingerprint is used once" in text)
        log.part("4. What the fake Jira holds after both.")
        second = log.show()
        log.check("the values are the same, and there is still exactly one history entry: no repeated change", first == second and DONE in second)
        problems += log.save("rerun.txt", [
            ("The real preview command run again after the real write.", "live-rerun-preview.txt"),
            ("The real confirm command run again with the fingerprint already used.", "live-rerun-confirm.txt")])

    # ------------------------------------------------------------ stale-run.txt
    with tempfile.TemporaryDirectory() as state:
        log = Log("An update refused because the field changed in Jira after the preview: jira-update-fields, attempt jira-attempt-008", state)
        log.out("This is the quest's scenario. A preview is made. Then someone else, here the product owner, raises")
        log.out("the story's priority. Then the preview is confirmed.")
        log.part("1. The preview: priority from Medium to High.")
        code, text, fingerprint = log.preview("priority-only.json")
        log.check("the preview saw priority Medium", 'priority  now:    "Medium" (id 3)' in text and bool(fingerprint))
        log.part("2. Someone else changes the priority in Jira to Highest.")
        log.command("fake_jira.py", "other-edit", "--state", "STATE", "--story", "SAND-1", "--field", "priority", "--value", '"Highest"')
        log.part("3. The confirmation of the preview, complete and in time.")
        code, text = log.confirm("priority-only.json", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        log.check("refused, exit code 1, nothing written (criterion 3)", code == 1 and "Nothing has been written." in text)
        log.check("the refusal names the field, the value the preview saw and the value Jira holds now",
                  'a field changed in Jira after the preview was made: priority: the preview saw "Medium" (id 3) and Jira now holds "Highest" (id 1)' in text)
        log.part("4. What the fake Jira holds afterwards.")
        held = log.show()
        log.check("the priority is still Highest, the other person's value, and the one history entry is theirs",
                  'priority "Highest". Changelog entries: 1.' in held)
        problems += log.save("stale-run.txt", [
            ("1. A real preview of a priority change. It saw the priority as not set.", "live-stale-preview.txt"),
            ("2. The participant then set the priority to Low by hand, in Jira's own page in a browser, playing the\n"
             "other person. 3. The real confirmation of the preview from step 1:", "live-stale-run.txt")])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
