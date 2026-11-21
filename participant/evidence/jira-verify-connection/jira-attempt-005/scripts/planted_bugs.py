#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-verify-connection quest.

Puts one bug at a time into scripts/verify.py, runs every test, notes which
tests fail, and takes the bug out again. At the end it checks that verify.py
is the same as when it started, byte for byte. No network is used.

It changes verify.py while it runs. Do not run the check at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and verify.py was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
TARGET = os.path.join(HERE, "verify.py")

# (what the bug is, the text in verify.py to replace, what to replace it with)
BUGS = [
    ("A. A project Jira refuses is reported as empty",
     '        return "inaccessible", status, first_message(body)', '        return "empty", None, None'),
    ("B. The identity is typed in, not read from the connection",
     'out("   account id:    %s" % body["accountId"])', 'out("   account id:    %s" % "5b10a0000000000000000001")'),
    ("C. Projects are listed by name, not by key",
     'page = [str(p.get("key", "")) for p in body["values"] if isinstance(p, dict)]',
     'page = [str(p.get("name", "")) for p in body["values"] if isinstance(p, dict)]'),
    ("D. The text of the item read is printed",
     'out("   The read succeeded.")', 'out("   The read succeeded: %s" % fields.get("summary"))'),
    ("E. Only the first page of projects is listed",
     'if body.get("isLast", True) or not page:', 'if True:'),
    ("F. The output is not searched for the credential",
     'found = sum(text.count(secret) for secret in secrets if secret)', 'found = 0'),
    ("G. The check is given a way to send a write",
     'request = urllib.request.Request(url, method="GET")',
     'request = urllib.request.Request(url, method="GET" if not (params or {}).get("_write") else "POST")'),
    ("H. A lost project does not change the exit code",
     '% (len(lost), len(expect), ", ".join(lost)))\n        return lines, 2',
     '% (len(lost), len(expect), ", ".join(lost)))\n        return lines, 0'),
    ("I. The denied run calls a visible project refused",
     '    refused = status == 404\n', '    refused = True\n'),
    ("J. Requests that Jira refused are left out of the list of requests",
     '        self.asked.append((path, dict(params or {}), status))',
     '        if status == 200:\n            self.asked.append((path, dict(params or {}), status))'),
    ("K. Reading nothing at all is reported as OK",
     '        out("RESULT: INCOMPLETE. Every expected project is visible, but no item could be read.")\n        return lines, 2',
     '        out("RESULT: OK. Every expected project is visible.")\n        return lines, 0'),
    ("L. Rejected credentials do not stop the check",
     '        if status == 401:', '        if status == 999:'),
    ("M. An inaccessible project is searched anyway, and the search decides",
     '    if status == 404:\n        return "inaccessible", status, first_message(body)\n    if status != 200 or not isinstance(body, dict) or body.get("key") != key:\n        raise Stop',
     '    if False:\n        raise Stop'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ATTEMPT,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_verify\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken verify.py? jira-verify-connection, attempt jira-attempt-005",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into scripts/verify.py, every test was run, and the bug was taken out again.",
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
    out += ["After the last bug was taken out: verify.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and verify.py was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % (", ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
