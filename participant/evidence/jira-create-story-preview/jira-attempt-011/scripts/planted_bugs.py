#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-create-story-preview quest.

Puts one bug at a time into participant/skills/jira-create-story-preview/preview.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes preview.py while it runs. Do not run a preview at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "jira-create-story-preview")
TARGET = os.path.join(SKILL, "preview.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. A missing required field is let through, to be filled by whatever Jira does (criterion 2)",
     '    if missing:\n        raise Refused("the draft is missing', '    if False:\n        raise Refused("the draft is missing'),
    ("B. Only the first missing required field is named (criterion 2)",
     'project["key"], ", ".join(missing), "it" if len(missing) == 1 else "them"))', 'project["key"], missing[0], "it" if len(missing) == 1 else "them"))'),
    ("C. A required field with a default is not shown as left to Jira (criterion 1)",
     '            left.append((field_id, field["name"], default_text(field)))', '            pass'),
    ("D. Optional fields that are not sent are left out of the list of every field (criterion 1)",
     '            unset.append((field_id, field["name"], default_text(field) if field.get("hasDefaultValue") is True else "no default reported"))', '            pass'),
    ("E. Only the first page of the field list is read, so later required fields are never checked (criteria 1 and 2)",
     '        if not page or (isinstance(body.get("total"), int) and start >= body["total"]):', '        if True:'),
    ("F. The payload shown is not the payload saved: the saved one gains a field (criterion 5)",
     '"issuetype": kind, "payload": payload, "payload_sha256": digest,', '"issuetype": kind, "payload": {"fields": dict(payload["fields"], priority={"id": "1"})}, "payload_sha256": digest,'),
    ("G. The SHA-256 is taken of something other than the bytes that would be sent (criterion 5)",
     '    digest = hashlib.sha256(body).hexdigest()', '    digest = hashlib.sha256(pretty(payload).encode("utf-8")).hexdigest()'),
    ("H. The payload is built a second time for the payload file, so the two could differ (criterion 5)",
     '        write_payload_file(args.payload_out, conn, site, project, kind, draft, rows, left, unset, payload, body, digest, sources)',
     '        write_payload_file(args.payload_out, conn, site, project, kind, draft, rows, left, unset, build_payload(draft, project, kind, meta, parent_id)[0], body, digest, sources)'),
    ("I. A component is sent by name where Jira's example takes an id (criterion 5)",
     '        put("components", [{"id": cid} for cid in ids],', '        put("components", [{"name": name} for name in draft["components"]],'),
    ("J. A value Jira does not allow is sent anyway (criterion 2 and the schema stretch goal)",
     '    if len(matches) != 1:\n        raise Refused("%s %s is not one of the values Jira allows', '    if False:\n        raise Refused("%s %s is not one of the values Jira allows'),
    ("K. The duplicate search is skipped and reported as none (criterion 3)",
     '        result = search.search(proposal, catalog, today)', '        result = {"searched": 0, "candidates": [], "dismissed": [], "overall": "proceed", "today": today}'),
    ("L. A stale catalog is searched without a word (criterion 3)",
     '    except search.Stop as stop:\n        raise Refused("the duplicate search could not run, so no preview is made: %s" % stop)',
     '    except search.Stop as stop:\n        return proposal, {"searched": 0, "candidates": [], "dismissed": [], "overall": "proceed", "today": today}, []'),
    ("M. The permission check's answer is ignored (criterion 4)",
     '    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:', '    if False:'),
    ("N. The allowlist is not applied (safety: sandbox only)",
     '    if (site, project["id"]) not in allowed:', '    if False:'),
    ("O. The snapshot after the preview is not compared with the one before (criterion 6)",
     '    if after != before:', '    if False:'),
    ("P. The preview is given a request that is not a GET (criterion 6)",
     '        request = urllib.request.Request(url, method="GET")', '        request = urllib.request.Request(url, method="GET" if not params or "_w" not in params else "POST")'),
    ("Q. Content with no citation is accepted (criterion 7)",
     '    if missing:\n        raise Refused("the draft gives no source for', '    if False:\n        raise Refused("the draft gives no source for'),
    ("R. A citation is not checked against the file it names (criterion 7)",
     '        if " ".join(source["quote"].split()) not in there:', '        if False:'),
    ("S. A citation may point at any file on the machine (criterion 7 and safety)",
     '        if os.path.commonpath([path, os.path.realpath(CONTEXT)]) != os.path.realpath(CONTEXT):', '        if False:'),
    ("T. A refused preview still writes a payload file (criterion 2)",
     '    payload, rows, left, unset = build_payload(draft, project, kind, meta, parent_id)',
     '    if args.payload_out:\n        open(args.payload_out, "w").write("payload")\n    payload, rows, left, unset = build_payload(draft, project, kind, meta, parent_id)'),
    ("U. The saved log keeps the site's address (safety: redacted records)",
     '        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text', '        saved = text'),
    ("V. Output is not searched for credentials (safety: no credential in a log)",
     '    if any(secret and secret in text for secret in secrets):', '    if False:'),
    ("W. A parent in another project is accepted (schema stretch goal)",
     '    if (fields.get("project") or {}).get("id") != project["id"]:', '    if False:'),
    ("Y. Stories in Jira that the local catalog lacks are not warned about (criterion 3)",
     '    if local < in_jira:', '    if False:'),
    ("X. A draft field the preview does not support is ignored without a word (criterion 1)",
     '        if name not in DRAFT_NAMES:', '        if False:'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_preview\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken preview? jira-create-story-preview, attempt jira-attempt-011",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/jira-create-story-preview/preview.py, every test was run, and the",
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
    out += ["After the last bug was taken out: preview.py is %s it was at the start. %s"
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
