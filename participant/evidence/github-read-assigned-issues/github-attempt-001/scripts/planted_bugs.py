#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the github-read-assigned-issues quest.

Puts one bug at a time into participant/skills/github-read-assigned/sync.py,
runs every test, notes which tests fail, and takes the bug out again. At the
end it checks that the file is the same as when it started, byte for byte.

It changes sync.py while it runs. Do not run a sync at the same time.

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
SKILL = os.path.join(ROOT, "participant", "skills", "github-read-assigned")
TARGET = os.path.join(SKILL, "sync.py")

# (what the bug is, the text to replace, what to replace it with)
BUGS = [
    ("A. The login is written into the skill instead of read from the connection (criterion 1)",
     '    return {"login": body["login"], "id": body["id"]}', '    return {"login": "robin-fixture", "id": 9001}'),
    ("B. An item that is not assigned to the signed-in user is accepted (criterion 1)",
     '        if identity["login"] not in fields["assignees"]:', '        if False:'),
    ("C. A folder holding another user's issues is synced into (criterion 1)",
     '    if (state.get("identity") or {}).get("id") != identity["id"]:', '    if False:'),
    ("D. A folder holding made-up issues may be synced from live GitHub (safety)",
     '    if state.get("source") != source:', '    if False:'),
    ("E. A restricted run does not say it is restricted (criterion 2)",
     '        if only_repos:\n            scope = ', '        if False:\n            scope = '),
    ("F. A repository that could not be read is not marked as such (criterion 2)",
     '            "unreadable": unreadable.get(repo_id),', '            "unreadable": None,'),
    ("G. Pull requests are kept as issues (criterion 3)",
     '(pulls if "pull_request" in row else issues)', '(pulls if False else issues)'),
    ("H. A pull request is told by what the key holds, not by the key (criterion 3)",
     '(pulls if "pull_request" in row else issues)', '(pulls if row.get("pull_request") else issues)'),
    ("I. Reading stops after the first page (criterion 4)",
     '        if not has_next(head):', '        if True:'),
    ("J. The next page is never asked for (criterion 4)",
     '        page += 1', '        page += 0'),
    ("K. The same page returned again is taken as the end (criterion 4)",
     '            raise Stop("GitHub kept returning the same of %s, so the skill cannot tell whether it has them all" % what)',
     '            return rows, sizes'),
    ("L. The total retrieved is not compared with the total GitHub declares (criterion 4)",
     '        if declared != len(issues):', '        if False:'),
    ("M. The search is not asked for issues only, so its total counts pull requests (criteria 3 and 4)",
     '["is:issue", "assignee:@me"]', '["assignee:@me"]'),
    ("N. A search that calls its own result incomplete is believed (criterion 4)",
     '    if body.get("incomplete_results"):', '    if False:'),
    ("O. Closed issues are not asked for (criteria 4 and 10)",
     '{"filter": "assigned", "state": "all"}', '{"filter": "assigned", "state": "open"}'),
    ("P. The state reason is not kept (criterion 5)",
     '"state_reason": row.get("state_reason"),', '"state_reason": None,'),
    ("Q. The milestone is not kept (criterion 5)",
     '    milestone = row.get("milestone") if isinstance(row.get("milestone"), dict) else None', '    milestone = None'),
    ("R. Record files are named by issue number alone, so two number 12s overwrite each other (criterion 6)",
     'os.path.join(out_dir, "issues", node + ".md"), render_record(', 'os.path.join(out_dir, "issues", str(record["number"]) + ".md"), render_record('),
    ("S. An issue whose repository was renamed loses its earlier identity (criterion 6)",
     '            record["previously"].append("%s#%d" % (old["full_name"], old["number"]))', '            pass'),
    ("T. Comments are added again at every sync (criterion 7)",
     '    return sorted(by_id.values(), key=lambda c: (c["created_at"] or "", c["id"])), added, edited, lost',
     '    return held + returned, len(returned), 0, 0'),
    ("U. Timeline entries are added again at every sync (criterion 7)",
     '    return sorted(by_key.values(), key=lambda e: (e["created_at"] or "", e["key"])), added',
     '    return held + returned, len(returned)'),
    ("V. A cross-reference, which has no id, gets a new key at every sync (criterion 7)",
     '    return "%s:%s:%s" % (row.get("event"), source.get("node_id"), row.get("created_at"))', '    return "x:%d" % id(row)'),
    ("W. Every timeline entry is kept as an event, comments included (criterion 7)",
     'if row.get("event") in MATERIAL]', 'if row.get("event")]'),
    ("X. A comment GitHub no longer returns is dropped (criterion 7)",
     '            by_id[comment_id] = dict(old, gone_since=now)     # kept, and marked. Nothing is removed locally\n            lost += 1',
     '            del by_id[comment_id]'),
    ("Y. A linked pull request is kept without its node ID (criterion 8)",
     '"ref": "%s#%d" % (there["full_name"], there["number"]), "node_id": there["node_id"],',
     '"ref": "%s#%d" % (there["full_name"], there["number"]), "node_id": "",'),
    ("Z. Commits are not kept as links (criterion 8)",
     '        elif detail.get("commit"):', '        elif False:'),
    ("AA. Reading a notes file adds a line to it (criterion 9)",
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()',
     '                    sums[name] = hashlib.sha256(f.read()).hexdigest()\n'
     '                with open(path, "a") as f:\n                    f.write("\\n")'),
    ("AB. Writing in the notes folder is no longer refused (criterion 9)",
     '    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:', '    if False:'),
    ("AC. An issue no longer assigned is deleted from the memory (criterion 10)",
     '    state.update(last_successful_sync=now, scope=scope, pulls_left_out=len(pulls))',
     '    state.update(last_successful_sync=now, scope=scope, pulls_left_out=len(pulls))\n'
     '    state["issues"] = {k: v for k, v in state["issues"].items() if v["status"] == "assigned"}'),
    ("AD. An issue no longer assigned is left out of the index (criterion 10)",
     '    gone = sorted((r for r in records if r["status"] != "assigned"), key=lambda r: (r["full_name"], r["number"]))', '    gone = []'),
    ("AE. A transferred issue is not recognised (criterion 10)",
     '    if (now["node_id"], now["number"]) != (old["node_id"], old["number"]):', '    if False:'),
    ("AF. A deleted issue is not recognised (criterion 10)",
     '    if status == 410:', '    if status == 4100:'),
    ("AG. An issue closed between syncs is not reported (criterion 10)",
     '        if old and old["state"] != fields["state"]:', '        if False:'),
    ("AH. The earlier states of an issue are thrown away (criterion 10)",
     '        history = list(old["state_history"]) if old else []', '        history = []'),
    ("AI. An issue assigned again stays flagged (criterion 10)",
     '        record.update(status="assigned", first_seen=', '        record.update(status=old["status"] if old else "assigned", first_seen='),
    ("AJ. A repository that could not be read gets a new last successful sync time (criterion 11)",
     '"last_successful_sync": old["last_successful_sync"] if repo_id in unreadable else now}', '"last_successful_sync": now}'),
    ("AK. The time an issue was first seen is replaced at every sync (criterion 11)",
     'first_seen=old["first_seen"] if old else now', 'first_seen=now'),
    ("AL. The token is put in the address (criterion 12)",
     '    url = "https://%s%s" % (API_HOST, path)',
     '    url = "https://%s%s?access_token=%s" % (API_HOST, path, os.environ.get("GITHUB_TOKEN"))'),
    ("AM. The whole answer from GitHub is kept, not the fields named (criterion 12)",
     '    return {"node_id": row["node_id"], "id": row.get("id"),', '    return {"raw": dict(row, repository_url="kept"), "node_id": row["node_id"], "id": row.get("id"),'),
    ("AN. The request is not a GET (safety)",
     'method="GET"', 'method="POST"'),
    ("AO. A redirect to a host other than GitHub's API is followed (safety)",
     '            if where.scheme != "https" or where.netloc != API_HOST or hops == MAX_REDIRECTS:', '            if hops == MAX_REDIRECTS:'),
    ("AP. An issue's body is written into its record as Markdown, not as text (safety)",
     'fenced(record["body"]), "", "### Comments', 'record["body"], "", "### Comments'),
    ("AQ. A vertical bar in a title is not escaped (safety)",
     '.replace("|", "\\\\|")', ''),
    ("AR. A closed issue that nothing points to is said to have delivery evidence (third stretch goal)",
     '    if not links:\n        return "missing"', '    if not links:\n        return "exists"'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=SKILL,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_sync\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    with open(TARGET, encoding="utf-8") as f:
        good = f.read()
    out = ["Do the tests notice a broken sync? github-read-assigned-issues, attempt github-attempt-001",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into participant/skills/github-read-assigned/sync.py, every test was run, and the",
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
    out += ["After the last bug was taken out: sync.py is %s it was at the start. %s"
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
