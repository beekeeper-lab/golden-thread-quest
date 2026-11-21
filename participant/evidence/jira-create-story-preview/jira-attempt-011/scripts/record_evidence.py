#!/usr/bin/env python3
"""Records logs/preview-run.txt and logs/missing-field-run.txt, and writes the payload file.

Everything here runs against the fake Jira in the skill folder, a made-up
one that can only be read. No network is used and no real Jira is contacted.
Each block between dashed lines is what the preview command printed, started
as a person would start it.

The first preview writes participant/context/jira/new-story/payload.md.

The drafts for the refusals are made here from the good draft, by taking
lines out of it, and saved in participant/context/jira/new-story/refused/,
so that each differs from the good draft only in what is being shown.

If logs/live-preview.txt is there, a preview a person ran against a real Jira
sandbox, it is copied unchanged onto the end of preview-run.txt.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
SKILL = "participant/skills/jira-create-story-preview"
NEW = "participant/context/jira/new-story"
CATALOG = "participant/context/jira/duplicates/fixture"
HEAD = ("Recorded by scripts/record_evidence.py. Each block between dashed lines is what the preview printed.\n"
        "The Jira here is %s/fake_jira.py, a made-up one that can only be read. No real Jira was contacted, so\n"
        "nothing is redacted: the site, the projects and the stories are invented. STATE stands for a temporary folder." % SKILL)


class Log:
    def __init__(self, title, state):
        self.lines, self.problems, self.state = [title, HEAD], [], state

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def preview(self, draft, *more):
        args = ["--source", "fake", "--draft", draft, "--allowlist", SKILL + "/fake-allowlist.json", "--catalog", CATALOG,
                "--state", self.state, "--today", "2026-11-19"] + list(more)
        self.out("$ python3 %s/preview.py %s" % (SKILL, " ".join(args).replace(self.state, "STATE")))
        done = subprocess.run([sys.executable, SKILL + "/preview.py"] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text = done.stdout.rstrip("\n").replace(self.state, "STATE")
        self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text

    def save(self, name, live=None):
        """`live` is the log of a run a person made against the real sandbox, copied onto the end if it is there."""
        self.out("")
        result = "RESULT: %s" % ("%d CHECK(S) FAILED" % len(self.problems) if self.problems else "ALL CHECKS PASSED.")
        self.out(result + (" (The checks are on the fake-Jira run above.)" if live else ""))
        if live and os.path.exists(os.path.join(REL, "logs", live)):
            with open(os.path.join(REL, "logs", live), encoding="utf-8") as f:
                text = f.read().strip("\n")
            self.lines += ["", "#" * 78, "THE SAME ON THE REAL JIRA SANDBOX",
                           "The block below was not made by this script. The participant ran the preview in their own terminal",
                           "against their real Jira sandbox, with the draft draft-sandbox.md, and the preview saved its output",
                           "with the site's address replaced by a marker. It is copied here unchanged from logs/%s." % live,
                           "The catalog it searched for duplicates is a copy of one real story, kept outside the repository.",
                           "-" * 78, text, "-" * 78]
        with open(os.path.join(REL, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, result))
        return self.problems


def without(text, *starts):
    """The draft with every line removed that starts with one of `starts`."""
    return "\n".join(line for line in text.split("\n") if not any(line.startswith(start) for start in starts)) \
        .replace("sources/intake-notes.md", "../sources/intake-notes.md")


def catalog_state():
    found = {}
    for folder, _, names in os.walk(CATALOG):
        for name in sorted(names):
            with open(os.path.join(folder, name), "rb") as f:
                found[os.path.join(folder, name)] = hashlib.sha256(f.read()).hexdigest()
    return found


def main():
    os.chdir(ROOT)
    os.makedirs(REL + "/logs", exist_ok=True)
    problems = []
    with open(NEW + "/draft.md", encoding="utf-8") as f:
        good = f.read()

    # ------------------------------------------------------------ preview-run.txt
    with tempfile.TemporaryDirectory() as state:
        log = Log("A preview of a new story, with nothing written: jira-create-story-preview, attempt jira-attempt-011", state)
        log.part("The draft is %s/draft.md. Its content is cited to %s/sources/intake-notes.md.\n"
                 "The payload is also written to %s/payload.md." % (NEW, NEW, NEW))
        before = catalog_state()
        code, text = log.preview(NEW + "/draft.md", "--payload-out", NEW + "/payload.md")
        log.out("")
        log.check("a preview was made, exit code 0, and it says nothing was written", code == 0
                  and text.startswith("PREVIEW OF A NEW STORY. Nothing has been written to Jira."))
        log.check("it lists the site, the target project and the issue type (criterion 1)",
                  "Project:     RPT (project id 30000)" in text and 'Issue type:  "Story" (issue type id 10001)' in text and "Jira site:" in text)
        log.check("it accounts for every one of the 12 fields Jira lists: 9 set by the draft, 2 left to Jira, 1 optional and not sent (criterion 1)",
                  "in RPT: 12." in text and "Set by the draft, 9:" in text and "has a default, 2:" in text and "and not sent, 1:" in text)
        log.check("the two fields left to Jira are shown with what Jira says its default is: Priority Medium, and a Reporter default Jira does not name",
                  'Priority      Jira\'s default is "Medium".' in text and "Reporter      Jira says it has a default and does not say what it is." in text)
        shown = None
        try:
            shown = json.loads(text.split("not a summary of it:\n")[1].split("\nAs sent it is")[0])
        except (IndexError, ValueError):
            pass
        body = json.dumps(shown, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") if shown else b""
        digest = hashlib.sha256(body).hexdigest()
        log.check("the payload is shown whole, and it parses as JSON with one member, fields, holding 9 fields (criterion 5)",
                  bool(shown) and list(shown) == ["fields"] and len(shown["fields"]) == 9)
        log.check("this script worked out the SHA-256 of that payload itself, and it is the one the preview printed: %s" % digest,
                  ("%d bytes, SHA-256 %s" % (len(body), digest)) in text)
        saved = [name for name in os.listdir(os.path.join(state, "create-previews"))]
        with open(os.path.join(state, "create-previews", saved[0]), encoding="utf-8") as f:
            record = json.load(f)
        log.check("the preview saved for a later write holds the same payload and the same SHA-256",
                  len(saved) == 1 and record["payload"] == shown and record["payload_sha256"] == digest)
        with open(NEW + "/payload.md", encoding="utf-8") as f:
            page = f.read()
        log.check("payload.md holds the same payload and the same SHA-256",
                  json.loads(page.split("```json\n")[1].split("\n```")[0]) == shown and digest in page)
        log.check("the duplicate search result is shown: one candidate, RPT-3, medium confidence, recommendation LINK (criterion 3)",
                  "Result: 1 candidate." in text and "RPT-3 (issue id 30003): confidence MEDIUM" in text and "Overall recommendation: LINK. A person decides." in text)
        log.check("it says how much of the project the search covered: the catalog holds 7 of RPT's stories and Jira holds 7",
                  "Coverage: the catalog holds 7 of project RPT's stories and Jira holds 7: the counts agree." in text)
        log.check("it shows how the draft differs from that nearest story", "How the draft differs from the nearest, RPT-3:" in text)
        log.check("the permission check result is shown: may create stories, yes (criterion 4)", "(CREATE_ISSUES):   yes" in text)
        log.check("10 source citations are shown, each checked against the file (criterion 7)", "10 citations, all true." in text)
        snaps = re.findall(r"(?:before|after) the preview:\s+(\d+ stories, [0-9a-f]{16})", text)
        log.check("it ends with the check that Jira is unchanged: the same snapshot before and after (criterion 6)",
                  len(snaps) == 2 and snaps[0] == snaps[1] and "The two are the same. Jira is unchanged." in text)
        sent = re.findall(r"^  (\w+) /rest/api/3/", text, re.M)
        log.check("all %d requests were GETs. The fake Jira has no way to be written to" % len(sent), bool(sent) and set(sent) == {"GET"})
        log.check("the local catalog searched for duplicates is as it was: all %d files have the same SHA-256" % len(before), catalog_state() == before)
        problems += log.save("preview-run.txt", live="live-preview.txt")

    # ------------------------------------------------------------ missing-field-run.txt
    os.makedirs(NEW + "/refused", exist_ok=True)
    drafts = {"draft-no-component.md": without(good, "components:", "- components:"),
              "draft-no-summary.md": without(good, "summary:", "- summary:"),
              "draft-no-team.md": without(good, "custom:", "- custom Team:")}
    for name, text in drafts.items():
        with open(os.path.join(NEW, "refused", name), "w", encoding="utf-8") as f:
            f.write(text)
    with tempfile.TemporaryDirectory() as state:
        log = Log("Previews refused because a required field is missing: jira-create-story-preview, attempt jira-attempt-011", state)
        log.out("Each draft below is the good draft with lines taken out. They are in %s/refused/." % NEW)

        log.part("1. A draft with no component. In the fake project RPT, Jira requires Components for a Story and has\n"
                 "no default for it.")
        code, text = log.preview(NEW + "/refused/draft-no-component.md", "--payload-out", os.path.join(state, "payload.md"))
        log.check("refused, exit code 1, and the reason names the field: \"Components\" (components) (criterion 2)",
                  code == 1 and 'gives no default for: "Components" (components)' in text)
        log.check("no payload was shown, none was saved, and no payload file was written",
                  '"fields"' not in text and not os.path.exists(os.path.join(state, "create-previews")) and not os.path.exists(os.path.join(state, "payload.md")))

        log.part("2. A draft with no summary. Every story needs one, so the preview refuses before asking Jira anything.")
        code, text = log.preview(NEW + "/refused/draft-no-summary.md")
        log.check("refused, exit code 1, with the reason", code == 1 and "REFUSED: the draft has no summary." in text)

        log.part("3. For contrast, the quest's scenario: a draft with no Team. Jira requires Team and HAS a default for\n"
                 "it, Support. This is not refused. The preview says that Jira would decide, and what it would put.")
        code, text = log.preview(NEW + "/refused/draft-no-team.md")
        log.check("a preview was made, and Team is listed as left to Jira with the default \"Support\"",
                  code == 0 and "has a default, 3:" in text and 'customfield_10050  Team          Jira\'s default is "Support".' in text)
        log.check("Team is not in the payload, so a reader can see that the team would be Jira's choice and not the draft's",
                  '"customfield_10050"' not in text)
        problems += log.save("missing-field-run.txt")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
