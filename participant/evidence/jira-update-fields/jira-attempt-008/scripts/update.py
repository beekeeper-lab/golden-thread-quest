#!/usr/bin/env python3
"""Changes labels, due date or priority on one Jira story: preview first, then a person confirms.

    update.py preview --source live|fake --change CHANGE.json --allowlist FILE --state DIR
    update.py confirm --source live|fake --change CHANGE.json --allowlist FILE --state DIR \
                      --fingerprint CODE --confirmed-by NAME

A change file names one story and the values wanted:

    {"story": "SAND-1",
     "fields": {"labels": ["onboarding", "q4"], "duedate": "2026-12-15", "priority": "High"}}

Supported fields, and nothing else:

    labels     the whole list wanted: up to 10, each of lowercase letters,
               digits and hyphens, starting with a letter or digit, at most 50 long.
    duedate    a date, YYYY-MM-DD. Clearing a due date is not supported.
    priority   the name of one of the priorities Jira offers for that story.

Any other field is refused. There is no option that widens the list.

preview   reads the story and writes nothing. It has no way to send a write.
          It shows the Jira site, the project, the story, the value each field
          holds now and the value it would hold after, the permission check and
          the duplicate check, and a fingerprint. It saves that preview in the
          state folder. A field that already holds the wanted value is not
          sent. If no field would change, no fingerprint is issued.

confirm   writes the changes of one preview, named by its fingerprint, and
          only if all of this holds at that moment:
            a fingerprint and the confirming person's name are given;
            the saved preview is unaltered, unused and at most 15 minutes old;
            the change file still asks for exactly what the preview showed;
            the project is on the sandbox allowlist, for this Jira site;
            Jira still says this identity may edit the story and the fields;
            each field still holds in Jira the value the preview saw.
          The story is read again last of all, just before the write. After
          the write it is read back, and Jira's history is read to find the
          entry the write made.

The allowlist is a JSON file listing projects by Jira's project id together
with a fingerprint of the site's address, because project ids repeat from
site to site.

What this cannot do: Jira's documented edit request has no "only if the value
is still X" condition. Between the last read and the write there is a moment
in which someone else's change would be overwritten. Afterwards the history
entry is compared with what the preview saw, so that case is reported.

A write is sent once and never retried.

--pretend-minutes-later N is for tests: it moves "now" forward by N minutes.
--log FILE saves the output with the site's address replaced by a marker.
--result FILE saves the result record of a write as Markdown, the same way.

The story's own text is never printed and nothing in it is acted on. Labels
and priority names from Jira are shown quoted, as values.

For a live run the connection comes from the environment variables
JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None is stored. The output is
searched for the token, the email address and their encoded form before it is
shown. The site's address is shown on screen, so that the person confirming
can see where the write would go, and is removed from anything saved.

Exit codes: 0 done; 1 refused, nothing written; 2 a write was sent and its
result needs a person to look.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SUPPORTED = ("labels", "duedate", "priority")
LIMIT_MINUTES = 15
MAX_LABELS = 10
LABEL = re.compile(r"[a-z0-9][a-z0-9-]{0,49}")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,60}")
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
MAX_HISTORY_PAGES = 50

LINES = []


class Refused(Exception):
    """Nothing was written. The message is the reason."""


class NeedsLooking(Exception):
    """A write was sent. The message says what is and is not known."""


def say(text=""):
    LINES.append(text)


# ---------------------------------------------------------------- the connection


class Connection:
    """Every request goes through here and is written down. A preview is given no way to write."""

    def __init__(self, get, put, host):
        self._get, self._put, self.host = get, put, host
        self.sent = []

    def get(self, path, params=None):
        self.sent.append(("GET", path))
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            reason = "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__
            if any(method == "PUT" for method, _ in self.sent):
                raise NeedsLooking("after the write was sent, a read failed: %s" % reason)
            raise Refused(reason)

    def put_issue(self, issue_id, fields):
        if self._put is None:
            raise Refused("this command has no way to write")
        if not (isinstance(issue_id, str) and issue_id.isascii() and issue_id.isdigit()):
            raise Refused("a write names the story by its issue id")
        if not fields or any(name not in SUPPORTED for name in fields):
            raise Refused("a write holds supported fields only")
        path = "/rest/api/3/issue/%s" % issue_id
        self.sent.append(("PUT", path))
        try:
            return self._put(path, None, {"fields": fields})
        except (OSError, TimeoutError) as err:
            raise NeedsLooking("the write was sent and no answer came back (%s). It is NOT KNOWN whether Jira "
                               "made the change. It was not sent again" % type(getattr(err, "reason", err)).__name__)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live(may_write):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    if not base.startswith("https://"):
        raise Refused("JIRA_BASE_URL must start with https://")
    host = urllib.parse.urlparse(base).hostname or ""
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = urllib.request.build_opener(NoRedirect)

    def send(method, path, params, body):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
                status, headers, raw = response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as err:
            status, headers, raw = err.code, dict(err.headers), err.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except ValueError:
            parsed = {}
        return status, headers, parsed if isinstance(parsed, dict) else {}

    def get(path, params=None):
        return send("GET", path, params, None)

    def put(path, params, body):
        if not re.fullmatch(r"/rest/api/3/issue/\d{1,20}", path):
            raise Refused("the only write this workflow sends is an edit of one story")
        return send("PUT", path, params, body)

    return Connection(get, put if may_write else None, host), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------- reading the local files


def no_repeats(pairs):
    names = [name for name, _ in pairs]
    for name in names:
        if names.count(name) > 1:
            raise Refused("the file gives the name %s twice in one place" % json.dumps(name)[:60])
    return dict(pairs)


def read_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, object_pairs_hook=no_repeats)
    except FileNotFoundError:
        raise Refused("there is no %s at the path given" % what)
    except ValueError:
        raise Refused("the %s is not JSON" % what)


def load_allowlist(path):
    data = read_json(path, "sandbox allowlist")
    entries = data.get("sandbox_projects") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise Refused("the sandbox allowlist must hold a list named sandbox_projects")
    allowed = set()
    for entry in entries:
        site, project = (entry or {}).get("site_fingerprint"), (entry or {}).get("project_id")
        if not (isinstance(site, str) and re.fullmatch(r"[0-9a-f]{16}", site)
                and isinstance(project, str) and project.isascii() and project.isdigit()):
            raise Refused("an entry in the sandbox allowlist is not a site fingerprint and a project id")
        allowed.add((site, project))
    return allowed


def read_change(path):
    """The story and the values wanted, checked. Returns (story, {field: value})."""
    change = read_json(path, "change file")
    if not isinstance(change, dict) or set(change) != {"story", "fields"}:
        raise Refused("the change file must have exactly 'story' and 'fields'")
    ref, fields = change["story"], change["fields"]
    if not isinstance(ref, str) or not REF.fullmatch(ref):
        raise Refused("the story is given by its id or its key: letters, digits and dashes only")
    if not isinstance(fields, dict) or not fields:
        raise Refused("the change file names no fields to change")
    for name in fields:
        if name not in SUPPORTED:
            raise Refused("the field %s is not supported. This workflow changes only %s, and refuses every "
                          "other field" % (json.dumps(str(name)[:40]), ", ".join(SUPPORTED)))
    wanted = {}
    if "labels" in fields:
        labels = fields["labels"]
        if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
            raise Refused("labels must be a list of labels")
        if len(labels) > MAX_LABELS:
            raise Refused("labels: at most %d labels are allowed" % MAX_LABELS)
        if len(set(labels)) != len(labels):
            raise Refused("labels: a label is given twice")
        for label in labels:
            if not LABEL.fullmatch(label):
                raise Refused("labels: %s is not allowed. A label is lowercase letters, digits and hyphens, "
                              "at most 50 long" % json.dumps(label[:60]))
        wanted["labels"] = sorted(labels)
    if "duedate" in fields:
        date = fields["duedate"]
        if date is None or date == "":
            raise Refused("duedate: clearing a due date is not supported. Jira's documentation does not say how")
        if not isinstance(date, str) or not DATE.fullmatch(date):
            raise Refused("duedate must be a date written YYYY-MM-DD")
        try:
            year = datetime.date.fromisoformat(date).year
        except ValueError:
            raise Refused("duedate is not a real date")
        if not 2000 <= year <= 2100:
            raise Refused("duedate must be between the years 2000 and 2100")
        wanted["duedate"] = date
    if "priority" in fields:
        name = fields["priority"]
        if not isinstance(name, str) or not name.strip() or len(name) > 60:
            raise Refused("priority must be the name of a priority")
        wanted["priority"] = name
    return ref, wanted


# ---------------------------------------------------------------- reading Jira


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def read_issue(conn, ref):
    status, _, issue = conn.get("/rest/api/3/issue/%s" % ref)
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the story. It does not exist, or this identity is not permitted "
                      "to see it. Jira gives one answer for both")
    fields = issue.get("fields") if isinstance(issue, dict) else None
    project = fields.get("project") if isinstance(fields, dict) else None
    ok = (status == 200 and isinstance(project, dict) and ident(issue.get("id")) and ident(project.get("id"))
          and isinstance(issue.get("key"), str) and REF.fullmatch(issue["key"])
          and isinstance(project.get("key"), str) and REF.fullmatch(project["key"]))
    if not ok:
        raise Refused("Jira's answer for the story could not be used (status %d)" % status)
    return issue


def current_values(issue):
    """What the three supported fields hold, in the form this workflow compares."""
    fields = issue["fields"]
    labels, date, priority = fields.get("labels") or [], fields.get("duedate"), fields.get("priority")
    if not isinstance(labels, list) or not all(isinstance(label, str) for label in labels):
        raise Refused("Jira's labels for the story are not a list of text")
    if date is not None and not (isinstance(date, str) and DATE.fullmatch(date)):
        raise Refused("Jira's due date for the story is not a date")
    if priority is not None and not (isinstance(priority, dict) and ident(priority.get("id"))
                                     and isinstance(priority.get("name"), str)):
        raise Refused("Jira's priority for the story could not be read")
    return {"labels": sorted(labels), "duedate": date,
            "priority": None if priority is None else {"id": priority["id"], "name": priority["name"]}}


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def snapshot(issue):
    """One short code for everything Jira returned about the story."""
    text = canonical({"id": issue["id"], "key": issue["key"], "fields": issue["fields"]})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read_myself(conn):
    status, _, body = conn.get("/rest/api/3/myself")
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status != 200 or not isinstance(body.get("accountId"), str):
        raise Refused("Jira did not say which identity this is (status %d)" % status)
    return body["accountId"]


def read_permissions(conn, issue_id):
    names = ("BROWSE_PROJECTS", "EDIT_ISSUES")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"issueId": issue_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


def read_editmeta(conn, issue_id):
    status, _, body = conn.get("/rest/api/3/issue/%s/editmeta" % issue_id)
    if status != 200 or not isinstance(body.get("fields"), dict):
        raise Refused("Jira did not say which fields can be edited (status %d), so nothing is assumed" % status)
    return body["fields"]


def read_history(conn, issue_id):
    """Every changelog entry, oldest first, or None if the history could not be read whole."""
    entries, start = [], 0
    for _ in range(MAX_HISTORY_PAGES):
        status, _, body = conn.get("/rest/api/3/issue/%s/changelog" % issue_id, {"startAt": start, "maxResults": 100})
        values = body.get("values") if status == 200 else None
        if not isinstance(values, list):
            return None
        entries += [entry for entry in values if isinstance(entry, dict)]
        start += len(values)
        if body.get("isLast") is True or not values:
            return entries
    return None


# ---------------------------------------------------------------- what the change is


def check_allowlist(site, allowed, issue, allowlist_path):
    project = issue["fields"]["project"]
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox "
                      "allowlist (%s). This workflow writes only to projects listed there"
                      % (project["key"], project["id"], site, allowlist_path))


def build_proposal(site, allowed, allowlist_path, issue, permissions, editmeta, ref, wanted):
    """The one place that decides what a change means. The preview shows its result; confirm compares with it."""
    check_allowlist(site, allowed, issue, allowlist_path)
    if not permissions["BROWSE_PROJECTS"] or not permissions["EDIT_ISSUES"]:
        raise Refused("Jira says this identity may not edit this story (EDIT_ISSUES: %s)"
                      % ("yes" if permissions["EDIT_ISSUES"] else "no"))
    for name in wanted:
        if name not in editmeta:
            raise Refused("Jira does not list %s as a field this identity can edit on this story. On some "
                          "projects the field is switched off" % name)
    now = current_values(issue)
    changes = {}
    for name in SUPPORTED:
        if name not in wanted:
            continue
        new = wanted[name]
        if name == "priority":
            offered = [value for value in (editmeta["priority"].get("allowedValues") or [])
                       if isinstance(value, dict) and ident(value.get("id")) and isinstance(value.get("name"), str)]
            matches = [value for value in offered if value["name"] == new]
            if len(matches) != 1:
                raise Refused("priority %s is not one of the priorities Jira offers for this story: %s"
                              % (json.dumps(new), ", ".join(json.dumps(value["name"]) for value in offered) or "none"))
            new = {"id": matches[0]["id"], "name": matches[0]["name"]}
        changes[name] = {"old": now[name], "new": new, "send": now[name] != new}
    project = issue["fields"]["project"]
    return {"site": site, "ref": ref, "issue_id": issue["id"], "key": issue["key"], "project_id": project["id"],
            "project_key": project["key"], "editable": sorted(name for name in SUPPORTED if name in editmeta),
            "permissions": permissions, "changes": changes}


def fingerprint_of(proposal, made_at):
    text = canonical({"proposal": proposal, "made_at": made_at})
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def shown(name, value):
    if name == "labels":
        return json.dumps(value) if value else "(none)"
    if name == "duedate":
        return value or "(not set)"
    return "%s (id %s)" % (json.dumps(value["name"]), value["id"]) if value else "(not set)"


def wire(name, value):
    """The value as Jira's edit request takes it."""
    return {"id": value["id"]} if name == "priority" else value


# ---------------------------------------------------------------- showing


def head(conn, proposal):
    say("Jira site:  https://%s  (site fingerprint %s)" % (conn.host, proposal["site"]))
    say("Project:    %s (project id %s). On the sandbox allowlist: yes." % (proposal["project_key"], proposal["project_id"]))
    say("Story:      %s (issue id %s). The id is what identifies it." % (proposal["key"], proposal["issue_id"]))


def requests_line(conn):
    kinds = sorted(set(method for method, _ in conn.sent))
    say("Requests sent to Jira: %d. %s" % (len(conn.sent), "Every one was a GET, which reads and cannot change anything."
                                           if kinds == ["GET"] else "Kinds: %s." % ", ".join(kinds)))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    ref, wanted = read_change(args.change)
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    issue = read_issue(conn, ref)
    check_allowlist(site, allowed, issue, args.allowlist)
    before = snapshot(issue)
    read_myself(conn)
    permissions = read_permissions(conn, issue["id"])
    editmeta = read_editmeta(conn, issue["id"])
    proposal = build_proposal(site, allowed, args.allowlist, issue, permissions, editmeta, ref, wanted)
    after = snapshot(read_issue(conn, issue["id"]))
    if after != before:
        raise Refused("the story changed in Jira while the preview was being made. Preview again")

    sending = [name for name in SUPPORTED if name in proposal["changes"] and proposal["changes"][name]["send"]]
    same = [name for name in SUPPORTED if name in proposal["changes"] and not proposal["changes"][name]["send"]]
    say("PREVIEW. Nothing has been written." if sending else "NOTHING TO CHANGE. Nothing has been written.")
    say("")
    head(conn, proposal)
    say("")
    if sending:
        say("Changes that would be made: %d field%s." % (len(sending), "" if len(sending) == 1 else "s"))
        for name in sending:
            say("  %-9s now:    %s" % (name, shown(name, proposal["changes"][name]["old"])))
            say("  %-9s after:  %s" % ("", shown(name, proposal["changes"][name]["new"])))
    for name in same:
        say("Already as wanted, so not sent: %s, which holds %s." % (name, shown(name, proposal["changes"][name]["old"])))
    untouched = [name for name in SUPPORTED if name not in proposal["changes"]]
    if sending:
        say("Nothing else on the story would be sent%s."
            % (". Not in this change: %s" % ", ".join(untouched) if untouched else ""))
        say("Jira may email the story's watchers about the change, as it does for any edit.")
    say("")
    say("Permission check, asked of Jira for this story and this identity:")
    say("  may see the story  (BROWSE_PROJECTS): %s" % ("yes" if permissions["BROWSE_PROJECTS"] else "no"))
    say("  may edit the story (EDIT_ISSUES):     %s" % ("yes" if permissions["EDIT_ISSUES"] else "no"))
    say("  fields Jira lists as editable here:   %s"
        % ", ".join("%s %s" % (name, "yes" if name in proposal["editable"] else "no") for name in SUPPORTED))
    say("Duplicate check: an edit sets a field to a value and creates nothing, so there is no second copy to make.")
    say("  What could repeat is the same edit being sent twice. Checked against Jira just now: %d of the %d"
        % (len(same), len(proposal["changes"])))
    say("  fields named already hold the wanted value and would not be sent. Jira's documentation does not say")
    say("  whether sending a value a field already holds adds a history entry, so this workflow never sends one.")
    say("Where Jira cannot check: its edit request has no 'only if the value is still the one I saw' condition.")
    say("  The confirmation reads the story again just before writing and stops if a field has moved.")
    say("")
    say("Snapshot of the whole story as Jira returned it, before the preview: %s" % before)
    say("Snapshot of the whole story as Jira returned it, after the preview:  %s" % after)
    say("The two are the same. Jira is unchanged.")
    requests_line(conn)
    say("")
    if not sending:
        say("The story already holds every value asked for. No fingerprint is issued, because there is nothing")
        say("to confirm, and nothing was sent.")
        return 0

    made = now_utc()
    made_at = made.strftime(TIME_FORMAT)
    expires_at = (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT)
    fingerprint = fingerprint_of(proposal, made_at)
    code = fingerprint[:12]
    folder = os.path.join(args.state, "previews")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, code + ".json")
    if os.path.exists(path):
        raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
    save_json(path, {"fingerprint": fingerprint, "made_at": made_at, "expires_at": expires_at,
                     "proposal": proposal, "state": "open"})
    say("Fingerprint of this preview: %s" % code)
    say("Made:    %s" % made_at)
    say("Expires: %s (%d minutes after it was made)" % (expires_at, LIMIT_MINUTES))
    say("")
    say("Nothing has been written. To make these changes, a person who has read this preview confirms it by")
    say("its fingerprint.")
    return 0


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------- confirm


def read_preview_record(state, code):
    path = os.path.join(state, "previews", code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        made = datetime.datetime.strptime(record["made_at"], TIME_FORMAT)
        genuine = fingerprint_of(record["proposal"], record["made_at"])
        status = record["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s. Make a preview, read it, and confirm "
                      "that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != record.get("fingerprint") or genuine[:12] != code:
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, record, made, status


def compare(shown_before, now):
    """How the change worked out now differs from the preview: (what differs in the request, what moved in Jira)."""
    differs, moved = [], []
    if shown_before["issue_id"] != now["issue_id"]:
        differs.append("it names a different story")
    if shown_before["project_id"] != now["project_id"]:
        moved.append("the story is now in a different project (project id %s)" % now["project_id"])
    a, b = shown_before["changes"], now["changes"]
    if set(a) != set(b):
        differs.append("the preview covered %s and the change file now names %s"
                       % (", ".join(n for n in SUPPORTED if n in a), ", ".join(n for n in SUPPORTED if n in b)))
    for name in SUPPORTED:
        if name in a and name in b:
            if a[name]["new"] != b[name]["new"]:
                differs.append("%s: the preview showed %s and the change file now asks for %s"
                               % (name, shown(name, a[name]["new"]), shown(name, b[name]["new"])))
            if a[name]["old"] != b[name]["old"]:
                moved.append("%s: the preview saw %s and Jira now holds %s"
                             % (name, shown(name, a[name]["old"]), shown(name, b[name]["old"])))
    return differs, moved


def history_agrees(name, old, item):
    """Does Jira's history entry say the value before the write was the one the preview saw?"""
    if name == "priority":
        return (item.get("from") or None) == (old["id"] if old else None)
    if name == "duedate":
        return str(item.get("from") or "")[:10] == (old or "")
    return sorted(str(item.get("fromString") or "").split()) == sorted(old)


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it "
                      "approves, and there is no way to write without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")

    record_path, record, made, status = read_preview_record(args.state, code)
    if status == "written":
        raise Refused("the preview %s has already been confirmed and written. A fingerprint is used once" % code)
    if status != "open":
        raise Refused("the preview %s was confirmed before and a write was sent (recorded as '%s'). It cannot be "
                      "used again. Read the story, then make a new preview" % (code, status))

    confirmed = now_utc()
    now = confirmed
    if args.pretend_minutes_later:
        say("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
        now += datetime.timedelta(minutes=args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview is too old. It was made %d minutes ago and the limit is %d. Make a new "
                      "preview and read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    before = record["proposal"]
    ref, wanted = read_change(args.change)
    if ref != before["ref"]:
        raise Refused("the change is not the one that was previewed: it names a different story. Make a new "
                      "preview and read it")
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    if site != before["site"]:
        raise Refused("this is not the Jira site the preview was made against. Make a new preview and read it")
    issue_id = before["issue_id"]
    me = read_myself(conn)
    permissions = read_permissions(conn, issue_id)
    editmeta = read_editmeta(conn, issue_id)
    history_before = read_history(conn, issue_id)
    issue = read_issue(conn, issue_id)  # the last read before the write
    proposal = build_proposal(site, allowed, args.allowlist, issue, permissions, editmeta, ref, wanted)
    differs, moved = compare(before, proposal)
    if differs:
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it"
                      % "; ".join(differs))
    if moved:
        raise Refused("a field changed in Jira after the preview was made: %s. Someone or something else "
                      "changed it, and writing now would overwrite that. Make a new preview and read it"
                      % "; ".join(moved))
    sending = [n for n in SUPPORTED if n in proposal["changes"] and proposal["changes"][n]["send"]]

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, proposal)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %d minute%s old, and the limit is %d: ok"
        % (age.total_seconds() // 60, "" if age.total_seconds() // 60 == 1 else "s", LIMIT_MINUTES))
    say("  the saved preview is unaltered and has not been used: ok")
    say("  the change file asks for exactly what the preview showed: ok")
    say("  the project is on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may edit the story and these fields: ok")
    say("  each field still holds in Jira the value the preview saw, read just before the write:")
    for field in sending:
        say("    %-9s preview saw %s, Jira holds %s: the same"
            % (field, shown(field, before["changes"][field]["old"]), shown(field, proposal["changes"][field]["old"])))
    say("")

    record["state"] = "sending"
    save_json(record_path, record)
    try:
        status, _, body = conn.put_issue(issue_id, {field: wire(field, proposal["changes"][field]["new"]) for field in sending})
    except NeedsLooking:
        record["state"] = "sent, answer not received"
        save_json(record_path, record)
        raise
    written_at = now_utc().strftime(TIME_FORMAT)
    after = current_values(read_issue(conn, issue_id))
    as_proposed = all(after[field] == proposal["changes"][field]["new"] for field in sending)
    as_before = all(after[field] == proposal["changes"][field]["old"] for field in sending)
    if status not in (200, 204):
        record["state"] = "sent, Jira answered %d" % status
        save_json(record_path, record)
        named = sorted(str(key)[:40] for key in (body.get("errors") or {}) if key in SUPPORTED) if isinstance(body.get("errors"), dict) else []
        detail = ("Jira answered %d to the write%s. Read back afterwards, the fields %s"
                  % (status, " and named: %s" % ", ".join(named) if named else "",
                     "hold what they held before, so nothing was written" if as_before
                     else "do NOT hold what they held before. A person needs to look at the story"))
        if as_before:
            raise Refused(detail + ". The preview cannot be used again")
        raise NeedsLooking(detail)

    say("WRITTEN to Jira: one edit of story %s, fields %s. Jira answered %d." % (proposal["key"], ", ".join(sending), status))
    say("The confirmation and the write happened in this one run of the command.")
    say("")
    say("Read back from Jira after the write:")
    for field in sending:
        say("  %-9s %s: %s" % (field, shown(field, after[field]),
                               "as proposed" if after[field] == proposal["changes"][field]["new"] else "NOT AS PROPOSED"))
    others = [field for field in SUPPORTED if field not in sending]
    earlier = current_values(issue)
    for field in others:
        say("  %-9s %s: %s" % (field, shown(field, after[field]),
                               "not part of the write, and unchanged" if after[field] == earlier[field]
                               else "not part of the write, and it has CHANGED since the last read"))

    # Find the history entry this write made: an entry that was not there before, by this identity, on these fields.
    history_after = read_history(conn, issue_id)
    mine, overwrote = [], []
    if history_before is not None and history_after is not None:
        known = set(entry.get("id") for entry in history_before)
        for entry in history_after:
            items = [item for item in (entry.get("items") or []) if isinstance(item, dict)
                     and (item.get("fieldId") or str(item.get("field") or "").lower()) in sending]
            if entry.get("id") not in known and items and (entry.get("author") or {}).get("accountId") == me:
                mine.append(str(entry.get("id"))[:40])
                for item in items:
                    field = item.get("fieldId") or str(item.get("field")).lower()
                    if not history_agrees(field, before["changes"][field]["old"], item):
                        overwrote.append(field)
    say("")
    if mine:
        say("Identifier of the change: Jira changelog entry %s for issue id %s." % (", ".join(mine), issue_id))
        say("  It is the history entry that was not there before the write, made by this identity, on these fields.")
    else:
        say("Identifier of the change: no single history entry could be picked out, so the read-back values")
        say("  above are the record of what was changed.")
    if overwrote:
        say("  WARNING: for %s, Jira's history records a different value before this write than the one the"
            % ", ".join(overwrote))
        say("  preview saw. A change made in the moment between the last read and the write may have been")
        say("  overwritten. A person needs to look at the story's history.")
    elif mine:
        say("  For each field, the value that entry records from before the write is the one the preview saw.")

    confirmed_at = confirmed.strftime(TIME_FORMAT)
    result = {"fingerprint": record["fingerprint"], "issue_key": proposal["key"], "issue_id": issue_id,
              "project_key": proposal["project_key"], "project_id": proposal["project_id"], "site_fingerprint": site,
              "changelog_entries": mine, "confirmed_by": name, "confirmed_at": confirmed_at, "written_at": written_at,
              "preview_made_at": record["made_at"],
              "fields": {field: {"before": proposal["changes"][field]["old"], "after": proposal["changes"][field]["new"],
                                 "read_back": after[field]} for field in sending}}
    os.makedirs(os.path.join(args.state, "written"), exist_ok=True)
    save_json(os.path.join(args.state, "written", code + ".json"), result)
    record["state"] = "written"
    save_json(record_path, record)

    say("")
    say("RESULT RECORD")
    for line in result_lines(result):
        say("  " + line)
    if args.result:
        text = "\n".join(["# Result record: fields updated on one Jira story", ""]
                         + ["- " + line for line in result_lines(result)]) + "\n"
        os.makedirs(os.path.dirname(os.path.abspath(args.result)), exist_ok=True)
        with open(args.result, "w", encoding="utf-8") as f:
            f.write(text.replace(conn.host, SITE_MARK))
        say("")
        say("The result record was also saved as Markdown where --result said.")
    if not as_proposed:
        raise NeedsLooking("Jira accepted the write, and the story does not read back as proposed")
    if overwrote:
        raise NeedsLooking("the write was made, and Jira's history suggests it overwrote a change made in the last moment")
    return 0


def result_lines(result):
    lines = ["Issue key: %s" % result["issue_key"],
             "Issue id: %s (this identifies the story; a key can change)" % result["issue_id"],
             "Target project: %s (project id %s), on the sandbox allowlist" % (result["project_key"], result["project_id"]),
             "Jira site: %s, site fingerprint %s" % (SITE_MARK, result["site_fingerprint"]),
             "Identifier of what was changed: %s" % ("Jira changelog entry %s" % ", ".join(result["changelog_entries"])
                                                     if result["changelog_entries"] else "the read-back values below")]
    for field in SUPPORTED:
        if field in result["fields"]:
            values = result["fields"][field]
            lines.append("Field %s: before %s; after %s; read back from Jira %s"
                         % (field, shown(field, values["before"]), shown(field, values["after"]), shown(field, values["read_back"])))
    lines += ["Written at: %s" % result["written_at"],
              "Confirmed by: %s, at %s" % (result["confirmed_by"], result["confirmed_at"]),
              "Preview: fingerprint %s, made %s" % (result["fingerprint"][:12], result["preview_made_at"]),
              "To reverse: make a new preview that sets each field back to its 'before' value. A field that was "
              "not set before cannot be put back by this workflow, which does not clear fields"]
    return lines


# ---------------------------------------------------------------- running


def minutes_forward(text):
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number of minutes, 0 or more")
    return int(text)


def refused(refusal):
    say("")
    say("REFUSED: %s." % refusal)
    say("Nothing has been written.")
    return 1


def run(args, conn):
    """One command, start to finish. Returns the exit code; what it said is in LINES."""
    try:
        return cmd_confirm(args, conn) if args.command == "confirm" else cmd_preview(args, conn)
    except Refused as refusal:
        return refused(refusal)
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        say("Do not run this again before reading the story in Jira.")
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, then confirm, a change to labels, due date or priority on one Jira story.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "confirm"):
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--change", required=True, help="the change file")
        sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
        sub.add_argument("--state", required=True, help="the folder where previews and write records are kept")
        sub.add_argument("--log", help="also save the output here, with the site's address removed")
        if command == "confirm":
            sub.add_argument("--fingerprint")
            sub.add_argument("--confirmed-by")
            sub.add_argument("--result", help="save the result record of a write here, as Markdown")
            sub.add_argument("--pretend-minutes-later", type=minutes_forward, default=0, metavar="N",
                             help="tests only: move 'now' forward by N minutes")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn, fake, fake_path = [], None, None, os.path.join(args.state, "fake-jira.json")
    try:
        if args.source == "fake":
            import fake_jira
            fake = fake_jira.FakeJira.open(fake_path)
            host = urllib.parse.urlparse(fake_jira.SITE).hostname
            conn = Connection(fake.get, fake.put if args.command == "confirm" else None, host)
        else:
            conn, secrets = make_live(args.command == "confirm")
        code = run(args, conn)
    except Refused as refusal:
        code = refused(refusal)
    if fake is not None:
        fake.save(fake_path)
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 2 if conn and any(method == "PUT" for method, _ in conn.sent) else 1
    print(text)
    if secrets:
        note = ("\nThe output above was searched for the API token, the account's email address and their encoded\n"
                "form: none found.")
        print(note)
        text += "\n" + note
    if args.log:
        host = conn.host if conn else ""
        saved = text.replace("https://" + host, SITE_MARK).replace(host, SITE_MARK) if host else text
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        with open(args.log, "w", encoding="utf-8") as f:
            f.write(saved + "\n")
    return code


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main())
