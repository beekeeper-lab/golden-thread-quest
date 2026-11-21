#!/usr/bin/env python3
"""A fake Jira for testing the connection check in the jira-verify-connection quest. No network.

It holds a made-up Jira site in memory and answers the read requests the
check makes, in the shape Jira's published API specification describes.

The site has four projects, chosen so that the cases the quest cares about
are all present:

    ALPHA   visible to the connection, with three stories
    EMPTY   visible to the connection, with no stories at all
    HIDDEN  exists, but the connection is not allowed to see it
    (and any other key does not exist)

Jira answers 404 for a project that does not exist and for one the
connection may not see, with one description for both. The fake does the same.

What Jira does when a search names a project the connection cannot see is not
stated in the specification. So the fake can do either, chosen by
`search_hidden`:

    "error"   answer 400, with a message that the project does not exist
    "empty"   answer 200 with no issues, exactly as for a project with none

The second is the dangerous one, and the check has to be right under both.

It is a stand-in, built from the specification and not checked against Jira
field by field.

The check talks to Jira through one function, get(path, params) ->
(status, headers, body). `FakeJira.get` is that function. Every request it
receives is kept in `.requests`.

Run this file to print the made-up site:  python3 fake_jira.py
"""
import json
import re

ME = {"accountId": "5b10a0000000000000000001", "accountType": "atlassian", "active": True,
      "displayName": "Not Used", "emailAddress": "not-used@example.invalid"}

PERMISSION_NAMES = {"BROWSE_PROJECTS": "Browse Projects", "CREATE_ISSUES": "Create Issues",
                    "EDIT_ISSUES": "Edit Issues", "DELETE_ISSUES": "Delete Issues",
                    "ADMINISTER_PROJECTS": "Administer Projects"}


def make_site():
    return {
        "ALPHA": {"id": "10001", "name": "Alpha sandbox", "visible": True,
                  "grants": {"BROWSE_PROJECTS"},
                  "issues": [("ALPHA-1", "Export the weekly report", "To Do"),
                             ("ALPHA-2", "Search by title", "In Progress"),
                             ("ALPHA-3", "Remove old banner", "Done")]},
        "EMPTY": {"id": "10002", "name": "Empty sandbox", "visible": True,
                  "grants": {"BROWSE_PROJECTS"}, "issues": []},
        "HIDDEN": {"id": "10003", "name": "Hidden from this connection", "visible": False,
                   "grants": set(), "issues": [("HIDDEN-1", "A story the connection must not read", "To Do")]},
    }


class FakeJira:
    def __init__(self, search_hidden="error"):
        self.site = make_site()
        self.me = dict(ME)
        self.search_hidden = search_hidden
        self.requests = []       # every (path, params) asked for
        self.credentials_ok = True
        self._failures = []      # [path prefix, status, how many more times]

    def get(self, path, params=None):
        params = dict(params or {})
        self.requests.append((path, params))
        for failure in self._failures:
            if path.startswith(failure[0]) and failure[2] != 0:
                failure[2] -= 1
                return failure[1], {}, {"errorMessages": ["fake failure"]}
        if not self.credentials_ok:
            return 401, {}, {"errorMessages": ["Client must be authenticated to access this resource."]}
        if path == "/rest/api/3/myself":
            return 200, {}, dict(self.me)
        if path == "/rest/api/3/project/search":
            visible = sorted(key for key, project in self.site.items() if project["visible"])
            start, size = int(params.get("startAt", 0)), min(int(params.get("maxResults", 50)), 100)
            page = visible[start:start + size]
            return 200, {}, {"startAt": start, "maxResults": size, "total": len(visible),
                             "isLast": start + size >= len(visible),
                             "values": [{"id": self.site[k]["id"], "key": k, "name": self.site[k]["name"]} for k in page]}
        if path.startswith("/rest/api/3/project/"):
            key = path.rsplit("/", 1)[1]
            project = self.site.get(key)
            if project is None or not project["visible"]:
                return 404, {}, {"errorMessages": ["No project could be found with key '%s'." % key]}
            return 200, {}, {"id": project["id"], "key": key, "name": project["name"]}
        if path == "/rest/api/3/mypermissions":
            project = self.site.get(params.get("projectKey", ""))
            if project is None or not project["visible"]:
                return 404, {}, {"errorMessages": ["No project could be found with key '%s'." % params.get("projectKey")]}
            if not params.get("permissions"):
                return 400, {}, {"errorMessages": ["The 'permissions' query parameter is required."]}
            return 200, {}, {"permissions": {
                key: {"key": key, "name": PERMISSION_NAMES.get(key, key), "havePermission": key in project["grants"]}
                for key in params["permissions"].split(",")}}
        if path == "/rest/api/3/search/jql":
            match = re.match(r'project = "([A-Za-z0-9_]+)"', params.get("jql", ""))
            if not match:
                return 400, {}, {"errorMessages": ["The search request is invalid."]}
            project = self.site.get(match.group(1))
            if project is None or not project["visible"]:
                if self.search_hidden == "error":
                    return 400, {}, {"errorMessages": ["The value '%s' does not exist for the field 'project'."
                                                       % match.group(1)]}
                return 200, {}, {"issues": [], "isLast": True}
            issues = project["issues"][: int(params.get("maxResults", 50))]
            return 200, {}, {"isLast": True, "issues": [
                {"id": str(20000 + n), "key": key, "fields": {"summary": summary, "status": {"name": status}}}
                for n, (key, summary, status) in enumerate(issues)]}
        return 404, {}, {"errorMessages": ["Not found."]}

    # ------------------------------------------------------------ changes a test can make

    def lose_access(self, key):
        """The connection can no longer see this project. The project still exists."""
        self.site[key]["visible"] = False

    def grant(self, key, permission):
        self.site[key]["grants"].add(permission)

    def fail(self, path_prefix, status, times=-1):
        self._failures.append([path_prefix, status, times])


if __name__ == "__main__":
    site = make_site()
    for project in site.values():
        project["grants"] = sorted(project["grants"])
    print(json.dumps(site, indent=2))
