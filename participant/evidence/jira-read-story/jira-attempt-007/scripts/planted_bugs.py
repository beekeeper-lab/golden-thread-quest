#!/usr/bin/env python3
"""Records logs/planted-bugs.txt for the jira-read-story quest.

Puts one bug at a time into scripts/story.py or scripts/adf.py, runs every
test, notes which tests fail, and takes the bug out again. At the end it
checks that both files are the same as when it started, byte for byte. No
network is used.

It changes those two files while it runs. Do not run the reader at the same time.

Run from anywhere:  python3 scripts/planted_bugs.py
Exit code 0 if every bug was caught and both files were restored, 1 if not.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)

# (what the bug is, the file, the text to replace, what to replace it with)
BUGS = [
    ("A. A custom field whose value is zero or empty is left out of the file", "story.py",
     'preserved = sorted(name for name in fields if name not in KNOWN and name != "description")',
     'preserved = sorted(name for name in fields if name not in KNOWN and name != "description" and fields[name] not in (0, [], {}, ""))'),
    ("B. Only custom fields are preserved, so other unfamiliar fields are dropped", "story.py",
     'preserved = sorted(name for name in fields if name not in KNOWN and name != "description")',
     'preserved = sorted(name for name in fields if name.startswith("customfield_"))'),
    ("C. The count of fields placed is not checked, and unfamiliar fields are dropped without a word", "story.py",
     '    if total != report["returned"]:', '    if False:'),
    ("D. A person is saved whole, with name, email address and pictures", "story.py",
     '            return {key: value[key] for key in PERSON_KEEPS if key in value}', '            return value'),
    ("E. Email addresses typed into text are left in", "story.py",
     '        if found:\n            counts["email addresses removed from text"]', '        if False:\n            counts["email addresses removed from text"]'),
    ("F. Links holding the site's address are left in", "story.py",
     '            if key in SITE_KEYS:', '            if False:'),
    ("G. The file records when it was made", "story.py",
     'out = ["---", "format: %s" % as_json(FORMAT),',
     'out = ["---", "format: %s" % as_json(FORMAT), "retrieved: %s" % as_json(__import__("time").time()),'),
    ("H. The summary is written into the front matter without quotes", "story.py",
     'out += ["%s: %s" % (name, as_json(fields[name])) for name in front]',
     'out += ["%s: %s" % (name, fields[name] if name == "summary" else as_json(fields[name])) for name in front]'),
    ("I. The key is written where the issue id belongs", "story.py",
     '"id: %s" % as_json(issue_id)', '"id: %s" % as_json(key)'),
    ("J. An unchanged file is rewritten on every run", "story.py",
     '    if existing == data:', '    if False:'),
    ("K. The reader is given a way to send a write", "story.py",
     'request = urllib.request.Request(url, method="GET")',
     'request = urllib.request.Request(url, method="GET" if not (params or {}).get("_write") else "POST")'),
    ("L. A table is flattened into separate paragraphs. This is the quest's scenario", "adf.py",
     '    if kind == "table":\n        return table(node, notes)',
     '    if kind == "table":\n        return "\\n\\n".join(cell_text(c, notes) for r in content for c in r.get("content") or [])'),
    ("M. Typed text is not escaped, so it can become Markdown", "adf.py",
     '    for ch in "`*_[]<>|~":', '    for ch in "":'),
    ("N. A line of typed text that starts like a heading or a list is not guarded", "adf.py",
     '        if re.match(r"(#{1,6}(\\s|$)|[-+](\\s|$)|={3,}\\s*$|-{3,}\\s*$)", stripped):', '        if False:'),
    ("O. A code block is always fenced with three backticks, whatever it contains", "adf.py",
     '        fence = fence_for(code)\n        language', '        fence = "```"\n        language'),
    ("P. A code block loses its language", "adf.py",
     '        return "%s%s\\n%s\\n%s" % (fence, language, code, fence)', '        return "%s%s\\n%s\\n%s" % (fence, "", code, fence)'),
    ("Q. A block the converter does not know is dropped", "adf.py",
     '    notes.add("unrecognised block: %s" % kind)\n', '    notes.add("unrecognised block: %s" % kind)\n    return ""\n'),
    ("R. Only the first paragraph of a list item is kept, so a list inside a list is lost", "adf.py",
     '            body = blocks(item.get("content"), notes) or ""', '            body = blocks((item.get("content") or [])[:1], notes) or ""'),
    ("S. A link keeps its text and loses its address", "adf.py",
     '            out = "[%s](<%s>)" % (out, href)', '            out = out'),
    ("T. A numbered list always starts at 1", "adf.py",
     '        number = attrs.get("order", 1) if isinstance(attrs.get("order", 1), int) else 1\n        items = []', '        number = 1\n        items = []'),
    ("U. A pipe character inside a table cell is not escaped", "adf.py",
     '    for ch in "`*_[]<>|~":', '    for ch in "`*_[]<>~":'),
    ("V. An image in the description is dropped", "adf.py",
     '        return "\\n\\n".join(media(child, notes) for child in content if child.get("type") == "media")', '        return ""'),
]


def run_tests():
    done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ATTEMPT,
                          capture_output=True, text=True)
    failed = sorted(set(re.findall(r"^(?:FAIL|ERROR): (\w+) \((?:test_story\.)?(\w+)", done.stderr, re.M)))
    return done.stderr.strip().splitlines()[-1], ["%s.%s" % (group, name) for name, group in failed]


def main():
    good = {}
    for name in ("story.py", "adf.py"):
        with open(os.path.join(HERE, name), encoding="utf-8") as f:
            good[name] = f.read()
    out = ["Do the tests notice a broken reader or converter? jira-read-story, attempt jira-attempt-007",
           "Recorded by scripts/planted_bugs.py.", "",
           "Each bug below was put into scripts/story.py or scripts/adf.py, every test was run, and the bug was",
           "taken out again. No network is used.", ""]
    last, failed = run_tests()
    out += ["Before any bug: %s" % last, ""]
    clean, missed = (not failed and last.startswith("OK")), []
    try:
        for title, name, old, new in BUGS:
            path = os.path.join(HERE, name)
            if good[name].count(old) != 1:
                out += ["PLANTED BUG %s  (in %s)" % (title, name), "  COULD NOT BE PLANTED: the text to replace was not found once", ""]
                missed.append(title)
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(good[name].replace(old, new))
            last, failed = run_tests()
            with open(path, "w", encoding="utf-8") as f:
                f.write(good[name])
            out += ["PLANTED BUG %s  (in %s)" % (title, name), "  unittest result: %s" % last, "  tests that failed (%d):" % len(failed)]
            out += ["    " + test for test in failed] or ["    NONE. THIS BUG WAS NOT CAUGHT."]
            out += [""]
            if not failed:
                missed.append(title)
    finally:
        for name, text in good.items():
            with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
                f.write(text)
    restored = all(open(os.path.join(HERE, name), encoding="utf-8").read() == text for name, text in good.items())
    last, failed = run_tests()
    out += ["After the last bug was taken out: story.py and adf.py are %s they were at the start. %s"
            % ("byte for byte what" if restored else "NOT what", last), ""]
    ok = clean and restored and not missed and not failed
    out += ["RESULT: %s" % ("all %d planted bugs were caught by at least one test, and both files were restored."
                            % len(BUGS) if ok else "NOT ALL AS EXPECTED: %s" % ("; ".join(missed) or "see above"))]
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "planted-bugs.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(out[-1])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
