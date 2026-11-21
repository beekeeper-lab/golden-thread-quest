#!/usr/bin/env python3
"""Records logs/stale-run.txt, logs/missing-timestamp.txt and logs/refresh.txt for the context-staleness quest.

Each block between dashed lines is what a command printed, started as a
person would start it. Only local files are read. Everything in the library
is made up. The clock is set on every run with --now, so the logs come out
the same whenever this script is run.

stale-run.txt runs on the library in the repository,
participant/context/freshness/library/, and changes nothing in it. The other
two logs change items, so they run on a copy in a temporary folder, shown in
the log as COPY.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
TOOL = "participant/skills/context-freshness/answer.py"
LIBRARY = "participant/context/freshness/library"
FRESH, LATER, NINE_DAYS = "2026-11-19T09:00:00Z", "2026-11-19T21:00:00Z", "2026-11-28T09:00:00Z"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what a command printed.\n"
        "Only local files are read. Every release, work item, team and decision here is made up, so nothing is redacted.")


class Log:
    def __init__(self, title, copy=None):
        self.lines, self.problems, self.copy = [title, HEAD], [], copy

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

    def run(self, *args):
        self.out("$ python3 %s %s" % (TOOL, self.tidy(" ".join(args))))
        done = subprocess.run([sys.executable, TOOL] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text = self.tidy(done.stdout.rstrip("\n"))
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text

    def show_file(self, path, lines=10):
        self.out("The first lines of %s:" % self.tidy(path))
        with open(path, encoding="utf-8") as f:
            self.lines += ["-" * 78] + f.read().split("\n")[:lines] + ["-" * 78]

    def save(self, name):
        self.out("")
        self.out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(self.problems) if self.problems else "ALL CHECKS PASSED."))
        with open(os.path.join(REL, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        return self.problems


def state(folder):
    found = {}
    for where, _, names in os.walk(folder):
        for name in sorted(names):
            path = os.path.join(where, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, folder)] = (hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mtime_ns)
    return found


def headline(text):
    return [line for line in text.split("\n") if line.startswith("ANSWER: ")][0]


def drop_line(path, start):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(line for line in lines if not line.startswith(start)))


def main():
    os.chdir(ROOT)
    os.makedirs(REL + "/logs", exist_ok=True)
    problems = []

    # ------------------------------------------------------------ stale-run.txt
    log = Log("The same question answered from fresh context and after the clock has moved: context-staleness, attempt context-attempt-001")
    before = state(LIBRARY)
    log.part("THE DATA. Every item in the library records when it was retrieved (criterion 1). Two of the nine files:")
    log.show_file(LIBRARY + "/work-items/WI-104.md", 10)
    log.show_file(LIBRARY + "/release-2.4.md", 7)
    log.out("WI-104 also gives one field, blocked_by, a retrieval time of its own, older than the record's.")

    log.part("RUN 1. The clock is set to %s. Everything the answer uses is inside its limit." % FRESH)
    code, text = log.run("blockers", "--release", "REL-2.4", "--now", FRESH)
    log.check("the run shows the clock value that was set (criterion 6)", "Clock: %s (set with --now)" % FRESH in text)
    log.check("the answer is a plain statement: 2 work items are blocking, exit code 0", code == 0 and headline(text) == "ANSWER: 2 work items are blocking release REL-2.4.")
    log.check("it lists all 10 items of context it used, each with its retrieval time, age, limit and verdict",
              "CONTEXT USED, oldest first: 10 items." in text and text.split("CONTEXT USED")[1].count(" fresh") >= 10)
    log.check("it names the oldest context it used and its age: decision D-12, 48 days 23 hours, limit 90 days (criterion 3)",
              "Oldest context used: decisions/D-12.md, retrieved 2026-10-01T10:00:00Z, age 48d 23h 00m, limit 90 days: fresh." in text)
    log.check("it says nothing is stale", "Stale context: none." in text)

    log.part("RUN 2. The same question, the same library. The clock is moved nine days on, to %s.\n"
             "This is the quest's scenario: a snapshot nine days old. The statuses (limit 24 hours) and the release\n"
             "scope (limit 3 days) are past their limits. The team (30 days) and the decision (90 days) are not." % NINE_DAYS)
    code, text = log.run("blockers", "--release", "REL-2.4", "--now", NINE_DAYS)
    log.check("the run shows the clock value that was set", "Clock: %s (set with --now)" % NINE_DAYS in text)
    log.check("the answer is qualified, exit code 1: it CANNOT SAY what is blocking, and gives no count (criterion 4)",
              code == 1 and headline(text) == "ANSWER: CANNOT SAY what is blocking release REL-2.4." and "work items are blocking" not in text)
    log.check("no work item is stated as blocking or as not blocking",
              not any(line.startswith(("  BLOCKING", "  NOT BLOCKING", "  SET ASIDE")) for line in text.split("\n")))
    log.check("what the stale items last said is shown as last known and not as a claim, for all 6 work items",
              all(("  %s " % item) in text.split("LAST KNOWN, NOT A CURRENT CLAIM:")[1].split("CONTEXT USED")[0]
                  for item in ("WI-101", "WI-102", "WI-103", "WI-104", "WI-105", "WI-106")))
    log.check("the 8 stale items are named one by one, each with its age and how far it is over its limit",
              "STALE CONTEXT, 8 items, each named:" in text and text.split("STALE CONTEXT, 8 items")[1].count(" over its limit of ") == 8)
    log.check("it names the oldest context it used and its age: decision D-12, 57 days 23 hours, still inside 90 days",
              "Oldest context used: decisions/D-12.md, retrieved 2026-10-01T10:00:00Z, age 57d 23h 00m, limit 90 days: fresh." in text)
    log.check("nothing stale was left out: all 10 items are still in the list of context used", "CONTEXT USED, oldest first: 10 items." in text)
    log.check("what is still fresh is still said: decision D-12", "Decision D-12, inside its limit, says:" in text)

    log.part("RUN 3. In between: the clock is set twelve hours after run 1, to %s.\n"
             "Two statuses retrieved the evening before are now 25 hours old. The scope is still inside its limit.\n"
             "So only what is said about those two items is spoiled." % LATER)
    code, text = log.run("blockers", "--release", "REL-2.4", "--now", LATER)
    log.check("the answer is PARTIAL: 2 are blocking as far as fresh context shows, 2 cannot be assessed",
              code == 1 and headline(text) == "ANSWER: PARTIAL: 2 work items are blocking release REL-2.4 as far as fresh context shows. 2 cannot be assessed.")
    log.check("WI-105 and WI-106 are shown as last known, and are not in the statements of fact",
              "  WI-105 " in text.split("LAST KNOWN")[1] and "NOT BLOCKING  WI-105" not in text and "SET ASIDE     WI-106" not in text)
    log.check("one field is stale while its record is fresh: WI-104 is Blocked (fresh), its reason is last known (33 hours)",
              "WI-104 \"Update the privacy notice\" is Blocked. Why, last known and not a current claim:" in text)

    log.part("THE WORKING. The ages command prints, for every item, the sum a person would do by hand from the\n"
             "policy: the clock value minus the retrieval time, against the limit for the kind (criterion 7).")
    code, text = log.run("ages", "--now", LATER)
    log.check("it gives each item's age and limit, and 3 of 10 are stale at this clock value", "Stale: 3 of 10." in text)
    log.out("")
    log.out("Worked by hand for run 3 from participant/context/freshness/policy.md, before looking at the tool:")
    log.out("  release-2.4.md   retrieved 11-18 16:00, clock 11-19 21:00: 29 hours. Limit 3 days. Fresh.")
    log.out("  WI-105, WI-106   retrieved 11-18 20:00: 25 hours. Limit 24 hours. Stale.")
    log.out("  WI-101 to WI-104 retrieved 11-19 07:00: 14 hours. Limit 24 hours. Fresh.")
    log.out("  WI-104 blocked_by retrieved 11-18 12:00: 33 hours. Limit 24 hours. Stale.")
    log.out("  team.md 17 days (limit 30). D-12 49 days (limit 90). Fresh.")
    log.out("  Scope fresh and two statuses stale, so the policy's table gives the first line: PARTIAL, 2 cannot be assessed.")
    log.check("the tool's ages agree with that working", all(part in text for part in (
        "release-2.4.md                         release-scope     2026-11-18T16:00:00Z  1d 05h 00m", "work-items/WI-105.md                   work-item-status  2026-11-18T20:00:00Z  1d 01h 00m   24 hours STALE",
        "work-items/WI-101.md                   work-item-status  2026-11-19T07:00:00Z  0d 14h 00m   24 hours fresh", "work-items/WI-104.md, field blocked_by work-item-status  2026-11-18T12:00:00Z  1d 09h 00m   24 hours STALE")))

    log.part("AFTERWARDS. The library.")
    log.check("all 9 files in the library have the SHA-256 and the modified time they had before the runs", state(LIBRARY) == before and len(before) == 9)
    log.out("  Running the script again gives this same log, because every run sets the clock.")
    problems += log.save("stale-run.txt")

    # ------------------------------------------------------------ missing-timestamp.txt
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "library")
        shutil.copytree(LIBRARY, copy)
        log = Log("An item with no retrieval time, treated as stale: context-staleness, attempt context-attempt-001", tmp)
        log.out("The library here is a copy of the one in the repository, in a temporary folder shown as COPY.")
        log.part("1. In the copy, the retrieved_at line is taken out of WI-103. Everything else is as in run 1 of\n"
                 "stale-run.txt, where WI-103 was 2 hours old, In Progress and stated as not blocking.")
        drop_line(copy + "/work-items/WI-103.md", "retrieved_at:")
        log.show_file(copy + "/work-items/WI-103.md", 9)
        code, text = log.run("blockers", "--release", "REL-2.4", "--now", FRESH, "--library", copy)
        log.check("the item is treated as STALE, with the reason: it records no retrieval time (criterion 5)",
                  "work-items/WI-103.md (work-item-status): it records no retrieval time." in text)
        log.check("it is not stated as fresh fact: WI-103 is no longer among the items stated as not blocking", "NOT BLOCKING  WI-103" not in text)
        log.check("the answer is qualified, exit code 1: PARTIAL, 1 cannot be assessed",
                  code == 1 and headline(text) == "ANSWER: PARTIAL: 2 work items are blocking release REL-2.4 as far as fresh context shows. 1 cannot be assessed.")
        log.check("what its copy says is shown as last known, of unknown age", "was In Progress in a copy of unknown age." in text)
        log.check("an unknown age is treated as the oldest: WI-103 is named as the oldest context used",
                  "Oldest context used: work-items/WI-103.md. Its age is unknown, because it records no retrieval time." in text)
        log.check("the item is not hidden: it is in the list of context used and in the list to refresh",
                  "work-items/WI-103.md                   work-item-status  none recorded         unknown" in text and "nothing else: work-items/WI-103.md." in text)

        log.part("2. The same for a time that cannot be read. WI-103's retrieved_at is set to the word \"yesterday\".")
        with open(copy + "/work-items/WI-103.md", encoding="utf-8") as f:
            body = f.read()
        with open(copy + "/work-items/WI-103.md", "w", encoding="utf-8") as f:
            f.write(body.replace('kind: "work-item-status"', 'kind: "work-item-status"\nretrieved_at: "yesterday"'))
        code, text = log.run("blockers", "--release", "REL-2.4", "--now", FRESH, "--library", copy)
        log.check("treated as stale: its retrieval time cannot be read", code == 1 and "its retrieval time cannot be read as a time in UTC." in text and "NOT BLOCKING  WI-103" not in text)

        log.part("3. And for a time later than the clock: retrieved_at is set one hour after the clock value.")
        with open(copy + "/work-items/WI-103.md", "w", encoding="utf-8") as f:
            f.write(body.replace('kind: "work-item-status"', 'kind: "work-item-status"\nretrieved_at: "2026-11-19T10:00:00Z"'))
        code, text = log.run("blockers", "--release", "REL-2.4", "--now", FRESH, "--library", copy)
        log.check("treated as stale: its retrieval time is later than the clock", code == 1 and "its retrieval time is later than the clock." in text and "NOT BLOCKING  WI-103" not in text)
        problems += log.save("missing-timestamp.txt")

    # ------------------------------------------------------------ refresh.txt
    with tempfile.TemporaryDirectory() as tmp:
        copy, source = os.path.join(tmp, "library"), os.path.join(tmp, "source")
        shutil.copytree(LIBRARY, copy)
        shutil.copytree(LIBRARY, source)
        log = Log("Refreshing only the items found stale: context-staleness, attempt context-attempt-001", tmp)
        log.out("A stretch goal. The quest allows no live connection, so the place items are fetched from is a made-up")
        log.out("folder, COPY/source, standing for the system the context came from. In it WI-105 has moved on: it is now")
        log.out("Blocked. The library is a copy in COPY/library.")
        with open(source + "/work-items/WI-105.md", encoding="utf-8") as f:
            newer = f.read().replace('status: "In Review"', 'status: "Blocked"').replace("blocked_by: null", 'blocked_by: "A load test failed"')
        with open(source + "/work-items/WI-105.md", "w", encoding="utf-8") as f:
            f.write(newer)
        before = state(copy)
        log.part("1. The clock is %s, as in run 3 of stale-run.txt: three items are stale." % LATER)
        code, text = log.run("refresh", "--source", source, "--now", LATER, "--library", copy)
        after = state(copy)
        changed = sorted(name for name in before if before[name] != after[name])
        log.check("3 stale items were fetched again and 6 fresh ones were left untouched", code == 0 and "Refreshed 3 of 3 stale items. 6 fresh items were not fetched and not rewritten." in text)
        log.check("checked by this script: exactly those 3 files changed, and the other 6 have the same SHA-256 and modified time",
                  changed == ["work-items/WI-104.md", "work-items/WI-105.md", "work-items/WI-106.md"])
        log.part("2. The same question again, at the same clock value.")
        code, text = log.run("blockers", "--release", "REL-2.4", "--now", LATER, "--library", copy)
        log.check("the answer is a plain statement again, exit code 0, and nothing is stale", code == 0 and "Stale context: none." in text)
        log.check("it is a different answer: 3 work items are blocking. The stale copy of WI-105 said In Review, and it is now Blocked",
                  headline(text) == "ANSWER: 3 work items are blocking release REL-2.4." and 'BLOCKING      WI-105' in text)
        problems += log.save("refresh.txt")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
