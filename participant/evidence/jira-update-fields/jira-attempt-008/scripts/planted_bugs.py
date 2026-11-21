#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-update-fields quest.

Puts one bug at a time into scripts/update.py, runs every test, notes which
tests fail, and takes the bug out again. At the end it checks that the file
is the same as when it started, byte for byte. No network is used.

It changes update.py while it runs. Do not run the updater at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
TARGET = os.path.join(HERE, "update.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A field outside the supported list is let through (criterion 2)",
     '    for name in fields:\n        if name not in SUPPORTED:', '    for name in fields:\n        if False:'),
    ("B. A label of any shape is accepted (criterion 2)",
     '            if not LABEL.fullmatch(label):', '            if False:'),
    ("C. A due date is not checked to be a real date (criterion 2)",
     '            year = datetime.date.fromisoformat(date).year', '            year = int(date[:4])'),
    ("D. Any priority name is accepted, and the first one Jira offers is used (criterion 2)",
     '            matches = [value for value in offered if value["name"] == new]', '            matches = offered[:1]'),
    ("E. Jira's list of editable fields is ignored (criteria 2 and 5)",
     '        if name not in editmeta:', '        if False:'),
    ("F. A field changed in Jira after the preview no longer stops the update (criterion 3)",
     '    if moved:\n        raise Refused("a field changed', '    if False:\n        raise Refused("a field changed'),
    ("G. The story changing while the preview is made goes unnoticed (criterion 4)",
     '    if after != before:', '    if False:'),
    ("H. A preview is able to send a write (criterion 4)",
     '        if self._put is None:', '        if False:'),
    ("I. The permission check's answer is ignored (criterion 5)",
     '    if not permissions["BROWSE_PROJECTS"] or not permissions["EDIT_ISSUES"]:', '    if False:'),
    ("J. The allowlist is not applied (criterion 6)",
     '    if (site, project["id"]) not in allowed:', '    if False:'),
    ("K. The allowlist forgets which Jira site a project id belongs to (criterion 6)",
     '    if (site, project["id"]) not in allowed:', '    if project["id"] not in set(p for _, p in allowed):'),
    ("L. A confirmation with no name is accepted (criterion 7)",
     '    if not name:\n        raise Refused("no confirmation', '    if False:\n        raise Refused("no confirmation'),
    ("M. A change that differs from the preview is written (criterion 7)",
     '    if differs:\n', '    if False:\n'),
    ("N. A preview never expires (criterion 7)",
     '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):', '    if False:'),
    ("O. An altered saved preview is accepted (criterion 7)",
     '    if genuine != record.get("fingerprint") or genuine[:12] != code:', '    if False:'),
    ("P. The test clock can be moved backwards, to make an old preview look new (criterion 7)",
     '    if not text.isascii() or not text.isdigit() or len(text) > 6:', '    if False:'),
    ("Q. A fingerprint that has been written can be used again (criterion 9)",
     '    if status == "written":', '    if False:'),
    ("R. A preview whose write was sent and went wrong can be sent again (criterion 9)",
     '    if status != "open":', '    if False:'),
    ("S. A field that already holds the wanted value is sent anyway (criterion 9)",
     '"send": now[name] != new}', '"send": True}'),
    ("T. A write that gets no answer is sent a second time (criterion 9)",
     '        except (OSError, TimeoutError) as err:\n            raise NeedsLooking("the write was sent and no answer',
     '        except (OSError, TimeoutError) as err:\n            return self._put(path, None, {"fields": fields})\n            raise NeedsLooking("the write was sent and no answer'),
    ("U. The read-back after the write is not compared with what was proposed (criterion 8)",
     '    as_proposed = all(after[field] == proposal["changes"][field]["new"] for field in sending)', '    as_proposed = True'),
    ("V. Any new history entry is claimed as this write's, whoever made it (criterion 8)",
     ' and (entry.get("author") or {}).get("accountId") == me:', ':'),
    ("W. A change overwritten in the last moment is not reported (criterion 3)",
     '                    if not history_agrees(field, before["changes"][field]["old"], item):', '                    if False:'),
    ("X. The story's summary is printed in the preview (safety rule: story text is untrusted)",
     '    issue = read_issue(conn, ref)\n    check_allowlist(site, allowed, issue, args.allowlist)',
     '    issue = read_issue(conn, ref)\n    say("Summary: %s" % issue["fields"].get("summary"))\n    check_allowlist(site, allowed, issue, args.allowlist)'),
    ("Y. The saved log keeps the site's address (safety rule: redacted records)",
     '        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text', '        saved = text'),
    ("Z. Output is not searched for credentials (safety rule: no credential in a log)",
     '    if any(secret and secret in text for secret in secrets):', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ATTEMPT,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_update\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken updater? jira-update-fields, attempt jira-attempt-008",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into scripts/update.py, every test was run, and the bug was taken out again.",
           "No network is used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, old, new in BUGS:
            out += ["PLANTED BUG %s" % title]
            if good.count(old) != 1:
                out += ["  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new))
            last, failed = run_tests()
            with open(TARGET, "w", encoding="utf-8") as f:
                f.write(good)
            out += ["  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(good)
    with open(TARGET, encoding="utf-8") as f:
        restored = f.read() == good
    last, failed = run_tests()
    out += ["After the last bug was taken out: update.py is %s it was at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and the file was restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
