#!/usr/bin/env python3
"""Previews the creation of one Jira story from a local draft. It writes nothing to Jira.

    preview.py --source live|fake --draft DRAFT.md --allowlist FILE --catalog FOLDER --state FOLDER
               [--payload-out FILE.md] [--log FILE] [--today YYYY-MM-DD]

It reads a draft, asks Jira what the project requires, and shows exactly what
a later create would send. Then it stops. This file has no code that sends a
write: every request it makes is a GET.

The draft is a Markdown file. Between two lines of three dashes are the
story's fields, one per line, a name, a colon and a JSON value:

    format: "jira-story-draft/1"
    project: "RPT"                    the project's key
    issuetype: "Story"                the issue type's name
    summary: "..."
    labels: ["a", "b"]                optional
    components: ["Reports"]           optional, by name
    priority: "High"                  optional, by name
    parent: "RPT-1"                   optional, the parent's key
    duedate: "2027-01-15"             optional
    custom: {"Team": "Data"}          optional, single-choice custom fields by name

Under the heading "## Description" is the description: paragraphs, and lists
whose lines start with "- ". Under "## Sources" is one line per citation:

    - summary: sources/notes.md line 7: "the words quoted"
    - description: sources/notes.md lines 8-9: "more words"
    - custom Team: sources/notes.md line 11: "the data team"

Every field of content in the draft needs at least one citation, and every
citation is checked: the file must be under participant/context/, and the
quoted words must be on the lines named.

What the preview does, in order. A refusal at any step stops it, and no
payload is shown or saved.

  1. reads the draft and checks its citations;
  2. asks Jira for the project, and checks it is on the sandbox allowlist;
  3. takes a snapshot of the project's stories, to compare at the end;
  4. asks Jira whether this identity may create stories in the project;
  5. asks Jira which fields the project takes for this issue type, which are
     required, which have defaults and which values each allows;
  6. checks the draft against that. A required field that is missing and has
     no default is a refusal that names the field;
  7. builds the payload, once, with build_payload;
  8. searches the local catalog for likely duplicates of the draft;
  9. takes the snapshot again and shows everything.

A required field that the draft leaves out and Jira has a default for is not
a refusal. It is listed as left to Jira, with the default Jira reports.

The payload is built in one place, build_payload, and turned into the bytes
that would be sent in one place, body_bytes. The preview shows the payload,
its SHA-256 and its length, and saves all three in the state folder with a
fingerprint, for a later write to check and send.

The site's address is shown on screen and removed from anything saved. For a
live run the connection comes from the environment variables JIRA_BASE_URL,
JIRA_EMAIL and JIRA_API_TOKEN. None is stored, and the output is searched for
them before it is shown.

Text from Jira and from stories is other people's writing. Names and values
from Jira are shown quoted. No story's title or description from Jira is
printed, and nothing in any of it is acted on.

Exit codes: 0 a preview was made; 1 refused, with the reason.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "jira-duplicate-search"))
import search  # noqa: E402
from search import index  # noqa: E402

DRAFT_FORMAT = "jira-story-draft/1"
DRAFT_NAMES = ("format", "project", "issuetype", "summary", "labels", "components", "priority", "parent", "duedate", "custom")
CONTENT = ("summary", "description", "labels", "components", "priority", "parent", "duedate")
CONTEXT = os.path.join(ROOT, "participant", "context")
LIMIT_MINUTES = 15
TIME_FORMAT = "%Y-%m-%d %H:%M:%S UTC"
SITE_MARK = "[site address removed]"
KEY = re.compile(r"[A-Z][A-Z0-9_]{1,19}")
ISSUE_KEY = re.compile(r"[A-Z][A-Z0-9_]{1,19}-[0-9]{1,9}")
LABEL = re.compile(r"[a-z0-9][a-z0-9-]{0,49}")
SOURCE = re.compile(r'- (?P<what>[^:]+): (?P<file>\S+) lines? (?P<first>\d+)(?:-(?P<last>\d+))?: "(?P<quote>.+)"')
MAX_PAGES = 20

LINES = []


class Refused(Exception):
    """No preview is made. The message is the reason."""


def say(text=""):
    LINES.append(text)


# ---------------------------------------------------------------- the connection: reading only


class Connection:
    """Every request goes through here and is written down. There is only get."""

    def __init__(self, get, host):
        self._get, self.host, self.sent = get, host, []

    def get(self, path, params=None):
        self.sent.append(("GET", path))
        try:
            return self._get(path, params)
        except (OSError, TimeoutError) as err:
            raise Refused("could not reach Jira (%s)" % type(getattr(err, "reason", err)).__name__)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def make_live():
    base = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email, token = os.environ.get("JIRA_EMAIL", ""), os.environ.get("JIRA_API_TOKEN", "")
    for name, value in (("JIRA_BASE_URL", base), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)):
        if not value:
            raise Refused("the environment variable %s is not set" % name)
    if not base.startswith("https://"):
        raise Refused("JIRA_BASE_URL must start with https://")
    encoded = base64.b64encode(("%s:%s" % (email, token)).encode("utf-8")).decode("ascii")
    opener = urllib.request.build_opener(NoRedirect)

    def get(path, params=None):
        url = base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        request = urllib.request.Request(url, method="GET")
        request.add_header("Authorization", "Basic " + encoded)
        request.add_header("Accept", "application/json")
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

    return Connection(get, urllib.parse.urlparse(base).hostname or ""), [token, email, encoded]


def site_fingerprint(host):
    return hashlib.sha256(host.lower().encode("utf-8")).hexdigest()[:16]


def load_allowlist(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise Refused("there is no sandbox allowlist at the path given")
    except ValueError:
        raise Refused("the sandbox allowlist is not JSON")
    entries = data.get("sandbox_projects") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise Refused("the sandbox allowlist must hold a list named sandbox_projects")
    allowed = set()
    for entry in entries:
        site, project = (entry or {}).get("site_fingerprint"), (entry or {}).get("project_id")
        if not (isinstance(site, str) and re.fullmatch(r"[0-9a-f]{16}", site) and isinstance(project, str) and project.isdigit()):
            raise Refused("an entry in the sandbox allowlist is not a site fingerprint and a project id")
        allowed.add((site, project))
    return allowed


# ---------------------------------------------------------------- the draft


def read_draft(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Refused("the draft could not be read")
    front = index.front_matter(text)
    if front is None or front.get("format") != DRAFT_FORMAT:
        raise Refused("the file is not a story draft: its format is not %s" % DRAFT_FORMAT)
    for name, value in front.items():
        if name not in DRAFT_NAMES:
            raise Refused("the draft has a field this preview does not support: %s. It supports %s"
                          % (json.dumps(name[:40]), ", ".join(DRAFT_NAMES[1:])))
        if value is index.Unreadable:
            raise Refused("the draft's value for %s is not JSON" % name)

    def text_of(name, pattern=None, required=False):
        value = front.get(name)
        if value is None:
            if required:
                raise Refused("the draft has no %s" % name)
            return None
        if not isinstance(value, str) or not value.strip() or "\n" in value or (pattern and not pattern.fullmatch(value)):
            raise Refused("the draft's %s is not usable" % name)
        return value

    def list_of(name):
        value = front.get(name)
        if value is None:
            return None
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value) \
                or len(set(value)) != len(value):
            raise Refused("the draft's %s must be a list of different names" % name)
        return value
    draft = {"path": os.path.abspath(path),
             "project": text_of("project", KEY, required=True), "issuetype": text_of("issuetype", required=True),
             "summary": text_of("summary", required=True), "labels": list_of("labels"), "components": list_of("components"),
             "priority": text_of("priority"), "parent": text_of("parent", ISSUE_KEY), "duedate": text_of("duedate")}
    if len(draft["summary"]) > 255:
        raise Refused("the draft's summary is longer than 255 characters")
    for label in draft["labels"] or []:
        if not LABEL.fullmatch(label):
            raise Refused("the draft's label %s is not allowed: lowercase letters, digits and hyphens only" % json.dumps(label[:60]))
    if draft["duedate"]:
        try:
            if not re.fullmatch(r"\d{4}-\d\d-\d\d", draft["duedate"]):
                raise ValueError
            datetime.date.fromisoformat(draft["duedate"])
        except ValueError:
            raise Refused("the draft's duedate is not a real date written YYYY-MM-DD")
    custom = front.get("custom") or {}
    if not isinstance(custom, dict) or not all(isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()
                                               for k, v in custom.items()):
        raise Refused("the draft's custom fields must be names with one chosen value each")
    draft["custom"] = custom

    body = text.split("\n## Description\n", 1)[1] if "\n## Description\n" in text else ""
    described, _, cited = body.partition("\n## Sources\n")
    draft["description"] = described.strip()
    draft["sources"] = []
    for line in cited.split("\n"):
        if not line.strip():
            continue
        match = SOURCE.fullmatch(line.strip())
        if not match:
            raise Refused("a line under Sources could not be read as a citation: %s" % json.dumps(line.strip()[:60]))
        first = int(match.group("first"))
        draft["sources"].append({"what": match.group("what").strip(), "file": match.group("file"), "first": first,
                                 "last": int(match.group("last") or first), "quote": match.group("quote")})
    return draft


def content_names(draft):
    """The pieces of content in the draft, by the name a citation uses for them."""
    names = [name for name in CONTENT if draft[name]]
    return names + ["custom %s" % name for name in draft["custom"]]


def check_sources(draft):
    """Every piece of content is cited, and every citation is true. Returns the checked citations."""
    needed = content_names(draft)
    for source in draft["sources"]:
        if source["what"] not in needed:
            raise Refused("a citation is for %s, which is not in the draft" % json.dumps(source["what"][:40]))
        path = os.path.realpath(os.path.join(os.path.dirname(draft["path"]), source["file"]))
        if os.path.commonpath([path, os.path.realpath(CONTEXT)]) != os.path.realpath(CONTEXT):
            raise Refused("the citation for %s points outside participant/context/" % source["what"])
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
        except (OSError, UnicodeDecodeError):
            raise Refused("the source cited for %s could not be read: %s" % (source["what"], source["file"]))
        if not 1 <= source["first"] <= source["last"] <= len(lines):
            raise Refused("the citation for %s names lines that %s does not have" % (source["what"], source["file"]))
        there = " ".join(" ".join(lines[source["first"] - 1:source["last"]]).split())
        if " ".join(source["quote"].split()) not in there:
            raise Refused("the citation for %s is not true: the quoted words are not at %s line %d"
                          % (source["what"], source["file"], source["first"]))
    missing = [name for name in needed if not any(source["what"] == name for source in draft["sources"])]
    if missing:
        raise Refused("the draft gives no source for: %s. Every piece of content needs a citation" % ", ".join(missing))
    return draft["sources"]


def description_to_adf(text):
    """The description as Atlassian Document Format: paragraphs and plain bullet lists. None if there is none."""
    blocks = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if all(line.startswith("- ") for line in lines):
            blocks.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": line[2:].strip()}]}]}
                for line in lines]})
        else:
            blocks.append({"type": "paragraph", "content": [{"type": "text", "text": " ".join(lines)}]})
    return {"type": "doc", "version": 1, "content": blocks} if blocks else None


# ---------------------------------------------------------------- reading Jira


def ident(value):
    return isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20


def paged(conn, path, name, what):
    """Every item of a list Jira gives in pages with startAt and total."""
    items, start = [], 0
    for _ in range(MAX_PAGES):
        status, _, body = conn.get(path, {"startAt": start, "maxResults": 50})
        page = body.get(name) if status == 200 else None
        if not isinstance(page, list):
            raise Refused("Jira did not give %s (status %d), so nothing is assumed" % (what, status))
        items += [item for item in page if isinstance(item, dict)]
        start += len(page)
        if not page or (isinstance(body.get("total"), int) and start >= body["total"]):
            return items
    raise Refused("%s did not end after %d pages" % (what, MAX_PAGES))


def read_project(conn, key):
    status, _, body = conn.get("/rest/api/3/project/%s" % key)
    if status == 401:
        raise Refused("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
    if status == 404:
        raise Refused("Jira answered 404 for the project %s. It does not exist, or this identity is not permitted to "
                      "see it. Jira gives one answer for both" % key)
    if status != 200 or not ident(body.get("id")) or not isinstance(body.get("key"), str) or not KEY.fullmatch(body["key"]):
        raise Refused("Jira's answer for the project could not be used (status %d)" % status)
    return {"id": body["id"], "key": body["key"]}


def read_permissions(conn, project_id):
    names = ("BROWSE_PROJECTS", "CREATE_ISSUES")
    status, _, body = conn.get("/rest/api/3/mypermissions", {"projectId": project_id, "permissions": ",".join(names)})
    found = body.get("permissions") if status == 200 else None
    if not isinstance(found, dict):
        raise Refused("Jira did not answer the permission check (status %d), so nothing is assumed" % status)
    return {name: (found.get(name) or {}).get("havePermission") is True for name in names}


def read_issue_type(conn, project, name):
    kinds = paged(conn, "/rest/api/3/issue/createmeta/%s/issuetypes" % project["id"], "issueTypes", "the project's issue types")
    matches = [kind for kind in kinds if kind.get("name") == name and ident(kind.get("id"))]
    if len(matches) != 1:
        raise Refused("the issue type %s is not one Jira offers for creating in %s. It offers: %s"
                      % (json.dumps(name), project["key"],
                         ", ".join(json.dumps(str(kind.get("name"))) for kind in kinds) or "none"))
    return {"id": matches[0]["id"], "name": name}


def read_fields(conn, project, kind):
    fields = paged(conn, "/rest/api/3/issue/createmeta/%s/issuetypes/%s" % (project["id"], kind["id"]), "fields",
                   "the fields of the issue type")
    meta = {}
    for item in fields:
        field_id = item.get("fieldId") or item.get("key")
        if isinstance(field_id, str) and re.fullmatch(r"[A-Za-z0-9_]{1,60}", field_id) and isinstance(item.get("name"), str):
            meta[field_id] = item
    if not meta:
        raise Refused("Jira lists no fields for creating a %s in %s. Jira gives that list only to an identity that may "
                      "create there" % (json.dumps(kind["name"]), project["key"]))
    return meta


def read_parent(conn, key, project):
    status, _, body = conn.get("/rest/api/3/issue/%s" % key, {"fields": "project,issuetype"})
    fields = body.get("fields") if status == 200 else None
    if not isinstance(fields, dict) or not ident(body.get("id")):
        raise Refused("the parent %s could not be read from Jira (status %d). It does not exist or cannot be seen" % (key, status))
    if (fields.get("project") or {}).get("id") != project["id"]:
        raise Refused("the parent %s is in another project" % key)
    return body["id"]


def snapshot(conn, project):
    """How many stories the project holds, and one code for their ids and last-update times."""
    seen, token = [], None
    for _ in range(MAX_PAGES):
        params = {"jql": "project = %s ORDER BY created ASC" % project["id"], "fields": "updated", "maxResults": 100}
        if token:
            params["nextPageToken"] = token
        status, _, body = conn.get("/rest/api/3/search/jql", params)
        issues = body.get("issues") if status == 200 else None
        if not isinstance(issues, list):
            raise Refused("Jira did not list the project's stories (status %d), so 'unchanged' could not be checked" % status)
        seen += [[str(item.get("id")), str((item.get("fields") or {}).get("updated"))] for item in issues if isinstance(item, dict)]
        token = body.get("nextPageToken")
        if not token or not issues:
            text = json.dumps(sorted(seen), separators=(",", ":"))
            return len(seen), hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    raise Refused("the project has more stories than this preview reads to check 'unchanged'")


# ---------------------------------------------------------------- the payload


def named(values, key, wanted, what):
    """The one allowed value whose `key` is `wanted`."""
    usable = [value for value in values or [] if isinstance(value, dict) and ident(value.get("id")) and isinstance(value.get(key), str)]
    matches = [value for value in usable if value[key] == wanted]
    if len(matches) != 1:
        raise Refused("%s %s is not one of the values Jira allows: %s"
                      % (what, json.dumps(wanted), ", ".join(json.dumps(value[key]) for value in usable) or "Jira lists none"))
    return matches[0]["id"]


def kind_of(field):
    schema = field.get("schema") if isinstance(field.get("schema"), dict) else {}
    return schema.get("type"), schema.get("items")


def expect(meta, field_id, name, kinds):
    """The field must be one Jira takes on create, and of the kind this preview builds."""
    if field_id not in meta:
        raise Refused("Jira does not list %s as a field that can be set when creating this issue type in this project" % name)
    if kind_of(meta[field_id]) not in kinds:
        raise Refused("Jira describes %s as %s, which is not what this preview builds for it" % (name, json.dumps(kind_of(meta[field_id]))))


def default_text(field):
    if "defaultValue" not in field or field["defaultValue"] is None:
        return "Jira says it has a default and does not say what it is"
    value = field["defaultValue"]
    if isinstance(value, dict):
        for key in ("name", "value", "displayName", "key"):
            if isinstance(value.get(key), str):
                return "Jira's default is %s" % json.dumps(value[key])
    if isinstance(value, list):
        return "Jira's default is a list of %d" % len(value)
    return "Jira's default is %s" % json.dumps(value)[:80]


def build_payload(draft, project, kind, meta, parent_id=None):
    """The one place a payload is made. Returns (payload, rows, left to Jira, not set).

    rows are (field id, Jira's name for it, the value as shown) for each field in the payload.
    """
    fields, rows = {}, []

    def put(field_id, value, shown):
        fields[field_id] = value
        rows.append((field_id, meta[field_id]["name"] if field_id in meta else field_id, shown))
    put("project", {"id": project["id"]}, "%s (project id %s)" % (project["key"], project["id"]))
    put("issuetype", {"id": kind["id"]}, "%s (issue type id %s)" % (json.dumps(kind["name"]), kind["id"]))
    expect(meta, "summary", "summary", (("string", None),))
    put("summary", draft["summary"], json.dumps(draft["summary"]))
    adf = description_to_adf(draft["description"])
    if adf:
        expect(meta, "description", "description", (("string", None),))
        put("description", adf, "%d block(s) of Atlassian Document Format, shown in full in the payload" % len(adf["content"]))
    if draft["labels"]:
        expect(meta, "labels", "labels", (("array", "string"),))
        put("labels", list(draft["labels"]), json.dumps(draft["labels"]))
    if draft["components"]:
        expect(meta, "components", "components", (("array", "component"),))
        ids = [named(meta["components"].get("allowedValues"), "name", name, "component") for name in draft["components"]]
        put("components", [{"id": cid} for cid in ids],
            ", ".join("%s (id %s)" % (json.dumps(name), cid) for name, cid in zip(draft["components"], ids)))
    if draft["priority"]:
        expect(meta, "priority", "priority", (("priority", None),))
        pid = named(meta["priority"].get("allowedValues"), "name", draft["priority"], "priority")
        put("priority", {"id": pid}, "%s (id %s)" % (json.dumps(draft["priority"]), pid))
    if draft["parent"]:
        if "parent" not in meta:
            raise Refused("Jira does not list parent as a field that can be set when creating this issue type in this project")
        put("parent", {"key": draft["parent"]}, "%s (issue id %s)" % (draft["parent"], parent_id))
    if draft["duedate"]:
        expect(meta, "duedate", "duedate", (("date", None),))
        put("duedate", draft["duedate"], draft["duedate"])
    for name in sorted(draft["custom"]):
        found = [fid for fid, field in meta.items() if fid.startswith("customfield_") and field["name"] == name]
        if len(found) != 1:
            raise Refused("the custom field %s is not one Jira lists for creating this issue type in this project" % json.dumps(name))
        if kind_of(meta[found[0]]) != ("option", None):
            raise Refused("the custom field %s is not a single-choice field. This preview sets no other kind" % json.dumps(name))
        oid = named(meta[found[0]].get("allowedValues"), "value", draft["custom"][name], "the value of %s" % json.dumps(name))
        put(found[0], {"id": oid}, "%s (option id %s)" % (json.dumps(draft["custom"][name]), oid))

    missing, left, unset = [], [], []
    for field_id in sorted(meta):
        field = meta[field_id]
        if field_id in fields:
            continue
        label = "%s (%s)" % (json.dumps(field["name"]), field_id)
        if field.get("required") is True and field.get("hasDefaultValue") is not True:
            missing.append(label)
        elif field.get("required") is True:
            left.append((field_id, field["name"], default_text(field)))
        else:
            unset.append((field_id, field["name"], default_text(field) if field.get("hasDefaultValue") is True else "no default reported"))
    if missing:
        raise Refused("the draft is missing %d field%s that Jira requires for a %s in %s and gives no default for: %s. "
                      "Add %s to the draft, with a source" % (len(missing), "" if len(missing) == 1 else "s", json.dumps(kind["name"]),
                                                            project["key"], ", ".join(missing), "it" if len(missing) == 1 else "them"))
    return {"fields": fields}, rows, left, unset


def body_bytes(payload):
    """The exact bytes of the request body. The one place a payload becomes bytes."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


# ---------------------------------------------------------------- duplicates


def find_duplicates(draft, catalog, today):
    proposal = {"title": draft["summary"], "description": draft["description"], "labels": draft["labels"] or [],
                "components": draft["components"] or [], "parent": draft["parent"]}
    try:
        result = search.search(proposal, catalog, today)
        with open(os.path.join(catalog, "catalog.json"), encoding="utf-8") as f:
            keys = [entry.get("key") or "" for entry in json.load(f)["entries"]]
        return proposal, result, keys
    except search.Stop as stop:
        raise Refused("the duplicate search could not run, so no preview is made: %s" % stop)
    except OSError:
        raise Refused("the duplicate search could not read the catalog at %s, so no preview is made" % index.place(catalog))


def coverage(keys, project, in_jira):
    """How many of the project's stories the local catalog holds, against how many Jira holds."""
    local = sum(1 for key in keys if key.startswith(project["key"] + "-"))
    if local < in_jira:
        return local, ("WARNING: the catalog holds %d of project %s's stories and Jira holds %d. %d in Jira have NOT been "
                       "searched. Save them locally and rebuild the catalog for a complete search"
                       % (local, project["key"], in_jira, in_jira - local))
    if local > in_jira:
        return local, ("the catalog holds %d of project %s's stories and Jira holds %d. Some in the catalog are no longer "
                       "in the project" % (local, project["key"], in_jira))
    return local, "the catalog holds %d of project %s's stories and Jira holds %d: the counts agree" % (local, project["key"], in_jira)


def duplicate_lines(proposal, result, catalog, covered):
    out = ["Duplicate search: the local catalog %s, %s, searched with the jira-duplicate-search skill."
           % (index.place(catalog), search.count(result["searched"], "story").replace("storys", "stories")),
           "  Coverage: %s." % covered]
    if not result["candidates"]:
        out.append("  Result: NONE. No story in the catalog matches this draft on three or more signals.")
    else:
        out.append("  Result: %d candidate%s." % (len(result["candidates"]), "" if len(result["candidates"]) == 1 else "s"))
    for c in result["candidates"]:
        out.append("  %s (issue id %s): confidence %s, %d of 11 points, matched on %s. Recommendation: %s."
                   % (c["entry"]["key"] or index.MISSING, c["entry"]["id"], c["level"].upper(), c["score"], ", ".join(c["matched"]),
                      c["advice"].upper()))
    for c in result["dismissed"]:
        out.append("  Looked at and not reported: %s (issue id %s), matched on %s only."
                   % (c["entry"]["key"] or index.MISSING, c["entry"]["id"], " and ".join(c["matched"])))
    out.append("  Overall recommendation: %s. A person decides. The catalog is a local copy: a story created in Jira"
               % result["overall"].upper())
    out.append("  since the records were saved is not in it.")
    if result["candidates"]:
        c = result["candidates"][0]
        story = c["story"]
        mine, theirs = search.words(proposal["description"]), search.words(story["description"])
        out.append("  How the draft differs from the nearest, %s:" % (c["entry"]["key"] or index.MISSING))
        for name, a, b in (("labels", proposal["labels"], story["labels"]), ("components", proposal["components"], story["components"])):
            out.append("    %-11s only in the draft: %s. only in the story: %s. in both: %s."
                       % (name + ":", ", ".join(sorted(set(a) - set(b))) or "none", ", ".join(sorted(set(b) - set(a))) or "none",
                          ", ".join(sorted(set(a) & set(b))) or "none"))
        out.append("    parent:     the draft has %s, the story has %s." % (proposal["parent"] or "none", story["parent_key"] or "none"))
        out.append("    description words only in the draft (%d): %s" % (len(mine - theirs), ", ".join(sorted(mine - theirs)[:14]) or "none"))
        out.append("    description words only in the story: %d. in both: %d." % (len(theirs - mine), len(mine & theirs)))
    return out


# ---------------------------------------------------------------- the preview


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)


def cmd_preview(args, conn):
    draft = read_draft(args.draft)
    sources = check_sources(draft)
    allowed = load_allowlist(args.allowlist)
    site = site_fingerprint(conn.host)
    project = read_project(conn, draft["project"])
    if (site, project["id"]) not in allowed:
        raise Refused("project %s (project id %s) on the Jira site with fingerprint %s is not on the sandbox allowlist "
                      "(%s). A story could not be created there, so no preview is made" % (project["key"], project["id"], site, args.allowlist))
    before = snapshot(conn, project)
    status, _, me = conn.get("/rest/api/3/myself")
    if status != 200 or not isinstance(me.get("accountId"), str):
        raise Refused("Jira did not say which identity this is (status %d)" % status)
    permissions = read_permissions(conn, project["id"])
    if not permissions["BROWSE_PROJECTS"] or not permissions["CREATE_ISSUES"]:
        raise Refused("Jira says this identity may not create stories in %s (CREATE_ISSUES: %s)"
                      % (project["key"], "yes" if permissions["CREATE_ISSUES"] else "no"))
    kind = read_issue_type(conn, project, draft["issuetype"])
    meta = read_fields(conn, project, kind)
    parent_id = read_parent(conn, draft["parent"], project) if draft["parent"] else None
    payload, rows, left, unset = build_payload(draft, project, kind, meta, parent_id)
    body = body_bytes(payload)
    digest = hashlib.sha256(body).hexdigest()
    proposal, result, keys = find_duplicates(draft, os.path.abspath(args.catalog), args.today)
    after = snapshot(conn, project)
    local, covered = coverage(keys, project, after[0])
    if after != before:
        raise Refused("the project's stories changed in Jira while the preview was being made. Preview again")

    say("PREVIEW OF A NEW STORY. Nothing has been written to Jira.")
    say("")
    say("Jira site:   https://%s  (site fingerprint %s)" % (conn.host, site))
    say("Project:     %s (project id %s). On the sandbox allowlist: yes." % (project["key"], project["id"]))
    say("Issue type:  %s (issue type id %s)" % (json.dumps(kind["name"]), kind["id"]))
    say("Draft:       %s" % index.place(draft["path"]))
    say("Would be sent, by a later write and not by this preview: POST /rest/api/3/issue")
    say("")
    say("EVERY FIELD Jira lists for creating a %s in %s: %d." % (json.dumps(kind["name"]), project["key"], len(meta)))
    say("Set by the draft, %d:" % len(rows))
    for field_id, name, shown in rows:
        say("  %-18s %-13s %s" % (field_id, name, shown))
    say("Required by Jira, not in the draft, and LEFT TO JIRA because it has a default, %d:" % len(left))
    for field_id, name, default in left:
        say("  %-18s %-13s %s." % (field_id, name, default))
    if left:
        say("  Jira, not this draft, decides these. If a default is wrong for this story, set the field in the draft.")
    say("Optional, not in the draft, and not sent, %d:" % len(unset))
    for field_id, name, default in unset:
        say("  %-18s %-13s %s." % (field_id, name, default))
    say("Required by Jira with no default, and missing from the draft: none.")
    say("")
    say("THE EXACT PAYLOAD. This is the request body, not a summary of it:")
    for line in pretty(payload).split("\n"):
        say("  " + line)
    say("As sent it is the same data with no spaces or line breaks and its names in alphabetical order:")
    say("  %d bytes, SHA-256 %s" % (len(body), digest))
    say("")
    say("Sources for the content, each checked against the file: %d citations, all true." % len(sources))
    for source in sources:
        say("  %-12s %s line%s: %s" % (source["what"], source["file"],
                                      " %d" % source["first"] if source["first"] == source["last"] else "s %d-%d" % (source["first"], source["last"]),
                                      json.dumps(source["quote"])))
    say("")
    say("Permission check, asked of Jira for this project and this identity:")
    say("  may see the project    (BROWSE_PROJECTS): yes")
    say("  may create stories     (CREATE_ISSUES):   yes")
    say("  Jira gives the field list above only to an identity that may create here.")
    for line in duplicate_lines(proposal, result, os.path.abspath(args.catalog), covered):
        say(line)
    say("")
    say("What Jira cannot be asked: it has no way to try a create without making one, so this preview cannot")
    say("promise the create would be accepted. Jira's list of required fields does not cover rules in the")
    say("project's workflow or automation.")
    say("")
    say("Snapshot of the project's stories in Jira before the preview: %d stories, %s" % before)
    say("Snapshot of the project's stories in Jira after the preview:  %d stories, %s" % after)
    say("The two are the same. Jira is unchanged.")
    say("Requests sent to Jira: %d. Every one was a GET, which reads and cannot change anything." % len(conn.sent))
    for method, path in conn.sent:
        say("  %s %s" % (method, path))

    made = now_utc()
    made_at = made.strftime(TIME_FORMAT)
    record = {"made_at": made_at, "expires_at": (made + datetime.timedelta(minutes=LIMIT_MINUTES)).strftime(TIME_FORMAT),
              "site": site, "project": project, "issuetype": kind, "payload": payload, "payload_sha256": digest,
              "payload_bytes": len(body), "left_to_jira": [field_id for field_id, _, _ in left],
              "duplicates": {"overall": result["overall"], "stories_in_catalog": local, "stories_in_jira": after[0],
                             "candidates": [[c["entry"]["id"], c["level"], c["advice"]] for c in result["candidates"]]}}
    fingerprint = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    folder = os.path.join(args.state, "create-previews")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, fingerprint[:12] + ".json")
    if os.path.exists(path):
        raise Refused("a preview with this fingerprint was made a moment ago. Wait a second and preview again")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dict(record, fingerprint=fingerprint, state="open"), f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    say("")
    say("Fingerprint of this preview: %s" % fingerprint[:12])
    say("Made:    %s" % made_at)
    say("Expires: %s (%d minutes after it was made)" % (record["expires_at"], LIMIT_MINUTES))
    say("The payload, its SHA-256 and this fingerprint are saved in the state folder for a later write to check.")
    say("")
    say("Nothing has been written to Jira. This preview creates nothing, and has no way to.")

    if args.payload_out:
        write_payload_file(args.payload_out, conn, site, project, kind, draft, rows, left, unset, payload, body, digest, sources)
        say("The payload was also written, field by field, where --payload-out said.")
    return 0


def write_payload_file(path, conn, site, project, kind, draft, rows, left, unset, payload, body, digest, sources):
    cell = search.md
    out = ["# Payload preview: one new Jira story", "",
           "> Generated by `participant/skills/jira-create-story-preview/preview.py` from the draft",
           "> `%s`. Do not edit it by hand: change the draft and preview again." % index.place(draft["path"]),
           "> Nothing in this file has been sent to Jira.", "",
           "## Where it would go", "",
           "| | |", "|---|---|",
           "| Jira site | %s, site fingerprint `%s` |" % (SITE_MARK, site),
           "| Target project | %s (project id %s), on the sandbox allowlist |" % (project["key"], project["id"]),
           "| Issue type | %s (issue type id %s) |" % (cell(kind["name"]), kind["id"]),
           "| Request | `POST /rest/api/3/issue` |", "",
           "## Field by field", "",
           "| Field id | Jira's name for it | Value | Source |", "|---|---|---|---|"]
    for field_id, name, shown in rows:
        what = field_id if field_id in CONTENT else ("custom %s" % name if field_id.startswith("customfield_") else None)
        cited = "; ".join("%s line%s" % (s["file"], " %d" % s["first"] if s["first"] == s["last"] else "s %d-%d" % (s["first"], s["last"]))
                          for s in sources if s["what"] == what)
        out.append("| `%s` | %s | %s | %s |" % (field_id, cell(name), cell(shown), cell(cited) if cited else "the draft's target"))
    out += ["", "## Fields Jira requires that the draft leaves to Jira", ""]
    out += ["- `%s`, %s: %s." % (field_id, cell(name), cell(default)) for field_id, name, default in left] or ["None."]
    out += ["", "## Optional fields that are not sent", ""]
    out += ["- `%s`, %s: %s." % (field_id, cell(name), cell(default)) for field_id, name, default in unset] or ["None."]
    out += ["", "## The exact payload", "",
            "This is the request body. A later write sends this data and nothing else.", "",
            "```json", pretty(payload), "```", "",
            "As sent it is the same data with no spaces or line breaks and its names in alphabetical order:",
            "%d bytes, SHA-256 `%s`." % (len(body), digest)]
    text = ("\n".join(out) + "\n").replace(conn.host, SITE_MARK)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run(args, conn):
    try:
        return cmd_preview(args, conn)
    except Refused as refusal:
        del LINES[:]
        say("REFUSED: %s." % refusal)
        say("No preview was made, no payload was saved, and nothing has been written to Jira.")
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Preview the creation of one Jira story from a local draft. Writes nothing to Jira.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--draft", required=True, help="the story draft, a Markdown file")
    parser.add_argument("--allowlist", required=True, help="the sandbox allowlist")
    parser.add_argument("--catalog", required=True, help="the local catalog folder to search for duplicates")
    parser.add_argument("--state", required=True, help="the folder where previews are saved")
    parser.add_argument("--payload-out", help="also write the payload, field by field, to this Markdown file")
    parser.add_argument("--log", help="also save the output here, with the site's address removed")
    parser.add_argument("--today", help="the date duplicate ages are counted to, YYYY-MM-DD. The default is today")
    args = parser.parse_args(argv)
    del LINES[:]
    secrets, conn = [], None
    try:
        try:
            args.today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
        except ValueError:
            raise Refused("--today must be a date written YYYY-MM-DD")
        if args.source == "fake":
            import fake_jira
            conn = Connection(fake_jira.FakeJira().get, urllib.parse.urlparse(fake_jira.SITE).hostname)
        else:
            conn, secrets = make_live()
        code = run(args, conn)
    except Refused as refusal:
        say("REFUSED: %s." % refusal)
        say("No preview was made, no payload was saved, and nothing has been written to Jira.")
        code = 1
    text = "\n".join(LINES)
    if any(secret and secret in text for secret in secrets):
        print("STOPPED: a credential was found in the output, so the output was not shown or saved.")
        return 1
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
    sys.exit(main())
