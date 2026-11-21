#!/usr/bin/env python3
"""A fake Jira that accepts the creation of a story, for testing the create workflow. No network.

It is the read-only fake of the jira-create-story-preview skill with one
thing added: POST /rest/api/3/issue. The projects, the nine stories and what
project RPT requires of a Story are the same as there:

    Summary and Components   required, no default.
    Team                     required, default Support.
    Priority                 required, default Medium.
    Reporter                 required, default the identity itself.

A create is answered as Jira's specification describes: 201 with the new
story's `id`, `key` and `self`, or 400 with the fields at fault. The story it
stores has what was sent, and what Jira would add: a status, a reporter, the
defaults, and the times it was created and updated. It gives each component,
priority and choice back with its name as well as its id, as Jira does.

It also answers the two searches the workflow makes with JQL:

    project = ID AND labels = "a-label"
    project = ID AND summary ~ "\\"some words\\""

Things a test can make it do:

    fail_post     answer the next create with this status and create nothing;
                  or "timeout" to raise TimeoutError and create nothing; or
                  "applied-timeout" to create the story and then raise, as
                  when the answer is lost on the way back.
    decorate      give the description back with identifiers added to each
                  block, as Jira may. The text and structure are unchanged.
    corrupt       a function applied to the stored fields after a create, to
                  play Jira storing something other than what was sent.
    search_lag    the label search finds nothing this many times before it
                  finds the story, as a search index that lags behind.

Used from the command line it keeps its stories in one JSON file, so that a
preview and a later confirmation see the same Jira:

    fake_jira.py show --state FOLDER
    fake_jira.py rename --state FOLDER --story RPT-10 --to RPT-99

Every project, person and site here is invented.
"""
import argparse
import copy
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "preview_fake_jira", os.path.join(HERE, "..", "jira-create-story-preview", "fake_jira.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

SITE, ME, PROJECTS = base.SITE, base.ME, base.PROJECTS


class FakeJira(base.FakeJira):
    def __init__(self, saved=None):
        super().__init__()
        self.next_number = {"30000": 10, "30100": 13, "30200": 1}
        self.next_id = 30010
        self.clock = 0
        self.fail_post = None
        self.decorate = False
        self.corrupt = None
        self.search_lag = 0
        self.bodies = []
        for item in self.issues:
            item["fields"]["labels"] = []
        if saved:
            self.issues, self.next_number, self.next_id, self.clock = (saved["issues"], saved["next_number"],
                                                                       saved["next_id"], saved["clock"])

    @classmethod
    def open(cls, path):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return cls(json.load(f))
        return cls()

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"issues": self.issues, "next_number": self.next_number, "next_id": self.next_id, "clock": self.clock},
                      f, indent=1, sort_keys=True)
            f.write("\n")

    def now(self):
        self.clock += 1
        return (datetime.datetime(2026, 11, 19, 12, 0, 0) + datetime.timedelta(seconds=self.clock)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")

    # ------------------------------------------------------------ reading

    def get(self, path, params=None):
        params = params or {}
        jql = str(params.get("jql", ""))
        label = re.fullmatch(r'project = (\d+) AND labels = "([a-z0-9-]+)"', jql)
        title = re.fullmatch(r'project = (\d+) AND summary ~ "\\"(.*)\\""', jql)
        if path == "/rest/api/3/search/jql" and (label or title):
            self.requests.append(("GET", path))
            if label and self.search_lag > 0:
                self.search_lag -= 1
                return 200, {}, {"issues": []}
            found = []
            for item in self.issues:
                fields = item["fields"]
                if fields["project"]["id"] != (label or title).group(1):
                    continue
                if label and label.group(2) in fields.get("labels", []):
                    found.append({"id": item["id"], "key": item["key"], "fields": {"labels": fields["labels"]}})
                if title and title.group(2).replace('\\"', '"').lower() in str(fields["summary"]).lower():
                    found.append({"id": item["id"], "key": item["key"], "fields": {"summary": fields["summary"]}})
            return 200, {}, {"issues": found}
        if re.fullmatch(r"/rest/api/3/issue/[^/]+", path) and params.get("expand") == "names":
            status, headers, body = super().get(path, {})
            if status == 200:
                names = {field["fieldId"]: field["name"] for field in self.fields["30000"]}
                names.update({"status": "Status", "created": "Created", "updated": "Updated", "creator": "Creator",
                              "assignee": "Assignee", "resolution": "Resolution"})
                body["names"] = names
            return status, headers, body
        return super().get(path, params)

    # ------------------------------------------------------------ creating

    def post(self, path, params=None, body=None):
        self.requests.append(("POST", path))
        self.bodies.append(body)
        if self.fail_post == "timeout":
            raise TimeoutError("the fake did not answer")
        if isinstance(self.fail_post, int):
            return self.fail_post, {}, {"errorMessages": ["The fake was told to answer %d." % self.fail_post], "errors": {}}
        if path != "/rest/api/3/issue":
            return 404, {}, {}
        try:
            sent = json.loads(body.decode("utf-8"))["fields"]
            project_id = sent["project"]["id"]
        except (ValueError, KeyError, TypeError, AttributeError):
            return 400, {}, {"errorMessages": ["The request body could not be read."], "errors": {}}
        if project_id not in PROJECTS or not self.may_create[project_id]:
            return 400, {}, {"errorMessages": ["No permission to create in this project."], "errors": {}}
        meta = {field["fieldId"]: field for field in self.fields[project_id]}
        errors = {}
        for name in sent:
            if name not in meta:
                errors[name] = "Field '%s' cannot be set. It is not on the appropriate screen, or unknown." % name
        for name, field in meta.items():
            if field["required"] and not field["hasDefaultValue"] and name not in sent:
                errors[name] = "%s is required." % field["name"]
        if errors:
            return 400, {}, {"errorMessages": [], "errors": errors}

        def chosen(name, key):
            allowed = {value["id"]: value for value in meta[name].get("allowedValues", [])}
            return {"id": sent[name]["id"], key: allowed[sent[name]["id"]][key]} if name in sent else \
                {"id": meta[name]["defaultValue"]["id"], key: meta[name]["defaultValue"][key]}
        stamp = self.now()
        number = self.next_number[project_id]
        self.next_number[project_id] += 1
        issue_id = str(self.next_id)
        self.next_id += 1
        description = copy.deepcopy(sent.get("description"))
        if description and self.decorate:
            for position, block in enumerate(description["content"]):
                block["attrs"] = {"localId": "block-%d" % position}
        components = {value["id"]: value["name"] for value in meta["components"]["allowedValues"]}
        parent = None
        if "parent" in sent:
            found = self.find(sent["parent"].get("key") or sent["parent"].get("id"))
            parent = {"id": found["id"], "key": found["key"]} if found else None
        fields = {"summary": sent["summary"], "description": description,
                  "project": {"id": project_id, "key": PROJECTS[project_id], "name": "Made-up project %s" % PROJECTS[project_id]},
                  "issuetype": {"id": sent["issuetype"]["id"], "name": "Story"},
                  "labels": sorted(sent.get("labels", [])), "duedate": sent.get("duedate"),
                  "components": [{"id": item["id"], "name": components[item["id"]]} for item in sent.get("components", [])],
                  "priority": chosen("priority", "name"), "customfield_10050": chosen("customfield_10050", "value"),
                  "customfield_10016": None, "parent": parent,
                  "status": {"id": "1", "name": "To Do"}, "resolution": None, "assignee": None,
                  "reporter": {"accountId": ME, "displayName": "Ada Fixture", "emailAddress": "ada.fixture@example.invalid"},
                  "creator": {"accountId": ME, "displayName": "Ada Fixture", "emailAddress": "ada.fixture@example.invalid"},
                  "created": stamp, "updated": stamp}
        if self.corrupt:
            self.corrupt(fields)
        self.issues.append({"id": issue_id, "key": "%s-%d" % (PROJECTS[project_id], number),
                            "self": "%s/rest/api/3/issue/%s" % (SITE, issue_id), "fields": fields})
        if self.fail_post == "applied-timeout":
            raise TimeoutError("the fake created the story and then did not answer")
        return 201, {}, {"id": issue_id, "key": "%s-%d" % (PROJECTS[project_id], number),
                         "self": "%s/rest/api/3/issue/%s" % (SITE, issue_id)}

    def find(self, ref):
        for item in self.issues:
            if ref in (item["id"], item["key"]):
                return item
        return None


def main():
    parser = argparse.ArgumentParser(description="Look at, or rename a story in, the fake Jira kept in a state folder.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("show", "rename"):
        sub = commands.add_parser(name)
        sub.add_argument("--state", required=True)
        if name == "rename":
            sub.add_argument("--story", required=True)
            sub.add_argument("--to", required=True)
    args = parser.parse_args()
    path = os.path.join(args.state, "fake-jira.json")
    fake = FakeJira.open(path)
    if args.command == "rename":
        item = fake.find(args.story)
        if item is None:
            print("The fake Jira has no story %s." % args.story)
            return 1
        item["key"] = args.to
        fake.save(path)
        print("FAKE JIRA: someone gave story %s (issue id %s) the new key %s." % (args.story, item["id"], args.to))
    mine = [item for item in fake.issues if item["fields"]["project"]["key"] == "RPT"]
    print("FAKE JIRA holds %d stories in project RPT: %s." % (len(mine), ", ".join("%s (id %s)" % (item["key"], item["id"]) for item in mine)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
