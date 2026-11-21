#!/usr/bin/env python3
"""Lists the Jira projects a connection can see, and keeps them by Jira's project id.

    projects.py --source live --out FOLDER
    projects.py --source fake --out FOLDER [--page-size N] [--fake-count N]

A project has three labels. Its id is given once by Jira and does not change.
Its key and its name can both be changed by an administrator. So a project is
known here by its id and by nothing else: records are matched on the id, files
are named by the id, and links point to the id. The key and the name are
stored beside it as two more fields.

It writes three things into FOLDER:

    projects.md            the list, with a lookup by name, by key and by id
    projects/<id>.md       one record for each project
    projects.json          what was held after the last run

On a second run, a project whose id is already held is updated in place,
whatever has happened to its key or name, and the old key or name is kept in
its history. A project that was held and is not returned is kept and flagged.
Nothing is ever deleted.

It only reads. It sends GET requests and has no code that sends any other
kind. For a live run the connection comes from the environment variables
JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN. None is printed or written, the
site's address included, and the output is searched for them before it is shown.

Everything is read before anything is written. If the list cannot be read
whole, nothing is written.

Exit codes: 0 done; 1 stopped, nothing written.
"""
import argparse
import base64
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PAGE_SIZE = 50


class Stop(Exception):
    """The run cannot go on. The message says why."""


LINES = []


def say(text=""):
    LINES.append(text)


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
            return err.code, dict(err.headers), {}
        except (urllib.error.URLError, OSError) as err:
            raise Stop("could not reach Jira: %s" % type(getattr(err, "reason", err)).__name__)
        except ValueError:
            raise Stop("Jira's answer to %s was not JSON" % path)

    host = urllib.parse.urlparse(base).hostname or ""
    return get, [token, email, encoded, host]


# ---------------------------------------------------------------- reading


def fetch_all(get, page_size=PAGE_SIZE):
    """Every visible project, across every page. Returns (projects, pages).

    Criterion 1. The loop goes on until Jira says a page is the last one. It
    does not stop because a page came back short or because it came back full.
    Jira may give fewer in a page than asked for, so the next page starts
    after as many as were actually returned.

    Afterwards the count is held against Jira's own `total`. A list that is
    shorter than Jira says it should be is not accepted.
    """
    projects, seen, pages, start, total = [], set(), 0, 0, None
    while True:
        status, _, body = get("/rest/api/3/project/search", {"startAt": start, "maxResults": page_size, "orderBy": "key"})
        if status == 401:
            raise Stop("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN")
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("values"), list):
            raise Stop("Jira did not return page %d of the projects (status %d)" % (pages + 1, status))
        pages += 1
        values = body["values"]
        if isinstance(body.get("total"), int) and not isinstance(body.get("total"), bool):
            total = body["total"]
        fresh = 0
        for value in values:
            ok = (isinstance(value, dict) and all(isinstance(value.get(f), str) and value[f] for f in ("id", "key", "name")))
            if not ok:
                raise Stop("Jira returned a project without an id, a key or a name, on page %d" % pages)
            if not value["id"].isascii() or not value["id"].isalnum():
                raise Stop("Jira returned a project id that is not letters and digits, so it cannot name a file")
            if value["id"] not in seen:
                seen.add(value["id"])
                fresh += 1
                projects.append({"id": value["id"], "key": value["key"], "name": value["name"]})
        say("  page %d: asked for %d from position %d, received %d%s"
            % (pages, page_size, start, len(values), "" if fresh == len(values) else " (%d already held)" % (len(values) - fresh)))
        last = body.get("isLast")
        if last is True:
            break
        if last is not False:
            # Jira did not say. Fall back on its count, and failing that on an empty page.
            if total is not None and start + len(values) >= total:
                break
            if total is None and not values:
                break
        if not values or (values and not fresh):
            raise Stop("Jira's pages stopped moving forward at page %d, so the list cannot be trusted to be whole" % pages)
        start += len(values)
    if total is not None and len(projects) != total:
        raise Stop("Jira said there are %d projects and %d were received over %d page(s). The list is not whole"
                   % (total, len(projects), pages))
    return projects, pages, total


# ---------------------------------------------------------------- memory


def load_state(folder, source):
    path = os.path.join(folder, "projects.json")
    if not os.path.exists(path):
        return {"schema": 1, "source": source, "projects": {}}
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        assert state["schema"] == 1 and isinstance(state["projects"], dict)
    except (ValueError, KeyError, TypeError, AssertionError):
        raise Stop("projects.json in the output folder cannot be read. Move it aside to start again")
    if state.get("source") != source:
        raise Stop("the output folder holds projects from a '%s' run, and this is a '%s' run. Use another --out"
                   % (state.get("source"), source))
    return state


def merge(state, projects, now):
    """Fold what Jira returned into what was held, matching on the project id alone.

    Criterion 4: a project whose key or name changed is the same project, and
    what it used to be called goes into its history.
    Criterion 5: a project that was held and was not returned is kept and flagged.
    """
    held = state["projects"]
    changes = {"new": [], "renamed": [], "unchanged": [], "not_returned": [], "returned": []}
    for project in projects:
        old = held.get(project["id"])
        if old is None:
            held[project["id"]] = dict(project, first_seen=now, last_returned=now, state="present", history=[])
            changes["new"].append(project["id"])
            continue
        if old["state"] == "not_returned":
            changes["returned"].append(project["id"])
            old.pop("not_returned_since", None)
        moved = [(field, old[field], project[field]) for field in ("key", "name") if old[field] != project[field]]
        for field, before, after in moved:
            old["history"].append({"noticed": now, "field": field, "was": before, "became": after})
            old[field] = after
        changes["renamed" if moved else "unchanged"].append((project["id"], moved) if moved else project["id"])
        old["last_returned"] = now
        old["state"] = "present"
    returned = {project["id"] for project in projects}
    for project_id, old in held.items():
        if project_id not in returned and old["state"] != "not_returned":
            old["state"] = "not_returned"
            old["not_returned_since"] = now
            changes["not_returned"].append(project_id)
    state["last_successful_sync"] = now
    return changes


# ---------------------------------------------------------------- Markdown


def one_line(text):
    """A label on one line, with nothing that could start Markdown structure. Labels are other people's text."""
    return " ".join(str(text).split()).replace("|", "\\|").replace("[", "(").replace("]", ")").replace("`", "'") or "(empty)"


def state_words(project):
    if project["state"] == "present":
        return "Returned by Jira at the last sync"
    return "NOT RETURNED by Jira since %s" % project["not_returned_since"]


def render_record(project):
    out = ["# %s" % one_line(project["name"]), "",
           "Generated by the project list. Do not edit this file: the next run replaces it.", "",
           "| | |", "|---|---|",
           "| Project id | `%s` |" % project["id"],
           "| Key | `%s` |" % one_line(project["key"]),
           "| Name | %s |" % one_line(project["name"]),
           "| State | %s |" % state_words(project),
           "| First seen | %s |" % project["first_seen"],
           "| Last returned by Jira | %s |" % project["last_returned"],
           "", "The project id is what identifies this project. It is the name of this file, and it does not",
           "change. The key and the name are labels, and either can be changed in Jira.", ""]
    if project["state"] != "present":
        out += ["Jira did not return this project at the last sync. It may have been deleted, or the connection",
                "may no longer be permitted to see it. Jira does not say which. This record is its last known state.", ""]
    out += ["## Former keys and names", ""]
    if project["history"]:
        out += ["| Noticed at | Label | Was | Became |", "|---|---|---|---|"]
        out += ["| %s | %s | %s | %s |" % (h["noticed"], h["field"], one_line(h["was"]), one_line(h["became"]))
                for h in project["history"]]
    else:
        out += ["none"]
    return "\n".join(out) + "\n"


def render_list(state):
    projects = list(state["projects"].values())
    present = [p for p in projects if p["state"] == "present"]
    missing = sorted((p for p in projects if p["state"] != "present"), key=lambda p: int(p["id"]) if p["id"].isdigit() else 0)
    link = lambda p: "[`%s`](projects/%s.md)" % (p["id"], p["id"])
    flag = lambda p: "" if p["state"] == "present" else " **(not returned)**"
    out = ["# Jira projects", "",
           "Generated by the project list. Do not edit this file: the next run replaces it.", "",
           "| | |", "|---|---|",
           "| Source | %s |" % ("a made-up Jira used for testing: every project here is synthetic"
                               if state["source"] == "fake" else "a live Jira site"),
           "| Last successful sync | %s |" % state["last_successful_sync"],
           "| Projects held | %d |" % len(projects),
           "| Returned by Jira at the last sync | %d |" % len(present),
           "| Not returned at the last sync | %d |" % len(missing),
           "", "Each project is known by its **project id**, which Jira gives once and does not change. Its key and",
           "its name are labels that can be changed. Every link below goes to a file named by the id.",
           "", "To find a project, look it up by whichever label you know. The three tables hold the same projects.",
           "A label a project used to have is listed too, marked as former, so an old key or name still leads to it.", ""]

    def table(title, label, sort_key, current, former_field):
        rows = [(sort_key(current(p)), "| %s%s | %s | %s | %s |" % (
            ("`%s`" if label == "Key" else "%s") % one_line(current(p)), flag(p),
            one_line(p["name"]) if label == "Key" else "`%s`" % one_line(p["key"]), link(p), "")) for p in projects]
        if former_field:
            for p in projects:
                for h in p["history"]:
                    if h["field"] == former_field:
                        rows.append((sort_key(h["was"]), "| %s *(former %s)* | %s | %s | until %s |" % (
                            ("`%s`" if label == "Key" else "%s") % one_line(h["was"]), former_field,
                            "now %s" % one_line(p["name"]) if label == "Key" else "now `%s`" % one_line(p["key"]),
                            link(p), h["noticed"])))
        other = "Name" if label == "Key" else "Key"
        return ["## By %s" % title, "", "| %s | %s | Project id | Note |" % (label, other), "|---|---|---|---|"] \
            + [row for _, row in sorted(rows)] + [""]

    out += table("name", "Name", lambda v: str(v).lower(), lambda p: p["name"], "name")
    out += table("key", "Key", lambda v: str(v).lower(), lambda p: p["key"], "key")
    out += ["## By project id", "", "| Project id | Key | Name | State |", "|---|---|---|---|"]
    out += ["| %s | `%s` | %s | %s |" % (link(p), one_line(p["key"]), one_line(p["name"]), state_words(p))
            for p in sorted(projects, key=lambda p: (len(p["id"]), p["id"]))]
    out += ["", "## Not returned by Jira (%d)" % len(missing), ""]
    if missing:
        out += ["These projects were held from an earlier sync and were not returned at a later one. Each is kept,",
                "with its last known key and name. Jira does not say whether a project was deleted or whether the",
                "connection can no longer see it.", "",
                "| Project id | Last key | Last name | Last returned | Not returned since |", "|---|---|---|---|---|"]
        out += ["| %s | `%s` | %s | %s | %s |" % (link(p), one_line(p["key"]), one_line(p["name"]), p["last_returned"],
                                               p["not_returned_since"]) for p in missing]
    else:
        out += ["none"]
    renames = sorted(((h["noticed"], p["id"], h) for p in projects for h in p["history"]), key=lambda r: (r[0], r[1], r[2]["field"]))
    out += ["", "## Renames noticed (%d)" % len(renames), ""]
    if renames:
        out += ["| Noticed at | Project id | Label | Was | Became |", "|---|---|---|---|---|"]
        out += ["| %s | [`%s`](projects/%s.md) | %s | %s | %s |" % (when, pid, pid, h["field"], one_line(h["was"]),
                                                               one_line(h["became"])) for when, pid, h in renames]
    else:
        out += ["none"]
    return "\n".join(out) + "\n"


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


# ---------------------------------------------------------------- the run


def run(get, folder, source, now=None, page_size=PAGE_SIZE):
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    say("PROJECT LIST. Reading only.")
    say("Retrieving the visible projects, %d to a page:" % page_size)
    projects, pages, total = fetch_all(get, page_size)
    say("  %d project(s) received over %d page(s). Jira's own count: %s."
        % (len(projects), pages, total if total is not None else "not given"))

    state = load_state(folder, source)
    before = state.get("last_successful_sync", "never")
    changes = merge(state, projects, now)
    held = state["projects"]
    for project in held.values():
        write_text(os.path.join(folder, "projects", project["id"] + ".md"), render_record(project))
    write_text(os.path.join(folder, "projects.md"), render_list(state))
    write_text(os.path.join(folder, "projects.json"), json.dumps(state, indent=1, ensure_ascii=False) + "\n")   # last

    say("")
    say("Compared with what was held, matching on the project id:")
    say("  held now: %d. new: %d, unchanged: %d, renamed: %d, not returned: %d, returned again: %d"
        % (len(held), len(changes["new"]), len(changes["unchanged"]), len(changes["renamed"]),
           len(changes["not_returned"]), len(changes["returned"])))
    for project_id, moved in changes["renamed"]:
        for field, was, became in moved:
            say("  RENAMED: project id %s, %s was '%s' and is now '%s'. Same id, same record, same file."
                % (project_id, field, one_line(was), one_line(became)))
    for project_id in changes["not_returned"]:
        say("  NOT RETURNED: project id %s (key '%s', name '%s'). Kept and flagged, not deleted."
            % (project_id, one_line(held[project_id]["key"]), one_line(held[project_id]["name"])))
    for project_id in changes["returned"]:
        say("  returned again: project id %s (key '%s')." % (project_id, one_line(held[project_id]["key"])))
    say("")
    say("Last successful sync before this run: %s. Now: %s." % (before, now))
    say("Written: projects.md, projects.json and %d file(s) in projects/, each named by project id." % len(held))
    return 0


def screened(text, secrets):
    """The output, or a refusal in its place if it holds a credential or the site's address."""
    if any(secret and secret in text for secret in secrets):
        return "STOPPED: a credential or the site's address was found in the output, so the output was not printed.", False
    return text, True


def main():
    parser = argparse.ArgumentParser(description="List visible Jira projects and keep them by project id. Reads only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--out", required=True, help="folder to write into")
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    parser.add_argument("--fake-count", type=int, default=7, help="with --source fake: how many projects the fake holds")
    args = parser.parse_args()
    secrets = []
    try:
        if not 1 <= args.page_size <= 100:
            raise Stop("--page-size is a number from 1 to 100")
        if args.source == "fake":
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import fake_jira
            get = fake_jira.FakeJira(count=args.fake_count).get
        else:
            get, secrets = make_live_get()
        code = run(get, args.out, args.source, page_size=args.page_size)
    except Stop as stop:
        say("")
        say("STOPPED: %s." % stop)
        say("Nothing was written.")
        code = 1
    text, clean = screened("\n".join(LINES), secrets)
    print(text)
    if not clean:
        return 1
    if secrets:
        print("")
        print("The output above was searched for the API token, the account's email address, their encoded form")
        print("and the site's address: none found.")
    return code


if __name__ == "__main__":
    sys.exit(main())
