#!/usr/bin/env python3
"""A fake Jira for testing the project list in the jira-list-projects quest. No network.

It holds made-up projects in memory and answers the one read request the
skill makes for them, GET /rest/api/3/project/search, in the shape Jira's
published API specification describes: a page of `values`, with `startAt`,
`maxResults`, `total` and `isLast`.

Each project has an id, a key and a name. The id never changes. A test can
rename a project (its key, its name, or both), remove one, and add one.

Like Jira, it gives at most `page_cap` projects in a page, whatever is asked
for. It can also be made to misbehave, to test that a short read is not taken
for a whole one:

    quirk = "says_last_early"   the first page claims to be the last
    quirk = "ignores_start"     every request returns the first page
    quirk = "no_is_last"        pages carry no isLast (total is still given)
    quirk = "no_total"          pages carry no total

It is a stand-in, built from the specification and not checked against Jira
field by field.

The skill talks to Jira through one function, get(path, params) ->
(status, headers, body). `FakeJira.get` is that function. Every request it
receives is kept in `.requests`.
"""

NAMES = ["Billing", "Customer portal", "Data platform", "Design system", "Mobile app", "Onboarding", "Search"]
ME = "5b10a0000000000000000001"


class FakeJira:
    def __init__(self, count=7, page_cap=50):
        self.projects = []
        self.page_cap = page_cap
        self.quirk = None
        self.requests = []
        self.credentials_ok = True
        self._next_id = 10001
        self._failures = []
        for n in range(count):
            name = NAMES[n] if n < len(NAMES) else "Project %03d" % (n + 1)
            key = ("".join(word[0] for word in name.split()) + name.replace(" ", "")[1:3]).upper() if n < len(NAMES) \
                else "P%03d" % (n + 1)
            self.add(key, name)

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
            return 200, {}, {"accountId": ME, "accountType": "atlassian", "active": True,
                             "displayName": "Not Used", "emailAddress": "not-used@example.invalid"}
        if path == "/rest/api/3/project/search":
            rows = sorted(self.projects, key=lambda p: p["key"])
            start = 0 if self.quirk == "ignores_start" else int(params.get("startAt", 0))
            size = max(1, min(int(params.get("maxResults", 50)), self.page_cap))
            page = rows[start:start + size]
            body = {"startAt": start, "maxResults": size, "total": len(rows), "isLast": start + size >= len(rows),
                    "values": [{"id": p["id"], "key": p["key"], "name": p["name"], "self": "not-used",
                                "projectTypeKey": "software"} for p in page]}
            if self.quirk == "says_last_early":
                body["isLast"] = True
            if self.quirk == "no_is_last":
                del body["isLast"]
            if self.quirk == "no_total":
                del body["total"]
            return 200, {}, body
        return 404, {}, {"errorMessages": ["Not found."]}

    # ------------------------------------------------------------ changes a test can make

    def add(self, key, name):
        project = {"id": str(self._next_id), "key": key, "name": name}
        self._next_id += 1
        self.projects.append(project)
        return project["id"]

    def by_key(self, key):
        return [p for p in self.projects if p["key"] == key][0]

    def rename(self, project_id, key=None, name=None):
        project = [p for p in self.projects if p["id"] == project_id][0]
        project["key"] = key or project["key"]
        project["name"] = name or project["name"]

    def remove(self, project_id):
        self.projects = [p for p in self.projects if p["id"] != project_id]

    def fail(self, path_prefix, status, times=-1):
        self._failures.append([path_prefix, status, times])


if __name__ == "__main__":
    for project in FakeJira().projects:
        print("%s  %-6s %s" % (project["id"], project["key"], project["name"]))
