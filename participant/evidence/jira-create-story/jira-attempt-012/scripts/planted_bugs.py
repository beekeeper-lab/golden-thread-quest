#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-create-story quest.

Puts one bug at a time into participant/skills/jira-create-story/create.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes create.py while it runs. Do not run the workflow at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and the file was restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = os.path.join(ROOT, "participant", "skills", "jira-create-story")
TARGET = os.path.join(SKILL, "create.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The bytes sent are not the bytes that were previewed (criterion 1)",
     '        status, _, body = conn.create(found["body"])', '        status, _, body = conn.create(pv.body_bytes({"fields": dict(found["payload"]["fields"], summary="Something else")}))'),
    ("B. The read-back comparison passes whatever came back (criterion 1)",
     '        good = good and same', '        good = True'),
    ("C. Labels are not compared in the read-back (criterion 1)",
     '            same = isinstance(b, list) and sorted(b) == sorted(a)', '            same = True'),
    ("D. The key that came back is not written to the link file (criterion 2)",
     'jira_id=body["id"], jira_key=body["key"]', 'jira_id=body["id"], jira_key=None'),
    ("E. The link is matched to Jira by its key where it should be by its id (criterion 3)",
     '    story = read_story(conn, front["jira_id"])\n    if story is None:\n        raise Refused("Jira answered 404', '    story = read_story(conn, front["jira_key"])\n    if story is None:\n        raise Refused("Jira answered 404'),
    ("F. A key changed in Jira is not recorded locally (criterion 3)",
     '    if story["key"] != front["jira_key"]:\n        front["earlier_keys"]', '    if False:\n        front["earlier_keys"]'),
    ("G. A preview is able to send a create (criterion 4)",
     '        if self._post is None:', '        if False:'),
    ("H. The marker is left out of the payload, so a lost create cannot be found again (criteria 5 and 9)",
     '    marked = dict(draft, labels=(draft["labels"] or []) + [marker])', '    marked = dict(draft)'),
    ("I. The allowlist is not applied (criterion 6)",
     '    if (site, project["id"]) not in allowed:', '    if False:'),
    ("J. A confirmation with no name is accepted (criterion 7)",
     '    if not name:\n        raise Refused("no confirmation', '    if False:\n        raise Refused("no confirmation'),
    ("K. A draft changed after the preview is created anyway (criterion 7)",
     '    if found["digest"] != record["payload_sha256"] or sha_of(found["draft"]["path"]) != record["draft_sha256"]:', '    if False:'),
    ("L. An edit to the draft file that leaves the payload the same goes unnoticed (criterion 7)",
     ' or sha_of(found["draft"]["path"]) != record["draft_sha256"]:', ':'),
    ("M. A preview never expires (criterion 7)",
     '    if age > datetime.timedelta(minutes=LIMIT_MINUTES):', '    if False:'),
    ("N. An altered saved preview is accepted (criterion 7)",
     '    if genuine != record.get("fingerprint") or genuine[:12] != code or not MARKER.fullmatch(str(record.get("marker"))):', '    if False:'),
    ("O. A draft that is already linked can be created again: the quest's scenario (criterion 9)",
     '    if front is None:\n        return\n    if front.get("draft")', '    if True:\n        return\n    if front.get("draft")'),
    ("P. The link file is not written before the create is sent, so a lost answer leaves no trace (criterion 9)",
     '    write_link(args.link, front, found["draft"], found["payload"])\n    record["state"] = "sending"', '    record["state"] = "sending"'),
    ("Q. A create that gets no answer is sent a second time (criterion 9)",
     '        except (OSError, TimeoutError) as err:\n            raise NeedsLooking("the create was sent and no answer',
     '        except (OSError, TimeoutError) as err:\n            return self._post("/rest/api/3/issue", None, body)\n            raise NeedsLooking("the create was sent and no answer'),
    ("R. A story already carrying the marker does not stop the create (criterion 9)",
     '    if already:', '    if False:'),
    ("S. A refusal from Jira is believed without looking for the marker (criterion 9)",
     '        if status in (400, 401, 403, 404, 422) and not marker_search(conn, project, record["marker"]):', '        if status in (400, 401, 403, 404, 422):'),
    ("T. A server error is treated as a plain refusal and the link is removed (criterion 9)",
     '        if status in (400, 401, 403, 404, 422) and', '        if status in (400, 401, 403, 404, 422, 500) and'),
    ("U. Reconcile links the first story when two carry the marker (criterion 9)",
     '    if len(found) > 1:', '    if False:'),
    ("V. One run can send more than one create (criterion 9)",
     '        if any(method == "POST" for method, _ in self.sent):\n            raise Refused("a create has already been sent', '        if False:\n            raise Refused("a create has already been sent'),
    ("Z. Verify reports that the marker leads to the story without having asked Jira (criterion 9)",
     '    if marked == [front["jira_id"]]:', '    if True:'),
    ("W. A person's name from Jira is shown in the comparison (safety rule: redacted records)",
     '        if "accountId" in value:\n            return "a person, not shown"', '        if "accountId" in value:\n            return str(value.get("displayName"))'),
    ("X. The saved log keeps the site's address (safety rule: redacted records)",
     '        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text', '        saved = text'),
    ("Y. Output is not searched for credentials (safety rule: no credential in a log)",
     '    if any(secret and secret in text for secret in secrets_found):', '    if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_create\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken create workflow? jira-create-story, attempt jira-attempt-012",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-create-story/create.py, every test was run, and the",
           "bug was taken out again. Only local files are used.", ""]
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
    out += ["After the last bug was taken out: create.py is %s it was at the start. %s"
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
