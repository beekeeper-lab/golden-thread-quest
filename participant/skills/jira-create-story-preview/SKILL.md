# Jira create-story preview

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill shows exactly what creating one Jira story would send, before anything is sent. It reads a local
draft, asks Jira what the project requires, searches the local catalog for duplicates, and prints the whole
request. Then it stops.

**It writes nothing to Jira.** `preview.py` has no code that sends a write: every request it makes is a GET.

Run it from the repository root:

    python3 participant/skills/jira-create-story-preview/preview.py --source live --draft DRAFT.md \
        --allowlist participant/context/jira/update/sandbox-allowlist.json --catalog FOLDER --state FOLDER

`--source fake` runs against the made-up Jira in `fake_jira.py`, with no network and no credentials.

## 2. Configuration

A live run reads three environment variables, set in the local shell and never stored in a file.

| Variable | What it holds |
|---|---|
| `JIRA_BASE_URL` | The Jira site's address, starting `https://`. |
| `JIRA_EMAIL` | The account the token belongs to. |
| `JIRA_API_TOKEN` | An API token for that account. |

The output is searched for the token, the email address and their encoded form before it is shown. The site's
address is shown on screen, so the person reading can see where a write would go, and is replaced by a marker
in anything saved with `--log` or `--payload-out`.

| Option | What it is |
|---|---|
| `--draft FILE` | The story draft. |
| `--allowlist FILE` | The sandbox allowlist: projects by project id, each with a fingerprint of its site's address. |
| `--catalog FOLDER` | The local catalog to search for duplicates, as the `jira-build-index` skill writes it. |
| `--state FOLDER` | Where the preview is saved for a later write. |
| `--payload-out FILE` | Also write the payload, field by field, as Markdown. |
| `--log FILE` | Also save the output, with the site's address removed. |

## 3. The draft

A Markdown file. Between two lines of three dashes are the story's fields, one per line: a name, a colon and a
JSON value.

    format: "jira-story-draft/1"
    project: "RPT"                  the project's key
    issuetype: "Story"              the issue type's name
    summary: "..."
    labels: ["a", "b"]              optional
    components: ["Reports"]         optional, by name
    priority: "High"                optional, by name
    parent: "RPT-1"                 optional, the parent's key
    duedate: "2027-01-15"           optional
    custom: {"Team": "Data"}        optional, single-choice custom fields by name

Under `## Description` is the description: paragraphs, and lists whose lines start with `- `. It is sent as
plain text in Atlassian Document Format. Bold, links and other formatting are not converted: the characters are
sent as typed.

Any other field name in the draft is refused. The preview never sets an assignee, a reporter or a security
level.

## 4. Citations

Under `## Sources` is one line for each citation:

    - summary: sources/notes.md line 7: "the words quoted"
    - description: sources/notes.md lines 8-9: "more words"
    - custom Team: sources/notes.md line 11: "the data team"

Every piece of content in the draft needs at least one. That is the summary, the description, and each of the
labels, components, priority, parent, due date and custom fields the draft sets. Each citation is checked: the
file must be under `participant/context/`, and the quoted words must be on the lines named. A source that was
changed after the draft was written fails that check.

## 5. What the preview does

In order. A refusal at any step stops it. A refused preview shows no payload, saves none and writes no payload
file.

1. Reads the draft and checks its citations.
2. Asks Jira for the project, and checks it is on the sandbox allowlist.
3. Takes a snapshot of the project's stories: how many, and one code for their ids and update times.
4. Asks Jira whether this identity may create stories in the project.
5. Asks Jira which fields the project takes for this issue type: which are required, which have defaults and
   which values each allows.
6. Checks the draft against that.
7. Builds the payload, once.
8. Searches the local catalog for likely duplicates, with the `jira-duplicate-search` skill.
9. Takes the snapshot again, and refuses if it differs.
10. Shows everything and saves the preview.

## 6. Required fields, defaults and allowed values

Every field Jira lists ends in one of three groups, and all three are shown.

| Group | Meaning |
|---|---|
| Set by the draft | In the payload, with the value shown. |
| Left to Jira | Required by Jira, not in the draft, and Jira says it has a default. Shown with the default Jira reports, or a statement that Jira does not say what it is. |
| Optional and not sent | Not required and not in the draft. |

**A field Jira requires, with no default, that the draft lacks is a refusal.** The reason names each such
field.

A field left to Jira is not a refusal. It is the case to read most carefully, because Jira and not the draft
decides its value.

Values are checked against what Jira allows. A component, a priority and a custom choice are given by name in
the draft, must match exactly one value Jira lists, and are sent by id. A field the draft sets that Jira does
not list for this issue type is refused. So is a field Jira describes as another kind than the preview builds.
A parent must exist and be in the same project.

## 7. The payload

The payload is made in one function, `build_payload`, and turned into bytes in one function, `body_bytes`. The
preview prints the payload whole, with its length in bytes and its SHA-256. The same payload and SHA-256 are
saved in the state folder under a fingerprint, with a 15-minute expiry, for a later write to check before it
sends those bytes.

The bytes are the payload as JSON with no spaces or line breaks and its names in alphabetical order. The
preview prints it indented, which is the same data.

## 8. The duplicate search

The result is shown with each candidate's confidence, matched signals and recommendation, and how the draft
differs from the nearest one. The preview completes whatever the search finds: a person decides.

The search reads a local copy, so the preview also says how much of the project that copy covers. It compares
the number of the project's stories in the catalog with the number Jira holds, and warns when Jira holds more.

A catalog that does not match its records stops the preview.

## 9. Tests

    cd participant/skills/jira-create-story-preview && python3 -m unittest discover -s tests -v

## 10. What it does not do

- It does not create anything. A later quest does the write.
- It cannot promise that Jira would accept the payload. Jira has no documented way to try a create without
  making one, and its list of required fields does not cover a project's workflow rules or automation.
- It sets single-choice custom fields only.
- It sends the description as plain paragraphs and lists.
- Its "unchanged" check covers the project's stories: their number, ids and update times. It does not look at
  the rest of the site.
