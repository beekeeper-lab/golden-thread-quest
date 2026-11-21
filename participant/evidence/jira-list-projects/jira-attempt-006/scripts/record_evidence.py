#!/usr/bin/env python3
"""Records logs/projects-run.txt and generates participant/context/jira/projects.md.

Everything here runs against scripts/fake_jira.py. No network is used, and no
real Jira is read or changed. Every project is made up.

Part 1 is the two runs the quest asks for: retrieving the projects, then
retrieving them again after a project was renamed. It writes into
participant/context/jira/, which is where the committed list lives:
projects.md, projects.json and projects/. Those three are removed first, so
what is there afterwards comes from this recording. Nothing else in that
folder is touched.

Part 2 tries the page boundaries the quest's hint points at, at Jira's
ordinary page size of 50. It writes into temporary folders.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
OUT = "participant/context/jira"
sys.path.insert(0, HERE)
import fake_jira  # noqa: E402
import projects  # noqa: E402

lines, problems = [], []


def out(text=""):
    lines.append(text)


def check(label, ok):
    out("  %-4s %s" % ("ok" if ok else "FAIL", label))
    if not ok:
        problems.append(label)


def run(get, folder, page_size):
    """One run of the skill. Writes what it printed into the log and returns (exit code, text)."""
    projects.LINES.clear()
    try:
        code = projects.run(get, folder, "fake", page_size=page_size)
    except projects.Stop as stop:
        projects.say("")
        projects.say("STOPPED: %s." % stop)
        projects.say("Nothing was written.")
        code = 1
    text = "\n".join(projects.LINES)
    out("-" * 78)
    out(text)
    out("-" * 78)
    out("exit code: %d" % code)
    return code, text


def rows(path, needle, section=None):
    """Lines of the list holding `needle`. With `section`, only lines under that heading."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if section:
        start = text.index("## " + section)
        end = text.find("\n## ", start + 1)
        text = text[start:end if end != -1 else len(text)]
    return [line for line in text.split("\n") if needle in line]


def main():
    os.chdir(ROOT)
    for name in ("projects.md", "projects.json"):
        if os.path.exists(os.path.join(OUT, name)):
            os.remove(os.path.join(OUT, name))
    shutil.rmtree(os.path.join(OUT, "projects"), ignore_errors=True)

    out("Retrieving projects, and retrieving them again after a rename: jira-list-projects, attempt jira-attempt-006")
    out("Recorded by scripts/record_evidence.py. Each block between dashed lines is what the skill printed.")
    out("Everything here runs against scripts/fake_jira.py, a made-up Jira. No real Jira was read or changed,")
    out("so that a project could be renamed and removed. Every project is synthetic, so nothing is redacted.")

    out("")
    out("=" * 78)
    out("PART 1. THE TWO RUNS. Eleven made-up projects, 5 to a page, written to %s/." % OUT)
    out("")
    out("RUN 1. Nothing is held yet.")
    out("$ projects.py --source fake --out %s --page-size 5      (the fake holding 11 projects)" % OUT)
    fake = fake_jira.FakeJira(count=11)
    code, text = run(fake.get, OUT, 5)
    files_1 = sorted(os.listdir(os.path.join(OUT, "projects")))
    out("")
    check("all 11 projects were retrieved, over 3 pages of 5, 5 and 1",
          code == 0 and "11 project(s) received over 3 page(s). Jira's own count: 11." in text)
    check("11 files, each named by a project id: %s ... %s" % (files_1[0], files_1[-1]),
          files_1 == ["%d.md" % n for n in range(10001, 10012)])

    renamed, relabelled, gone = fake.by_key("DPAT"), fake.by_key("MAOB"), fake.by_key("ONB")
    out("")
    out("BETWEEN THE RUNS, on the fake Jira:")
    out("  1. Project id %s: its KEY is changed from DPAT to DATA. This is the quest's scenario." % renamed["id"])
    out("  2. Project id %s: its NAME is changed from 'Mobile app' to 'Mobile apps'." % relabelled["id"])
    out("  3. Project id %s (key ONB) is removed, so Jira no longer returns it." % gone["id"])
    out("  4. A new project is added with the key BIL2 and the name 'Billing', a name another project already has.")
    fake.rename(renamed["id"], key="DATA")
    fake.rename(relabelled["id"], name="Mobile apps")
    fake.remove(gone["id"])
    added = fake.add("BIL2", "Billing")

    out("")
    out("RUN 2. The same command again.")
    out("$ projects.py --source fake --out %s --page-size 5" % OUT)
    code, text = run(fake.get, OUT, 5)
    files_2 = sorted(os.listdir(os.path.join(OUT, "projects")))
    out("")
    check("the project whose key changed was matched to its existing record",
          "RENAMED: project id %s, key was 'DPAT' and is now 'DATA'. Same id, same record, same file." % renamed["id"] in text)
    check("the project whose name changed was matched too",
          "RENAMED: project id %s, name was 'Mobile app' and is now 'Mobile apps'." % relabelled["id"] in text)
    check("the removed project was flagged and kept, not deleted",
          "NOT RETURNED: project id %s (key 'ONB', name 'Onboarding'). Kept and flagged, not deleted." % gone["id"] in text)
    check("the only new file is for the new project (%s.md); no file was renamed or removed" % added,
          files_2 == sorted(files_1 + [added + ".md"]))
    check("no file is named by a key: there is no DATA.md, DPAT.md or BIL2.md",
          not any(name.split(".")[0] in ("DATA", "DPAT", "BIL2", "ONB") for name in files_2))
    check("12 projects are held: the 11 from run 1, the removed one among them, and the new one",
          "held now: 12. new: 1, unchanged: 8, renamed: 2, not returned: 1" in text)

    listing = os.path.join(OUT, "projects.md")
    out("")
    out("FINDING THE RENAMED PROJECT in %s, by each of its labels" % listing)
    for label, section, needle in (
            ("its new key", "By key", "| `DATA` |"), ("its OLD key", "By key", "| `DPAT` *(former key)*"),
            ("its name", "By name", "| Data platform |"),
            ("its project id", "By project id", "| [`%s`](projects/%s.md) |" % (renamed["id"], renamed["id"]))):
        found = rows(listing, needle, section)
        out("  by %s, in the table '%s':" % (label, section))
        for row in found:
            out("    " + row)
        check("found by %s, and the row leads to projects/%s.md" % (label, renamed["id"]),
              len(found) == 1 and "projects/%s.md" % renamed["id"] in found[0])
    out("")
    out("THE REMOVED PROJECT, as the list now shows it:")
    for row in rows(listing, "projects/%s.md" % gone["id"]):
        out("    " + row)
    check("it is in the list four times, flagged, and under 'Not returned by Jira (1)'",
          len(rows(listing, "projects/%s.md" % gone["id"])) == 4 and bool(rows(listing, "## Not returned by Jira (1)")))
    out("")
    out("THE RECORD OF THE RENAMED PROJECT, %s/projects/%s.md:" % (OUT, renamed["id"]))
    with open(os.path.join(OUT, "projects", renamed["id"] + ".md"), encoding="utf-8") as f:
        for line in f.read().rstrip("\n").split("\n"):
            out("    " + line)

    out("")
    out("=" * 78)
    out("PART 2. PAGE BOUNDARIES, at Jira's ordinary page size of 50. Each run is in a temporary folder.")
    for count, pages, why in ((49, 1, "one fewer than a page"), (50, 1, "exactly a page"),
                              (51, 2, "one more than a page: the case the quest's hint names"),
                              (100, 2, "exactly two pages"), (101, 3, "one more than two pages")):
        out("")
        out("%d projects: %s." % (count, why))
        with tempfile.TemporaryDirectory() as folder:
            fake = fake_jira.FakeJira(count=count)
            code, text = run(fake.get, folder, 50)
            held = len(os.listdir(os.path.join(folder, "projects")))
        check("%d received and %d files written, over %d page(s)" % (count, held, pages),
              code == 0 and held == count and "%d project(s) received over %d page(s)" % (count, pages) in text)

    out("")
    out("A Jira whose first page wrongly says it is the last, with 51 projects:")
    with tempfile.TemporaryDirectory() as folder:
        fake = fake_jira.FakeJira(count=51)
        fake.quirk = "says_last_early"
        code, text = run(fake.get, folder, 50)
        check("the run stopped, because 50 were received and Jira's own count was 51, and nothing was written",
              code == 1 and "Jira said there are 51 projects and 50 were received" in text and os.listdir(folder) == [])

    out("")
    out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(problems) if problems else "ALL CHECKS PASSED."))
    with open(os.path.join(ATTEMPT, "logs", "projects-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[-1])
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
