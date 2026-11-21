#!/usr/bin/env python3
"""Checks a saved story against what Jira returns for it, for the jira-read-story quest.

    fidelity.py --source live|fake --story ID_OR_KEY --file FILE.md

It asks Jira for the story again, reads the Markdown file, and compares the
two. It does not use story.py or adf.py: it has its own reading of the file,
its own statement of what must be removed before saving, and its own walk of
Jira's description. If the reader and this check disagree, one of them is wrong.

It checks:

  1. the story's identity: the file's `id` is Jira's issue id
  2. every field Jira returned is in the file, in the front matter, the body
     or the preserved section, with the value Jira sent (after the removals)
  3. the description's structure survived: the same number of headings, list
     items, tables, table rows and code blocks, each code block's text exact,
     every run of text present and in order, and nothing typed as plain text
     turned into structure
  4. nothing private is in the file: no person's name, email address or
     picture link that Jira sent, no site address, no credential

It prints field ids, Jira's names for them, where each was found and the kind
of value. It does not print the text of the story.

Exit codes: 0 every check passed; 1 at least one failed, or it could not run.
"""
import argparse
import copy
import json
import os
import re
import sys

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
HANDLED_BLOCKS = {"paragraph", "heading", "bulletList", "orderedList", "listItem", "taskList", "taskItem", "codeBlock",
                  "blockquote", "panel", "rule", "table", "tableRow", "tableHeader", "tableCell", "mediaSingle",
                  "mediaGroup", "media", "expand", "doc"}
INLINE = {"text", "hardBreak", "mention", "emoji", "inlineCard", "date", "status", "mediaInline"}


class Check:
    def __init__(self):
        self.lines, self.failed = [], []

    def out(self, text=""):
        self.lines.append(text)

    def ok(self, label, passed):
        self.lines.append("  %-4s %s" % ("ok" if passed else "FAIL", label))
        if not passed:
            self.failed.append(label)
        return passed


# ---------------------------------------------------------------- what the file should hold


def expected(value, site_host):
    """What a value should look like in the file. This check's own statement of the removals."""
    if isinstance(value, list):
        return [expected(item, site_host) for item in value]
    if isinstance(value, dict):
        if isinstance(value.get("accountId"), str):
            return {k: value[k] for k in ("accountId", "accountType", "active") if k in value}
        result = {}
        for k, v in value.items():
            if k in ("self", "avatarUrls", "iconUrl", "avatarUrl"):
                continue
            if k == "attrs" and value.get("type") == "mention" and isinstance(v, dict):
                v = {a: b for a, b in v.items() if a != "text"}
            result[k] = expected(v, site_host)
        return result
    if isinstance(value, str):
        value = EMAIL.sub("[email address removed]", value)
        if site_host:
            value = value.replace(site_host, "[site address removed]")
    return value


def private_strings(issue, site_host):
    """Everything in Jira's answer that must not be in the file: names, email addresses, picture links, the site."""
    found = set()

    def walk(value, key=None):
        if isinstance(value, dict):
            if isinstance(value.get("accountId"), str):
                for k in ("displayName", "emailAddress", "timeZone"):
                    if isinstance(value.get(k), str) and len(value[k]) > 3:
                        found.add(value[k])
                for url in (value.get("avatarUrls") or {}).values():
                    found.add(url)
            if value.get("type") == "mention" and isinstance((value.get("attrs") or {}).get("text"), str):
                found.add(value["attrs"]["text"].lstrip("@"))
            for k, v in value.items():
                walk(v, k)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            found.update(EMAIL.findall(value))
    walk(issue)
    found.discard("")
    if site_host:
        found.add(site_host)
    return sorted(found)


# ---------------------------------------------------------------- reading the file


def split_file(text):
    """(front matter as a dict, description Markdown, preserved fields as a dict)."""
    if not text.startswith("---\n"):
        raise ValueError("the file does not begin with front matter")
    end = text.index("\n---\n", 4)
    front = {}
    for line in text[4:end].split("\n"):
        key, _, value = line.partition(": ")
        if not re.fullmatch(r"[A-Za-z0-9_]+", key) or key in front:
            raise ValueError("a front matter line is not 'key: value', or a key is given twice")
        front[key] = json.loads(value)
    body = text[end + 5:]
    start = body.index("\n## Description\n\n") + len("\n## Description\n\n")
    cut = body.rindex("\n\n## Preserved fields\n")
    description, tail = body[start:cut], body[cut:]
    preserved = {}
    block = re.search(r"\n(`{3,})json\n(.*)\n\1\n", tail, re.S)
    if block:
        preserved = json.loads(block.group(2))
    return front, description, preserved


def kind_of(value):
    if value is None:
        return "empty (null)"
    if isinstance(value, bool):
        return "true/false: %s" % json.dumps(value)
    if isinstance(value, (int, float)):
        return "number: %s" % json.dumps(value)
    if isinstance(value, str):
        return "text, %d characters" % len(value)
    if isinstance(value, list):
        return "list of %d" % len(value)
    return "object with %d parts" % len(value)


# ---------------------------------------------------------------- the description


def survey(document):
    """Count what is in Jira's description, by this check's own walk of it."""
    seen = {"headings": [], "list_items": 0, "list_items_in_tables": 0, "tables": 0, "table_rows": 0, "code": [],
            "text": [], "links": 0, "unknown_blocks": 0, "media": 0}

    def walk(node, in_table):
        kind = node.get("type")
        if kind == "codeBlock":
            seen["code"].append(((node.get("attrs") or {}).get("language") or "",
                                 "".join(c.get("text", "") for c in node.get("content") or []), in_table))
            return
        if kind not in HANDLED_BLOCKS and kind not in INLINE:
            seen["unknown_blocks"] += 1
            return
        if kind == "heading":
            seen["headings"].append((node.get("attrs") or {}).get("level", 1))
        if kind in ("listItem", "taskItem"):
            seen["list_items_in_tables" if in_table else "list_items"] += 1
        if kind == "table":
            seen["tables"] += 1
            in_table = True
        if kind == "tableRow":
            seen["table_rows"] += 1
        if kind in ("media", "mediaInline"):
            seen["media"] += 1
        if kind == "text":
            if node.get("text", "").strip():
                seen["text"].append(node["text"])
            seen["links"] += sum(1 for m in node.get("marks") or [] if m.get("type") == "link")
        for child in node.get("content") or []:
            walk(child, in_table)

    if isinstance(document, dict):
        walk(document, False)
    return seen


def read_markdown(description):
    """Count what is in the Markdown description, line by line."""
    found = {"headings": [], "list_items": 0, "list_items_in_tables": 0, "tables": 0, "table_rows": 0, "code": [],
             "links": 0, "unknown_blocks": 0, "media": 0}
    lines = description.split("\n")
    prose, i, in_table = [], 0, False
    while i < len(lines):
        line = lines[i]
        opener = re.fullmatch(r"(\s*)(`{3,})([A-Za-z0-9+#._-]*)", line)
        if opener:
            pad, fence, language = opener.groups()
            j = i + 1
            while j < len(lines) and lines[j] != pad + fence:
                j += 1
            body = "\n".join(l[len(pad):] if l.startswith(pad) else l for l in lines[i + 1:j])
            if i > 0 and lines[i - 1].lstrip().startswith("<!-- jira-unrecognised-block:"):
                found["unknown_blocks"] += 1
            else:
                found["code"].append((language, body))
            i, in_table = j + 1, False
            continue
        if line.startswith("| ") or line.startswith("|---"):
            if not in_table:
                found["tables"] += 1
                in_table = True
            if not line.startswith("|---"):
                found["table_rows"] += 1
                found["list_items_in_tables"] += len(re.findall(r"(?:^|<br>|\| )(?:&nbsp;)*(?:\\-|\d+\\\.) ", line))
        else:
            in_table = False
            heading = re.match(r"(#{1,6}) ", line)
            if heading:
                found["headings"].append(len(heading.group(1)))
            if re.match(r"\s*(- |\d+\. )", line):
                found["list_items"] += 1
        found["links"] += len(re.findall(r"(?<!!)\[[^\]]*\]\(<[^>]*>\)", line))
        found["media"] += len(re.findall(r"!\[[^\]]*\]\(<[^>]*>\)", line))
        prose.append(line)
        i += 1
    return found, "\n".join(prose)


def unescape(text):
    return re.sub(r"\\([\\`*_\[\]<>|~#+\-.)=])", r"\1", text)


# ---------------------------------------------------------------- the check


def check(issue, file_text, site_host="", secrets=()):
    c = Check()
    fields, names = issue.get("fields") or {}, issue.get("names") or {}
    try:
        front, description, preserved = split_file(file_text)
    except (ValueError, KeyError, IndexError) as problem:
        c.ok("the file could be read as front matter, a description and a preserved section (%s)" % problem, False)
        return c

    c.out("1. IDENTITY")
    c.ok("the file's `id` is Jira's issue id (%s), and `id` is the first field after the format line"
         % issue.get("id"), front.get("id") == issue.get("id") and list(front)[:2] == ["format", "id"])
    c.ok("the key is stored as a separate field (%s)" % issue.get("key"), front.get("key") == issue.get("key"))

    c.out("")
    c.out("2. EVERY FIELD JIRA RETURNED (%d). Where each is in the file, and whether its value is what Jira sent." % len(fields))
    c.out("     %-20s %-18s %-13s %s" % ("field id", "Jira's name", "found in", "kind of value"))
    missing = []
    for name in sorted(fields):
        want = expected(copy.deepcopy(fields[name]), site_host)
        label = str(names.get(name, ""))[:18]
        if name == "description":
            where, same = "body", front.get("description") is not None or fields[name] is None
        elif name in front:
            where, same = "front matter", front[name] == want
        elif name in preserved:
            where, same = "preserved", preserved[name].get("value") == want and preserved[name].get("name") == names.get(name)
        else:
            where, same = "NOWHERE", False
            missing.append(name)
        c.lines.append("  %-4s %-20s %-18s %-13s %s" % ("ok" if same else "FAIL", name, label, where, kind_of(fields[name])))
        if not same:
            c.failed.append("field %s" % name)
    c.out("")
    c.ok("all %d fields are in the file, none missing" % len(fields), not missing)
    extra = sorted((set(front) | set(preserved)) - set(fields)
                   - {"format", "id", "key", "preserved_fields", "removed_before_saving", "description_notes", "description"})
    c.ok("the file holds no field that Jira did not send", not extra)
    custom = [n for n in fields if n.startswith("customfield_")]
    c.ok("every custom field (%d) is in the preserved section" % len(custom), all(n in preserved for n in custom))
    unusual = [n for n in fields if fields[n] in (0, False, "", [], {}) and fields[n] is not None]
    c.ok("fields whose value is zero or empty but present (%s) kept that value and were not dropped or turned into null"
         % (", ".join(sorted(unusual)) or "none in this story"),
         all((front.get(n) if n in front else preserved.get(n, {}).get("value", "MISSING")) == fields[n] for n in unusual))

    c.out("")
    c.out("3. THE DESCRIPTION'S STRUCTURE")
    jira = survey(expected(copy.deepcopy(fields.get("description")), site_host))
    md, prose = read_markdown(description)
    c.ok("headings: Jira has %d (levels %s), the Markdown has %d (levels %s)"
         % (len(jira["headings"]), jira["headings"], len(md["headings"]), md["headings"]), jira["headings"] == md["headings"])
    c.ok("list items outside tables: Jira has %d, the Markdown has %d" % (jira["list_items"], md["list_items"]),
         jira["list_items"] == md["list_items"])
    c.ok("tables: Jira has %d with %d rows, the Markdown has %d with %d rows"
         % (jira["tables"], jira["table_rows"], md["tables"], md["table_rows"]),
         (jira["tables"], jira["table_rows"]) == (md["tables"], md["table_rows"]))
    c.ok("list items inside table cells: Jira has %d, the Markdown keeps %d as lines"
         % (jira["list_items_in_tables"], md["list_items_in_tables"]),
         jira["list_items_in_tables"] == md["list_items_in_tables"])
    blocks = [(lang, text) for lang, text, in_table in jira["code"] if not in_table]
    c.ok("code blocks: Jira has %d, the Markdown has %d, and each one's language and text are exactly the same"
         % (len(blocks), len(md["code"])), blocks == md["code"])
    c.ok("links: Jira has %d, the Markdown has %d" % (jira["links"], md["links"]), jira["links"] == md["links"])
    c.ok("images and files: Jira has %d, the Markdown keeps %d as references" % (jira["media"], md["media"]),
         jira["media"] == md["media"])
    c.ok("blocks of a kind the converter does not know: Jira has %d, the Markdown carries %d along"
         % (jira["unknown_blocks"], md["unknown_blocks"]), jira["unknown_blocks"] == md["unknown_blocks"])
    plain, position, lost = unescape(prose).replace("\\\n", "\n"), 0, 0
    for text in jira["text"]:
        piece = " ".join(text.split())
        at = " ".join(plain[position:].split()).find(piece) if piece else 0
        flat = " ".join(plain.split())
        at = flat.find(piece, position)
        if at == -1:
            lost += 1
        else:
            position = at + len(piece)
    code_text = sum(1 for _, text, in_table in jira["code"])
    c.ok("every run of text in Jira's description (%d, outside code blocks) is in the Markdown, in the same order"
         % len(jira["text"]), lost == 0)

    c.out("")
    c.out("4. NOTHING PRIVATE")
    private = private_strings(issue, site_host)
    present = [value for value in private if value in file_text]
    c.ok("Jira's answer held %d private strings (people's names, email addresses, time zones, picture links, the "
         "site's address). In the file: %d" % (len(private), len(present)), not present)
    c.ok("no email address of any kind is in the file", not EMAIL.search(file_text))
    people = file_text.count('"accountId"')
    c.ok("people appear only as account ids (%d places), with no displayName or emailAddress beside them" % people,
         '"displayName"' not in file_text and '"emailAddress"' not in file_text and '"avatarUrls"' not in file_text)
    leaked = [s for s in secrets if s and s in file_text]
    c.ok("no credential is in the file (searched for %s)"
         % ("the API token, the account's email address and their encoded form" if secrets else
            "the words that mark one: Authorization, Basic, Bearer"),
         not leaked and not re.search(r"Authorization|Basic [A-Za-z0-9+/=]{12,}|Bearer [A-Za-z0-9._-]{12,}", file_text))
    return c


def main():
    parser = argparse.ArgumentParser(description="Check a saved story against what Jira returns. Reads only.")
    parser.add_argument("--source", choices=("live", "fake"), required=True)
    parser.add_argument("--story", required=True)
    parser.add_argument("--file", required=True)
    args = parser.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    secrets, host = [], ""
    try:
        if args.source == "fake":
            import fake_jira
            get, host = fake_jira.FakeJira().get, "fixture-site.example.invalid"
        else:
            import story
            get, secrets, host = story.make_live_get()
        status, _, issue = get("/rest/api/3/issue/%s" % args.story, {"expand": "names"})
        if status != 200:
            print("STOPPED: Jira answered %d for the story." % status)
            return 1
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    except Exception as problem:   # the check must never print a credential in a traceback
        print("STOPPED: %s." % type(problem).__name__)
        return 1
    c = check(issue, text, host, secrets[:3])
    output = "\n".join(["FIDELITY CHECK. Jira's answer for the story against the saved file. Reading only.", ""] + c.lines
                       + ["", "RESULT: %s" % ("%d CHECK(S) FAILED" % len(c.failed) if c.failed else "ALL CHECKS PASSED.")])
    if any(s and s in output for s in secrets):
        print("STOPPED: a credential or the site's address was found in the output, so the output was not printed.")
        return 1
    print(output)
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
