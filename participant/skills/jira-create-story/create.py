#!/usr/bin/env python3
"""Creates one Jira story from a local draft: preview first, then a person confirms, then the local link.

    create.py preview   --source live|fake --draft DRAFT.md --link LINK.md --allowlist FILE --catalog FOLDER --state FOLDER
    create.py confirm   (the same options) --fingerprint CODE --confirmed-by NAME [--result FILE.md]
    create.py verify    --source live|fake --link LINK.md
    create.py reconcile --source live|fake --link LINK.md --state FOLDER [--result FILE.md]

The draft is the one the jira-create-story-preview skill reads, and this
workflow builds its payload with that skill's own function, build_payload,
so that a preview here and a preview there cannot mean different things.

preview    reads Jira and writes nothing to it. It has no way to send a write.
           It shows the site, the project, every field, the exact payload, the
           permission check, the duplicate checks and a fingerprint, and saves
           the preview in the state folder. It refuses if the draft is already
           linked to a Jira story.

confirm    creates the story of one preview, named by its fingerprint, and only
           if all of this holds at that moment: a fingerprint and the
           confirming person's name are given; the saved preview is unaltered,
           unused and at most 15 minutes old; the draft is byte for byte the one
           previewed; the payload worked out again from the draft and from Jira
           as it is now has the same SHA-256; the project is on the sandbox
           allowlist; Jira says this identity may create there; and no story
           carrying this preview's marker exists.

           Then, in this order: it writes the link file saying a create is
           being sent; sends the create once; writes the key and id that came
           back into the link file; reads the story back from Jira; compares
           it with the payload field for field; and writes the comparison and
           the result record.

verify     reads the linked story from Jira by its issue id and compares it
           again with the payload that was sent. If the key has changed in
           Jira it says so, matches by id all the same, and updates the key in
           the link file. It writes nothing to Jira.

reconcile  is for when a create was sent and its result was never recorded.
           It looks in Jira for the preview's marker. Exactly one story found:
           it is linked, read back and compared. None found: it says so, says
           that Jira's search can lag, and creates nothing. It writes nothing
           to Jira.

The marker. Jira has no documented way to refuse a second create of the same
story. So each preview adds one label to the payload, gtq- and eight random
characters, shown in the preview like every other part of it. After a failure
it is how the workflow finds out whether the story exists.

A create is sent once and never retried.

The link file is the local story: its fields, the Jira key and id, the
preview it came from, the payload that was sent and the read-back comparison.

The site's address is shown on screen and removed from anything saved. For a
live run the connection comes from the environment variables JIRA_BASE_URL,
JIRA_EMAIL and JIRA_API_TOKEN. None is stored, and the output is searched for
them before it is shown. No story text from Jira is printed.

Exit codes: 0 done; 1 refused, nothing written to Jira; 2 a create was sent
and a person needs to look.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "jira-create-story-preview"))
import preview as pv  # noqa: E402
from preview import Refused, index, search  # noqa: E402

LINK_FORMAT = "jira-linked-story/1"
SENT = "create sent, result not recorded"
CREATED = "created"
LIMIT_MINUTES = 15
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
MARKER = re.compile(r"gtq-[0-9a-f]{8}")
LINK_NAMES = ("format", "state", "draft", "draft_sha256", "marker", "preview_fingerprint", "payload_sha256", "site_fingerprint",
              "project_id", "project_key", "jira_id", "jira_key", "earlier_keys", "confirmed_by", "confirmed_at", "created_at",
              "compared_at", "comparison")
SHOWN_EXTRAS = ("status", "priority", "reporter", "assignee", "creator", "resolution", "security", "created")

LINES = []


class NeedsLooking(Exception):
    """A create was sent. The message says what is and is not known."""


def say(text=""):
    LINES.append(text)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


# ---------------------------------------------------------------- the connection


class Connection:
    """Every request goes through here and is written down. Without `post` there is no way to write."""

    def __init__(self, get, post, host):
        self._get, self._post, self.host, self.sent = get, post, host, []

    def get(self, path, params=None):
        self.sent.append(("GET", path))
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            reason = "could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__
            if any(method == "POST" for method, _ in self.sent):
                raise NeedsLooking("after the create was sent, a read failed: %s" % reason)
            raise Refused(reason)

    def create(self, body):
        """Send one create. `body` is the exact bytes of the request."""
        if self._post is None:
            raise Refused("this command has no way to write")
        if any(method == "POST" for method, _ in self.sent):
            raise Refused("a create has already been sent in this run, and a create is sent once")
        self.sent.append(("POST", "/rest/api/3/issue"))
        try:
            return self._post("/rest/api/3/issue", None, body)
        except (OSError, TimeoutError) as err:
            raise NeedsLooking("the create was sent and no answer came back (%s). It is NOT KNOWN whether Jira created "
                               "the story. It was not sent again" % type(getattr(err, "reason", err)).__name__)


def make_live(may_write):
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    if not base.startswith("https://"):
        raise Refused("JIRA_BASE_URL must start with https://")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = urllib.request.build_opener(pv.NoRedirect)

    def send(method, path, params, body):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with opener.open(request, timeout=30) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as err:
            status, raw = err.code, err.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except ValueError:
            parsed = {}
        return status, {}, parsed if isinstance(parsed, dict) else {}

    def get(path, params=None):
        return send("GET", path, params, None)

    def post(path, params, body):
        if path != "/rest/api/3/issue" or params or not isinstance(body, bytes):
            raise Refused("the only write this workflow sends is the creation of one story")
        return send("POST", path, None, body)

    return Connection(get, post if may_write else None, urllib.parse.urlparse(base).hostname or ""), [token, email, encoded]


# ---------------------------------------------------------------- the link file


def sha_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def read_link(path):
    """The link file as (its fields, the payload it holds), or (None, None) if there is none."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None, None
    except (OSError, UnicodeDecodeError):
        raise Refused("the link file could not be read")
    front = index.front_matter(text)
    if front is None or front.get("format") != LINK_FORMAT or front.get("state") not in (SENT, CREATED):
        raise Refused("the file at the link path is not a link this workflow wrote, so it is left alone")
    try:
        payload = json.loads(text.split("\n## The payload that was sent\n", 1)[1].split("```json\n", 1)[1].split("\n```", 1)[0])
    except (IndexError, ValueError):
        raise Refused("the link file's payload could not be read")
    return front, payload


def write_link(path, front, draft, payload, rows=None, extras=None, note=None):
    cell = search.md
    out = ["---"] + ["%s: %s" % (name, json.dumps(front.get(name), ensure_ascii=False, sort_keys=True)) for name in LINK_NAMES] + ["---", ""]
    out += ["# %s" % cell(draft["summary"]), "",
            "> This file is written by `participant/skills/jira-create-story/create.py`. It is the local record of one",
            "> Jira story. The story is identified by its issue id, `jira_id` above. A key can change.", ""]
    if front["state"] == SENT:
        out += ["**A create was sent to Jira and its result has not been recorded.** The story may or may not exist.",
                "Do not create it again. Run the `reconcile` command, which looks in Jira for the marker `%s`." % front["marker"], ""]
    else:
        out += ["Linked to Jira story **%s**, issue id **%s**, in project %s (project id %s)."
                % (front["jira_key"], front["jira_id"], front["project_key"], front["project_id"]), ""]
    out += ["## Description", "", draft["description"] or "(none)", "",
            "## Sources", ""]
    out += ['- %s: %s line%s: "%s"' % (s["what"], s["file"], " %d" % s["first"] if s["first"] == s["last"] else "s %d-%d" % (s["first"], s["last"]), s["quote"])
            for s in draft["sources"]] or ["none"]
    out += ["", "## Read-back and compare", ""]
    if rows is None:
        out += [note or "The story has not been read back yet."]
    else:
        out += ["The story was read back from Jira by its issue id at %s and compared with the payload that was sent." % front["compared_at"],
                "Result: **%s**" % front["comparison"], "",
                "| Field | Sent | Read back from Jira | Verdict |", "|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s |" % (field, cell(sent), cell(back), verdict) for field, sent, back, verdict in rows]
        out += ["", "Fields Jira set that the payload did not send:", ""]
        out += ["- `%s`, %s: %s" % (field, cell(name), cell(value)) for field, name, value in extras["shown"]] or ["- none of the ones this workflow shows"]
        if extras["others"]:
            out += ["- and %d more that hold a value, by field id: %s" % (len(extras["others"]), ", ".join("`%s`" % f for f in extras["others"]))]
    out += ["", "## The payload that was sent", "",
            "%d bytes as sent, SHA-256 `%s`." % (len(pv.body_bytes(payload)), front["payload_sha256"]), "",
            "```json", pv.pretty(payload), "```"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(path + ".tmp", path)


def refuse_if_linked(link_path, draft_path):
    front, _ = read_link(link_path)
    if front is None:
        return
    if front.get("draft") != os.path.relpath(draft_path, os.path.dirname(os.path.abspath(link_path))):
        raise Refused("the link file belongs to another draft, %s. Give this draft a link file of its own" % json.dumps(front.get("draft")))
    if front["state"] == CREATED:
        raise Refused("this draft has already been created in Jira as %s (issue id %s), recorded in the link file. "
                      "It is not created twice. Use the verify command to compare it with Jira"
                      % (front.get("jira_key"), front.get("jira_id")))
    raise Refused("a create for this draft was sent and its result was never recorded. The story may exist in Jira. "
                  "Run the reconcile command before anything else. Nothing is created")


# ---------------------------------------------------------------- reading Jira


def jql(conn, query, fields):
    """Every story a JQL query finds, or None if Jira would not run it."""
    found, token = [], None
    for _ in range(pv.MAX_PAGES):
        params = {"jql": query, "fields": fields, "maxResults": 100}
        if token:
            params["nextPageToken"] = token
        status, _, body = conn.get("/rest/api/3/search/jql", params)
        issues = body.get("issues") if status == 200 else None
        if not isinstance(issues, list):
            return None
        found += [item for item in issues if isinstance(item, dict) and pv.ident(str(item.get("id")))]
        token = body.get("nextPageToken")
        if not token or not issues:
            return found
    return None


def marker_search(conn, project, marker):
    """The issue ids of the stories in the project that carry the marker label."""
    found = jql(conn, 'project = %s AND labels = "%s"' % (project["id"], marker), "labels")
    if found is None:
        raise Refused("Jira would not search for the marker %s, so it is not known whether the story exists" % marker)
    return [str(item["id"]) for item in found if marker in ((item.get("fields") or {}).get("labels") or [marker])]


def title_check(conn, project, title):
    """Stories in the project whose title is this title, and others Jira's text search returns. None if it would not run."""
    phrase = title.replace("\\", "\\\\").replace('"', '\\"')
    found = jql(conn, 'project = %s AND summary ~ "\\"%s\\""' % (project["id"], phrase), "summary")
    if found is None:
        return None
    same = [str(item["id"]) for item in found
            if " ".join(str((item.get("fields") or {}).get("summary")).split()).lower() == " ".join(title.split()).lower()]
    return same, [str(item["id"]) for item in found if str(item["id"]) not in same]


def read_story(conn, issue_id):
    status, _, body = conn.get("/rest/api/3/issue/%s" % issue_id, {"expand": "names"})
    if status == 404:
        return None
    if status != 200 or not isinstance(body.get("fields"), dict) or not pv.ident(body.get("id")) or not isinstance(body.get("key"), str):
        raise NeedsLooking("the story with issue id %s could not be read back from Jira (status %d)" % (issue_id, status))
    return body


# ---------------------------------------------------------------- compare


def plain(node):
    """An Atlassian Document Format tree reduced to its structure and text, without Jira's own bookkeeping."""
    if isinstance(node, dict):
        kept = {"type": node.get("type")}
        if "text" in node:
            kept["text"] = node["text"]
        if node.get("marks"):
            kept["marks"] = [plain(mark) for mark in node["marks"]]
        if node.get("content"):
            kept["content"] = [plain(child) for child in node["content"]]
        return kept
    return node


def ids(value):
    return sorted(str(item.get("id")) for item in value or [] if isinstance(item, dict))


def brief(value):
    """A value in a few words, for the comparison table. People are never shown."""
    if value is None or value == [] or value == "":
        return "(empty)"
    if isinstance(value, dict):
        if "accountId" in value:
            return "a person, not shown"
        if value.get("type") == "doc":
            return "%d block(s) of document" % len(value.get("content") or [])
        for key in ("name", "value", "key"):
            if isinstance(value.get(key), str):
                return "%s (id %s)" % (json.dumps(value[key]), value["id"]) if value.get("id") else json.dumps(value[key])
        return "id %s" % value["id"] if "id" in value else "a value"
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return json.dumps(sorted(value))
        return ", ".join(brief(item) for item in value)
    return json.dumps(value) if isinstance(value, str) else str(value)


def compare(payload, story):
    """Each field the payload sent, against the story read back. Returns (rows, all the same, extras)."""
    sent, back = payload["fields"], story["fields"]
    rows, good = [], True
    for field in sent:
        a, b = sent[field], back.get(field)
        if field in ("project", "issuetype", "priority") or field.startswith("customfield_"):
            same = isinstance(b, dict) and str(b.get("id")) == str(a.get("id"))
        elif field == "parent":
            same = isinstance(b, dict) and (b.get("key") == a.get("key") if "key" in a else str(b.get("id")) == str(a.get("id")))
        elif field == "components":
            same = ids(b) == ids(a)
        elif field == "labels":
            same = isinstance(b, list) and sorted(b) == sorted(a)
        elif field == "description":
            same = plain(b) == plain(a)
        else:
            same = a == b
        verdict = "the same" if same else "**DIFFERENT**"
        if field == "description" and same:
            verdict = "the same, identical as sent" if a == b else "the same text and structure; Jira's copy also holds its own block identifiers"
        good = good and same
        if field == "project" and isinstance(b, dict):
            b = {"id": b.get("id"), "key": b.get("key")}  # a project's name is not shown, only its key and id
        rows.append((field, brief(a), brief(b), verdict))
    names = story.get("names") if isinstance(story.get("names"), dict) else {}
    held = [field for field in sorted(back) if field not in sent and back[field] not in (None, [], "", {})]
    shown = [(field, str(names.get(field, field)), brief(back[field])) for field in held if field in SHOWN_EXTRAS]
    return rows, good, {"shown": shown, "others": [field for field in held if field not in SHOWN_EXTRAS]}


# ---------------------------------------------------------------- working the change out


def gather(conn, args, marker):
    """Everything a preview and a confirmation both need, worked out the same way from the draft and from Jira now."""
    draft = pv.read_draft(args.draft)
    pv.check_sources(draft)
    allowed = pv.load_allowlist(args.allowlist)
    site = pv.site_fingerprint(conn.host)
    project = pv.read_project(conn, draft["project"])
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox allowlist "
                      "(%s). This workflow writes only to projects listed there" % (project["key"], project["id"], site, args.allowlist))
    status, _, me = conn.get("/rest/api/3/myself")
    if status != 200 or not isinstance(me.get("accountId"), str):
        raise Refused("Jira did not say which identity this is (status %d)" % status)
    permissions = pv.read_permissions(conn, project["id"])
    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:
        raise Refused("Jira says this identity may not create stories in %s (CREATE_ISSUES: %s)"
                      % (project["key"], "yes" if permissions["CREATE_ISSUES"] else "no"))
    kind = pv.read_issue_type(conn, project, draft["issuetype"])
    meta = pv.read_fields(conn, project, kind)
    parent_id = pv.read_parent(conn, draft["parent"], project) if draft["parent"] else None
    if marker in (draft["labels"] or []):
        raise Refused("the draft already has the label %s" % marker)
    marked = dict(draft, labels=(draft["labels"] or []) + [marker])
    payload, rows, left, unset = pv.build_payload(marked, project, kind, meta, parent_id)
    body = pv.body_bytes(payload)
    return {"draft": draft, "site": site, "project": project, "kind": kind, "meta": meta, "payload": payload, "rows": rows,
            "left": left, "unset": unset, "body": body, "digest": hashlib.sha256(body).hexdigest()}


def head(conn, found):
    say("Jira site:   https://%s  (site fingerprint %s)" % (conn.host, found["site"]))
    say("Project:     %s (project id %s). On the sandbox allowlist: yes." % (found["project"]["key"], found["project"]["id"]))
    say("Issue type:  %s (issue type id %s)" % (json.dumps(found["kind"]["name"]), found["kind"]["id"]))
    say("Draft:       %s" % index.place(found["draft"]["path"]))


def requests_line(conn):
    kinds = [method for method, _ in conn.sent]
    say("Requests sent to Jira: %d. %s" % (len(kinds), "Every one was a GET, which reads and cannot change anything."
                                           if set(kinds) == {"GET"} else "%d GET and %d POST. The POST is the one create."
                                           % (kinds.count("GET"), kinds.count("POST"))))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))


def fingerprint_of(record):
    core = {name: record[name] for name in ("made_at", "site", "project", "issuetype", "payload", "payload_sha256", "marker",
                                            "draft_sha256", "link")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(path + ".tmp", path)


# ---------------------------------------------------------------- preview


def cmd_preview(args, conn):
    refuse_if_linked(args.link, os.path.abspath(args.draft))
    marker = "gtq-" + secrets.token_hex(4)
    found = gather(conn, args, marker)
    project, draft, payload = found["project"], found["draft"], found["payload"]
    before = pv.snapshot(conn, project)
    titles = title_check(conn, project, draft["summary"])
    proposal, result, keys = pv.find_duplicates(draft, os.path.abspath(args.catalog), args.today)
    after = pv.snapshot(conn, project)
    if after != before:
        raise Refused("the project's stories changed in Jira while the preview was being made. Preview again")
    _, covered = pv.coverage(keys, project, after[0])

    say("PREVIEW OF CREATING ONE STORY. Nothing has been written to Jira.")
    say("")
    head(conn, found)
    say("Link file:   %s (not there yet: this draft has not been created)" % index.place(os.path.abspath(args.link)))
    say("The change:  one new story would be created, with one request: POST /rest/api/3/issue")
    say("")
    say("EVERY FIELD Jira lists for creating a %s in %s: %d." % (json.dumps(found["kind"]["name"]), project["key"], len(found["meta"])))
    say("Set by the draft, and by this preview's marker, %d:" % len(found["rows"]))
    for field_id, name, shown in found["rows"]:
        say("  %-18s %-13s %s" % (field_id, name, shown))
    say("  The label %s is this preview's marker. It is not in the draft. It is how the story is found" % marker)
    say("  again if the create is sent and its answer is lost.")
    say("Required by Jira, not in the draft, and LEFT TO JIRA because it has a default, %d:" % len(found["left"]))
    for field_id, name, default in found["left"]:
        say("  %-18s %-13s %s." % (field_id, name, default))
    say("Optional, not in the draft, and not sent, %d:" % len(found["unset"]))
    for field_id, name, default in found["unset"]:
        say("  %-18s %-13s %s." % (field_id, name, default))
    say("")
    say("THE EXACT PAYLOAD. This is the request body, not a summary of it:")
    for line in pv.pretty(payload).split("\n"):
        say("  " + line)
    say("As sent it is the same data with no spaces or line breaks and its names in alphabetical order:")
    say("  %d bytes, SHA-256 %s" % (len(found["body"]), found["digest"]))
    say("")
    say("Permission check, asked of Jira for this project and this identity:")
    say("  may see the project    (BROWSE_PROJECTS): yes")
    say("  may create stories     (CREATE_ISSUES):   yes")
    say("Duplicate checks:")
    say("  1. This draft's own link file: there is none, so this workflow has not created it before.")
    if titles is None:
        say("  2. Asked of Jira, stories in %s with this title: Jira would not run the search, so this was NOT checked." % project["key"])
    else:
        say("  2. Asked of Jira, stories in %s with this title: %d with exactly this title%s; %d more returned by Jira's"
            % (project["key"], len(titles[0]), " (issue id %s)" % ", ".join(titles[0]) if titles[0] else "", len(titles[1])))
        say("     text search for these words%s." % (" (issue id %s)" % ", ".join(titles[1][:10]) if titles[1] else ""))
    say("  3. " + pv.duplicate_lines(proposal, result, os.path.abspath(args.catalog), covered)[0])
    for line in pv.duplicate_lines(proposal, result, os.path.abspath(args.catalog), covered)[1:]:
        say("   " + line)
    say("Where Jira cannot check: it has no way to refuse a second create of the same story, and no way to try a")
    say("  create without making one. The link file and the marker are this workflow's own protection.")
    say("")
    say("Snapshot of the project's stories in Jira before the preview: %d stories, %s" % before)
    say("Snapshot of the project's stories in Jira after the preview:  %d stories, %s" % after)
    say("The two are the same. Jira is unchanged.")
    requests_line(conn)

    made = now_utc()
    record = {"made_at": made.strftime(TIME_FORMAT), "expires_at": (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT),
              "site": found["site"], "project": project, "issuetype": found["kind"], "payload": payload, "payload_sha256": found["digest"],
              "marker": marker, "draft_sha256": sha_of(draft["path"]), "link": os.path.abspath(args.link), "state": "open"}
    record["fingerprint"] = fingerprint_of(record)
    code = record["fingerprint"][:12]
    path = os.path.join(args.state, "create-story-previews", code + ".json")
    save_json(path, record)
    say("")
    say("Fingerprint of this preview: %s" % code)
    say("Made:    %s" % record["made_at"])
    say("Expires: %s (%d minutes after it was made)" % (record["expires_at"], LIMIT_MINUTES))
    say("")
    say("Nothing has been written to Jira. To create this story, a person who has read this preview confirms it")
    say("by its fingerprint.")
    return 0


# ---------------------------------------------------------------- confirm


def read_preview_record(state, code):
    path = os.path.join(state, "create-story-previews", code + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        made = datetime.datetime.strptime(record["made_at"], TIME_FORMAT)
        genuine = fingerprint_of(record)
        status = record["state"]
    except FileNotFoundError:
        raise Refused("there is no preview with the fingerprint %s. Make a preview, read it, and confirm that one" % code)
    except (ValueError, KeyError, TypeError):
        raise Refused("the saved preview %s cannot be read, so it cannot be confirmed" % code)
    if genuine != record.get("fingerprint") or genuine[:12] != code or not MARKER.fullmatch(str(record.get("marker"))):
        raise Refused("the saved preview %s has been altered since it was made, so it cannot be confirmed" % code)
    return path, record, made, status


def differing(a, b):
    names = sorted(set(a["fields"]) | set(b["fields"]))
    return [name for name in names if a["fields"].get(name) != b["fields"].get(name)]


def cmd_confirm(args, conn):
    code = (args.fingerprint or "").strip().lower()
    if not code:
        raise Refused("no confirmation was given. A confirmation names the fingerprint of the preview it approves, and "
                      "there is no way to create without one")
    if len(code) != 12 or any(ch not in "0123456789abcdef" for ch in code):
        raise Refused("a fingerprint is 12 characters, each 0 to 9 or a to f")
    name = (args.confirmed_by or "").strip()
    if not name:
        raise Refused("no confirmation was given. A confirmation gives the name of the person confirming")
    if len(name) > 60 or "@" in name or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise Refused("the confirming person's name must be short plain text, and not an email address")

    record_path, record, made, status = read_preview_record(args.state, code)
    if status == "written":
        raise Refused("the preview %s has already been confirmed and its story created. A fingerprint is used once" % code)
    if status != "open":
        raise Refused("the preview %s was confirmed before and a create was sent (recorded as '%s'). It cannot be used "
                      "again" % (code, status))
    refuse_if_linked(args.link, os.path.abspath(args.draft))
    if os.path.abspath(args.link) != record["link"]:
        raise Refused("the link file named is not the one the preview was made for")

    confirmed = now_utc()
    now = confirmed
    if args.pretend_minutes_later:
        say("TEST CLOCK: pretending it is %d minutes later than it is." % args.pretend_minutes_later)
        now += datetime.timedelta(minutes=args.pretend_minutes_later)
    age = now - made
    if age < datetime.timedelta(0):
        raise Refused("the preview %s is dated later than the clock says it is now" % code)
    if age > datetime.timedelta(minutes=LIMIT_MINUTES):
        raise Refused("this preview is too old. It was made %d minutes ago and the limit is %d. Make a new preview and "
                      "read it" % (age.total_seconds() // 60, LIMIT_MINUTES))

    found = gather(conn, args, record["marker"])
    project = found["project"]
    if found["site"] != record["site"] or project["id"] != record["project"]["id"]:
        raise Refused("the change is not the one that was previewed: it is for another site or project. Make a new "
                      "preview and read it")
    if found["digest"] != record["payload_sha256"] or sha_of(found["draft"]["path"]) != record["draft_sha256"]:
        fields = differing(record["payload"], found["payload"])
        raise Refused("the change is not the one that was previewed: %s. Make a new preview and read it"
                      % ("the payload now differs in %s" % ", ".join(fields) if fields else
                         "the draft file has been edited since the preview, though the payload comes out the same"))
    already = marker_search(conn, project, record["marker"])
    if already:
        raise Refused("a story carrying this preview's marker %s already exists in Jira (issue id %s). Nothing is "
                      "created. Run the reconcile command" % (record["marker"], ", ".join(already)))

    say("CONFIRMATION for preview %s, given by: %s (the name given with the confirmation)." % (code, name))
    say("")
    head(conn, found)
    say("")
    say("Checked in this run, before writing:")
    say("  the preview is %d minute%s old, and the limit is %d: ok" % (age.total_seconds() // 60, "" if age.total_seconds() // 60 == 1 else "s", LIMIT_MINUTES))
    say("  the saved preview is unaltered and has not been used: ok")
    say("  the draft file is byte for byte the one that was previewed: ok")
    say("  the payload worked out again now has the SHA-256 of the previewed one, %s: ok" % found["digest"])
    say("  the project is on the sandbox allowlist for this site: ok")
    say("  Jira says this identity may create stories here: ok")
    say("  this draft has no link file, and no story in Jira carries the marker %s: ok" % record["marker"])
    say("")

    front = {"format": LINK_FORMAT, "state": SENT, "draft": os.path.relpath(found["draft"]["path"], os.path.dirname(os.path.abspath(args.link))),
             "draft_sha256": record["draft_sha256"], "marker": record["marker"], "preview_fingerprint": record["fingerprint"],
             "payload_sha256": found["digest"], "site_fingerprint": found["site"], "project_id": project["id"],
             "project_key": project["key"], "jira_id": None, "jira_key": None, "earlier_keys": [], "confirmed_by": name,
             "confirmed_at": confirmed.strftime(TIME_FORMAT), "created_at": None, "compared_at": None, "comparison": None}
    write_link(args.link, front, found["draft"], found["payload"])
    record["state"] = "sending"
    save_json(record_path, record)
    say("Written to the link file before sending: a create is being sent, result not yet recorded.")
    try:
        status, _, body = conn.create(found["body"])
    except NeedsLooking:
        record["state"] = "sent, answer not received"
        save_json(record_path, record)
        raise
    if status != 201 or not pv.ident(body.get("id")) or not isinstance(body.get("key"), str):
        record["state"] = "sent, Jira answered %d" % status
        save_json(record_path, record)
        if status in (400, 401, 403, 404, 422) and not marker_search(conn, project, record["marker"]):
            os.remove(args.link)
            fields = sorted(str(key)[:40] for key in body.get("errors") or {}) if isinstance(body.get("errors"), dict) else []
            messages = [str(m)[:200] for m in body.get("errorMessages") or []][:3] if isinstance(body.get("errorMessages"), list) else []
            raise Refused("Jira answered %d to the create and made no story%s%s. No story carries the marker. The link file "
                          "has been removed, and this preview cannot be used again"
                          % (status, ". Fields Jira named: %s" % ", ".join(fields) if fields else "",
                             ". Jira said: %s" % "; ".join(json.dumps(m) for m in messages) if messages else ""))
        raise NeedsLooking("Jira answered %d to the create, and it is not certain that no story was made. The link file "
                           "says a create was sent. Run the reconcile command" % status)
    say("CREATED in Jira: one story. Jira answered 201 with the key %s and the issue id %s." % (body["key"], body["id"]))
    say("The confirmation and the write happened in this one run of the command.")
    front.update(state=CREATED, jira_id=body["id"], jira_key=body["key"], created_at=now_utc().strftime(TIME_FORMAT))
    try:
        write_link(args.link, front, found["draft"], found["payload"], note="Created. The read-back had not been done when this was written.")
    except OSError:
        raise NeedsLooking("the story was created as %s (issue id %s) and the link file COULD NOT BE WRITTEN. Write these "
                           "two values down now. Do not create it again" % (body["key"], body["id"]))
    say("Written to the link file: the key %s and the issue id %s." % (body["key"], body["id"]))
    record["state"] = "written"
    save_json(record_path, record)
    return finish(args, conn, front, found["draft"], found["payload"])


def finish(args, conn, front, draft, payload):
    """Read the created story back by its id, compare it with the payload, and record both."""
    story = read_story(conn, front["jira_id"])
    if story is None:
        raise NeedsLooking("the story with issue id %s was created and cannot be read back: Jira answered 404" % front["jira_id"])
    rows, good, extras = compare(payload, story)
    front.update(compared_at=now_utc().strftime(TIME_FORMAT),
                 comparison="every field the payload sent reads back the same" if good else
                 "NOT ALL THE SAME: " + ", ".join(field for field, _, _, verdict in rows if "DIFFERENT" in verdict))
    if story["key"] != front["jira_key"]:
        front["earlier_keys"] = front["earlier_keys"] + [front["jira_key"]]
        front["jira_key"] = story["key"]
    write_link(args.link, front, draft, payload, rows, extras)
    say("")
    say("READ BACK from Jira by issue id %s, and compared with the payload field for field:" % front["jira_id"])
    for field, sent, back, verdict in rows:
        say("  %-18s sent %s" % (field, sent))
        say("  %-18s read %s: %s" % ("", back, verdict.replace("**", "")))
    say("Result: %s." % front["comparison"])
    say("Fields Jira set that the payload did not send:")
    for field, name, value in extras["shown"]:
        say("  %-18s %-13s %s" % (field, name, value))
    if extras["others"]:
        say("  and %d more that hold a value: %s" % (len(extras["others"]), ", ".join(extras["others"])))
    say("")
    say("The link file %s now holds the key, the issue id and this comparison." % index.place(os.path.abspath(args.link)))
    result = ["Issue key: %s" % front["jira_key"],
              "Identifier of what was created: Jira issue id %s (this identifies the story; a key can change)" % front["jira_id"],
              "Target project: %s (project id %s), on the sandbox allowlist" % (front["project_key"], front["project_id"]),
              "Jira site: %s, site fingerprint %s" % (SITE_MARK, front["site_fingerprint"]),
              "Created at: %s" % front["created_at"],
              "Confirmed by: %s, at %s" % (front["confirmed_by"], front["confirmed_at"]),
              "Preview: fingerprint %s" % front["preview_fingerprint"][:12],
              "Payload: SHA-256 %s" % front["payload_sha256"],
              "Marker label: %s" % front["marker"],
              "Read back and compared at %s: %s" % (front["compared_at"], front["comparison"]),
              "Local link: %s" % index.place(os.path.abspath(args.link))]
    say("")
    say("RESULT RECORD")
    for line in result:
        say("  " + line)
    if getattr(args, "result", None):
        os.makedirs(os.path.dirname(os.path.abspath(args.result)), exist_ok=True)
        with open(args.result, "w", encoding="utf-8") as f:
            f.write(("\n".join(["# Result record: one Jira story created", ""] + ["- " + line for line in result]) + "\n").replace(conn.host, SITE_MARK))
        say("")
        say("The result record was also saved as Markdown where --result said.")
    say("")
    requests_line(conn)
    if not good:
        raise NeedsLooking("the story exists as %s and does not read back as it was sent. A person needs to look at it"
                           % front["jira_key"])
    return 0


# ---------------------------------------------------------------- verify and reconcile


def linked_draft(link_path, front):
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(link_path)), str(front.get("draft"))))
    try:
        return pv.read_draft(path)
    except Refused:
        raise Refused("the draft the link file names, %s, could not be read" % json.dumps(front.get("draft")))


def cmd_verify(args, conn):
    front, payload = read_link(args.link)
    if front is None:
        raise Refused("there is no link file at the path given, so there is nothing to verify")
    if front["state"] != CREATED or not pv.ident(front.get("jira_id")):
        raise Refused("the link file says a create was sent and its result was never recorded. Run the reconcile command")
    if pv.site_fingerprint(conn.host) != front.get("site_fingerprint"):
        raise Refused("this is not the Jira site the link file was made against")
    story = read_story(conn, front["jira_id"])
    if story is None:
        raise Refused("Jira answered 404 for issue id %s. The story has been deleted, or this identity may not see it. "
                      "The link file is left as it is" % front["jira_id"])
    say("VERIFY. Reads Jira and writes nothing to it.")
    say("Link file: %s" % index.place(os.path.abspath(args.link)))
    say("Matched to Jira by issue id %s: found." % front["jira_id"])
    if story["key"] != front["jira_key"]:
        say("The key has CHANGED in Jira: the link file recorded %s and the story is now %s. It is the same story, by its"
            % (front["jira_key"], story["key"]))
        say("issue id. The link file is updated with the new key, and keeps the earlier one.")
    else:
        say("The key in Jira is %s, as the link file records." % story["key"])
    marked = marker_search(conn, {"id": front["project_id"]}, front["marker"])
    if marked == [front["jira_id"]]:
        say("Asked of Jira for the marker %s: exactly one story carries it, and it is this one. So reconcile would" % front["marker"])
        say("have found this story had its key never been recorded.")
    else:
        say("Asked of Jira for the marker %s: %d stor%s found%s. The marker does NOT lead to this story alone."
            % (front["marker"], len(marked), "y" if len(marked) == 1 else "ies", " (issue id %s)" % ", ".join(marked) if marked else ""))
    args.result = None
    return finish(args, conn, front, linked_draft(args.link, front), payload)


def cmd_reconcile(args, conn):
    front, payload = read_link(args.link)
    if front is None:
        raise Refused("there is no link file at the path given, so there is nothing to reconcile")
    if front["state"] != SENT:
        raise Refused("the link file already records the story %s (issue id %s). There is nothing to reconcile"
                      % (front.get("jira_key"), front.get("jira_id")))
    if pv.site_fingerprint(conn.host) != front.get("site_fingerprint"):
        raise Refused("this is not the Jira site the link file was made against")
    found = marker_search(conn, {"id": front["project_id"]}, front["marker"])
    say("RECONCILE. Reads Jira and writes nothing to it.")
    say("The link file says a create was sent and its result was never recorded.")
    say("Asked of Jira: stories in project %s carrying the marker %s. Found: %d." % (front["project_key"], front["marker"], len(found)))
    if not found:
        say("")
        say("NOT FOUND. No story carries the marker, so as far as Jira's search shows the story was not created.")
        say("Jira's search can lag a few seconds behind a create, so this is not proof. Nothing has been created or")
        say("changed, and the link file is left as it is. Wait a minute and run reconcile again. If it is still not")
        say("found, a person decides: delete the link file by hand, then make a new preview.")
        return 1
    if len(found) > 1:
        raise Refused("%d stories carry the marker %s (issue ids %s). That should not be possible, so nothing is linked. "
                      "A person needs to look" % (len(found), front["marker"], ", ".join(found)))
    story = read_story(conn, found[0])
    if story is None:
        raise Refused("the story with the marker could not be read (issue id %s)" % found[0])
    say("FOUND exactly one: %s, issue id %s. It is linked now." % (story["key"], story["id"]))
    front.update(state=CREATED, jira_id=story["id"], jira_key=story["key"],
                 created_at="not recorded: the create's answer was lost. Linked by reconcile at %s" % now_utc().strftime(TIME_FORMAT))
    draft = linked_draft(args.link, front)
    write_link(args.link, front, draft, payload, note="Linked by reconcile. The read-back had not been done when this was written.")
    for name in sorted(os.listdir(os.path.join(args.state, "create-story-previews"))) if os.path.isdir(os.path.join(args.state, "create-story-previews")) else []:
        path = os.path.join(args.state, "create-story-previews", name)
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        if record.get("fingerprint") == front["preview_fingerprint"]:
            record["state"] = "written"
            save_json(path, record)
    return finish(args, conn, front, draft, payload)


# ---------------------------------------------------------------- running


def minutes_forward(text):
    if not text.isascii() or not text.isdigit() or len(text) > 6:
        raise argparse.ArgumentTypeError("must be a whole number of minutes, 0 or more")
    return int(text)


COMMANDS = {"preview": cmd_preview, "confirm": cmd_confirm, "verify": cmd_verify, "reconcile": cmd_reconcile}


def run(args, conn):
    """One command, start to finish. Returns the exit code; what it said is in LINES."""
    try:
        return COMMANDS[args.command](args, conn)
    except Refused as refusal:
        say("")
        say("REFUSED: %s." % refusal)
        say("Nothing has been written to Jira.")
        return 1
    except NeedsLooking as problem:
        say("")
        say("A PERSON NEEDS TO LOOK: %s." % problem)
        say("Do not create this story again. The link file records where things stand.")
        return 2


def load_fake():
    """This skill's fake Jira, loaded from its file so that it cannot be mistaken for another skill's."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("create_story_fake_jira", os.path.join(HERE, "fake_jira.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview, confirm, verify and reconcile the creation of one Jira story.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        sub = commands.add_parser(command)
        sub.add_argument("--source", choices=("live", "fake"), required=True)
        sub.add_argument("--link", required=True, help="the link file: the local record of the story")
        sub.add_argument("--log", help="also save the output here, with the site's address removed")
        if command in ("preview", "confirm"):
            sub.add_argument("--draft", required=True, help="the story draft")
            sub.add_argument("--allowlist", required=True, help="the sandbox allowlist")
            sub.add_argument("--catalog", required=True, help="the local catalog folder to search for duplicates")
            sub.add_argument("--today", help="the date duplicate ages are counted to, YYYY-MM-DD")
        if command in ("confirm", "reconcile"):
            sub.add_argument("--result", help="save the result record here, as Markdown")
        sub.add_argument("--state", required=command != "verify", help="the folder where previews are kept")
        if command == "confirm":
            sub.add_argument("--fingerprint")
            sub.add_argument("--confirmed-by")
            sub.add_argument("--pretend-minutes-later", type=minutes_forward, default=0, metavar="N",
                             help="tests only: move 'now' forward by N minutes")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets_found, conn, fake, fake_path = [], None, None, None
    try:
        if getattr(args, "today", None):
            try:
                args.today = datetime.date.fromisoformat(args.today)
            except ValueError:
                raise Refused("--today must be a date written YYYY-MM-DD")
        elif hasattr(args, "today"):
            args.today = datetime.date.today()
        if args.source == "fake":
            fake_jira = load_fake()
            fake_path = os.path.join(args.state or os.path.dirname(os.path.abspath(args.link)), "fake-jira.json")
            fake = fake_jira.FakeJira.open(fake_path)
            conn = Connection(fake.get, fake.post if args.command == "confirm" else None, urllib.parse.urlparse(fake_jira.SITE).hostname)
        else:
            conn, secrets_found = make_live(args.command == "confirm")
        code = run(args, conn)
    except Refused as refusal:
        say("REFUSED: %s." % refusal)
        say("Nothing has been written to Jira.")
        code = 1
    if fake is not None:
        fake.save(fake_path)
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets_found):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 2 if conn and any(method == "POST" for method, _ in conn.sent) else 1
    print(text)
    if secrets_found:
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
    sys.exit(main())
