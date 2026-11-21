"""Jira read-assigned sync: read the settings, find the account, fetch the items, and write the outputs."""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")
SEARCH_PATH = "/rest/api/3/search/jql"
PAGE_SIZE = 100
FIXTURE_BASE_URL = "https://jira.example.invalid"
REPO = Path(__file__).resolve().parents[3]
OUT_DIR = REPO / "participant" / "context" / "jira" / "assigned"
# Participant notes, one file per story. The sync only checks whether a file exists; it never writes here.
NOTES_DIR = OUT_DIR / "notes"
# Delta mode keeps its cursor here. It is written last, and only after a whole delta run has succeeded.
STATE_PATH = REPO / "participant" / "context" / "jira" / "sync-state.md"
# Each delta run asks again for this much time before the cursor. It covers clock differences,
# Jira comparing dates to the minute, and Jira's search showing an edit a little late.
MARGIN_MINUTES = 5
JIRA_TIME = "%Y-%m-%dT%H:%M:%S.%f%z"
# Stories fetched by key are asked for in groups of this size, to keep each query short.
GAP_BATCH = 50
FIXTURE_DIR = REPO / "validators" / "fixtures" / "jira"
# Only these fields are requested. People, worklogs, attachments, links and custom fields
# are never asked for, so they cannot end up on disk.
STORY_FIELDS = (
    "summary,status,priority,assignee,labels,description,issuetype,created,updated,parent,comment,"
    "project,resolution,resolutiondate,duedate,components,fixVersions"
)


def read_settings() -> dict:
    """Return the three Jira settings, or stop and name the first one missing."""
    settings = {}
    for name in REQUIRED:
        value = os.environ.get(name, "").strip()
        if not value:
            sys.exit(f"Missing environment variable: {name}")
        settings[name] = value
    base_url = settings["JIRA_BASE_URL"].rstrip("/")
    if not base_url.startswith("https://"):
        sys.exit("JIRA_BASE_URL must start with https://, so credentials are never sent unencrypted.")
    settings["JIRA_BASE_URL"] = base_url
    return settings


def get_json(settings: dict, path: str) -> dict:
    """Send a read-only GET to Jira and return the parsed JSON response."""
    credentials = f"{settings['JIRA_EMAIL']}:{settings['JIRA_API_TOKEN']}"
    token = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        f"{settings['JIRA_BASE_URL']}{path}",
        headers={"Accept": "application/json", "Authorization": f"Basic {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            sys.exit("Jira rejected the credentials (401). Check JIRA_EMAIL and JIRA_API_TOKEN.")
        sys.exit(f"Jira returned HTTP {error.code}.")
    except urllib.error.URLError:
        sys.exit("Could not reach Jira. Check JIRA_BASE_URL.")


def find_account_id(settings: dict) -> str:
    """Ask Jira who the token belongs to, and return only the account ID."""
    return get_json(settings, "/rest/api/3/myself")["accountId"]


def search_all(settings: dict, jql: str, fields: str) -> list:
    """Follow nextPageToken until Jira returns none, and return every issue once."""
    issues = []
    seen_keys = set()
    seen_tokens = set()
    token = None
    while True:
        params = {"jql": jql, "maxResults": PAGE_SIZE, "fields": fields}
        if token:
            params["nextPageToken"] = token
        page = get_json(settings, f"{SEARCH_PATH}?{urllib.parse.urlencode(params)}")
        if not isinstance(page, dict) or not isinstance(page.get("issues"), list):
            sys.exit("Jira's answer to a search held no list of issues. Stopping, so it is not read as an empty result.")
        for issue in page["issues"]:
            if issue["key"] not in seen_keys:
                seen_keys.add(issue["key"])
                issues.append(issue)
        token = page.get("nextPageToken")
        if not token:
            return issues
        if token in seen_tokens:
            sys.exit("Jira sent a page token it had already sent. Stopping so the sync does not loop.")
        seen_tokens.add(token)


def _text(node) -> str:
    """Return the plain text inside an Atlassian Document Format node."""
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    if node.get("type") == "hardBreak":
        return "\n"
    return "".join(_text(child) for child in node.get("content", []))


LIST_TYPES = ("bulletList", "orderedList", "taskList")


def _item_text(item) -> str:
    """Return a list item as plain text: the first paragraph, or a checklist item's own text."""
    if item.get("type") == "taskItem":
        return _text(item).strip()
    for child in item.get("content", []):
        if child.get("type") == "paragraph":
            return _text(child).strip()
    return ""


def _block_markdown(node) -> str:
    """Convert one block-level Atlassian Document Format node to Markdown."""
    kind = node.get("type")
    if kind == "paragraph":
        return _text(node)
    if kind == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return f"{'#' * level} {_text(node)}"
    if kind in ("bulletList", "orderedList"):
        lines = []
        for number, item in enumerate(node.get("content", []), start=1):
            marker = f"{number}." if kind == "orderedList" else "-"
            lines.append(f"{marker} {_item_text(item)}")
        return "\n".join(lines)
    if kind == "taskList":
        lines = []
        for item in node.get("content", []):
            box = "[x]" if item.get("attrs", {}).get("state") == "DONE" else "[ ]"
            lines.append(f"- {box} {_item_text(item)}")
        return "\n".join(lines)
    if kind == "codeBlock":
        return f"```\n{_text(node)}\n```"
    return "\n\n".join(filter(None, (_block_markdown(child) for child in node.get("content", []))))


def adf_to_markdown(description) -> str:
    """Convert a Jira description to Markdown. A plain string passes through unchanged."""
    if not description:
        return ""
    if isinstance(description, str):
        return description
    return _block_markdown(description)


def _label(node):
    """Return the text of a heading, or of a paragraph that is entirely bold. Otherwise None."""
    if node.get("type") == "heading":
        return _text(node)
    if node.get("type") == "paragraph":
        parts = [c for c in node.get("content", []) if c.get("type") == "text" and c.get("text", "").strip()]
        if parts and all(any(mark.get("type") == "strong" for mark in c.get("marks", [])) for c in parts):
            return _text(node)
    return None


def acceptance_criteria(description) -> tuple:
    """Return (found, items): whether an "Acceptance criteria" label exists, and the list items under it.

    The label is a heading or an all-bold line, in any capitalization, with or without a colon.
    The section ends at the next label.
    """
    if not isinstance(description, dict):
        return False, []
    items = []
    found = False
    in_section = False
    for node in description.get("content", []):
        label = _label(node)
        if label is not None:
            if in_section:
                break
            in_section = label.strip().rstrip(":").strip().lower() == "acceptance criteria"
            found = found or in_section
            continue
        if in_section and node.get("type") in LIST_TYPES:
            items.extend(_item_text(item) for item in node.get("content", []))
    return found, [item for item in items if item]


def _comments(raw_comments: list, key: str, total, warnings: list) -> list:
    """Keep each comment's id and timestamps, once per id. Warn if Jira returned fewer than it holds."""
    if total is not None and total > len(raw_comments):
        warnings.append(f"{key}: {len(raw_comments)} of {total} comments came back; the rest were not fetched.")
    seen = set()
    records = []
    for comment in raw_comments:
        comment_id = str(comment["id"])
        if comment_id in seen:
            continue
        seen.add(comment_id)
        records.append({"id": comment_id, "created": comment.get("created"), "updated": comment.get("updated")})
    return records


def platform_fields(fields: dict) -> dict:
    """Keep a short, fixed list of extra Jira fields. Nothing else is copied."""
    return {
        "project": (fields.get("project") or {}).get("key"),
        "resolution": (fields.get("resolution") or {}).get("name"),
        "resolution_date": fields.get("resolutiondate"),
        "due_date": fields.get("duedate"),
        "components": [item.get("name") for item in fields.get("components") or []],
        "fix_versions": [item.get("name") for item in fields.get("fixVersions") or []],
    }


def record_from_issue(issue: dict, base_url: str, synced_at: str, warnings: list) -> dict:
    """Map one Jira issue to the canonical fields from section 6."""
    fields = issue["fields"]
    comment = fields.get("comment") or {}
    description = fields.get("description")
    criteria_found, criteria = acceptance_criteria(description)
    return {
        "key": issue["key"],
        "source_url": f"{base_url}/browse/{issue['key']}",
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "priority": (fields.get("priority") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("accountId"),
        "labels": fields.get("labels") or [],
        "description": adf_to_markdown(description),
        "acceptance_criteria": criteria,
        "acceptance_criteria_found": criteria_found,
        "issue_type": (fields.get("issuetype") or {}).get("name"),
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "parent": (fields.get("parent") or {}).get("key"),
        "comments": _comments(comment.get("comments", []), issue["key"], comment.get("total"), warnings),
        "retrieved_at": synced_at,
        "platform": platform_fields(fields),
    }


def record_from_fixture(item: dict, synced_at: str, warnings: list) -> dict:
    """Shape one fixture story like a live record. Fixtures carry only a few fields."""
    return {
        "key": item["key"],
        "source_url": f"{FIXTURE_BASE_URL}/browse/{item['key']}",
        "summary": item.get("summary"),
        "status": item.get("status"),
        "priority": None,
        "assignee": None,
        "labels": [],
        "description": "",
        "acceptance_criteria": [],
        "acceptance_criteria_found": False,
        "issue_type": None,
        "created": None,
        "updated": None,
        "parent": None,
        "comments": _comments(item.get("comments", []), item["key"], None, warnings),
        "retrieved_at": synced_at,
        "platform": {},
    }


def merge(current: list, prior: dict, earlier_removed: list) -> tuple:
    """Keep comments already stored, and report stories that are no longer returned instead of dropping them."""
    current_keys = {story["key"] for story in current}
    stories = []
    for record in current:
        old = prior.get(record["key"])
        if old:
            # Stored comments keep their place; Jira's newer timestamps replace the stored ones.
            fresh = {comment["id"]: comment for comment in record["comments"]}
            known = {comment["id"] for comment in old.get("comments", [])}
            record["comments"] = [fresh.get(comment["id"], comment) for comment in old.get("comments", [])] + [
                comment for comment in record["comments"] if comment["id"] not in known
            ]
        stories.append(record)
    removed = [entry for entry in earlier_removed if entry["key"] not in current_keys]
    reported = {entry["key"] for entry in removed}
    for key, old in prior.items():
        if key not in current_keys and key not in reported:
            removed.append({"key": key, "last_known_status": old.get("status")})
    return stories, removed


def load_existing() -> dict:
    """Return the previous stories.json, or an empty one if none exists. Stop rather than overwrite a broken file."""
    path = OUT_DIR / "stories.json"
    if not path.exists():
        return {"stories": [], "removed": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.exit("The previous stories.json is not valid JSON. Fix or move it, then run again.")


def fixture_path(source: str) -> Path:
    """Accept a fixture name such as happy-path, or a path. Only files in validators/fixtures/jira/ are allowed."""
    path = FIXTURE_DIR / f"{source}.json" if "/" not in source else REPO / source
    path = path.resolve()
    if path.parent != FIXTURE_DIR.resolve() or path.suffix != ".json":
        sys.exit("A fixture must be a .json file inside validators/fixtures/jira/.")
    if not path.exists():
        sys.exit(f"Fixture not found: {source}")
    return path


def type_counts(others: list) -> Counter:
    """Count the assigned items that are not stories, by issue type."""
    return Counter(item["fields"]["issuetype"]["name"] for item in others)


def gather_live(settings: dict, synced_at: str, warnings: list) -> tuple:
    account_id = find_account_id(settings)
    raw_stories = search_all(settings, f'assignee = "{account_id}" AND issuetype = Story', STORY_FIELDS)
    others = search_all(settings, f'assignee = "{account_id}" AND issuetype != Story', "key,issuetype")
    current = [record_from_issue(issue, settings["JIRA_BASE_URL"], synced_at, warnings) for issue in raw_stories]
    previous = load_existing()
    # Merge only with earlier live output. A file with no source is treated as live, to be safe.
    if previous.get("source", "live") != "live":
        if previous.get("stories") or previous.get("removed"):
            warnings.append(f"the previous stories.json came from the {previous['source']!r} fixture, so it was replaced, not merged.")
        return current, {}, [], others, "live"
    prior = {story["key"]: story for story in previous.get("stories", [])}
    return current, prior, previous.get("removed", []), others, "live"


def gather_fixture(source: str, synced_at: str, warnings: list) -> tuple:
    """Fixture runs ignore the previous stories.json, so every rerun gives the same result.

    A fixture run never replaces live data: if stories.json holds live stories or removed entries,
    the run stops before anything is written.
    """
    path = fixture_path(source)
    previous = load_existing()
    if previous.get("source", "live") == "live" and (previous.get("stories") or previous.get("removed")):
        sys.exit(
            "stories.json holds live Jira data, and a fixture run would replace it. "
            "Move it aside first (for example to stories.live.json), then run again."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    current = [record_from_fixture(item, synced_at, warnings) for item in data["stories"]]
    prior = {
        item["key"]: {"key": item["key"], "status": item.get("status"), "comments": []}
        for item in data.get("previously_assigned", [])
    }
    return current, prior, [], [], path.stem


def cell(value) -> str:
    """Make a value safe for one Markdown table cell."""
    return ("" if value is None else str(value)).replace("|", "\\|").replace("\n", " ")


def notes_link(key: str) -> str:
    """Link to the participant's notes file for a story, if there is one."""
    return f"[notes](notes/{key}.md)" if (NOTES_DIR / f"{key}.md").is_file() else ""


def index_markdown(stories: list, removed: list, others: list, source: str, synced_at: str) -> str:
    lines = [
        "# Assigned Jira stories",
        "",
        f"Source: {source}. Synced at {synced_at}.",
        "",
        "| Key | Summary | Status | Type | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for story in stories:
        lines.append(
            f"| {cell(story['key'])} | {cell(story['summary'])} | {cell(story['status'])} "
            f"| {cell(story['issue_type'])} | {notes_link(story['key'])} |"
        )
    if not stories:
        lines.append("| No stories assigned. | | | | |")
    if removed:
        lines += ["", "## Removed", "", "| Key | Last known status |", "| --- | --- |"]
        lines += [f"| {cell(entry['key'])} | {cell(entry['last_known_status'])} |" for entry in removed]
    missing = [story for story in stories if not story.get("acceptance_criteria")]
    if missing:
        lines += ["", "## Missing acceptance criteria", "", "| Key | Reason |", "| --- | --- |"]
        for story in missing:
            reason = "heading with no items" if story.get("acceptance_criteria_found") else "no heading"
            lines.append(f"| {cell(story['key'])} | {reason} |")
    lines += ["", "## Not synced", ""]
    counts = type_counts(others)
    if not counts:
        lines.append("No other work items are assigned.")
    else:
        lines += ["| Type | Count | Keys |", "| --- | --- | --- |"]
        for name, count in sorted(counts.items()):
            keys = ", ".join(sorted(item["key"] for item in others if item["fields"]["issuetype"]["name"] == name))
            lines.append(f"| {cell(name)} | {count} | {cell(keys)} |")
    return "\n".join(lines) + "\n"


def write_atomic(path: Path, text: str) -> None:
    """Write to a temporary file, then move it into place, so a failure never leaves a half-written file."""
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, path)
    except OSError:
        temp.unlink(missing_ok=True)
        raise


def write_outputs(stories: list, removed: list, others: list, source: str, synced_at: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {"source": source, "synced_at": synced_at, "stories": stories, "removed": removed}
    write_atomic(OUT_DIR / "stories.json", json.dumps(data, indent=2) + "\n")
    write_atomic(OUT_DIR / "index.md", index_markdown(stories, removed, others, source, synced_at))


def jira_time_ms(value: str) -> int:
    """Turn a Jira timestamp such as 2026-11-02T09:00:00.000+0000 into milliseconds since 1970, whatever its offset."""
    return int(datetime.strptime(value, JIRA_TIME).timestamp() * 1000)


def read_cursor():
    """Return the saved cursor, or None if no delta run has succeeded yet. Stop rather than guess if the file is unreadable."""
    if not STATE_PATH.exists():
        return None
    for line in STATE_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("- cursor: "):
            value = line[len("- cursor: "):].strip()
            if value == "none":
                return None
            try:
                jira_time_ms(value)
            except ValueError:
                break
            return value
    sys.exit(f"{STATE_PATH.name} exists but holds no readable cursor. Fix or move it, then run again.")


def state_markdown(cursor, synced_at: str, counts: dict) -> str:
    lines = [
        "# Jira sync state",
        "",
        "Written by `participant/skills/jira-read-assigned/sync.py --delta`. Do not edit by hand.",
        "",
        f"- cursor: {cursor or 'none'}",
        f"- last_successful_sync: {synced_at}",
        f"- safety_margin_minutes: {MARGIN_MINUTES}",
        "- source: live",
        "- last_run: " + ", ".join(f"{name} {counts[name]}" for name in ("fetched", "new", "changed", "unchanged", "removed")),
        "",
        "## What the cursor is",
        "",
        "The cursor is the newest `updated` timestamp Jira has sent for a story that was held in `assigned/stories.json`",
        "when a delta run finished. It stays where it is if that story later leaves the list.",
        "It is Jira's own timestamp, copied as Jira sent it. This machine's clock is never used to build a query.",
        "`last_successful_sync` is this machine's clock and is here for people to read; no query uses it.",
        "",
        "## How it is updated",
        "",
        "1. A delta run reads the cursor and asks Jira for stories updated at or after the cursor minus the safety margin.",
        "2. It lists every story assigned now with its key and updated time only. A story that left the list is",
        "   reported as removed. A listed story whose local copy is missing or has a different updated time is fetched by key.",
        "3. It merges what came back into `stories.json`, matching on the Jira key, and rewrites `index.md`.",
        "4. Last of all, it writes this file with the new cursor.",
        "",
        "If any request or write in steps 1 to 3 fails, the run stops before step 4 and this file is left as it was.",
        "The next run asks the same question again. Stories fetched twice are matched on their key, so nothing is duplicated.",
        "The cursor never moves backward.",
        "",
    ]
    return "\n".join(lines)


def _same_story(a: dict, b: dict) -> bool:
    """Two records hold the same story content. When each was fetched does not count."""
    strip = lambda record: {k: v for k, v in record.items() if k != "retrieved_at"}  # noqa: E731
    return strip(a) == strip(b)


def _same_time(a, b) -> bool:
    """Two Jira timestamps name the same instant, whatever their offsets. Unreadable values are compared as text."""
    try:
        return jira_time_ms(a) == jira_time_ms(b)
    except (TypeError, ValueError):
        return a == b


def run_delta(settings: dict, synced_at: str, warnings: list) -> None:
    """Fetch only the stories updated since the last successful delta run, and save the cursor last."""
    cursor = read_cursor()
    previous = load_existing()
    if previous.get("source", "live") != "live":
        if previous.get("stories") or previous.get("removed"):
            warnings.append(f"the previous stories.json came from the {previous['source']!r} fixture, so it was replaced, not merged.")
        previous = {"stories": [], "removed": []}
    prior = {story["key"]: story for story in previous.get("stories", [])}
    since = cursor
    if cursor and not prior:
        warnings.append("a cursor is saved but no stories are stored locally, so everything was fetched.")
        since = None

    account_id = find_account_id(settings)
    assigned = f'assignee = "{account_id}" AND issuetype = Story'
    if since:
        threshold = jira_time_ms(since) - MARGIN_MINUTES * 60 * 1000
        # An unquoted number in JQL is milliseconds since 1970, so no time zone is involved.
        raw = search_all(settings, f"{assigned} AND updated >= {threshold}", STORY_FIELDS)
        # A cheap list of everything assigned now: the key and the updated time, nothing else.
        listed = {issue["key"]: issue["fields"].get("updated") for issue in search_all(settings, assigned, "key,updated")}
    else:
        raw = search_all(settings, assigned, STORY_FIELDS)
        listed = {}
    assigned_now = set(listed)
    # Every story Jira lists as assigned must end up held and current. A listed story that the filtered
    # search did not return is fetched by its key when it is not stored, or when the stored copy's
    # updated time differs from the listed one. That covers a story that came back without a newer
    # timestamp, a cursor that is too far ahead, an older stories.json, and an edit Jira showed very late.
    returned = {issue["key"] for issue in raw}
    gap = sorted(key for key, updated in listed.items()
                 if key not in returned and (key not in prior or not _same_time(prior[key].get("updated"), updated)))
    for start in range(0, len(gap), GAP_BATCH):
        keys = ", ".join(f'"{key}"' for key in gap[start:start + GAP_BATCH])
        raw += search_all(settings, f"{assigned} AND key in ({keys})", STORY_FIELDS)
    by_key = [key for key in gap if key in {issue["key"] for issue in raw}]
    not_returned = [key for key in gap if key not in by_key]
    if by_key:
        warnings.append(f"{len(by_key)} assigned stories were missing or out of date locally and were fetched by key: {', '.join(by_key)}.")
    if not_returned:
        warnings.append(f"{len(not_returned)} stories were listed as assigned but not returned when asked for by key, "
                        f"so the local copy was left as it was: {', '.join(not_returned)}.")
    listed = {key: updated for key, updated in listed.items() if key not in not_returned or key in prior}
    assigned_now = set(listed)
    others = search_all(settings, f'assignee = "{account_id}" AND issuetype != Story', "key,issuetype")

    fetched = []
    for issue in raw:
        if issue["key"] not in {record["key"] for record in fetched}:
            fetched.append(record_from_issue(issue, settings["JIRA_BASE_URL"], synced_at, warnings))
    assigned_now |= {record["key"] for record in fetched}
    # Reuse the full sync's comment rules for the stories that came back.
    merged, _ = merge(fetched, {r["key"]: prior[r["key"]] for r in fetched if r["key"] in prior}, [])
    counts = {"fetched": len(fetched), "new": 0, "changed": 0, "unchanged": 0, "removed": 0}
    latest = {}
    for record in merged:
        old = prior.get(record["key"])
        if old is None:
            counts["new"] += 1
            latest[record["key"]] = record
        elif _same_story(record, old):
            latest[record["key"]] = old  # fetched again inside the margin, and identical: keep the stored copy
        else:
            counts["changed"] += 1
            latest[record["key"]] = record

    # A story that was not returned did not change. It is kept exactly as stored, unless it left the list.
    stories = [latest.pop(key, old) for key, old in prior.items() if key in assigned_now]
    stories += list(latest.values())
    counts["unchanged"] = len(stories) - counts["new"] - counts["changed"]
    held = {story["key"] for story in stories}
    # A removed entry is dropped only when the story is really held again, not because its key was listed.
    removed = [entry for entry in previous.get("removed", []) if entry["key"] not in held]
    for key, old in prior.items():
        if key not in assigned_now:
            removed.append({"key": key, "last_known_status": old.get("status")})
            counts["removed"] += 1

    new_cursor = cursor
    newest_ms = jira_time_ms(cursor) if cursor else None
    for story in stories:
        value = story.get("updated")
        if not value:
            continue
        try:
            value_ms = jira_time_ms(value)
        except (TypeError, ValueError):
            # A value the cursor reader would reject is never saved as the cursor.
            warnings.append(f"{story['key']}: its updated time could not be read, so it was not used for the cursor.")
            continue
        if newest_ms is None or value_ms > newest_ms:
            new_cursor, newest_ms = value, value_ms

    write_outputs(stories, removed, others, "live", synced_at)
    # The cursor is written last. Anything that stops the run before this line leaves the old cursor in place.
    write_atomic(STATE_PATH, state_markdown(new_cursor, synced_at, counts))

    if since:
        print(f"mode: delta, asking for stories updated since {since} minus {MARGIN_MINUTES} minutes")
    else:
        print("mode: delta, no usable cursor yet, so everything was fetched")
    for name in ("fetched", "new", "changed", "unchanged", "removed"):
        print(f"{name}: {counts[name]}")
    print(f"stories held: {len(stories)}")
    print(f"removed held: {len(removed)}")
    print(f"cursor before: {cursor or 'none'}")
    print(f"cursor after: {new_cursor or 'none'}")
    for warning in warnings:
        print(f"warning: {warning}")
    print(f"wrote {OUT_DIR / 'stories.json'}, {OUT_DIR / 'index.md'} and {STATE_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync my assigned Jira stories to local files.")
    parser.add_argument("--source", default="live", help='"live" (the default), or a fixture name such as happy-path')
    parser.add_argument("--delta", action="store_true", help="fetch only stories updated since the last successful delta run (live only)")
    args = parser.parse_args()
    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warnings: list = []
    if args.delta:
        if args.source != "live":
            sys.exit("--delta works on live Jira only, not on a fixture.")
        run_delta(read_settings(), synced_at, warnings)
        return
    if args.source == "live":
        current, prior, earlier_removed, others, source = gather_live(read_settings(), synced_at, warnings)
    else:
        current, prior, earlier_removed, others, source = gather_fixture(args.source, synced_at, warnings)
    stories, removed = merge(current, prior, earlier_removed)
    write_outputs(stories, removed, others, source, synced_at)
    print(f"stories: {len(stories)}")
    print(f"removed: {len(removed)}")
    print(f"missing acceptance criteria: {sum(not s.get('acceptance_criteria') for s in stories)}")
    print(f"other items: {len(others)}")
    for name, count in sorted(type_counts(others).items()):
        print(f"  {name}: {count}")
    for warning in warnings:
        print(f"warning: {warning}")
    print(f"wrote {OUT_DIR / 'stories.json'} and {OUT_DIR / 'index.md'}")


if __name__ == "__main__":
    main()
