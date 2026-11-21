#!/usr/bin/env python3
"""Read-only synchronization of the GitHub issues assigned to the signed-in user.

See SKILL.md in this folder for what it does and the rules it follows.

    sync.py --source fake [--fake-step N]      read the made-up GitHub in fake_github.py
    sync.py --source live --out FOLDER         read GitHub as the user the token belongs to

It only ever sends GET requests. There is no code here that creates, comments
on, labels, closes or reopens anything in GitHub.

Exit codes: 0 synchronized; 1 stopped, nothing written; 2 incomplete (rate-limited), nothing written.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API_HOST = "api.github.com"
PER_PAGE = 100             # the most GitHub returns for one request
MAX_WAITS = 3              # waits for one request before giving up
MAX_WAIT_SECONDS = 15      # the longest single wait
DEFAULT_WAIT_SECONDS = 10
MAX_REDIRECTS = 3
NODE_ID = re.compile(r"^[A-Za-z0-9_=-]{1,120}$")
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
SHA = re.compile(r"^[0-9a-f]{7,64}$")
UNREADABLE = (403, 404, 410, 451)
# The timeline entries that are kept. Everything else in a timeline is counted and left out.
MATERIAL = ("closed", "reopened", "assigned", "unassigned", "transferred", "renamed", "cross-referenced",
            "referenced", "connected", "disconnected")
WATCHED = ("full_name", "number", "title", "state", "state_reason", "author", "assignees", "labels", "milestone",
           "body", "created_at", "updated_at", "closed_at")
PULL_REQUEST_RULE = ("an item is a pull request when it carries a `pull_request` key, and only then. GitHub's list of "
                     "assigned items returns issues and pull requests together, and that key is how GitHub marks the "
                     "pull requests")


class Stop(Exception):
    """The run cannot go on. The message says why, in plain words."""


class RateLimited(Exception):
    """GitHub kept answering with a rate limit after every allowed wait."""


class Unreadable(Exception):
    """GitHub refused a request about one repository. The status is the first argument."""


def say(text):
    print("github-sync: " + text, flush=True)


def shown_path(path):
    """A path as it is printed: from the folder the skill was run in, so a home folder's name is not shown."""
    try:
        relative = os.path.relpath(path)
    except ValueError:
        return os.path.basename(path)
    return os.path.basename(path) if relative.startswith("..") else relative


def plural(count, word, many=None):
    return "%d %s" % (count, word if count == 1 else many or word + "s")


# ---------------------------------------------------------------- talking to GitHub


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None            # a redirect comes back as an answer, and the Client decides whether to follow it


def live_get(path, params=None):
    """One GET to api.github.com. Returns (status, headers, body).

    The token comes from the environment and goes in a request header. It is
    never part of an address, and it is never printed, returned or written.
    """
    url = "https://%s%s" % (API_HOST, path)
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, method="GET")
    request.add_header("Authorization", "Bearer %s" % os.environ.get("GITHUB_TOKEN"))
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "github-read-assigned-skill")
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=20) as response:
            return response.status, dict(response.headers), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", "replace")
        try:
            body = json.loads(text)
        except ValueError:
            body = {"message": text[:200]}
        return err.code, dict(err.headers), body
    except (urllib.error.URLError, OSError) as err:
        raise Stop("could not reach GitHub: %s" % getattr(err, "reason", err))
    except ValueError:
        raise Stop("GitHub's answer to %s was not JSON" % path)


def lowered(headers):
    return {str(name).lower(): str(value) for name, value in (headers or {}).items()}


class Client:
    """Every request the skill makes goes through here. It can only read."""

    def __init__(self, get, sleep=time.sleep, clock=time.time):
        self._get, self._sleep, self._clock = get, sleep, clock
        self.waits = []        # seconds waited for rate limits, in order
        self.count = 0         # requests answered
        self.redirects = 0     # redirects followed
        self.scopes = None     # what GitHub says the token may do, when it says

    def _wait_for(self, headers):
        if headers.get("retry-after", "").isdigit():
            return int(headers["retry-after"])
        if headers.get("x-ratelimit-reset", "").isdigit():
            return max(1, int(headers["x-ratelimit-reset"]) - int(self._clock()) + 1)
        return DEFAULT_WAIT_SECONDS

    def _once(self, path, params):
        waited = 0
        while True:
            status, headers, body = self._get(path, params)
            self.count += 1
            head = lowered(headers)
            if "x-oauth-scopes" in head:
                self.scopes = head["x-oauth-scopes"]
            limited = status == 429 or (status == 403 and (head.get("x-ratelimit-remaining") == "0" or "retry-after" in head))
            if not limited:
                return status, head, body
            seconds = self._wait_for(head)
            if seconds > MAX_WAIT_SECONDS or waited == MAX_WAITS:
                say("rate limited by GitHub, and %s" % ("it asks for a %d second wait when the limit is %d"
                    % (seconds, MAX_WAIT_SECONDS) if seconds > MAX_WAIT_SECONDS else "still limited after %d waits" % MAX_WAITS))
                raise RateLimited()
            waited += 1
            say("rate limited by GitHub. Wait %d of %d: %d seconds" % (waited, MAX_WAITS, seconds))
            self._sleep(seconds)
            self.waits.append(seconds)

    def get(self, path, params=None):
        """Returns (status, headers with lower-case names, body). Follows GitHub's own redirects, and no others."""
        params, hops = dict(params or {}), 0
        while True:
            status, head, body = self._once(path, params)
            if status == 401:
                raise Stop("GitHub rejected the token (401). Check GITHUB_TOKEN. A token also stops working when it expires")
            if status not in (301, 302, 307, 308):
                return status, head, body
            where = urllib.parse.urlsplit(head.get("location", ""))
            if where.scheme != "https" or where.netloc != API_HOST or hops == MAX_REDIRECTS:
                raise Stop("GitHub redirected %s to somewhere the skill does not follow" % path)
            path, params, hops = where.path, dict(urllib.parse.parse_qsl(where.query)), hops + 1
            self.redirects += 1


def has_next(head):
    """GitHub says there is a further page with a Link header that has rel="next"."""
    return any('rel="next"' in part for part in head.get("link", "").split(","))


def read_pages(client, path, params, what, key):
    """Criterion 4: ask for the next page until GitHub reports no further page. Returns (rows, size of each page)."""
    rows, sizes, seen, page = [], [], set(), 1
    while True:
        status, head, body = client.get(path, dict(params, per_page=PER_PAGE, page=page))
        if status in UNREADABLE:
            raise Unreadable(status)
        if status != 200 or not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
            raise Stop("GitHub did not return %s (status %d). A part may be missing, so nothing is saved" % (what, status))
        if len(body) > PER_PAGE:
            raise Stop("GitHub returned more of %s than were asked for, so paging cannot be trusted" % what)
        fresh = [row for row in body if key(row) not in seen]
        sizes.append(len(body))
        rows += fresh
        seen.update(key(row) for row in fresh)
        if not has_next(head):
            return rows, sizes
        if not fresh:
            # GitHub says there is more, and gave nothing new. Asking for the next page is not working, so
            # there may be rows that were never reached. This is not treated as the end.
            raise Stop("GitHub kept returning the same of %s, so the skill cannot tell whether it has them all" % what)
        page += 1


# ---------------------------------------------------------------- reading


def login_of(person):
    return person["login"] if isinstance(person, dict) and isinstance(person.get("login"), str) else "(nobody)"


def repo_in_url(url, marker="/repos/"):
    """owner/name out of one of GitHub's own addresses, or None."""
    rest = str(url or "").partition(marker)[2]
    name = "/".join(rest.split("/")[:2])
    return name if good_repo(name) else None


def good_repo(name):
    return bool(isinstance(name, str) and REPO_NAME.match(name) and not set(name.split("/")) & {".", ".."})


def resolve_identity(client):
    """Criterion 1: ask GitHub who the token belongs to. No login is named in this skill or its configuration."""
    status, _, body = client.get("/user")
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("login"), str) or not isinstance(body.get("id"), int):
        raise Stop("GitHub did not say who the signed-in user is (status %d)" % status)
    return {"login": body["login"], "id": body["id"]}


def as_fields(row):
    """The fields kept of one issue (criterion 5), from GitHub's answer. Nothing else in the answer is kept."""
    repo = row.get("repository") if isinstance(row.get("repository"), dict) else {}
    full = repo.get("full_name") if good_repo(repo.get("full_name")) else repo_in_url(row.get("repository_url"))
    if not isinstance(row.get("node_id"), str) or not NODE_ID.match(row["node_id"]):
        raise Stop("GitHub returned an item with no usable node ID")
    if full is None or not isinstance(row.get("number"), int) or isinstance(row.get("number"), bool):
        raise Stop("GitHub returned item %s without a usable repository and number" % row["node_id"])
    milestone = row.get("milestone") if isinstance(row.get("milestone"), dict) else None
    return {"node_id": row["node_id"], "id": row.get("id"), "repo_id": repo.get("id"), "private": bool(repo.get("private")),
            "full_name": full, "number": row["number"], "title": str(row.get("title") or ""),
            "state": str(row.get("state") or "unknown"), "state_reason": row.get("state_reason"),
            "author": login_of(row.get("user")),
            "assignees": sorted(login_of(person) for person in row.get("assignees") or []),
            "labels": sorted(str(label.get("name")) if isinstance(label, dict) else str(label) for label in row.get("labels") or []),
            "milestone": {"title": str(milestone.get("title")), "number": milestone.get("number")} if milestone else None,
            "body": str(row.get("body") or ""), "created_at": row.get("created_at"), "updated_at": row.get("updated_at"),
            "closed_at": row.get("closed_at")}


def read_assigned(client, identity):
    """Everything GitHub lists as assigned to the user, split into issues and pull requests (criterion 3)."""
    rows, sizes = read_pages(client, "/issues", {"filter": "assigned", "state": "all"},
                             "the items assigned to the user", key=lambda row: row.get("node_id"))
    issues, pulls = [], []
    for row in rows:
        fields = as_fields(row)
        if not isinstance(fields["repo_id"], int):
            raise Stop("GitHub returned item %s without its repository's id" % fields["node_id"])
        if identity["login"] not in fields["assignees"]:
            raise Stop("GitHub returned item %s, which is not assigned to the signed-in user" % fields["node_id"])
        (pulls if "pull_request" in row else issues).append(fields)
    return issues, pulls, sizes


def search_total(client, only_repos):
    """How many issues GitHub's search declares are assigned to the user. Only the total is used."""
    query = " ".join(["is:issue", "assignee:@me"] + ["repo:%s" % name for name in only_repos])
    status, _, body = client.get("/search/issues", {"q": query, "per_page": 1})
    if status != 200 or not isinstance(body, dict) or not isinstance(body.get("total_count"), int):
        raise Stop("GitHub's search did not give a total (status %d), so the count cannot be checked and nothing is saved" % status)
    if body.get("incomplete_results"):
        raise Stop("GitHub's search says its own result is incomplete, so the count cannot be checked and nothing is saved")
    return body["total_count"]


def as_comment(row):
    if not isinstance(row.get("id"), int):
        raise Stop("GitHub returned a comment with no id")
    return {"id": row["id"], "author": login_of(row.get("user")), "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"), "body": str(row.get("body") or "")}


def event_key(row):
    """What makes a timeline entry itself. GitHub gives a cross-reference no id, so its source and time are used."""
    if isinstance(row.get("id"), int):
        return "id:%d" % row["id"]
    source = ((row.get("source") or {}).get("issue") or {}) if isinstance(row.get("source"), dict) else {}
    return "%s:%s:%s" % (row.get("event"), source.get("node_id"), row.get("created_at"))


def as_event(row):
    """One kept timeline entry (criteria 7 and 8). Only ids, logins, times and states are taken from it."""
    kind, detail = row.get("event"), {}
    if kind == "cross-referenced":
        source = (row.get("source") or {}).get("issue") or {}
        there = as_fields(source)
        pull = source.get("pull_request") if isinstance(source.get("pull_request"), dict) else None
        detail = {"kind": "pull request" if "pull_request" in source else "issue",
                  "ref": "%s#%d" % (there["full_name"], there["number"]), "node_id": there["node_id"],
                  "state": there["state"], "merged_at": pull.get("merged_at") if pull else None}
    elif kind in ("referenced", "closed"):
        sha = row.get("commit_id")
        if isinstance(sha, str) and SHA.match(sha):
            detail = {"commit": sha, "commit_repo": repo_in_url(row.get("commit_url"))}
        if kind == "closed" and row.get("state_reason"):
            detail["state_reason"] = str(row["state_reason"])
    elif kind in ("assigned", "unassigned"):
        detail = {"assignee": login_of(row.get("assignee"))}
    elif kind == "renamed":
        rename = row.get("rename") if isinstance(row.get("rename"), dict) else {}
        detail = {"from": str(rename.get("from") or ""), "to": str(rename.get("to") or "")}
    return {"key": event_key(row), "event": kind, "actor": login_of(row.get("actor")),
            "created_at": row.get("created_at"), "detail": detail}


def read_thread(client, issue):
    """The comments and the timeline of one issue. Raises Unreadable if GitHub refuses either."""
    base = "/repos/%s/issues/%d" % (issue["full_name"], issue["number"])
    comments, comment_pages = read_pages(client, base + "/comments", {}, "the comments of %s" % issue["node_id"],
                                         key=lambda row: row.get("id"))
    entries, entry_pages = read_pages(client, base + "/timeline", {}, "the timeline of %s" % issue["node_id"], key=event_key)
    kept = [as_event(row) for row in entries if row.get("event") in MATERIAL]
    return {"comments": [as_comment(row) for row in comments], "events": kept, "entries_read": len(entries),
            "requests": len(comment_pages) + len(entry_pages)}


def why_gone(client, old, identity, in_scope):
    """Criterion 10: look up one held issue that GitHub no longer lists, to say what became of it."""
    status, _, body = client.get("/repos/%s/issues/%d" % (old["full_name"], old["number"]))
    if status == 410:
        return {"reason": "deleted", "detail": "GitHub says the issue was deleted"}
    if status == 404:
        return {"reason": "not found", "detail": "GitHub answers 404: the issue was deleted, or the connection can "
                                                 "no longer see its repository"}
    if status in (403, 451):
        return {"reason": "not reachable", "detail": "GitHub refuses to show the issue to this connection (status %d)" % status}
    if status != 200 or not isinstance(body, dict):
        raise Stop("GitHub did not say what became of %s (status %d), so nothing is saved" % (old["node_id"], status))
    now = as_fields(body)
    assigned = identity["login"] in now["assignees"]
    if (now["node_id"], now["number"]) != (old["node_id"], old["number"]):
        return {"reason": "transferred", "shown": "now node ID %s" % now["node_id"], "moved_to": {"ref": "%s#%d" % (now["full_name"], now["number"]), "node_id": now["node_id"]},
                "detail": "GitHub redirects its old address to %s#%d, node ID %s, which is %s to the user"
                          % (now["full_name"], now["number"], now["node_id"], "assigned" if assigned else "not assigned")}
    if "pull_request" in body:
        return {"reason": "now a pull request", "detail": "GitHub now marks this item as a pull request"}
    if not assigned:
        return {"reason": "reassigned" if now["assignees"] else "unassigned", "shown": "now %s" % plural(len(now["assignees"]), "assignee"),
                "detail": "now assigned to %s" % (", ".join(now["assignees"]) or "nobody")}
    if not in_scope(now["full_name"]):
        return {"reason": "repository not searched", "detail": "still assigned to the user, in a repository this "
                                                               "sync was restricted away from"}
    raise Stop("%s is still assigned to the user and GitHub's list did not return it. The list was not complete, "
               "so nothing is saved" % old["node_id"])


# ---------------------------------------------------------------- the person's notes


def notes_checksums(out_dir):
    """SHA-256 of every notes file. The files are opened for reading only. Nothing in this skill writes there."""
    folder, sums = os.path.join(out_dir, "notes"), {}
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    sums[name] = hashlib.sha256(f.read()).hexdigest()
    return sums


def write_text(path, text, out_dir):
    """Write the whole file or nothing. Refuses anything in the notes folder (criterion 9)."""
    notes = os.path.realpath(os.path.join(out_dir, "notes"))
    if os.path.commonpath([notes, os.path.realpath(path)]) == notes:
        raise Stop("the sync does not write in the notes folder")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- memory: assigned.json


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(out_dir, source, identity):
    path = os.path.join(out_dir, "assigned.json")
    if not os.path.exists(path):
        return {"schema": 1, "source": source, "identity": identity, "issues": {}, "repos": {}}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        assert state["schema"] == 1 and isinstance(state["issues"], dict) and isinstance(state["repos"], dict)
    except (ValueError, KeyError, TypeError, AssertionError):
        raise Stop("%s cannot be read as this skill's memory. Move it aside to start again" % shown_path(path))
    if state.get("source") != source:
        raise Stop("%s holds issues from a %s run, and this is a %s run. One folder holds one source. Use another --out"
                   % (shown_path(out_dir), state.get("source"), source))
    if (state.get("identity") or {}).get("id") != identity["id"]:
        raise Stop("%s holds another user's issues. One folder holds one user. Use another --out" % shown_path(out_dir))
    state["identity"] = identity      # a login can be renamed. The user id cannot
    return state


def merge_comments(held, returned, now):
    """Fold the comments GitHub returned into those held, by comment id, so none is ever entered twice."""
    by_id, added, edited, lost = {c["id"]: c for c in held}, 0, 0, 0
    for comment in returned:
        old = by_id.get(comment["id"])
        if old is None:
            added += 1
        elif (old["body"], old["updated_at"]) != (comment["body"], comment["updated_at"]):
            edited += 1
        by_id[comment["id"]] = comment
    back = {comment["id"] for comment in returned}
    for comment_id, old in list(by_id.items()):
        if comment_id not in back and "gone_since" not in old:
            by_id[comment_id] = dict(old, gone_since=now)     # kept, and marked. Nothing is removed locally
            lost += 1
    return sorted(by_id.values(), key=lambda c: (c["created_at"] or "", c["id"])), added, edited, lost


def merge_events(held, returned):
    by_key = {e["key"]: e for e in held}
    added = sum(e["key"] not in by_key for e in returned)
    by_key.update((e["key"], e) for e in returned)
    return sorted(by_key.values(), key=lambda e: (e["created_at"] or "", e["key"])), added


def merge(state, issues, threads, gone, now):
    """Fold what GitHub returned into what was held, matching on the node ID and nothing else (criterion 6).

    An issue held and no longer returned is kept and flagged with why (criterion 10). Nothing is ever removed.
    """
    held = state["issues"]
    changes = {"new": [], "changed": [], "unchanged": [], "closed": [], "reopened": [], "flagged": [], "back": [],
               "comments_added": 0, "comments_edited": 0, "comments_lost": 0, "events_added": 0}
    for fields in issues:
        node = fields["node_id"]
        old = held.get(node)
        record = dict(old or {}, **fields)
        for stale in ("reason", "detail", "since", "moved_to", "shown"):
            record.pop(stale, None)
        record.update(status="assigned", first_seen=old["first_seen"] if old else now, last_synced=now)
        record["previously"] = list(old["previously"]) if old else []
        history = list(old["state_history"]) if old else []
        if old and (old["full_name"], old["number"]) != (fields["full_name"], fields["number"]):
            record["previously"].append("%s#%d" % (old["full_name"], old["number"]))
        if not old or (old["state"], old["state_reason"]) != (fields["state"], fields["state_reason"]):
            history.append({"state": fields["state"], "state_reason": fields["state_reason"], "seen_at": now})
        record["state_history"] = history
        thread = threads[node]
        record["comments"], added, edited, lost = merge_comments(old["comments"] if old else [], thread["comments"], now)
        record["events"], events_added = merge_events(old["events"] if old else [], thread["events"])
        changes["comments_added"] += added
        changes["comments_edited"] += edited
        changes["comments_lost"] += lost
        changes["events_added"] += events_added
        what = [field for field in WATCHED if old and old.get(field) != fields[field]]
        what += [word for word, count in (("comments added", added), ("comments edited", edited),
                                          ("comments no longer returned", lost), ("timeline entries added", events_added)) if count]
        if old is None:
            changes["new"].append(node)
        elif old["status"] != "assigned":
            changes["back"].append(node)
        elif what:
            changes["changed"].append((node, what))
        else:
            changes["unchanged"].append(node)
        if old and old["state"] != fields["state"]:
            changes["closed" if fields["state"] == "closed" else "reopened"].append((node, old["state"], old["state_reason"]))
        held[node] = record
    for node, why in gone.items():
        held[node].update(status="not assigned", since=now, **why)
        changes["flagged"].append(node)
        target = held.get((why.get("moved_to") or {}).get("node_id"))
        was = "%s#%d, node ID %s" % (held[node]["full_name"], held[node]["number"], node)
        if target is not None and target is not held[node] and was not in target["previously"]:
            target["previously"].append(was)       # the issue it became points back to the one it was
    return changes


# ---------------------------------------------------------------- links from request to delivery


def links_of(record):
    """Criterion 8: the pull requests, commits and issues an issue's timeline points to, each with its own identifier."""
    found = {}
    for event in record["events"]:
        detail = event["detail"]
        if event["event"] == "cross-referenced":
            link = {"kind": detail["kind"], "ref": detail["ref"], "node_id": detail["node_id"], "how": "mentions this issue",
                    "state": ("merged %s" % detail["merged_at"]) if detail.get("merged_at") else detail["state"],
                    "merged": bool(detail.get("merged_at"))}
        elif detail.get("commit"):
            link = {"kind": "commit", "ref": detail["commit"], "node_id": "", "merged": False,
                    "how": "closed this issue" if event["event"] == "closed" else "references this issue",
                    "state": "in %s" % detail["commit_repo"] if detail.get("commit_repo") else "repository not given"}
        else:
            continue
        link["at"] = event["created_at"]
        found[(link["kind"], link["ref"], link["how"])] = link
    return sorted(found.values(), key=lambda link: (link["at"] or "", link["kind"], link["ref"]))


def delivery(record):
    """The third stretch goal: is there evidence that the issue was delivered?

    exists:  closed as completed, and a merged pull request mentions it or a commit closed it.
    partial: a pull request or commit points to it, and the above is not all true.
    missing: no pull request and no commit points to it.
    """
    links = [link for link in links_of(record) if link["kind"] != "issue"]
    if not links:
        return "missing"
    proven = any(link["merged"] or link["how"] == "closed this issue" for link in links)
    return "exists" if proven and record["state"] == "closed" and record["state_reason"] == "completed" else "partial"


# ---------------------------------------------------------------- what is written


def one_line(text):
    """Text on one line, with nothing that could start Markdown structure. Titles are other people's writing."""
    return " ".join(str(text).split()).replace("|", "\\|").replace("[", "(").replace("]", ")").replace("`", "'") or "(empty)"


def fenced(text):
    """Other people's text, shown as text: inside a fence longer than any run of backticks in it."""
    if not text.strip():
        return "(empty)"
    longest = max([len(run) for run in re.findall(r"`+", text)] or [0])
    fence = "`" * max(3, longest + 1)
    return "%stext\n%s\n%s" % (fence, text.rstrip("\n"), fence)


def ref(record):
    return "%s#%d" % (record["full_name"], record["number"])


def state_words(record):
    return record["state"] + (" (%s)" % one_line(record["state_reason"]) if record["state_reason"] else "")


def describe_event(event):
    detail = event["detail"]
    if event["event"] == "cross-referenced":
        return "%s `%s`, node ID `%s`, %s" % (detail["kind"], detail["ref"], detail["node_id"],
                                              ("merged %s" % detail["merged_at"]) if detail.get("merged_at") else detail["state"])
    if event["event"] == "renamed":
        return "title changed from \"%s\" to \"%s\"" % (one_line(detail["from"]), one_line(detail["to"]))
    words = []
    if detail.get("assignee"):
        words.append("assignee %s" % one_line(detail["assignee"]))
    if detail.get("state_reason"):
        words.append("reason %s" % one_line(detail["state_reason"]))
    if detail.get("commit"):
        words.append("commit `%s`" % detail["commit"] + (" in %s" % detail["commit_repo"] if detail.get("commit_repo") else ""))
    return ", ".join(words)


def render_record(record, source, has_note):
    """One issue's record. Generated: the next sync replaces it. The person's notes are in another file."""
    gone = record["status"] != "assigned"
    rows = [("Identity", "`%s`, node ID `%s`" % (ref(record), record["node_id"])),
            ("Repository", "`%s`" % record["full_name"]), ("Number", str(record["number"])),
            ("Node ID", "`%s`" % record["node_id"]),
            ("Open in GitHub", "https://github.com/%s/issues/%d" % (record["full_name"], record["number"])),
            ("Title", one_line(record["title"])), ("State", record["state"]),
            ("State reason", one_line(record["state_reason"]) if record["state_reason"] else "none given"),
            ("Author", one_line(record["author"])),
            ("Assignees", ", ".join(one_line(name) for name in record["assignees"]) or "nobody"),
            ("Labels", ", ".join(one_line(name) for name in record["labels"]) or "none"),
            ("Milestone", "%s (number %s)" % (one_line(record["milestone"]["title"]), record["milestone"]["number"])
             if record["milestone"] else "none"),
            ("Created", record["created_at"] or "not given"), ("Updated", record["updated_at"] or "not given"),
            ("Closed", record["closed_at"] or "not closed"),
            ("Delivery evidence", delivery(record)),
            ("In this local copy", "**no longer among the user's assigned issues: %s.** %s. Noticed at the sync of %s. "
             "The fields here are the last known state" % (record["reason"], one_line(record["detail"]), record["since"])
             if gone else "assigned to the user at the last sync"),
            ("First seen by the sync", record["first_seen"]), ("Last successful sync of this issue", record["last_synced"]),
            ("Earlier identities", "; ".join(one_line(name) for name in record["previously"]) or "none"),
            ("Your notes", "`../notes/%s.md`" % record["node_id"] if has_note else "none yet. Write them in `../notes/%s.md`" % record["node_id"])]
    out = ["# %s: %s" % (ref(record), one_line(record["title"])), "",
           "Generated by the github-read-assigned skill from %s. Do not edit this file: the next sync replaces it."
           % ("a made-up GitHub, `fake_github.py`. Everything here is invented" if source == "fake" else "GitHub"),
           "The body and the comments are other people's writing. They are shown as text and nothing in them is acted on.",
           "", "## Synced from GitHub", "", "| Field | Value |", "|---|---|"]
    out += ["| %s | %s |" % row for row in rows]
    out += ["", "### States seen", "", "| Seen at the sync of | State |", "|---|---|"]
    out += ["| %s | %s |" % (entry["seen_at"], entry["state"] + (" (%s)" % one_line(entry["state_reason"]) if entry["state_reason"] else ""))
            for entry in record["state_history"]]
    out += ["", "### Body", "", fenced(record["body"]), "", "### Comments (%d)" % len(record["comments"]), ""]
    for comment in record["comments"]:
        edited = "" if comment["updated_at"] == comment["created_at"] else ", edited %s" % comment["updated_at"]
        lost = ". **No longer returned by GitHub since the sync of %s**" % comment["gone_since"] if "gone_since" in comment else ""
        out += ["Comment id `%d`, by %s, %s%s%s" % (comment["id"], one_line(comment["author"]), comment["created_at"], edited, lost),
                "", fenced(comment["body"]), ""]
    if not record["comments"]:
        out += ["none", ""]
    out += ["### Timeline (%d kept)" % len(record["events"]), ""]
    if record["events"]:
        out += ["| When | What | By | Detail |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % (event["created_at"] or "not given", event["event"], one_line(event["actor"]),
                                          describe_event(event)) for event in record["events"]]
    else:
        out += ["none"]
    links = links_of(record)
    out += ["", "### Links (%d)" % len(links), ""]
    if links:
        out += ["| Kind | Identifier | Node ID | How it is linked | State | When |", "|---|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | %s | %s |" % (link["kind"], link["ref"], "`%s`" % link["node_id"] if link["node_id"] else "",
                                                      link["how"], link["state"], link["at"] or "not given") for link in links]
    else:
        out += ["none"]
    return "\n".join(out).rstrip("\n") + "\n"


def by_repo(records):
    groups = {}
    for record in sorted(records, key=lambda r: (r["full_name"], r["number"], r["node_id"])):
        groups.setdefault(record["full_name"], []).append(record)
    return groups


def render_index(state, notes):
    now, me = state["last_successful_sync"], state["identity"]
    records = list(state["issues"].values())
    mine = [r for r in records if r["status"] == "assigned"]
    gone = sorted((r for r in records if r["status"] != "assigned"), key=lambda r: (r["full_name"], r["number"]))
    note = lambda r: "`notes/%s.md`" % r["node_id"] if r["node_id"] + ".md" in notes else ""
    link = lambda r: "[record](issues/%s.md)" % r["node_id"]
    repos = sorted(state["repos"].values(), key=lambda repo: repo["full_name"])
    unread = [repo for repo in repos if repo.get("unreadable")]
    out = ["# Issues assigned to the user", "",
           "Generated by the github-read-assigned skill from %s. Do not edit this file: the next sync replaces it."
           % ("a made-up GitHub, `fake_github.py`. Every repository, issue and login here is invented" if state["source"] == "fake" else "GitHub"),
           "Your own notes on an issue go in `notes/<node ID>.md`, which the sync never writes to.", "",
           "| | |", "|---|---|",
           "| Identity, read from the connection | login %s, user id `%d` |" % (one_line(me["login"]), me["id"]),
           "| Last successful sync | %s |" % now,
           "| Scope | %s |" % state["scope"],
           "| Assigned and open | %d |" % sum(r["state"] == "open" for r in mine),
           "| Assigned and closed | %d |" % sum(r["state"] != "open" for r in mine),
           "| No longer among the assigned issues, kept | %d |" % len(gone),
           "| Pull requests left out at the last sync | %d |" % state["pulls_left_out"],
           "| Repositories that could not be read at the last sync | %d |" % len(unread),
           "| Notes files | %d |" % len(notes),
           "", "Pull requests: %s." % PULL_REQUEST_RULE, "",
           "## Repositories (%d)" % len(repos), "",
           "| Repository | Repository id | Visibility | Issues held | Last successful sync | At the last sync |", "|---|---|---|---|---|---|"]
    for repo in repos:
        if repo.get("unreadable"):
            status = "**COULD NOT BE READ** (status %d). %s there not refreshed" % (
                repo["unreadable"]["status"], plural(repo["unreadable"]["issues"], "assigned issue"))
        elif repo["seen_at"] != now:
            status = "no assigned issue returned"
        else:
            status = "read. %s left out" % plural(repo["pulls_left_out"], "pull request")
        was = " (earlier %s)" % ", ".join("`%s`" % name for name in repo["previously"]) if repo["previously"] else ""
        out += ["| `%s`%s | `%d` | %s | %d | %s | %s |" % (
            repo["full_name"], was, repo["id"], "private" if repo["private"] else "public",
            sum(r.get("repo_id") == repo["id"] for r in records), repo["last_successful_sync"] or "never", status)]
    out += ["", "## Assigned issues, by repository (%d)" % len(mine), ""]
    for full_name, group in by_repo(mine).items():
        out += ["### %s (%d)" % (full_name, len(group)), "",
                "| Issue | Title | State | Updated | Delivery evidence | Last synced | Record | Your notes |", "|---|---|---|---|---|---|---|---|"]
        out += ["| `%s` | %s | %s | %s | %s | %s | %s | %s |" % (
            ref(r), one_line(r["title"]), state_words(r), r["updated_at"] or "not given", delivery(r), r["last_synced"],
            link(r), note(r)) for r in group] + [""]
    if not mine:
        out += ["none", ""]
    out += ["## No longer among the assigned issues (%d)" % len(gone), ""]
    if gone:
        out += ["Held from an earlier sync and no longer returned by GitHub as assigned to the user. Nothing here has been",
                "deleted. Each row is the issue's last known state, and its record and notes are where they were.", "",
                "| Issue | Title | Last known state | Why | Noticed at the sync of | Last synced | Record | Your notes |",
                "|---|---|---|---|---|---|---|---|"]
        out += ["| `%s` | %s | %s | **%s**: %s | %s | %s | %s | %s |" % (
            ref(r), one_line(r["title"]), state_words(r), r["reason"], one_line(r["detail"]), r["since"], r["last_synced"],
            link(r), note(r)) for r in gone]
    else:
        out += ["none"]
    orphans = sorted(name for name in notes if name[:-3] not in state["issues"] or not name.endswith(".md"))
    if orphans:
        out += ["", "## Notes files with no issue here (%d)" % len(orphans), "",
                "Left as they are. The sync does not move or remove notes.", ""] + ["- `notes/%s`" % one_line(n) for n in orphans]
    return "\n".join(out).rstrip("\n") + "\n"


def rows_in_index(text):
    """How many issue rows the two issue sections of an index hold, counted from its text."""
    count, inside = 0, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.startswith(("## Assigned issues, by repository", "## No longer among the assigned issues"))
        elif inside and line.startswith("| `"):
            count += 1
    return count


def render_links(state):
    records = sorted(state["issues"].values(), key=lambda r: (r["full_name"], r["number"]))
    counts = {word: sum(delivery(r) == word for r in records) for word in ("exists", "partial", "missing")}
    out = ["# From request to delivery", "",
           "Generated by the github-read-assigned skill. Do not edit this file: the next sync replaces it.",
           "Each row is a link GitHub's timeline of an issue records, with the linked thing's own identifier.", "",
           "Delivery evidence: **exists** when the issue is closed as completed and a merged pull request mentions it or",
           "a commit closed it. **partial** when a pull request or commit points to it and that is not all true.",
           "**missing** when no pull request and no commit points to it. A link is a claim, not a proof that the work is right.", "",
           "| Delivery evidence | Issues |", "|---|---|"] + ["| %s | %d |" % item for item in counts.items()]
    out += ["", "## Links", "", "| Issue | Issue state | Delivery evidence | Kind | Identifier | Node ID | How it is linked | State | When |",
            "|---|---|---|---|---|---|---|---|---|"]
    rows = ["| `%s` | %s | %s | %s | `%s` | %s | %s | %s | %s |" % (
        ref(r), state_words(r), delivery(r), link["kind"], link["ref"], "`%s`" % link["node_id"] if link["node_id"] else "",
        link["how"], link["state"], link["at"] or "not given") for r in records for link in links_of(r)]
    out += rows or ["| none | | | | | | | | |"]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- the run


def run(client, out_dir, source, now=None, only_repos=()):
    now = now or utc_now()
    only_repos = sorted(set(only_repos))
    in_scope = lambda name: not only_repos or name in only_repos
    notes_before = notes_checksums(out_dir)
    # Everything is read first. Nothing is written until every request has been answered.
    try:
        identity = resolve_identity(client)
        say('identity read from the connection: login %s, user id %d. GitHub was asked "who am I?". No login is '
            "named in the skill or given to it" % (identity["login"], identity["id"]))
        say("token scopes GitHub reports: %s" % (
            "none reported, as for a fine-grained token" if client.scopes is None else (client.scopes or "none")))
        state = load_state(out_dir, source, identity)
        scope = "every repository GitHub lists an assigned issue in"
        if only_repos:
            scope = "RESTRICTED with --only-repos to %s. This is not every repository" % plural(len(only_repos), "repository", "repositories")
        say("scope: %s" % scope)
        issues, pulls, sizes = read_assigned(client, identity)
        say("GitHub's list of items assigned to the user: %d items in %s (%s). GitHub reported no further page after the last"
            % (len(issues) + len(pulls), plural(len(sizes), "request"), " + ".join(str(size) for size in sizes)))
        say("pull requests left out: %d. Issues: %d. Rule: %s" % (len(pulls), len(issues), PULL_REQUEST_RULE))
        outside = [i for i in issues if not in_scope(i["full_name"])]
        issues = [i for i in issues if in_scope(i["full_name"])]
        pulls = [p for p in pulls if in_scope(p["full_name"])]
        if only_repos:
            say("in scope: %d issues. Outside the restriction and not recorded: %d" % (len(issues), len(outside)))
        if len({i["node_id"].lower() for i in issues} | {n.lower() for n in state["issues"]}) != len({i["node_id"] for i in issues} | set(state["issues"])):
            raise Stop("two node IDs differ only in upper and lower case, and each record is a file named by its node "
                       "ID, which this file system may not keep apart")
        declared = search_total(client, only_repos)
        if declared != len(issues):
            raise Stop("GitHub's list returned %d issues assigned to the user, and GitHub's search declares %d. They "
                       "disagree, so the list cannot be taken as complete" % (len(issues), declared))
        say("retrieved %d issues. GitHub's search declares %d. The totals agree" % (len(issues), declared))

        repos, threads, readable = {}, {}, []
        for issue in issues:
            repos.setdefault(issue["repo_id"], []).append(issue)
        say("repositories with an assigned issue: %d" % len(repos))
        unreadable = {}
        for repo_id in sorted(repos):
            group, read, requests = repos[repo_id], {}, 0
            left_out = sum(p["repo_id"] == repo_id for p in pulls)
            try:
                for issue in group:
                    read[issue["node_id"]] = read_thread(client, issue)
                    requests += read[issue["node_id"]]["requests"]
            except Unreadable as refused:
                unreadable[repo_id] = {"status": refused.args[0], "issues": len(group), "at": now}
                say("  repository id %d, %s: COULD NOT BE READ. GitHub refused its comments and timelines (status %d). "
                    "%s there not recorded or refreshed by this sync"
                    % (repo_id, "private" if group[0]["private"] else "public", refused.args[0], plural(len(group), "assigned issue")))
                continue
            threads.update(read)
            readable += group
            say("  repository id %d, %s: %s, %s left out, comments and timelines read in %s"
                % (repo_id, "private" if group[0]["private"] else "public", plural(len(group), "issue"),
                   plural(left_out, "pull request"), plural(requests, "request")))
        returned = {i["node_id"] for i in issues} | {i["node_id"] for i in outside}
        gone = {node: why_gone(client, old, identity, in_scope) for node, old in sorted(state["issues"].items())
                if old["status"] == "assigned" and node not in returned}
    except RateLimited:
        say("INCOMPLETE: GitHub rate-limited this run. Nothing was written. The files from the last successful "
            "sync are as they were. Run it again later.")
        return 2
    except Unreadable as refused:
        raise Stop("GitHub refused the list of assigned items (status %d)" % refused.args[0])

    held_before = len(state["issues"])
    changes = merge(state, readable, threads, gone, now)
    for repo_id, group in repos.items():
        old = state["repos"].get(str(repo_id)) or {"previously": [], "last_successful_sync": None, "full_name": group[0]["full_name"]}
        previously = list(old["previously"]) + ([old["full_name"]] if old["full_name"] != group[0]["full_name"] else [])
        state["repos"][str(repo_id)] = {
            "id": repo_id, "full_name": group[0]["full_name"], "private": group[0]["private"], "previously": previously,
            "seen_at": now, "pulls_left_out": sum(p["repo_id"] == repo_id for p in pulls),
            "unreadable": unreadable.get(repo_id),
            "last_successful_sync": old["last_successful_sync"] if repo_id in unreadable else now}   # criterion 11
    for key, repo in state["repos"].items():
        if repo["seen_at"] != now:
            repo["unreadable"] = None
    state.update(last_successful_sync=now, scope=scope, pulls_left_out=len(pulls))

    read_entries = sum(t["entries_read"] for t in threads.values())
    say("comments read: %d. Added to the local copy: %d, edited: %d, no longer returned and kept: %d"
        % (sum(len(t["comments"]) for t in threads.values()), changes["comments_added"], changes["comments_edited"], changes["comments_lost"]))
    say("timeline entries read: %d. Kept as material: %d. Added to the local copy: %d"
        % (read_entries, sum(len(t["events"]) for t in threads.values()), changes["events_added"]))
    say("issues held before this sync: %d. This sync: %d new, %d changed, %d unchanged, %d newly flagged as no longer "
        "assigned, %d assigned again" % (held_before, len(changes["new"]), len(changes["changed"]),
                                        len(changes["unchanged"]), len(changes["flagged"]), len(changes["back"])))
    for node, fields in changes["changed"]:
        say("  changed: issue %s (%s)" % (node, ", ".join(fields)))
    for word in ("closed", "reopened"):
        for node, was, was_reason in changes[word]:
            say("  %s since the last sync: issue %s is now %s. It was %s. Kept, with both states in its record"
                % (word.upper(), node, state_words(state["issues"][node]), was + (" (%s)" % was_reason if was_reason else "")))
    for node in changes["flagged"]:
        record = state["issues"][node]
        say("  FLAGGED, not deleted: issue %s is no longer among the user's assigned issues: %s%s. Last known state: "
            "%s. Its record and its notes are kept" % (node, record["reason"], ", " + record["shown"] if record.get("shown") else "",
                                                       state_words(record)))
    for node in changes["back"]:
        say("  assigned again: issue %s" % node)
    kinds = [link["kind"] for record in state["issues"].values() for link in links_of(record)]
    say("links held: %d to pull requests, %d to commits, %d to other issues"
        % (kinds.count("pull request"), kinds.count("commit"), kinds.count("issue")))

    for node, record in sorted(state["issues"].items()):
        write_text(os.path.join(out_dir, "issues", node + ".md"), render_record(record, source, node + ".md" in notes_before), out_dir)
    index_path = os.path.join(out_dir, "index.md")
    text = render_index(state, notes_before)
    write_text(index_path, text, out_dir)
    write_text(os.path.join(out_dir, "delivery-links.md"), render_links(state), out_dir)
    write_text(os.path.join(out_dir, "assigned.json"), json.dumps(state, indent=1, ensure_ascii=False, sort_keys=True) + "\n", out_dir)  # last
    files = len([name for name in os.listdir(os.path.join(out_dir, "issues")) if name.endswith(".md")]) if state["issues"] else 0
    saved, flagged = rows_in_index(text), sum(r["status"] != "assigned" for r in state["issues"].values())
    not_recorded = sum(len(repos[repo_id]) for repo_id in unreadable)
    recorded = sum(state["issues"][i["node_id"]]["status"] == "assigned" for i in readable)
    agree = saved == len(state["issues"]) == files and recorded == len(issues) - not_recorded
    say("counts: retrieved %d, of which %d in unreadable repositories were not recorded or refreshed. Recorded by this sync: %d. "
        "Held in all: %d, of which %d no longer assigned. Rows in the index: %d. Record files: %d. %s"
        % (len(issues), not_recorded, recorded, len(state["issues"]), flagged, saved, files,
                                                        "The counts agree" if agree else "THE COUNTS DISAGREE"))
    notes_after = notes_checksums(out_dir)
    say("notes: %s, opened for reading only. SHA-256 before and after this sync:" % plural(len(notes_before), "file"))
    for name in sorted(set(notes_before) | set(notes_after)):
        say("  notes/%s  before %s  after %s  %s" % (name, notes_before.get(name, "absent"), notes_after.get(name, "absent"),
                                                    "same" if notes_before.get(name) == notes_after.get(name) else "DIFFERENT"))
    if client.waits:
        say("this run waited %d time(s) for GitHub's rate limit" % len(client.waits))
    say("requests made: %d, every one a GET%s" % (client.count, ". Redirects followed, all to GitHub's API: %d" % client.redirects if client.redirects else ""))
    say("last successful sync: %s. Written: %s, %s in issues/, delivery-links.md and assigned.json"
        % (now, shown_path(index_path), plural(files, "record")))
    if not agree or notes_before != notes_after:
        say("STOPPED AFTER WRITING: a check above failed. Do not rely on this index.")
        return 1
    return 0


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "..", "..", "context", "github", "assigned")
    parser = argparse.ArgumentParser(description="Synchronize the GitHub issues assigned to the signed-in user. Read-only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--out", help="folder to write into (default: participant/context/github/assigned)")
    parser.add_argument("--only-repos", help="record only these repositories, owner/name separated by commas. The index then says it is restricted")
    parser.add_argument("--fake-step", type=int, default=0, choices=(0, 1), help="with --source fake: the made-up GitHub at step 0, or at step 1, a day later")
    args = parser.parse_args(argv)
    out = os.path.normpath(args.out or default_out)
    try:
        only = [name.strip() for name in (args.only_repos or "").split(",") if name.strip()]
        if any(not good_repo(name) for name in only):
            raise Stop("--only-repos takes repository names as owner/name")
        if args.source == "fake":
            sys.path.insert(0, here)
            import fake_github
            fake = fake_github.FakeGitHub(args.fake_step)
            return run(Client(fake.get), out, "fake", now=fake.now, only_repos=only)
        if args.fake_step:
            raise Stop("--fake-step only goes with --source fake")
        if not args.out:
            raise Stop("a live run needs --out, a folder outside this repository, because real issues can be private")
        if not os.environ.get("GITHUB_TOKEN"):
            raise Stop("the environment variable GITHUB_TOKEN is not set")
        return run(Client(live_get), out, "live", only_repos=only)
    except Stop as stop:
        say("STOPPED: %s." % stop)
        say("Nothing was written.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
