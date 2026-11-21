#!/usr/bin/env python3
"""Records logs/second-run.txt and logs/disappearance.txt for the github-read-assigned-issues quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts GitHub: every run is
against the made-up GitHub in participant/skills/github-read-assigned/fake_github.py,
and every repository, issue, comment and login is invented.

The runs write participant/context/github/assigned/: index.md, issues/,
delivery-links.md and assigned.json. This script removes those first, because
they are generated and can be made again. It never writes, moves or removes
anything in the notes folder there. Two parts need a GitHub more awkward than
the made-up one. They run in this script's own process and write to a
temporary folder, shown as COPY.

This script checks for itself. It counts the issues and pull requests in the
made-up GitHub, the rows of the index and the record files, and takes the
SHA-256 of every notes file and every generated file, rather than taking the
sync's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/github-read-assigned"
SYNC = SKILL + "/sync.py"
OUT = "participant/context/github/assigned"
INDEX, MEMORY, NOTES, ISSUES, LINKS = OUT + "/index.md", OUT + "/assigned.json", OUT + "/notes", OUT + "/issues", OUT + "/delivery-links.md"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_github  # noqa: E402
import sync  # noqa: E402


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.copy = [title], [], None
        self.out("Recorded by scripts/record_evidence.py. No request was sent to GitHub. Every repository, issue, comment and login is made up.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.copy, "COPY") if self.copy else text

    def block(self, title, code, text):
        self.out(title)
        self.lines += ["-" * 78, self.tidy(text.rstrip("\n")), "-" * 78, "exit code: %s" % code]

    def command(self, *args, script=SYNC):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.block("$ python3 %s" % " ".join([script] + list(args)), done.returncode, done.stdout)
        return done.returncode, done.stdout

    def in_process(self, what, fake, out_dir, **options):
        """A sync started inside this script, for a made-up GitHub that the command line cannot make."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            try:
                code = sync.run(sync.Client(fake.get, sleep=lambda s: None), out_dir, "fake", now=fake.now, **options)
            except sync.Stop as stop:
                print("github-sync: STOPPED: %s.\ngithub-sync: Nothing was written." % stop)
                code = 1
        self.block("(inside this script) %s" % what, code, printed.getvalue())
        return code, printed.getvalue()

    def save(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.out()
        self.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems else "%d OF %d CHECKS FAILED." % (len(self.problems), count)))
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def notes_now():
    return {name: sha(os.path.join(NOTES, name)) for name in sorted(os.listdir(NOTES))}


def generated_now():
    """SHA-256 of every generated file: the index, the links, the memory and each record."""
    found = {name: sha(name) for name in (INDEX, LINKS, MEMORY)}
    found.update((ISSUES + "/" + name, sha(os.path.join(ISSUES, name))) for name in sorted(os.listdir(ISSUES)))
    return found


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def memory():
    return json.loads(read(MEMORY))


def line(text, start):
    return next((row for row in text.splitlines() if start in row), "")


def twice(state):
    """Issues that hold a comment id or a timeline key more than once."""
    return [node for node, record in state["issues"].items()
            if len({c["id"] for c in record["comments"]}) != len(record["comments"])
            or len({e["key"] for e in record["events"]}) != len(record["events"])]


def second_run(notes_start):
    log = Log("Two synchronizations in a row. github-read-assigned-issues, attempt github-attempt-001")
    fake = fake_github.FakeGitHub()
    mine = fake.assigned_to_me()
    issues, pulls = [i for i in mine if not i["pr"]], [i for i in mine if i["pr"]]
    log.out("Counted by this script in the made-up GitHub: %d items assigned to the user, of which %d issues and %d pull requests."
            % (len(mine), len(issues), len(pulls)))
    log.out("Notes files before the first sync, SHA-256 taken by this script:")
    for name, value in notes_start.items():
        log.out("  notes/%s  %s" % (name, value))

    log.part("PART 1. The first synchronization")
    code, text = log.command("--source", "fake")
    state, index = memory(), read(INDEX)
    files = sorted(os.listdir(ISSUES))
    log.check("exit code 0", code == 0)
    log.check("criterion 1: the identity is the one the made-up GitHub answers with, and the run says so",
              state["identity"] == {"login": fake_github.ME["login"], "id": fake_github.ME["id"]} and "login robin-fixture, user id 9001" in text)
    log.check("criterion 1: the login is not in sync.py", fake_github.ME["login"] not in read(SKILL + "/sync.py"))
    log.check("criterion 2: the scope is stated, and all 5 repositories are listed in the index",
              "| Scope | every repository GitHub lists an assigned issue in |" in index and index.count("| read. ") == 5)
    log.check("criterion 3: %d pull requests left out, and none has a record" % len(pulls),
              "pull requests left out: %d. Issues: %d" % (len(pulls), len(issues)) in text
              and not {i["node_id"] for i in pulls} & (set(state["issues"]) | {name[:-3] for name in files}))
    log.check("criterion 4: the list took 2 requests, 100 + 49, and GitHub reported no further page",
              "149 items in 2 requests (100 + 49). GitHub reported no further page after the last" in text)
    log.check("criterion 4: retrieved %d, and GitHub's search declared %d" % (len(issues), len(issues)),
              "retrieved %d issues. GitHub's search declares %d. The totals agree" % (len(issues), len(issues)) in text)
    log.check("the issues this script counted are exactly the ones recorded: %d" % len(issues),
              {i["node_id"] for i in issues} == set(state["issues"]) == {name[:-3] for name in files})
    log.check("rows in the index, counted by this script: %d" % sync.rows_in_index(index), sync.rows_in_index(index) == len(issues))
    twelve = sorted(node for node, r in state["issues"].items() if r["number"] == 12)
    log.out("  issues numbered 12: %s" % ", ".join("%s is %s#12" % (n, state["issues"][n]["full_name"]) for n in twelve))
    log.check("criterion 6: three issues are numbered 12, in three repositories, each with its own record file and its own title",
              len(twelve) == 3 and len({state["issues"][n]["full_name"] for n in twelve}) == 3
              and all(os.path.exists(os.path.join(ISSUES, n + ".md")) for n in twelve)
              and len({state["issues"][n]["title"] for n in twelve}) == 3
              and all(state["issues"][n]["title"] in read(ISSUES + "/" + n + ".md") for n in twelve))
    comments = sum(len(i["comments"]) for i in issues)
    log.check("criterion 7: every comment in the made-up GitHub is held once: %d" % comments,
              sum(len(r["comments"]) for r in state["issues"].values()) == comments and not twice(state))
    first = generated_now()

    log.part("PART 2. The second synchronization, with nothing changed in the made-up GitHub")
    code, text = log.command("--source", "fake")
    state = memory()
    log.check("exit code 0", code == 0)
    log.check("criterion 4: the same paging summary and the same totals",
              "149 items in 2 requests (100 + 49)" in text and "The totals agree" in text)
    log.check("0 new, 0 changed, %d unchanged" % len(issues), "This sync: 0 new, 0 changed, %d unchanged, 0 newly flagged" % len(issues) in text)
    log.check("criterion 7: %d comments read, 0 added. No comment or timeline entry is held twice" % comments,
              "comments read: %d. Added to the local copy: 0, edited: 0" % comments in text
              and "Added to the local copy: 0\n" in text.split("timeline entries read")[1] and not twice(state))
    second = generated_now()
    log.check("every generated file is byte for byte what the first sync wrote: %d files, SHA-256 taken by this script" % len(second),
              first == second)
    log.check("criterion 9: every notes file has the SHA-256 it had before the first sync", notes_now() == notes_start)
    log.check("criterion 9: no note text is in the index, the records or the memory",
              not any("Made-up note" in read(name) for name in second))
    log.check("criterion 11: the sync time is held for each of 5 repositories and each of %d issues" % len(issues),
              all(r["last_successful_sync"] == fake.now for r in state["repos"].values())
              and all(r["last_synced"] == fake.now for r in state["issues"].values()))

    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        log.part("PART 3. A repository GitHub refuses to show the comments of (criterion 2)")
        fake = fake_github.FakeGitHub()
        fake.deny_details(fake_github.SUPPORT)
        code, text = log.in_process("the made-up GitHub, with repository id 102 answering 403 for comments and timelines", fake, copy)
        state = json.loads(read(os.path.join(copy, "assigned.json")))
        index = read(os.path.join(copy, "index.md"))
        log.out("  " + line(index, "COULD NOT BE READ"))
        log.check("exit code 0: the other repositories were synchronized", code == 0)
        log.check("the run says the repository could not be read, and how many issues that leaves out",
                  "repository id 102, public: COULD NOT BE READ" in text and "14 assigned issues there not recorded" in text)
        log.check("the index lists it as not read, with no successful sync",
                  "| never | **COULD NOT BE READ** (status 403). 14 assigned issues there not refreshed |" in index
                  and state["repos"]["102"]["last_successful_sync"] is None)
        log.check("126 retrieved, 14 not recorded, 112 recorded", len(state["issues"]) == 112)

    with tempfile.TemporaryDirectory() as copy:
        log.copy = copy
        log.part("PART 4. GitHub's list ends early, and the declared total catches it (criterion 4)")
        fake = fake_github.FakeGitHub()
        fake.drop_next_link = ("/issues",)
        code, text = log.in_process("the made-up GitHub, whose first page of the list says there is no further page", fake, copy)
        log.check("exit code 1", code == 1)
        log.check("the run says the totals disagree", "They disagree, so the list cannot be taken as complete" in text)
        log.check("nothing was written", os.listdir(copy) == [])
    return log.save("second-run.txt")


def disappearance(notes_start):
    log = Log("Issues that closed, moved or became unreadable between synchronizations. github-read-assigned-issues, attempt github-attempt-001")
    log.out("This follows the two runs in second-run.txt, in the same folder. The made-up GitHub is now at step 1, a day later:")
    log.out("  acme-fixture/platform#7 was closed as completed, by a commit, after a pull request that mentions it was merged")
    log.out("  acme-fixture/support#12 was transferred to beta-fixture/docs, where it is number 41 with a new node ID")
    log.out("  acme-fixture/design#5 was given to someone else")
    log.out("  beta-fixture/docs#3 was deleted")
    log.out("  acme-fixture/legacy-tools, a private repository with two closed issues, can no longer be seen by the connection")
    log.out("  acme-fixture/design was renamed acme-fixture/design-system")
    log.out("  acme-fixture/platform#2 got a new comment and an edited one, and acme-fixture/platform#200 is new")
    before = memory()
    held = generated_now()

    log.part("PART 1. The synchronization after the changes")
    code, text = log.command("--source", "fake", "--fake-step", "1")
    state, index = memory(), read(INDEX)
    issues = state["issues"]
    log.check("exit code 0", code == 0)
    log.check("nothing was deleted: every issue held before is still held, and every record file is still there",
              set(before["issues"]) <= set(issues) and all(os.path.exists(name) for name in held))
    gone = {node: r for node, r in issues.items() if r["status"] != "assigned"}
    for node, r in sorted(gone.items()):
        log.out("  %s  %s#%d  %s  last known state: %s" % (node, r["full_name"], r["number"], r["reason"], sync.state_words(r)))
    log.check("criterion 10: 5 issues are flagged, none deleted",
              len(gone) == 5 and "5 newly flagged as no longer assigned" in text and text.count("FLAGGED, not deleted") == 5)
    moved = issues["I_kwFX1020012"]
    log.check("TRANSFERRED: support#12 is flagged as transferred, with where it went and the state it was last in",
              moved["reason"] == "transferred" and moved["moved_to"] == {"ref": "beta-fixture/docs#41", "node_id": "I_kwFX1040041"}
              and moved["state"] == "open" and moved["title"] == before["issues"]["I_kwFX1020012"]["title"])
    log.check("the issue it became is recorded as new, and points back to the one it was",
              issues["I_kwFX1040041"]["status"] == "assigned" and issues["I_kwFX1040041"]["previously"] == ["acme-fixture/support#12, node ID I_kwFX1020012"])
    log.check("UNREADABLE: both legacy-tools issues are flagged as not found, with the closed states they were last in",
              [(issues[n]["reason"], issues[n]["state"], issues[n]["state_reason"]) for n in ("I_kwFX1050001", "I_kwFX1050002")]
              == [("not found", "closed", "not_planned"), ("not found", "closed", "completed")])
    log.check("the repository's last successful sync is still the earlier one",
              state["repos"]["105"]["last_successful_sync"] == "2026-11-02T09:00:00Z" != state["repos"]["101"]["last_successful_sync"])
    log.check("reassigned and deleted issues are flagged with those reasons",
              (issues["I_kwFX1030005"]["reason"], issues["I_kwFX1040003"]["reason"]) == ("reassigned", "deleted"))
    closed = issues["I_kwFX1010007"]
    log.out("  " + line(text, "CLOSED since the last sync").strip())
    log.check("CLOSED: platform#7 is still assigned, is now closed (completed), and the run says it was open",
              closed["status"] == "assigned" and (closed["state"], closed["state_reason"]) == ("closed", "completed")
              and "is now closed (completed). It was open" in text)
    log.check("its record holds both states, each with the sync that saw it",
              [(h["state"], h["seen_at"]) for h in closed["state_history"]] == [("open", "2026-11-02T09:00:00Z"), ("closed", "2026-11-03T09:00:00Z")]
              and "| 2026-11-02T09:00:00Z | open |" in read(ISSUES + "/I_kwFX1010007.md"))
    log.check("criterion 8: the pull request and the commit that answer it are held as links, and its delivery evidence exists",
              [(l["kind"], l["ref"]) for l in sync.links_of(closed)] == [("pull request", "acme-fixture/platform#302"), ("commit", "c3" * 20)]
              and sync.delivery(closed) == "exists")
    for node in sorted(gone):
        record = read(ISSUES + "/" + node + ".md")
        if "The fields here are the last known state" not in record or issues[node]["title"] not in record:
            log.check("the record of %s still holds its last known state" % node, False)
    log.check("each of the 5 records still holds the issue's fields, and says they are the last known state", not log.problems)
    log.check("the index lists the 5 in their own section, with the last known state of each",
              "## No longer among the assigned issues (5)" in index and index.split("## No longer among")[1].count("\n| `") == 5)
    log.check("criterion 6: the renamed repository's issues kept their records, with the earlier name",
              issues["I_kwFX1030012"]["full_name"] == "acme-fixture/design-system" and issues["I_kwFX1030012"]["previously"] == ["acme-fixture/design#12"]
              and issues["I_kwFX1030012"]["first_seen"] == "2026-11-02T09:00:00Z")
    two = issues["I_kwFX1010002"]["comments"]
    log.check("criterion 7: platform#2 has 4 comments, the new one once and the edited one in place of the old",
              len(two) == 4 and two[0]["body"].endswith("edited.") and "Added to the local copy: 1, edited: 1" in text and not twice(state))
    log.check("criterion 11: a flagged issue keeps the time it was last synced, and the others have the new time",
              moved["last_synced"] == "2026-11-02T09:00:00Z" and closed["last_synced"] == "2026-11-03T09:00:00Z")
    log.check("rows in the index and record files, counted by this script: 128 and 128",
              sync.rows_in_index(index) == 128 == len(os.listdir(ISSUES)) == len(issues))
    log.check("criterion 9: every notes file has the SHA-256 it had before the first sync, the notes of two flagged issues included",
              notes_now() == notes_start and {"I_kwFX1020012.md", "I_kwFX1050001.md"} <= set(notes_start))
    log.check("the index still shows the notes of the transferred issue", "`notes/I_kwFX1020012.md`" in line(index, "| `acme-fixture/support#12`"))
    first = generated_now()

    log.part("PART 2. The same synchronization again")
    code, text = log.command("--source", "fake", "--fake-step", "1")
    log.check("exit code 0", code == 0)
    log.check("nothing is flagged a second time, and nothing is new or changed",
              "This sync: 0 new, 0 changed, 123 unchanged, 0 newly flagged as no longer assigned" in text)
    log.check("every generated file is byte for byte as it was: %d files" % len(first), generated_now() == first)
    log.check("no comment or timeline entry is held twice", not twice(memory()))
    log.check("every notes file has the SHA-256 it had before the first sync", notes_now() == notes_start)
    return log.save("disappearance.txt")


def main():
    os.chdir(ROOT)
    for name in (INDEX, LINKS, MEMORY):
        if os.path.exists(name):
            os.remove(name)
    if os.path.isdir(ISSUES):
        for name in os.listdir(ISSUES):
            os.remove(os.path.join(ISSUES, name))
    notes_start = notes_now()
    ok = second_run(notes_start)
    ok = disappearance(notes_start) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
