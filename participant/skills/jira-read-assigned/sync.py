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
        for issue in page.get("issues", []):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync my assigned Jira stories to local files.")
    parser.add_argument("--source", default="live", help='"live" (the default), or a fixture name such as happy-path')
    args = parser.parse_args()
    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warnings: list = []
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
