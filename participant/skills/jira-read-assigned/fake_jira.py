"""A fake Jira for the delta-sync quest. It answers sync.py's read-only requests from delta_fixture/timeline.json.

It stands in for sync.get_json. It never touches the network. It can be told to fail on a
chosen request, the same way the real get_json stops when Jira returns an error.
"""
import json
import re
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

TIMELINE = Path(__file__).resolve().parent / "delta_fixture" / "timeline.json"


def to_ms(jira_timestamp: str) -> int:
    """Turn a Jira timestamp such as 2026-11-02T09:00:00.000+0000 into milliseconds since 1970."""
    return int(datetime.strptime(jira_timestamp, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp() * 1000)


def _stored_ms(jira_timestamp: str) -> int:
    """How the fake itself reads a ticket's time when filtering. Unlike to_ms, it also accepts a time without milliseconds."""
    try:
        return to_ms(jira_timestamp)
    except ValueError:
        return int(datetime.strptime(jira_timestamp, "%Y-%m-%dT%H:%M:%S%z").timestamp() * 1000)


class FakeJira:
    def __init__(self, page_size: int = 2, timeline_path: Path = TIMELINE):
        self.timeline = json.loads(Path(timeline_path).read_text(encoding="utf-8"))
        self.page_size = page_size
        self.moment = 0
        self.requests = []
        self.fail_on_search_number = None  # e.g. 2: the second search request of a run stops with an error
        self.fail_on_request_number = None  # counts every request since `requests` was last cleared, /myself included
        self._searches = 0

    def at(self, moment_name: str) -> "FakeJira":
        names = [m["name"] for m in self.timeline["moments"]]
        self.moment = names.index(moment_name)
        self._searches = 0
        return self

    def _snapshot(self) -> dict:
        moment = self.timeline["moments"][self.moment]
        if "same_as" in moment:
            moment = next(m for m in self.timeline["moments"] if m["name"] == moment["same_as"])
        return moment

    def _issue(self, story: dict) -> dict:
        account = self.timeline["account_id"]
        comments = [{"id": cid, "created": story["updated"], "updated": story["updated"],
                     "body": "synthetic comment", "author": {"accountId": "acc-other"}} for cid in story["comments"]]
        return {"key": story["key"], "fields": {
            "summary": story["summary"], "status": {"name": story["status"]}, "issuetype": {"name": "Story"},
            "assignee": {"accountId": account}, "labels": [], "description": None,
            "created": "2026-11-01T09:00:00.000+0000", "updated": story["updated"],
            "comment": {"comments": comments, "total": len(comments)}, "project": {"key": "GTQ"},
        }}

    def get_json(self, settings: dict, path: str) -> dict:
        self.requests.append(path)
        if self.fail_on_request_number == len(self.requests):
            sys.exit("Jira returned HTTP 503.")
        if path.startswith("/rest/api/3/myself"):
            return {"accountId": self.timeline["account_id"]}
        self._searches += 1
        if self.fail_on_search_number == self._searches:
            sys.exit("Jira returned HTTP 503.")
        query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        jql = query["jql"][0]
        snapshot = self._snapshot()
        if "issuetype != Story" in jql:
            issues = [{"key": o["key"], "fields": {"issuetype": {"name": o["type"]}}} for o in snapshot["others"]]
        else:
            issues = [self._issue(s) for s in sorted(snapshot["stories"], key=lambda s: s["key"])]
            since = re.search(r"updated >= (\d+)", jql)
            if since:
                issues = [i for i in issues if _stored_ms(i["fields"]["updated"]) >= int(since.group(1))]
            named = re.search(r"key in \(([^)]*)\)", jql)
            if named:
                keys = {part.strip().strip('"') for part in named.group(1).split(",")}
                issues = [i for i in issues if i["key"] in keys]
            wanted = set(query["fields"][0].split(","))
            issues = [{"key": i["key"], "fields": {k: v for k, v in i["fields"].items() if k in wanted}} for i in issues]
        start = int(query["nextPageToken"][0][1:]) if "nextPageToken" in query else 0
        response = {"issues": issues[start:start + self.page_size]}
        if start + self.page_size < len(issues):
            response["nextPageToken"] = f"t{start + self.page_size}"
        return response
