# Fields the Jira updater may change

This is the list for the workflow in
`participant/evidence/jira-update-fields/jira-attempt-008/scripts/update.py`. The rule is refuse by default: the
workflow holds a list of three fields, and any field not on it is refused without needing a reason. There is no
option that widens the list.

## Supported fields and their allowed values

| Field | Jira's field id | Allowed values | What is sent to Jira |
|---|---|---|---|
| Labels | `labels` | The whole list wanted. At most 10 labels, none repeated. Each label is lowercase letters, digits and hyphens, starts with a letter or a digit, and is at most 50 characters long. An empty list is allowed. | The list |
| Due date | `duedate` | A real date written `YYYY-MM-DD`, between the years 2000 and 2100. | The date |
| Priority | `priority` | The name of one of the priorities Jira offers for that story, matched exactly. | That priority's id |

Notes on the choices.

- The label rule is this workflow's own and is stricter than Jira's. Atlassian's API documentation states no
  rule for label characters or length.
- Clearing a due date is refused. The documentation shows how to set a date and does not say how to clear one.
- Priority values are not a fixed list in this file. The preview asks Jira which priorities it offers for the
  one story (`GET /rest/api/3/issue/{id}/editmeta`) and accepts a name only if exactly one offered priority has
  it.
- A supported field is still refused for a story where Jira does not list it as editable by this identity. On
  some projects a field such as priority is switched off.
- A field that already holds the wanted value is reported and not sent.

## Fields that are refused

Every field that is not one of the three above. That includes, each for a reason:

| Field | Why the workflow does not change it |
|---|---|
| Assignee, reporter | They say who is responsible and who asked. Changing the assignee is the quest's own scenario. |
| Status | Moving a story through its workflow is a different act from editing a field. |
| Summary, description | Free text. Changing them carries text outward and can erase what someone wrote. |
| Project, issue type, parent | They move the story or change what it is. |
| Security level | It decides who can see the story at all. |
| Custom fields, and everything else | Not on the list. |

A change file that names an unsupported field is refused whole, even if it also names a supported one. The
refusal happens when the change file is read, before any request is sent to Jira.

## A run showing unsupported fields being refused

From `participant/evidence/jira-update-fields/jira-attempt-008/logs/unsupported-field.txt`, recorded against the
fake Jira. The first change file asks for priority and also for the assignee. The second asks for the summary.

```text
$ python3 .../scripts/update.py preview --source fake --change .../scripts/changes/unsupported-assignee.json --allowlist .../scripts/fake-allowlist.json --state STATE

REFUSED: the field "assignee" is not supported. This workflow changes only labels, duedate, priority, and refuses every other field.
Nothing has been written.
exit code: 1

$ python3 .../scripts/update.py preview --source fake --change .../scripts/changes/unsupported-summary.json --allowlist .../scripts/fake-allowlist.json --state STATE

REFUSED: the field "summary" is not supported. This workflow changes only labels, duedate, priority, and refuses every other field.
Nothing has been written.
exit code: 1
```

The log goes on to show the fake Jira holding the same values afterwards, the priority included.

## A preview showing the old and new value of each supported field

From `participant/evidence/jira-update-fields/jira-attempt-008/logs/preview.txt`, recorded against the fake
Jira. The change file asks for all three fields.

```text
PREVIEW. Nothing has been written.

Jira site:  https://fixture-site.example.invalid  (site fingerprint 738169e667642f09)
Project:    SAND (project id 20001). On the sandbox allowlist: yes.
Story:      SAND-1 (issue id 30001). The id is what identifies it.

Changes that would be made: 3 fields.
  labels    now:    ["onboarding"]
            after:  ["onboarding", "q4"]
  duedate   now:    2026-12-01
            after:  2026-12-15
  priority  now:    "Medium" (id 3)
            after:  "High" (id 2)
Nothing else on the story would be sent.
```

The same on the participant's real Jira sandbox, from `logs/live-preview.txt`, with the site's address removed
by the workflow when it saved the log. That change file asked for two of the three fields.

```text
Changes that would be made: 2 fields.
  labels    now:    (none)
            after:  ["gtq-sandbox"]
  duedate   now:    2026-11-15
            after:  2026-12-15
Nothing else on the story would be sent. Not in this change: priority.
```

## Where the workflow may write

Only to a project on the sandbox allowlist, `participant/context/jira/update/sandbox-allowlist.json`. An entry
is a project id together with a fingerprint of the Jira site's address, because project ids repeat from site to
site. Entries are added by a person.
