#!/usr/bin/env python3
"""Records logs/preview.txt, confirmation.txt, rerun.txt and recovery.txt against the fake Jira.

Everything here runs against the fake Jira in the skill folder. No network is
used and no real Jira is read or written. In preview.txt, confirmation.txt
and rerun.txt each block between dashed lines is what the real command
printed, started as a person would start it. The fake Jira keeps its stories
in a temporary folder, shown as STATE, so that a preview and a later
confirmation see the same Jira.

The draft used is a copy of participant/context/jira/new-story/draft.md, made
here in participant/context/jira/new-story/fixture-run/, with its link file
and result record beside it. That folder is rebuilt on each run.

recovery.txt is different. A lost answer cannot be staged from the command
line, so that log is recorded inside this script: it gives the workflow a
fake Jira that creates the story and then does not answer, and writes down
what the workflow says.

Where a person has made the same kind of run against a real Jira sandbox and
its saved log is in logs/ under a name starting live-, that log is copied
unchanged onto the end of the matching record.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
SKILL = "participant/skills/jira-create-story"
NEW = "participant/context/jira/new-story"
RUN = NEW + "/fixture-run"
CATALOG = "participant/context/jira/duplicates/fixture"
HEAD = ("Recorded by scripts/record_evidence.py.\n"
        "The Jira here is %s/fake_jira.py, a made-up one. No real Jira was read or written, so nothing is\n"
        "redacted: the site, the projects and the stories are invented. STATE stands for a temporary folder." % SKILL)


class Log:
    def __init__(self, title, state):
        self.lines, self.problems, self.state = [title, HEAD], [], state

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def run(self, script, *args):
        args = [self.state if a == "STATE" else a for a in args]
        shown = " ".join('"%s"' % a if " " in a else a for a in args).replace(self.state, "STATE")
        self.out("$ python3 %s/%s %s" % (SKILL, script, shown))
        done = subprocess.run([sys.executable, SKILL + "/" + script] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text = done.stdout.rstrip("\n").replace(self.state, "STATE")
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text

    def create(self, command, *more, draft="draft.md", link="linked.md", allow=SKILL + "/fake-allowlist.json"):
        base = [command, "--source", "fake", "--link", "%s/%s" % (RUN, link), "--state", "STATE"]
        if command in ("preview", "confirm"):
            base += ["--draft", "%s/%s" % (RUN, draft), "--allowlist", allow, "--catalog", CATALOG, "--today", "2026-11-19"]
        return self.run("create.py", *(base + list(more)))

    def show(self):
        return self.run("fake_jira.py", "show", "--state", "STATE")[1]

    def save(self, name, live=()):
        self.out("")
        result = "RESULT: %s" % ("%d CHECK(S) FAILED" % len(self.problems) if self.problems else "ALL CHECKS PASSED.")
        found = [(what, log) for what, log in live if os.path.exists(os.path.join(REL, "logs", log))]
        self.out(result + (" (The checks are on the fake-Jira runs above.)" if found else ""))
        if found:
            self.lines += ["", "#" * 78, "THE SAME ON THE REAL JIRA SANDBOX",
                           "The blocks below were not made by this script. The participant ran each command in their own",
                           "terminal against their real Jira sandbox, and the workflow saved its output with the site's",
                           "address replaced by a marker. They are copied here unchanged from the log files named."]
            for what, log in found:
                with open(os.path.join(REL, "logs", log), encoding="utf-8") as f:
                    self.lines += ["", what, "(copied from logs/%s)" % log, "-" * 78, f.read().strip("\n"), "-" * 78]
        with open(os.path.join(REL, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, result))
        return self.problems


def fingerprint_in(text):
    found = re.findall(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text, re.M)
    return found[0] if found else None


def main():
    os.chdir(ROOT)
    os.makedirs(REL + "/logs", exist_ok=True)
    problems = []
    if os.path.isdir(RUN):
        shutil.rmtree(RUN)
    os.makedirs(RUN)
    with open(NEW + "/draft.md", encoding="utf-8") as f:
        good = f.read().replace("sources/intake-notes.md", "../sources/intake-notes.md")
    with open(RUN + "/draft.md", "w", encoding="utf-8") as f:
        f.write(good)
    with open(RUN + "/draft-ops.md", "w", encoding="utf-8") as f:
        f.write(good.replace('project: "RPT"', 'project: "OPS"'))
    with open(SKILL + "/fake-allowlist.json", encoding="utf-8") as f:
        allow = json.load(f)
    allow["about"] = "The fake allowlist with RPT taken off, to show the allowlist being checked again at confirmation."
    allow["sandbox_projects"] = [entry for entry in allow["sandbox_projects"] if entry["project_id"] != "30000"]
    with open(RUN + "/allowlist-without-rpt.json", "w", encoding="utf-8") as f:
        json.dump(allow, f, indent=2)
        f.write("\n")

    with tempfile.TemporaryDirectory() as state:
        # ------------------------------------------------------------ preview.txt
        log = Log("The workflow stopping at a preview: jira-create-story, attempt jira-attempt-012", state)
        log.out("The draft is %s/draft.md, a copy of %s/draft.md." % (RUN, NEW))
        log.part("1. What the fake Jira holds before the preview.")
        first = log.show()
        log.part("2. The preview.")
        code, text = log.create("preview")
        fingerprint = fingerprint_in(text)
        log.part("3. What the fake Jira holds after the preview.")
        second = log.show()
        log.out("")
        log.check("the preview shows the Jira site, the project and the one change: a new story (criterion 4)",
                  code == 0 and "Jira site:   https://fixture-site.example.invalid" in text and "Project:     RPT (project id 30000)" in text
                  and "one new story would be created, with one request: POST /rest/api/3/issue" in text)
        log.check("it shows the exact payload, with its SHA-256, and the marker label in it",
                  "THE EXACT PAYLOAD." in text and bool(re.search(r"\d+ bytes, SHA-256 [0-9a-f]{64}", text)) and bool(re.search(r'"gtq-[0-9a-f]{8}"', text)))
        log.check("it records the permission check: may create stories, yes (criterion 5)", "(CREATE_ISSUES):   yes" in text)
        log.check("it records three duplicate checks: the link file, the title asked of Jira, and the local catalog (criterion 5)",
                  "1. This draft's own link file: there is none" in text and "2. Asked of Jira, stories in RPT with this title: 0 with exactly this title" in text
                  and "3. Duplicate search:" in text and "Result: 1 candidate." in text)
        log.check("it says where Jira cannot check", "Where Jira cannot check: it has no way to refuse a second create" in text)
        log.check("it gives a fingerprint and an expiry time (criterion 7)", bool(fingerprint) and "(15 minutes after it was made)" in text)
        snaps = re.findall(r"(?:before|after) the preview:\s+(\d+ stories, [0-9a-f]{16})", text)
        log.check("the snapshot of the project before and after the preview is the same, and every request was a GET",
                  len(snaps) == 2 and snaps[0] == snaps[1] and "Every one was a GET" in text and "POST /rest/api/3/issue\n" not in text.split("Requests sent")[1])
        log.check("the fake Jira holds the same 7 stories in RPT before and after, and no link file was made",
                  first == second and "holds 7 stories in project RPT" in first and not os.path.exists(RUN + "/linked.md"))
        problems += log.save("preview.txt", [("The real preview of the story for the sandbox.", "live-preview.txt")])

        # ------------------------------------------------------------ confirmation.txt
        log = Log("Four refusals and the approved run: jira-create-story, attempt jira-attempt-012", state)
        log.out("This carries on from the preview recorded in logs/preview.txt, in the same STATE folder.")
        log.out("The fingerprint of that preview is %s." % fingerprint)

        log.part("REFUSAL 1. A missing confirmation: the confirm command with no fingerprint and no name.")
        code, text = log.create("confirm")
        log.check("refused, exit code 1, nothing written", code == 1 and "no confirmation was given" in text and "Nothing has been written to Jira." in text)
        log.out("And with the fingerprint but no name of a person confirming:")
        code, text = log.create("confirm", "--fingerprint", fingerprint)
        log.check("refused, exit code 1, nothing written", code == 1 and "no confirmation was given" in text)

        log.part("REFUSAL 2. A change that differs from the preview. The fingerprint is the right one, and the draft\n"
                 "has been edited since: the due date is now 2027-01-14 where the preview showed 2027-01-15.")
        with open(RUN + "/draft.md", "w", encoding="utf-8") as f:
            f.write(good.replace('duedate: "2027-01-15"', 'duedate: "2027-01-14"'))
        code, text = log.create("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        with open(RUN + "/draft.md", "w", encoding="utf-8") as f:
            f.write(good)
        log.check("refused, exit code 1, nothing written, and the field that differs is named",
                  code == 1 and "the change is not the one that was previewed: the payload now differs in duedate" in text)
        log.out("The draft was then put back as it was.")

        log.part("REFUSAL 3. A preview older than the limit of 15 minutes. The test clock is moved 16 minutes on.")
        code, text = log.create("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--pretend-minutes-later", "16")
        log.check("refused, exit code 1, nothing written", code == 1 and "this preview is too old" in text and "the limit is 15" in text)

        log.part("REFUSAL 4. A project that is not on the sandbox allowlist. The same draft aimed at project OPS, where\n"
                 "the identity is permitted to create, so the allowlist is the only thing that stops it.")
        code, text = log.create("preview", draft="draft-ops.md", link="linked-ops.md")
        log.check("refused at the preview, exit code 1, and no fingerprint was issued, so there is nothing to confirm",
                  code == 1 and fingerprint_in(text) is None and "project OPS (project id 30100)" in text and "is not on the sandbox allowlist" in text)
        log.out("The allowlist is checked again at confirmation. Here the good preview is confirmed against an allowlist")
        log.out("that no longer lists RPT:")
        code, text = log.create("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant", allow=RUN + "/allowlist-without-rpt.json")
        log.check("refused, exit code 1, nothing written", code == 1 and "project RPT (project id 30000)" in text and "is not on the sandbox allowlist" in text)

        log.part("After the refusals, what the fake Jira holds.")
        held = log.show()
        log.check("still 7 stories in RPT, and there is still no link file", "holds 7 stories in project RPT" in held
                  and not os.path.exists(RUN + "/linked.md") and not os.path.exists(RUN + "/linked-ops.md"))

        log.part("THE APPROVED RUN. The same preview, confirmed by its fingerprint, with the confirming person's name,\n"
                 "the draft as it was previewed, and inside the time limit. In this recording the command is started by\n"
                 "the recording script, which stands in for the person. In a real run a person types it.")
        code, text = log.create("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--result", RUN + "/result.md")
        log.check("created, exit code 0: Jira answered 201 with the key RPT-10 and the issue id 30010",
                  code == 0 and "CREATED in Jira: one story. Jira answered 201 with the key RPT-10 and the issue id 30010." in text)
        log.check("the confirmation names the preview's fingerprint and who confirmed, in the same run as the write (criterion 7)",
                  ("CONFIRMATION for preview %s, given by: the participant" % fingerprint) in text
                  and "The confirmation and the write happened in this one run of the command." in text)
        log.check("the link file was written before sending, and the key and id after (criterion 2)",
                  text.index("Written to the link file before sending") < text.index("CREATED in Jira") < text.index("Written to the link file: the key RPT-10 and the issue id 30010."))
        log.check("the story was read back by its id and all 9 fields the payload sent are the same (criterion 1)",
                  "READ BACK from Jira by issue id 30010" in text and text.count(": the same") == 9
                  and "Result: every field the payload sent reads back the same." in text)
        log.check("what Jira set itself is listed, with people not shown", 'priority           Priority      "Medium" (id 3)' in text
                  and "a person, not shown" in text and "Ada Fixture" not in text)
        log.check("the result record has the key, the issue id, the project, the time and the confirmer (criterion 8)",
                  all(part in text for part in ("Issue key: RPT-10", "Identifier of what was created: Jira issue id 30010",
                                                "Target project: RPT (project id 30000)", "Created at: ", "Confirmed by: the participant")))
        log.check("exactly one POST was sent", "1 POST. The POST is the one create." in text and text.count("  POST /rest/api/3/issue") == 1)
        held = log.show()
        log.check("the fake Jira now holds 8 stories in RPT, the new one being RPT-10 (id 30010)", "holds 8 stories" in held and "RPT-10 (id 30010)" in held)
        problems += log.save("confirmation.txt", [("The real approved run: the participant confirming the real preview by its fingerprint.", "live-confirmation.txt")])

        # ------------------------------------------------------------ rerun.txt
        log = Log("Running the approved workflow a second time: jira-create-story, attempt jira-attempt-012", state)
        log.out("This carries on from the approved run recorded in logs/confirmation.txt, in the same STATE folder.")
        log.part("1. The same preview command again, with the same draft. This is the quest's scenario: the next run.")
        code, text = log.create("preview")
        log.check("refused, exit code 1: the draft is already linked to RPT-10, and it is not created twice (criterion 9)",
                  code == 1 and "this draft has already been created in Jira as RPT-10 (issue id 30010)" in text and "It is not created twice" in text)
        log.part("2. The same confirm command again, with the fingerprint that was already used.")
        code, text = log.create("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        log.check("refused, exit code 1: a fingerprint is used once", code == 1 and "A fingerprint is used once" in text)
        log.part("3. What the fake Jira holds after both.")
        held = log.show()
        log.check("still 8 stories in RPT: no second story was created", "holds 8 stories in project RPT" in held)
        log.part("4. The verify command: the link file matched to Jira by issue id, and compared again (criterion 3).")
        code, text = log.create("verify")
        log.check("matched by issue id 30010, the key is as recorded, and every field is the same",
                  code == 0 and "Matched to Jira by issue id 30010: found." in text and "The key in Jira is RPT-10, as the link file records." in text
                  and "Result: every field the payload sent reads back the same." in text and "Every one was a GET" in text)
        log.part("5. Someone gives the story another key in Jira, as when a story is moved. Then verify again.")
        log.run("fake_jira.py", "rename", "--state", "STATE", "--story", "RPT-10", "--to", "RPT-99")
        code, text = log.create("verify")
        with open(RUN + "/linked.md", encoding="utf-8") as f:
            linked = f.read()
        log.check("still matched, by the issue id, and the changed key is reported",
                  code == 0 and "The key has CHANGED in Jira: the link file recorded RPT-10 and the story is now RPT-99." in text)
        log.check("the link file now holds the new key and keeps the earlier one, under the same issue id",
                  'jira_id: "30010"' in linked and 'jira_key: "RPT-99"' in linked and 'earlier_keys: ["RPT-10"]' in linked)
        log.out("")
        log.out("Where Jira cannot prevent a repeat: Jira would accept this same payload again and make a second story.")
        log.out("What stops it here is local: the link file, and a fingerprint that is used once. A person or a tool")
        log.out("creating the same story some other way is not stopped. They would be noticed by the same-title check in")
        log.out("the next preview, and by two stories with one title on the board.")
        problems += log.save("rerun.txt", [("The real preview command run again after the real create.", "live-rerun-preview.txt"),
                                           ("The real confirm command run again with the fingerprint already used.", "live-rerun-confirm.txt"),
                                           ("The real verify command.", "live-verify.txt")])

    # ------------------------------------------------------------ recovery.txt, recorded in this process
    sys.path.insert(0, os.path.join(ROOT, SKILL))
    import create
    fake_jira = create.load_fake()
    with tempfile.TemporaryDirectory() as state:
        log = Log("A create whose answer is lost, and the recovery: jira-create-story, attempt jira-attempt-012", state)
        log.out("This log is recorded inside the recording script, because a lost answer cannot be staged from the")
        log.out("command line. The workflow's own functions are called with a fake Jira that this script controls.")
        log.out("Each block between dashed lines is what the workflow said.")
        fake = fake_jira.FakeJira()
        folder = os.path.join(RUN, "recovery")
        os.makedirs(folder)
        with open(folder + "/draft.md", "w", encoding="utf-8") as f:
            f.write(good.replace("../sources/intake-notes.md", "../../sources/intake-notes.md"))

        def run(command, **more):
            args = dict(command=command, draft=folder + "/draft.md", link=folder + "/linked.md", allowlist=SKILL + "/fake-allowlist.json",
                        catalog=CATALOG, state=state, log=None, result=None, fingerprint=None, confirmed_by=None,
                        pretend_minutes_later=0, today=datetime.date(2026, 11, 19))
            args.update(more)
            del create.LINES[:]
            conn = create.Connection(fake.get, fake.post if command == "confirm" else None, "fixture-site.example.invalid")
            code = create.run(argparse.Namespace(**args), conn)
            text = "\n".join(create.LINES)
            log.out("[%s]" % command)
            log.lines += ["-" * 78, text if command != "preview" or code else "(a preview, as in logs/preview.txt. Its last lines:)\n" + "\n".join(create.LINES[-6:]),
                          "-" * 78, "exit code: %d" % code]
            return code, text

        def rpt():
            return [item["key"] for item in fake.issues if item["key"].startswith("RPT-")]

        log.part("1. A preview, then its confirmation. The fake Jira is told to create the story and then not answer.")
        code, text = run("preview")
        fingerprint = fingerprint_in(text)
        fake.fail_post = "applied-timeout"
        code, text = run("confirm", fingerprint=fingerprint, confirmed_by="the participant")
        fake.fail_post = None
        posts = [1 for method, _ in fake.requests if method == "POST"]
        log.check("exit code 2, and the workflow says it is not known whether the story was created",
                  code == 2 and "It is NOT KNOWN whether Jira created the story. It was not sent again" in text)
        log.check("the create was sent once and not retried", len(posts) == 1)
        log.check("the story does exist in the fake Jira, 8 stories in RPT, and the workflow was never told its key", len(rpt()) == 8)
        with open(folder + "/linked.md", encoding="utf-8") as f:
            linked = f.read()
        log.check("the link file, written before the create was sent, says so: a create was sent and its result is not recorded",
                  'state: "create sent, result not recorded"' in linked and "jira_id: null" in linked)

        log.part("2. The next run. This is where the quest's scenario would create the story a second time.")
        code, text = run("preview")
        log.check("refused, exit code 1: a create was sent and never recorded, so nothing is created",
                  code == 1 and "a create for this draft was sent and its result was never recorded" in text and "reconcile" in text)
        log.check("still one POST in all, and still 8 stories", len([1 for m, _ in fake.requests if m == "POST"]) == 1 and len(rpt()) == 8)

        log.part("3. Reconcile. The search is made to find nothing the first time, as an index that lags behind.")
        fake.search_lag = 1
        code, text = run("reconcile")
        log.check("not found the first time, exit code 1, and it says the search can lag and creates nothing",
                  code == 1 and "NOT FOUND." in text and "Jira's search can lag" in text and len(rpt()) == 8)
        code, text = run("reconcile")
        log.check("found the second time by the marker: exactly one story, RPT-10, issue id 30010, now linked",
                  code == 0 and "FOUND exactly one: RPT-10, issue id 30010. It is linked now." in text)
        log.check("it was read back and every field the payload sent is the same", "Result: every field the payload sent reads back the same." in text)
        with open(folder + "/linked.md", encoding="utf-8") as f:
            linked = f.read()
        log.check("the link file now holds the key and the id", 'state: "created"' in linked and 'jira_id: "30010"' in linked and 'jira_key: "RPT-10"' in linked)
        log.check("through all of it, one POST was sent and one story was created",
                  len([1 for m, _ in fake.requests if m == "POST"]) == 1 and len(rpt()) == 8)

        log.part("4. The other case: the create is sent, Jira never receives it, and nothing is created.")
        fake = fake_jira.FakeJira()
        shutil.rmtree(folder)
        os.makedirs(folder)
        with open(folder + "/draft.md", "w", encoding="utf-8") as f:
            f.write(good.replace("../sources/intake-notes.md", "../../sources/intake-notes.md"))
        code, text = run("preview")
        fake.fail_post = "timeout"
        run("confirm", fingerprint=fingerprint_in(text), confirmed_by="the participant")
        fake.fail_post = None
        code, text = run("reconcile")
        log.check("reconcile reports not found, exit code 1, links nothing and creates nothing: 7 stories, one POST",
                  code == 1 and "NOT FOUND." in text and len(rpt()) == 7 and len([1 for m, _ in fake.requests if m == "POST"]) == 1)
        log.check("it leaves the decision to a person: delete the link file by hand, then preview again",
                  "a person decides: delete the link file by hand, then make a new preview." in text)
        shutil.rmtree(folder)
        problems += log.save("recovery.txt")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
