#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-list-projects quest.

Puts one bug at a time into scripts/projects.py, runs every test, notes which
tests fail, and takes the bug out again. At the end it checks that projects.py
is the same as when it started, byte for byte. No network is used.

It changes projects.py while it runs. Do not run the skill at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and projects.py was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
TARGET = os.path.join(HERE, "projects.py")

# (what the bug is, the text in projects.py to replace, what to replace it with)
BUGS = [
    ("A. Projects are matched by key, not by id",
     '        old = held.get(project["id"])',
     '        old = next((p for p in held.values() if p["key"] == project["key"]), None)'),
    ("B. Projects are matched by name, not by id",
     '        old = held.get(project["id"])',
     '        old = next((p for p in held.values() if p["name"] == project["name"]), None)'),
    ("C. Files are named by key",
     'write_text(os.path.join(folder, "projects", project["id"] + ".md"), render_record(project))',
     'write_text(os.path.join(folder, "projects", project["key"] + ".md"), render_record(project))'),
    ("D. Paging stops at the first page that is not completely full, without asking Jira's count",
     """        last = body.get("isLast")
        if last is True:
            break""",
     """        last = body.get("isLast")
        if len(values) < page_size:
            return projects, pages, None
        if last is True:
            break"""),
    ("E. Only the first page is read",
     '        if last is True:\n            break', '        if True:\n            break'),
    ("F. The count is not held against Jira's own",
     '    if total is not None and len(projects) != total:', '    if False:'),
    ("G. The next page starts one page-size on, whatever was actually returned",
     '        start += len(values)', '        start += page_size'),
    ("H. A project that disappears is deleted from the local copy",
     """        if project_id not in returned and old["state"] != "not_returned":""",
     """        if project_id not in returned:
            continue
        if False:"""),
    ("I. A rename keeps no record of the old key or name",
     '            old["history"].append({"noticed": now, "field": field, "was": before, "became": after})',
     '            pass'),
    ("J. Links in the list use the key",
     '    link = lambda p: "[`%s`](projects/%s.md)" % (p["id"], p["id"])',
     '    link = lambda p: "[`%s`](projects/%s.md)" % (p["id"], p["key"])'),
    ("K. The lookup by key is left out of the list",
     '    out += table("key", "Key", lambda v: str(v).lower(), lambda p: p["key"], "key")', '    pass'),
    ("L. The skill is given a way to send a write",
     'request = urllib.request.Request(url, method="GET")',
     'request = urllib.request.Request(url, method="GET" if not (params or {}).get("_write") else "POST")'),
    ("M. Files are written before the whole list has been read",
     """        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("values"), list):
            raise Stop""",
     """        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("values"), list):
            return projects, pages, None
        if False:
            raise Stop"""),
    ("N. The site's address is left out of the search for credentials",
     '    return get, [token, email, encoded, host]', '    return get, [token, email, encoded]'),
    ("O. A vanished project is reported again on every run",
     """if project_id not in returned and old["state"] != "not_returned":""", """if project_id not in returned:"""),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ATTEMPT,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_projects\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken projects.py? jira-list-projects, attempt jira-attempt-006",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into scripts/projects.py, every test was run, and the bug was taken out again.",
           "No network is used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            if good.count(old) != 1:
                out += ["PLANTED BUG " + title, "  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            out += ["PLANTED BUG " + title, "  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + name for name in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: projects.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and projects.py was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % (", ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
