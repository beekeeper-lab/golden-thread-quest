#!/usr/bin/env python3
"""Checks a Jira connection, reading only, for the jira-verify-connection quest.

    verify.py check  --source live|fake --expect KEY[,KEY...]
    verify.py denied --source live|fake --project KEY

`check` shows who the connection is, which projects it can see, whether each
project it is expected to see is reachable, what it is permitted to do there,
and that one item can be read.

`denied` tries to read one project that the connection should NOT be able to
see, and reports what Jira answers.

The point of both is that a project the connection cannot reach is never
reported as an empty one. Whether a project is reachable is decided by asking
Jira for the project itself, which Jira answers with 404 when the project is
not found or the connection may not see it. It is never decided from a search
that came back with nothing.

For a live run the connection is described by three environment variables:
JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. They are never printed. Before
anything is printed, the whole output is searched for the token, the email
address and the encoded pair that is sent to Jira, and the count is reported.
The site's address is not printed either, because it names an organization.

Only GET requests are sent. There is no code here that sends any other kind.
Every request is listed at the end of the output.

Ticket text is other people's writing. The check reads one item and prints
its key and status, and the length of its summary. It does not print the
summary and acts on nothing in it.

Exit codes for `check`:
  0  every expected project is reachable and one item was read
  2  at least one expected project is INACCESSIBLE
  1  stopped before it could finish; the reason is printed
Exit codes for `denied`:
  0  the project was refused, as it should be
  3  the project is VISIBLE, and it should not be
  1  stopped before it could finish
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PERMISSIONS = ("BROWSE_PROJECTS", "CREATE_ISSUES", "EDIT_ISSUES", "DELETE_ISSUES", "ADMINISTER_PROJECTS")


class Stop(Exception):
    """The check cannot go on. The message says why."""


def make_live_get():
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Stop("the environment variable %s is not set" % name)
    if not base.startswith("https://"):
        raise Stop("JIRA_BASE_URL must start with https://")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")

    def get(path, params=None):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, method="GET")
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            try:
                body = json.loads(err.read().decode("utf-8", "replace"))
            except ValueError:
                body = {}
            return err.code, dict(err.headers), body
        except (urllib.error.URLError, OSError) as err:
            raise Stop("could not reach Jira: %s" % type(getattr(err, "reason", err)).__name__)
        except ValueError:
            raise Stop("Jira's answer to %s was not JSON" % path)

    return get, [token, email, encoded]


class Connection:
    """Every request goes through here. It can only read, and it remembers what it asked."""

    def __init__(self, get):
        self._get = get
        self.asked = []   # (path, params, status), in order

    def get(self, path, params=None):
        status, _, body = self._get(path, params or {})
        self.asked.append((path, dict(params or {}), status))
        if status == 401:
            raise Stop("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN. "
                       "A token also stops working when it expires or is revoked")
        return status, body


def first_message(body):
    messages = body.get("errorMessages") if isinstance(body, dict) else None
    return str(messages[0]) if messages else "no message"


def good_key(key):
    return key.isascii() and key.replace("_", "").isalnum() and key[:1].isalpha()


# ---------------------------------------------------------------- the questions


def who(conn, out):
    """Criterion 1: the identity is read from the connection."""
    status, body = conn.get("/rest/api/3/myself")
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("accountId"), str):
        raise Stop("Jira did not say who the connection is (status %d)" % status)
    out("1. WHO THE CONNECTION IS (read from Jira, not typed in)")
    out("   account id:    %s" % body["accountId"])
    out("   account type:  %s" % body.get("accountType", "not given"))
    out("   active:        %s" % ("yes" if body.get("active") else "NO"))
    out("   The account's name and email address were not printed.")


def visible_projects(conn, out):
    """Criterion 2: the visible projects, by stable key."""
    keys, start = [], 0
    while True:
        status, body = conn.get("/rest/api/3/project/search", {"startAt": start, "maxResults": 50, "orderBy": "key"})
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("values"), list):
            raise Stop("Jira did not return the list of projects (status %d)" % status)
        page = [str(p.get("key", "")) for p in body["values"] if isinstance(p, dict)]
        keys += page
        if body.get("isLast", True) or not page:
            break
        start += len(page)
    out("")
    out("2. PROJECTS THE CONNECTION CAN SEE (by key; names are not printed)")
    out("   %d visible: %s" % (len(keys), ", ".join(keys) or "none"))
    return keys


def project_state(conn, key):
    """Is this project reachable, and if so does it hold anything?

    Returns ("inaccessible", status, message), ("empty", None, None) or ("has_items", issue, None).
    Reachable is decided by asking for the project. Only when Jira returns the
    project is it searched, and only then can "no issues" mean "empty".
    """
    status, body = conn.get("/rest/api/3/project/%s" % key)
    if status == 404:
        return "inaccessible", status, first_message(body)
    if status != 200 or not isinstance(body, dict) or body.get("key") != key:
        raise Stop("Jira's answer about project %s could not be used (status %d)" % (key, status))
    status, body = conn.get("/rest/api/3/search/jql", {"jql": 'project = "%s" ORDER BY key ASC' % key,
                                                         "maxResults": 1, "fields": "summary,status"})
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("issues"), list):
        raise Stop("project %s is visible, but reading from it failed (status %d: %s)"
                   % (key, status, first_message(body)))
    return ("has_items", body["issues"][0], None) if body["issues"] else ("empty", None, None)


def permissions(conn, key, out):
    """What Jira says the connection may do in this project."""
    for name in PERMISSIONS:
        status, body = conn.get("/rest/api/3/mypermissions", {"projectKey": key, "permissions": name})
        entry = (body.get("permissions") or {}).get(name) if status == 200 and isinstance(body, dict) else None
        if isinstance(entry, dict) and isinstance(entry.get("havePermission"), bool):
            out("     %-20s %s" % (name, "yes" if entry["havePermission"] else "no"))
        else:
            out("     %-20s not reported (status %d)" % (name, status))


def requests_and_scan(conn, lines, secrets):
    """Criteria 5 and 6: what was sent, and whether a credential is in the output."""
    out = lines.append
    out("")
    out("REQUESTS ISSUED, in order. Every one is a GET, which reads and changes nothing.")
    for path, params, status in conn.asked:
        query = "&".join("%s=%s" % (k, v) for k, v in params.items())
        out("   GET %s%s  -> %d" % (path, "?" + query if query else "", status))
    out("   %d requests, all GET. No write operation was attempted. This check has no code that sends one."
        % len(conn.asked))
    text = "\n".join(lines)
    found = sum(text.count(secret) for secret in secrets if secret)
    out("")
    if secrets:
        out("CREDENTIAL SCAN. The output above was searched for the API token, the account's email address")
        out("   and the encoded pair that is sent to Jira: %d found." % found)
    else:
        out("CREDENTIAL SCAN. This run used the fake, which has no credential. Nothing to search for.")
    return found


# ---------------------------------------------------------------- the two commands


def check(conn, expect, secrets):
    lines = []
    out = lines.append
    out("JIRA CONNECTION CHECK. Reading only.")
    out("")
    who(conn, out)
    visible = visible_projects(conn, out)

    out("")
    out("3. PROJECTS THE CONNECTION IS EXPECTED TO SEE: %s" % ", ".join(expect))
    lost, read = [], None
    for key in expect:
        state, detail, message = project_state(conn, key)
        if state == "inaccessible":
            lost.append(key)
            out("   %s: INACCESSIBLE. Jira answered %d (%s)." % (key, detail, message))
            out("     It does not exist, or this connection is not permitted to see it. Jira gives one answer")
            out("     for both. This is NOT an empty project. Nothing was read from it.")
            continue
        listed = "listed in section 2" if key in visible else "NOT listed in section 2, though Jira returned it"
        if state == "empty":
            out("   %s: VISIBLE AND EMPTY. Jira returned the project (%s), and it holds no issues." % (key, listed))
        else:
            out("   %s: VISIBLE, WITH ISSUES. Jira returned the project (%s)." % (key, listed))
            read = read or (key, detail)
        out("     permissions Jira reports for this connection in %s:" % key)
        permissions(conn, key, out)

    out("")
    out("4. ONE SAFE READ")
    if read:
        key, issue = read
        fields = issue.get("fields") or {}
        out("   Read one item from %s: %s, status '%s', summary of %d characters (not printed)."
            % (key, issue.get("key"), (fields.get("status") or {}).get("name", "not given"),
               len(str(fields.get("summary", "")))))
        out("   The read succeeded.")
    else:
        out("   NO ITEM WAS READ. None of the expected projects is both visible and holding an issue.")

    found = requests_and_scan(conn, lines, secrets)
    out("")
    if found:
        return ["RESULT: STOPPED. A credential was found in the output, so the output was not printed."], 1
    if lost:
        out("RESULT: ACCESS PROBLEM. %d of %d expected project(s) INACCESSIBLE: %s."
            % (len(lost), len(expect), ", ".join(lost)))
        return lines, 2
    if not read:
        out("RESULT: INCOMPLETE. Every expected project is visible, but no item could be read.")
        return lines, 2
    out("RESULT: OK. All %d expected project(s) visible, and one item was read." % len(expect))
    return lines, 0


def denied(conn, key, secrets):
    lines = []
    out = lines.append
    out("JIRA CONNECTION CHECK: A PROJECT THAT SHOULD NOT BE VISIBLE. Reading only.")
    out("")
    who(conn, out)
    visible = visible_projects(conn, out)
    out("")
    out("3. THE PROJECT THAT SHOULD NOT BE VISIBLE: %s" % key)
    out("   In the list of visible projects above: %s" % ("YES" if key in visible else "no"))
    status, body = conn.get("/rest/api/3/project/%s" % key)
    refused = status == 404
    if refused:
        out("   Asked Jira for the project itself: REFUSED. Jira answered 404 (%s)." % first_message(body))
    elif status == 200:
        out("   Asked Jira for the project itself: Jira RETURNED it (200).")
    else:
        raise Stop("Jira's answer about project %s could not be used (status %d)" % (key, status))
    status, body = conn.get("/rest/api/3/mypermissions", {"projectKey": key, "permissions": "BROWSE_PROJECTS"})
    out("   Asked what the connection may do there: Jira answered %d%s."
        % (status, " (%s)" % first_message(body) if status != 200 else ""))
    status, body = conn.get("/rest/api/3/search/jql", {"jql": 'project = "%s" ORDER BY key ASC' % key,
                                                         "maxResults": 1, "fields": "summary,status"})
    if status == 200 and isinstance(body, dict) and isinstance(body.get("issues"), list):
        count = len(body["issues"])
        out("   For comparison, a search of the same project: Jira answered 200 with %d issue(s)." % count)
        if refused and not count:
            out("     Taken alone, that search is the answer an EMPTY project gives. This is why the check")
            out("     does not decide from a search.")
    else:
        out("   For comparison, a search of the same project: Jira answered %d (%s)." % (status, first_message(body)))

    out("")
    out("4. WHAT THIS MEANS")
    if refused:
        out("   %s is INACCESSIBLE to this connection. It does not exist, or the connection is not permitted" % key)
        out("   to see it. Jira gives the same answer for both, so the check cannot say which.")
        out("   It is reported as INACCESSIBLE. It is not reported as empty. Nothing was read from it.")
    else:
        out("   %s is VISIBLE to this connection, and it was expected not to be." % key)
    found = requests_and_scan(conn, lines, secrets)
    out("")
    if found:
        return ["RESULT: STOPPED. A credential was found in the output, so the output was not printed."], 1
    if refused:
        out("RESULT: REFUSED, AS IT SHOULD BE. %s is inaccessible to this connection." % key)
        return lines, 0
    out("RESULT: NOT AS INTENDED. %s is visible, and this connection was not meant to see it." % key)
    return lines, 3


def main():
    parser = argparse.ArgumentParser(description="Check a Jira connection. Reads only.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "denied"):
        sub = commands.add_parser(name)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--fake-search", choices=("error", "empty"), default="error",
                         help="with --source fake: what a search of a hidden project answers")
    commands.choices["check"].add_argument("--expect", required=True, help="project keys it should see, comma-separated")
    commands.choices["denied"].add_argument("--project", required=True, help="a project key it should not see")
    args = parser.parse_args()
    try:
        keys = [k.strip() for k in (args.expect if args.command == "check" else args.project).split(",") if k.strip()]
        if not keys or not all(good_key(k) for k in keys):
            raise Stop("a project key is letters, digits and underscores, starting with a letter")
        if args.source == "fake":
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import fake_jira
            get, secrets = fake_jira.FakeJira(search_hidden=args.fake_search).get, []
        else:
            get, secrets = make_live_get()
        conn = Connection(get)
        lines, code = check(conn, keys, secrets) if args.command == "check" else denied(conn, keys[0], secrets)
    except Stop as stop:
        lines, code = ["STOPPED: %s." % stop, "Nothing was changed. This check only reads."], 1
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
